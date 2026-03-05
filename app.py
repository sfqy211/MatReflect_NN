import streamlit as st
import os
from pathlib import Path

st.set_page_config(
    page_title="MatReflect_NN - 项目主页",
    page_icon="🏠",
    layout="wide"
)

st.title("基于神经网络的材质反射属性表达方法研究与实现")

root_dir = Path(__file__).parent
local_mitsuba = root_dir / "mitsuba" / "dist" / "mitsuba.exe"
default_mitsuba = Path(r"d:\mitsuba\dist\mitsuba.exe")

mitsuba_path = local_mitsuba if local_mitsuba.exists() else default_mitsuba
mitsuba_status = f"✅ 已检测到: `{mitsuba_path}`" if mitsuba_path.exists() else f"⚠️ 未检测到，请检查路径: `{mitsuba_path}`"

st.markdown(f"""
### 项目简介
本项目旨在利用深度学习技术对材质的双向反射分布函数（BRDF）进行压缩与表达，并结合物理渲染引擎（Mitsuba）实现高质量的真实感渲染。

### 功能导航
请在左侧侧边栏选择相应的功能页面：

- **🎨 Mitsuba Render Tool**: 提供 Mitsuba 渲染器的批量渲染、EXR 格式转换、Mitsuba 源码编译及实时日志监控等功能。
- **🧠 Model Training**: 支持 Neural-BRDF (Sztrajman et al. 2021) 与 HyperBRDF (Gokbudak et al. 2024) 两种材质神经网络表达方案的训练与转换。
- **📊 数据分析**: 提供渲染结果的图片预览、量化指标评估（PSNR/SSIM/Delta E）、网格拼图及对比图生成等分析工具。

### 快速开始
1. 确保已配置好 Mitsuba 渲染器路径。
2. 准备好 MERL (.binary) 材质数据。
3. 进入 **Mitsuba Render Tool** 页面开始渲染，或在 **Model Training** 页面训练新模型。

### 系统状态
- **项目根目录**: `{root_dir}`
- **渲染器状态**: {mitsuba_status}
""")

if mitsuba_path.exists():
    st.sidebar.success("🚀 渲染器就绪")
else:
    st.sidebar.warning("🛑 渲染器缺失")

st.sidebar.info("请从上方选择一个页面开始。")
