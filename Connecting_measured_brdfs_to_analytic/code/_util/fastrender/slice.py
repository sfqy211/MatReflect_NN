import numpy as np
from transform import *
import scipy.io as sio

# R = load_sparse_csr('weights/brdfWeightR.npz')
# G = load_sparse_csr('weights/brdfWeightG.npz')
# B = load_sparse_csr('weights/brdfWeightB.npz')
# mean = (R + G + B) / 3.
# save_sparse_csr('weights/brdfWeightMean.npz', mean)

# sliceMid = np.concatenate([np.arange(10, 240) * 250 + x for x in range(115, 130)])
sliceMid = np.r_[np.arange(10, 240) * 250 + 121, np.arange(10, 240) + 121 * 250]
mean = load_sparse_csr('weights/brdfWeightMean.npz')
sio.savemat('weights/renderSlice.mat', {'renderSlice': mean[sliceMid, :]})
