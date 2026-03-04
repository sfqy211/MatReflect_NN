import streamlit as st
from pages._modules import render_tool_page

st.set_page_config(page_title="Mitsuba 渲染工具", page_icon="🎨", layout="wide")
render_tool_page.render_page()
