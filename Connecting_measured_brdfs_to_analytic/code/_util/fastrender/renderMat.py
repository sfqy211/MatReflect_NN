import cv2
import numpy as np
from numpy.linalg import norm, inv
from numpy.random import sample
import scipy.sparse as ssp
from multiprocessing import Process, Queue, freeze_support

from transform import *

# parameters
resolution = 250
# Reduced sampling for faster weight precomputation during workflow testing.
pixelSampleNum = 64
lightSampleNum = 64
materialSampleNum = 64
brdfLen = 1098594

threadsNum = 12

# camera 
radius = 1.1
fov = 22. * np.pi / 180.
cameraToWorld = lookAt([0, -2, 6], [0, 0, 0], [0, 1, 0])

class EnvMap:
	def __init__(self, filename, lightToWorld):
		self.envMap = self.readExr(filename)
		self.size = self.envMap.shape
		self.num = self.size[0] * self.size[1]

		self.lightToWorld = lightToWorld
		self.worldToLight = inv(lightToWorld)

		pdfIllum = np.sum(self.envMap, axis=2).flatten()
		self.cdf = np.cumsum(pdfIllum)
		pdfIllum /= self.cdf[-1]
		self.cdf /= self.cdf[-1]

		self.pdf = pdfIllum * self.num / (np.sin((np.mgrid[:self.size[0], :self.size[1]][0] + 0.5) * np.pi / self.size[0]) * (2 * np.pi ** 2)).flatten()

	def readExr(self, filename):
		return cv2.imread(filename, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)[:, :, ::-1]

	def worldDirToValue(self, worldDir):
		lightDir = self.worldToLight[:3, :3].dot(worldDir)
		theta = np.arccos(np.clip(lightDir[2], -1., 1.))
		phi = np.arctan2(lightDir[1], lightDir[0])
		if phi < 0:
			phi += 2 * np.pi
		y, x = int(theta / np.pi * self.size[0]), int(phi / (2*np.pi) * self.size[1])
		return self.envMap[y, x, :], self.pdf[y * self.size[1] + x]

	def getLight(self, lightSample):
		l, r = 0, self.num-1
		while l < r:
			mid = (l + r) / 2
			if lightSample <= self.cdf[mid]:
				r = mid
			else:
				l = mid + 1
		pdf = self.pdf[mid]
		y, x = np.unravel_index(mid, self.size[:2])
		light = self.envMap[y, x, :]
		theta = np.pi * y / self.size[0]
		phi = 2 * np.pi * x / self.size[1]
		lightDir = np.array([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)])
		return light, lightToWorld[:3, :3].dot(lightDir), pdf

def getBrdfPdf(cosVal):
	return cosVal / np.pi

def sampleBrdf(normal):
	r, theta = np.sqrt(sample()), 2 * np.pi * sample()
	x, y = r * np.cos(theta), r * np.sin(theta)
	z = np.sqrt(max(0, 1 - r ** 2))

	c = normal[2]
	if c == -1:
		R = -np.eye(3)
	else:
		v = np.cross(np.array([0, 0, 1]), normal)
		Mv = np.array([[0, -v[2], v[1]],
					   [v[2], 0, -v[0]],
					   [-v[1], v[0], 0]])
		R = np.eye(3) + Mv + Mv.dot(Mv) / (1 + c)
	return R.dot(np.array([x, y, z]))


# light
lightToWorld = RzMatrix(np.pi / 2.).dot(RyMatrix(220. / 180. * np.pi).dot(RzMatrix(170. / 180. * np.pi)))
envMap = EnvMap('stpeters_probe_latlong.exr', lightToWorld)

