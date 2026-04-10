# MatReflect_NN

`MatReflect_NN` 是一个运行在 Windows 本机上的材质研究工作台，当前统一采用 V2 架构：

- 前端：React + Vite
- 后端：FastAPI + WebSocket
- 训练与推理：Conda 多环境调度

项目围绕以下闭环展开：

1. 使用 Mitsuba 0.6 渲染 MERL / FullBin / NBRDF 材质。
2. 使用 Neural-BRDF 训练 `.binary -> .npy`。
3. 使用 HyperBRDF 完成 `.binary -> checkpoint.pt -> .pt -> .fullbin`。
4. 在工作台内完成渲染预览、量化评估、网格拼图、对比拼图和模型管理。

## 1. 当前入口

当前仓库不再保留 V1 / Streamlit 入口，默认只使用 V2：

```powershell
scripts\start_v2_dev.ps1
scripts\start_v2_prod.ps1
```

更多说明见：

- [V2_QUICK_START.md](/d:/AHEU/GP/MatReflect_NN/V2_QUICK_START.md)
- [V2_CUTOVER_GUIDE.md](/d:/AHEU/GP/MatReflect_NN/V2_CUTOVER_GUIDE.md)
- [V1_V2_COMPARISON.md](/d:/AHEU/GP/MatReflect_NN/V1_V2_COMPARISON.md)

## 2. 关键环境

推荐使用 Conda，多环境隔离如下：

### `matreflect`

用于：

- V2 backend
- 渲染调度
- 分析模块

建议安装：

```powershell
conda create -n matreflect -c conda-forge python=3.9 mamba -y
conda activate matreflect
mamba install -c conda-forge pyexr -y
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### `mitsuba-build`

用于 Mitsuba 0.6 的 SCons 编译：

```powershell
conda create -n mitsuba-build python=2.7 scons -y
```

### `nbrdf-train`

用于 Neural-BRDF 训练与 `h5 -> npy` 转换：

```powershell
conda create -n nbrdf-train python=3.8 -y
conda activate nbrdf-train
pip install numpy==1.19.5 tensorflow==2.4.1 keras==2.4.3 pandas matplotlib scikit-learn pillow scipy
```

### `hyperbrdf`

用于 HyperBRDF 训练、参数提取与解码：

```powershell
conda create -n hyperbrdf python=3.8 -y
conda activate hyperbrdf
pip install torch==1.8.1+cpu torchvision==0.9.1+cpu -f https://download.pytorch.org/whl/torch_stable.html
pip install matplotlib==3.3.4 numpy==1.21.6 pandas==1.2.2 scikit_learn==1.1.3 PyYAML==6.0 torchmeta==1.8.0
```

## 3. 启动方式

### 开发模式

```powershell
scripts\start_v2_dev.ps1
```

作用：

- 启动 FastAPI 后端
- 启动 Vite 前端开发服务器

默认地址：

- 前端：`http://127.0.0.1:5173`
- API：`http://127.0.0.1:8000/api/v1`
- 文档：`http://127.0.0.1:8000/docs`

### 生产模式

```powershell
scripts\start_v2_prod.ps1
```

作用：

1. 构建 `frontend/dist`
2. 启动 FastAPI
3. 由后端直接托管前端静态资源

默认地址：

- 应用：`http://127.0.0.1:8000`
- 文档：`http://127.0.0.1:8000/docs`

## 4. 主要功能

### 网络模型管理

- 内置 Neural-BRDF / HyperBRDF 模型注册项
- 支持自定义模型注册与删除
- 支持训练任务、参数提取、`pt -> fullbin`
- 支持独立 `H5 -> NPY` 转换
- 支持模型运行记录扫描

### 渲染可视化

- 支持 `.binary`、`.fullbin`、`.npy` 三类输入
- 支持 Mitsuba XML 场景切换
- 支持 EXR -> PNG 自动转换
- 支持一键重建后渲染

### 材质表达结果分析

- 图片预览
- 图片删除与对应 EXR 清理
- PSNR / SSIM / Delta E 量化评估
- 网格拼图
- 对比拼图
- 自定义分析目录与输出目录

### 设置页

- 深浅主题切换
- 系统摘要
- Mitsuba 编译辅助入口

## 5. 目录结构

```text
MatReflect_NN/
├── frontend/                 # V2 React 前端
├── backend/                  # V2 FastAPI 后端
├── scripts/                  # 启动脚本、桌面封装脚本等
├── data/                     # 输入数据与输出结果
├── scene/                    # Mitsuba 场景资源
├── Neural-BRDF/              # Neural-BRDF 上游代码
├── HyperBRDF/                # HyperBRDF 上游代码
├── README.md
├── V2_QUICK_START.md
├── V2_CUTOVER_GUIDE.md
└── V1_V2_COMPARISON.md
```

## 6. 常见问题

### 默认应该使用哪个入口？

默认只使用 V2：

- `scripts\start_v2_dev.ps1`
- `scripts\start_v2_prod.ps1`

### 为什么需要多个 Conda 环境？

因为 Mitsuba 编译、Neural-BRDF、HyperBRDF 依赖栈差异很大，强行放在同一个环境里会导致版本冲突和不可复现问题。

### 如果 Mitsuba 没有被检测到怎么办？

先打开 V2 的设置页，检查系统摘要和路径状态。默认检测位置为项目目录下的 `mitsuba/dist/mitsuba.exe`。
