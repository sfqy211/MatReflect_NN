import streamlit as st
import os
from pathlib import Path
from . import render_tool_actions as actions
from . import get_project_root

def render_page():
    actions.init_state()
    if not st.session_state.root_dir:
        st.session_state.root_dir = str(get_project_root())
    actions.ensure_mitsuba_state(st.session_state.root_dir)
    if not st.session_state.scene_path:
        st.session_state.scene_path = actions.get_default_scene_path(st.session_state.root_dir)
    st.sidebar.title("全局配置")
    st.sidebar.text_input("项目根目录", value=st.session_state.root_dir, key="root_dir")
    st.sidebar.text_input("Mitsuba 目录", value=st.session_state.mitsuba_dir, key="mitsuba_dir")
    st.sidebar.text_input("Mitsuba 可执行文件", value=st.session_state.mitsuba_exe, key="mitsuba_exe")
    st.sidebar.text_input("Mtsutil 可执行文件", value=st.session_state.mtsutil_exe, key="mtsutil_exe")
    root_dir = st.session_state.root_dir
    scene_paths = actions.list_scene_xmls(root_dir)
    if st.session_state.scene_path and st.session_state.scene_path not in scene_paths:
        scene_paths.insert(0, st.session_state.scene_path)
    display_map = {}
    for p in scene_paths:
        try:
            rel = str(Path(p).resolve().relative_to(Path(root_dir).resolve()))
            display_map[rel.replace("\\", "/")] = p
        except Exception:
            display_map[p] = p
    display_options = list(display_map.keys())
    current_display = None
    for label, path in display_map.items():
        if path == st.session_state.scene_path:
            current_display = label
            break
    if current_display is None and display_options:
        current_display = display_options[0]
    if display_options:
        selected_display = st.sidebar.selectbox("场景 XML", display_options, index=display_options.index(current_display) if current_display in display_options else 0, key="scene_path_select")
        st.session_state.scene_path = display_map.get(selected_display, st.session_state.scene_path)
    else:
        st.sidebar.text_input("场景 XML", key="scene_path")
    if st.sidebar.button("选择场景 XML 文件", key="scene_open_dialog", use_container_width=True):
        selected_paths = actions.open_file_dialog(root_dir, "请选择场景 XML", [("XML files", "*.xml"), ("All files", "*.*")])
        if selected_paths:
            st.session_state.scene_path = selected_paths[0]
            st.rerun()
    st.title("Mitsuba Render Tool")
    tabs = st.tabs(["批量渲染", "EXR 转 PNG", "编译", "日志"])
    with tabs[0]:
        st.header("Mitsuba 批量渲染")
        base_dir, input_dir_map, output_dir_map = actions.get_paths()
        if "input_dir" not in st.session_state:
            st.session_state.input_dir = str(input_dir_map.get("brdfs", ""))
        if "output_dir" not in st.session_state:
            st.session_state.output_dir = str(output_dir_map.get("brdfs", ""))
        render_mode_labels = {
            "brdfs": "GT / BRDF (.binary)",
            "fullbin": "HyperBRDF (.fullbin)",
            "npy": "Neural-BRDF (.npy)"
        }
        render_mode = st.radio(
            "输入类型",
            ["brdfs", "fullbin", "npy"],
            horizontal=True,
            key="render_mode",
            on_change=actions.on_render_mode_change,
            format_func=lambda v: render_mode_labels.get(v, v)
        )
        integrator_type = st.selectbox("积分器类型 (Integrator)", ["bdpt", "path"], index=0, key="integrator_type", help="bdpt: 双向路径追踪 (适合 MERL/Fullbin); path: 标准路径追踪")
        sample_count = st.number_input("采样数量 (Sample Count)", min_value=1, value=256, key="sample_count")
        auto_convert = st.checkbox("渲染后自动转换为 PNG", value=True, key="auto_convert")
        skip_existing = st.checkbox("跳过已存在文件", value=False, key="skip_existing")
        input_dir = st.text_input("输入目录", key="input_dir")
        output_dir = st.text_input("输出目录", key="output_dir")
        use_custom_cmd = st.checkbox("使用自定义渲染命令", value=False, key="use_custom_cmd")
        if use_custom_cmd:
            custom_cmd_str = st.text_input("自定义命令 (支持占位符: {mitsuba}, {input}, {output})", value='"{mitsuba}" -o "{output}" "{input}"', key="custom_cmd_str")
        else:
            custom_cmd_str = None
        render_files = actions.list_render_files(input_dir, render_mode)
        
        # Native File Dialog Button
        col_dialog, col_ref = st.columns([1, 1])
        with col_dialog:
            if st.button("📂 打开文件选择器 (Windows 原生)", key="render_open_dialog", use_container_width=True):
                # Determine file types
                ftypes = [("All files", "*.*")]
                if render_mode == "brdfs":
                    ftypes = [("Binary files", "*.binary"), ("All files", "*.*")]
                elif render_mode == "fullbin":
                    ftypes = [("Fullbin files", "*.fullbin"), ("All files", "*.*")]
                elif render_mode == "npy":
                    ftypes = [("NPY files", "*.npy"), ("All files", "*.*")]
                actions.update_selection_from_dialog(
                    input_dir,
                    "请选择待渲染文件",
                    ftypes,
                    render_files,
                    "render_selected",
                    "部分选择的文件不在当前输入目录中，已被自动忽略。请确保选择的文件位于配置的输入目录内。"
                )
                    
        with col_ref:
            if st.button("刷新文件列表", key="render_refresh", use_container_width=True):
                pass

        if st.button("🎯 选择预设测试集 (20个材质)", key="render_select_preset", use_container_width=True):
            actions.select_preset_test_set(render_files)

        render_selected = st.multiselect("待渲染文件列表", options=render_files, default=st.session_state.render_selected, key="render_selected")
        st.caption(f"已选择 {len(render_selected)} / {len(render_files)} 个文件")
        
        render_progress = st.progress(0)
        render_status = st.empty()
        render_log_placeholder = st.empty()
        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button("开始批量渲染"):
                actions.STOP_SIGNAL.clear()
                actions.render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, render_progress, render_status, base_dir, render_log_placeholder, custom_cmd_str, integrator_type, sample_count)
        with col_stop:
            if st.button("停止渲染"):
                if not actions.STOP_SIGNAL:
                    actions.STOP_SIGNAL.append(True)
                actions.log("已发送停止信号，将在当前文件完成后中断...")
    with tabs[1]:
        st.header("EXR 转 PNG")
        base_dir, _, output_dir_map = actions.get_paths()
        output_dir = output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "binary")
        conv_input_dir = st.text_input("EXR 输入目录", value=str(Path(output_dir) / "exr"), key="conv_input_dir")
        conv_output_dir = st.text_input("PNG 输出目录", value=str(Path(output_dir) / "png"), key="conv_output_dir")
        conv_files = actions.list_exr_files(conv_input_dir)
        
        # Native File Dialog Button (EXR)
        c_dialog, c_ref = st.columns([1, 1])
        with c_dialog:
            if st.button("📂 打开文件选择器 (Windows 原生)", key="conv_open_dialog", use_container_width=True):
                ftypes = [("EXR files", "*.exr"), ("All files", "*.*")]
                actions.update_selection_from_dialog(
                    conv_input_dir,
                    "请选择 EXR 文件",
                    ftypes,
                    conv_files,
                    "conv_selected"
                )
                    
        with c_ref:
            if st.button("刷新文件列表", key="conv_refresh", use_container_width=True):
                pass

        conv_selected = st.multiselect("待转换 EXR 文件列表", options=conv_files, default=st.session_state.conv_selected, key="conv_selected")
        st.caption(f"已选择 {len(conv_selected)} / {len(conv_files)} 个文件")
        
        conv_progress = st.progress(0)
        conv_status = st.empty()
        conv_log_placeholder = st.empty()
        if st.button("开始 EXR -> PNG 转换"):
            actions.convert_exr(conv_selected, conv_input_dir, conv_output_dir, conv_progress, conv_status, conv_log_placeholder)
    with tabs[2]:
        st.header("编译")
        compile_presets = [
            {
                "label": "默认并行编译",
                "cmd": "scons --parallelize",
                "desc": "使用 SCons 并行构建 Mitsuba 目标。"
            },
            {
                "label": "强制全量重编译",
                "cmd": "scons --parallelize --force",
                "desc": "忽略缓存时间戳，强制重新编译全部目标。"
            },
            {
                "label": "清除编译缓存",
                "cmd": "scons -c",
                "desc": "清理已生成的构建产物与缓存。"
            },
            {
                "label": "详细日志编译",
                "cmd": "scons --parallelize --debug=explain",
                "desc": "输出更详细的依赖与重建原因，便于排查问题。"
            },
            {
                "label": "自定义命令",
                "cmd": "",
                "desc": "使用自定义 SCons 命令。"
            }
        ]
        preset_labels = [p["label"] for p in compile_presets]
        preset_map = {p["label"]: p for p in compile_presets}
        if "compile_preset" not in st.session_state:
            st.session_state.compile_preset = preset_labels[0]
        def on_compile_preset_change():
            preset = preset_map.get(st.session_state.compile_preset)
            if preset and preset["label"] != "自定义命令":
                st.session_state.compile_cmd_display = preset["cmd"]
        selected_preset = st.selectbox(
            "编译预设",
            preset_labels,
            index=preset_labels.index(st.session_state.compile_preset),
            key="compile_preset",
            on_change=on_compile_preset_change
        )
        preset = preset_map.get(selected_preset)
        st.caption(preset["desc"])
        if selected_preset == "自定义命令":
            compile_cmd = st.text_input("编译命令", value=st.session_state.get("compile_cmd", "scons --parallelize"), key="compile_cmd")
        else:
            if st.session_state.get("compile_cmd_display") != preset["cmd"]:
                st.session_state.compile_cmd_display = preset["cmd"]
            st.text_input("编译命令", value=st.session_state.compile_cmd_display, key="compile_cmd_display", disabled=True)
            compile_cmd = preset["cmd"]
        conda_env = st.text_input("Conda 环境名", value="mitsuba-build", key="conda_env")
        vcvarsall_path = st.text_input("vcvarsall.bat 路径 (可选)", value=st.session_state.get("vcvarsall_path", actions.DEFAULT_VCVARSALL_PATH), key="vcvarsall_path")
        st.caption("可填写 vcvarsall.bat 或 VS2017 工具快捷方式 .lnk，留空将自动检测")
        st.caption("并行编译若命中 mt.exe manifest 写入冲突，将自动回退为串行增量补编译")
        compile_log_placeholder = st.empty()
        if st.button("开始编译"):
            actions.run_compile(compile_cmd, conda_env, compile_log_placeholder, selected_preset, vcvarsall_path)
    with tabs[3]:
        st.header("日志")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("清空日志"):
                actions.clear_logs()
        with col2:
            st.write(f"日志条数: {len(st.session_state.logs)}")
        st.text_area("日志输出", value="\n".join(st.session_state.logs), height=400)
