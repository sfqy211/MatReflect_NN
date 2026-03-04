import streamlit as st
import os
from pathlib import Path

st.set_page_config(
    page_title="MatReflect_NN - 项目主页",
    page_icon="🏠",
    layout="wide"
)

st.title("基于神经网络的材质反射属性表达方法研究与实现")

st.markdown("""
### 项目简介
本项目旨在利用深度学习技术对材质的双向反射分布函数（BRDF）进行压缩与表达，并结合物理渲染引擎（Mitsuba）实现高质量的真实感渲染。

### 功能导航
请在左侧侧边栏选择相应的功能页面：

- **🎨 Mitsuba Render Tool**: 集成了批量渲染、格式转换、项目编译、量化评估及图像处理等核心工具。
- **🧠 Model Training**: 集成了 Neural-BRDF (Sztrajman et al. 2021) 与 HyperBRDF (Gokbudak et al. 2024) 两种主流材质神经网络表达方案。
- **📊 (规划中) 数据分析**: 材质数据的统计分析与可视化。

### 快速开始
1. 确保已配置好 Mitsuba 渲染器路径。
2. 准备好 MERL (.binary) 材质数据。
3. 进入 **Mitsuba Render Tool** 页面开始工作。

### 系统状态
- **项目根目录**: `d:\AHEU\GP\MatReflect_NN`
- **渲染器状态**: 检测中...
""")

root_dir = Path(__file__).parent
local_mitsuba = root_dir / "mitsuba" / "dist" / "mitsuba.exe"
default_mitsuba = Path(r"d:\mitsuba\dist\mitsuba.exe")

mitsuba_path = local_mitsuba if local_mitsuba.exists() else default_mitsuba
if mitsuba_path.exists():
    st.success(f"✅ 检测到 Mitsuba 渲染器: `{mitsuba_path}`")
else:
    st.warning(f"⚠️ 未检测到 Mitsuba 渲染器，请检查路径: `{mitsuba_path}`")

st.sidebar.success("请从上方选择一个页面开始。")
