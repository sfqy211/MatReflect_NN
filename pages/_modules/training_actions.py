import streamlit as st
import os
import subprocess
import glob
from pathlib import Path

import shutil

ROOT_DIR = Path(__file__).resolve().parents[2]
NEURAL_BRDF_DIR = ROOT_DIR / "Neural-BRDF"
HYPER_BRDF_DIR = ROOT_DIR / "HyperBRDF"
DATA_INPUTS_NPY = ROOT_DIR / "data" / "inputs" / "npy"

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
    
    # 确保目标输出目录存在
    os.makedirs(DATA_INPUTS_NPY, exist_ok=True)
    
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(NEURAL_BRDF_DIR / "binary_to_nbrdf") + os.pathsep + env.get("PYTHONPATH", "")
        
        # 记录转换前 output 目录的文件列表，以便后续移动
        output_dir = NEURAL_BRDF_DIR / "binary_to_nbrdf" / "output"
        
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(NEURAL_BRDF_DIR / "binary_to_nbrdf"))
        for line in proc.stdout:
            log_exp(line.strip(), log_placeholder)
        proc.wait()
        
        if proc.returncode == 0:
            # 移动生成的 npy 文件到指定目录
            basename = os.path.splitext(selected_merl)[0]
            generated_files = glob.glob(os.path.join(str(output_dir), f"{basename}*.npy"))
            
            if generated_files:
                for f in generated_files:
                    target_f = DATA_INPUTS_NPY / os.path.basename(f)
                    shutil.move(f, str(target_f))
                    log_exp(f"移动权重文件: {os.path.basename(f)} -> data/inputs/npy", log_placeholder)
                st.success(f"转换并移动成功！权重已存放在: {DATA_INPUTS_NPY}")
            else:
                st.warning("转换完成但未找到生成的权重文件，请检查脚本输出。")
        else:
            st.error(f"转换失败，退出码: {proc.returncode}")
    except Exception as e:
        st.error(f"执行出错: {str(e)}")
