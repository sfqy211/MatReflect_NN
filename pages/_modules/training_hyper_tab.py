import json
import os

import pandas as pd
import streamlit as st

from . import render_tool_actions as render_actions
from . import training_actions as actions


def _list_trained_runs(results_dir: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, str]] = []
    if not os.path.exists(results_dir):
        return runs
    for root, _, files in os.walk(results_dir):
        if "args.txt" in files:
            rel = os.path.relpath(root, results_dir)
            runs.append((rel, root))
    return sorted(runs, key=lambda item: item[0])


def _load_run_info(run_dir: str) -> tuple[dict, int, str]:
    args_path = os.path.join(run_dir, "args.txt")
    train_loss_path = os.path.join(run_dir, "train_loss.csv")
    args_data: dict = {}
    completed_epochs = 0
    if os.path.exists(args_path):
        with open(args_path, "r", encoding="utf-8") as handle:
            args_data = json.load(handle)
    if os.path.exists(train_loss_path):
        train_df = pd.read_csv(train_loss_path)
        column_index = -1 if train_df.shape[1] > 1 else 0
        completed_epochs = max(len(train_df.iloc[:, column_index]) - 1, 0)
    checkpoint_path = os.path.join(run_dir, "checkpoint.pt")
    return args_data, completed_epochs, checkpoint_path


def _render_template_check(config: dict) -> None:
    template_path = config["dir"] / "data" / "brdf.fullbin"
    if not template_path.exists():
        st.warning(f"未找到参考模板: {template_path}")
        return
    try:
        template_size = template_path.stat().st_size
    except OSError:
        st.warning(f"无法读取参考模板: {template_path}")
        return
    if template_size != render_actions.MERL_FULL_FILE_SIZE:
        st.warning(
            f"参考模板大小异常: {template_size} bytes "
            f"(期望 {render_actions.MERL_FULL_FILE_SIZE} bytes)"
        )


