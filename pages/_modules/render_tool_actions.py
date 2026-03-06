import streamlit as st
import os
import subprocess
from pathlib import Path
import glob
import math
import xml.etree.ElementTree as ET
import numpy as np
import cv2
from skimage import metrics, color
import concurrent.futures
from PIL import Image, ImageDraw, ImageFont
import fnmatch
import tkinter as tk
from tkinter import filedialog

STOP_SIGNAL = []

def open_file_dialog(initial_dir, title="选择文件", filetypes=None):
    """
    Opens a native file dialog to select multiple files.
    """
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Make the dialog appear on top
        
        file_paths = filedialog.askopenfilenames(
            initialdir=initial_dir,
            title=title,
            filetypes=filetypes
        )
        
        root.destroy()
        return file_paths
    except Exception as e:
        st.error(f"无法打开文件选择器: {e}")
        return []

def init_state():
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "render_selected" not in st.session_state:
        st.session_state.render_selected = []
    if "conv_selected" not in st.session_state:
        st.session_state.conv_selected = []
    if "stop_render" not in st.session_state:
        st.session_state.stop_render = False
    if "eval_result" not in st.session_state:
        st.session_state.eval_result = None
    if "preview_dir_type" not in st.session_state:
        st.session_state.preview_dir_type = "brdfs"
    if "preview_selected_img" not in st.session_state:
        st.session_state.preview_selected_img = None
    if "root_dir" not in st.session_state or not st.session_state.root_dir:
        # Use CWD as default if explicit path resolution fails or is empty
        st.session_state.root_dir = os.getcwd()
        
    if "mitsuba_dir" not in st.session_state or not st.session_state.mitsuba_dir:
        local_mitsuba = Path(st.session_state.root_dir) / "mitsuba" / "dist"
        if local_mitsuba.exists():
            st.session_state.mitsuba_dir = str(local_mitsuba)
        else:
            st.session_state.mitsuba_dir = r"d:\mitsuba\dist"
            
    if "mitsuba_exe" not in st.session_state or not st.session_state.mitsuba_exe:
        st.session_state.mitsuba_exe = str(Path(st.session_state.mitsuba_dir) / "mitsuba.exe")
        
    if "mtsutil_exe" not in st.session_state or not st.session_state.mtsutil_exe:
        st.session_state.mtsutil_exe = str(Path(st.session_state.mitsuba_dir) / "mtsutil.exe")
        
    if "scene_path" not in st.session_state or not st.session_state.scene_path:
        st.session_state.scene_path = str(Path(st.session_state.root_dir) / "scene" / "scene_merl.xml")

def log(msg, placeholder=None):
    clean_msg = msg.replace("\b", "").replace("\r", "")
    st.session_state.logs.append(clean_msg)
    if placeholder:
        recent_logs = "\n".join(st.session_state.logs[::-1][:20])
        placeholder.text_area("实时日志 (最新在顶部)", value=recent_logs, height=200)

def clear_logs():
    st.session_state.logs = []

def get_paths():
    base_dir = Path(st.session_state.root_dir)
    input_dir_map = {
        "brdfs": base_dir / "data" / "inputs" / "brdfs",
        "fullbin": base_dir / "data" / "inputs" / "fullbin",
        "npy": base_dir / "data" / "inputs" / "npy"
    }
    output_dir_map = {
        "brdfs": base_dir / "data" / "outputs" / "brdfs",
        "fullbin": base_dir / "data" / "outputs" / "fullbin",
        "npy": base_dir / "data" / "outputs" / "npy"
    }
    return base_dir, input_dir_map, output_dir_map

def list_render_files(input_dir, render_mode):
    if not os.path.exists(input_dir):
        return []
    if render_mode == "npy":
        files = sorted(glob.glob(os.path.join(input_dir, "*fc1.npy")))
        return [os.path.basename(f) for f in files]
    ext = "*.binary" if render_mode == "brdfs" else "*.fullbin"
    return sorted([os.path.basename(p) for p in glob.glob(os.path.join(input_dir, ext))])

