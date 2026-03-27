import glob
import os
import os.path as op

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

from utils import coords, common, fastmerl

device = "cpu"
Xvars = ["hx", "hy", "hz", "dx", "dy", "dz"]
Yvars = ["brdf_r", "brdf_g", "brdf_b"]
Mvars = ["median_r", "median_g", "median_b"]


def brdf_to_rgb(rvectors, brdf):
    hx = np.reshape(rvectors[:, 0], (-1, 1))
    hy = np.reshape(rvectors[:, 1], (-1, 1))
    hz = np.reshape(rvectors[:, 2], (-1, 1))
    dx = np.reshape(rvectors[:, 3], (-1, 1))
    dy = np.reshape(rvectors[:, 4], (-1, 1))
    dz = np.reshape(rvectors[:, 5], (-1, 1))

    theta_h = np.arctan2(np.sqrt(hx ** 2 + hy ** 2), hz)
    theta_d = np.arctan2(np.sqrt(dx ** 2 + dy ** 2), dz)
    phi_d = np.arctan2(dy, dx)
    wiz = np.cos(theta_d) * np.cos(theta_h) - np.sin(theta_d) * np.cos(phi_d) * np.sin(theta_h)
    return brdf * np.clip(wiz, 0, 1)


def default_teacher_dir():
    return op.join(op.dirname(op.abspath(__file__)), "data", "analytic_teacher")


def teacher_cache_path(teacher_root, dataset, fname):
    if not teacher_root:
        return None
    mat_name = op.splitext(op.basename(fname))[0]
    return op.join(teacher_root, dataset, mat_name + ".pt")


def detach_teacher_dict(payload):
    if isinstance(payload, list):
        return [detach_teacher_dict(value) for value in payload]
    result = {}
    for key, value in payload.items():
        if torch.is_tensor(value):
            result[key] = value.to(dtype=torch.float32)
        elif isinstance(value, dict):
            result[key] = detach_teacher_dict(value)
        elif isinstance(value, list):
            result[key] = [detach_teacher_dict(item) for item in value]
        else:
            result[key] = value
    return result


def load_teacher_payload(teacher_root, dataset, fname):
    cache_path = teacher_cache_path(teacher_root, dataset, fname)
    if cache_path is None or not op.exists(cache_path):
        return None
    payload = torch.load(cache_path, map_location="cpu")
    analytic_params = payload.get("analytic_params", payload)
    return detach_teacher_dict(analytic_params)


def sample_indices_from_pool(pool, sample_count):
    if sample_count <= 0 or pool.numel() == 0:
        return torch.empty(0, dtype=torch.long)
    if pool.numel() >= sample_count:
        perm = torch.randperm(pool.numel())[:sample_count]
        return pool[perm]
    extra = pool[torch.randint(pool.numel(), (sample_count - pool.numel(),))]
    return torch.cat([pool, extra], dim=0)


def build_sampling_indices(coords, amps, sparse_samples, sampling_mode):
    total_samples = coords.shape[0]
    if sparse_samples >= total_samples:
        return torch.arange(total_samples)

    if sampling_mode == "random":
        return torch.randperm(total_samples)[:sparse_samples]

    brightness = amps.max(dim=-1).values
    highlight_thresh = torch.quantile(brightness, 0.9)
    highlight_pool = torch.nonzero(brightness >= highlight_thresh, as_tuple=False).flatten()

    hz = coords[:, 2]
    near_spec_thresh = torch.quantile(hz, 0.9)
    near_spec_pool = torch.nonzero(hz >= near_spec_thresh, as_tuple=False).flatten()

    num_random = max(int(sparse_samples * 0.5), 1)
    num_highlight = max(int(sparse_samples * 0.25), 1)
    num_spec = max(sparse_samples - num_random - num_highlight, 1)

    idx = torch.cat(
        [
            torch.randperm(total_samples)[:num_random],
            sample_indices_from_pool(highlight_pool, num_highlight),
            sample_indices_from_pool(near_spec_pool, num_spec),
        ],
        dim=0,
    )
    idx = torch.unique(idx)
    while idx.numel() < sparse_samples:
        filler = torch.randperm(total_samples)[: sparse_samples - idx.numel()]
        idx = torch.unique(torch.cat([idx, filler], dim=0))
    if idx.numel() > sparse_samples:
        idx = idx[:sparse_samples]
    return idx


