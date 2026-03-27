import sys
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
    wiz = torch.cos(theta_d) * torch.cos(theta_h) - \
          torch.sin(theta_d) * torch.cos(phi_d) * torch.sin(theta_h)
    rgb = brdf * torch.clamp(wiz, 0, 1)
    return rgb


def image_mse(model_output, gt):
    return {'img_loss': ((brdf_to_rgb(model_output['model_in'], model_output['model_out'])
                          - brdf_to_rgb(model_output['model_in'], gt['amps'])) ** 2).mean()}


def latent_loss(model_output):
    return torch.mean(model_output['latent_vec'] ** 2)


def hypo_weight_loss(model_output):
    weight_sum = 0
    total_weights = 0

    for weight in model_output['hypo_params'].values():
        weight_sum += torch.sum(weight ** 2)
        total_weights += weight.numel()

    return weight_sum * (1 / total_weights)


def image_hypernetwork_loss(kl, fw, model_output, gt):
    return {'img_loss': image_mse(model_output, gt)['img_loss'],
            'latent_loss': kl * latent_loss(model_output),
            'hypo_weight_loss': fw * hypo_weight_loss(model_output)}


def eval_epoch(model, train_dataloader, loss_fn, optim, epoch):
    epoch_loss = []
    individual_loss = []
    for step, (model_input, gt) in enumerate(train_dataloader):
        model.eval()
        model_input = {key: value.to(device) for key, value in model_input.items()}
        gt = {key: value.to(device) for key, value in gt.items()}

        model_output = model(model_input)
        losses = loss_fn(model_output, gt)

        train_loss = 0.
        for loss_name, loss in losses.items():
            single_loss = loss.mean()
            train_loss += single_loss
        individual_loss.append([loss.cpu().detach().numpy() for loss_name, loss in losses.items()])
        epoch_loss.append(train_loss.item())
    return np.mean(epoch_loss), np.stack(individual_loss).mean(axis=0)


# Epoch training
def train_epoch(model, train_dataloader, loss_fn, optim, epoch):
    epoch_loss = []
    individual_loss = []
    for step, (model_input, gt) in enumerate(train_dataloader):
        model.train()
        model_input = {key: value.to(device) for key, value in model_input.items()}

        gt = {key: value.to(device) for key, value in gt.items()}
        model_output = model(model_input)
        losses = loss_fn(model_output, gt)
        # print('step:', step, 'epoch:', epoch, 'bin_path:')

        train_loss = 0.
        for loss_name, loss in losses.items():
            single_loss = loss.mean()
            train_loss += single_loss
        individual_loss.append([loss.cpu().detach().numpy() for loss_name, loss in losses.items()])
        optim.zero_grad()
        train_loss.backward()

        if clip_grad:
            if isinstance(clip_grad, bool):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.)
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=clip_grad)
        optim.step()
        epoch_loss.append(train_loss.item())
    return np.mean(epoch_loss), np.stack(individual_loss).mean(axis=0)


def eval_model(model, dataloader, path_=None, name=''):
    model_inp = []
    model_out = []
    for step, (model_input, gt) in enumerate(dataloader):
        model.eval()
        model_input = {key: value.to(device) for key, value in model_input.items()}
        gt = {key: value.to(device) for key, value in gt.items()}
        model_output = model(model_input)
        model_out.append(model_output['model_out'].cpu().detach().numpy())
        model_inp.append(gt['amps'].cpu().numpy())
    y_true = np.concatenate(model_inp)
    y_true = y_true[:, :, 0]
    y_pred = np.concatenate(model_out)
    y_pred = y_pred[:, :, 0]
    mse = mean_squared_error(y_true, y_pred)
    return mse


######################################################################################

parser = argparse.ArgumentParser('')
parser.add_argument('--destdir', dest='destdir', type=str, required=True, help='output directory')
parser.add_argument('--binary', type=str, required=True, help='dataset path')
parser.add_argument('--dataset', choices=['MERL', 'EPFL'], default='MERL')
parser.add_argument('--kl_weight', type=float, default=0., help='latent loss weight')
parser.add_argument('--fw_weight', type=float, default=0., help='hypo loss weight')
parser.add_argument('--epochs', type=int, default=100, help='number of epochs')
parser.add_argument('--sparse_samples', type=int, default=4000, help='number of sparse samples for encoder')
parser.add_argument('--lr', type=float, default=5e-5, help='learning rate')
parser.add_argument('--keepon', action='store_true', help='continue training from loaded checkpoint')
parser.add_argument('--train_subset', type=int, default=0, help='number of materials to sample for training (0 = all)')
parser.add_argument('--train_seed', type=int, default=42, help='random seed for training material sampling')

args = parser.parse_args()
device = get_device()
print(device)

path_ = op.join(args.destdir, args.dataset)
create_directory(path_)
create_directory(op.join(path_, 'img'))

