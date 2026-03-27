import json
import os

import pandas as pd
import streamlit as st

from . import render_tool_actions as render_actions
from . import training_actions as actions


HB_VARIANTS = {
    "hyperbrdf": {
        "label": "HyperBRDF (原版)",
        "description": "单网络 HyperNetwork 基线流程，适合保持与原论文和旧实验一致。",
    },
    "decoupled": {
        "label": "DecoupledHyperBRDF (增强版)",
        "description": "解析基底 + 高光残差 + 门控融合，更适合稀疏采样下的高光细节重建。",
    },
}


def _variant_key(project_variant, suffix):
    return f"hb_{project_variant}_{suffix}"


def _list_trained_runs(results_dir):
    runs = []
    if not os.path.exists(results_dir):
        return runs
    for root, _, files in os.walk(results_dir):
        if "args.txt" in files:
            rel = os.path.relpath(root, results_dir)
            runs.append((rel, root))
    return sorted(runs, key=lambda item: item[0])


def _load_run_info(run_dir):
    args_path = os.path.join(run_dir, "args.txt")
    train_loss_path = os.path.join(run_dir, "train_loss.csv")
    args_data = {}
    completed_epochs = 0
    if os.path.exists(args_path):
        with open(args_path, "r", encoding="utf-8") as handle:
            args_data = json.load(handle)
    if os.path.exists(train_loss_path):
        train_df = pd.read_csv(train_loss_path)
        if train_df.shape[1] > 1:
            completed_epochs = max(len(train_df.iloc[:, -1]) - 1, 0)
        else:
            completed_epochs = max(len(train_df.iloc[:, 0]) - 1, 0)
    checkpoint_path = os.path.join(run_dir, "checkpoint.pt")
    return args_data, completed_epochs, checkpoint_path


def _render_template_check(config):
    template_path = config["dir"] / "data" / "brdf.fullbin"
    if not template_path.exists():
        st.warning(f"未找到参考模板: {template_path}")
        return
    try:
        template_size = template_path.stat().st_size
        if template_size != render_actions.MERL_FULL_FILE_SIZE:
            st.warning(
                f"参考模板大小异常: {template_size} bytes "
                f"(期望 {render_actions.MERL_FULL_FILE_SIZE} bytes)"
            )
    except OSError:
        st.warning(f"无法读取参考模板: {template_path}")


