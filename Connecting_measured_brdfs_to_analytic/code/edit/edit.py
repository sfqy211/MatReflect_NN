import sys, os
utilFuncPath = '../_util/functions'
utilDataPath = '../_util/data'
if utilFuncPath not in sys.path:
    sys.path.insert(0, utilFuncPath)

import numpy as np
import scipy.io as sio
from shutil import copyfile
import matplotlib.pyplot as plt

from merlFunctions import *
from coordinateFunctions import *
from hsi import *

maskMap = np.load('%s/maskMap.npy'%utilDataPath)   #Indicating valid regions in MERL BRDFs
brdfValNum = np.sum(maskMap)

brdfDir = '../../brdf'
brdfList = sorted([f.split('.')[0] for f in os.listdir(brdfDir) if f.endswith('.binary') and 'a' <= f[0] <= 'z'])
writeBrdfDir = 'brdf'
if not os.path.exists(writeBrdfDir):
    os.makedirs(writeBrdfDir)

# %% 0. utility
brdfDataDir = '../diffspec/data'
metric = 'log2'

cosMap = sio.loadmat('%s/cosMap.mat'%utilDataPath)['cosMap']
diffAll = np.load('%s/diffAll_%s.npy'%(brdfDataDir, metric))
specAll = np.load('%s/specAll_%s.npy'%(brdfDataDir, metric))
colorAll = np.load('%s/colorAll_image2.npy'%brdfDataDir)

# %% 1a. Edit diffuse color (teaser)
index = brdfList.index('violet-acrylic')
diffuseColor = colorAll[:1, :, index]
I, S, H = RGBtoHSI(diffuseColor)
step = 45
for i in range(5):
    newHue = H[0] + step * (i - 2) / 180. * np.pi
    if newHue < 0:
        newHue += 2 * np.pi
    elif newHue >= 2 * np.pi:
        newHue -= 2 * np.pi
    newDiffuseColor = HSItoRGB(I, S, np.array([newHue]))
    writeBrdf[maskMap] = diffAll[:, index:index+1].dot(newDiffuseColor) + specAll[:, index:index+1].dot(colorAll[1:, :, index])
    saveMERLBRDF('%s/diffuseHue_%s.binary'%(writeBrdfDir, i), writeBrdf)

# %% 1b. Edit diffuse color (image)
index = brdfList.index('green-plastic')
diffuseColor = colorAll[:1, :, index]
I, S, H = RGBtoHSI(diffuseColor)
hue_step = 30
saturation_step = 0.19
for i in range(5):
    for j in range(5):
        if i + j > 4:
            continue
        newHue = H[0] + hue_step * i / 180. * np.pi
        if newHue < 0:
            newHue += 2 * np.pi
        elif newHue >= 2 * np.pi:
            newHue -= 2 * np.pi
        newSaturation = S[0] - saturation_step * j
        newDiffuseColor = HSItoRGB(I, np.array([newSaturation]), np.array([newHue]))
        writeBrdf[maskMap] = diffAll[:, index:index+1].dot(newDiffuseColor) + specAll[:, index:index+1].dot(colorAll[1:, :, index])
        saveMERLBRDF('%s/%s_Hue%s_Saturation%s.binary'%(writeBrdfDir, brdfList[index], i, j), writeBrdf)

# %% 2. Edit specular color
index = brdfList.index('blue-metallic-paint1')
specularColor = colorAll[1:, :, index]
I, S, H = RGBtoHSI(specularColor)
step = 36
for i in range(10):
    newHue = H[0] - step * i / 180. * np.pi
    if newHue < 0:
        newHue += 2 * np.pi
    elif newHue >= 2 * np.pi:
        newHue -= 2 * np.pi
    newSpecularColor = HSItoRGB(I, S, np.array([newHue]))
    writeBrdf[maskMap] = diffAll[:, index:index+1].dot(colorAll[0:1, :, index]) + specAll[:, index:index+1].dot(newSpecularColor)
    saveMERLBRDF('%s/%s_%s.binary'%(writeBrdfDir, brdfList[index], i), writeBrdf)

# %% 3. Highlight Removal
index = brdfList.index('gold-metallic-paint2')
step = 0.2
for i in range(6):
    writeBrdf[maskMap] = diffAll[:, index:index+1].dot(colorAll[0:1, :, index]) + (i * step + (1. - 5 * step)) * specAll[:, index:index+1].dot(colorAll[1:, :, index])
    saveMERLBRDF('%s/%s_%s.binary'%(writeBrdfDir, brdfList[index], i), writeBrdf)


# %% 4. Mix reflectances
index1 = brdfList.index('red-phenolic')
index2 = brdfList.index('two-layer-silver')

copyfile('%s/%s.binary'%(brdfDir, brdfList[index1]), '%s/mix_original1.binary'%(writeBrdfDir))
copyfile('%s/%s.binary'%(brdfDir, brdfList[index2]), '%s/mix_original2.binary'%(writeBrdfDir))
writeBrdf[maskMap] = diffAll[:, index1:index1+1].dot(colorAll[0:1, :, index1]) + specAll[:, index2:index2+1].dot(colorAll[1:, :, index2])
saveMERLBRDF('%s/mix_mix1.binary'%(writeBrdfDir), writeBrdf)
writeBrdf[maskMap] = diffAll[:, index2:index2+1].dot(colorAll[0:1, :, index2]) + specAll[:, index1:index1+1].dot(colorAll[1:, :, index1])
saveMERLBRDF('%s/mix_mix2.binary'%(writeBrdfDir), writeBrdf)
