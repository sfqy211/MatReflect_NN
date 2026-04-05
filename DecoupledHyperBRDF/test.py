import time
import argparse
import os

import torch

from data_processing import *
from utils.common import get_device


def detach_to_cpu(value):
    if isinstance(value, dict):
        return {key: detach_to_cpu(val) for key, val in value.items()}
    if isinstance(value, list):
        return [detach_to_cpu(item) for item in value]
    if torch.is_tensor(value):
        tensor = value.detach().cpu()
        if tensor.dim() > 0 and tensor.shape[0] == 1:
            tensor = tensor.squeeze(0)
        return tensor
    return value


parser = argparse.ArgumentParser()
parser.add_argument("--model")
parser.add_argument("--binary")
parser.add_argument("--destdir")
parser.add_argument("--dataset", choices=["MERL", "EPFL"], default="MERL")
parser.add_argument("--sparse_samples", type=int, default=4000)

args = parser.parse_args()
device = get_device()
print(f"Using device: {device}")


def build_export_payload(model, model_output):
    model_type = getattr(model, "model_type", "baseline")
    if model_type == "decoupled":
        return {
            "format_version": 2,
            "model_type": "decoupled",
            "dataset": args.dataset,
            "analytic_lobes": int(getattr(model, "analytic_lobes", 1)),
            "analytic_params": detach_to_cpu(model_output["analytic_params"]),
            "residual_hypo_params": detach_to_cpu(model_output["residual_hypo_params"]),
            "gate_hypo_params": detach_to_cpu(model_output["gate_hypo_params"]),
        }

    return {
        "format_version": 1,
        "model_type": "baseline",
        "dataset": args.dataset,
        "hypo_params": detach_to_cpu(model_output["hypo_params"]),
    }


def eval_model(model, dataloader):
    for _, (model_input, gt) in enumerate(dataloader):
        start = time.time()

        model.eval()
        model_input = {key: value.to(device) for key, value in model_input.items()}

        idx = int(model_input["idx"].item()) if torch.is_tensor(model_input["idx"]) else int(model_input["idx"])
        full_path = dataloader.dataset.fnames[idx]
        mat_name = os.path.splitext(os.path.basename(full_path))[0]

        model_output = model(model_input)

        if not os.path.exists(args.destdir):
            os.makedirs(args.destdir)

        save_path = os.path.join(args.destdir, mat_name + ".pt")
        torch.save(build_export_payload(model, model_output), save_path)
        print(time.time() - start)
    return -1


if args.dataset == "MERL":
    dataset = MerlDataset(args.binary, sparse_samples=args.sparse_samples)
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1)
else:
    dataset = EPFL(args.binary, sparse_samples=args.sparse_samples)
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1)


model = torch.load(args.model, map_location=device, weights_only=False)
model.to(device)
eval_model(model, dataloader)
