import streamlit as st

from .training_hyper_tab import render_hyper_brdf_tab
from .training_neural_tab import render_neural_brdf_tab


def render_page():
    st.title("材质表达模型训练")
    tabs = st.tabs(["Neural-BRDF (Baseline)", "HyperBRDF / DecoupledHyperBRDF"])
    with tabs[0]:
        render_neural_brdf_tab()
    with tabs[1]:
        render_hyper_brdf_tab()

    st.sidebar.markdown("---")
    st.sidebar.info(
        "HyperBRDF 页签已同时集成原版 HyperBRDF 和增强版 DecoupledHyperBRDF。"
    )
