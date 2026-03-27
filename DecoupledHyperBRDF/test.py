import time
import argparse
import os

from data_processing import *
from utils.common import get_device

parser = argparse.ArgumentParser()
parser.add_argument('--model')
parser.add_argument('--binary')
parser.add_argument('--destdir')
parser.add_argument('--dataset', choices=['MERL', 'EPFL'], default='MERL')

args = parser.parse_args()
device = get_device()
print(f"Using device: {device}")


def eval_model(model, dataloader, path_=None, name=''):
    for step, (model_input, gt) in enumerate(dataloader):
        start = time.time()

        model.eval()
        model_input = {key: value.to(device) for key, value in model_input.items()}
        
        # Use os.path to safely extract filename
        full_path = dataloader.dataset.fnames[model_input['idx']]
        mat_name = os.path.splitext(os.path.basename(full_path))[0]
        
        model_output = model(model_input)
        
        # Ensure output directory exists
        if not os.path.exists(args.destdir):
            os.makedirs(args.destdir)
            
        save_path = os.path.join(args.destdir, mat_name + '.pt')
        torch.save(model_output['hypo_params'], save_path)
        end = time.time()
        print(end - start)
    return -1


if args.dataset == 'MERL':
    #4000采样给fullbin
    dataset = MerlDataset(args.binary, sparse_samples=4000)
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1)

elif args.dataset == 'EPFL':
    dataset = EPFL(args.binary, sparse_samples=4000)
    dataloader = DataLoader(dataset, shuffle=True, batch_size=1)


model = torch.load(args.model, map_location=device)
model.to(device)
eval_model(model, dataloader)
