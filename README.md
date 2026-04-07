# MatReflect\_NN: 基于神经网络的材质反射属性表达方法研究与实现

## 🌟 项目简介

**MatReflect\_NN** 是一个集成传统物理渲染（Mitsuba）与现代深度学习技术（Neural-BRDF / HyperBRDF）的研究平台。本项目当前同时保留：

- V2：React + FastAPI 工作台，作为默认入口
- V1：Streamlit 旧版工作流，作为兼容兜底

项目目标仍然是探索高效的材质双向反射分布函数（BRDF）压缩与表达方法，并提供覆盖数据生成、模型训练、权重转换、渲染评估与结果分析的完整工具链。

***

## 🏗️ 架构概览

本项目当前采用 **V2 主工作台 + V1 兼容兜底** 的双入口结构，并继续使用 **多环境隔离 (Multi-Environment)** 策略，以解决不同工具组件之间复杂的依赖冲突（如 Python 2.7 编译环境、TensorFlow 2.4 与 PyTorch 1.8 的共存问题）。

### 核心模块

| 模块名称                       | 功能描述                                                                                       | 主要依赖环境                                              |
| :------------------------- | :----------------------------------------------------------------------------------------- | :-------------------------------------------------- |
| **🧭 V2 Workspace**        | React + FastAPI 主工作台，覆盖渲染、分析、模型管理与设置页。                                                     | `matreflect`                                        |
| **🎨 Mitsuba Render Tool** | 批量渲染 MERL 材质、EXR 转 PNG、Mitsuba 源码编译、实时日志监控。                                                | `matreflect` (渲染/转换)`mitsuba-build` (编译)            |
| **🧠 Model Training**      | **Neural-BRDF**: 基于 MLP 的单材质过拟合训练 (PyTorch/Keras)。**HyperBRDF**: 基于 HyperNetwork 的多材质泛化重建。 | `nbrdf-train` (Neural-BRDF) `hyperbrdf` (HyperBRDF) |
| **📊 Data Analysis**       | 渲染结果可视化对比、PSNR/SSIM/Delta E 量化评估、拼图生成。                                                     | `matreflect`                                        |
| **🖥️ Legacy Terminal**    | V1 Streamlit 中保留的网页终端，支持直接在宿主机 Shell 环境中运行命令，支持实时日志流与目录切换。                                 | 宿主 Shell (自动继承)                                     |

***

## 🛠️ 环境配置指南 (关键)

由于集成了多个异构系统，本项目**强烈建议**使用 Conda 进行环境管理。当前建议准备 **5 个** 关键环境，其中训练相关环境必须彼此隔离。

### 1. 主环境: `matreflect` (V2 Backend / V1 UI / Analysis)

这是当前默认工作环境，用于运行 V2 backend、V1 Streamlit 兜底入口，以及分析和渲染集成能力。

```bash
# 1. 创建环境 (Python 3.9)
conda create -n matreflect -c conda-forge python=3.9 mamba -y
conda activate matreflect

# 2. 安装 PyEXR (必须通过 Conda 安装以获取 OpenEXR 库支持)
mamba install -c conda-forge pyexr -y

# 3. 安装其余 Python 依赖
pip install -r requirements.txt
```

### 2. 编译环境: `mitsuba-build` (Mitsuba SCons)

仅用于编译 Mitsuba 0.6 源码（因其构建脚本依赖 Python 2.7）。

```bash
# 创建 Python 2.7 环境并安装 SCons 构建工具
conda create -n mitsuba-build python=2.7 scons -y
```

### 3. 训练环境 A: `nbrdf-train` (Neural-BRDF)

专用于 Neural-BRDF (Sztrajman et al. 2021) 的训练，需兼容旧版 TensorFlow 2.x 和 Keras。

```bash
# 1. 创建环境 (Python 3.8)
conda create -n nbrdf-train python=3.8 -y
conda activate nbrdf-train

# 2. 安装指定版本的依赖 (顺序很重要)
pip install numpy==1.19.5 tensorflow==2.4.1 keras==2.4.3 pandas matplotlib scikit-learn pillow scipy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 训练环境 B: `hyperbrdf` (HyperBRDF)

专用于 HyperBRDF (Gokbudak et al. 2024) 的训练与推理，需 PyTorch 和 TorchMeta 支持。

```bash
# 1. 创建环境 (Python 3.8)
conda create -n hyperbrdf python=3.8 -y
conda activate hyperbrdf