def render_hyper_brdf_tab() -> None:
    config = actions.get_hb_project_config("hyperbrdf")
    results_dir = str(config["default_results_dir"])
    default_train_out = str(config["default_results_dir"] / "test")
    default_extract_dir = str(config["default_extract_dir"])
    default_model = str(config["default_model"])
    default_fullbin_dir = str(actions.ROOT_DIR / "data" / "inputs" / "fullbin")

    st.header("HyperBRDF 重建与预览")
    st.info("当前 V1 兼容页仅保留 HyperBRDF 流程。")
    _render_template_check(config)

    st.subheader("已训练模型")
    runs = _list_trained_runs(results_dir)
    if runs:
        run_labels = [item[0] for item in runs]
        selected_run = st.selectbox("选择训练结果", options=run_labels, key="hb_trained_run")
        run_dir = dict(runs).get(selected_run)
        if run_dir:
            args_data, completed_epochs, checkpoint_path = _load_run_info(run_dir)
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Checkpoint 路径", value=checkpoint_path, disabled=True, key="hb_checkpoint_preview")
                st.number_input("已训练轮数", value=completed_epochs, min_value=0, disabled=True, key="hb_epochs_preview")
            with col2:
                if st.button("应用到参数提取", key="hb_apply_run"):
                    st.session_state["hb_checkpoint"] = checkpoint_path
                    if "dataset" in args_data:
                        st.session_state["hb_dataset"] = args_data["dataset"]
                    st.rerun()
            if args_data:
                st.json(args_data)
    else:
        st.info("未找到训练结果，请先完成 HyperBRDF 训练。")

    hb_dataset = st.selectbox("数据集", options=["MERL", "EPFL"], index=0, key="hb_dataset")
    merl_dir = st.text_input("材质目录", value=str(actions.DATA_INPUTS_BRDFS), key="hb_merl_dir")
    hb_conda_env = st.text_input("Conda 环境名", value="hyperbrdf", key="hb_train_env")

    st.subheader("1. 训练 HyperBRDF")
    col1, col2 = st.columns(2)
    with col1:
        hb_train_out = st.text_input("模型输出目录", value=default_train_out, key="hb_train_out")
        hb_epochs = st.number_input("训练轮次 (Epochs)", value=100, min_value=1, key="hb_train_epochs")
        hb_kl_weight = st.number_input("KL 权重", value=0.1, min_value=0.0, key="hb_train_kl_weight")
        hb_lr = st.number_input("学习率 (LR)", value=5e-5, min_value=1e-7, format="%.7f", key="hb_train_lr")
    with col2:
        hb_sparse = st.number_input("稀疏采样点数", value=4000, min_value=100, key="hb_train_sparse")
        st.number_input("潜在空间维度", value=40, min_value=1, disabled=True, key="hb_train_latent")
        hb_fw_weight = st.number_input("FW 权重", value=0.1, min_value=0.0, key="hb_train_fw_weight")
        hb_keepon = st.checkbox("继续训练 (Keepon)", value=False, key="hb_train_keepon")
        hb_train_subset = st.number_input("训练材质数量 (0=全部)", value=80, min_value=0, key="hb_train_subset")
        hb_train_seed = st.number_input("训练材质随机种子", value=42, min_value=0, key="hb_train_seed")

    hb_train_log = st.empty()
    if st.button("开始训练模型", key="hb_start_training"):
        actions.run_hb_training(
            merl_dir=merl_dir,
            output_dir=hb_train_out,
            epochs=hb_epochs,
            sparse_samples=hb_sparse,
            latent_dim=40,
            log_placeholder=hb_train_log,
            conda_env=hb_conda_env,
            kl_weight=hb_kl_weight,
            fw_weight=hb_fw_weight,
            dataset=hb_dataset,
            lr=hb_lr,
            keepon=hb_keepon,
            train_subset=hb_train_subset,
            train_seed=hb_train_seed,
            project_variant="hyperbrdf",
        )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("2. 材质参数提取 (Encoding)")
        st.write("将 `.binary` 或 `.csv` 材质编码为 `.pt` 参数文件。")

        merl_files = actions.list_merl_files(merl_dir, hb_dataset)
        if st.button("应用预设 20 材质", key="hb_apply_preset_merls"):
            st.session_state["hb_selected_merls"] = render_actions.get_preset_test_set_selection(merl_files)
            st.rerun()

        selected_merls = st.multiselect(
            "选择材质文件",
            options=merl_files,
            default=st.session_state.get("hb_selected_merls", []),
            key="hb_selected_merls",
        )
        model_path = st.text_input(
            "Checkpoint 路径",
            value=st.session_state.get("hb_checkpoint", default_model),
            key="hb_checkpoint",
        )
        extract_out = st.text_input("PT 输出目录", value=default_extract_dir, key="hb_extract_out")

        extract_log = st.empty()
        if st.button("启动参数提取", key="hb_start_extract"):
            actions.run_hb_extraction(
                merl_dir=merl_dir,
                selected_merls=selected_merls,
                model_path=model_path,
                output_dir=extract_out,
                log_placeholder=extract_log,
                conda_env=hb_conda_env,
                dataset=hb_dataset,
                project_variant="hyperbrdf",
                sparse_samples=hb_sparse,
            )

    with col2:
        st.subheader("3. PT 转 FullBin")
        st.write("将提取好的 `.pt` 参数解码为 Mitsuba 可用的 `.fullbin` 文件。")

        pt_dir = st.text_input("PT 目录", value=default_extract_dir, key="hb_pt_dir")
        pt_files = actions.list_pt_files(pt_dir)
        selected_pts = st.multiselect("选择 PT 文件", options=pt_files, key="hb_selected_pts")
        fullbin_out = st.text_input("FullBin 输出目录", value=default_fullbin_dir, key="hb_fullbin_out")

        fullbin_log = st.empty()
        if st.button("执行重建转换", key="hb_start_fullbin"):
            actions.run_hb_to_fullbin(
                pt_dir=pt_dir,
                selected_pts=selected_pts,
                output_dir=fullbin_out,
                log_placeholder=fullbin_log,
                conda_env=hb_conda_env,
                dataset=hb_dataset,
                project_variant="hyperbrdf",
            )