def configure_bsdf_smart(bsdf_node, filename):
    for child in list(bsdf_node):
        if child.tag == "bsdf":
            bsdf_node.remove(child)
    name = filename.lower()
    is_metal = False
    metal_material = "Cu"
    if "gold" in name:
        is_metal = True
        metal_material = "Au"
    elif "silver" in name:
        is_metal = True
        metal_material = "Ag"
    elif "aluminium" in name or "alum-" in name:
        is_metal = True
        metal_material = "Al"
    elif "chrome" in name or "steel" in name or "ss440" in name:
        is_metal = True
        metal_material = "Cr"
    elif "nickel" in name:
        is_metal = True
        metal_material = "Cr"
    elif "tungsten" in name:
        is_metal = True
        metal_material = "W"
    elif "brass" in name or "bronze" in name or "copper" in name:
        is_metal = True
        metal_material = "Cu"
    elif "hematite" in name:
        is_metal = True
        metal_material = "Cr"
    elif "metallic" in name:
        is_metal = True
        metal_material = "Al"
    if is_metal:
        guide = ET.SubElement(bsdf_node, "bsdf", {"type": "roughconductor"})
        ET.SubElement(guide, "string", {"name": "material", "value": metal_material})
        alpha_val = "0.02"
        if "mirror" in name or "polished" in name or "smooth" in name or "specular" in name:
            alpha_val = "0.005"
        elif "chrome" in name or "steel" in name or "silver" in name or "gold" in name:
            alpha_val = "0.01"
        elif "alum" in name or "aluminium" in name or "aluminum" in name:
            alpha_val = "0.015"
        elif "brushed" in name or "matte" in name or "satin" in name:
            alpha_val = "0.05"
        elif "rough" in name:
            alpha_val = "0.1"
        ET.SubElement(guide, "float", {"name": "alpha", "value": alpha_val})
        return
    guide = ET.SubElement(bsdf_node, "bsdf", {"type": "roughplastic"})
    ior_val = "polypropylene"
    if "acrylic" in name:
        ior_val = "acrylic glass"
    elif "diamond" in name:
        ior_val = "diamond"
    elif "water" in name:
        ior_val = "water"
    elif "glass" in name or "bk7" in name or "obsidian" in name:
        ior_val = "bk7"
    elif "teflon" in name:
        ior_val = "1.35"
    elif "delrin" in name:
        ior_val = "1.48"
    elif "silicon-nitrade" in name:
        ior_val = "2.0"
    try:
        float(ior_val)
        ET.SubElement(guide, "float", {"name": "intIOR", "value": ior_val})
    except ValueError:
        ET.SubElement(guide, "string", {"name": "intIOR", "value": ior_val})
    color_val = "0.5 0.5 0.5"
    if "dark-red" in name:
        color_val = "0.3 0.05 0.05"
    elif "dark-blue" in name:
        color_val = "0.05 0.05 0.3"
    elif "light-red" in name:
        color_val = "0.8 0.3 0.3"
    elif "light-brown" in name:
        color_val = "0.6 0.4 0.2"
    elif "blue" in name:
        color_val = "0.1 0.1 0.6"
    elif "red" in name:
        color_val = "0.6 0.1 0.1"
    elif "green" in name:
        color_val = "0.1 0.6 0.1"
    elif "white" in name or "alumina" in name or "marble" in name or "pearl" in name or "delrin" in name:
        color_val = "0.9 0.9 0.9"
    elif "black" in name or "obsidian" in name:
        color_val = "0.05 0.05 0.05"
    elif "yellow" in name:
        color_val = "0.8 0.8 0.1"
    elif "pink" in name:
        color_val = "0.8 0.5 0.5"
    elif "orange" in name:
        color_val = "0.8 0.4 0.1"
    elif "purple" in name or "violet" in name:
        color_val = "0.5 0.1 0.5"
    elif "beige" in name:
        color_val = "0.85 0.75 0.6"
    elif "brown" in name:
        color_val = "0.4 0.2 0.1"
    elif "maroon" in name:
        color_val = "0.4 0.0 0.0"
    elif "cyan" in name:
        color_val = "0.1 0.6 0.6"
    elif "gray" in name or "grey" in name:
        color_val = "0.5 0.5 0.5"
    if "cherry" in name:
        color_val = "0.55 0.2 0.1"
    elif "maple" in name or "natural" in name:
        color_val = "0.8 0.7 0.5"
    elif "pine" in name:
        color_val = "0.8 0.7 0.4"
    elif "oak" in name:
        color_val = "0.65 0.5 0.3"
    elif "walnut" in name:
        color_val = "0.35 0.2 0.1"
    elif "fruitwood" in name:
        color_val = "0.5 0.35 0.2"
    elif "mahogany" in name:
        color_val = "0.4 0.1 0.05"
    ET.SubElement(guide, "spectrum", {"name": "diffuseReflectance", "value": color_val})
    alpha_val = "0.1"
    if "fabric" in name or "matte" in name or "wood" in name or "rubber" in name or "foam" in name:
        alpha_val = "0.3"
    elif "felt" in name or "velvet" in name:
        alpha_val = "0.5"
    elif "wood" in name or "cherry" in name or "maple" in name or "pine" in name or "oak" in name or "walnut" in name:
        alpha_val = "0.2"
    elif "specular" in name or "obsidian" in name:
        alpha_val = "0.05"
    ET.SubElement(guide, "float", {"name": "alpha", "value": alpha_val})