# 2. 安装 PyTorch (根据您的 CUDA 版本选择，以下为 CPU 示例)
# 如需 GPU: pip install torch==1.8.1+cu111 torchvision==0.9.1+cu111 ...
pip install torch==1.8.1+cpu torchvision==0.9.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

# 3. 安装其余依赖
pip install matplotlib==3.3.4 numpy==1.21.6 pandas==1.2.2 scikit_learn==1.1.3 PyYAML==6.0 torchmeta==1.8.0
```

## 🚀 启动与使用

### 启动 V2 工作台

推荐直接使用统一脚本：

```powershell
scripts\start_v2_dev.ps1
```

生产模式：

```powershell
scripts\start_v2_prod.ps1
```

更多切换说明见：

- `V2_QUICK_START.md`
- `V2_CUTOVER_GUIDE.md`
- `V1_V2_COMPARISON.md`

### 启动 V1 兜底界面

如需旧版终端或尚未迁移的历史操作面板，再启动 Streamlit：

```bash
cd D:\AHEU\GP\MatReflect_NN
conda activate matreflect
streamlit run app.py
```

### 功能使用流程

1. **准备数据**:
   - 将 `.binary` 格式的 MERL 材质文件放入 `data/inputs/binary`。
   - (可选) 将 `.fullbin` 采样文件放入 `data/inputs/fullbin`。
2. **渲染基准图 (Ground Truth)**:
   - 优先进入 V2 的 **渲染可视化** 模块。
   - 使用“批量选择工具”选中材质文件。
   - 点击“开始批量渲染”生成参考图像。
3. **训练神经材质**:
   - 优先进入 V2 的 **网络模型管理** 模块。
   - **Neural-BRDF**: 选择材质 -> 点击“开始 PyTorch 训练” -> 生成 `.npy` 权重。
   - **HyperBRDF**: 训练或选择 checkpoint -> 点击“启动参数提取” -> 生成 `.pt` 参数 -> 点击“执行重建转换” -> 生成 `.fullbin`。
4. **评估与分析**:
   - 优先进入 V2 的 **材质表达结果分析** 模块。
   - 选择参考图与预测图。
   - 查看 PSNR/SSIM 指标与误差热力图。

***

## 📁 目录结构说明

```
MatReflect_NN/
├── frontend/               # V2 React 前端
├── backend/                # V2 FastAPI 后端
├── app.py                  # V1 Streamlit 入口
├── requirements.txt        # 主环境依赖列表
├── pages/                  # V1 功能页面
│   ├── 1_Mitsuba_Render_Tool.py
│   ├── 2_Model_Training.py
│   ├── 3_Data_Analysis.py
│   ├── 4_Terminal.py
│   └── _modules/           # V1 页面共享逻辑与后端 Action
├── data/                   # 数据存放区
│   ├── inputs/             # 输入数据 (brdfs, fullbin, npy)
│   └── outputs/            # 输出结果 (renderings, weights)
├── scene/                  # Mitsuba 场景文件与配置
├── Neural-BRDF/            # Neural-BRDF 子模块源码
└── HyperBRDF/              # HyperBRDF 子模块源码
```

## ❓ 常见问题 (FAQ)

**Q: 为什么需要这么多环境？**
A: 本项目整合了不同时期的研究代码。Mitsuba 0.6 需要 Python 2.7；Neural-BRDF 基于 TensorFlow 2.4；HyperBRDF 基于 PyTorch 1.8。为了保证代码的原始复现性与稳定性，使用独立环境是最安全的策略。

**Q: 现在默认该用哪个入口？**
A: 默认使用 V2，即 `scripts\start_v2_dev.ps1` 或 `scripts\start_v2_prod.ps1`。只有在需要旧版网页终端或尚未迁移的历史入口时，再使用 `streamlit run app.py`。

**Q: 可以在网页终端里切换环境吗？**
A: 可以，但这是 V1 Streamlit 里的 legacy 功能。网页终端直接运行在宿主机 Shell 中，您可以输入 `conda activate <env_name>` 来切换环境，或者直接指定环境的 Python 路径来运行脚本。

**Q: 渲染器未检测到怎么办？**
A: 请先在 V2 的“设置”页检查后端状态与路径信息，确认 `mitsuba.exe` 是否可被检测到，或者将其添加到系统环境变量中。默认路径检测位置为项目目录下的 `mitsuba/dist/mitsuba.exe`。
