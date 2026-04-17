# Connecting Measured BRDFs to Analytic

本目录在当前工作区中的运行方式如下。

## 目录约定

- 项目根目录：`D:\AHEU\GP\MatReflect_NN`
- 代码目录：`D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code`
- 材质目录：`D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\brdf`

说明：

- `brdf` 已准备好，作为输入材质目录使用。
- 所有脚本都必须在各自所在目录内执行，不能在项目根目录直接运行。

## 环境

推荐环境：`conda + Python 2.7`

当前已验证可用：

- 环境名：`measured-brdf-py27`
- Python：`2.7.18`
- OpenCV：`3.2.0`
- NumPy：`1.13.3`
- SciPy：`1.2.1`
- scikit-learn：`0.20.3`

已执行过的关键步骤：

```powershell
conda create -n measured-brdf-py27 python=2.7 numpy scipy scikit-learn matplotlib requests pip
conda activate measured-brdf-py27
conda install -n measured-brdf-py27 -c conda-forge "opencv=3.2.0" "numpy=1.13"
```

验证：

```powershell
python -c "import cv2; print(cv2.__version__)"
python -c "import numpy, scipy, sklearn; print(numpy.__version__, scipy.__version__, sklearn.__version__)"
```

## 先装 MATLAB Engine

这一步没通过前，不要继续跑主脚本。

```powershell
conda activate measured-brdf-py27
cd "D:\Program Files\MATLAB\R2022b\extern\engines\python"
python setup.py install
python -c "import matlab.engine; print('matlab engine ok')"
```

## 运行顺序

### 1. 生成基础数据

```powershell
conda activate measured-brdf-py27
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\_util
python generateData.py
```

输出：

- `code\_util\data\maskMap.npy`
- `code\_util\data\directions.mat`
- `code\_util\data\cosMap.npy`
- `code\_util\data\cosMap.mat`
- `code\_util\data\volumnWeight.mat`

说明：

- 首次运行会先生成上述基础文件。
- 如果 `fastrender\weights` 还不存在，脚本会跳过 `originalImages.npy`。

### 2. 生成渲染权重

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\_util\fastrender
python renderMat.py
```

输出：

- `weights\brdfBias.npy`
- `weights\brdfWeightR.npz`
- `weights\brdfWeightG.npz`
- `weights\brdfWeightB.npz`

### 3. 生成 `brdfWeightMean.npz` 和 `renderSlice.mat`

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\_util\fastrender
python -c "from transform import load_sparse_csr, save_sparse_csr; R=load_sparse_csr('weights/brdfWeightR.npz'); G=load_sparse_csr('weights/brdfWeightG.npz'); B=load_sparse_csr('weights/brdfWeightB.npz'); save_sparse_csr('weights/brdfWeightMean.npz', (R + G + B) / 3.0)"
python slice.py
```

### 4. 回到 `_util` 补 `originalImages.npy`

权重生成后，再跑一次：

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\_util
python generateData.py
```

这次会补出：

- `code\_util\data\originalImages.npy`

### 5. 跑 `diffspec`

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\diffspec
python diffspecSeparation.py
```

首次运行前需要先改两处：

- 把

```python
colorPsnrVals = np.load('%s/colorPsnrVals.npy'%(writeDataDir)).item()
```

- 改成

```python
colorPsnrVals = {}
```

- 注释掉文件末尾这几行：

```python
colorPsnrVals = np.load('%s/colorPsnrVals.npy'%(writeDataDir))
colorPsnrVals.item()['brdf1'].mean()
colorPsnrVals.item()['brdf2'.mean()
colorPsnrVals.item()['image1'].mean()
colorPsnrVals.item()['image2'].mean()
```

### 6. 跑 `pca`

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\pca
python pcaAnalysis.py
```

运行前处理一处：

- 注释掉这几行，或者先补 `writeBrdf` 定义：

```python
index = brdfList.index('specular-orange-phenolic')
writeBrdf[maskMap] = diffPcaRecon1[:, index:index+1].dot(colorAll[:1, :, index]) + specMapPcaRecon3[:, index:index+1].dot(colorAll[1:, :, index])
saveMERLBRDF('%s_diff1spec3.binary'%brdfList[index], writeBrdf)
```

### 7. 跑 `connect`

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\connect
python connect.py
```

### 8. 跑 `edit`

```powershell
cd D:\AHEU\GP\MatReflect_NN\Connecting_measured_brdfs_to_analytic\code\edit
python edit.py
```

## 最小检查项

如果中途报错，优先检查：

- `matlab.engine` 是否可导入
- `code\_util\data\` 是否已生成
- `code\_util\fastrender\weights\` 是否已生成
- 是否在脚本所在目录运行
- 是否使用 `measured-brdf-py27`
