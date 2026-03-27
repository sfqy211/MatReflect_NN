import json
import time
import argparse
import os
import glob
from functools import partial

import pandas as pd
import torch
from sklearn.metrics import mean_squared_error

from utils.common import *
from models import *
from data_processing import *


def brdf_to_rgb(rvectors, brdf):
    hx = torch.reshape(rvectors[:, :, 0], (-1, 1))
    hy = torch.reshape(rvectors[:, :, 1], (-1, 1))
    hz = torch.reshape(rvectors[:, :, 2], (-1, 1))
    dx = torch.reshape(rvectors[:, :, 3], (-1, 1))
    dy = torch.reshape(rvectors[:, :, 4], (-1, 1))
    dz = torch.reshape(rvectors[:, :, 5], (-1, 1))

    theta_h = torch.atan2(torch.sqrt(hx ** 2 + hy ** 2), hz)
    theta_d = torch.atan2(torch.sqrt(dx ** 2 + dy ** 2), dz)
    phi_d = torch.atan2(dy, dx)
    wiz = torch.cos(theta_d) * torch.cos(theta_h) - torch.sin(theta_d) * torch.cos(phi_d) * torch.sin(theta_h)
    return brdf * torch.clamp(wiz, 0, 1)


def move_to_device(value, target_device):
    if torch.is_tensor(value):
        return value.to(target_device)
    if isinstance(value, dict):
        return {key: move_to_device(val, target_device) for key, val in value.items()}
    if isinstance(value, list):
        return [move_to_device(item, target_device) for item in value]
    return value


def image_mse(model_output, gt):
    pred_rgb = brdf_to_rgb(model_output["model_in"], model_output["model_out"])
    target_rgb = brdf_to_rgb(model_output["model_in"], gt["amps"])
    return {"img_loss": ((pred_rgb - target_rgb) ** 2).mean()}


def latent_loss(model_output):
    return torch.mean(model_output["latent_vec"] ** 2)


def iter_hypo_param_sets(model_output):
    if "residual_hypo_params" in model_output:
        yield model_output["residual_hypo_params"]
    if "gate_hypo_params" in model_output:
        yield model_output["gate_hypo_params"]
    elif "hypo_params" in model_output:
        yield model_output["hypo_params"]


def hypo_weight_loss(model_output):
    weight_sum = 0.0
    total_weights = 0
    for param_group in iter_hypo_param_sets(model_output):
        for weight in param_group.values():
            weight_sum += torch.sum(weight ** 2)
            total_weights += weight.numel()
    if total_weights == 0:
        return torch.tensor(0.0, device=model_output["model_out"].device)
    return weight_sum * (1.0 / total_weights)


def achromatic(brdf):
    return brdf.mean(dim=-1, keepdim=True)


def analytic_supervision_loss(model_output, gt):
    if "analytic_out" not in model_output:
        return torch.tensor(0.0, device=model_output["model_out"].device)
    if "teacher_params" in gt:
        teacher_analytic = eval_analytic_brdf(
            model_output["model_in"],
            gt["teacher_params"],
            median_vals=gt.get("median_vals"),
        )
        return ((model_output["analytic_out"] - teacher_analytic) ** 2).mean()
    return ((achromatic(model_output["analytic_out"]) - achromatic(gt["amps"])) ** 2).mean()


def residual_target_loss(model_output, gt):
    if "residual_out" not in model_output:
        return torch.tensor(0.0, device=model_output["model_out"].device)
    target = torch.clamp(gt["amps"] - model_output["analytic_out"].detach(), min=0.0)
    return ((model_output["residual_out"] - target) ** 2).mean()


def specular_mask(amps, percentile):
    brightness = amps.max(dim=-1, keepdim=True).values
    flat = brightness.reshape(brightness.shape[0], -1)
    threshold = torch.quantile(flat, percentile, dim=1, keepdim=True).view(-1, 1, 1)
    return (brightness >= threshold).float().expand_as(amps)


def specular_loss(model_output, gt, percentile):
    mask = specular_mask(gt["amps"], percentile)
    diff = (model_output["model_out"] - gt["amps"]) ** 2
    denom = torch.clamp(mask.sum(), min=1.0)
    return (diff * mask).sum() / denom


def gate_regularization_loss(model_output):
    if "gate_out" not in model_output:
        return torch.tensor(0.0, device=model_output["model_out"].device)
    return model_output["gate_out"].mean()


