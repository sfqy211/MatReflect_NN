#Read BRDF
import numpy as np
import os.path as path

def readMERLBRDF(filename):
	"""Reads a MERL-type .binary file, containing a densely sampled BRDF

	Returns a 4-dimensional array (phi_d, theta_h, theta_d, channel)"""
	# print("Loading MERL-BRDF: ",filename)
	try:
		f = open(filename, "rb")
		dims = np.fromfile(f,np.int32,3)
		vals = np.fromfile(f,np.float64,-1)
		f.close()
	except IOError:
		print("Cannot read file:", path.basename(filename))
		return

	BRDFVals = np.swapaxes(np.reshape(vals,(dims[2], dims[1], dims[0], 3),'F'),1,2)
	BRDFVals *= (1.00/1500,1.15/1500,1.66/1500) #Colorscaling
	BRDFVals[BRDFVals<0] = -1

	return BRDFVals

def saveMERLBRDF(filename,BRDFVals,shape=(180,90,90),toneMap=True):
    "Saves a BRDF to a MERL-type .binary file"
    # print("Saving MERL-BRDF: ",filename)
    BRDFVals = np.array(BRDFVals)   #Make a copy
    if(BRDFVals.shape != (np.prod(shape),3) and BRDFVals.shape != shape+(3,)):
        print("Shape of BRDFVals incorrect")
        return

    #Do MERL tonemapping if needed
    if(toneMap):
        BRDFVals /= (1.00/1500,1.15/1500,1.66/1500) #Colorscaling

    #Are the values not mapped in a cube?
    if(BRDFVals.shape[1] == 3):
        BRDFVals = np.reshape(BRDFVals,shape+(3,))

    #Vectorize:
    vec = np.reshape(np.swapaxes(BRDFVals,1,2),(-1),'F')
    shape = [shape[2],shape[1],shape[0]]

    try:
        f = open(filename, "wb")
        np.array(shape).astype(np.int32).tofile(f)
        vec.astype(np.float64).tofile(f)
        f.close()
    except IOError:
        print("Cannot write to file:", path.basename(filename))
        return

# Save BRDF image
import scipy.sparse as ssp
import cv2

def load_sparse_csr(filename):
    loader = np.load(filename)
    return ssp.csr_matrix((loader['data'], loader['indices'], loader['indptr']), shape=loader['shape'])

resolution = 250
renderWeightDir = path.dirname(__file__) + '/../fastrender/weights'

writeBrdf = np.ones((180*90*90, 3)) * (-1)

def saveBrdfImage(filename, brdf, compare=None):
	if not saveBrdfImage.load:
		saveBrdfImage.brdfBias = np.load(renderWeightDir + '/brdfBias.npy')
		saveBrdfImage.brdfWeightR = load_sparse_csr(renderWeightDir + '/brdfWeightR.npz')
		saveBrdfImage.brdfWeightG = load_sparse_csr(renderWeightDir + '/brdfWeightG.npz')
		saveBrdfImage.brdfWeightB = load_sparse_csr(renderWeightDir + '/brdfWeightB.npz')
		saveBrdfImage.load = True
	if len(brdf.shape) == 2:
		image = (np.stack([saveBrdfImage.brdfWeightR.dot(brdf[:, 0]), saveBrdfImage.brdfWeightG.dot(brdf[:, 1]), saveBrdfImage.brdfWeightB.dot(brdf[:, 2])], axis=1) + saveBrdfImage.brdfBias).reshape((resolution, resolution, 3))
	else:
		image = (np.stack([saveBrdfImage.brdfWeightR.dot(brdf), saveBrdfImage.brdfWeightG.dot(brdf), saveBrdfImage.brdfWeightB.dot(brdf)], axis=1) + saveBrdfImage.brdfBias).reshape((resolution, resolution, 3))
	cv2.imwrite(filename, image[:, :, ::-1].clip(min=0) ** (1 / 2.2) * 255)
	if compare is not None:
		for compareName, compareImage in compare.iteritems():
			residual = np.mean(image, axis=2) - compareImage
			residualImage = np.zeros_like(image)
			residualImage[:, :, 0] = np.fmax(residual, 0.) * 5
			residualImage[:, :, 2] = -np.fmin(residual, 0.) * 5
			cv2.imwrite(filename[:-4] + '_residual_%s.png'%compareName, residualImage[:, :, ::-1])
	return image
saveBrdfImage.load = False

def saveBrdfMeanImage(filename, brdf):
	if not saveBrdfMeanImage.load:
		saveBrdfMeanImage.brdfWeightMean = load_sparse_csr(renderWeightDir + '/brdfWeightMean.npz')
		saveBrdfMeanImage.load = True

	image = saveBrdfMeanImage.brdfWeightMean.dot(brdf).reshape((resolution, resolution, 3))
	cv2.imwrite(filename, image[:, :, ::-1].clip(min=0) ** (1 / 2.2) * 255)
	return image
saveBrdfMeanImage.load = False

def psnr(img1, img2):
	PIXEL_MAX = 1.0
	mse = np.mean( (img1.clip(max=PIXEL_MAX) - img2.clip(max=PIXEL_MAX)) ** 2 )
	return -10 * np.log10(mse)