def render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, progress, status, base_dir, log_placeholder=None, custom_cmd=None, integrator_type="bdpt", sample_count=256):
    if not render_selected:
        log("未选择渲染文件", log_placeholder)
        return
    scene_path = st.session_state.scene_path
    if not os.path.exists(scene_path):
        log(f"场景文件不存在: {scene_path}", log_placeholder)
        return
    os.makedirs(output_dir, exist_ok=True)
    exr_dir = os.path.join(output_dir, "exr")
    png_dir = os.path.join(output_dir, "png")
    temp_xml_dir = os.path.join(str(base_dir), "data", "batch_temp_xmls")
    for d in [exr_dir, png_dir, temp_xml_dir]:
        os.makedirs(d, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(st.session_state.mitsuba_exe) + os.pathsep + env.get("PATH", "")
    with open(scene_path, "r", encoding="utf-8") as f:
        scene_xml_text = f.read()
    total = len(render_selected)
    for idx, filename in enumerate(render_selected):
        if STOP_SIGNAL:
            log("渲染已停止 (收到停止信号)", log_placeholder)
            break
        file_path = os.path.join(input_dir, filename).replace("\\", "/")
        basename = os.path.splitext(filename)[0]
        exr_out = os.path.join(exr_dir, f"{basename}.exr")
        png_out = os.path.join(png_dir, f"{basename}.png")
        if skip_existing:
            target_file = png_out if auto_convert else exr_out
            if os.path.exists(target_file):
                log(f"[{idx+1}/{total}] 跳过 (已存在): {basename}", log_placeholder)
                overall_percent = (idx + 1) / total
                progress.progress(min(100, int(overall_percent * 100)))
                continue
        status.text(f"正在渲染 ({idx+1}/{total}): {filename}")
        root = ET.fromstring(scene_xml_text)
        
        # 更新积分器类型
        integrator_node = root.find("integrator")
        if integrator_node is not None:
            integrator_node.set("type", integrator_type)
        else:
            log("⚠️ 警告: 场景中未找到 integrator 节点，无法修改积分器类型", log_placeholder)

        # 更新采样数量
        sampler_node = root.find(".//sampler")
        if sampler_node is not None:
            found = False
            for int_node in sampler_node.findall("integer"):
                if int_node.get("name") == "sampleCount":
                    int_node.set("value", str(sample_count))
                    found = True
                    break
            if not found:
                log(f"⚠️ 警告: 在 sampler 节点中未找到 name='sampleCount' 的 integer 节点，无法修改采样数量", log_placeholder)
        else:
            log("⚠️ 警告: 场景中未找到 sampler 节点，无法修改采样数量", log_placeholder)

        tree = ET.ElementTree(root)
        scene_dir = os.path.dirname(os.path.abspath(scene_path))
        for string_node in root.iter("string"):
            if string_node.get("name") == "filename":
                val = string_node.get("value")
                if val and not os.path.isabs(val):
                    abs_val = os.path.abspath(os.path.join(scene_dir, val))
                    if os.path.exists(abs_val):
                        string_node.set("value", abs_val.replace("\\", "/"))
                    else:
                        string_node.set("value", abs_val.replace("\\", "/"))
                        log(f"⚠️ 警告: 场景引用的资源不存在: {abs_val}", log_placeholder)
        target_bsdf = None
        for bsdf in root.iter("bsdf"):
            if bsdf.get("type") in ["merl", "fullmerl", "nbrdf_npy"]:
                target_bsdf = bsdf
                break
        if target_bsdf is None:
            log("错误: 场景中未找到 bsdf 节点", log_placeholder)
            return
        for child in list(target_bsdf):
            if child.get("name") in ["filename", "binary", "nn_basename"]:
                target_bsdf.remove(child)
        if render_mode == "brdfs":
            target_bsdf.set("type", "merl")
            ET.SubElement(target_bsdf, "string", {"name": "binary", "value": file_path})
            configure_bsdf_smart(target_bsdf, filename)
        elif render_mode == "fullbin":
            target_bsdf.set("type", "fullmerl")
            ET.SubElement(target_bsdf, "string", {"name": "filename", "value": file_path})
            configure_bsdf_smart(target_bsdf, filename)
        else:
            target_bsdf.set("type", "nbrdf_npy")
            base_path = file_path
            if base_path.endswith("fc1.npy"):
                base_path = base_path[:-7]
            elif base_path.endswith(".npy"):
                base_path = base_path[:-4]
            for child in list(target_bsdf):
                if child.tag == "bsdf" or child.get("name") == "nn_basename":
                    target_bsdf.remove(child)
            ET.SubElement(target_bsdf, "string", {"name": "nn_basename", "value": base_path})
            if not any(c.get("name") == "reflectance" for c in target_bsdf):
                ET.SubElement(target_bsdf, "spectrum", {"name": "reflectance", "value": "0.5"})
        temp_xml = os.path.join(temp_xml_dir, f"{basename}.xml")
        tree.write(temp_xml)
        if custom_cmd:
            mitsuba_path = st.session_state.mitsuba_exe.replace("\\", "/")
            input_path = temp_xml.replace("\\", "/")
            output_path = exr_out.replace("\\", "/")
            final_cmd_str = custom_cmd.replace("{mitsuba}", mitsuba_path)\
                                     .replace("{input}", input_path)\
                                     .replace("{output}", output_path)
            import shlex
            cmd = shlex.split(final_cmd_str)
        else:
            cmd = [st.session_state.mitsuba_exe, "-o", exr_out, temp_xml]
        log(f"[{idx+1}/{total}] 渲染: {filename}", log_placeholder)
        if not os.path.exists(cmd[0]):
            log(f"  -> 错误: 未找到可执行文件 {cmd[0]}", log_placeholder)
            continue
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, bufsize=1)
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    line_str = line.strip()
                    log(f"  > {line_str}", log_placeholder)
                    if "Rendering: [" in line_str:
                        try:
                            content = line_str[line_str.find("[")+1 : line_str.find("]")]
                            total_width = len(content)
                            done_count = content.count("+")
                            if total_width > 0:
                                percent = done_count / total_width
                                overall_percent = (idx + percent) / total
                                progress.progress(min(100, int(overall_percent * 100)))
                        except:
                            pass
            proc.wait()
            if proc.returncode == 0:
                log("  -> EXR 完成", log_placeholder)
                if auto_convert:
                    cmd_conv = [st.session_state.mtsutil_exe, "tonemap", "-o", png_out, exr_out]
                    subprocess.run(cmd_conv, env=env, check=False)
                    log("  -> PNG 完成", log_placeholder)
            else:
                log(f"  -> 渲染失败，退出码: {proc.returncode}", log_placeholder)
        except Exception as e:
            log(f"  -> 启动进程失败: {str(e)}", log_placeholder)
        progress.progress(int((idx + 1) / total * 100))
    status.text("渲染完成")

