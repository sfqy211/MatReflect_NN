import sys, os
utilFuncPath = '../_util/functions'
utilDataPath = '../_util/data'
if utilFuncPath not in sys.path:
    sys.path.insert(0, utilFuncPath)

import StringIO
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt

from merlFunctions import *
from coordinateFunctions import *
from hsi import *

import matlab.engine
eng = matlab.engine.start_matlab()
eng.addpath(utilFuncPath)
eng.addpath(utilDataPath)
eng.addpath(renderWeightDir)
# eng.exit()

maskMap = np.load('%s/maskMap.npy'%utilDataPath)   #Indicating valid regions in MERL BRDFs
brdfValNum = np.sum(maskMap)

brdfDir = '../../brdf'
brdfList = sorted([f.split('.')[0] for f in os.listdir(brdfDir) if f.endswith('.binary') and 'a' <= f[0] <= 'z'])
writeDataDir = 'data'
if not os.path.exists(writeDataDir):
    os.makedirs(writeDataDir)
writeImageDir = 'brdfimage'
if not os.path.exists(writeImageDir):
    os.makedirs(writeImageDir)


# %% 1. Analytic Fit Test
writeBrdfImageDir = 'brdfimage/1-analyticOpt'
if not os.path.exists(writeBrdfImageDir):
    os.makedirs(writeBrdfImageDir)

# Check if all results already exist
allAnalyticDone = os.path.exists('%s/analyticPsnrVals.npy'%writeDataDir)

analyticPsnrVals = {}
for metric in ['log1', 'log2', 'cubicRoot', 'weightSquare']:

    print metric, " optimzing"

    # Check if this metric is already done
    metricDone = os.path.exists('%s/diffParamAll_%s.npy'%(writeDataDir, metric)) and \
                 os.path.exists('%s/specParamAll_%s.npy'%(writeDataDir, metric)) and \
                 os.path.exists('%s/diffAnalyticAll_%s.npy'%(writeDataDir, metric)) and \
                 os.path.exists('%s/specAnalyticAll_%s.npy'%(writeDataDir, metric))

    if metricDone:
        print "  Skipping (already done)"
        continue

    # Initialize or load existing data for resumption
    diffParamAllPath = '%s/diffParamAll_%s.npy'%(writeDataDir, metric)
    specParamAllPath = '%s/specParamAll_%s.npy'%(writeDataDir, metric)
    diffAnalyticAllPath = '%s/diffAnalyticAll_%s.npy'%(writeDataDir, metric)
    specAnalyticAllPath = '%s/specAnalyticAll_%s.npy'%(writeDataDir, metric)
    analyticPsnrValsPath = '%s/analyticPsnrVals_%s.npy'%(writeDataDir, metric)

    if os.path.exists(diffParamAllPath):
        diffParamAll = np.load(diffParamAllPath)
        specParamAll = np.load(specParamAllPath)
        diffAnalyticAll = np.load(diffAnalyticAllPath)
        specAnalyticAll = np.load(specAnalyticAllPath)
        analyticPsnrVals[metric] = np.load(analyticPsnrValsPath)
        print "  Loaded existing data for resumption"
    else:
        diffParamAll = np.zeros((1, len(brdfList)))
        specParamAll = np.zeros((3, len(brdfList)))
        diffAnalyticAll = np.zeros((brdfValNum, len(brdfList)))
        specAnalyticAll = np.zeros((brdfValNum, len(brdfList)))
        analyticPsnrVals[metric] = np.zeros((len(brdfList), ))

    for i, brdfname in enumerate(brdfList):
        # Check if this material is already processed
        combineImgPath = '%s/%s_combineanalytic_%s.png'%(writeBrdfImageDir, brdfname, metric)
        if os.path.exists(combineImgPath) and diffParamAll[0, i] != 0:
            print "  Skipping", brdfname, "(already done)"
            continue

        brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
        brdf = brdfRaw.reshape((-1, 3))[maskMap]
        brdfMean = np.mean(brdf, axis=1)
        originalImage = saveBrdfImage('%s/%s.png'%(writeBrdfImageDir, brdfname), brdfMean)

        diffParam, specParam, diffAnalytic, specAnalytic = eng.analyticOpt(brdfMean.flatten().tolist(), 'Lambertian', 'GGX', metric, nargout=4)
        diffParam = np.array(diffParam).reshape((-1, ))
        specParam = np.array(specParam).reshape((-1, ))
        diffAnalytic = np.array(diffAnalytic).reshape((-1, ))
        specAnalytic = np.array(specAnalytic).reshape((-1, ))

        saveBrdfImage('%s/%s_diffanalytic_%s.png'%(writeBrdfImageDir, brdfname, metric), diffAnalytic)
        saveBrdfImage('%s/%s_specanalytic_%s.png'%(writeBrdfImageDir, brdfname, metric), specAnalytic)
        analyticImage = saveBrdfImage('%s/%s_combineanalytic_%s.png'%(writeBrdfImageDir, brdfname, metric), diffAnalytic + specAnalytic)

        diffParamAll[:, i] = diffParam
        specParamAll[:, i] = specParam
        diffAnalyticAll[:, i] = diffAnalytic
        specAnalyticAll[:, i] = specAnalytic
        analyticPsnrVals[metric][i] = psnr(originalImage, analyticImage)

        # Save intermediate results for resumption
        np.save(diffParamAllPath, diffParamAll)
        np.save(specParamAllPath, specParamAll)
        np.save(diffAnalyticAllPath, diffAnalyticAll)
        np.save(specAnalyticAllPath, specAnalyticAll)
        np.save(analyticPsnrValsPath, analyticPsnrVals[metric])

    np.save('%s/diffParamAll_%s.npy'%(writeDataDir, metric), diffParamAll)
    np.save('%s/specParamAll_%s.npy'%(writeDataDir, metric), specParamAll)
    np.save('%s/diffAnalyticAll_%s.npy'%(writeDataDir, metric), diffAnalyticAll)
    np.save('%s/specAnalyticAll_%s.npy'%(writeDataDir, metric), specAnalyticAll)

