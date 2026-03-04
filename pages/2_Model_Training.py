import streamlit as st
from pages._modules import training_page

st.set_page_config(page_title="模型训练 - MatReflect_NN", page_icon="🧠", layout="wide")
training_page.render_page()