def get_schedule_multiplier(epoch, warmup_epochs):
    if warmup_epochs <= 0:
        return 1.0
    return min(float(epoch + 1) / float(warmup_epochs), 1.0)


def get_gate_decay(epoch, args):
    if epoch < args.stage_a_epochs:
        return 1.0
    if args.stage_b_ramp_epochs <= 0:
        return 0.0
    progress = min(float(epoch - args.stage_a_epochs + 1) / float(args.stage_b_ramp_epochs), 1.0)
    return max(1.0 - progress, 0.0)


def image_hypernetwork_loss(args, epoch, model_output, gt):
    losses = {
        "img_loss": image_mse(model_output, gt)["img_loss"],
        "latent_loss": args.kl_weight * latent_loss(model_output),
        "hypo_weight_loss": args.fw_weight * hypo_weight_loss(model_output),
    }

    if "analytic_out" in model_output:
        spec_mult = get_schedule_multiplier(epoch, args.stage_a_epochs)
        gate_mult = get_gate_decay(epoch, args)
        losses["analytic_loss"] = args.analytic_loss_weight * analytic_supervision_loss(model_output, gt)
        losses["residual_loss"] = args.residual_loss_weight * residual_target_loss(model_output, gt)
        losses["spec_loss"] = args.spec_loss_weight * spec_mult * specular_loss(
            model_output, gt, args.spec_percentile
        )
        losses["gate_reg_loss"] = args.gate_reg_weight * gate_mult * gate_regularization_loss(model_output)

    return losses


def eval_epoch(model, train_dataloader, loss_fn, optim, epoch):
    epoch_loss = []
    individual_loss = []
    for _, (model_input, gt) in enumerate(train_dataloader):
        model.eval()
        model_input = move_to_device(model_input, device)
        gt = move_to_device(gt, device)

        model_output = model(model_input)
        losses = loss_fn(epoch=epoch, model_output=model_output, gt=gt)

        train_loss = 0.0
        for loss in losses.values():
            train_loss += loss.mean()
        individual_loss.append([loss.cpu().detach().numpy() for loss in losses.values()])
        epoch_loss.append(train_loss.item())
    return np.mean(epoch_loss), np.stack(individual_loss).mean(axis=0)


def train_epoch(model, train_dataloader, loss_fn, optim, epoch):
    epoch_loss = []
    individual_loss = []
    for _, (model_input, gt) in enumerate(train_dataloader):
        model.train()
        model_input = move_to_device(model_input, device)
        gt = move_to_device(gt, device)

        model_output = model(model_input)
        losses = loss_fn(epoch=epoch, model_output=model_output, gt=gt)

        train_loss = 0.0
        for loss in losses.values():
            train_loss += loss.mean()

        individual_loss.append([loss.cpu().detach().numpy() for loss in losses.values()])
        optim.zero_grad()
        train_loss.backward()

        if clip_grad:
            if isinstance(clip_grad, bool):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=clip_grad)
        optim.step()
        epoch_loss.append(train_loss.item())
    return np.mean(epoch_loss), np.stack(individual_loss).mean(axis=0)


def eval_model(model, dataloader, path_=None, name=""):
    model_inp = []
    model_out = []
    for _, (model_input, gt) in enumerate(dataloader):
        model.eval()
        model_input = move_to_device(model_input, device)
        gt = move_to_device(gt, device)
        model_output = model(model_input)
        model_out.append(model_output["model_out"].cpu().detach().numpy())
        model_inp.append(gt["amps"].cpu().numpy())
    y_true = np.concatenate(model_inp)[:, :, 0]
    y_pred = np.concatenate(model_out)[:, :, 0]
    return mean_squared_error(y_true, y_pred)


def load_baseline_into_decoupled(model, baseline_checkpoint):
    baseline = torch.load(baseline_checkpoint, map_location=device)
    if not hasattr(baseline, "state_dict"):
        return

    baseline_state = baseline.state_dict()
    model_state = model.state_dict()
    remapped = {}

    for key, value in baseline_state.items():
        if key.startswith("set_encoder.") and key in model_state and model_state[key].shape == value.shape:
            remapped[key] = value

    prefix_map = {
        "hypo_net.": "residual_hypo_net.",
        "hyper_net.": "residual_hyper_net.",
    }
    for old_prefix, new_prefix in prefix_map.items():
        for key, value in baseline_state.items():
            if key.startswith(old_prefix):
                mapped_key = new_prefix + key[len(old_prefix) :]
                if mapped_key in model_state and model_state[mapped_key].shape == value.shape:
                    remapped[mapped_key] = value

    model_state.update(remapped)
    model.load_state_dict(model_state, strict=False)


