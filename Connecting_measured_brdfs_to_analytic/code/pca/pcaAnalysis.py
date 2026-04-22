import sys, os
utilFuncPath = '../_util/functions'
utilDataPath = '../_util/data'
if utilFuncPath not in sys.path:
    sys.path.insert(0, utilFuncPath)

import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from scipy.linalg import svd
from sklearn.decomposition import PCA
from numpy.linalg import inv

from merlFunctions import *

maskMap = np.load(utilDataPath + '/maskMap.npy')   #Indicating valid regions in MERL BRDFs
brdfValNum = np.sum(maskMap)

brdfDir = '../../brdf'
brdfList = sorted([f.split('.')[0] for f in os.listdir(brdfDir) if f.endswith('.binary') and 'a' <= f[0] <= 'z'])

writeDataDir = 'data'
if not os.path.exists(writeDataDir):
    os.makedirs(writeDataDir)
writeBrdfImageDir = 'brdfimage'
if not os.path.exists(writeBrdfImageDir):
    os.makedirs(writeBrdfImageDir)

# %% 0. utility
brdfDataDir = '../diffspec/data'
metric = 'log2'

cosMap = sio.loadmat('%s/cosMap.mat'%utilDataPath)['cosMap']
diffAll = np.load('%s/diffAll_%s.npy'%(brdfDataDir, metric))
specAll = np.load('%s/specAll_%s.npy'%(brdfDataDir, metric))
colorAll = np.load('%s/colorAll_image2.npy'%brdfDataDir)
colorAllBrdf = np.load('%s/colorAll_brdf2.npy'%brdfDataDir)
originalImages = np.load('%s/originalImages.npy'%utilDataPath)

def MapBRDF(brdfData):
    return np.log(brdfData+0.001) #Our mapping
def UnmapBRDF(mappedData):
    return np.exp(mappedData)-0.001

# %% 1. Pca Analysis on diffuse
U, s, Vt = svd(diffAll, full_matrices=False, check_finite=False)
sign = np.sign(U[0, 0]) #Try to make the first coefficient positive
diffPcaComponents = sign * U[:, :3] * s[:3]
diffPcaReconCoeff = sign * Vt[:3, :]
np.save('%s/diffPcaReconCoeff.npy'%writeDataDir, diffPcaReconCoeff)
np.save('%s/diffPcaComponents.npy'%writeDataDir, diffPcaComponents)
diffPcaRecon1 = diffPcaComponents[:, :1].dot(diffPcaReconCoeff[:1, :])
diffPcaRecon2 = diffPcaComponents[:, :2].dot(diffPcaReconCoeff[:2, :])
diffPcaRecon3 = diffPcaComponents[:, :3].dot(diffPcaReconCoeff[:3, :])

# %% 2. Pca Analysis on specular
specMap = MapBRDF(specAll * cosMap)
specMapMean = np.mean(specMap, axis=1, keepdims=True)
np.save('%s/specMapMean.npy'%writeDataDir, specMapMean)

specMapPca = PCA(n_components=20).fit((specMap - specMapMean).T)
print specMapPca.explained_variance_ratio_
Q = specMapPca.components_.T
specMapPcaReconCoeff = inv(Q.T.dot(Q)).dot(Q.T.dot(specMap - specMapMean))
specMapPcaRecon2 = UnmapBRDF(Q[:, :2].dot(specMapPcaReconCoeff[:2, :]) + specMapMean) / cosMap
specMapPcaRecon3 = UnmapBRDF(Q[:, :3].dot(specMapPcaReconCoeff[:3, :]) + specMapMean) / cosMap
specMapPcaRecon5 = UnmapBRDF(Q[:, :5].dot(specMapPcaReconCoeff[:5, :]) + specMapMean) / cosMap
specMapPcaRecon10 = UnmapBRDF(Q[:, :10].dot(specMapPcaReconCoeff[:10, :]) + specMapMean) / cosMap
np.save('%s/specMapPcaReconCoeff.npy'%writeDataDir, specMapPcaReconCoeff)
np.save('%s/specMapPcaComponents.npy'%writeDataDir, Q)