prev_args = None
prev_train_losses = None
prev_all_losses = None
prev_args_path = op.join(path_, 'args.txt')
if args.keepon and op.exists(prev_args_path):
    with open(prev_args_path, 'r') as f:
        prev_args = json.load(f)
    for key in ['kl_weight', 'fw_weight', 'sparse_samples', 'lr', 'train_subset', 'train_seed']:
        if key in prev_args:
            setattr(args, key, prev_args[key])
    if 'binary' in prev_args and prev_args['binary']:
        args.binary = prev_args['binary']
    if 'dataset' in prev_args and prev_args['dataset']:
        args.dataset = prev_args['dataset']
    if 'epochs' in prev_args and isinstance(prev_args['epochs'], int):
        prev_epochs = prev_args['epochs']
    else:
        prev_epochs = 0
else:
    prev_epochs = 0

train_loss_path = op.join(path_, 'train_loss.csv')
all_loss_path = op.join(path_, 'all_losses.csv')
completed_epochs = 0
if args.keepon and op.exists(train_loss_path):
    train_df = pd.read_csv(train_loss_path)
    if train_df.shape[1] > 1:
        prev_train_losses = train_df.iloc[:, -1].tolist()
    else:
        prev_train_losses = train_df.iloc[:, 0].tolist()
    completed_epochs = max(len(prev_train_losses) - 1, 0)
if args.keepon and op.exists(all_loss_path):
    all_df = pd.read_csv(all_loss_path)
    if all_df.shape[1] > 1:
        prev_all_losses = all_df.drop(columns=[all_df.columns[0]]).values.tolist()
    else:
        prev_all_losses = all_df.values.tolist()

if args.keepon:
    base_epochs = max(prev_epochs, completed_epochs)
    args.epochs = base_epochs + args.epochs

with open(op.join(path_, 'args.txt'), 'w') as f:
    json.dump(args.__dict__, f, indent=2)

#### Set hyperparameters
kl_weight = args.kl_weight
fw_weight = args.fw_weight

loss_fn = partial(image_hypernetwork_loss, kl_weight, fw_weight)

clip_grad = True
lr = args.lr
epochs = args.epochs
binary = args.binary

if args.dataset == 'MERL':
    subset_list_path = op.join(path_, 'train_subset.json')
    subset_files = None
    if args.train_subset and args.train_subset > 0:
        if args.keepon and op.exists(subset_list_path):
            try:
                with open(subset_list_path, 'r') as f:
                    subset_files = json.load(f)
            except Exception:
                subset_files = None
            if subset_files:
                subset_files = [p for p in subset_files if op.exists(p)]
        if not subset_files:
            all_files = sorted(glob.glob(op.join(binary, "*.binary")))
            if len(all_files) > args.train_subset:
                rng = np.random.default_rng(args.train_seed)
                idx = rng.permutation(len(all_files))[:args.train_subset]
                subset_files = [all_files[i] for i in idx]
            else:
                subset_files = all_files
            with open(subset_list_path, 'w') as f:
                json.dump(subset_files, f, indent=2)
    max_materials = None if subset_files else (args.train_subset if args.train_subset and args.train_subset > 0 else None)
    dataset = MerlDataset(binary, sparse_samples=args.sparse_samples, max_materials=max_materials, seed=args.train_seed, file_list=subset_files)
    num_workers = 0 if os.name == 'nt' else 6
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1, num_workers=num_workers)

elif args.dataset == 'EPFL':
    dataset = EPFL(binary, sparse_samples=args.sparse_samples)
    num_workers = 0 if os.name == 'nt' else 6
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1, num_workers=num_workers)


#### Train model
start_time = time.time()
if args.keepon:
    model = torch.load(op.join(path_, 'checkpoint.pt'))
else:
    model = HyperBRDF(in_features=6, out_features=3).to(device)
train_losses = prev_train_losses if prev_train_losses is not None else []
all_losses = prev_all_losses if prev_all_losses is not None else []
optim = torch.optim.Adam(lr=lr, params=model.parameters())
start_epoch = completed_epochs if args.keepon else 0
if not args.keepon:
    epoch_loss, individual_losses = eval_epoch(model, dataloader, loss_fn, optim, 0)
    train_losses.append(epoch_loss)
    all_losses.append(individual_losses)
    print('init', epoch_loss, all_losses)

for epoch in range(start_epoch, epochs):
    epoch_loss, individual_losses = train_epoch(model, dataloader, loss_fn, optim, epoch)
    train_losses.append(epoch_loss)
    all_losses.append(individual_losses)
    print(epoch, epoch_loss, all_losses)

# Save training losses, and trained model
pd.DataFrame(train_losses).to_csv(op.join(path_, 'train_loss.csv'))
pd.DataFrame(all_losses).to_csv(op.join(path_, 'all_losses.csv'))
torch.save(model, op.join(path_, 'checkpoint.pt'))
#### Finish training