def build_model(args):
    if args.model_type == "baseline":
        return HyperBRDF(in_features=6, out_features=3).to(device)

    model = DecoupledHyperBRDF(
        in_features=6,
        out_features=3,
        gate_bias_init=args.gate_bias_init,
        analytic_lobes=args.analytic_lobes,
    ).to(device)
    if args.baseline_checkpoint and op.exists(args.baseline_checkpoint):
        load_baseline_into_decoupled(model, args.baseline_checkpoint)
    return model


parser = argparse.ArgumentParser("")
parser.add_argument("--destdir", dest="destdir", type=str, required=True, help="output directory")
parser.add_argument("--binary", type=str, required=True, help="dataset path")
parser.add_argument("--dataset", choices=["MERL", "EPFL"], default="MERL")
parser.add_argument("--model_type", choices=["baseline", "decoupled"], default="decoupled")
parser.add_argument("--baseline_checkpoint", type=str, default="", help="optional baseline checkpoint for warm start")
parser.add_argument("--kl_weight", type=float, default=0.0, help="latent loss weight")
parser.add_argument("--fw_weight", type=float, default=0.0, help="hypo loss weight")
parser.add_argument("--analytic_loss_weight", type=float, default=0.1, help="analytic weak supervision weight")
parser.add_argument("--residual_loss_weight", type=float, default=0.1, help="residual supervision weight")
parser.add_argument("--spec_loss_weight", type=float, default=0.2, help="highlight reconstruction weight")
parser.add_argument("--gate_reg_weight", type=float, default=0.05, help="gate regularization weight")
parser.add_argument("--spec_percentile", type=float, default=0.9, help="highlight mask percentile")
parser.add_argument("--gate_bias_init", type=float, default=-2.0, help="initial gate bias")
parser.add_argument("--analytic_lobes", type=int, choices=[1, 2], default=1, help="number of GGX lobes in analytic base")
parser.add_argument("--stage_a_epochs", type=int, default=10, help="warmup epochs before releasing spec branch")
parser.add_argument("--stage_b_ramp_epochs", type=int, default=20, help="gate regularization decay epochs")
parser.add_argument("--epochs", type=int, default=100, help="number of epochs")
parser.add_argument("--sparse_samples", type=int, default=4000, help="number of sparse samples for encoder")
parser.add_argument("--sampling_mode", choices=["random", "hybrid"], default="hybrid", help="context sampling mode")
parser.add_argument("--teacher_dir", type=str, default=default_teacher_dir(), help="analytic teacher cache directory")
parser.add_argument("--lr", type=float, default=5e-5, help="learning rate")
parser.add_argument("--keepon", action="store_true", help="continue training from loaded checkpoint")
parser.add_argument("--train_subset", type=int, default=0, help="number of materials to sample for training (0 = all)")
parser.add_argument("--train_seed", type=int, default=42, help="random seed for training material sampling")

args = parser.parse_args()
device = get_device()
print(device)

path_ = op.join(args.destdir, args.dataset)
create_directory(path_)
create_directory(op.join(path_, "img"))

prev_args = None
prev_train_losses = None
prev_all_losses = None
prev_args_path = op.join(path_, "args.txt")
if args.keepon and op.exists(prev_args_path):
    with open(prev_args_path, "r") as handle:
        prev_args = json.load(handle)
    sticky_keys = [
        "model_type",
        "baseline_checkpoint",
        "kl_weight",
        "fw_weight",
        "analytic_loss_weight",
        "residual_loss_weight",
        "spec_loss_weight",
        "gate_reg_weight",
        "spec_percentile",
        "gate_bias_init",
        "analytic_lobes",
        "stage_a_epochs",
        "stage_b_ramp_epochs",
        "sparse_samples",
        "sampling_mode",
        "teacher_dir",
        "lr",
        "train_subset",
        "train_seed",
    ]
    for key in sticky_keys:
        if key in prev_args:
            setattr(args, key, prev_args[key])
    if "binary" in prev_args and prev_args["binary"]:
        args.binary = prev_args["binary"]
    if "dataset" in prev_args and prev_args["dataset"]:
        args.dataset = prev_args["dataset"]
    prev_epochs = prev_args["epochs"] if isinstance(prev_args.get("epochs"), int) else 0