for i, brdfname in enumerate(brdfList):
    saveBrdfImage('%s/%s_spec.png'%(writeBrdfImageDir, brdfname), specAll[:, i:i+1].dot(colorAll[1:, :, i]))

    saveBrdfImage('%s/%s_spec2.png'%(writeBrdfImageDir, brdfname), specMapPcaRecon2[:, i:i+1].dot(colorAll[1:, :, i]))
    saveBrdfImage('%s/%s_spec3.png'%(writeBrdfImageDir, brdfname), specMapPcaRecon3[:, i:i+1].dot(colorAll[1:, :, i]))
    saveBrdfImage('%s/%s_spec5.png'%(writeBrdfImageDir, brdfname), specMapPcaRecon5[:, i:i+1].dot(colorAll[1:, :, i]))
    saveBrdfImage('%s/%s_spec10.png'%(writeBrdfImageDir, brdfname), specMapPcaRecon10[:, i:i+1].dot(colorAll[1:, :, i]))

# %% 3. Combine diffuse and specular reconstruction
diffPcaReconCoeff = np.load('%s/diffPcaReconCoeff.npy'%writeDataDir)
diffPcaComponents = np.load('%s/diffPcaComponents.npy'%writeDataDir)

specMapMean = np.load('%s/specMapMean.npy'%writeDataDir)
specMapPcaReconCoeff = np.load('%s/specMapPcaReconCoeff.npy'%writeDataDir)
specMapPcaComponents = np.load('%s/specMapPcaComponents.npy'%writeDataDir)

diffPcaRecon1 = diffPcaComponents[:, :1].dot(diffPcaReconCoeff[:1, :])
specMapPcaRecon3 = UnmapBRDF(specMapPcaComponents[:, :3].dot(specMapPcaReconCoeff[:3, :]) + specMapMean) / cosMap
specMapPcaRecon5 = UnmapBRDF(specMapPcaComponents[:, :5].dot(specMapPcaReconCoeff[:5, :]) + specMapMean) / cosMap

# Optional export example from the paper code. Disabled to keep the main PCA
# pipeline runnable without requiring an extra scratch MERL buffer here.
# index = brdfList.index('specular-orange-phenolic')
# writeBrdf[maskMap] = diffPcaRecon1[:, index:index+1].dot(colorAll[:1, :, index]) + specMapPcaRecon3[:, index:index+1].dot(colorAll[1:, :, index])
# saveMERLBRDF('%s_diff1spec3.binary'%brdfList[index], writeBrdf)

for i, brdfname in enumerate(brdfList):
    brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
    brdf = brdfRaw.reshape((-1, 3))[maskMap]
    saveBrdfImage('%s/%s.png'%(writeBrdfImageDir, brdfname), brdf)

    saveBrdfImage('%s/%s_diff.png'%(writeBrdfImageDir, brdfname), diffPcaRecon1[:, i:i+1].dot(colorAll[:1, :, i]))
    saveBrdfImage('%s/%s_combine_diff1spec3.png'%(writeBrdfImageDir, brdfname), diffPcaRecon1[:, i:i+1].dot(colorAll[:1, :, i]) + specMapPcaRecon3[:, i:i+1].dot(colorAll[1:, :, i]))
    saveBrdfImage('%s/%s_combine_diff1spec5.png'%(writeBrdfImageDir, brdfname), diffPcaRecon1[:, i:i+1].dot(colorAll[:1, :, i]) + specMapPcaRecon5[:, i:i+1].dot(colorAll[1:, :, i]))

# %% 4. Compute ours error
diffPcaReconCoeff = np.load('%s/diffPcaReconCoeff.npy'%writeDataDir)
diffPcaComponents = np.load('%s/diffPcaComponents.npy'%writeDataDir)

specMapMean = np.load('%s/specMapMean.npy'%writeDataDir)
specMapPcaReconCoeff = np.load('%s/specMapPcaReconCoeff.npy'%writeDataDir)
specMapPcaComponents = np.load('%s/specMapPcaComponents.npy'%writeDataDir)

