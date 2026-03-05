import streamlit as st
import os
from pathlib import Path
from . import render_tool_actions as actions

def render_page():
    actions.init_state()
    st.title("📊 数据分析与评估")
    
    tabs = st.tabs(["图片预览", "量化评估", "网格拼图", "对比拼图"])
    
    with tabs[0]:
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
            
    with tabs[1]:
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
            
    with tabs[2]:
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
            
    with tabs[3]:
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
