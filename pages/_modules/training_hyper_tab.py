import streamlit as st
from . import training_actions as actions

def render_hyper_brdf_tab():
    st.header("HyperBRDF 训练与预测")
    st.info("HyperBRDF (Gokbudak et al. 2024) 使用 HyperNetwork 从稀疏采样中重建材质。")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader("1. 批量处理与重建")
        st.write("调用 `batch_process.py` 或 `main.py` 进行材质库重建。")
        st.text_input("Checkpoint 路径", value=str(actions.HYPER_BRDF_DIR / "results" / "test" / "MERL" / "checkpoint.pt"), key="hb_checkpoint")
        if st.button("启动重建进程"):
            st.warning("功能集成中...")
    with col_h2:
        st.subheader("2. 结果转换 (pt -> fullbin)")
        st.write("将训练好的 PyTorch 权重转换为 Mitsuba 可读的 `.fullbin` 格式。")
        if st.button("执行 pt_to_fullmerl.py"):
            st.info("正在调用转换脚本...")