def list_exr_files(conv_input_dir):
    if not os.path.exists(conv_input_dir):
        return []
    return sorted([os.path.basename(p) for p in glob.glob(os.path.join(conv_input_dir, "*.exr"))])

def convert_exr(conv_selected, conv_input_dir, conv_output_dir, progress, status, log_placeholder=None):
    if not conv_selected:
        log("未选择 EXR 文件", log_placeholder)
        return
    os.makedirs(conv_output_dir, exist_ok=True)
    env = os.environ.copy()
    total = len(conv_selected)
    for idx, filename in enumerate(conv_selected):
        status.text(f"正在转换 ({idx+1}/{total}): {filename}")
        progress.progress(int((idx / total) * 100))
        in_path = os.path.join(conv_input_dir, filename)
        out_name = os.path.splitext(filename)[0] + ".png"
        out_path = os.path.join(conv_output_dir, out_name)
        cmd = [st.session_state.mtsutil_exe, "tonemap", "-o", out_path, in_path]
        if not os.path.exists(cmd[0]):
            log(f"[转换] 错误: 未找到可执行文件 {cmd[0]}", log_placeholder)
            continue
        try:
            subprocess.run(cmd, env=env, check=True)
            log(f"[转换] 成功: {out_name}", log_placeholder)
        except Exception as e:
            log(f"[转换] 失败: {filename} ({str(e)})", log_placeholder)
    status.text("转换完成")
    progress.progress(100)

