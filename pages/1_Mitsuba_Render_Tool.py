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

st.set_page_config(page_title="Mitsuba 渲染工具", page_icon="🎨", layout="wide")

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
if "root_dir" not in st.session_state:
    st.session_state.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "mitsuba_dir" not in st.session_state:
    # 优先检测项目根目录下的 mitsuba
    local_mitsuba = Path(st.session_state.root_dir) / "mitsuba" / "dist"
    if local_mitsuba.exists():
        st.session_state.mitsuba_dir = str(local_mitsuba)
    else:
        st.session_state.mitsuba_dir = r"d:\mitsuba\dist"
if "mitsuba_exe" not in st.session_state:
    st.session_state.mitsuba_exe = str(Path(st.session_state.mitsuba_dir) / "mitsuba.exe")
if "mtsutil_exe" not in st.session_state:
    st.session_state.mtsutil_exe = str(Path(st.session_state.mitsuba_dir) / "mtsutil.exe")
if "scene_path" not in st.session_state:
    st.session_state.scene_path = str(Path(st.session_state.root_dir) / "scene" / "scene_merl.xml")

# 使用全局列表作为共享内存来传递停止信号，绕过 Streamlit 在运行期间无法更新 session_state 的限制
STOP_SIGNAL = []

def log(msg, placeholder=None):
    # 过滤掉退格符等不可见字符
    clean_msg = msg.replace("\b", "").replace("\r", "")
    st.session_state.logs.append(clean_msg)
    if placeholder:
        # 将最新的日志放在最上面，解决滚动条重置导致看不见最新日志的问题
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
        # 参考 batch_render_tool.py 的逻辑：一个材质包含6个文件，只加载 fc1 作为代表
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
        alpha_val = "0.1"
        if "matte" in name or "brushed" in name or "rough" in name:
            alpha_val = "0.2"
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

def render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, progress, status, base_dir, log_placeholder=None, custom_cmd=None):
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
                # 更新总进度
                overall_percent = (idx + 1) / total
                progress.progress(min(100, int(overall_percent * 100)))
                continue
        status.text(f"正在渲染 ({idx+1}/{total}): {filename}")
        
        root = ET.fromstring(scene_xml_text)
        tree = ET.ElementTree(root)
        # 修正 XML 中的相对路径资源 (如 envmap.exr, matpreview.serialized)
        scene_dir = os.path.dirname(os.path.abspath(scene_path))
        for string_node in root.iter("string"):
            if string_node.get("name") == "filename":
                val = string_node.get("value")
                if val and not os.path.isabs(val):
                    # 优先尝试在模板 XML 目录下寻找资源
                    abs_val = os.path.abspath(os.path.join(scene_dir, val))
                    if os.path.exists(abs_val):
                        string_node.set("value", abs_val.replace("\\", "/"))
                    else:
                        # 即使找不到也强行设为绝对路径，方便报错
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
            # npy 渲染逻辑：参考 batch_render_tool.py
            # 一个材质包含 fc1, fc2, fc3, b1, b2, b3 六个文件
            target_bsdf.set("type", "nbrdf_npy")
            # 去除后缀获取基础路径
            base_path = file_path
            if base_path.endswith("fc1.npy"):
                base_path = base_path[:-7] # 移除 "fc1.npy"
            elif base_path.endswith(".npy"):
                base_path = base_path[:-4] # 移除 ".npy"
            
            # 移除旧的子节点并添加 nn_basename
            for child in list(target_bsdf):
                if child.tag == "bsdf" or child.get("name") == "nn_basename":
                    target_bsdf.remove(child)
            
            ET.SubElement(target_bsdf, "string", {"name": "nn_basename", "value": base_path})
            
            if not any(c.get("name") == "reflectance" for c in target_bsdf):
                ET.SubElement(target_bsdf, "spectrum", {"name": "reflectance", "value": "0.5"})
        temp_xml = os.path.join(temp_xml_dir, f"{basename}.xml")
        tree.write(temp_xml)
        
        # 确定命令
        if custom_cmd:
            # 支持占位符替换
            # 为防止路径包含空格或反斜杠导致解析错误，将所有反斜杠统一替换为正斜杠，
            # 并使用 shlex 的默认 POSIX 模式 (posix=True) 来正确剥离引号。
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
        
        # 预检可执行文件是否存在
        if not os.path.exists(cmd[0]):
            log(f"  -> 错误: 未找到可执行文件 {cmd[0]}", log_placeholder)
            continue

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
            for line in proc.stdout:
                line_str = line.strip()
                log(f"  > {line_str}", log_placeholder)
                
                # 解析 Mitsuba 进度条并更新总进度条
                if "Rendering: [" in line_str:
                    try:
                        content = line_str[line_str.find("[")+1 : line_str.find("]")]
                        total_width = len(content)
                        done_count = content.count("+")
                        if total_width > 0:
                            percent = done_count / total_width
                            # 统一进度计算: (当前文件索引 + 当前文件内部百分比) / 总文件数
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
        
        # 预检可执行文件是否存在
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
    # 自动定位 Mitsuba 源码目录 (包含 SConstruct 的目录)
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
call "{vcvarsall}" x64
call activate {conda_env}
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
    st.image(grid_img, caption="网格拼图结果", use_column_width=True)
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
    # 切换模式时清空已选文件，防止 multiselect 报错
    st.session_state.render_selected = []

