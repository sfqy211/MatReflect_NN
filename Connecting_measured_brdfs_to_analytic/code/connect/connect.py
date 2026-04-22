import sys, os
utilFuncPath = '../_util/functions'
utilDataPath = '../_util/data'
if utilFuncPath not in sys.path:
    sys.path.insert(0, utilFuncPath)

import timeit
import numpy as np
import scipy.io as sio
import scipy.spatial as sp
from shutil import copyfile
import matplotlib.pyplot as plt
from numpy.linalg import inv
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors

from merlFunctions import *
from brdfModel import lambertian, GGX

import matlab.engine
eng = matlab.engine.start_matlab()
eng.addpath(utilFuncPath)
eng.addpath(utilDataPath)
eng.addpath(renderWeightDir)
# eng.exit()

maskMap = np.load(utilDataPath + '/maskMap.npy')   #Indicating valid regions in MERL BRDFs
brdfValNum = np.sum(maskMap)

brdfDir = '../../brdf'
brdfList = sorted([f.split('.')[0] for f in os.listdir(brdfDir) if f.endswith('.binary') and 'a' <= f[0] <= 'z'])

writeDataDir = 'data'
if not os.path.exists(writeDataDir):
    os.makedirs(writeDataDir)
pcaDataDir = '../pca/data'
pcaImageDir = '../pca/brdfimage'
testBrdfImageDir = 'testbrdfimage'
if not os.path.exists(testBrdfImageDir):
    os.makedirs(testBrdfImageDir)
brdfImageDir = 'brdfimage'
if not os.path.exists(brdfImageDir):
    os.makedirs(brdfImageDir)

# %% 0. utility
pcNum = 3
cosMap = sio.loadmat('%s/cosMap.mat'%utilDataPath)['cosMap']

brdfDataDir = '../diffspec/data'
specAll = np.load('%s/specAll_log2.npy'%(brdfDataDir))
colorAll = np.load('%s/colorAll_image2.npy'%brdfDataDir)
originalImages = np.load('%s/originalImages.npy'%utilDataPath)

def MapBRDF(brdfData):
    return np.log(brdfData+0.001) #Our mapping
def UnmapBRDF(mappedData):
    return np.exp(mappedData)-0.001

def l2norm(a, b):
    return np.sum((a-b) ** 2, axis=0)
def projection(brdf, Q, mean):
    return Q.T.dot(MapBRDF(brdf * cosMap) - mean)
def measuredBrdf(pc, Q, mean):
    return (UnmapBRDF(Q.dot(pc) + mean) / cosMap).clip(min=0)

# %% 1. Construct data
trainScaleLine = np.exp(np.linspace(np.log(0.6), np.log(0.01), num=4, endpoint=False))
trainRoughLine = np.exp(np.linspace(np.log(0.005), np.log(0.8), num=8))
trainIorLine = np.exp(np.linspace(np.log(1.3), np.log(3.0), num=4))
trainScaleGrid, trainRoughGrid, trainIorGrid = np.meshgrid(trainScaleLine, trainRoughLine, trainIorLine, indexing='ij')
trainScaleSample = trainScaleGrid.flatten()[np.newaxis, :]
trainRoughSample = trainRoughGrid.flatten()[np.newaxis, :]
trainIorSample = trainIorGrid.flatten()[np.newaxis, :]
trainAnalytic = GGX(trainScaleSample, trainRoughSample, trainIorSample)

# %% 2. Train analytic and measured together
jointSpec = np.concatenate([specAll, trainAnalytic], axis=1)
jointMap = MapBRDF(jointSpec * cosMap)
jointMapMean = np.mean(jointMap, axis=1, keepdims=True)
np.save('%s/jointMapMean.npy'%writeDataDir, jointMapMean)

jointMapPca = PCA(n_components=10).fit((jointMap - jointMapMean).T)
print jointMapPca.explained_variance_ratio_
jointMapPcaComponents = jointMapPca.components_.T
np.save('%s/jointMapPcaComponents.npy'%writeDataDir, jointMapPcaComponents)
jointMapPcaReconCoeff = jointMapPcaComponents.T.dot(jointMap - jointMapMean)
np.save('%s/jointMapPcaReconCoeff.npy'%writeDataDir, jointMapPcaReconCoeff)

# %% 2b. Train analytic only
analyticMap = MapBRDF(trainAnalytic * cosMap)
analyticMapMean = np.mean(analyticMap, axis=1, keepdims=True)
np.save('%s/analyticMapMean.npy'%writeDataDir, analyticMapMean)

