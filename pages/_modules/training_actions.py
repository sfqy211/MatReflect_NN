import streamlit as st
import os
import subprocess
import glob
from pathlib import Path

import shutil

from . import get_project_root

ROOT_DIR = get_project_root()
NEURAL_BRDF_DIR = ROOT_DIR / "Neural-BRDF"
HYPER_BRDF_DIR = ROOT_DIR / "HyperBRDF"
DATA_INPUTS_BRDFS = ROOT_DIR / "data" / "inputs" / "binary"
DATA_INPUTS_NPY = ROOT_DIR / "data" / "inputs" / "npy"
DATA_INTERMEDIATE_H5 = NEURAL_BRDF_DIR / "data" / "merl_nbrdf"
BINARY_TO_NBRDF_DIR = NEURAL_BRDF_DIR / "binary_to_nbrdf"
PYTORCH_SCRIPT = BINARY_TO_NBRDF_DIR / "pytorch_code" / "train_NBRDF_pytorch.py"
KERAS_SCRIPT = BINARY_TO_NBRDF_DIR / "binary_to_nbrdf.py"
H5_TO_NPY_SCRIPT = BINARY_TO_NBRDF_DIR / "h5_to_npy.py"

# HyperBRDF 相关脚本
HB_MAIN_SCRIPT = HYPER_BRDF_DIR / "main.py"
HB_TEST_SCRIPT = HYPER_BRDF_DIR / "test.py"
HB_PT_TO_FULLBIN_SCRIPT = HYPER_BRDF_DIR / "pt_to_fullmerl.py"
HB_MEDIAN_SCRIPT = HYPER_BRDF_DIR / "compute_median.py"
HB_DEFAULT_MODEL = HYPER_BRDF_DIR / "results" / "test" / "MERL" / "checkpoint.pt"

HB_PROJECTS = {
    "hyperbrdf": {
        "label": "HyperBRDF",
        "dir": HYPER_BRDF_DIR,
        "main_script": HYPER_BRDF_DIR / "main.py",
        "test_script": HYPER_BRDF_DIR / "test.py",
        "pt_to_fullbin_script": HYPER_BRDF_DIR / "pt_to_fullmerl.py",
        "median_script": HYPER_BRDF_DIR / "compute_median.py",
        "fit_teacher_script": None,
        "default_model": HYPER_BRDF_DIR / "results" / "test" / "MERL" / "checkpoint.pt",
        "default_results_dir": HYPER_BRDF_DIR / "results",
        "default_extract_dir": HYPER_BRDF_DIR / "results" / "extracted_pts",
        "supports_teacher": False,
    },
}


def get_hb_project_config(project_variant="hyperbrdf"):
    return HB_PROJECTS.get(project_variant, HB_PROJECTS["hyperbrdf"])


def _run_streamlit_command(cmd, env, cwd, log_placeholder, start_message, success_message, error_message):
    log_exp(start_message, log_placeholder)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(cwd),
        shell=True,
    )
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            log_exp(line.strip(), log_placeholder)
    proc.wait()
    if proc.returncode == 0:
        st.success(success_message)
    else:
        st.error(f"{error_message} (退出码: {proc.returncode})")

def log_exp(msg, placeholder=None):
    if "train_logs" not in st.session_state:
        st.session_state.train_logs = []
    # 清理控制字符
    clean_msg = msg.replace("\b", "").replace("\r", "")
    st.session_state.train_logs.append(clean_msg)
    if placeholder:
        placeholder.code("\n".join(st.session_state.train_logs[::-1]), language=None)

def list_merl_files(merl_dir, dataset="MERL"):
    pattern = "*.binary" if dataset == "MERL" else "*.csv"
    return [os.path.basename(f) for f in glob.glob(os.path.join(merl_dir, pattern))]

def resolve_binary_paths(merl_dir, selected_merls):
    return [os.path.join(merl_dir, f) for f in selected_merls]

def list_h5_files(h5_dir):
    return [os.path.basename(f) for f in glob.glob(os.path.join(h5_dir, "*.h5"))]

def run_pytorch_training(merl_dir, selected_merls, epochs, output_dir, log_placeholder, device="cpu"):
    if not selected_merls:
        st.warning("未选择材质文件")
        return
    os.makedirs(output_dir, exist_ok=True)
    st.session_state.train_logs = []
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(BINARY_TO_NBRDF_DIR) + os.pathsep + str(PYTORCH_SCRIPT.parent) + os.pathsep + env.get("PYTHONPATH", "")
    for merl in resolve_binary_paths(merl_dir, selected_merls):
        cmd = ["python", str(PYTORCH_SCRIPT), merl, "--outpath", str(output_dir), "--epochs", str(epochs), "--device", device]
        log_exp(f"启动 PyTorch 训练 ({device}): {' '.join(cmd)}", log_placeholder)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(PYTORCH_SCRIPT.parent), bufsize=1)
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                log_exp(line.strip(), log_placeholder)
        proc.wait()
        if proc.returncode == 0:
            st.success(f"训练完成: {os.path.basename(merl)}")
        else:
            st.error(f"训练失败: {os.path.basename(merl)} (退出码: {proc.returncode})")

