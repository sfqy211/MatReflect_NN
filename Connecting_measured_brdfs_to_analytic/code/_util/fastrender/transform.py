import numpy as np
from numpy.linalg import norm
import scipy.sparse as ssp

def lookAt(origin, target, up):
	origin = np.array(origin)
	target = np.array(target)
	up = np.array(up)

	direction = target - origin
	direction = direction / norm(direction)
	left = np.cross(up, direction)
	left = left / norm(left)
	newUp = np.cross(direction, left)

	matrix = np.array([
		[left[0], newUp[0], direction[0], origin[0]],
		[left[1], newUp[1], direction[1], origin[1]],
		[left[2], newUp[2], direction[2], origin[2]],
		[0, 0, 0, 1],
		])

	return matrix

def RxMatrix(theta):
	return np.array([[1,0,0],[0,np.cos(theta),-np.sin(theta)],[0,np.sin(theta),np.cos(theta)]]) 

def RyMatrix(theta):
	return np.array([[np.cos(theta), 0, np.sin(theta)],[0,1,0],[-np.sin(theta),0,np.cos(theta)]])

def RzMatrix(theta):
	return np.array([[np.cos(theta), -np.sin(theta), 0],[np.sin(theta), np.cos(theta), 0],[0,0,1]])


#Normalize vector(s)
def normalize(x):
	if(len(np.shape(x)) == 1):
		return x/norm(x)
	else:
		return x/norm(x,axis=1)[:,np.newaxis]


#Convert two direction vectors to rus-coords
#In:    Direction vectors to view/lightsource
#Out:   Rusinkiewicz coordinates (phi_d, theta_h, theta_d)  [rad]
def DirectionsToRusink(a,b,norm):
	a = np.reshape(normalize(a),(3,))
	b = np.reshape(normalize(b),(3,))
	norm = np.reshape(normalize(norm),(3,))
	H = normalize((a+b)/2)
	theta_h = np.arccos(np.clip(H.dot(norm), -1, 1))
	theta_d = np.arccos(np.clip(H.dot(a), -1, 1))
	phi_d = np.arccos(np.clip(normalize(H * norm.dot(H) - norm).dot(normalize(b-a)), -1, 1))

	return np.array([phi_d,theta_h,theta_d])

BRDFSHAPE = (180,90,90)
maskMap = np.load('../data/maskMap.npy')
cumMaskMap = np.cumsum(maskMap)-1
def RusinkToMERL(rusinkCoords):
	shp = BRDFSHAPE
	coords = np.array(np.reshape(rusinkCoords,(-1,3)))
	coords[:,0] = np.clip(np.floor(coords[:,0]/(np.pi)*shp[0]),0,shp[0]-1)
	coords[:,1] = np.clip(np.floor(np.sqrt(coords[:,1]/(np.pi/2))*shp[1]),0,shp[1]-1)
	coords[:,2] = np.clip(np.floor(coords[:,2]/(np.pi/2)*shp[2]),0,shp[2]-1)
	return coords

def MERLToID(coord):
	coord = np.reshape(coord,(-1,3)).astype(int)
	return np.ravel_multi_index(np.transpose(coord),BRDFSHAPE)

def IDtoValidID(Id):
	ValIds = cumMaskMap[Id]
	return ValIds

def readMERLBRDF(filename):
	"""Reads a MERL-type .binary file, containing a densely sampled BRDF
	
	Returns a 4-dimensional array (phi_d, theta_h, theta_d, channel)"""
	print "Loading MERL-BRDF: ",filename
	try: 
		f = open(filename, "rb")
		dims = np.fromfile(f,np.int32,3)
		vals = np.fromfile(f,np.float64,-1)
		f.close()
	except IOError:
		print "Cannot read file:", path.basename(filename)
		return
		
	BRDFVals = np.swapaxes(np.reshape(vals,(dims[2], dims[1], dims[0], 3),'F'),1,2)
	BRDFVals *= (1.00/1500,1.15/1500,1.66/1500) #Colorscaling
	tolerance = -0.05
	BRDFVals[(BRDFVals<0) * (BRDFVals>=tolerance)] = 0
	BRDFVals[BRDFVals<tolerance] = -1
	
	return BRDFVals

def save_sparse_csr(filename, array):
	np.savez(filename, data=array.data, indices=array.indices, indptr=array.indptr, shape=array.shape )

def load_sparse_csr(filename):
    loader = np.load(filename)
    return ssp.csr_matrix((loader['data'], loader['indices'], loader['indptr']), shape=loader['shape'])