def on_preview_dir_type_change():
    base_dir, _, output_dir_map = get_paths()
    p_type = st.session_state.preview_dir_type
    st.session_state.preview_dir = str(output_dir_map.get(p_type, base_dir / "data" / "outputs" / p_type) / "png")
    # 切换预览类型时清空已选图片
    st.session_state.preview_selected_img = None

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
    base_dir, input_dir_map, output_dir_map = get_paths()
    
    # 确保 session_state 中有初始值
    if "input_dir" not in st.session_state:
        st.session_state.input_dir = str(input_dir_map.get("brdfs", ""))
    if "output_dir" not in st.session_state:
        st.session_state.output_dir = str(output_dir_map.get("brdfs", ""))

    render_mode = st.radio("输入类型", ["brdfs", "fullbin", "npy"], horizontal=True, key="render_mode", on_change=on_render_mode_change)
    auto_convert = st.checkbox("渲染后自动转换为 PNG", value=True, key="auto_convert")
    skip_existing = st.checkbox("跳过已存在文件", value=False, key="skip_existing")
    input_dir = st.text_input("输入目录", key="input_dir")
    output_dir = st.text_input("输出目录", key="output_dir")
    
    use_custom_cmd = st.checkbox("使用自定义渲染命令", value=False, key="use_custom_cmd")
    if use_custom_cmd:
        custom_cmd_str = st.text_input("自定义命令 (支持占位符: {mitsuba}, {input}, {output})", 
                                      value='"{mitsuba}" -o "{output}" "{input}"', 
                                      key="custom_cmd_str")
    else:
        custom_cmd_str = None

    render_files = list_render_files(input_dir, render_mode)
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
            STOP_SIGNAL.clear() # 清除之前的停止信号
            render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, render_progress, render_status, base_dir, render_log_placeholder, custom_cmd_str)
    with col_stop:
        if st.button("停止渲染"):
            if not STOP_SIGNAL:
                STOP_SIGNAL.append(True)
            log("已发送停止信号，将在当前文件完成后中断...")

with tabs[1]:
    st.header("EXR 转 PNG")
    base_dir, _, output_dir_map = get_paths()
    output_dir = output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs")
    conv_input_dir = st.text_input("EXR 输入目录", value=str(Path(output_dir) / "exr"), key="conv_input_dir")
    conv_output_dir = st.text_input("PNG 输出目录", value=str(Path(output_dir) / "png"), key="conv_output_dir")
    conv_files = list_exr_files(conv_input_dir)
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
        convert_exr(conv_selected, conv_input_dir, conv_output_dir, conv_progress, conv_status, conv_log_placeholder)

