import streamlit as st
from pages._modules import get_project_root, get_mitsuba_paths

st.set_page_config(page_title="MatReflect_NN - 项目主页", page_icon="🏠", layout="wide")

st.title("基于神经网络的材质反射属性表达方法研究与实现")

root_dir = get_project_root()
_, mitsuba_path, _ = get_mitsuba_paths(root_dir)
mitsuba_status = (
    f"✅ 已检测到: `{mitsuba_path}`"
    if mitsuba_path.exists()
    else f"⚠️ 未检测到，请检查路径: `{mitsuba_path}`"
)

st.markdown(
    f"""
### 🌟 项目简介
本项目是一个集成了传统物理渲染与现代深度学习技术的综合性研究平台，旨在探索高效的材质反射属性（BRDF）表达方法。项目不仅提供了完整的 Mitsuba 渲染流程，还集成了 Neural-BRDF 与 HyperBRDF 两种前沿的神经网络材质压缩方案，并配套了完善的数据分析与可视化工具。

### 🧭 功能模块导航

#### 1. 🎨 **Mitsuba Render Tool (渲染工具)**
   - **核心功能**: 批量渲染 MERL 材质、自动化 EXR 转 PNG、Mitsuba 源码编译。
   - **适用场景**: 生成 Ground Truth 数据集、测试材质渲染效果。
   - **依赖环境**: 
     - 渲染: `matreflect` (本环境)
     - 编译: `mitsuba-build` (Python 2.7 + SCons)

#### 2. 🧠 **Model Training (模型训练)**
   - **核心功能**: 
     - **Neural-BRDF**: 基于 MLP 的单材质过拟合训练 (PyTorch/Keras)。
     - **HyperBRDF**: 基于 HyperNetwork 的多材质泛化重建。
   - **适用场景**: 训练神经网络材质模型、从稀疏采样中恢复材质。
   - **依赖环境**:
     - Neural-BRDF: `nbrdf-train` (TensorFlow 2.4.1)
     - HyperBRDF: `hyperbrdf` (PyTorch + TorchMeta)

#### 3. 📊 **Data Analysis (数据分析)**
   - **核心功能**: 渲染结果可视化对比、PSNR/SSIM/Delta E 量化评估、拼图生成。
   - **适用场景**: 评估神经网络材质模型的渲染质量与误差分析。
   - **依赖环境**: `matreflect` (本环境)

#### 4. 🖥️ **Terminal (网页终端)**
   - **核心功能**: 在网页端直接运行命令行指令，支持实时日志与环境切换。
   - **适用场景**: 手动运行脚本、调试环境、查看系统状态。

---

### 🚀 快速上手指南
1. **环境检查**: 确保您已安装 Conda，并根据 `README.md` 配置好了所有 4 个虚拟环境。
2. **数据准备**: 将您的 MERL (.binary) 材质文件放入 `data/inputs/binary` 目录。
3. **开始渲染**: 前往 **Mitsuba Render Tool** 页面，批量生成参考图像。
4. **训练模型**: 前往 **Model Training** 页面，选择一种方案进行训练。
5. **评估结果**: 前往 **Data Analysis** 页面，对比真实渲染图与神经网络预测图。

### ⚙️ 系统状态概览
- **项目根目录**: `{root_dir}`
- **渲染器状态**: {mitsuba_status}
"""
)

if mitsuba_path.exists():
    st.sidebar.success("🚀 渲染器就绪")
else:
    st.sidebar.warning("🛑 渲染器缺失")

st.sidebar.info("请从左侧导航栏选择一个页面开始工作。")