if not allAnalyticDone:
    np.save('%s/analyticPsnrVals.npy'%(writeDataDir), analyticPsnrVals)

analyticPsnrVals = np.load('%s/analyticPsnrVals.npy'%(writeDataDir))
analyticPsnrVals.item()['log1'].mean()
analyticPsnrVals.item()['log2'].mean()
analyticPsnrVals.item()['cubicRoot'].mean()
analyticPsnrVals.item()['weightSquare'].mean()
# plt.plot(analyticPsnrVals.item()['log1'])
# plt.plot(analyticPsnrVals.item()['log2'])
# plt.plot(analyticPsnrVals.item()['cubicRoot'])
# plt.plot(analyticPsnrVals.item()['weightSquare'])
# plt.legend(['log1', 'log2', 'cubicRoot', 'weightSquare'])
# # plt.show()
# plt.savefig('analyticPsnrVals.eps')


# %% 2. DiffSpec Separation Test
writeBrdfImageDir = 'brdfimage/2-diffSpecOpt'
if not os.path.exists(writeBrdfImageDir):
    os.makedirs(writeBrdfImageDir)

# Check if all results already exist
allSeparationDone = os.path.exists('%s/separationPsnrVals.npy'%writeDataDir)

f = open('log.txt', 'a')  # Use append mode to preserve previous logs
separationPsnrVals = {}
for metric in ['log1', 'log2', 'cubicRoot']:

    # Check if this metric is already done
    metricDone = os.path.exists('%s/diffAll_%s.npy'%(writeDataDir, metric)) and \
                 os.path.exists('%s/specAll_%s.npy'%(writeDataDir, metric))

    if metricDone:
        print "Skipping", metric, "(already done)"
        continue

    diffAnalyticAll = np.load('%s/diffAnalyticAll_%s.npy'%(writeDataDir, metric))
    specAnalyticAll = np.load('%s/specAnalyticAll_%s.npy'%(writeDataDir, metric))

    # Initialize or load existing data for resumption
    diffAllPath = '%s/diffAll_%s.npy'%(writeDataDir, metric)
    specAllPath = '%s/specAll_%s.npy'%(writeDataDir, metric)
    separationPsnrValsPath = '%s/separationPsnrVals_%s.npy'%(writeDataDir, metric)

    if os.path.exists(diffAllPath):
        diffAll = np.load(diffAllPath)
        specAll = np.load(specAllPath)
        separationPsnrVals[metric] = np.load(separationPsnrValsPath)
        print "Loaded existing data for", metric, "resumption"
    else:
        diffAll = np.zeros((brdfValNum, len(brdfList)))
        specAll = np.zeros((brdfValNum, len(brdfList)))
        separationPsnrVals[metric] = np.zeros((len(brdfList), ))

    for i, brdfname in enumerate(brdfList):
        # Check if this material is already processed (check if data is non-zero)
        combineImgPath = '%s/%s_combine_%s.png'%(writeBrdfImageDir, brdfname, metric)
        if os.path.exists(combineImgPath) and np.any(diffAll[:, i] != 0):
            print "Skipping", brdfname, metric, "(already done)"
            continue

        brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
        brdf = brdfRaw.reshape((-1, 3))[maskMap]
        brdfMean = np.mean(brdf, axis=1)
        originalImage = saveBrdfImage('%s/%s.png'%(writeBrdfImageDir, brdfname), brdfMean)

        out = StringIO.StringIO()
        diff, spec = eng.diffSpecOpt(brdfMean.flatten().tolist(), diffAnalyticAll[:, i].flatten().tolist(), specAnalyticAll[:, i].flatten().tolist(), 0.9, 0.8, nargout=2, stdout=out)
        f.write('=====%s %s=====\n%s'%(metric, brdfname, out.getvalue()))
        f.flush()  # Flush after each write
        diff = np.array(diff).reshape((-1, ))
        spec = np.array(spec).reshape((-1, ))

        saveBrdfImage('%s/%s_diff_%s.png'%(writeBrdfImageDir, brdfname, metric), diff)
        saveBrdfImage('%s/%s_spec_%s.png'%(writeBrdfImageDir, brdfname, metric), spec)
        separationImage = saveBrdfImage('%s/%s_combine_%s.png'%(writeBrdfImageDir, brdfname, metric), diff + spec)

        diffAll[:, i] = diff
        specAll[:, i] = spec
        separationPsnrVals[metric][i] = psnr(originalImage, separationImage)

        # Save intermediate results for resumption
        np.save(diffAllPath, diffAll)
        np.save(specAllPath, specAll)
        np.save(separationPsnrValsPath, separationPsnrVals[metric])

    np.save('%s/diffAll_%s.npy'%(writeDataDir, metric), diffAll)
    np.save('%s/specAll_%s.npy'%(writeDataDir, metric), specAll)