with tabs[2]:
    st.header("图片结果预览")
    base_dir, _, output_dir_map = get_paths()
    
    # 确保 session_state 中有预览路径初始值
    if "preview_dir" not in st.session_state:
        st.session_state.preview_dir = str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png")
        
    preview_dir_type = st.radio("预览类型", ["brdfs", "fullbin", "npy"], horizontal=True, key="preview_dir_type", on_change=on_preview_dir_type_change)
    preview_dir = st.text_input("预览目录", key="preview_dir")
    
    if os.path.exists(preview_dir):
        image_files = sorted([f for f in os.listdir(preview_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        if image_files:
            col1, col2 = st.columns([1, 3])
            with col1:
                selected_img = st.selectbox("选择图片", options=image_files, key="preview_selected_img")
            with col2:
                img_path = os.path.join(preview_dir, selected_img)
                st.image(img_path, caption=selected_img, use_column_width=True)
                
                # 基本信息
                st.info(f"文件名: {selected_img} | 路径: {img_path}")
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
        run_compile(compile_cmd, conda_env, compile_log_placeholder)

with tabs[4]:
    st.header("量化评估")
    base_dir, _, output_dir_map = get_paths()
    eval_gt_dir = st.text_input("GT (BRDFs) PNG 目录", value=str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png"), key="eval_gt_dir")
    eval_method1_dir = st.text_input("Method1 (FullBin) PNG 目录", value=str(output_dir_map.get("fullbin", base_dir / "data" / "outputs" / "fullbin") / "png"), key="eval_method1_dir")
    eval_method2_dir = st.text_input("Method2 (NPY) PNG 目录", value=str(output_dir_map.get("npy", base_dir / "data" / "outputs" / "npy") / "png"), key="eval_method2_dir")
    eval_progress = st.progress(0)
    eval_status = st.empty()
    if st.button("开始量化评估"):
        run_evaluation(eval_gt_dir, eval_method1_dir, eval_method2_dir, eval_progress, eval_status)
    if st.session_state.eval_result:
        table_data = []
        for k, v in st.session_state.eval_result.items():
            table_data.append({"Comparison": k, "PSNR (dB)": float(v[0]), "SSIM": float(v[1]), "Delta E": float(v[2])})
        st.table(table_data)

with tabs[5]:
    st.header("网格拼图")
    base_dir, _, output_dir_map = get_paths()
    grid_input_dir = st.text_input("图片输入目录", value=str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png"), key="grid_input_dir")
    grid_output_file = st.text_input("输出文件路径", value=str(base_dir / "data" / "outputs" / "merged_grid.png"), key="grid_output_file")
    grid_show_names = st.checkbox("显示文件名", value=True, key="grid_show_names")
    grid_cell_width = st.number_input("单图宽度", min_value=64, max_value=1024, value=256, key="grid_cell_width")
    grid_padding = st.number_input("间距", min_value=0, max_value=100, value=10, key="grid_padding")
    if st.button("生成网格大图"):
        run_grid_generation(grid_input_dir, grid_output_file, grid_show_names, grid_cell_width, grid_padding)

with tabs[6]:
    st.header("对比拼图")
    base_dir, _, output_dir_map = get_paths()
    eval_gt_dir = st.text_input("GT (BRDFs) PNG 目录", value=str(output_dir_map.get("brdfs", base_dir / "data" / "outputs" / "brdfs") / "png"), key="comp_eval_gt_dir")
    eval_method1_dir = st.text_input("Method1 (FullBin) PNG 目录", value=str(output_dir_map.get("fullbin", base_dir / "data" / "outputs" / "fullbin") / "png"), key="comp_eval_method1_dir")
    eval_method2_dir = st.text_input("Method2 (NPY) PNG 目录", value=str(output_dir_map.get("npy", base_dir / "data" / "outputs" / "npy") / "png"), key="comp_eval_method2_dir")
    comp_output_dir = st.text_input("对比图输出目录", value=str(base_dir / "data" / "outputs" / "comparisons"), key="comp_output_dir")
    comp_labels = st.text_input("标题文本(逗号分隔)", value="Ground Truth,FullBin,Neural BRDF", key="comp_labels")
    comp_show_label = st.checkbox("添加列标题", value=True, key="comp_show_label")
    comp_show_filename = st.checkbox("添加文件名", value=True, key="comp_show_filename")
    if st.button("生成对比拼图"):
        run_comp_generation(eval_gt_dir, eval_method1_dir, eval_method2_dir, comp_output_dir, comp_labels, comp_show_label, comp_show_filename)

with tabs[7]:
    st.header("日志")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("清空日志"):
            clear_logs()
    with col2:
        st.write(f"日志条数: {len(st.session_state.logs)}")
    st.text_area("日志输出", value="\n".join(st.session_state.logs), height=400)