def get_merl_median_vals(rvectors):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    median_path = os.path.join(current_dir, "data", "merl_median.binary")
    if not os.path.exists(median_path):
        median_path = "data/merl_median.binary"
    median = fastmerl.Merl(median_path)
    return brdf_values(rvectors, brdf=median)


def get_epfl_median_vals(rvectors):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    median_np_path = os.path.join(current_dir, "data", "epfl_median.npy")
    if not os.path.exists(median_np_path):
        median_np_path = os.path.join("data", "epfl_median.npy")
    median_np = np.load(median_np_path)

    any_fullbin = os.path.join(current_dir, "data", "brdf.fullbin")
    if not os.path.exists(any_fullbin):
        any_fullbin = os.path.join("data", "brdf.fullbin")

    median = fastmerl.Merl(any_fullbin)
    median.from_array(median_np)
    median.brdf_np = np.array(median.brdf)
    median.sampling_phi_d = 180
    return brdf_values(rvectors, brdf=median)


class BaseBRDFDataset(Dataset):
    def __init__(self, sparse_samples=4000, sampling_mode="random", teacher_dir=""):
        self.sparse_samples = sparse_samples
        self.sampling_mode = sampling_mode
        self.teacher_dir = teacher_dir
        self.fnames = []
        self.train_coords = []
        self.train_brdfvals = []
        self.train_medianvals = []
        self.teacher_payloads = []

    def build_item(self, idx):
        total_samples = self.train_coords[idx].shape[0]
        idx_sparse = build_sampling_indices(
            self.train_coords[idx],
            self.train_brdfvals[idx],
            min(self.sparse_samples, total_samples),
            self.sampling_mode,
        )

        context_coords = self.train_coords[idx][idx_sparse]
        context_amps = self.train_brdfvals[idx][idx_sparse]

        in_dict = {
            "idx": idx,
            "coords": self.train_coords[idx],
            "amps": self.train_brdfvals[idx],
            "median_vals": self.train_medianvals[idx],
            "context_coords": context_coords,
            "context_amps": context_amps,
        }
        gt_dict = {
            "amps": self.train_brdfvals[idx],
            "median_vals": self.train_medianvals[idx],
        }
        teacher_payload = self.teacher_payloads[idx] if idx < len(self.teacher_payloads) else None
        if teacher_payload is not None:
            gt_dict["teacher_params"] = teacher_payload
        return in_dict, gt_dict

    def __len__(self):
        return len(self.fnames)

    def __getitem__(self, idx):
        return self.build_item(idx)


class EPFL(BaseBRDFDataset):
    def __init__(self, merlPath, sparse_samples=4000, sampling_mode="random", teacher_dir=""):
        super().__init__(sparse_samples=sparse_samples, sampling_mode=sampling_mode, teacher_dir=teacher_dir)
        self.fnames = glob.glob(op.join(merlPath, "*.csv"))

        for fname in self.fnames:
            df = pd.read_csv(fname, sep=" ")
            tensor = torch.tensor(df.values, dtype=torch.float32)
            amps = tensor[:, 9:].detach().numpy()

            any_fullbin = "brdf.fullbin"
            merl = fastmerl.Merl(any_fullbin)
            merl.from_array(amps)
            merl.brdf_np = np.array(merl.brdf)
            merl.sampling_phi_d = 180
            reflectance_train = generate_nn_datasets(merl, nsamples=180 * 90 * 90, dataset="EPFL", pct=1)

            self.train_coords.append(reflectance_train[Xvars].values)
            self.train_brdfvals.append(reflectance_train[Yvars].values)
            self.train_medianvals.append(reflectance_train[Mvars].values)
            self.teacher_payloads.append(load_teacher_payload(teacher_dir, "EPFL", fname))
            print(fname)

        self.train_coords = [torch.tensor(arr, dtype=torch.float32, device=device) for arr in self.train_coords]
        self.train_brdfvals = [torch.tensor(arr, dtype=torch.float32, device=device) for arr in self.train_brdfvals]
        self.train_medianvals = [torch.tensor(arr, dtype=torch.float32, device=device) for arr in self.train_medianvals]


