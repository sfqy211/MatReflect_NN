import numpy as np

def RGBtoHSI(rgbval):
	assert(rgbval.shape[1] == 3)
	I = rgbval.mean(axis=1)
	S = 1 - np.min(rgbval, axis=1) / I
	RminusG = rgbval[:, 0] - rgbval[:, 1]
	RminusB = rgbval[:, 0] - rgbval[:, 2]
	H = np.arccos(0.5 * (RminusG + RminusB) / np.sqrt(RminusG * RminusG + RminusB * (rgbval[:, 1] - rgbval[:, 2])))
	H[rgbval[:, 2] > rgbval[:, 1]] = 2 * np.pi - H[rgbval[:, 2] > rgbval[:, 1]]
	return I, S, H

def HSItoRGB(I, S, H):
	assert(I.shape[0] == S.shape[0] and I.shape[0] == H.shape[0])
	Hsector = np.floor(3 * H / (2 * np.pi))
	Hsector[Hsector >= 2] = 2
	Hremain = H - Hsector * 2 * np.pi / 3
	Rindex = (Hsector == 0)
	Gindex = (Hsector == 1)
	Bindex = (Hsector >= 2)

	RGB = np.zeros((I.shape[0], 3), dtype=np.float64)
	temp1 = I * (1 + S * np.cos(Hremain) / np.cos(np.pi / 3 - Hremain))
	RGB[Rindex, 0] = temp1[Rindex]
	RGB[Gindex, 1] = temp1[Gindex]
	RGB[Bindex, 2] = temp1[Bindex]

	temp2 = I * (1 - S)
	RGB[Rindex, 2] = temp2[Rindex]
	RGB[Gindex, 0] = temp2[Gindex]
	RGB[Bindex, 1] = temp2[Bindex]

	RGB[Rindex, 1] = 3 * I[Rindex] - RGB[Rindex, 0] - RGB[Rindex, 2]
	RGB[Gindex, 2] = 3 * I[Gindex] - RGB[Gindex, 0] - RGB[Gindex, 1]
	RGB[Bindex, 0] = 3 * I[Bindex] - RGB[Bindex, 1] - RGB[Bindex, 2]

	return RGB
