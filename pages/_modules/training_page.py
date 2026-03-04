import streamlit as st
from .training_neural_tab import render_neural_brdf_tab
from .training_hyper_tab import render_hyper_brdf_tab

def render_page():
    st.title("🧠 材质表达模型训练")
    tabs = st.tabs(["Neural-BRDF (Baseline)", "HyperBRDF (Advanced)"])
    with tabs[0]:
        render_neural_brdf_tab()
    with tabs[1]:
        render_hyper_brdf_tab()
    st.sidebar.markdown("---")
    st.sidebar.info("💡 提示：Neural-BRDF 转换速度较快，HyperBRDF 重建需要较长时间，请耐心等待。")
