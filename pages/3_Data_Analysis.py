import streamlit as st
from pages._modules import analysis_page

st.set_page_config(page_title="数据分析 - MatReflect_NN", page_icon="📊", layout="wide")
analysis_page.render_page()