analyticMapPca = PCA(n_components=10).fit((analyticMap - analyticMapMean).T)
print analyticMapPca.explained_variance_ratio_
analyticMapPcaComponents = analyticMapPca.components_.T
analyticMapPcaReconCoeff = analyticMapPcaComponents.T.dot(analyticMap - analyticMapMean)
np.save('%s/analyticMapPcaComponents.npy'%writeDataDir, analyticMapPcaComponents)
np.save('%s/analyticMapPcaReconCoeff.npy'%writeDataDir, analyticMapPcaReconCoeff)

# %% 2c. Test principal components
specMapMean = np.load('%s/specMapMean.npy'%pcaDataDir)
specMapPcaReconCoeff = np.load('%s/specMapPcaReconCoeff.npy'%pcaDataDir)
specMapPcaComponents = np.load('%s/specMapPcaComponents.npy'%pcaDataDir)

jointMapMean = np.load('%s/jointMapMean.npy'%writeDataDir)
jointMapPcaReconCoeff = np.load('%s/jointMapPcaReconCoeff.npy'%writeDataDir)
jointMapPcaComponents = np.load('%s/jointMapPcaComponents.npy'%writeDataDir)

analyticMapMean = np.load('%s/analyticMapMean.npy'%writeDataDir)
analyticMapPcaReconCoeff = np.load('%s/analyticMapPcaReconCoeff.npy'%writeDataDir)
analyticMapPcaComponents = np.load('%s/analyticMapPcaComponents.npy'%writeDataDir)

# Analytic
testAnalytic = GGX(np.array([[0.4] * 10]), np.array([np.exp(np.linspace(np.log(0.008), np.log(0.2), num=10))]), np.array([[2.0] * 10]))
for i in range(testAnalytic.shape[1]):
    saveBrdfImage('%s/%s.png'%(testBrdfImageDir, i), testAnalytic[:, i])

testAnalyticMap = MapBRDF(testAnalytic * cosMap) - specMapMean
testAnalyticCoeffs = inv(specMapPcaComponents.T.dot(specMapPcaComponents)).dot(specMapPcaComponents.T).dot(testAnalyticMap)
testAnalyticRecon3 = UnmapBRDF(specMapPcaComponents[:, :3].dot(testAnalyticCoeffs[:3, :]) + specMapMean) / cosMap
for i in range(testAnalytic.shape[1]):
    saveBrdfImage('%s/%s_spec3.png'%(testBrdfImageDir, i), testAnalyticRecon3[:, i])

testAnalyticMap = MapBRDF(testAnalytic * cosMap) - jointMapMean
testAnalyticCoeffs = inv(jointMapPcaComponents.T.dot(jointMapPcaComponents)).dot(jointMapPcaComponents.T).dot(testAnalyticMap)
testAnalyticRecon3 = UnmapBRDF(jointMapPcaComponents[:, :3].dot(testAnalyticCoeffs[:3, :]) + jointMapMean) / cosMap
for i in range(testAnalytic.shape[1]):
    saveBrdfImage('%s/%s_joint3.png'%(testBrdfImageDir, i), testAnalyticRecon3[:, i])

testAnalyticMap = MapBRDF(testAnalytic * cosMap) - analyticMapMean
testAnalyticCoeffs = inv(analyticMapPcaComponents.T.dot(analyticMapPcaComponents)).dot(analyticMapPcaComponents.T).dot(testAnalyticMap)
testAnalyticRecon3 = UnmapBRDF(analyticMapPcaComponents[:, :3].dot(testAnalyticCoeffs[:3, :]) + analyticMapMean) / cosMap
for i in range(testAnalytic.shape[1]):
    saveBrdfImage('%s/%s_analytic3.png'%(testBrdfImageDir, i), testAnalyticRecon3[:, i])

# Measured
testMeasuredRecon3 = UnmapBRDF(specMapPcaComponents[:, :3].dot(specMapPcaReconCoeff[:3, :]) + specMapMean) / cosMap
for i, brdfname in enumerate(brdfList):
    saveBrdfImage('%s/%s_spec.png'%(testBrdfImageDir, brdfname), specAll[:, i:i+1].dot(colorAll[1:, :, i]))
    saveBrdfImage('%s/%s_spec3.png'%(testBrdfImageDir, brdfname), testMeasuredRecon3[:, i:i+1].dot(colorAll[1:, :, i]))
testMeasuredRecon3 = UnmapBRDF(jointMapPcaComponents[:, :3].dot(jointMapPcaReconCoeff[:3, :]) + jointMapMean) / cosMap
for i, brdfname in enumerate(brdfList):
    saveBrdfImage('%s/%s_joint3.png'%(testBrdfImageDir, brdfname), testMeasuredRecon3[:, i:i+1].dot(colorAll[1:, :, i]))
