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
    tabs = st.tabs(["批量渲染", "EXR 转 PNG", "图片预览", "编译", "量化评估", "网格拼图", "对比拼图", "日志"])
    with tabs[0]:
        st.header("Mitsuba 批量渲染")
        base_dir, input_dir_map, output_dir_map = actions.get_paths()
        if "input_dir" not in st.session_state:
            st.session_state.input_dir = str(input_dir_map.get("brdfs", ""))
        if "output_dir" not in st.session_state:
            st.session_state.output_dir = str(output_dir_map.get("brdfs", ""))
        render_mode = st.radio("输入类型", ["brdfs", "fullbin", "npy"], horizontal=True, key="render_mode", on_change=actions.on_render_mode_change)
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
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("全选", key="render_select_all"):
                st.session_state.render_selected = render_files
        with col_b:
            if st.button("全不选", key="render_select_none"):
                st.session_state.render_selected = []
        with col_c:
            if st.button("刷新列表", key="render_refresh"):
                pass
        render_selected = st.multiselect("待渲染文件", options=render_files, default=st.session_state.render_selected, key="render_selected")
        render_progress = st.progress(0)
        render_status = st.empty()
        render_log_placeholder = st.empty()
        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button("开始批量渲染"):
                actions.STOP_SIGNAL.clear()
                actions.render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, render_progress, render_status, base_dir, render_log_placeholder, custom_cmd_str)
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
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            if st.button("全选", key="conv_select_all"):
                st.session_state.conv_selected = conv_files
        with col_c2:
            if st.button("全不选", key="conv_select_none"):
                st.session_state.conv_selected = []
        with col_c3:
            if st.button("刷新列表", key="conv_refresh"):
                pass
        conv_selected = st.multiselect("待转换 EXR 文件", options=conv_files, default=st.session_state.conv_selected, key="conv_selected")
        conv_progress = st.progress(0)
        conv_status = st.empty()
        conv_log_placeholder = st.empty()
        if st.button("开始 EXR -> PNG 转换"):
            actions.convert_exr(conv_selected, conv_input_dir, conv_output_dir, conv_progress, conv_status, conv_log_placeholder)
    with tabs[2]:
        st.header("图片结果预览")
        base_dir, _, output_dir_map = actions.get_paths()
        if "preview_dir" not in st.session_state:
            st.session_state.preview_dir = str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png")
        preview_dir_type = st.radio("预览类型", ["brdfs", "fullbin", "npy", "grids", "comparisons"], horizontal=True, key="preview_dir_type", on_change=actions.on_preview_dir_type_change)
        preview_dir = st.text_input("预览目录", key="preview_dir")
        if os.path.exists(preview_dir):
            image_files = sorted([f for f in os.listdir(preview_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if image_files:
                col1, col2 = st.columns([1, 3])
                with col1:
                    selected_img = st.selectbox("选择图片", options=image_files, key="preview_selected_img")
                with col2:
                    if selected_img:
                        img_path = os.path.join(preview_dir, selected_img)
                        st.image(img_path, caption=selected_img, use_container_width=True)
                        st.info(f"文件名: {selected_img} | 路径: {img_path}")
                    else:
                        st.write("请从左侧选择一张图片进行预览。")
            else:
                st.warning("该目录下没有图片文件。")
        else:
            st.error(f"目录不存在: {preview_dir}")
    with tabs[3]:
        st.header("编译")
        compile_cmd = st.text_input("编译命令", value="scons --parallelize", key="compile_cmd")
        conda_env = st.text_input("Conda 环境名", value="py27", key="conda_env")
        compile_log_placeholder = st.empty()
        if st.button("开始编译"):
            actions.run_compile(compile_cmd, conda_env, compile_log_placeholder)
    with tabs[4]:
        st.header("量化评估")
        base_dir, _, output_dir_map = actions.get_paths()
        eval_gt_dir = st.text_input("GT (BRDFs) PNG 目录", value=str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png"), key="eval_gt_dir")
        eval_method1_dir = st.text_input("Method1 (FullBin) PNG 目录", value=str(output_dir_map.get("fullbin", base_dir / "data" / "outputs" / "fullbin") / "png"), key="eval_method1_dir")
        eval_method2_dir = st.text_input("Method2 (NPY) PNG 目录", value=str(output_dir_map.get("npy", base_dir / "data" / "outputs" / "npy") / "png"), key="eval_method2_dir")
        eval_progress = st.progress(0)
        eval_status = st.empty()
        if st.button("开始量化评估"):
            actions.run_evaluation(eval_gt_dir, eval_method1_dir, eval_method2_dir, eval_progress, eval_status)
        if st.session_state.eval_result:
            table_data = []
            for k, v in st.session_state.eval_result.items():
                table_data.append({"Comparison": k, "PSNR (dB)": float(v[0]), "SSIM": float(v[1]), "Delta E": float(v[2])})
            st.table(table_data)
    with tabs[5]:
        st.header("网格拼图")
        base_dir, _, output_dir_map = actions.get_paths()
        grid_input_dir = st.text_input("图片输入目录", value=str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png"), key="grid_input_dir")
        grid_output_dir = st.text_input("网格图输出目录", value=str(base_dir / "data" / "outputs" / "grids"), key="grid_output_dir")
        grid_filename = st.text_input("输出文件名", value="merged_grid.png", key="grid_filename")
        grid_show_names = st.checkbox("显示文件名", value=True, key="grid_show_names")
        grid_cell_width = st.number_input("单图宽度", min_value=64, max_value=1024, value=256, key="grid_cell_width")
        grid_padding = st.number_input("间距", min_value=0, max_value=100, value=10, key="grid_padding")
        if st.button("生成网格大图"):
            os.makedirs(grid_output_dir, exist_ok=True)
            grid_output_path = os.path.join(grid_output_dir, grid_filename)
            actions.run_grid_generation(grid_input_dir, grid_output_path, grid_show_names, grid_cell_width, grid_padding)
    with tabs[6]:
        st.header("对比拼图")
        base_dir, _, output_dir_map = actions.get_paths()
        eval_gt_dir = st.text_input("GT (BRDFs) PNG 目录", value=str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png"), key="comp_eval_gt_dir")
        eval_method1_dir = st.text_input("Method1 (FullBin) PNG 目录", value=str(output_dir_map.get("fullbin", base_dir / "data" / "outputs" / "fullbin") / "png"), key="comp_eval_method1_dir")
        eval_method2_dir = st.text_input("Method2 (NPY) PNG 目录", value=str(output_dir_map.get("npy", base_dir / "data" / "outputs" / "npy") / "png"), key="comp_eval_method2_dir")
        comp_output_dir = st.text_input("对比图输出目录", value=str(base_dir / "data" / "outputs" / "comparisons"), key="comp_output_dir")
        comp_labels = st.text_input("标题文本(逗号分隔)", value="Ground Truth,FullBin,Neural BRDF", key="comp_labels")
        comp_show_label = st.checkbox("添加列标题", value=True, key="comp_show_label")
        comp_show_filename = st.checkbox("添加文件名", value=True, key="comp_show_filename")
        if st.button("生成对比拼图"):
            actions.run_comp_generation(eval_gt_dir, eval_method1_dir, eval_method2_dir, comp_output_dir, comp_labels, comp_show_label, comp_show_filename)
    with tabs[7]:
        st.header("日志")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("清空日志"):
                actions.clear_logs()
        with col2:
            st.write(f"日志条数: {len(st.session_state.logs)}")
        st.text_area("日志输出", value="\n".join(st.session_state.logs), height=400)
