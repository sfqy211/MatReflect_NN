# MatReflect_NN

本目录包含基于 Streamlit 的一体化工具，将 Mitsuba 渲染、EXR 转换、编译、量化评估与图像工具拆分为多个小页面，便于独立操作与后续扩展。

## 启动方式

在命令行进入该目录后执行：

```bash
streamlit run app.py
```

## 页面结构

本项目采用多页面架构，各页面功能如下：

- **🎨 Mitsuba Render Tool**: 核心渲染工具。支持批量渲染（BRDF / FullBin / NPY 格式）、EXR 格式转换、Mitsuba 源码编译及实时日志监控。
- **🧠 Model Training**: 模型训练模块。支持 Neural-BRDF (PyTorch/Keras) 与 HyperBRDF (Advanced) 方案的训练、权重转换。
- **📊 Data Analysis**: 数据分析与评估。提供图片结果预览、量化评估 (PSNR / SSIM / Delta E)、网格拼图及对比图生成工具。

## 依赖环境

本项目依赖于 Conda 进行环境管理，以确保复杂的二进制库（如 PyEXR）能够正确安装。

### 1. 安装 Miniconda

如果你的系统中没有 Conda，强烈建议安装 **Miniconda**（而不是完整的 Anaconda），以获得一个干净、轻量的环境。

- **下载地址**: [Miniconda for Windows](https://docs.anaconda.com/free/miniconda/miniconda-install/#windows-install-or-update)
- **安装选项**: 推荐为 "Just Me" 安装，并且 **不要** 勾选 "Add Miniconda3 to my PATH"。

安装完成后，请使用 "Anaconda Prompt (miniconda3)" 来执行后续所有命令。

### 2. (推荐) 使用 Mamba 创建环境并安装

Conda 在解析复杂的依赖关系时可能会非常缓慢。我们强烈推荐在创建环境时就直接安装 Mamba（一个用 C++ 实现的 Conda 加速器），以获得极速的安装体验。

```bash
# 1. 创建环境，同时从 conda-forge 安装 python 和 mamba
# (此步骤可能需要等待几分钟，但比后续安装要快得多)
conda create -n matreflect -c conda-forge python=3.9 mamba

# 2. 激活新环境
conda activate matreflect

# 3. 使用 Mamba 安装 PyEXR (现在 mamba 命令已可用)
mamba install -c conda-forge pyexr

# 4. 安装其余依赖
pip install -r requirements.txt
```

### 3. (备选) 使用原生 Conda 安装

如果你不想安装 Mamba，也可以使用原生 Conda，但请有心理准备，依赖解析步骤可能会非常耗时。

```bash
# 1. 创建并激活环境
conda create -n matreflect python=3.9
conda activate matreflect

# 2. 安装 PyEXR (此步骤可能耗时较长)
conda install -c conda-forge pyexr

# 3. 安装其余依赖
pip install -r requirements.txt
```

### 核心库清单
- **UI/Web**: streamlit
- **Deep Learning**: tensorflow, keras, protobuf (<=3.20.x), torch, torchvision
- **Image Processing**: opencv-python, scikit-image, pillow, scipy, pyexr
- **Data Analysis**: numpy, pandas, matplotlib
- **Build Tools**: scons, vswhere

## 全局配置说明

左侧导航栏包含全局配置：

- 项目根目录：默认 `d:\AHEU\GP\MatReflect_NN`
- Mitsuba 目录：默认 `d:\mitsuba\dist`
- Mitsuba 可执行文件 / Mtsutil 可执行文件
- 场景 XML：默认指向 `scene\scene_merl.xml`

## 后续开发建议

可按以下方向继续扩展：

- 结果可视化分析报表一键导出
- 增加更多的材质预览模板（基于 Mitsuba 不同的测试场景）
- 引入自动化模型评估流水线（训练完成后自动进行渲染与评估）