testMeasuredMap = MapBRDF(specAll * cosMap) - analyticMapMean
testMeasuredCoeffs = inv(analyticMapPcaComponents.T.dot(analyticMapPcaComponents)).dot(analyticMapPcaComponents.T).dot(testMeasuredMap)
testMeasuredRecon3 = UnmapBRDF(analyticMapPcaComponents[:, :3].dot(testMeasuredCoeffs[:3, :]) + analyticMapMean) / cosMap
for i, brdfname in enumerate(brdfList):
    saveBrdfImage('%s/%s_analytic3.png'%(testBrdfImageDir, brdfname), testMeasuredRecon3[:, i:i+1].dot(colorAll[1:, :, i]))


# %% 3a. Test on analytic
jointMapMean = np.load('%s/jointMapMean.npy'%writeDataDir)
Q = np.load('%s/jointMapPcaComponents.npy'%writeDataDir)

testScaleLine = np.exp(np.linspace(np.log(0.01), np.log(0.6), num=20))
testRoughLine = np.exp(np.linspace(np.log(0.005), np.log(0.8), num=40))
testIorLine = np.exp(np.linspace(np.log(1.3), np.log(3.0), num=20))
testScaleGrid, testRoughGrid, testIorGrid = np.meshgrid(testScaleLine, testRoughLine, testIorLine, indexing='ij')
testScaleSample = testScaleGrid.flatten()[np.newaxis, :]
testRoughSample = testRoughGrid.flatten()[np.newaxis, :]
testIorSample = testIorGrid.flatten()[np.newaxis, :]
testAnalyticParams = np.concatenate([testScaleSample, testRoughSample, testIorSample], axis=0)
np.save('%s/testAnalyticParams.npy'%writeDataDir, testAnalyticParams)

step = 500
testAnalyticCoeffs = np.zeros((10, testAnalyticParams.shape[1]))
testAnalyticErrors = np.zeros((testAnalyticParams.shape[1], ))
for i in range(testAnalyticParams.shape[1] / step):
    testAnalytic = GGX(testAnalyticParams[0:1, step*i:step*(i+1)], testAnalyticParams[1:2, step*i:step*(i+1)], testAnalyticParams[2:, step*i:step*(i+1)])
    testAnalyticMap = MapBRDF(testAnalytic * cosMap) - jointMapMean
    testAnalyticCoeffs[:, step*i:step*(i+1)] = Q.T.dot(testAnalyticMap)
    testAnalyticErrors[step*i:step*(i+1)] = l2norm(testAnalyticMap, Q.dot(testAnalyticCoeffs[:, step*i:step*(i+1)]))
    print i, '/', testAnalyticParams.shape[1] / step

np.save('%s/testAnalyticCoeffs.npy'%writeDataDir, testAnalyticCoeffs)
np.save('%s/testAnalyticErrors.npy'%writeDataDir, testAnalyticErrors)

# %% 3b. convex hulls
clusterNum = 12
kmeans = KMeans(n_clusters=clusterNum).fit(testAnalyticCoeffs.T)
convexHullCenters = kmeans.cluster_centers_.T
distToCenter = np.sum((testAnalyticCoeffs[:, :, np.newaxis] - convexHullCenters[:, np.newaxis, :]) ** 2, axis=0)
distToCenterMin = np.min(distToCenter, axis=1)


# %% 4a. Prepare diffuse data
diffPcaComponents = np.load('%s/diffPcaComponents.npy'%pcaDataDir)[:, :1]
diffPcaReconCoeff = np.load('%s/diffPcaReconCoeff.npy'%pcaDataDir)[:1, :]

diffSlope = np.pi * diffPcaComponents.T.dot(diffPcaComponents)[0, 0] / (diffPcaComponents).sum()

# %% 4b. Prepare specular data
jointMapMean = np.load('%s/jointMapMean.npy'%writeDataDir)
jointMapPcaComponents = np.load('%s/jointMapPcaComponents.npy'%writeDataDir)[:, :pcNum]
jointMapPcaReconCoeff = np.load('%s/jointMapPcaReconCoeff.npy'%writeDataDir)[:pcNum, :len(brdfList)]

testAnalyticParams = np.load('%s/testAnalyticParams.npy'%writeDataDir)
testAnalyticCoeffs = np.load('%s/testAnalyticCoeffs.npy'%writeDataDir)[:pcNum, :]
testAnalyticErrors = np.load('%s/testAnalyticErrors.npy'%writeDataDir)

