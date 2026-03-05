import streamlit as st
import os
from . import training_actions as actions
from . import render_tool_actions as render_actions

def render_hyper_brdf_tab():
    st.header("HyperBRDF 重建与预测")
    st.info("HyperBRDF (Gokbudak et al. 2024) 使用 HyperNetwork 从稀疏采样中重建材质。")
    
    merl_dir = st.text_input("MERL 材质目录", value=str(actions.DATA_INPUTS_BRDFS), key="hb_merl_dir")

    with st.expander("0. 训练基础超网络 (One-time)", expanded=False):
        st.write("用于训练 HyperBRDF 的基础生成器模型，通常只需运行一次。")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            hb_train_out = st.text_input("模型输出目录", value=str(actions.HYPER_BRDF_DIR / "results" / "test"), key="hb_train_out")
            hb_epochs = st.number_input("训练轮次 (Epochs)", value=100, min_value=1, key="hb_train_epochs")
            hb_kl_weight = st.number_input("KL 权重", value=0.1, min_value=0.0, key="hb_train_kl_weight")
        with col_t2:
            hb_sparse = st.number_input("稀疏采样点数", value=4000, min_value=100, key="hb_train_sparse")
            hb_latent = st.number_input("潜在空间维度", value=40, min_value=1, disabled=True, key="hb_train_latent")
            hb_fw_weight = st.number_input("FW 权重", value=0.1, min_value=0.0, key="hb_train_fw_weight")
        hb_conda_env = st.text_input("Conda 环境名", value="hyperbrdf", key="hb_train_env")
        hb_train_log = st.empty()
        if st.button("开始训练基础模型"):
            actions.run_hb_training(merl_dir, hb_train_out, hb_epochs, hb_sparse, hb_latent, hb_train_log, hb_conda_env, hb_kl_weight, hb_fw_weight)
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader("1. 材质参数提取 (Encoding)")
        st.write("将 `.binary` 材质通过超网络编码为 `.pt` 参数文件。")
        
        merl_files = actions.list_merl_files(merl_dir)
        
        # Native File Dialog for Encoding
        if st.button("📂 打开文件选择器 (Encoding)", key="hb_merl_open_dialog", use_container_width=True):
            ftypes = [("Binary files", "*.binary"), ("All files", "*.*")]
            selected_paths = render_actions.open_file_dialog(merl_dir, "请选择材质文件", ftypes)
            if selected_paths:
                selected_names = [os.path.basename(p) for p in selected_paths]
                valid_names = [n for n in selected_names if n in merl_files]
                if len(valid_names) < len(selected_names):
                    st.warning("部分选择的文件不在当前目录中，已自动忽略。")
                st.session_state.hb_selected_merls = valid_names
                st.rerun()
                
        selected_merls = st.multiselect("选择材质", options=merl_files, default=st.session_state.get("hb_selected_merls", []), key="hb_selected_merls")
        
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
            
            # Native File Dialog for Decoding
            if st.button("📂 打开文件选择器 (Decoding)", key="hb_pt_open_dialog", use_container_width=True):
                ftypes = [("PT files", "*.pt"), ("All files", "*.*")]
                selected_paths = render_actions.open_file_dialog(pt_dir, "请选择 PT 参数文件", ftypes)
                if selected_paths:
                    selected_names = [os.path.basename(p) for p in selected_paths]
                    valid_names = [n for n in selected_names if n in pt_files]
                    if len(valid_names) < len(selected_names):
                        st.warning("部分选择的文件不在当前目录中，已自动忽略。")
                    st.session_state.hb_selected_pts = valid_names
                    st.rerun()
            
            selected_pts = st.multiselect("选择参数文件", options=pt_files, default=st.session_state.get("hb_selected_pts", []), key="hb_selected_pts")
            
            fullbin_out_dir = st.text_input("重建输出目录 (.fullbin)", value=str(actions.ROOT_DIR / "data" / "inputs" / "fullbin"), key="hb_fullbin_out")
            
            hb_log_2 = st.empty()
            if st.button("执行重建转换"):
                actions.run_hb_to_fullbin(pt_dir, selected_pts, fullbin_out_dir, hb_log_2)
        else:
            st.error(f"PT 目录不存在: {pt_dir}")
