import streamlit as st
import os
from pathlib import Path
from . import render_tool_actions as actions

def render_page():
    actions.init_state()
    st.sidebar.title("全局配置")
    st.sidebar.text_input("项目根目录", key="root_dir")
    st.sidebar.text_input("Mitsuba 目录", key="mitsuba_dir")
    st.sidebar.text_input("Mitsuba 可执行文件", key="mitsuba_exe")
    st.sidebar.text_input("Mtsutil 可执行文件", key="mtsutil_exe")
    st.sidebar.text_input("场景 XML", key="scene_path")
    st.title("Mitsuba Render Tool")
    tabs = st.tabs(["批量渲染", "EXR 转 PNG", "编译", "日志"])
    with tabs[0]:
        st.header("Mitsuba 批量渲染")
        base_dir, input_dir_map, output_dir_map = actions.get_paths()
        if "input_dir" not in st.session_state:
            st.session_state.input_dir = str(input_dir_map.get("brdfs", ""))
        if "output_dir" not in st.session_state:
            st.session_state.output_dir = str(output_dir_map.get("brdfs", ""))
        render_mode = st.radio("输入类型", ["brdfs", "fullbin", "npy"], horizontal=True, key="render_mode", on_change=actions.on_render_mode_change)
        integrator_type = st.selectbox("积分器类型 (Integrator)", ["bdpt", "path"], index=0, key="integrator_type", help="bdpt: 双向路径追踪 (适合 MERL/Fullbin); path: 标准路径追踪")
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
                
                selected_paths = actions.open_file_dialog(input_dir, "请选择待渲染文件", ftypes)
                if selected_paths:
                    # Filter files to ensure they are in the input directory list to avoid path issues
                    selected_names = [os.path.basename(p) for p in selected_paths]
                    valid_names = [n for n in selected_names if n in render_files]
                    
                    if len(valid_names) < len(selected_names):
                        st.warning("部分选择的文件不在当前输入目录中，已被自动忽略。请确保选择的文件位于配置的输入目录内。")
                    
                    st.session_state.render_selected = valid_names
                    st.rerun()
                    
        with col_ref:
            if st.button("刷新文件列表", key="render_refresh", use_container_width=True):
                pass

        render_selected = st.multiselect("待渲染文件列表", options=render_files, default=st.session_state.render_selected, key="render_selected")
        st.caption(f"已选择 {len(render_selected)} / {len(render_files)} 个文件")
        
        render_progress = st.progress(0)
        render_status = st.empty()
        render_log_placeholder = st.empty()
        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button("开始批量渲染"):
                actions.STOP_SIGNAL.clear()
                actions.render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, render_progress, render_status, base_dir, render_log_placeholder, custom_cmd_str, integrator_type)
        with col_stop:
            if st.button("停止渲染"):
                if not actions.STOP_SIGNAL:
                    actions.STOP_SIGNAL.append(True)
                actions.log("已发送停止信号，将在当前文件完成后中断...")
    with tabs[1]:
        st.header("EXR 转 PNG")
        base_dir, _, output_dir_map = actions.get_paths()
        output_dir = output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs")
        conv_input_dir = st.text_input("EXR 输入目录", value=str(Path(output_dir) / "exr"), key="conv_input_dir")
        conv_output_dir = st.text_input("PNG 输出目录", value=str(Path(output_dir) / "png"), key="conv_output_dir")
        conv_files = actions.list_exr_files(conv_input_dir)
        
        # Native File Dialog Button (EXR)
        c_dialog, c_ref = st.columns([1, 1])
        with c_dialog:
            if st.button("📂 打开文件选择器 (Windows 原生)", key="conv_open_dialog", use_container_width=True):
                ftypes = [("EXR files", "*.exr"), ("All files", "*.*")]
                
                selected_paths = actions.open_file_dialog(conv_input_dir, "请选择 EXR 文件", ftypes)
                if selected_paths:
                    selected_names = [os.path.basename(p) for p in selected_paths]
                    valid_names = [n for n in selected_names if n in conv_files]
                    
                    if len(valid_names) < len(selected_names):
                        st.warning("部分选择的文件不在当前输入目录中，已被自动忽略。")
                    
                    st.session_state.conv_selected = valid_names
                    st.rerun()
                    
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
        compile_cmd = st.text_input("编译命令", value="scons --parallelize", key="compile_cmd")
        conda_env = st.text_input("Conda 环境名", value="mitsuba-build", key="conda_env")
        compile_log_placeholder = st.empty()
        if st.button("开始编译"):
            actions.run_compile(compile_cmd, conda_env, compile_log_placeholder)
    with tabs[3]:
        st.header("日志")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("清空日志"):
                actions.clear_logs()
        with col2:
            st.write(f"日志条数: {len(st.session_state.logs)}")
        st.text_area("日志输出", value="\n".join(st.session_state.logs), height=400)