nearNeighborFinder = NearestNeighbors(n_neighbors=1)#, metric='mahalanobis', metric_params={'VI': })
nearNeighborFinder.fit(testAnalyticCoeffs.T)

# %% 4c. analytic fitting

# Parameter for iterative projection
iteration = 10

# Parameter for exhaustive
step = 500

# Precomputation for tree search
class ClusterTree:
    def __init__(self, data, clusterNum, tol, thres):
        self.leaf = (data.shape[1] <= thres)
        if self.leaf:
            self.centerIndices = nearNeighborFinder.kneighbors(data.T)[1][:, 0]
        else:
            kmeans = KMeans(n_clusters=clusterNum).fit(data.T)
            self.centerIndices = nearNeighborFinder.kneighbors(kmeans.cluster_centers_)[1][:, 0]
            distToCenter = kmeans.transform(data.T)
            distToCenterMin = np.min(distToCenter, axis=1)

            self.clusters = []
            for index in range(clusterNum):
                selector = distToCenter[:, index] < tol * distToCenterMin
                self.clusters.append(ClusterTree(data[:, selector], clusterNum, tol, thres))

tol = 1.05
clusterNum = 12
clusterTree = ClusterTree(testAnalyticCoeffs, clusterNum, tol, 80)

# Lobe Fitting
exhaustiveOn = False
oneLobePsnrVals = np.zeros((len(brdfList),))
oneLobeTime = np.zeros((len(brdfList),))
oneLobeParams = np.zeros((len(brdfList), 1 + 3))
twoLobePsnrVals_projection = np.zeros((len(brdfList),))
twoLobeTime_projection = np.zeros((len(brdfList),))
twoLobeParam_projection = np.zeros((len(brdfList), 1 + 2 * 3))
twoLobePsnrVals_iterative = np.zeros((len(brdfList),))
twoLobeTime_iterative = np.zeros((len(brdfList),))
twoLobeParam_iterative = np.zeros((len(brdfList), 1 + 2 * 3))
if exhaustiveOn:
    twoLobePsnrVals_exhaustive = np.zeros((len(brdfList),))
    twoLobeTime_exhaustive = np.zeros((len(brdfList),))
    twoLobeParam_exhaustive = np.zeros((len(brdfList), 1 + 2 * 3))
twoLobePsnrVals_tree = np.zeros((len(brdfList),))
twoLobeTime_tree = np.zeros((len(brdfList),))
twoLobeParam_tree = np.zeros((len(brdfList), 1 + 2 * 3))