def run_h5_to_npy(h5_paths, output_dir, log_placeholder):
    if not h5_paths:
        st.warning("未选择 .h5 文件")
        return
    os.makedirs(output_dir, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(BINARY_TO_NBRDF_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    
    # 同样使用 nbrdf-train 环境运行 H5 转换脚本
    # 使用 shell=True 兼容 Windows 环境变量
    cmd = ["conda", "run", "--no-capture-output", "-n", "nbrdf-train", "python", str(H5_TO_NPY_SCRIPT), *h5_paths, "--destdir", str(output_dir)]
    log_exp(f"启动 h5 -> npy 转换 (nbrdf-train): {' '.join(cmd)}", log_placeholder)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(BINARY_TO_NBRDF_DIR), bufsize=1, shell=True)
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            log_exp(line.strip(), log_placeholder)
    proc.wait()
    if proc.returncode == 0:
        st.success(f"转换完成，权重已存放在: {output_dir}")
    else:
        st.error(f"h5 转换失败，退出码: {proc.returncode}")

def run_keras_training(merl_dir, selected_merls, cuda_device, h5_output_dir, npy_output_dir, log_placeholder):
    if not selected_merls:
        st.warning("未选择材质文件")
        return
    st.session_state.train_logs = []
    os.makedirs(h5_output_dir, exist_ok=True)
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(BINARY_TO_NBRDF_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["CUDA_VISIBLE_DEVICES"] = cuda_device
    binary_paths = resolve_binary_paths(merl_dir, selected_merls)
    
    # 使用 nbrdf-train 环境运行 Keras 训练
    # 在 Windows 上，subprocess 可能找不到 'conda'，需要用 shell=True 或绝对路径
    cmd = ["conda", "run", "--no-capture-output", "-n", "nbrdf-train", "python", str(KERAS_SCRIPT), *binary_paths, "--cuda_device", cuda_device]
    log_exp(f"启动 Keras 训练 (nbrdf-train): {' '.join(cmd)}", log_placeholder)
    
    # Keras 脚本默认在当前工作目录生成文件，所以我们要在 H5 目标目录下运行，或者运行后移动
    # 鉴于脚本内部使用了相对路径引用 coords 等模块，我们在 BINARY_TO_NBRDF_DIR 运行更稳妥，然后移动结果
    # Windows 下使用 shell=True 来正确解析 conda 命令
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(BINARY_TO_NBRDF_DIR), bufsize=1, shell=True)
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            log_exp(line.strip(), log_placeholder)
    proc.wait()
    
    if proc.returncode != 0:
        st.error(f"Keras 训练失败，退出码: {proc.returncode}")
        return
    
    # 移动生成的 h5 和 json 文件到 h5_output_dir
    h5_paths = []
    for merl in selected_merls:
        basename = os.path.splitext(merl)[0]
        # 脚本在 BINARY_TO_NBRDF_DIR 下生成文件
        src_h5 = BINARY_TO_NBRDF_DIR / f"{basename}.h5"
        src_json = BINARY_TO_NBRDF_DIR / f"{basename}.json"
        src_loss = BINARY_TO_NBRDF_DIR / f"lossplot_{basename}.png"
        
        target_h5 = Path(h5_output_dir) / f"{basename}.h5"
        
        if src_h5.exists():
            shutil.move(str(src_h5), str(target_h5))
            if src_json.exists():
                shutil.move(str(src_json), str(Path(h5_output_dir) / f"{basename}.json"))
            if src_loss.exists():
                shutil.move(str(src_loss), str(Path(h5_output_dir) / f"lossplot_{basename}.png"))
            
            h5_paths.append(str(target_h5))
            log_exp(f"已移动中间文件: {basename}.h5/json -> {h5_output_dir}", log_placeholder)
            
    if h5_paths:
        run_h5_to_npy(h5_paths, npy_output_dir, log_placeholder)
    else:
        st.warning("训练完成但未找到对应 .h5 文件，请检查输出目录")

def _build_hb_env(project_variant="hyperbrdf"):
    config = get_hb_project_config(project_variant)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(config["dir"]) + os.pathsep + env.get("PYTHONPATH", "")
    return config, env


def _run_logged_process(cmd, env, cwd, log_placeholder, start_message):
    log_exp(start_message, log_placeholder)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(cwd),
        shell=True,
    )
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            log_exp(line.strip(), log_placeholder)
    proc.wait()
    return proc.returncode


