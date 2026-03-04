import streamlit as st
import os
import subprocess
import glob
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
NEURAL_BRDF_DIR = ROOT_DIR / "Neural-BRDF"
HYPER_BRDF_DIR = ROOT_DIR / "HyperBRDF"

def log_exp(msg, placeholder=None):
    if "train_logs" not in st.session_state:
        st.session_state.train_logs = []
    st.session_state.train_logs.append(msg)
    if placeholder:
        placeholder.text_area("训练实时日志", value="\n".join(st.session_state.train_logs[::-1]), height=300)

def list_merl_files(merl_dir):
    return [os.path.basename(f) for f in glob.glob(os.path.join(merl_dir, "*.binary"))]

def run_binary_to_npy(merl_dir, selected_merl, log_placeholder):
    if not selected_merl:
        st.warning("未选择材质文件")
        return
    st.session_state.train_logs = []
    script_path = NEURAL_BRDF_DIR / "binary_to_nbrdf" / "binary_to_nbrdf.py"
    target_path = os.path.join(merl_dir, selected_merl)
    cmd = ["python", str(script_path), target_path]
    log_exp(f"启动转换: {' '.join(cmd)}", log_placeholder)
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(NEURAL_BRDF_DIR / "binary_to_nbrdf") + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(NEURAL_BRDF_DIR / "binary_to_nbrdf"))
        for line in proc.stdout:
            log_exp(line.strip(), log_placeholder)
        proc.wait()
        if proc.returncode == 0:
            st.success("转换成功！权重已保存至 Neural-BRDF/binary_to_nbrdf/output")
        else:
            st.error(f"转换失败，退出码: {proc.returncode}")
    except Exception as e:
        st.error(f"执行出错: {str(e)}")