for i, brdfname in enumerate(brdfList):
    copyfile('%s/%s.png'%(pcaImageDir, brdfname), '%s/%s.png'%(brdfImageDir, brdfname))

    # Diffuse
    copyfile('%s/%s_diff.png'%(pcaImageDir, brdfname), '%s/%s_diff.png'%(brdfImageDir, brdfname))
    diffParam = (diffPcaReconCoeff[:, i:i+1]) * diffSlope
    diffAnalytic = lambertian(diffParam).dot(colorAll[:1, :, i])
    saveBrdfImage('%s/%s_diff_analytic.png'%(brdfImageDir, brdfname), diffAnalytic)

    # Specular
    copyfile('%s/%s_spec.png'%(pcaImageDir, brdfname), '%s/%s_spec.png'%(brdfImageDir, brdfname))
    copyfile('%s/%s_spec3.png'%(pcaImageDir, brdfname), '%s/%s_spec3.png'%(brdfImageDir, brdfname))
    orginalCoeff = jointMapPcaReconCoeff[:, i:i+1]

    # 1-lobe fitting
    start = timeit.default_timer()
    oneLobeClosestIndex = nearNeighborFinder.kneighbors(orginalCoeff.T)[1][0, 0]
    oneLobeParam = testAnalyticParams[:, oneLobeClosestIndex:oneLobeClosestIndex+1]
    oneLobeCoeff = testAnalyticCoeffs[:, oneLobeClosestIndex:oneLobeClosestIndex+1]
    oneLobeAnalytic = GGX(oneLobeParam[:1, :], oneLobeParam[1:2, :], oneLobeParam[2:, :]).dot(colorAll[1:, :, i])
    end = timeit.default_timer()
    saveBrdfImage('%s/%s_spec3_nearest.png'%(brdfImageDir, brdfname), measuredBrdf(oneLobeCoeff, jointMapPcaComponents, jointMapMean).dot(colorAll[1:, :, i]))
    saveBrdfImage('%s/%s_spec_analytic_1lobe.png'%(brdfImageDir, brdfname), oneLobeAnalytic)
    oneLobeAnalyticImage = saveBrdfImage('%s/%s_analytic_1lobe.png'%(brdfImageDir, brdfname), diffAnalytic + oneLobeAnalytic)
    oneLobePsnrVals[i] = psnr(originalImages[:, :, :, i], oneLobeAnalyticImage)
    oneLobeTime[i] = end - start
    oneLobeParams[i, :] = np.r_[diffParam.flatten(), oneLobeParam.flatten()]
    print brdfname, '1 lobe finish'
    
    # 2-lobe fitting (Only project the residual)
    start = timeit.default_timer()
    residual = specAll[:, i:i+1] - oneLobeAnalytic
    residualClosestIndex = nearNeighborFinder.kneighbors(projection(residual.clip(min=0), jointMapPcaComponents, jointMapMean).T)[1][0, 0]
    residualParam = testAnalyticParams[:, residualClosestIndex:residualClosestIndex+1]
    residualAnalytic = GGX(residualParam[:1, :], residualParam[1:2, :], residualParam[2:, :]).dot(colorAll[1:, :, i])
    twoLobeAnalytic = oneLobeAnalytic + residualAnalytic
    end = timeit.default_timer()
    saveBrdfImage('%s/%s_spec_analytic_2lobe_1projection.png'%(brdfImageDir, brdfname), twoLobeAnalytic)
    twoLobeAnalyticImage = saveBrdfImage('%s/%s_analytic_2lobe_1projection.png'%(brdfImageDir, brdfname), diffAnalytic + twoLobeAnalytic)
    twoLobePsnrVals_projection[i] = psnr(originalImages[:, :, :, i], twoLobeAnalyticImage)
    twoLobeTime_projection[i] = end - start
    twoLobeParam_projection[i, :] = np.r_[diffParam.flatten(), oneLobeParam.flatten(), residualParam.flatten()]
    print brdfname, '2 lobe projection finish'
    
    # 2-lobe fitting (Iterative projection)
    currentClosestIndex = residualClosestIndex
    for _ in range(iteration):
        lastClosestIndex = currentClosestIndex
        lastParam = testAnalyticParams[:, lastClosestIndex:lastClosestIndex+1]
        residual = specAll[:, i:i+1] - GGX(lastParam[:1, :], lastParam[1:2, :], lastParam[2:, :])
        currentClosestIndex = nearNeighborFinder.kneighbors(projection(residual.clip(min=0), jointMapPcaComponents, jointMapMean).T)[1][0, 0]
    twoLobeParam = testAnalyticParams[:, [lastClosestIndex, currentClosestIndex]]
    twoLobeAnalytic = GGX(twoLobeParam[:1, :], twoLobeParam[1:2, :], twoLobeParam[2:, :]).sum(axis=1, keepdims=True).dot(colorAll[1:, :, i])
    end = timeit.default_timer()
    saveBrdfImage('%s/%s_spec_analytic_2lobe_2iterative.png'%(brdfImageDir, brdfname), twoLobeAnalytic)
    twoLobeAnalyticImage = saveBrdfImage('%s/%s_analytic_2lobe_2iterative.png'%(brdfImageDir, brdfname), diffAnalytic + twoLobeAnalytic)
    twoLobePsnrVals_iterative[i] = psnr(originalImages[:, :, :, i], twoLobeAnalyticImage)
    twoLobeTime_iterative[i] = end - start
    twoLobeParam_iterative[i, :] = np.r_[diffParam.flatten(), twoLobeParam[:, 0].flatten(), twoLobeParam[:, 1].flatten()]
    print brdfname, '2 lobe iterative projection finish'
    
    # 2-lobe fitting (Exhaustive: enumerate all the possibility of the first lobe, then find the second lobe)
    if exhaustiveOn:
        start = timeit.default_timer()
        residualClosestIndices = np.zeros((testAnalyticParams.shape[1], ), int)
        errors = np.zeros((testAnalyticParams.shape[1], ))
        for j in range(testAnalyticParams.shape[1] / step):
            firstLobes = GGX(testAnalyticParams[:1, step*j:step*(j+1)], testAnalyticParams[1:2, step*j:step*(j+1)], testAnalyticParams[2:, step*j:step*(j+1)])
            residual = specAll[:, i:i+1] - firstLobes
            residualClosestIndices[step*j:step*(j+1)] = nearNeighborFinder.kneighbors(projection(residual.clip(min=0), jointMapPcaComponents, jointMapMean).T)[1][:, 0]
            residualParams = testAnalyticParams[:, residualClosestIndices[step*j:step*(j+1)].astype(int)]
            secondLobes = GGX(residualParams[:1, :], residualParams[1:2, :], residualParams[2:, :])
            errors[step*j:step*(j+1)] = l2norm(MapBRDF(specAll[:, i:i+1] * cosMap), MapBRDF((firstLobes + secondLobes) * cosMap))
            print brdfname, j, '/', testAnalyticParams.shape[1] / step
        bestFirstIndex = np.argmin(errors)
        twoLobeParam = testAnalyticParams[:, [bestFirstIndex, residualClosestIndices[bestFirstIndex]]]
        twoLobeAnalytic = GGX(twoLobeParam[:1, :], twoLobeParam[1:2, :], twoLobeParam[2:, :]).sum(axis=1, keepdims=True).dot(colorAll[1:, :, i])
        end = timeit.default_timer()
        saveBrdfImage('%s/%s_spec_analytic_2lobe_3exhaustive.png'%(brdfImageDir, brdfname), twoLobeAnalytic)
        twoLobeAnalyticImage = saveBrdfImage('%s/%s_analytic_2lobe_3exhaustive.png'%(brdfImageDir, brdfname), diffAnalytic + twoLobeAnalytic)
        twoLobePsnrVals_exhaustive[i] = psnr(originalImages[:, :, :, i], twoLobeAnalyticImage)
        twoLobeTime_exhaustive[i] = end - start
        twoLobeParam_exhaustive[i, :] = np.r_[diffParam.flatten(), twoLobeParam[:, 0].flatten(), twoLobeParam[:, 1].flatten()]
        print brdfname, '2 lobe exhaustive finish'
        print brdfname, twoLobePsnrVals_exhaustive[i], twoLobePsnrVals_tree[i]
        print brdfname, twoLobeTime_exhaustive[i], twoLobeTime_tree[i]

    #2-lobe fitting (tree search: search for min loss on a tree)
    start = timeit.default_timer()
    clusterNode = clusterTree
    while True:
        centerParams = testAnalyticParams[:, clusterNode.centerIndices]
        centerLobes = GGX(centerParams[:1, :], centerParams[1:2, :], centerParams[2:, :])
        centerResidual = specAll[:, i:i+1] - centerLobes
        centerResidualClosestIndices = nearNeighborFinder.kneighbors(projection(centerResidual.clip(min=0), jointMapPcaComponents, jointMapMean).T)[1][:, 0]
        centerResidualParams = testAnalyticParams[:, centerResidualClosestIndices]
        centerSecondLobes = GGX(centerResidualParams[:1, :], centerResidualParams[1:2, :], centerResidualParams[2:, :])
        closestCenterIndex = np.argmin(l2norm(MapBRDF(specAll[:, i:i+1] * cosMap), MapBRDF((centerLobes + centerSecondLobes) * cosMap)))
        if clusterNode.leaf:
            break
        else:
            clusterNode = clusterNode.clusters[closestCenterIndex]
    
    twoLobeAnalytic = (centerLobes[:, closestCenterIndex:closestCenterIndex+1] + centerSecondLobes[:, closestCenterIndex:closestCenterIndex+1]).dot(colorAll[1:, :, i])
    end = timeit.default_timer()
    saveBrdfImage('%s/%s_spec_analytic_2lobe_4tree.png'%(brdfImageDir, brdfname), twoLobeAnalytic)
    twoLobeAnalyticImage = saveBrdfImage('%s/%s_analytic_2lobe_4tree.png'%(brdfImageDir, brdfname), diffAnalytic + twoLobeAnalytic)
    twoLobePsnrVals_tree[i] = psnr(originalImages[:, :, :, i], twoLobeAnalyticImage)
    twoLobeTime_tree[i] = end - start
    twoLobeParam_tree[i, :] = np.r_[diffParam.flatten(), centerParams[:, closestCenterIndex].flatten(), centerResidualParams[:, closestCenterIndex].flatten()]
    print brdfname, '2 lobe tree finish'