def run_compile(compile_cmd, conda_env, log_placeholder=None):
    vswhere = os.path.expandvars(r"${ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe")
    if not os.path.exists(vswhere):
        vswhere = os.path.expandvars(r"${ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe")
    if not os.path.exists(vswhere):
        log("未找到 vswhere.exe", log_placeholder)
        return
    cmd_vswhere = [vswhere, "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"]
    vs_path = subprocess.check_output(cmd_vswhere, text=True).strip()
    if not vs_path:
        log("未找到安装了 VC++ 工具集的 Visual Studio", log_placeholder)
        return
    vcvarsall = os.path.join(vs_path, r"VC\Auxiliary\Build\vcvarsall.bat")
    if not os.path.exists(vcvarsall):
        log(f"未找到 vcvarsall.bat: {vcvarsall}", log_placeholder)
        return
    base_dir = Path(st.session_state.root_dir)
    mitsuba_src_dir = base_dir / "mitsuba"
    if not (mitsuba_src_dir / "SConstruct").exists():
        mitsuba_src_dir = base_dir
    work_dir = str(mitsuba_src_dir)
    dep_bin = os.path.join(work_dir, "dependencies", "bin")
    dep_lib = os.path.join(work_dir, "dependencies", "lib")
    bat_content = f"""
@echo off
cd /d "{work_dir}"
echo [1/4] Setting up Visual Studio environment...
call "{vcvarsall}" x64

echo [2/4] Activating Conda environment '{conda_env}'...
@rem Try multiple ways to activate conda
if exist "%CONDA_EXE%" (
    for /f "delims=" %%i in ("%CONDA_EXE%") do set "CONDA_ROOT=%%~dpi.."
)
if exist "%CONDA_ROOT%\Scripts\activate.bat" (
    call "%CONDA_ROOT%\Scripts\activate.bat" {conda_env}
) else (
    call activate {conda_env} 2>nul || conda activate {conda_env} 2>nul
)

echo [3/4] Python Version:
python --version

echo [4/4] Setting dependency paths and running: {compile_cmd}
set PATH={dep_bin};{dep_lib};%PATH%
{compile_cmd}
"""
    bat_file = os.path.join(work_dir, "temp_build.bat")
    with open(bat_file, "w") as f:
        f.write(bat_content)
    log(f"生成构建脚本: {bat_file}", log_placeholder)
    proc = subprocess.Popen(bat_file, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        log(line.strip(), log_placeholder)
    proc.wait()
    if proc.returncode == 0:
        log("编译成功", log_placeholder)
    else:
        log("编译失败", log_placeholder)
    if os.path.exists(bat_file):
        os.remove(bat_file)

def calc_single_pair(img1, img2):
    psnr = metrics.peak_signal_noise_ratio(img1, img2, data_range=255)
    try:
        ssim = metrics.structural_similarity(img1, img2, data_range=255, channel_axis=2)
    except TypeError:
        ssim = metrics.structural_similarity(img1, img2, data_range=255, multichannel=True)
    lab1 = color.rgb2lab(img1)
    lab2 = color.rgb2lab(img2)
    de_map = color.deltaE_ciede2000(lab1, lab2)
    de = np.mean(de_map)
    return np.array([psnr, ssim, de])

def process_single_file(f_gt, dir_m1, dir_m2):
    basename = os.path.basename(f_gt)
    name_root = os.path.splitext(basename)[0]
    f_m1 = None
    for cand in [basename, f"{name_root}.fullbin.png"]:
        path = os.path.join(dir_m1, cand)
        if os.path.exists(path):
            f_m1 = path
            break
    f_m2 = None
    for cand in [basename, f"{name_root}_fc1.png", f"{name_root}.binary.png"]:
        path = os.path.join(dir_m2, cand)
        if os.path.exists(path):
            f_m2 = path
            break
    if not f_m1 or not f_m2:
        return None, f"跳过 {basename}: 未找到对应文件"
    img_gt = cv2.imread(f_gt)
    img_m1 = cv2.imread(f_m1)
    img_m2 = cv2.imread(f_m2)
    if img_gt is None or img_m1 is None or img_m2 is None:
        return None, f"读取失败: {basename}"
    if img_gt.shape != img_m1.shape or img_gt.shape != img_m2.shape:
        img_m1 = cv2.resize(img_m1, (img_gt.shape[1], img_gt.shape[0]))
        img_m2 = cv2.resize(img_m2, (img_gt.shape[1], img_gt.shape[0]))
    img_gt_rgb = cv2.cvtColor(img_gt, cv2.COLOR_BGR2RGB)
    img_m1_rgb = cv2.cvtColor(img_m1, cv2.COLOR_BGR2RGB)
    img_m2_rgb = cv2.cvtColor(img_m2, cv2.COLOR_BGR2RGB)
    res_gt_m1 = calc_single_pair(img_gt_rgb, img_m1_rgb)
    res_gt_m2 = calc_single_pair(img_gt_rgb, img_m2_rgb)
    res_m1_m2 = calc_single_pair(img_m1_rgb, img_m2_rgb)
    return (res_gt_m1, res_gt_m2, res_m1_m2), None

def run_evaluation(eval_gt_dir, eval_method1_dir, eval_method2_dir, progress, status):
    if not all(os.path.exists(d) for d in [eval_gt_dir, eval_method1_dir, eval_method2_dir]):
        log("至少有一个输入目录不存在")
        return
    files = sorted(glob.glob(os.path.join(eval_gt_dir, "*.png")))
    if not files:
        log("GT 目录中没有 PNG 文件")
        return
    metrics_gt_m1 = np.zeros(3)
    metrics_gt_m2 = np.zeros(3)
    metrics_m1_m2 = np.zeros(3)
    count = 0
    total = len(files)
    max_workers = min(32, (os.cpu_count() or 1) + 4)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_single_file, f, eval_method1_dir, eval_method2_dir): f for f in files}
        for idx, future in enumerate(concurrent.futures.as_completed(future_to_file)):
            f = future_to_file[future]
            basename = os.path.basename(f)
            try:
                results, error_msg = future.result()
                if error_msg:
                    log(error_msg)
                else:
                    metrics_gt_m1 += results[0]
                    metrics_gt_m2 += results[1]
                    metrics_m1_m2 += results[2]
                    count += 1
            except Exception as exc:
                log(f"处理异常 {basename}: {exc}")
            status.text(f"正在评估 ({idx+1}/{total})")
            progress.progress(int(((idx + 1) / total) * 100))
    if count == 0:
        log("未成功处理任何图片")
        return
    avg_gt_m1 = metrics_gt_m1 / count
    avg_gt_m2 = metrics_gt_m2 / count
    avg_m1_m2 = metrics_m1_m2 / count
    st.session_state.eval_result = {
        "GT vs FullBin": avg_gt_m1,
        "GT vs NPY": avg_gt_m2,
        "FullBin vs NPY": avg_m1_m2
    }
    log("评估完成")