testSpecPcNum = 20
oursPsnrVals = np.zeros((len(brdfList), testSpecPcNum))
for specPcNum in range(testSpecPcNum):
    diffPcaRecon = diffPcaComponents[:, :1].dot(diffPcaReconCoeff[:1, :])
    specMapPcaRecon = UnmapBRDF(specMapPcaComponents[:, :specPcNum+1].dot(specMapPcaReconCoeff[:specPcNum+1, :]) + specMapMean) / cosMap

    for i, brdfname in enumerate(brdfList):
        brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
        brdf = brdfRaw.reshape((-1, 3))[maskMap]

        brdfPcaRecon = diffPcaRecon[:, i:i+1].dot(colorAll[:1, :, i]) + specMapPcaRecon[:, i:i+1].dot(colorAll[1:, :, i])
        reconImage = saveBrdfImage('recon.png', brdfPcaRecon)
        oursPsnrVals[i, specPcNum] = psnr(originalImages[:, :, :, i], reconImage)
    print specPcNum, oursPsnrVals[:, specPcNum].mean()

np.save('%s/oursPsnrVals.npy'%writeDataDir, oursPsnrVals)
print oursPsnrVals.mean(axis=0)

# %% 4b. Compute ours diffuse error
diffPcaReconCoeff = np.load('%s/diffPcaReconCoeff.npy'%writeDataDir)
diffPcaComponents = np.load('%s/diffPcaComponents.npy'%writeDataDir)

oursPsnrVals_Diff = np.zeros((len(brdfList), 1))

diffPcaRecon = diffPcaComponents[:, :1].dot(diffPcaReconCoeff[:1, :])
for i, brdfname in enumerate(brdfList):
    brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
    brdf = brdfRaw.reshape((-1, 3))[maskMap]

    brdfPcaRecon = diffPcaRecon[:, i:i+1].dot(colorAll[:1, :, i])
    reconImage = saveBrdfImage('recon.png', brdfPcaRecon)
    oursPsnrVals_Diff[i, 0] = psnr(originalImages[:, :, :, i], reconImage)

np.save('%s/oursPsnrVals_Diff.npy'%writeDataDir, oursPsnrVals_Diff)
print oursPsnrVals_Diff.mean(axis=0)


# %% 5. [Compare] Jannik's method
# Skip if required files don't exist
if os.path.exists('%s/maskMap_old.npy'%utilDataPath) and os.path.exists('%s/cosMap_old.npy'%utilDataPath):
    maskMap_old = np.load('%s/maskMap_old.npy'%utilDataPath)
    cosMap_old = np.load('%s/cosMap_old.npy'%utilDataPath)

    brdfAll = np.zeros((maskMap_old.sum(), 3 * len(brdfList)))
    for i, brdfname in enumerate(brdfList):
        brdfAll[:, 3*i:3*(i+1)] = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname)).reshape((-1, 3))[maskMap_old]

    brdfMap = MapBRDF(brdfAll * cosMap_old)
    brdfMapMean = np.mean(brdfMap, axis=1, keepdims=True)
    np.save('%s/NielsenMapMean.npy'%writeDataDir, brdfMapMean)

    brdfMapPca = PCA(n_components=10).fit((brdfMap - brdfMapMean).T)
    print brdfMapPca.explained_variance_ratio_
    Q = brdfMapPca.components_.T
    brdfMapPcaReconCoeff = inv(Q.T.dot(Q)).dot(Q.T.dot(brdfMap - brdfMapMean))
    np.save('%s/NielsenMapPcaReconCoeff.npy'%writeDataDir, brdfMapPcaReconCoeff)
    np.save('%s/NielsenMapPcaComponents.npy'%writeDataDir, Q)

    testPcNum = 10
    NielsenPsnrVals = np.zeros((len(brdfList), testPcNum))
    writeBrdf = np.zeros((len(maskMap_old), 3))
    for pcNum in range(testPcNum):
        brdfPcaRecon = UnmapBRDF(Q[:, :pcNum+1].dot(brdfMapPcaReconCoeff[:pcNum+1, :]) + brdfMapMean) / cosMap_old
        for i, brdfname in enumerate(brdfList):
            writeBrdf[maskMap_old] = brdfPcaRecon[:, 3*i:3*(i+1)]
            reconImage = saveBrdfImage('recon.png',  writeBrdf[maskMap, :])
            NielsenPsnrVals[i, pcNum] = psnr(originalImages[:, :, :, i], reconImage)

    np.save('%s/NielsenPsnrVals.npy'%writeDataDir, NielsenPsnrVals)
    NielsenPsnrVals = np.load('%s/NielsenPsnrVals.npy'%writeDataDir)
    print NielsenPsnrVals.mean(axis=0)
else:
    print "Skipping Nielsen comparison (maskMap_old.npy or cosMap_old.npy not found)"
