import json
import os

import pandas as pd
import streamlit as st

from . import render_tool_actions as render_actions
from . import training_actions as actions


def render_hyper_brdf_tab():
    st.header("HyperBRDF 重建与预测")
    st.info("HyperBRDF (Gokbudak et al. 2024) 使用 HyperNetwork 从稀疏采样中重建材质。")

    template_path = actions.HYPER_BRDF_DIR / "data" / "brdf.fullbin"
    if not template_path.exists():
        st.warning(f"未找到参考模板: {template_path}")
    else:
        try:
            template_size = template_path.stat().st_size
            if template_size != render_actions.MERL_FULL_FILE_SIZE:
                st.warning(
                    f"参考模板大小异常: {template_size} bytes "
                    f"(期望 {render_actions.MERL_FULL_FILE_SIZE} bytes)"
                )
        except OSError:
            st.warning(f"无法读取参考模板: {template_path}")

    def list_trained_runs(results_dir):
        runs = []
        if not os.path.exists(results_dir):
            return runs
        for root, _, files in os.walk(results_dir):
            if "args.txt" in files:
                rel = os.path.relpath(root, results_dir)
                runs.append((rel, root))
        return sorted(runs, key=lambda x: x[0])

    def load_run_info(run_dir):
        args_path = os.path.join(run_dir, "args.txt")
        train_loss_path = os.path.join(run_dir, "train_loss.csv")
        args_data = {}
        completed_epochs = 0
        if os.path.exists(args_path):
            with open(args_path, "r", encoding="utf-8") as f:
                args_data = json.load(f)
        if os.path.exists(train_loss_path):
            train_df = pd.read_csv(train_loss_path)
            if train_df.shape[1] > 1:
                completed_epochs = max(len(train_df.iloc[:, -1]) - 1, 0)
            else:
                completed_epochs = max(len(train_df.iloc[:, 0]) - 1, 0)
        checkpoint_path = os.path.join(run_dir, "checkpoint.pt")
        return args_data, completed_epochs, checkpoint_path

    st.subheader("已训练模型")
    runs = list_trained_runs(str(actions.HYPER_BRDF_DIR / "results"))
    if runs:
        run_labels = [r[0] for r in runs]
        selected_run = st.selectbox("选择训练结果", options=run_labels, key="hb_trained_run")
        run_dir = dict(runs).get(selected_run)
        if run_dir:
            args_data, completed_epochs, checkpoint_path = load_run_info(run_dir)
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.text_input("Checkpoint 路径", value=checkpoint_path, key="hb_trained_checkpoint", disabled=True)
                st.number_input("已训练轮数", value=completed_epochs, min_value=0, key="hb_trained_epochs", disabled=True)
            with col_r2:
                if st.button("应用到参数提取"):
                    st.session_state["hb_checkpoint"] = checkpoint_path
                    if "dataset" in args_data:
                        st.session_state["hb_dataset"] = args_data["dataset"]
            if args_data:
                st.json(args_data)
    else:
        st.info("未找到已训练结果，请先完成训练。")

    hb_dataset = st.selectbox("数据集", options=["MERL", "EPFL"], index=0, key="hb_dataset")
    merl_dir = st.text_input("材质目录", value=str(actions.DATA_INPUTS_BRDFS), key="hb_merl_dir")

    st.subheader("1. 训练基础超网络 (One-time)")
    st.write("用于训练 HyperBRDF 的基础生成器模型，通常只需运行一次。")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        hb_train_out = st.text_input("模型输出目录", value=str(actions.HYPER_BRDF_DIR / "results" / "test"), key="hb_train_out")
        hb_epochs = st.number_input("训练轮次 (Epochs)", value=100, min_value=1, key="hb_train_epochs")
        hb_kl_weight = st.number_input("KL 权重", value=0.1, min_value=0.0, key="hb_train_kl_weight")
        hb_lr = st.number_input("学习率 (LR)", value=5e-5, min_value=1e-7, format="%.7f", key="hb_train_lr")
    with col_t2:
        hb_sparse = st.number_input("稀疏采样点数", value=4000, min_value=100, key="hb_train_sparse")
        hb_latent = st.number_input("潜在空间维度", value=40, min_value=1, disabled=True, key="hb_train_latent")
        hb_fw_weight = st.number_input("FW 权重", value=0.1, min_value=0.0, key="hb_train_fw_weight")
        hb_keepon = st.checkbox("继续训练 (Keepon)", value=False, key="hb_train_keepon")
        hb_train_subset = st.number_input("训练材质数量 (0=全部)", value=80, min_value=0, key="hb_train_subset")
        hb_train_seed = st.number_input("训练材质随机种子", value=42, min_value=0, key="hb_train_seed")

    hb_conda_env = st.text_input("Conda 环境名", value="hyperbrdf", key="hb_train_env")
    hb_train_log = st.empty()
    if st.button("开始训练基础模型"):
        actions.run_hb_training(
            merl_dir,
            hb_train_out,
            hb_epochs,
            hb_sparse,
            hb_latent,
            hb_train_log,
            hb_conda_env,
            hb_kl_weight,
            hb_fw_weight,
            hb_dataset,
            hb_lr,
            hb_keepon,
            hb_train_subset,
            hb_train_seed,
        )

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader("2. 材质参数提取 (Encoding)")
        st.write("将 `.binary` 材质通过超网络编码为 `.pt` 参数文件。")

        merl_files = actions.list_merl_files(merl_dir, hb_dataset)

        if st.session_state.get("hb_apply_preset_merls"):
            preset_selected = render_actions.get_preset_test_set_selection(merl_files)
            st.session_state["hb_selected_merls"] = preset_selected
            del st.session_state["hb_apply_preset_merls"]
            if preset_selected:
                st.success(f"已选中 {len(preset_selected)} 个预设测试材质")
            else:
                st.warning("当前目录未找到预设测试集中的材质文件")

        col_pick_1, col_pick_2 = st.columns(2)
        with col_pick_1:
            if st.button("📂 打开文件选择器 (Encoding)", key="hb_merl_open_dialog", use_container_width=True):
                ftypes = [("Binary files", "*.binary"), ("All files", "*.*")] if hb_dataset == "MERL" else [("CSV files", "*.csv"), ("All files", "*.*")]
                render_actions.update_selection_from_dialog(
                    merl_dir,
                    "请选择材质文件",
                    ftypes,
                    merl_files,
                    "hb_selected_merls",
                )
        with col_pick_2:
            if st.button("🎯 选择预设测试集 (20个材质)", key="hb_merl_select_preset", use_container_width=True, disabled=hb_dataset != "MERL"):
                st.session_state["hb_apply_preset_merls"] = True
                st.rerun()

        if hb_dataset != "MERL":
            st.caption("预设测试集仅适用于 MERL 数据集。")

        selected_merls = st.multiselect(
            "选择材质",
            options=merl_files,
            default=st.session_state.get("hb_selected_merls", []),
            key="hb_selected_merls",
        )

        checkpoint = st.text_input("Checkpoint (.pt)", value=str(actions.HB_DEFAULT_MODEL), key="hb_checkpoint")
        pt_output_dir = st.text_input("参数输出目录 (.pt)", value=str(actions.HYPER_BRDF_DIR / "results" / "extracted_pts"), key="hb_pt_out")

        hb_log_1 = st.empty()
        if st.button("启动参数提取"):
            actions.run_hb_extraction(merl_dir, selected_merls, checkpoint, pt_output_dir, hb_log_1, dataset=hb_dataset)

    with col_h2:
        st.subheader("3. 完整重建 (Decoding)")
        st.write("将 `.pt` 参数解码为 Mitsuba 可读的 `.fullbin` 采样文件。")

        pt_dir = st.text_input("PT 参数目录", value=str(actions.HYPER_BRDF_DIR / "results" / "extracted_pts"), key="hb_pt_dir")
        if os.path.exists(pt_dir):
            pt_files = actions.list_pt_files(pt_dir)

            if st.button("📂 打开文件选择器 (Decoding)", key="hb_pt_open_dialog", use_container_width=True):
                ftypes = [("PT files", "*.pt"), ("All files", "*.*")]
                render_actions.update_selection_from_dialog(
                    pt_dir,
                    "请选择 PT 参数文件",
                    ftypes,
                    pt_files,
                    "hb_selected_pts",
                )

            selected_pts = st.multiselect(
                "选择参数文件",
                options=pt_files,
                default=st.session_state.get("hb_selected_pts", []),
                key="hb_selected_pts",
            )

            fullbin_out_dir = st.text_input(
                "重建输出目录 (.fullbin)",
                value=str(actions.ROOT_DIR / "data" / "inputs" / "fullbin"),
                key="hb_fullbin_out",
            )

            hb_log_2 = st.empty()
            if st.button("执行重建转换"):
                actions.run_hb_to_fullbin(pt_dir, selected_pts, fullbin_out_dir, hb_log_2, dataset=hb_dataset)
        else:
            st.error(f"PT 目录不存在: {pt_dir}")
