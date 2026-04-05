import streamlit as st
from pathlib import Path

from . import get_project_root
from . import render_tool_actions as actions
from . import ui_shell


def _prepare_scene_selector(root_dir):
    scene_paths = actions.list_scene_xmls(root_dir)
    if st.session_state.scene_path and st.session_state.scene_path not in scene_paths:
        scene_paths.insert(0, st.session_state.scene_path)

    display_map = {}
    for path in scene_paths:
        try:
            rel = str(Path(path).resolve().relative_to(Path(root_dir).resolve()))
            display_map[rel.replace("\\", "/")] = path
        except Exception:
            display_map[path] = path
    return display_map


def _render_focus_buttons():
    focus_specs = [
        ("engine", "模型设置"),
        ("materials", "材质选择"),
        ("settings", "渲染设置"),
        ("launch", "开始渲染"),
    ]
    cols = st.columns(4, gap="small")
    for idx, (focus_key, label) in enumerate(focus_specs):
        button_type = (
            "primary"
            if st.session_state.get("render_focus") == focus_key
            else "secondary"
        )
        if cols[idx].button(
            label,
            key=f"render_focus_button_{focus_key}",
            type=button_type,
            use_container_width=True,
        ):
            st.session_state.render_focus = focus_key


def render_page(left_panel, main_panel):
    actions.init_state()
    if not st.session_state.root_dir:
        st.session_state.root_dir = str(get_project_root())
    actions.ensure_mitsuba_state(st.session_state.root_dir)
    if not st.session_state.scene_path:
        st.session_state.scene_path = actions.get_default_scene_path(
            st.session_state.root_dir
        )

    root_dir = st.session_state.root_dir
    base_dir, input_dir_map, output_dir_map = actions.get_paths()

    with left_panel:
        st.markdown("### ⚙️ 渲染控制")

        # 1. 模型选择
        model_options = {
            "brdfs": "GT / 物理基本模型 (.binary)",
            "npy": "Neural-BRDF (优化版1 .npy)",
            "fullbin": "HyperBRDF (优化版2 .fullbin)",
            "decoupled": "DecoupledHyperBRDF (优化版3 .fullbin)",
        }
        # In current logic, decoupled might use fullbin render mode as well, but for UI sake let's map them to render modes
        render_mode_map = {
            "brdfs": "brdfs",
            "npy": "npy",
            "fullbin": "fullbin",
            "decoupled": "fullbin",
        }
        selected_model = st.selectbox(
            "1. 选择网络模型",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            key="render_model_selector",
        )
        render_mode = render_mode_map[selected_model]
        # sync state
        st.session_state.render_mode = render_mode
        if "input_dir" not in st.session_state:
            st.session_state.input_dir = str(input_dir_map.get("brdfs", ""))
        if "output_dir" not in st.session_state:
            st.session_state.output_dir = str(output_dir_map.get("brdfs", ""))

        input_dir = st.session_state.input_dir
        output_dir = st.session_state.output_dir
        render_files = actions.list_render_files(input_dir, render_mode)

        # 2. 材质选择
        st.markdown("### 🎨 材质选择")
        render_selected = st.multiselect(
            "2. 选择要渲染的材质",
            options=render_files,
            default=st.session_state.get("render_selected", []),
            key="render_selected",
            label_visibility="collapsed",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("预设 20 材质", use_container_width=True):
                actions.select_preset_test_set(render_files)
        with col2:
            if st.button("刷新目录", use_container_width=True):
                pass

        # 3. 高级设置 (Optional)
        with st.expander("高级设置 (可选)"):
            integrator_type = st.selectbox(
                "积分器", ["bdpt", "path"], index=0, key="integrator_type"
            )
            sample_count = st.number_input(
                "SPP", min_value=1, value=256, key="sample_count"
            )
            auto_convert = st.checkbox("自动转 PNG", value=True, key="auto_convert")
            skip_existing = st.checkbox("跳过已存在", value=False, key="skip_existing")
            use_custom_cmd = st.checkbox(
                "自定义命令", value=False, key="use_custom_cmd"
            )
            custom_cmd_str = (
                st.text_input(
                    "命令占位符",
                    value='"{mitsuba}" -o "{output}" "{input}"',
                    key="custom_cmd_str",
                )
                if use_custom_cmd
                else None
            )

        # 4. 开始渲染
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        col_start, col_stop = st.columns([2, 1])
        with col_start:
            start_btn = st.button(
                "🚀 开始渲染", type="primary", use_container_width=True
            )
        with col_stop:
            stop_btn = st.button("🛑 停止", use_container_width=True)

    with main_panel:
        ui_shell.render_section_heading("Render Module", "渲染可视化")

        status_container = st.container()
        render_progress = status_container.empty()
        render_status = status_container.empty()
        render_log_placeholder = status_container.empty()

        if stop_btn:
            if not actions.STOP_SIGNAL:
                actions.STOP_SIGNAL.append(True)
            actions.log("已发送停止信号...")

        if start_btn:
            actions.STOP_SIGNAL.clear()
            prog_bar = render_progress.progress(0)
            actions.render_batch(
                render_selected,
                render_mode,
                input_dir,
                output_dir,
                auto_convert,
                skip_existing,
                prog_bar,
                render_status,
                base_dir,
                render_log_placeholder,
                custom_cmd_str,
                integrator_type,
                sample_count,
            )
            st.rerun()

        # Gallery
        st.markdown("### 🖼️ 渲染结果画廊")
        png_dir = Path(output_dir) / "png"
        if png_dir.exists() and png_dir.is_dir():
            import os

            png_files = sorted(
                [
                    f
                    for f in os.listdir(png_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))
                ]
            )
            if png_files:
                c_search, c_info = st.columns([1, 2])
                search_query = c_search.text_input("🔍 搜索材质...", "")
                if search_query:
                    png_files = [
                        f for f in png_files if search_query.lower() in f.lower()
                    ]
                c_info.caption(
                    f"当前输出目录: `{png_dir}`\n\n共渲染了 **{len(png_files)}** 个材质。"
                )

                cols_per_row = 4
                for i in range(0, len(png_files), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(png_files):
                            file_name = png_files[i + j]
                            with col:
                                display_name = (
                                    file_name.split("_202")[0].replace(".png", "")
                                    if "_202" in file_name
                                    else file_name.replace(".png", "")
                                )
                                st.image(
                                    str(png_dir / file_name),
                                    caption=display_name,
                                    use_container_width=True,
                                )
            else:
                st.info("当前模式下暂无已渲染的 PNG 图片。")
        else:
            st.info("输出目录尚未生成任何结果。")