def run_grid_generation(grid_input_dir, grid_output_file, grid_show_names, grid_cell_width, grid_padding):
    if not os.path.exists(grid_input_dir):
        log(f"输入目录不存在: {grid_input_dir}")
        return
    exts = ["*.png", "*.jpg", "*.jpeg", "*.bmp"]
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(grid_input_dir, ext)))
    files = sorted(files)
    count = len(files)
    if count == 0:
        log("未找到图片")
        return
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    text_height = 30 if grid_show_names else 0
    cell_height = int(grid_cell_width)
    try:
        with Image.open(files[0]) as tmp:
            aspect = tmp.height / tmp.width
            cell_height = int(grid_cell_width * aspect)
    except Exception:
        log("读取图片失败")
        return
    grid_width = cols * grid_cell_width + (cols + 1) * grid_padding
    grid_height = rows * (cell_height + text_height) + (rows + 1) * grid_padding
    grid_img = Image.new("RGB", (grid_width, grid_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(grid_img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font = ImageFont.load_default()
    for idx, fpath in enumerate(files):
        with Image.open(fpath) as img:
            img_resized = img.resize((grid_cell_width, cell_height), Image.LANCZOS)
            col = idx % cols
            row = idx // cols
            x = grid_padding + col * (grid_cell_width + grid_padding)
            y = grid_padding + row * (cell_height + text_height + grid_padding)
            grid_img.paste(img_resized, (x, y))
            if grid_show_names:
                filename = os.path.basename(fpath)
                name_text = os.path.splitext(filename)[0]
                if len(name_text) > 25:
                    name_text = name_text[:22] + "..."
                bbox = draw.textbbox((0, 0), name_text, font=font)
                text_w = bbox[2] - bbox[0]
                text_x = x + (grid_cell_width - text_w) / 2
                text_y = y + cell_height + 5
                draw.text((text_x, text_y), name_text, fill=(0, 0, 0), font=font)
    grid_img.save(grid_output_file)
    st.image(grid_img, caption="网格拼图结果", use_container_width=True)
    log(f"网格拼图已保存: {grid_output_file}")

def run_comp_generation(eval_gt_dir, eval_method1_dir, eval_method2_dir, comp_output_dir, comp_labels, comp_show_label, comp_show_filename):
    if not all(os.path.exists(d) for d in [eval_gt_dir, eval_method1_dir, eval_method2_dir]):
        log("输入目录不存在，请检查量化评估配置")
        return
    os.makedirs(comp_output_dir, exist_ok=True)
    labels = [t.strip() for t in comp_labels.split(",")]
    if len(labels) < 3:
        labels = ["GT", "Method1", "Method2"]
    files = sorted(glob.glob(os.path.join(eval_gt_dir, "*.png")))
    if not files:
        log("GT 目录中没有图片")
        return
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
    for f_gt in files:
        basename = os.path.basename(f_gt)
        name_root = os.path.splitext(basename)[0]
        f_m1 = None
        for cand in [basename, f"{name_root}.fullbin.png"]:
            path = os.path.join(eval_method1_dir, cand)
            if os.path.exists(path):
                f_m1 = path
                break
        f_m2 = None
        for cand in [basename, f"{name_root}_fc1.png", f"{name_root}.binary.png"]:
            path = os.path.join(eval_method2_dir, cand)
            if os.path.exists(path):
                f_m2 = path
                break
        if not f_m1 or not f_m2:
            log(f"跳过 {basename}: 缺失对应文件")
            continue
        images = [Image.open(f_gt), Image.open(f_m1), Image.open(f_m2)]
        w, h = images[0].size
        images[1] = images[1].resize((w, h), Image.LANCZOS)
        images[2] = images[2].resize((w, h), Image.LANCZOS)
        padding = 10
        label_height = 30 if comp_show_label else 0
        filename_height = 40 if comp_show_filename else 0
        comp_w = w * 3 + padding * 4
        comp_h = h + padding * 2 + label_height + filename_height
        comp_img = Image.new("RGB", (comp_w, comp_h), (255, 255, 255))
        draw = ImageDraw.Draw(comp_img)
        if comp_show_filename:
            name_text = name_root
            try:
                title_font = ImageFont.truetype("arial.ttf", 24)
            except IOError:
                title_font = font
            bbox = draw.textbbox((0, 0), name_text, font=title_font)
            text_w = bbox[2] - bbox[0]
            text_x = (comp_w - text_w) / 2
            text_y = padding
            draw.text((text_x, text_y), name_text, fill=(0, 0, 0), font=title_font)
        for i, img in enumerate(images):
            x = padding + i * (w + padding)
            y = padding + label_height + filename_height
            comp_img.paste(img, (x, y))
            if comp_show_label:
                label_text = labels[i] if i < len(labels) else ""
                bbox = draw.textbbox((0, 0), label_text, font=font)
                text_w = bbox[2] - bbox[0]
                text_x = x + (w - text_w) / 2
                text_y = padding + filename_height
                draw.text((text_x, text_y), label_text, fill=(0, 0, 0), font=font)
        out_path = os.path.join(comp_output_dir, f"comp_{basename}")
        comp_img.save(out_path)
    log(f"对比拼图已生成: {comp_output_dir}")

def on_render_mode_change():
    base_dir, input_dir_map, output_dir_map = get_paths()
    mode = st.session_state.render_mode
    st.session_state.input_dir = str(input_dir_map.get(mode, ""))
    st.session_state.output_dir = str(output_dir_map.get(mode, ""))
    st.session_state.render_selected = []

def on_preview_dir_type_change():
    base_dir, _, output_dir_map = get_paths()
    p_type = st.session_state.preview_dir_type
    if p_type == "grids":
        st.session_state.preview_dir = str(base_dir / "data" / "outputs" / "grids")
    elif p_type == "comparisons":
        st.session_state.preview_dir = str(base_dir / "data" / "outputs" / "comparisons")
    else:
        st.session_state.preview_dir = str(output_dir_map.get(p_type, base_dir / "data" / "outputs" / p_type) / "png")
    st.session_state.preview_selected_img = None