class MerlDataset(BaseBRDFDataset):
    def __init__(
        self,
        merlPath,
        sparse_samples=4000,
        max_materials=None,
        seed=42,
        file_list=None,
        sampling_mode="random",
        teacher_dir="",
    ):
        super().__init__(sparse_samples=sparse_samples, sampling_mode=sampling_mode, teacher_dir=teacher_dir)
        if file_list:
            self.fnames = list(file_list)
        elif os.path.isfile(merlPath):
            self.fnames = [merlPath]
        else:
            self.fnames = sorted(glob.glob(op.join(merlPath, "*.binary")))
            if max_materials and len(self.fnames) > max_materials:
                rng = np.random.default_rng(seed)
                idx = rng.permutation(len(self.fnames))[:max_materials]
                self.fnames = [self.fnames[i] for i in idx]

        for fname in self.fnames:
            brdf = fastmerl.Merl(fname)
            reflectance_train = generate_nn_datasets(brdf, nsamples=180 * 90 * 90, dataset="MERL", pct=1)
            self.train_coords.append(reflectance_train[Xvars].values)
            self.train_brdfvals.append(reflectance_train[Yvars].values)
            self.train_medianvals.append(reflectance_train[Mvars].values)
            self.teacher_payloads.append(load_teacher_payload(teacher_dir, "MERL", fname))
            print(fname)

        self.train_coords = [torch.tensor(arr, dtype=torch.float32, device=device) for arr in self.train_coords]
        self.train_brdfvals = [torch.tensor(arr, dtype=torch.float32, device=device) for arr in self.train_brdfvals]
        self.train_medianvals = [torch.tensor(arr, dtype=torch.float32, device=device) for arr in self.train_medianvals]


def generate_nn_datasets(brdf, nsamples, dataset, pct=1):
    rangles = np.random.uniform([0, 0, 0], [np.pi / 2.0, np.pi / 2.0, 2 * np.pi], [int(nsamples * pct), 3]).T
    rangles[2] = common.normalize_phid(rangles[2])
    rvectors = coords.rangles_to_rvectors(*rangles)

    if dataset == "MERL":
        median_vals = get_merl_median_vals(rvectors)
    elif dataset == "EPFL":
        median_vals = get_epfl_median_vals(rvectors)
    else:
        raise ValueError(f"Unsupported dataset: {dataset}")

    brdf_vals = brdf_values(rvectors, brdf=brdf)
    normalized_brdf_vals = np.log(1 + ((brdf_vals + 0.002) / (median_vals + 0.002)))

    df = pd.DataFrame(
        np.concatenate([rvectors.T, normalized_brdf_vals, median_vals], axis=1),
        columns=[*Xvars, *Yvars, *Mvars],
    )
    df = df[(df.T != 0).any()]
    df = df.drop(df[df["brdf_r"] < 0].index)
    return df


def brdf_values(rvectors, brdf=None, model=None):
    if brdf is not None:
        rangles = coords.rvectors_to_rangles(*rvectors)
        brdf_arr = brdf.eval_interp(*rangles).T
    elif model is not None:
        raise RuntimeError("Should not have entered that branch at all from the original code")
    else:
        raise NotImplementedError("Something went really wrong.")
    brdf_arr *= common.mask_from_array(rvectors.T).reshape(-1, 1)
    return brdf_arr
