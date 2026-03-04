import streamlit as st
import os
from . import training_actions as actions

def render_neural_brdf_tab():
    st.header("Neural-BRDF 训练与转换")
    st.info("Neural-BRDF (Sztrajman et al. 2021) 将单个材质表达为 MLP 网络权重。")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. 权重转换 (binary -> npy)")
        merl_dir = st.text_input("MERL 材质目录", value=str(actions.ROOT_DIR / "data" / "inputs" / "brdfs"), key="nb_merl_dir")
        if os.path.exists(merl_dir):
            merl_files = actions.list_merl_files(merl_dir)
            selected_merl = st.selectbox("选择待转换材质", options=merl_files, key="nb_selected_merl")
            nb_conv_log = st.empty()
            if st.button("开始转换为 .npy"):
                actions.run_binary_to_npy(merl_dir, selected_merl, nb_conv_log)
        else:
            st.error(f"目录不存在: {merl_dir}")
    with col2:
        st.subheader("2. PyTorch 完整训练")
        st.write("待集成: 调用 `pytorch_code/train_NBRDF_pytorch.py` 进行大规模迭代训练。")
        st.number_input("迭代次数 (Epochs)", value=100, key="nb_epochs")
        st.selectbox("优化器", ["Adam", "LBFGS"], key="nb_optimizer")
        if st.button("开始 PyTorch 训练"):
            st.warning("功能集成中...")
