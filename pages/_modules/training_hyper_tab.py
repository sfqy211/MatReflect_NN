import streamlit as st
import os
from . import training_actions as actions

def render_hyper_brdf_tab():
    st.header("HyperBRDF 重建与预测")
    st.info("HyperBRDF (Gokbudak et al. 2024) 使用 HyperNetwork 从稀疏采样中重建材质。")
    
    merl_dir = st.text_input("MERL 材质目录", value=str(actions.DATA_INPUTS_BRDFS), key="hb_merl_dir")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader("1. 材质参数提取 (Encoding)")
        st.write("将 `.binary` 材质通过超网络编码为 `.pt` 参数文件。")
        
        merl_files = actions.list_merl_files(merl_dir)
        selected_merls = st.multiselect("选择材质", options=merl_files, key="hb_selected_merls")
        
        checkpoint = st.text_input("Checkpoint (.pt)", value=str(actions.HB_DEFAULT_MODEL), key="hb_checkpoint")
        pt_output_dir = st.text_input("参数输出目录 (.pt)", value=str(actions.HYPER_BRDF_DIR / "results" / "extracted_pts"), key="hb_pt_out")
        
        hb_log_1 = st.empty()
        if st.button("启动参数提取"):
            actions.run_hb_extraction(merl_dir, selected_merls, checkpoint, pt_output_dir, hb_log_1)
            
    with col_h2:
        st.subheader("2. 完整重建 (Decoding)")
        st.write("将 `.pt` 参数解码为 Mitsuba 可读的 `.fullbin` 采样文件。")
        
        pt_dir = st.text_input("PT 参数目录", value=str(actions.HYPER_BRDF_DIR / "results" / "extracted_pts"), key="hb_pt_dir")
        if os.path.exists(pt_dir):
            pt_files = actions.list_pt_files(pt_dir)
            selected_pts = st.multiselect("选择参数文件", options=pt_files, key="hb_selected_pts")
            
            fullbin_out_dir = st.text_input("重建输出目录 (.fullbin)", value=str(actions.ROOT_DIR / "data" / "inputs" / "fullbin"), key="hb_fullbin_out")
            
            hb_log_2 = st.empty()
            if st.button("执行重建转换"):
                actions.run_hb_to_fullbin(pt_dir, selected_pts, fullbin_out_dir, hb_log_2)
        else:
            st.error(f"PT 目录不存在: {pt_dir}")