def render_hyper_brdf_tab():
    st.header("HyperBRDF 重建与预测")
    project_variant = st.radio(
        "方案版本",
        options=list(HB_VARIANTS.keys()),
        format_func=lambda key: HB_VARIANTS[key]["label"],
        horizontal=True,
        key="hb_project_variant",
    )
    config = actions.get_hb_project_config(project_variant)
    st.info(HB_VARIANTS[project_variant]["description"])
    _render_template_check(config)

    results_dir = str(config["default_results_dir"])
    default_train_out = str(config["default_results_dir"] / "test")
    default_extract_dir = str(config["default_extract_dir"])
    default_model = str(config["default_model"])
    default_teacher_dir = str(config["dir"] / "data" / "analytic_teacher")
    default_fullbin_dir = str(actions.ROOT_DIR / "data" / "inputs" / "fullbin")
    default_baseline_ckpt = str(actions.HB_PROJECTS["hyperbrdf"]["default_model"])

    st.subheader("已训练模型")
    runs = _list_trained_runs(results_dir)
    if runs:
        run_labels = [item[0] for item in runs]
        selected_run = st.selectbox(
            "选择训练结果",
            options=run_labels,
            key=_variant_key(project_variant, "trained_run"),
        )
        run_dir = dict(runs).get(selected_run)
        if run_dir:
            args_data, completed_epochs, checkpoint_path = _load_run_info(run_dir)
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.text_input(
                    "Checkpoint 路径",
                    value=checkpoint_path,
                    key=_variant_key(project_variant, "trained_checkpoint"),
                    disabled=True,
                )
                st.number_input(
                    "已训练轮数",
                    value=completed_epochs,
                    min_value=0,
                    key=_variant_key(project_variant, "trained_epochs"),
                    disabled=True,
                )
            with col_r2:
                if st.button("应用到参数提取", key=_variant_key(project_variant, "apply_run")):
                    st.session_state[_variant_key(project_variant, "checkpoint")] = checkpoint_path
                    if "dataset" in args_data:
                        st.session_state[_variant_key(project_variant, "dataset")] = args_data["dataset"]
                    st.rerun()
            if args_data:
                st.json(args_data)
    else:
        st.info("未找到已训练结果，请先完成训练。")

    hb_dataset = st.selectbox(
        "数据集",
        options=["MERL", "EPFL"],
        index=0,
        key=_variant_key(project_variant, "dataset"),
    )
    merl_dir = st.text_input(
        "材质目录",
        value=str(actions.DATA_INPUTS_BRDFS),
        key=_variant_key(project_variant, "merl_dir"),
    )
    hb_conda_env = st.text_input(
        "Conda 环境名",
        value="hyperbrdf",
        key=_variant_key(project_variant, "train_env"),
    )

    if config["supports_teacher"]:
        st.subheader("0. 解析教师缓存")
        st.write("先拟合解析基底教师参数，再用于增强版三分支训练。")
        col_teacher_1, col_teacher_2 = st.columns(2)
        with col_teacher_1:
            teacher_output_dir = st.text_input(
                "教师缓存输出目录",
                value=default_teacher_dir,
                key=_variant_key(project_variant, "teacher_out"),
            )
            teacher_fit_samples = st.number_input(
                "教师拟合采样数",
                value=32768,
                min_value=1024,
                step=1024,
                key=_variant_key(project_variant, "teacher_fit_samples"),
            )
            teacher_steps = st.number_input(
                "教师优化步数",
                value=400,
                min_value=1,
                key=_variant_key(project_variant, "teacher_steps"),
            )
            teacher_lr = st.number_input(
                "教师学习率",
                value=5e-2,
                min_value=1e-6,
                format="%.6f",
                key=_variant_key(project_variant, "teacher_lr"),
            )
        with col_teacher_2:
            teacher_spec_percentile = st.number_input(
                "高光百分位阈值",
                value=0.9,
                min_value=0.5,
                max_value=0.999,
                step=0.01,
                format="%.3f",
                key=_variant_key(project_variant, "teacher_spec_percentile"),
            )
            teacher_analytic_lobes = st.selectbox(
                "解析 lobe 数",
                options=[1, 2],
                index=0,
                key=_variant_key(project_variant, "analytic_lobes"),
            )
            teacher_max_materials = st.number_input(
                "教师拟合材质数 (0=全部)",
                value=0,
                min_value=0,
                key=_variant_key(project_variant, "teacher_max_materials"),
            )
            teacher_seed = st.number_input(
                "教师随机种子",
                value=42,
                min_value=0,
                key=_variant_key(project_variant, "teacher_seed"),
            )

        teacher_log = st.empty()
        if st.button("生成教师缓存", key=_variant_key(project_variant, "fit_teacher")):
            actions.run_hb_fit_teacher(
                merl_dir=merl_dir,
                output_dir=teacher_output_dir,
                log_placeholder=teacher_log,
                conda_env=hb_conda_env,
                dataset=hb_dataset,
                fit_samples=teacher_fit_samples,
                steps=teacher_steps,
                lr=teacher_lr,
                spec_percentile=teacher_spec_percentile,
                analytic_lobes=teacher_analytic_lobes,
                max_materials=teacher_max_materials,
                seed=teacher_seed,
                project_variant=project_variant,
            )

    st.subheader("1. 训练基础超网络")
    st.write("在当前版本下训练重建模型。原版保持单网络流程，增强版使用三分支解耦结构。")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        hb_train_out = st.text_input(
            "模型输出目录",
            value=default_train_out,
            key=_variant_key(project_variant, "train_out"),
        )
        hb_epochs = st.number_input(
            "训练轮次 (Epochs)",
            value=100,
            min_value=1,
            key=_variant_key(project_variant, "train_epochs"),
        )
        hb_kl_weight = st.number_input(
            "KL 权重",
            value=0.1,
            min_value=0.0,
            key=_variant_key(project_variant, "train_kl_weight"),
        )
        hb_lr = st.number_input(
            "学习率 (LR)",
            value=5e-5,
            min_value=1e-7,
            format="%.7f",
            key=_variant_key(project_variant, "train_lr"),
        )
    with col_t2:
        hb_sparse = st.number_input(
            "稀疏采样点数",
            value=4000,
            min_value=100,
            key=_variant_key(project_variant, "train_sparse"),
        )
        st.number_input(
            "潜在空间维度",
            value=40,
            min_value=1,
            disabled=True,
            key=_variant_key(project_variant, "train_latent"),
        )
        hb_fw_weight = st.number_input(
            "FW 权重",
            value=0.1,
            min_value=0.0,
            key=_variant_key(project_variant, "train_fw_weight"),
        )
        hb_keepon = st.checkbox(
            "继续训练 (Keepon)",
            value=False,
            key=_variant_key(project_variant, "train_keepon"),
        )
        hb_train_subset = st.number_input(
            "训练材质数量 (0=全部)",
            value=80,
            min_value=0,
            key=_variant_key(project_variant, "train_subset"),
        )
        hb_train_seed = st.number_input(
            "训练材质随机种子",
            value=42,
            min_value=0,
            key=_variant_key(project_variant, "train_seed"),
        )

    train_extra_kwargs = {}
    if project_variant == "decoupled":
        st.markdown("**增强版训练参数**")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            model_type = st.selectbox(
                "模型类型",
                options=["decoupled", "baseline"],
                index=0,
                key=_variant_key(project_variant, "model_type"),
            )
            sampling_mode = st.selectbox(
                "采样策略",
                options=["hybrid", "random"],
                index=0,
                key=_variant_key(project_variant, "sampling_mode"),
            )
            teacher_dir = st.text_input(
                "教师缓存目录",
                value=default_teacher_dir,
                key=_variant_key(project_variant, "teacher_dir"),
            )
            baseline_checkpoint = st.text_input(
                "原版预热 Checkpoint",
                value=default_baseline_ckpt,
                key=_variant_key(project_variant, "baseline_checkpoint"),
            )
            analytic_loss_weight = st.number_input(
                "解析分支损失权重",
                value=0.1,
                min_value=0.0,
                key=_variant_key(project_variant, "analytic_loss_weight"),
            )
            residual_loss_weight = st.number_input(
                "残差分支损失权重",
                value=0.1,
                min_value=0.0,
                key=_variant_key(project_variant, "residual_loss_weight"),
            )
            spec_loss_weight = st.number_input(
                "高光损失权重",
                value=0.2,
                min_value=0.0,
                key=_variant_key(project_variant, "spec_loss_weight"),
            )
        with col_d2:
            gate_reg_weight = st.number_input(
                "门控正则权重",
                value=0.05,
                min_value=0.0,
                key=_variant_key(project_variant, "gate_reg_weight"),
            )
            spec_percentile = st.number_input(
                "高光百分位阈值",
                value=0.9,
                min_value=0.5,
                max_value=0.999,
                step=0.01,
                format="%.3f",
                key=_variant_key(project_variant, "spec_percentile"),
            )
            gate_bias_init = st.number_input(
                "门控 bias 初值",
                value=-2.0,
                format="%.3f",
                key=_variant_key(project_variant, "gate_bias_init"),
            )
            analytic_lobes = st.selectbox(
                "解析 lobe 数",
                options=[1, 2],
                index=0,
                key=_variant_key(project_variant, "train_analytic_lobes"),
            )
            stage_a_epochs = st.number_input(
                "阶段 A 轮次",
                value=10,
                min_value=0,
                key=_variant_key(project_variant, "stage_a_epochs"),
            )
            stage_b_ramp_epochs = st.number_input(
                "阶段 B ramp 轮次",
                value=20,
                min_value=0,
                key=_variant_key(project_variant, "stage_b_ramp_epochs"),
            )

        train_extra_kwargs = {
            "project_variant": project_variant,
            "model_type": model_type,
            "sampling_mode": sampling_mode,
            "teacher_dir": teacher_dir,
            "analytic_lobes": analytic_lobes,
            "baseline_checkpoint": baseline_checkpoint,
            "analytic_loss_weight": analytic_loss_weight,
            "residual_loss_weight": residual_loss_weight,
            "spec_loss_weight": spec_loss_weight,
            "gate_reg_weight": gate_reg_weight,
            "spec_percentile": spec_percentile,
            "gate_bias_init": gate_bias_init,
            "stage_a_epochs": stage_a_epochs,
            "stage_b_ramp_epochs": stage_b_ramp_epochs,
        }
    else:
        train_extra_kwargs = {"project_variant": project_variant}

    hb_train_log = st.empty()
    if st.button("开始训练模型", key=_variant_key(project_variant, "start_training")):
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
            **train_extra_kwargs,
        )

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.subheader("2. 材质参数提取 (Encoding)")
        st.write("将 `.binary` 或 `.csv` 材质编码为 `.pt` 参数文件。")

        merl_files = actions.list_merl_files(merl_dir, hb_dataset)
        preset_flag_key = _variant_key(project_variant, "apply_preset_merls")
        selected_merls_key = _variant_key(project_variant, "selected_merls")

        if st.session_state.get(preset_flag_key):
            preset_selected = render_actions.get_preset_test_set_selection(merl_files)
            st.session_state[selected_merls_key] = preset_selected
            del st.session_state[preset_flag_key]
            if preset_selected:
                st.success(f"已选中 {len(preset_selected)} 个预设测试材质")
            else:
                st.warning("当前目录未找到预设测试集中的材质文件")

        col_pick_1, col_pick_2 = st.columns(2)
        with col_pick_1:
            if st.button("打开文件选择器 (Encoding)", key=_variant_key(project_variant, "merl_open_dialog"), use_container_width=True):
                file_types = (
                    [("Binary files", "*.binary"), ("All files", "*.*")]
                    if hb_dataset == "MERL"
                    else [("CSV files", "*.csv"), ("All files", "*.*")]
                )
                render_actions.update_selection_from_dialog(
                    merl_dir,
                    "请选择材质文件",
                    file_types,
                    merl_files,
                    selected_merls_key,
                )
        with col_pick_2:
            if st.button(
                "选择预设测试集 (20个材质)",
                key=_variant_key(project_variant, "merl_select_preset"),
                use_container_width=True,
                disabled=hb_dataset != "MERL",
            ):
                st.session_state[preset_flag_key] = True
                st.rerun()

        if hb_dataset != "MERL":
            st.caption("预设测试集仅适用于 MERL 数据集。")

        selected_merls = st.multiselect(
            "选择材质",
            options=merl_files,
            default=st.session_state.get(selected_merls_key, []),
            key=selected_merls_key,
        )

        checkpoint = st.text_input(
            "Checkpoint (.pt)",
            value=default_model,
            key=_variant_key(project_variant, "checkpoint"),
        )
        pt_output_dir = st.text_input(
            "参数输出目录 (.pt)",
            value=default_extract_dir,
            key=_variant_key(project_variant, "pt_out"),
        )
        extract_sparse = st.number_input(
            "提取阶段稀疏采样点数",
            value=4000,
            min_value=100,
            key=_variant_key(project_variant, "extract_sparse"),
            disabled=project_variant != "decoupled",
        )

        hb_log_1 = st.empty()
        if st.button("启动参数提取", key=_variant_key(project_variant, "start_extract")):
            actions.run_hb_extraction(
                merl_dir=merl_dir,
                selected_merls=selected_merls,
                model_path=checkpoint,
                output_dir=pt_output_dir,
                log_placeholder=hb_log_1,
                conda_env=hb_conda_env,
                dataset=hb_dataset,
                project_variant=project_variant,
                sparse_samples=extract_sparse,
            )

    with col_h2:
        st.subheader("3. 完整重建 (Decoding)")
        st.write("将 `.pt` 参数文件解码为 Mitsuba 可读取的 `.fullbin` 材质。")

        pt_dir = st.text_input(
            "PT 参数目录",
            value=default_extract_dir,
            key=_variant_key(project_variant, "pt_dir"),
        )
        if os.path.exists(pt_dir):
            pt_files = actions.list_pt_files(pt_dir)
            selected_pts_key = _variant_key(project_variant, "selected_pts")

            if st.button("打开文件选择器 (Decoding)", key=_variant_key(project_variant, "pt_open_dialog"), use_container_width=True):
                render_actions.update_selection_from_dialog(
                    pt_dir,
                    "请选择 PT 参数文件",
                    [("PT files", "*.pt"), ("All files", "*.*")],
                    pt_files,
                    selected_pts_key,
                )

            selected_pts = st.multiselect(
                "选择参数文件",
                options=pt_files,
                default=st.session_state.get(selected_pts_key, []),
                key=selected_pts_key,
            )

            fullbin_out_dir = st.text_input(
                "重建输出目录 (.fullbin)",
                value=default_fullbin_dir,
                key=_variant_key(project_variant, "fullbin_out"),
            )

            hb_log_2 = st.empty()
            if st.button("执行重建转换", key=_variant_key(project_variant, "start_decode")):
                actions.run_hb_to_fullbin(
                    pt_dir=pt_dir,
                    selected_pts=selected_pts,
                    output_dir=fullbin_out_dir,
                    log_placeholder=hb_log_2,
                    conda_env=hb_conda_env,
                    dataset=hb_dataset,
                    project_variant=project_variant,
                )
        else:
            st.error(f"PT 目录不存在: {pt_dir}")
