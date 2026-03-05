import streamlit as st
import os
from . import training_actions as actions
from . import render_tool_actions as render_actions

def render_neural_brdf_tab():
    st.header("Neural-BRDF 训练与转换")
    st.info("Neural-BRDF (Sztrajman et al. 2021) 将单个材质表达为 MLP 网络权重。")
    merl_dir = st.text_input("MERL 材质目录", value=str(actions.DATA_INPUTS_BRDFS), key="nb_merl_dir")
    if not os.path.exists(merl_dir):
        st.error(f"目录不存在: {merl_dir}")
        return
    merl_files = actions.list_merl_files(merl_dir)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. PyTorch 训练 (直接输出 .npy)")
        
        # Native File Dialog Button for PyTorch
        if st.button("📂 打开文件选择器 (PyTorch)", key="nb_pt_open_dialog", use_container_width=True):
            ftypes = [("Binary files", "*.binary"), ("All files", "*.*")]
            selected_paths = render_actions.open_file_dialog(merl_dir, "请选择材质文件", ftypes)
            if selected_paths:
                selected_names = [os.path.basename(p) for p in selected_paths]
                valid_names = [n for n in selected_names if n in merl_files]
                if len(valid_names) < len(selected_names):
                    st.warning("部分选择的文件不在当前目录中，已自动忽略。")
                st.session_state.nb_pt_selected = valid_names
                st.rerun()
                
        pt_selected = st.multiselect("选择材质 (可多选)", options=merl_files, default=st.session_state.get("nb_pt_selected", []), key="nb_pt_selected")
        pt_epochs = st.number_input("迭代次数 (Epochs)", value=100, min_value=1, key="nb_pt_epochs")
        pt_device = st.selectbox("训练设备", options=["cpu", "cuda"], index=0, key="nb_pt_device")
        pt_output_dir = st.text_input("权重输出目录", value=str(actions.DATA_INPUTS_NPY), key="nb_pt_output_dir")
        pt_log = st.empty()
        if st.button("开始 PyTorch 训练"):
            actions.run_pytorch_training(merl_dir, pt_selected, pt_epochs, pt_output_dir, pt_log, pt_device)
    with col2:
        st.subheader("2. Keras 训练 + h5 -> npy")
        
        # Native File Dialog Button for Keras
        if st.button("📂 打开文件选择器 (Keras)", key="nb_keras_open_dialog", use_container_width=True):
            ftypes = [("Binary files", "*.binary"), ("All files", "*.*")]
            selected_paths = render_actions.open_file_dialog(merl_dir, "请选择材质文件", ftypes)
            if selected_paths:
                selected_names = [os.path.basename(p) for p in selected_paths]
                valid_names = [n for n in selected_names if n in merl_files]
                if len(valid_names) < len(selected_names):
                    st.warning("部分选择的文件不在当前目录中，已自动忽略。")
                st.session_state.nb_keras_selected = valid_names
                st.rerun()
                
        keras_selected = st.multiselect("选择材质 (可多选)", options=merl_files, default=st.session_state.get("nb_keras_selected", []), key="nb_keras_selected")
        cuda_device = st.text_input("CUDA 设备 ID", value="0", help="设置 GPU ID (如 0, 1)。输入 -1 使用 CPU 训练。", key="nb_keras_cuda_device")
        keras_h5_dir = st.text_input("中间 H5 目录", value=str(actions.DATA_INTERMEDIATE_H5), key="nb_keras_h5_dir")
        keras_npy_dir = st.text_input("权重输出目录", value=str(actions.DATA_INPUTS_NPY), key="nb_keras_npy_dir")
        keras_log = st.empty()
        if st.button("开始 Keras 训练并转换"):
            if cuda_device == "-1":
                st.info("已选择 CPU 模式进行 Keras 训练")
            actions.run_keras_training(merl_dir, keras_selected, cuda_device, keras_h5_dir, keras_npy_dir, keras_log)
    st.subheader("3. 独立 H5 -> NPY 转换")
    st.write("如果你已有 .h5 模型文件，可以在此直接转换为 .npy 权重。")
    h5_dir = st.text_input("H5 文件目录", value=str(actions.DATA_INTERMEDIATE_H5), key="nb_h5_dir")
    if os.path.exists(h5_dir):
        h5_files = actions.list_h5_files(h5_dir)
        
        # Native File Dialog Button for H5
        col_h5_dlg, col_h5_ph = st.columns([1, 3])
        with col_h5_dlg:
            if st.button("📂 打开 H5 选择器", key="nb_h5_open_dialog", use_container_width=True):
                ftypes = [("H5 files", "*.h5"), ("All files", "*.*")]
                selected_paths = render_actions.open_file_dialog(h5_dir, "请选择 H5 模型文件", ftypes)
                if selected_paths:
                    selected_names = [os.path.basename(p) for p in selected_paths]
                    valid_names = [n for n in selected_names if n in h5_files]
                    if len(valid_names) < len(selected_names):
                        st.warning("部分选择的文件不在当前目录中，已自动忽略。")
                    st.session_state.nb_selected_h5s = valid_names
                    st.rerun()
        
        selected_h5s = st.multiselect("选择 H5 文件", options=h5_files, default=st.session_state.get("nb_selected_h5s", []), key="nb_selected_h5s")
        h5_conv_log = st.empty()
        h5_npy_output_dir = st.text_input("权重输出目录", value=str(actions.DATA_INPUTS_NPY), key="nb_h5_npy_output_dir")
        if st.button("开始转换 H5"):
            h5_paths = [os.path.join(h5_dir, f) for f in selected_h5s]
            actions.run_h5_to_npy(h5_paths, h5_npy_output_dir, h5_conv_log)
    else:
        st.error(f"H5 目录不存在: {h5_dir}")