np.save('%s/oneLobePsnrVals.npy'%writeDataDir, oneLobePsnrVals)
np.save('%s/oneLobeTime.npy'%writeDataDir, oneLobeTime)
np.save('%s/oneLobeParams.npy'%writeDataDir, oneLobeParams)
np.save('%s/twoLobePsnrVals_projection.npy'%writeDataDir, twoLobePsnrVals_projection)
np.save('%s/twoLobeTime_projection.npy'%writeDataDir, twoLobeTime_projection)
np.save('%s/twoLobeParam_projection.npy'%writeDataDir, twoLobeParam_projection)
np.save('%s/twoLobePsnrVals_iterative.npy'%writeDataDir, twoLobePsnrVals_iterative)
np.save('%s/twoLobeTime_iterative.npy'%writeDataDir, twoLobeTime_iterative)
np.save('%s/twoLobeParam_iterative.npy'%writeDataDir, twoLobeParam_iterative)
if exhaustiveOn:
    np.save('%s/twoLobePsnrVals_exhaustive.npy'%writeDataDir, twoLobePsnrVals_exhaustive)
    np.save('%s/twoLobeTime_exhaustive.npy'%writeDataDir, twoLobeTime_exhaustive)
    np.save('%s/twoLobeParam_exhaustive.npy'%writeDataDir, twoLobeParam_exhaustive)
