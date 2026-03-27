#!/usr/bin/env python3
import time
import glob
import os, sys
import os.path as op
from utils import coords, fastmerl
from utils.common import get_device
import numpy as np
import argparse
from pathlib import Path

import torch

from data_processing import brdf_values
from models import SingleBVPNet


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
    wiz = np.cos(theta_d) * np.cos(theta_h) - \
          np.sin(theta_d) * np.cos(phi_d) * np.sin(theta_h)
    rgb = brdf * np.clip(wiz, 0, 1)
    return rgb


def h5_to_fullmerl(h5, destdir=None, device='cpu'):
    t = time.time()

    basename = Path(h5).stem
    if (destdir == None):
        destdir = Path(h5).parent
    
    if not os.path.exists(destdir):
        os.makedirs(destdir)

    pred_fullbin = os.path.join(destdir, basename + '.fullbin')

    db_model = SingleBVPNet(out_features=3, hidden_features=60, type='relu', in_features=6)
    db_model.to(device)
    h5_model = torch.load(h5, map_location=device)
    for weight in h5_model:
        h5_model[weight] = torch.squeeze(h5_model[weight], 0)
    db_model.load_state_dict(h5_model)
    db_model.eval()

    rangle_names = ['theta_h', 'theta_d', 'phi_d']

    current_dir = os.path.dirname(os.path.abspath(__file__))

    any_fullbin = os.path.join(current_dir, 'data', 'brdf.fullbin')
    if not os.path.exists(any_fullbin):
        raise FileNotFoundError(f"Missing reference template: {any_fullbin}")
    merl = fastmerl.Merl(any_fullbin)

    if args.dataset == 'MERL' and merl.sampling_phi_d != 360:
        raise ValueError(f"Expected sampling_phi_d=360 for MERL, got {merl.sampling_phi_d}")
    if args.dataset == 'EPFL':
        merl.sampling_phi_d = 180

    df_rangles = merl.to_dataframe(angles_only=True)
    rvectors = coords.rangles_to_rvectors(*df_rangles[rangle_names].values.T).T
    rvectors = torch.tensor(rvectors).to(device)
    rvectors = rvectors.float()

    in_dict = {'idx': 0, 'coords': rvectors, 'amps': 0}

    model_input = {key: value for key, value in in_dict.items()}
    pred_brdf = db_model(model_input)['model_out']

    if args.dataset == 'MERL':
        median_path = os.path.join(current_dir, 'data', 'merl_median.binary')
        if not os.path.exists(median_path):
            median_path = 'data/merl_median.binary'
        
        median = fastmerl.Merl(median_path)
        median_vals = brdf_values(rvectors.cpu().T.detach().numpy(), brdf=median)
        median_vals = np.clip(median_vals, 1e-6, np.inf)
    elif args.dataset == 'EPFL':
        median_np_path = os.path.join(current_dir, 'data', 'epfl_median.npy')
        if not os.path.exists(median_np_path):
            median_np_path = os.path.join('data', 'epfl_median.npy')
        median_vals = np.load(median_np_path)

    pred_brdf = (np.exp(pred_brdf.cpu().detach().numpy()) - 1) * (median_vals + 0.002) - 0.002
    pred_brdf = np.clip(pred_brdf, a_min=1e-6, a_max=np.inf)
    target_len = merl.sampling_theta_h * merl.sampling_theta_d * merl.sampling_phi_d
    if pred_brdf.shape[0] < target_len:
        raise ValueError(f"Predicted BRDF length {pred_brdf.shape[0]} smaller than target {target_len}")
    pred_brdf = pred_brdf[:target_len, :]

    merl.from_array(pred_brdf)
    merl.write_merl_file(pred_fullbin)
    print('wrote ', pred_fullbin)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('pts')
    parser.add_argument('destdir')
    parser.add_argument('--dataset', choices=['MERL', 'EPFL'], default='MERL')
    parser.add_argument('--cuda_device', default='0', help=' ')
    parser.add_argument('--force', action='store_true', default=False, help=' ')
    args = parser.parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda_device
    device = get_device()
    print(f"Using device: {device}")

    if os.path.isdir(args.pts):
        for pt in os.listdir(args.pts):
            if pt.endswith('.pt'):
                print('Processing ', pt)
                h5_to_fullmerl(os.path.join(args.pts, pt), args.destdir, device=device)
    elif os.path.isfile(args.pts):
        h5_to_fullmerl(args.pts, args.destdir, device=device)