else:
    prev_epochs = 0

train_loss_path = op.join(path_, "train_loss.csv")
all_loss_path = op.join(path_, "all_losses.csv")
completed_epochs = 0
if args.keepon and op.exists(train_loss_path):
    train_df = pd.read_csv(train_loss_path)
    prev_train_losses = train_df.iloc[:, -1].tolist() if train_df.shape[1] > 1 else train_df.iloc[:, 0].tolist()
    completed_epochs = max(len(prev_train_losses) - 1, 0)
if args.keepon and op.exists(all_loss_path):
    all_df = pd.read_csv(all_loss_path)
    prev_all_losses = (
        all_df.drop(columns=[all_df.columns[0]]).values.tolist() if all_df.shape[1] > 1 else all_df.values.tolist()
    )

if args.keepon:
    base_epochs = max(prev_epochs, completed_epochs)
    args.epochs = base_epochs + args.epochs

with open(op.join(path_, "args.txt"), "w") as handle:
    json.dump(args.__dict__, handle, indent=2)

loss_fn = partial(image_hypernetwork_loss, args)

clip_grad = True
lr = args.lr
epochs = args.epochs
binary = args.binary

if args.dataset == "MERL":
    subset_list_path = op.join(path_, "train_subset.json")
    subset_files = None
    if args.train_subset and args.train_subset > 0:
        if args.keepon and op.exists(subset_list_path):
            try:
                with open(subset_list_path, "r") as handle:
                    subset_files = json.load(handle)
            except Exception:
                subset_files = None
            if subset_files:
                subset_files = [path for path in subset_files if op.exists(path)]
        if not subset_files:
            all_files = sorted(glob.glob(op.join(binary, "*.binary")))
            if len(all_files) > args.train_subset:
                rng = np.random.default_rng(args.train_seed)
                idx = rng.permutation(len(all_files))[: args.train_subset]
                subset_files = [all_files[i] for i in idx]
            else:
                subset_files = all_files
            with open(subset_list_path, "w") as handle:
                json.dump(subset_files, handle, indent=2)
    max_materials = None if subset_files else (args.train_subset if args.train_subset and args.train_subset > 0 else None)
    dataset = MerlDataset(
        binary,
        sparse_samples=args.sparse_samples,
        max_materials=max_materials,
        seed=args.train_seed,
        file_list=subset_files,
        sampling_mode=args.sampling_mode,
        teacher_dir=args.teacher_dir,
    )
    num_workers = 0 if os.name == "nt" else 6
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1, num_workers=num_workers)
else:
    dataset = EPFL(binary, sparse_samples=args.sparse_samples, sampling_mode=args.sampling_mode, teacher_dir=args.teacher_dir)
    num_workers = 0 if os.name == "nt" else 6
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1, num_workers=num_workers)


start_time = time.time()
if args.keepon:
    model = torch.load(op.join(path_, "checkpoint.pt"), map_location=device)
    model.to(device)
else:
    model = build_model(args)

train_losses = prev_train_losses if prev_train_losses is not None else []
all_losses = prev_all_losses if prev_all_losses is not None else []
optim = torch.optim.Adam(lr=lr, params=model.parameters())
start_epoch = completed_epochs if args.keepon else 0

if not args.keepon:
    epoch_loss, individual_losses = eval_epoch(model, dataloader, loss_fn, optim, 0)
    train_losses.append(epoch_loss)
    all_losses.append(individual_losses)
    print("init", epoch_loss, all_losses)

for epoch in range(start_epoch, epochs):
    epoch_loss, individual_losses = train_epoch(model, dataloader, loss_fn, optim, epoch)
    train_losses.append(epoch_loss)
    all_losses.append(individual_losses)
    print(epoch, epoch_loss, all_losses)

pd.DataFrame(train_losses).to_csv(op.join(path_, "train_loss.csv"))
pd.DataFrame(all_losses).to_csv(op.join(path_, "all_losses.csv"))
torch.save(model, op.join(path_, "checkpoint.pt"))

print("training_seconds", time.time() - start_time)