np.save('%s/twoLobePsnrVals_tree.npy'%writeDataDir, twoLobePsnrVals_tree)
np.save('%s/twoLobeTime_tree.npy'%writeDataDir, twoLobeTime_tree)
np.save('%s/twoLobeParam_tree.npy'%writeDataDir, twoLobeParam_tree)

# %% 4d. Two Lobe Naive Fitting
import numpy.random as nr
diffParamAll_log2 = np.load('%s/diffParamAll_log2.npy'%brdfDataDir)
specParamAll_log2 = np.load('%s/specParamAll_log2.npy'%brdfDataDir)

specAnalyticAll_log2 = np.load('%s/specAnalyticAll_log2.npy'%brdfDataDir)

index = brdfList.index('specular-blue-phenolic')
saveBrdfImage('specular-blue-phenolic_spec_log2.png', specAnalyticAll_log2[:, index:index+1].dot(colorAll[1:, :, index]))

testNum = 5
paramLen = 1 + 3 + 2 * 3 + 3

# Initialize or load existing data for resumption
twoLobeNaivePsnrVals_log2_path = '%s/twoLobeNaivePsnrVals_log2.npy'%writeDataDir
twoLobeNaiveTime_log2_path = '%s/twoLobeNaiveTime_log2.npy'%writeDataDir
twoLobeNaiveParam_log2_path = '%s/twoLobeNaiveParam_log2.npy'%writeDataDir
twoLobeNaivePsnrVals_cubicRoot_path = '%s/twoLobeNaivePsnrVals_cubicRoot.npy'%writeDataDir
twoLobeNaiveTime_cubicRoot_path = '%s/twoLobeNaiveTime_cubicRoot.npy'%writeDataDir
twoLobeNaiveParam_cubicRoot_path = '%s/twoLobeNaiveParam_cubicRoot.npy'%writeDataDir

if os.path.exists(twoLobeNaivePsnrVals_log2_path):
    print "Loading existing data for Two Lobe Naive resumption..."
    twoLobeNaivePsnrVals_log2 = np.load(twoLobeNaivePsnrVals_log2_path)
    twoLobeNaiveTime_log2 = np.load(twoLobeNaiveTime_log2_path)
    twoLobeNaiveParam_log2 = np.load(twoLobeNaiveParam_log2_path)
    twoLobeNaivePsnrVals_cubicRoot = np.load(twoLobeNaivePsnrVals_cubicRoot_path)
    twoLobeNaiveTime_cubicRoot = np.load(twoLobeNaiveTime_cubicRoot_path)
    twoLobeNaiveParam_cubicRoot = np.load(twoLobeNaiveParam_cubicRoot_path)
else:
    twoLobeNaivePsnrVals_log2 = np.zeros((len(brdfList), testNum))
    twoLobeNaiveTime_log2 = np.zeros((len(brdfList), testNum))
    twoLobeNaiveParam_log2 = np.zeros((len(brdfList), testNum, paramLen))
    twoLobeNaivePsnrVals_cubicRoot = np.zeros((len(brdfList), testNum))
    twoLobeNaiveTime_cubicRoot = np.zeros((len(brdfList), testNum))
    twoLobeNaiveParam_cubicRoot = np.zeros((len(brdfList), testNum, paramLen))