def worker(workingRows, wq, bq, fq):
	print 'threads start:', workingRows[0], '~', workingRows[-1]
	for y in workingRows:
		for x in range(resolution):
			pixelPos = y * resolution + x
			brdfContribution = np.zeros((brdfLen, 3))
			for pixelSampleIndex in range(pixelSampleNum):
				dx, dy = sample(), sample()
				cameraPoint = np.array([np.tan(fov / 2.) * (2. * float(x + dx) / resolution - 1.), np.tan(fov / 2.) * (1. - 2. * float(y + dy) / resolution), 1.])
				ray = (cameraToWorld.dot(np.array([0, 0, 0, 1])), cameraToWorld[:3, :3].dot(normalize(cameraPoint)))

				A = np.sum(ray[1] ** 2)
				B = 2 * np.dot(ray[0][:3], ray[1])
				C = np.sum(ray[0][:3] ** 2) - radius ** 2
				delta = B ** 2 - 4 * A * C
				if delta < 0:
					light, _ = envMap.worldDirToValue(ray[1])
					bq.put([pixelPos, light])
					# brdfBias[pixelPos] = brdfBias[pixelPos] + light
				else:
					t = (-B - np.sqrt(delta)) / (2 * A)
					hitPoint = ray[0][:3] + t * ray[1]
					normal = normalize(hitPoint)

					for lightSampleIndex in range(lightSampleNum):
						lightSample = sample()
						light, worldDir, lightPdf = envMap.getLight(lightSample)
						cosVal = normal.dot(worldDir)
						if cosVal > 0:
							brdfSlot = IDtoValidID(MERLToID(RusinkToMERL(DirectionsToRusink(-ray[1], worldDir, normal))))
							brdfPdf = getBrdfPdf(cosVal)
							brdfContribution[brdfSlot, :] += light * cosVal * lightSampleNum * lightPdf / ((lightSampleNum * lightPdf) ** 2 + (materialSampleNum * brdfPdf) ** 2)

					for materialSampleIndex in range(materialSampleNum):
						worldDir = sampleBrdf(normal)
						light, lightPdf = envMap.worldDirToValue(worldDir)
						cosVal = normal.dot(worldDir)
						if cosVal > 0:
							brdfSlot = IDtoValidID(MERLToID(RusinkToMERL(DirectionsToRusink(-ray[1], worldDir, normal))))
							brdfPdf = getBrdfPdf(cosVal)
							brdfContribution[brdfSlot, :] += light * cosVal * materialSampleNum * brdfPdf / ((lightSampleNum * lightPdf) ** 2 + (materialSampleNum * brdfPdf) ** 2)


			nonzeros = np.nonzero(brdfContribution[:, 0] != 0)[0]
			wq.put([pixelPos, np.ones((len(nonzeros),)) * pixelPos, nonzeros, brdfContribution[nonzeros, :]])
	fq.put(1)

def main():
	brdfBias = [np.array([0., 0., 0.])] * (resolution ** 2)
	rows = [None] * (resolution ** 2)
	cols = [None] * (resolution ** 2)
	Rchannel = [None] * (resolution ** 2)
	Gchannel = [None] * (resolution ** 2)
	Bchannel = [None] * (resolution ** 2)


	threads = [None] * threadsNum
	averageRows = float(resolution) / threadsNum
	weightQueue = Queue()
	biasQueue = Queue()
	flagQueue = Queue()
	for i in range(threadsNum):
		start, stop = int(i * averageRows), int((i + 1) * averageRows)
		if i == threadsNum - 1:
			stop = resolution
		threads[i] = Process(target=worker, args=(range(start, stop), weightQueue, biasQueue, flagQueue))
		threads[i].start()

	flags = 0
	while flags != threadsNum:
		while not flagQueue.empty():
			flagQueue.get()
			flags += 1

		while not biasQueue.empty():
			obj = biasQueue.get()
			brdfBias[obj[0]] = brdfBias[obj[0]] + obj[1]

		while not weightQueue.empty():
			obj = weightQueue.get()
			pixelPos = obj[0]
			rows[pixelPos] = obj[1]
			cols[pixelPos] = obj[2]
			Rchannel[pixelPos] = obj[3][:, 0]
			Gchannel[pixelPos] = obj[3][:, 1]
			Bchannel[pixelPos] = obj[3][:, 2]

	for i in range(threadsNum):
		threads[i].join()

	brdfBias = np.stack(brdfBias, axis=0) / pixelSampleNum
	np.save('weights/brdfBias.npy', brdfBias)

	rows = np.concatenate(rows)
	cols = np.concatenate(cols)
	Rchannel = np.concatenate(Rchannel) / pixelSampleNum
	Gchannel = np.concatenate(Gchannel) / pixelSampleNum
	Bchannel = np.concatenate(Bchannel) / pixelSampleNum
	brdfWeightR = ssp.csr_matrix((Rchannel, (rows, cols)), shape=(resolution ** 2, brdfLen))
	brdfWeightG = ssp.csr_matrix((Gchannel, (rows, cols)), shape=(resolution ** 2, brdfLen))
	brdfWeightB = ssp.csr_matrix((Bchannel, (rows, cols)), shape=(resolution ** 2, brdfLen))
	save_sparse_csr('weights/brdfWeightR.npz', brdfWeightR)
	save_sparse_csr('weights/brdfWeightG.npz', brdfWeightG)
	save_sparse_csr('weights/brdfWeightB.npz', brdfWeightB)
	# brdfBias = np.load('weights/brdfBias.npy')
	# brdfWeightR = load_sparse_csr('weights/brdfWeightR.npz')
	# brdfWeightG = load_sparse_csr('weights/brdfWeightG.npz')
	# brdfWeightB = load_sparse_csr('weights/brdfWeightB.npz')


	## test 
	brdf = readMERLBRDF('../../../brdf/aluminium.binary').reshape((-1, 3))[maskMap]
	image = (np.concatenate([brdfWeightR.dot(brdf[:, :1]), brdfWeightG.dot(brdf[:, 1:2]), brdfWeightB.dot(brdf[:, 2:])], axis=1) + brdfBias).reshape((resolution, resolution, 3))
	# image = brdfBias.reshape((resolution, resolution, 3))
	cv2.imwrite('test.png', image[:, :, ::-1] ** (1 / 2.2) * 255)


if __name__ == '__main__':
	freeze_support()
	main()
