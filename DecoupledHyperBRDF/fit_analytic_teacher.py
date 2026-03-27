import argparse
import os
import glob

import numpy as np
import torch
import pandas as pd

from data_processing import (
    generate_nn_datasets,
    default_teacher_dir,
    Xvars,
    Yvars,
    Mvars,
)
from models import analytic_param_tensor_to_dict, eval_analytic_brdf, analytic_param_dim
from utils import fastmerl
from utils.common import create_directory, get_device


def detach_to_cpu(value):
    if torch.is_tensor(value):
        tensor = value.detach().cpu()
        if tensor.dim() > 0 and tensor.shape[0] == 1:
            tensor = tensor.squeeze(0)
        return tensor
    if isinstance(value, dict):
        return {key: detach_to_cpu(val) for key, val in value.items()}
    if isinstance(value, list):
        return [detach_to_cpu(item) for item in value]
    return value


def get_file_list(binary_path, dataset):
    if os.path.isfile(binary_path):
        return [binary_path]
    pattern = "*.binary" if dataset == "MERL" else "*.csv"
    return sorted(glob.glob(os.path.join(binary_path, pattern)))


def load_material_samples(fname, dataset, fit_samples):
    if dataset == "MERL":
        brdf = fastmerl.Merl(fname)
        df = generate_nn_datasets(brdf, nsamples=fit_samples, dataset="MERL", pct=1)
    else:
        df_csv = pd.read_csv(fname, sep=" ")
        tensor = torch.tensor(df_csv.values, dtype=torch.float32)
        amps = tensor[:, 9:].detach().numpy()
        any_fullbin = "brdf.fullbin"
        brdf = fastmerl.Merl(any_fullbin)
        brdf.from_array(amps)
        brdf.brdf_np = np.array(brdf.brdf)
        brdf.sampling_phi_d = 180
        df = generate_nn_datasets(brdf, nsamples=fit_samples, dataset="EPFL", pct=1)

    coords = torch.tensor(df[Xvars].values, dtype=torch.float32).unsqueeze(0)
    amps = torch.tensor(df[Yvars].values, dtype=torch.float32).unsqueeze(0)
    median_vals = torch.tensor(df[Mvars].values, dtype=torch.float32).unsqueeze(0)
    return coords, amps, median_vals


def fit_teacher_for_material(coords, amps, median_vals, steps, lr, spec_percentile, analytic_lobes, device):
    coords = coords.to(device)
    amps = amps.to(device)
    median_vals = median_vals.to(device)

    raw_params = torch.nn.Parameter(torch.zeros(1, analytic_param_dim(analytic_lobes), device=device))
    optimizer = torch.optim.Adam([raw_params], lr=lr)

    for _ in range(steps):
        analytic_params = analytic_param_tensor_to_dict(raw_params, analytic_lobes=analytic_lobes)
        pred = eval_analytic_brdf(coords, analytic_params, median_vals=median_vals)

        recon_loss = ((pred - amps) ** 2).mean()
        brightness = amps.max(dim=-1, keepdim=True).values
        threshold = torch.quantile(brightness.reshape(1, -1), spec_percentile, dim=1, keepdim=True).view(1, 1, 1)
        spec_mask = (brightness >= threshold).float().expand_as(amps)
        spec_loss = (((pred - amps) ** 2) * spec_mask).sum() / torch.clamp(spec_mask.sum(), min=1.0)
        achro_loss = ((pred.mean(dim=-1, keepdim=True) - amps.mean(dim=-1, keepdim=True)) ** 2).mean()

        loss = recon_loss + 0.5 * spec_loss + 0.25 * achro_loss
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    analytic_params = analytic_param_tensor_to_dict(raw_params.detach(), analytic_lobes=analytic_lobes)
    final_pred = eval_analytic_brdf(coords, analytic_params, median_vals=median_vals)
    final_loss = ((final_pred - amps) ** 2).mean().item()
    return detach_to_cpu(analytic_params), final_loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--dataset", choices=["MERL", "EPFL"], default="MERL")
    parser.add_argument("--destdir", default=default_teacher_dir())
    parser.add_argument("--fit_samples", type=int, default=32768)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--lr", type=float, default=5e-2)
    parser.add_argument("--spec_percentile", type=float, default=0.9)
    parser.add_argument("--analytic_lobes", type=int, choices=[1, 2], default=1)
    parser.add_argument("--max_materials", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = get_device()
    print(f"Using device: {device}")

    file_list = get_file_list(args.binary, args.dataset)
    if args.max_materials and args.max_materials > 0:
        file_list = file_list[: args.max_materials]

    out_dir = os.path.join(args.destdir, args.dataset)
    create_directory(out_dir)

    for fname in file_list:
        mat_name = os.path.splitext(os.path.basename(fname))[0]
        out_path = os.path.join(out_dir, mat_name + ".pt")

        coords, amps, median_vals = load_material_samples(fname, args.dataset, args.fit_samples)
        analytic_params, fit_loss = fit_teacher_for_material(
            coords,
            amps,
            median_vals,
            steps=args.steps,
            lr=args.lr,
            spec_percentile=args.spec_percentile,
            analytic_lobes=args.analytic_lobes,
            device=device,
        )

        torch.save(
            {
                "format_version": 1,
                "dataset": args.dataset,
                "material": mat_name,
                "analytic_params": analytic_params,
                "analytic_lobes": args.analytic_lobes,
                "fit_loss": fit_loss,
                "fit_samples": coords.shape[1],
                "steps": args.steps,
            },
            out_path,
        )
        print(f"saved {out_path} loss={fit_loss:.6f}")


if __name__ == "__main__":
    main()
