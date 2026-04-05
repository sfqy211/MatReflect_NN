import streamlit as st

from .training_hyper_tab import render_hyper_brdf_tab
from .training_neural_tab import render_neural_brdf_tab
from . import ui_shell


def render_page(embedded=False):
    if embedded:
        ui_shell.render_section_heading(
            "Model Module",
            "网络模型管理",
        )
    else:
        st.title("材质表达模型训练")
    tabs = st.tabs(["Neural-BRDF (Baseline)", "HyperBRDF / DecoupledHyperBRDF"])
    with tabs[0]:
        render_neural_brdf_tab()
    with tabs[1]:
        render_hyper_brdf_tab()

    if not embedded:
        st.sidebar.markdown("---")
        st.sidebar.info(
            "HyperBRDF 页签已同时集成原版 HyperBRDF 和增强版 DecoupledHyperBRDF。"
        )
    else:
        st.caption("当前模块保留原有训练链路，只重排成主画布工作区。后续如有需要，可以继续补充模型增删与资产管理视图。")
