import os.path as path
import numpy as np
import scipy.io as sio

# %% Helper Functions

def normalize(x):
    if(len(np.shape(x)) == 1):
        return x / np.linalg.norm(x)
    else:
        return x / np.linalg.norm(x,axis=1)[:,np.newaxis]

def dot(a, b):
    if(len(np.shape(a)) == 1):
        return a.dot(b)
    else:
        return np.sum(a * b, axis=1, keepdims=True)

def Fresnel(f0, u):
    return pow(1-u, 5).dot(1-f0) + f0

def Beckmann(m, t):
    M = m ** 2;
    T = t ** 2;
    return np.exp( (T - 1) / (T.dot(M)) ) / ((np.pi * T * T).dot(M))

# %% Utility data
directions = sio.loadmat(path.dirname(__file__) + '/../data/directions.mat')
L, V = normalize(directions['L']), normalize(directions['V'])
N = np.zeros_like(L)
N[:, 2] = 1.
H = normalize(L + V)

NdotH = dot(N, H)
VdotH = dot(V, H)
NdotL = dot(N, L)
NdotV = dot(N, V)
NdotH2 = NdotH ** 2
NdotLTan2 = np.abs((1 - NdotL ** 2) / (NdotL ** 2))
NdotVTan2 = np.abs((1 - NdotV ** 2) / (NdotV ** 2))

# %% BRDF functions

# Specular models

def GGX(rho, alpha, ior):
    assert(rho.shape[0] == 1)
    assert(alpha.shape[0] == 1)
    assert(ior.shape[0] == 1)
    global L, V, N, H, NdotH, VdotH, NdotL, NdotV, NdotH2, NdotLTan2, NdotVTan2

    alpha2 = alpha ** 2;
    D = alpha2 / (np.pi * (1 + NdotH2.dot(alpha2 - 1)) ** 2);
    G = 4 / ( (1 + np.sqrt(1 + NdotLTan2.dot(alpha2))) * (1 + np.sqrt(1 + NdotVTan2.dot(alpha2))) );
    g = np.sqrt(ior ** 2 - 1 + VdotH ** 2);
    F = 0.5 * ((g - VdotH) / (g + VdotH)) ** 2 * (1 + ((VdotH * (g + VdotH) - 1) / (VdotH * (g - VdotH) + 1)) ** 2);

    brdf = rho * D * G * F / (4 * NdotL * NdotV)
    # brdf[NdotL[:, 0] < 0] = 0
    # brdf[NdotV[:, 0] < 0] = 0

    return brdf

def cookTorrance(rho, m, f0):
    assert(rho.shape[0] == 1)
    assert(m.shape[0] == 1)
    assert(f0.shape[0] == 1)
    global L, V, NdotH, VdotH, NdotL, NdotV

    F = Fresnel(f0, VdotH);
    D = Beckmann(m, NdotH);
    G = 2 * NdotH / VdotH * np.min(np.concatenate([NdotL, NdotV], axis=1), axis=1, keepdims=True)
    G[G < 1] = 1

    brdf = rho * D * G * F / (4 * NdotL * NdotV)
    # brdf[NdotL[:, 0] < 0] = 0
    # brdf[NdotV[:, 0] < 0] = 0

    return brdf

# Diffuse models

def lambertian(rho):
    assert(rho.shape[0] == 1)
    return (1. / np.pi) * np.ones((L.shape[0], 1)).dot(rho)
