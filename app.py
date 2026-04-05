import streamlit as st

from pages._modules import get_project_root, get_mitsuba_paths
from pages._modules import analysis_page, render_tool_page, training_page, ui_shell


st.set_page_config(page_title="MatReflect_NN", page_icon="◼", layout="wide")

ui_shell.init_shell_state()
ui_shell.inject_global_styles(st.session_state.ui_theme_mode)

root_dir = get_project_root()
_, mitsuba_path, _ = get_mitsuba_paths(root_dir)

# --- Top Navigation Bar ---
col_nav, col_theme = st.columns([5, 1], vertical_alignment="center")
with col_nav:
    active_module = st.radio(
        "Navigation",
        options=["render", "models", "analysis"],
        format_func=lambda x: {"render": "🎨 渲染可视化", "models": "🧠 网络模型管理", "analysis": "📊 材质结果分析"}[x],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state.ui_active_module = active_module

with col_theme:
    current = st.session_state.ui_theme_mode
    mode = st.radio(
        "Theme",
        options=["light", "dark"],
        format_func=lambda value: "🌞" if value == "light" else "🌙",
        horizontal=True,
        index=0 if current == "light" else 1,
        label_visibility="collapsed"
    )
    if mode != current:
        st.session_state.ui_theme_mode = mode
        st.rerun()

st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1.5rem; border-color: var(--line);' />", unsafe_allow_html=True)

# --- Main Workspace Layout ---
left_col, right_col = st.columns([1.2, 3.8], gap="large")

if active_module == "models":
    training_page.render_page(left_col, right_col)
elif active_module == "analysis":
    analysis_page.render_page(left_col, right_col)
else:
    render_tool_page.render_page(left_col, right_col)