for i, brdfname in enumerate(brdfList):
    # Check if this material is already processed (check if last test image exists and data is non-zero)
    lastImgPath = '%s/%s_analytic_2lobe_naive_cubicRoot_4.png'%(brdfImageDir, brdfname)
    if os.path.exists(lastImgPath) and np.any(twoLobeNaiveParam_log2[i, 0, :] != 0):
        print "Skipping", brdfname, "(already done)"
        continue

    brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
    brdf = brdfRaw.reshape((-1, 3))[maskMap]

    for metric in ['log2', 'cubicRoot']:
        for j in range(testNum):
            if j == 0:
                initVal = [float(diffParamAll_log2[0, i]),
                           float(0.5 * specParamAll_log2[0, i]), float(specParamAll_log2[1, i]), float(specParamAll_log2[2, i]),
                           float(0.5 * specParamAll_log2[0, i]), float(specParamAll_log2[1, i]), float(specParamAll_log2[2, i]),
                          ] + (nr.rand(6, ) * 3).astype(float).tolist()
            elif j == 1:
                initVal = [float(diffParamAll_log2[0, i]),
                           float(specParamAll_log2[0, i]), float(specParamAll_log2[1, i]), float(specParamAll_log2[2, i]),
                           float(0.0), float(specParamAll_log2[1, i]), float(specParamAll_log2[2, i]),
                          ] + (nr.rand(6, ) * 3).astype(float).tolist()
            else:
                initVal = [nr.random(),
                           nr.random(), float(np.exp(nr.uniform(np.log(0.001), np.log(1.0)))), float(np.exp(nr.uniform(np.log(1.0), np.log(10.0)))),
                           nr.random(), float(np.exp(nr.uniform(np.log(0.001), np.log(1.0)))), float(np.exp(nr.uniform(np.log(1.0), np.log(10.0)))),
                          ] + (nr.rand(6, ) * 3).astype(float).tolist()

            start = timeit.default_timer()
            diffParam, specParam1, specParam2, diffColor, specColor = eng.twoLobeNaiveFit(brdf.T.flatten().tolist(), initVal, metric, nargout=5)
            diffParam = np.array(diffParam).reshape((-1, 1))
            specParam1 = np.array(specParam1).reshape((-1, 1))
            specParam2 = np.array(specParam2).reshape((-1, 1))
            diffColor = np.array(diffColor).reshape((1, -1))
            specColor = np.array(specColor).reshape((1, -1))
            analyticBrdf = (lambertian(diffParam).dot(diffColor)
                         + (GGX(specParam1[:1, :], specParam1[1:2, :], specParam1[2:, :])
                         + GGX(specParam2[:1, :], specParam2[1:2, :], specParam2[2:, :])).dot(specColor))
            end = timeit.default_timer()
            analyticBrdfImage = saveBrdfImage('%s/%s_analytic_2lobe_naive_%s_%s.png'%(brdfImageDir, brdfname, metric, j), analyticBrdf)
            if metric == 'log2':
                twoLobeNaivePsnrVals_log2[i, j] = psnr(analyticBrdfImage, originalImages[:, :, :, i])
                twoLobeNaiveTime_log2[i, j] = end - start
                twoLobeNaiveParam_log2[i, j, :] = np.r_[diffParam.flatten(), diffColor.flatten(), specParam1.flatten(), specParam2.flatten(), specColor.flatten()]
            elif metric == 'cubicRoot':
                twoLobeNaivePsnrVals_cubicRoot[i, j] = psnr(analyticBrdfImage, originalImages[:, :, :, i])
                twoLobeNaiveTime_cubicRoot[i, j] = end - start
                twoLobeNaiveParam_cubicRoot[i, j, :] = np.r_[diffParam.flatten(), diffColor.flatten(), specParam1.flatten(), specParam2.flatten(), specColor.flatten()]

    # Save intermediate results after each material
    np.save(twoLobeNaivePsnrVals_log2_path, twoLobeNaivePsnrVals_log2)
    np.save(twoLobeNaiveTime_log2_path, twoLobeNaiveTime_log2)
    np.save(twoLobeNaiveParam_log2_path, twoLobeNaiveParam_log2)
    np.save(twoLobeNaivePsnrVals_cubicRoot_path, twoLobeNaivePsnrVals_cubicRoot)
    np.save(twoLobeNaiveTime_cubicRoot_path, twoLobeNaiveTime_cubicRoot)
    np.save(twoLobeNaiveParam_cubicRoot_path, twoLobeNaiveParam_cubicRoot)
    print brdfname, "completed", i+1, "/", len(brdfList)

np.save('%s/twoLobeNaivePsnrVals_log2.npy'%writeDataDir, twoLobeNaivePsnrVals_log2)
np.save('%s/twoLobeNaiveTime_log2.npy'%writeDataDir, twoLobeNaiveTime_log2)
np.save('%s/twoLobeNaiveParam_log2.npy'%writeDataDir, twoLobeNaiveParam_log2)
np.save('%s/twoLobeNaivePsnrVals_cubicRoot.npy'%writeDataDir, twoLobeNaivePsnrVals_cubicRoot)
np.save('%s/twoLobeNaiveTime_cubicRoot.npy'%writeDataDir, twoLobeNaiveTime_cubicRoot)
np.save('%s/twoLobeNaiveParam_cubicRoot.npy'%writeDataDir, twoLobeNaiveParam_cubicRoot)
