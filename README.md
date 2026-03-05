# MatReflect_NN

本目录包含基于 Streamlit 的一体化工具，将 Mitsuba 渲染、EXR 转换、编译、量化评估与图像工具拆分为多个小页面，便于独立操作与后续扩展。

## 启动方式

在命令行进入该目录后执行：

```bash
cd D:\AHEU\GP\MatReflect_NN
conda activate matreflect
streamlit run app.py
```

## 页面结构

本项目采用多页面架构，各页面功能如下：

- **🎨 Mitsuba Render Tool**: 核心渲染工具。支持批量渲染（BRDF / FullBin / NPY 格式）、EXR 格式转换、Mitsuba 源码编译及实时日志监控。
- **🧠 Model Training**: 模型训练模块。支持 Neural-BRDF (PyTorch/Keras) 与 HyperBRDF (Advanced) 方案的训练、权重转换。
- **📊 Data Analysis**: 数据分析与评估。提供图片结果预览、量化评估 (PSNR / SSIM / Delta E)、网格拼图及对比图生成工具。

## 依赖环境

本项目采用多环境管理策略，以解决不同组件（Mitsuba 编译、深度学习训练、Web 交互）之间的库版本冲突。

### 1. 主环境: `matreflect` (用于 Streamlit UI)

此环境运行主应用及图像处理工具。

```bash
# 创建环境
conda create -n matreflect -c conda-forge python=3.9 mamba -y
conda activate matreflect

# 安装 PyEXR (建议使用 mamba)
mamba install -c conda-forge pyexr -y

# 安装其余依赖
pip install -r requirements.txt
```

### 2. 专项环境: `mitsuba-build` (用于 Mitsuba 源码编译)

由于 Mitsuba 0.6 的 SCons 构建脚本基于 Python 2.7，必须使用独立环境。

```bash
# 创建环境
conda create -n mitsuba-build python=2.7 scons -y
```

### 3. 专项环境: `nbrdf-train` (用于 Neural-BRDF 训练)

为了兼容旧版 TensorFlow (2.4.1) 和 Keras API，建议使用此隔离环境。

```bash
# 1. 创建空环境
conda create -n nbrdf-train python=3.8 -y
conda activate nbrdf-train

# 2. 通过 pip 安装指定版本的兼容包 (注意：必须严格按顺序执行)
pip install numpy==1.19.5 tensorflow==2.4.1 keras==2.4.3 pandas matplotlib scikit-learn pillow scipy -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 核心库清单 (Main Env)
- **UI/Web**: streamlit
- **Deep Learning**: torch, torchvision (HyperBRDF 基础)
- **Image Processing**: opencv-python, scikit-image, pillow, scipy, pyexr
- **Data Analysis**: numpy, pandas, matplotlib
- **Build Tools**: vswhere

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
