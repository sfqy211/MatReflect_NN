# MatReflect_NN: 基于神经网络的材质反射属性表达方法研究与实现

## 🌟 项目简介

**MatReflect_NN** 是一个基于 Streamlit 开发的一体化研究平台，集成了传统物理渲染（Mitsuba）与现代深度学习技术（Neural-BRDF / HyperBRDF）。本项目旨在探索高效的材质双向反射分布函数（BRDF）压缩与表达方法，并提供了一套完整的工具链，涵盖数据生成、模型训练、权重转换、渲染评估与结果分析。

---

## 🏗️ 架构概览

本项目采用 **多页面架构 (Multi-Page App)** 与 **多环境隔离 (Multi-Environment)** 策略，以解决不同工具组件之间复杂的依赖冲突（如 Python 2.7 编译环境、TensorFlow 2.4 与 PyTorch 1.8 的共存问题）。

### 核心模块

| 模块名称 | 功能描述 | 主要依赖环境 |
| :--- | :--- | :--- |
| **🎨 Mitsuba Render Tool** | 批量渲染 MERL 材质、EXR 转 PNG、Mitsuba 源码编译、实时日志监控。 | `matreflect` (渲染/转换)<br>`mitsuba-build` (编译) |
| **🧠 Model Training** | **Neural-BRDF**: 基于 MLP 的单材质过拟合训练 (PyTorch/Keras)。<br>**HyperBRDF**: 基于 HyperNetwork 的多材质泛化重建。 | `nbrdf-train` (Neural-BRDF)<br>`hyperbrdf` (HyperBRDF) |
| **📊 Data Analysis** | 渲染结果可视化对比、PSNR/SSIM/Delta E 量化评估、拼图生成。 | `matreflect` |
| **🖥️ Terminal** | 内置网页终端，支持直接在宿主机 Shell 环境中运行命令，支持实时日志流与目录切换。 | 宿主 Shell (自动继承) |

---

## 🛠️ 环境配置指南 (关键)

由于集成了多个异构系统，本项目**强烈建议**使用 Conda 进行环境管理。请严格按照以下步骤配置 **4 个** 独立的虚拟环境。

### 1. 主环境: `matreflect` (Web UI & Analysis)
这是运行 Streamlit 主程序的环境，也是默认的交互环境。

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

---

## 🚀 启动与使用

### 启动主程序
请始终在 `matreflect` 环境下启动 Streamlit 应用：

```bash
cd D:\AHEU\GP\MatReflect_NN
conda activate matreflect
streamlit run app.py
```

### 功能使用流程

1.  **准备数据**:
    *   将 `.binary` 格式的 MERL 材质文件放入 `data/inputs/brdfs`。
    *   (可选) 将 `.fullbin` 采样文件放入 `data/inputs/fullbin`。

2.  **渲染基准图 (Ground Truth)**:
    *   进入 **Mitsuba Render Tool** 页面。
    *   使用“批量选择工具”选中材质文件。
    *   点击“开始批量渲染”生成参考图像。

3.  **训练神经材质**:
    *   进入 **Model Training** 页面。
    *   **Neural-BRDF**: 选择材质 -> 点击“开始 PyTorch 训练” -> 生成 `.npy` 权重。
    *   **HyperBRDF**: 选择材质 -> 点击“启动参数提取” -> 生成 `.pt` 参数 -> 点击“执行重建转换” -> 生成 `.fullbin`。

4.  **评估与分析**:
    *   进入 **Data Analysis** 页面。
    *   选择参考图与预测图。
    *   查看 PSNR/SSIM 指标与误差热力图。

---

## 📁 目录结构说明

```
MatReflect_NN/
├── app.py                  # Streamlit 入口主程序
├── requirements.txt        # 主环境依赖列表
├── pages/                  # 功能页面
│   ├── 1_Mitsuba_Render_Tool.py
│   ├── 2_Model_Training.py
│   ├── 3_Data_Analysis.py
│   ├── 4_Terminal.py
│   └── _modules/           # 页面共享逻辑与后端 Action
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

**Q: 可以在网页终端里切换环境吗？**
A: 可以。网页终端直接运行在宿主机 Shell 中，您可以输入 `conda activate <env_name>` 来切换环境，或者直接指定环境的 Python 路径来运行脚本（工具内部已自动处理了大部分跨环境调用）。

**Q: 渲染器未检测到怎么办？**
A: 请在“全局配置”侧边栏中手动输入正确的 `mitsuba.exe` 路径，或者将其添加到系统环境变量中。默认路径检测位置为项目目录下的 `mitsuba/dist/mitsuba.exe`。
