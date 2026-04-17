import sys, os
utilFuncPath = 'functions'
if utilFuncPath not in sys.path:
    sys.path.insert(0, utilFuncPath)

import numpy as np
import scipy.io as sio

from merlFunctions import *
from coordinateFunctions import *
from brdfModel import *

brdfShape = (180, 90, 90)
brdfEntryNum = np.prod(brdfShape)
dataDir = 'data'
if not os.path.exists(dataDir):
    os.makedirs(dataDir)

# %% 1. Compute mask from MERL BRDF data
brdfDir = '../../brdf'
brdfList = sorted([f.split('.')[0] for f in os.listdir(brdfDir) if f.endswith('.binary') and 'a' <= f[0] <= 'z'])
brdfMask = np.ones((brdfEntryNum, ), dtype=bool)
for i, brdfname in enumerate(brdfList):
    brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname)).reshape((-1, 3))
    curMask = (np.sum(brdfRaw < 0, axis=1) == 0)  #True if and only if all values in RGB are non-negative
    brdfMask *= curMask

print np.sum(brdfMask)

# %% 2. Compute directions
lightDir = []
viewDir = []
for vId in range(brdfEntryNum):
    rusCoord = MERLToRusink(IDToMERL(vId))[0,:]  #Get rusink coordinate
    (v,i) = np.squeeze(RusinkToDirections(rusCoord[0],rusCoord[1],rusCoord[2])) #get view/light vectrors
    lightDir.append(i)
    viewDir.append(v)
lightDir = np.stack(lightDir, axis=0)
viewDir = np.stack(viewDir, axis=0)
directionMask = (lightDir[:, 2] > 0) * (viewDir[:, 2] > 0)

print np.sum(directionMask)

# %% 3. Compute mask
maskMap = brdfMask * directionMask
np.save('%s/maskMap.npy'%dataDir, maskMap)
sio.savemat('%s/directions.mat'%dataDir, {'L': lightDir[maskMap], 'V': viewDir[maskMap]})

# %% 4. Compute cosine map
minVal = 0.001
cosMap = lightDir[maskMap, 2] * viewDir[maskMap, 2]
cosMap = np.clip(cosMap, minVal, 1)
np.save('%s/cosMap.npy'%dataDir, cosMap)
sio.savemat('%s/cosMap.mat'%dataDir, {'cosMap': cosMap[:, np.newaxis]})

# %% 5. Generate volumnWeight (used in weightedSquare)
brdfValNum = np.sum(maskMap)
rusinkCoords = MERLToRusink(ValidIDToMERL(np.arange(brdfValNum), maskMap))
volumnWeight = np.sin(rusinkCoords[:, 2]) * np.sqrt(rusinkCoords[:, 1] * (np.cos(rusinkCoords[:, 2]) ** 2 + (np.sin(rusinkCoords[:, 2]) * np.cos(rusinkCoords[:, 0])) ** 2))
sio.savemat('%s/volumnWeight.mat'%dataDir, {'volumnWeight': volumnWeight[:, np.newaxis]})

# %% 6. Precompute MERL BRDFs
originalImages = np.zeros((250, 250, 3, 100))
for i, brdfname in enumerate(brdfList):
    brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
    brdf = brdfRaw.reshape((-1, 3))[maskMap]
    originalImages[:, :, :, i] = saveBrdfImage('original.png', brdf)
np.save('%s/originalImages.npy'%dataDir, originalImages)