def run_hb_training(
    merl_dir,
    output_dir,
    epochs,
    sparse_samples,
    latent_dim,
    log_placeholder,
    conda_env="hyperbrdf",
    kl_weight=0.1,
    fw_weight=0.1,
    dataset="MERL",
    lr=5e-5,
    keepon=False,
    train_subset=0,
    train_seed=42,
    project_variant="hyperbrdf",
):
    if not os.path.exists(merl_dir):
        st.warning(f"目录不存在: {merl_dir}")
        return
    st.session_state.train_logs = []
    os.makedirs(output_dir, exist_ok=True)
    config, env = _build_hb_env(project_variant)
    cmd = [
        "conda", "run", "--no-capture-output", "-n", conda_env, "python", str(config["main_script"]),
        "--destdir", str(output_dir),
        "--binary", str(merl_dir),
        "--dataset", dataset,
        "--epochs", str(epochs),
        "--sparse_samples", str(sparse_samples),
        "--kl_weight", str(kl_weight),
        "--fw_weight", str(fw_weight),
        "--lr", str(lr),
        "--train_subset", str(train_subset),
        "--train_seed", str(train_seed),
    ]
    if keepon:
        cmd.append("--keepon")
    returncode = _run_logged_process(
        cmd,
        env,
        config["dir"],
        log_placeholder,
        f"启动 {config['label']} 训练: {' '.join(cmd)}",
    )
    if returncode == 0:
        st.success(f"训练完成，模型已保存至: {output_dir}")
    else:
        st.error(f"训练失败 (退出码: {returncode})")

def run_hb_compute_median(output_dir, log_placeholder, conda_env="hyperbrdf", project_variant="hyperbrdf"):
    st.session_state.train_logs = []
    os.makedirs(output_dir, exist_ok=True)
    config, env = _build_hb_env(project_variant)
    env["HB_MEDIAN_OUTPUT_DIR"] = str(output_dir)
    cmd = ["conda", "run", "--no-capture-output", "-n", conda_env, "python", str(config["median_script"])]
    returncode = _run_logged_process(
        cmd,
        env,
        config["dir"],
        log_placeholder,
        f"启动 {config['label']} 中位数计算: {' '.join(cmd)}",
    )
    if returncode == 0:
        st.success(f"中位数计算完成，输出目录: {output_dir}")
    else:
        st.error(f"中位数计算失败 (退出码: {returncode})")


def run_hb_extraction(
    merl_dir,
    selected_merls,
    model_path,
    output_dir,
    log_placeholder,
    conda_env="hyperbrdf",
    dataset="MERL",
    project_variant="hyperbrdf",
    sparse_samples=4000,
):
    if dataset == "MERL" and not selected_merls:
        st.warning("未选择材质文件")
        return
    st.session_state.train_logs = []
    os.makedirs(output_dir, exist_ok=True)
    config, env = _build_hb_env(project_variant)

    if dataset == "EPFL":
        cmd = [
            "conda", "run", "--no-capture-output", "-n", conda_env, "python", str(config["test_script"]),
            "--model", str(model_path),
            "--binary", str(merl_dir),
            "--destdir", str(output_dir),
            "--dataset", "EPFL",
        ]
        returncode = _run_logged_process(
            cmd,
            env,
            config["dir"],
            log_placeholder,
            f"启动 {config['label']} 参数提取: EPFL 目录",
        )
        if returncode == 0:
            st.success("参数提取完成: EPFL")
        else:
            st.error(f"参数提取失败: EPFL (退出码: {returncode})")
    else:
        for merl in selected_merls:
            binary_path = os.path.join(merl_dir, merl)
            cmd = [
                "conda", "run", "--no-capture-output", "-n", conda_env, "python", str(config["test_script"]),
                "--model", str(model_path),
                "--binary", str(binary_path),
                "--destdir", str(output_dir),
                "--dataset", "MERL",
            ]
            returncode = _run_logged_process(
                cmd,
                env,
                config["dir"],
                log_placeholder,
                f"启动 {config['label']} 参数提取: {merl}",
            )
            if returncode == 0:
                st.success(f"参数提取完成: {merl}")
            else:
                st.error(f"参数提取失败: {merl} (退出码: {returncode})")

def run_hb_to_fullbin(
    pt_dir,
    selected_pts,
    output_dir,
    log_placeholder,
    conda_env="hyperbrdf",
    dataset="MERL",
    project_variant="hyperbrdf",
):
    if not selected_pts:
        st.warning("未选择 .pt 文件")
        return
    st.session_state.train_logs = []
    os.makedirs(output_dir, exist_ok=True)
    config, env = _build_hb_env(project_variant)

    for pt_name in selected_pts:
        pt_path = os.path.join(pt_dir, pt_name)
        cmd = [
            "conda", "run", "--no-capture-output", "-n", conda_env, "python", str(config["pt_to_fullbin_script"]),
            str(pt_path), str(output_dir), "--dataset", dataset,
        ]
        returncode = _run_logged_process(
            cmd,
            env,
            config["dir"],
            log_placeholder,
            f"启动 {config['label']} pt -> fullbin 转换: {pt_name}",
        )
        if returncode == 0:
            st.success(f"转换完成: {pt_name}")
        else:
            st.error(f"转换失败: {pt_name} (退出码: {returncode})")

def list_pt_files(pt_dir):
    return [os.path.basename(f) for f in glob.glob(os.path.join(pt_dir, "*.pt"))]