f.close()
if not allSeparationDone:
    np.save('%s/separationPsnrVals.npy'%(writeDataDir), separationPsnrVals)

separationPsnrVals = np.load('%s/separationPsnrVals.npy'%(writeDataDir))
separationPsnrVals.item()['log1'].mean()
separationPsnrVals.item()['log2'].mean()
separationPsnrVals.item()['cubicRoot'].mean()
# plt.plot(separationPsnrVals.item()['log1'])
# plt.plot(separationPsnrVals.item()['log2'])
# plt.plot(separationPsnrVals.item()['cubicRoot'])
# plt.legend(['log1', 'log2', 'cubicRoot'])
# # plt.show()
# plt.savefig('separationPsnrVals.eps')
# plt.show()

# %% 3. Color Restoration Test
writeBrdfImageDir = 'brdfimage/3-colorOpt'
if not os.path.exists(writeBrdfImageDir):
    os.makedirs(writeBrdfImageDir)

# Check if all results already exist
allColorDone = os.path.exists('%s/colorPsnrVals.npy'%writeDataDir)

separationMetric = 'log2'
colorPsnrVals = {}
for metric in ['image2', 'brdf2']:

    # Check if this metric is already done
    metricDone = os.path.exists('%s/colorAll_%s.npy'%(writeDataDir, metric))

    if metricDone:
        print "Skipping", metric, "(already done)"
        continue

    diffAll = np.load('%s/diffAll_%s.npy'%(writeDataDir, separationMetric))
    specAll = np.load('%s/specAll_%s.npy'%(writeDataDir, separationMetric))

    # Initialize or load existing data for resumption
    colorAllPath = '%s/colorAll_%s.npy'%(writeDataDir, metric)
    colorPsnrPath = '%s/colorPsnrVals_%s.npy'%(writeDataDir, metric)
    if os.path.exists(colorAllPath):
        print "Loading existing colorAll for resumption..."
        colorAll = np.load(colorAllPath)
    else:
        colorAll = np.zeros((2, 3, len(brdfList)))

    if os.path.exists(colorPsnrPath):
        colorPsnrVals[metric] = np.load(colorPsnrPath)
    else:
        colorPsnrVals[metric] = np.zeros((len(brdfList), ))

    for i, brdfname in enumerate(brdfList):
        # Check if this material is already processed (has valid color data)
        combineImgPath = '%s/%s_combine_%s.png'%(writeBrdfImageDir, brdfname, metric)
        if os.path.exists(combineImgPath) and np.any(colorAll[:, :, i] != 0):
            print "Skipping", brdfname, metric, "(already done)"
            continue

        brdfRaw = readMERLBRDF('%s/%s.binary'%(brdfDir, brdfname))
        brdf = brdfRaw.reshape((-1, 3))[maskMap]
        originalImage = saveBrdfImage('%s/%s.png'%(writeBrdfImageDir, brdfname), brdf)

        I, S, H = RGBtoHSI(brdf)
        histogram2d, xedges, yedges, Image = plt.hist2d(H, S, bins=[180, 100])
        Hindex, Sindex = np.unravel_index(np.argmax(histogram2d), histogram2d.shape)
        HBest = (xedges[Hindex] + xedges[Hindex + 1]) / 2
        SBest = yedges[min(Sindex + 5, 100)]
        commonColor = HSItoRGB(np.array([1.]), np.array([SBest]), np.array([HBest]))
        colorGuess = np.concatenate([commonColor, np.ones((1, 3))], axis=1)

        lobes = np.stack([diffAll[:, i], specAll[:, i]], axis=1)
        color = eng.colorOpt(brdf.T.flatten().tolist(), lobes.T.flatten().tolist(), colorGuess.T.flatten().tolist(), metric)
        color = np.array(color).reshape((2, 3))

        saveBrdfImage('%s/%s_diff_%s.png'%(writeBrdfImageDir, brdfname, metric), lobes[:, :1].dot(color[:1, :]))
        saveBrdfImage('%s/%s_spec_%s.png'%(writeBrdfImageDir, brdfname, metric), lobes[:, 1:].dot(color[1:, :]))
        colorImage = saveBrdfImage('%s/%s_combine_%s.png'%(writeBrdfImageDir, brdfname, metric), lobes.dot(color))

        colorAll[:, :, i] = color
        colorPsnrVals[metric][i] = psnr(originalImage, colorImage)
        print metric, brdfname, colorPsnrVals[metric][i]

        # Save intermediate results for resumption
        np.save(colorAllPath, colorAll)
        np.save(colorPsnrPath, colorPsnrVals[metric])

    print metric, colorPsnrVals[metric].mean()

if not allColorDone:
    np.save('%s/colorPsnrVals.npy'%(writeDataDir), colorPsnrVals)

# plt.plot(colorPsnrVals.item()['brdf1'])
# plt.plot(colorPsnrVals.item()['image1'])
# plt.plot(colorPsnrVals.item()['image2'])
# plt.legend(['brdf1', 'image1', 'image2'])
# # plt.show()
# plt.savefig('colorPsnrVals.eps')
