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
import tkinter as tk
from tkinter import filedialog
import datetime
from . import get_project_root, get_mitsuba_paths
import locale
import re
import time

STOP_SIGNAL = []
DEFAULT_VCVARSALL_PATH = r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat"
MERL_STANDARD_FILE_SIZE = 12 + 90 * 90 * 180 * 3 * 8
MERL_FULL_FILE_SIZE = 12 + 90 * 90 * 360 * 3 * 8

TEST_SET_20 = [
    "alum-bronze", "beige-fabric", "black-obsidian", "blue-acrylic", "chrome",
    "chrome-steel", "dark-red-paint", "dark-specular-fabric", "delrin",
    "green-metallic-paint", "natural-209", "nylon", "polyethylene", "pure-rubber",
    "silicon-nitrade", "teflon", "violet-rubber", "white-diffuse-bball",
    "white-fabric", "yellow-paint"
]


def build_serial_compile_command(compile_cmd):
    if not compile_cmd or "scons" not in compile_cmd.lower():
        return None
    serial_cmd = re.sub(r"(?i)(^|\s)-j\s*\d+", r"\1-j1", compile_cmd)
    serial_cmd = re.sub(r"(?i)(^|\s)--jobs(?:=|\s*)\d+", r"\1--jobs=1", serial_cmd)
    if serial_cmd == compile_cmd:
        serial_cmd = f"{compile_cmd} -j1"
    return serial_cmd


def has_manifest_access_denied(log_lines):
    joined = "\n".join(log_lines).lower()
    patterns = [
        "mt.exe : general error c101008d",
        "failed to write the updated manifest",
        "error 31",
        "拒绝访问",
        "access is denied",
    ]
    return any(pattern in joined for pattern in patterns)


def detect_merl_variant(file_path):
    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        return None
    if file_size == MERL_STANDARD_FILE_SIZE:
        return "merl"
    if file_size == MERL_FULL_FILE_SIZE:
        return "fullmerl"
    return None


def decode_subprocess_output(raw):
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    preferred = locale.getpreferredencoding(False) or "utf-8"
    candidates = []
    for encoding in ("utf-8", preferred, "gb18030", "cp936"):
        if encoding and encoding.lower() not in {c.lower() for c in candidates}:
            candidates.append(encoding)
    for encoding in candidates:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def execute_compile_attempt(work_dir, vcvarsall, conda_cmd, conda_env, dep_bin, dep_lib, compile_cmd, log_placeholder=None):
    exit_code_file = os.path.join(work_dir, "temp_build_exit_code.txt")
    bat_file = os.path.join(work_dir, "temp_build.bat")
    bat_content = f"""
@echo off
cd /d "{work_dir}"
setlocal EnableExtensions
echo 99> "{exit_code_file}"
echo [1/4] Setting up Visual Studio environment...
call "{vcvarsall}" x64
echo [1/4] Done (errorlevel %errorlevel%)

set "CONDA_CMD={conda_cmd}"
if not exist "%CONDA_CMD%" set "CONDA_CMD=conda"
for %%i in ("%CONDA_CMD%") do set "CONDA_ROOT=%%~dpi.."
echo [2/4] Activating Conda environment '{conda_env}'...
if exist "%CONDA_ROOT%\\condabin\\conda.bat" (
    call "%CONDA_ROOT%\\condabin\\conda.bat" activate {conda_env}
) else if exist "%CONDA_ROOT%\\Scripts\\activate.bat" (
    call "%CONDA_ROOT%\\Scripts\\activate.bat" {conda_env}
) else (
    call activate {conda_env} 2>nul || conda activate {conda_env} 2>nul
)
if "%CONDA_PREFIX%"=="" (
    echo [2/4] Failed to activate conda env
    echo 1> "{exit_code_file}"
    exit /b 1
)
echo [2/4] Done (errorlevel %errorlevel%)

echo [3/4] Toolchain Info:
where python || echo python not found
python --version || echo python version failed
where scons || echo scons not found
call scons --version || echo scons version failed
where cl || echo cl not found
echo [3/4] Done (errorlevel %errorlevel%)

echo [4/4] Running build command
echo WorkDir: {work_dir}
echo Command: {compile_cmd}
set PATH={dep_bin};{dep_lib};%PATH%
call {compile_cmd}
set "BUILD_ERROR=%errorlevel%"
echo [4/4] Done (errorlevel %BUILD_ERROR%)
echo %BUILD_ERROR%> "{exit_code_file}"
exit /b %BUILD_ERROR%
"""
    with open(bat_file, "w", encoding="utf-8") as f:
        f.write(bat_content)
    log(f"生成构建脚本: {bat_file}", log_placeholder)
    output_lines = []
    proc = subprocess.Popen(
        bat_file,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False
    )
    for raw_line in proc.stdout:
        line = decode_subprocess_output(raw_line).strip()
        output_lines.append(line)
        log(line, log_placeholder)
    proc.wait()
    final_exit_code = proc.returncode
    if os.path.exists(exit_code_file):
        try:
            with open(exit_code_file, "r") as f:
                final_exit_code = int(f.read().strip())
        except Exception:
            final_exit_code = proc.returncode
        os.remove(exit_code_file)
    log(f"构建脚本退出码: {proc.returncode}", log_placeholder)
    log(f"最终退出码: {final_exit_code}", log_placeholder)
    if os.path.exists(bat_file):
        os.remove(bat_file)
    return final_exit_code, output_lines

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

def update_selection_from_dialog(input_dir, title, filetypes, available_files, session_key, warning_text=None):
    selected_paths = open_file_dialog(input_dir, title, filetypes)
    if not selected_paths:
        return
    selected_names = [os.path.basename(p) for p in selected_paths]
    valid_names = [n for n in selected_names if n in available_files]
    if len(valid_names) < len(selected_names):
        st.warning(warning_text or "部分选择的文件不在当前目录中，已自动忽略。")
    st.session_state[session_key] = valid_names
    st.rerun()

def get_preset_test_set_selection(available_files):
    """
    Return files matched by the shared 20-material preset list.
    """
    selected = []
    for preset in TEST_SET_20:
        found = False
        for f in available_files:
            if os.path.splitext(f)[0] == preset:
                selected.append(f)
                found = True
                break
        if not found:
            for f in available_files:
                if preset in f:
                    selected.append(f)
                    break
    return list(dict.fromkeys(selected))

def apply_preset_test_set_selection(available_files, session_key, success_label="预设测试材质"):
    selected = get_preset_test_set_selection(available_files)
    if selected:
        st.session_state[session_key] = selected
        st.success(f"已选中 {len(selected)} 个{success_label}")
    else:
        st.warning("当前目录未找到预设测试集中的材质文件")
    st.rerun()

def ensure_mitsuba_state(root_dir):
    base_root = Path(root_dir) if root_dir else get_project_root()
    default_dir, default_exe, default_mtsutil = get_mitsuba_paths(base_root)
    if "mitsuba_dir" not in st.session_state or not st.session_state.mitsuba_dir:
        st.session_state.mitsuba_dir = str(default_dir)
    if "mitsuba_exe" not in st.session_state or not st.session_state.mitsuba_exe:
        if Path(st.session_state.mitsuba_dir) == default_dir:
            st.session_state.mitsuba_exe = str(default_exe)
        else:
            st.session_state.mitsuba_exe = str(Path(st.session_state.mitsuba_dir) / "mitsuba.exe")
    if "mtsutil_exe" not in st.session_state or not st.session_state.mtsutil_exe:
        if Path(st.session_state.mitsuba_dir) == default_dir:
            st.session_state.mtsutil_exe = str(default_mtsutil)
        else:
            st.session_state.mtsutil_exe = str(Path(st.session_state.mitsuba_dir) / "mtsutil.exe")

def resolve_vcvarsall_from_shortcut(lnk_path):
    if not os.path.exists(lnk_path):
        return ""
    escaped = lnk_path.replace("'", "''")
    ps_script = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{escaped}');"
        "Write-Output $s.TargetPath; Write-Output $s.Arguments"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_script],
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace"
        ).splitlines()
    except Exception:
        return ""
    target = output[0].strip() if output else ""
    args = output[1].strip() if len(output) > 1 else ""
    if target.lower().endswith("vcvarsall.bat") and os.path.exists(target):
        return target
    if target.lower().endswith("cmd.exe") and args:
        match = re.search(r'([A-Za-z]:\\[^"]*vcvarsall\.bat)', args, flags=re.IGNORECASE)
        if match:
            cand = match.group(1)
            if os.path.exists(cand):
                return cand
    return ""

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
        st.session_state.root_dir = str(get_project_root())
    ensure_mitsuba_state(st.session_state.root_dir)
        
    if "scene_path" not in st.session_state or not st.session_state.scene_path:
        st.session_state.scene_path = get_default_scene_path(st.session_state.root_dir)

def get_scene_search_dirs(root_dir):
    base_dir = Path(root_dir)
    return [
        base_dir / "scene" / "dj_xml",
        base_dir / "scene" / "old_xml"
    ]

def list_scene_xmls(root_dir):
    scene_dirs = get_scene_search_dirs(root_dir)
    results = []
    for scene_dir in scene_dirs:
        if scene_dir.exists():
            results.extend(sorted(scene_dir.glob("*.xml")))
    return [str(p) for p in results]

def get_default_scene_path(root_dir):
    base_dir = Path(root_dir)
    preferred = base_dir / "scene" / "old_xml" / "scene_merl.xml"
    if preferred.exists():
        return str(preferred)
    fallback = base_dir / "scene" / "scene_merl.xml"
    if fallback.exists():
        return str(fallback)
    candidates = list_scene_xmls(root_dir)
    return candidates[0] if candidates else str(fallback)

def log(msg, placeholder=None):
    clean_msg = msg.replace("\b", "").replace("\r", "")
    st.session_state.logs.append(clean_msg)
    if placeholder:
        recent_logs = "\n".join(st.session_state.logs[::-1][:20])
        placeholder.code(recent_logs, language=None)

def clear_logs():
    st.session_state.logs = []

def get_paths():
    base_dir = Path(st.session_state.root_dir)
    input_dir_map = {
        "brdfs": base_dir / "data" / "inputs" / "binary",
        "fullbin": base_dir / "data" / "inputs" / "fullbin",
        "npy": base_dir / "data" / "inputs" / "npy"
    }
    output_dir_map = {
        "brdfs": base_dir / "data" / "outputs" / "binary",
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

def is_placeholder_value(value):
    return isinstance(value, str) and value.strip().startswith("$")

def has_merl_accelerated(mitsuba_dir):
    if not mitsuba_dir:
        return False
    plugin_path = os.path.join(mitsuba_dir, "plugins", "merl_accelerated.dll")
    return os.path.exists(plugin_path)

def resolve_scene_resource(scene_dir, root_dir, value):
    if not value:
        return None
    cleaned = value.replace("\\", "/")
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    candidates = []
    candidates.append(os.path.abspath(os.path.join(scene_dir, cleaned)))
    if "dj_xml/" in cleaned:
        candidates.append(os.path.abspath(os.path.join(scene_dir, cleaned.split("dj_xml/")[-1])))
    if "old_xml/" in cleaned:
        candidates.append(os.path.abspath(os.path.join(scene_dir, cleaned.split("old_xml/")[-1])))
    if root_dir:
        candidates.append(os.path.abspath(os.path.join(root_dir, cleaned)))
        candidates.append(os.path.abspath(os.path.join(root_dir, "scene", cleaned)))
    candidates.append(os.path.abspath(os.path.join(scene_dir, os.path.basename(cleaned))))
    for cand in candidates:
        if os.path.exists(cand):
            return cand
    return candidates[0] if candidates else None

def normalize_output_dir(output_dir):
    if not output_dir:
        return output_dir
    tail = os.path.basename(output_dir).lower()
    if tail in ["exr", "png"]:
        return os.path.dirname(output_dir)
    return output_dir

def ensure_hdr_film(root):
    film_node = root.find(".//film")
    if film_node is not None and film_node.get("type") == "ldrfilm":
        film_node.set("type", "hdrfilm")

def find_target_bsdf(root):
    for bsdf in root.iter("bsdf"):
        if bsdf.get("id") == "Material":
            return bsdf
    preferred_types = {
        "merl",
        "fullmerl",
        "nbrdf_npy",
        "merl_accelerated",
        "SIREN_h21l5_nbrdf_npy",
        "SIREN_gray_h21l5_nbrdf_npy"
    }
    for bsdf in root.iter("bsdf"):
        if bsdf.get("type") in preferred_types:
            return bsdf
    name_keys = {"binary", "filename", "nn_basename", "nn_basename_r", "nn_basename_g", "nn_basename_b"}
    for bsdf in root.iter("bsdf"):
        for child in bsdf:
            if child.tag == "string" and child.get("name") in name_keys:
                return bsdf
    return None

def normalize_npy_base_path(file_path):
    base_path = file_path
    if base_path.endswith("fc1.npy"):
        base_path = base_path[:-7]
    elif base_path.endswith(".npy"):
        base_path = base_path[:-4]
    return base_path

def split_rgb_base_paths(base_path):
    trimmed = base_path[:-1] if base_path.endswith("_") else base_path
    tail = os.path.basename(trimmed).lower()
    if tail.endswith("_r") or tail.endswith("_g") or tail.endswith("_b"):
        prefix = trimmed[:-2]
        return f"{prefix}_r", f"{prefix}_g", f"{prefix}_b"
    return trimmed, trimmed, trimmed

def update_bsdf_for_mode(bsdf_node, render_mode, file_path, filename, mitsuba_dir=None):
    existing_type = bsdf_node.get("type", "")
    name_keys = {"filename", "binary", "nn_basename", "nn_basename_r", "nn_basename_g", "nn_basename_b"}
    for child in list(bsdf_node):
        if child.get("name") in name_keys:
            bsdf_node.remove(child)
    if render_mode == "brdfs":
        if existing_type == "merl_accelerated" and has_merl_accelerated(mitsuba_dir):
            bsdf_node.set("type", "merl_accelerated")
            ET.SubElement(bsdf_node, "string", {"name": "filename", "value": file_path})
            selected_type = "merl_accelerated"
        else:
            bsdf_node.set("type", "merl")
            ET.SubElement(bsdf_node, "string", {"name": "binary", "value": file_path})
            selected_type = "merl"
        configure_bsdf_smart(bsdf_node, filename)
        return selected_type
    if render_mode == "fullbin":
        detected_type = detect_merl_variant(file_path)
        if detected_type == "merl":
            bsdf_node.set("type", "merl")
            ET.SubElement(bsdf_node, "string", {"name": "binary", "value": file_path})
        else:
            bsdf_node.set("type", "fullmerl")
            ET.SubElement(bsdf_node, "string", {"name": "filename", "value": file_path})
        configure_bsdf_smart(bsdf_node, filename)
        return detected_type or "fullmerl_unknown"
    base_path = normalize_npy_base_path(file_path)
    for child in list(bsdf_node):
        if child.tag == "bsdf":
            bsdf_node.remove(child)
    if existing_type == "SIREN_gray_h21l5_nbrdf_npy":
        bsdf_node.set("type", existing_type)
        r_path, g_path, b_path = split_rgb_base_paths(base_path)
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename_r", "value": r_path})
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename_g", "value": g_path})
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename_b", "value": b_path})
    else:
        if existing_type.startswith("SIREN_"):
            bsdf_node.set("type", existing_type)
        else:
            bsdf_node.set("type", "nbrdf_npy")
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename", "value": base_path})
    if not any(c.get("name") == "reflectance" for c in bsdf_node):
        ET.SubElement(bsdf_node, "spectrum", {"name": "reflectance", "value": "0.5"})
    return bsdf_node.get("type", "nbrdf_npy")

def update_integrator_and_sampler(root, integrator_type, sample_count, log_placeholder):
    integrator_node = root.find("integrator")
    if integrator_node is not None:
        integrator_node.set("type", integrator_type)
    else:
        log("⚠️ 警告: 场景中未找到 integrator 节点，无法修改积分器类型", log_placeholder)
    sampler_node = root.find(".//sampler")
    if sampler_node is not None:
        found = False
        for int_node in sampler_node.findall("integer"):
            if int_node.get("name") == "sampleCount":
                int_node.set("value", str(sample_count))
                found = True
                break
        if not found:
            log("⚠️ 警告: 在 sampler 节点中未找到 name='sampleCount' 的 integer 节点，无法修改采样数量", log_placeholder)
    else:
        log("⚠️ 警告: 场景中未找到 sampler 节点，无法修改采样数量", log_placeholder)

def render_batch(render_selected, render_mode, input_dir, output_dir, auto_convert, skip_existing, progress, status, base_dir, log_placeholder=None, custom_cmd=None, integrator_type="bdpt", sample_count=256):
    if not render_selected:
        log("未选择渲染文件", log_placeholder)
        return
    scene_path = st.session_state.scene_path
    if not os.path.exists(scene_path):
        log(f"场景文件不存在: {scene_path}", log_placeholder)
        return
    base_output_dir = normalize_output_dir(output_dir)
    if base_output_dir != output_dir:
        log(f"⚠️ 输出目录已自动校正为: {base_output_dir}", log_placeholder)
    os.makedirs(base_output_dir, exist_ok=True)
    exr_dir = os.path.join(base_output_dir, "exr")
    png_dir = os.path.join(base_output_dir, "png")
    temp_xml_dir = os.path.join(str(base_dir), "data", "batch_temp_xmls")
    for d in [exr_dir, png_dir, temp_xml_dir]:
        os.makedirs(d, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(st.session_state.mitsuba_exe) + os.pathsep + env.get("PATH", "")
    with open(scene_path, "r", encoding="utf-8") as f:
        scene_xml_text = f.read()
    
    # 获取当前时间后缀 (仅保留日_时分秒，移除年份和月份)
    timestamp = datetime.datetime.now().strftime("%d_%H%M%S")
    
    total = len(render_selected)
    for idx, filename in enumerate(render_selected):
        if STOP_SIGNAL:
            log("渲染已停止 (收到停止信号)", log_placeholder)
            break
        file_path = os.path.join(input_dir, filename).replace("\\", "/")
        basename = os.path.splitext(filename)[0]
        # 添加时间戳后缀
        exr_out = os.path.join(exr_dir, f"{basename}_{timestamp}.exr")
        png_out = os.path.join(png_dir, f"{basename}_{timestamp}.png")
        if skip_existing:
            # 检查输出目录中是否存在任何以该材质名为开头的文件
            search_dir = png_dir if auto_convert else exr_dir
            ext = ".png" if auto_convert else ".exr"
            found_existing = False
            if os.path.exists(search_dir):
                for f in os.listdir(search_dir):
                    # 匹配完整名或以材质名开头且后缀正确的文件 (避免 chrome 匹配到 chrome-steel)
                    name_part = os.path.splitext(f)[0]
                    if (name_part == basename or name_part.startswith(f"{basename}_")) and f.endswith(ext):
                        found_existing = True
                        break
            
            if found_existing:
                log(f"[{idx+1}/{total}] 跳过 (检测到已存在渲染结果): {basename}", log_placeholder)
                overall_percent = (idx + 1) / total
                progress.progress(min(100, int(overall_percent * 100)))
                continue
        status.text(f"正在渲染 ({idx+1}/{total}): {filename}")
        root = ET.fromstring(scene_xml_text)
        update_integrator_and_sampler(root, integrator_type, sample_count, log_placeholder)

        ensure_hdr_film(root)

        tree = ET.ElementTree(root)
        scene_dir = os.path.dirname(os.path.abspath(scene_path))
        root_dir = st.session_state.root_dir
        for string_node in root.iter("string"):
            if string_node.get("name") == "filename":
                val = string_node.get("value")
                if val and not os.path.isabs(val) and not is_placeholder_value(val):
                    abs_val = resolve_scene_resource(scene_dir, root_dir, val)
                    if abs_val:
                        string_node.set("value", abs_val.replace("\\", "/"))
                        if not os.path.exists(abs_val):
                            log(f"⚠️ 警告: 场景引用的资源不存在: {abs_val}", log_placeholder)
        target_bsdf = find_target_bsdf(root)
        if target_bsdf is None:
            log("错误: 场景中未找到 bsdf 节点", log_placeholder)
            return
        selected_bsdf_type = update_bsdf_for_mode(target_bsdf, render_mode, file_path, filename, st.session_state.mitsuba_dir)
        if render_mode == "fullbin":
            if selected_bsdf_type == "fullmerl_unknown":
                log("  -> FullBin 文件大小与标准格式不匹配，已按 fullmerl 处理", log_placeholder)
            else:
                log(f"  -> FullBin 自动识别为 `{selected_bsdf_type}` 格式", log_placeholder)
        temp_xml = os.path.join(temp_xml_dir, f"{basename}_{timestamp}.xml")
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
                if os.path.exists(exr_out):
                    log("  -> EXR 完成", log_placeholder)
                    if auto_convert:
                        cmd_conv = [st.session_state.mtsutil_exe, "tonemap", "-o", png_out, exr_out]
                        subprocess.run(cmd_conv, env=env, check=False)
                        log("  -> PNG 完成", log_placeholder)
                else:
                    fallback_png = os.path.splitext(exr_out)[0] + ".png"
                    if os.path.exists(fallback_png):
                        os.makedirs(png_dir, exist_ok=True)
                        os.replace(fallback_png, png_out)
                        log("  -> PNG 完成 (场景输出为 PNG，已移动)", log_placeholder)
                    else:
                        log("  -> 警告: 未找到 EXR/PNG 输出", log_placeholder)
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

def run_compile(compile_cmd, conda_env, log_placeholder=None, compile_label=None, vcvarsall_path=None):
    vcvarsall = vcvarsall_path.strip() if vcvarsall_path else DEFAULT_VCVARSALL_PATH
    if vcvarsall:
        if vcvarsall.lower().endswith(".lnk"):
            vcvarsall = resolve_vcvarsall_from_shortcut(vcvarsall)
            if not vcvarsall:
                log("无法从快捷方式解析 vcvarsall.bat，请检查链接目标", log_placeholder)
                return
    if vcvarsall:
        if not os.path.exists(vcvarsall):
            log(f"默认 vcvarsall.bat 不存在，尝试自动检测: {vcvarsall}", log_placeholder)
            vcvarsall = ""
    if not vcvarsall:
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
    if compile_label:
        log(f"编译预设: {compile_label}", log_placeholder)
    log(f"vcvarsall 路径: {vcvarsall}", log_placeholder)
    log(f"编译工作目录: {work_dir}", log_placeholder)
    log(f"编译命令: {compile_cmd}", log_placeholder)
    conda_cmd = os.environ.get("CONDA_EXE") or "conda"
    log(f"Conda 运行器: {conda_cmd}", log_placeholder)
    log("开始执行编译", log_placeholder)
    final_exit_code, output_lines = execute_compile_attempt(
        work_dir,
        vcvarsall,
        conda_cmd,
        conda_env,
        dep_bin,
        dep_lib,
        compile_cmd,
        log_placeholder
    )
    if final_exit_code != 0 and has_manifest_access_denied(output_lines):
        serial_cmd = build_serial_compile_command(compile_cmd)
        if serial_cmd and serial_cmd != compile_cmd:
            log("检测到 mt.exe manifest 写入冲突，2 秒后使用串行增量补编译", log_placeholder)
            time.sleep(2)
            log(f"串行补编译命令: {serial_cmd}", log_placeholder)
            final_exit_code, _ = execute_compile_attempt(
                work_dir,
                vcvarsall,
                conda_cmd,
                conda_env,
                dep_bin,
                dep_lib,
                serial_cmd,
                log_placeholder
            )
    if final_exit_code == 0:
        log("编译成功", log_placeholder)
    else:
        log("编译失败", log_placeholder)

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

def resolve_comparison_files(basename, dir_m1, dir_m2):
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
    return name_root, f_m1, f_m2

def process_single_file(f_gt, dir_m1, dir_m2):
    basename = os.path.basename(f_gt)
    _, f_m1, f_m2 = resolve_comparison_files(basename, dir_m1, dir_m2)
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

def run_comp_generation(comp_config, comp_output_dir, comp_show_label, comp_show_filename, selected_files=None):
    """
    comp_config: list of dicts with {"dir": str, "label": str}
    selected_files: optional list of filenames (basenames) to process
    """
    valid_configs = [c for c in comp_config if os.path.exists(c["dir"])]
    if not valid_configs:
        log("没有有效的输入目录，请检查配置")
        return
    
    os.makedirs(comp_output_dir, exist_ok=True)
    
    # Use first valid directory as the source of filenames if none provided
    if not selected_files:
        files = sorted(glob.glob(os.path.join(valid_configs[0]["dir"], "*.png")))
        basenames = [os.path.basename(f) for f in files]
    else:
        basenames = selected_files

    if not basenames:
        log("未找到可处理的图片")
        return

    try:
        font = ImageFont.truetype("arial.ttf", 20)
        title_font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
        title_font = font

    processed_rows = [] # List of Image objects (each is one row)
    
    count = 0
    padding = 10
    label_height = 30 if comp_show_label else 0
    filename_height = 40 if comp_show_filename else 0

    for basename in basenames:
        # Ensure it has .png extension
        if not basename.lower().endswith(".png"):
            basename += ".png"
            
        # Extract pure name from the basename (assuming format name_dd_HHMMSS or just name)
        # If the basename already has a timestamp, we need to extract the material name part
        name_root = os.path.splitext(basename)[0]
        # Heuristic: if it ends with _dd_HHMMSS (e.g. _14_030834), strip it
        # Pattern: _\d{1,2}_\d{6}$
        import re
        match = re.search(r'^(.*)_\d{1,2}_\d{6}$', name_root)
        if match:
            pure_name = match.group(1)
        else:
            pure_name = name_root

        # Try to resolve files for each config
        all_found = True
        current_images = []
        current_labels = []
        for config in valid_configs:
            # Try exact match first
            target_path = os.path.join(config["dir"], basename)
            if not os.path.exists(target_path):
                # Try fuzzy matching in this directory using pure_name
                found_f = None
                for f in os.listdir(config["dir"]):
                    if not f.lower().endswith(".png"):
                        continue
                    f_base = os.path.splitext(f)[0]
                    
                    # Check if file matches pure_name exactly or pure_name_timestamp
                    # 1. Exact match with pure_name (e.g. "alum-bronze.png")
                    if f_base == pure_name:
                        found_f = os.path.join(config["dir"], f)
                        break
                    
                    # 2. Match pure_name + timestamp suffix (e.g. "alum-bronze_15_120000.png")
                    if f_base.startswith(pure_name + "_"):
                        # Ensure the prefix is indeed the full material name
                        # (e.g. "chrome" shouldn't match "chrome-steel_...")
                        # Since we check startswith(pure_name + "_"), this is safe.
                        found_f = os.path.join(config["dir"], f)
                        break
                        
                if found_f:
                    target_path = found_f
                else:
                    all_found = False
                    break
            
            current_images.append(Image.open(target_path))
            current_labels.append(config["label"])

        if not all_found or not current_images:
            log(f"跳过 {basename}: 缺失部分对比文件")
            continue

        # Resize all to match first image
        w, h = current_images[0].size
        for i in range(1, len(current_images)):
            current_images[i] = current_images[i].resize((w, h), Image.LANCZOS)

        num_cols = len(current_images)
        
        # Calculate width needed for filename on the left
        name_width = 0
        if comp_show_filename:
            # Set a narrower fixed width for vertical text
            name_width = 60 
        
        row_w = name_width + w * num_cols + padding * (num_cols + 1)
        row_h = h + padding * 2 
        
        row_img = Image.new("RGB", (row_w, row_h), (255, 255, 255))
        draw_row = ImageDraw.Draw(row_img)

        if comp_show_filename:
            # Draw name on the left, vertically rotated -90 degrees
            # Create a temporary image for the text
            # Measure text size first
            temp_img = Image.new("RGB", (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), pure_name, font=title_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            # Create image for text, slightly larger than bounding box
            txt_img = Image.new("RGBA", (text_w + 10, text_h + 10), (255, 255, 255, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((0, 0), pure_name, font=title_font, fill=(0, 0, 0))
            
            # Rotate text image by 90 degrees
            txt_rotated = txt_img.rotate(90, expand=True)
            
            # Calculate position to center vertically in the name column
            rot_w, rot_h = txt_rotated.size
            # Center horizontally in name_width
            dest_x = (name_width - rot_w) // 2
            # Center vertically in row_h
            dest_y = (row_h - rot_h) // 2
            
            row_img.paste(txt_rotated, (dest_x, dest_y), txt_rotated)

        for i, img in enumerate(current_images):
            x = name_width + padding + i * (w + padding)
            y = padding 
            row_img.paste(img, (x, y))
        
        processed_rows.append(row_img)
        count += 1

    if not processed_rows:
        log("未能生成任何对比拼图")
        return

    # Merge all rows into one big image
    total_w = processed_rows[0].width
    
    # Calculate header height if labels are shown
    header_height = 0
    header_img = None
    if comp_show_label and current_labels:
        header_height = 40
        header_img = Image.new("RGB", (total_w, header_height), (255, 255, 255))
        draw_header = ImageDraw.Draw(header_img)
        
        # Draw labels aligned with image columns
        # First column is empty (for names)
        # Images start at: name_width + padding + i * (w + padding)
        
        # We need 'name_width' again. It was 300 if comp_show_filename else 0.
        name_col_w = 300 if comp_show_filename else 0
        
        for i, label in enumerate(current_labels):
            x = name_col_w + padding + i * (w + padding)
            # Center text in this column
            bbox = draw_header.textbbox((0, 0), label, font=title_font)
            text_w = bbox[2] - bbox[0]
            text_x = x + (w - text_w) / 2
            text_y = (header_height - (bbox[3] - bbox[1])) / 2
            draw_header.text((text_x, text_y), label, fill=(0, 0, 0), font=title_font)

    total_h = sum(img.height for img in processed_rows) + header_height
    
    merged_img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
    current_y = 0
    
    if header_img:
        merged_img.paste(header_img, (0, 0))
        current_y += header_height

    for row_img in processed_rows:
        merged_img.paste(row_img, (0, current_y))
        current_y += row_img.height
    
    # Save merged image
    merged_filename = "merged_comparison.png"
    out_path = os.path.join(comp_output_dir, merged_filename)
    merged_img.save(out_path)
    
    st.image(merged_img, caption="合并对比拼图", use_container_width=True)
    log(f"合并对比拼图已生成: {out_path}")

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

def select_preset_test_set(available_files):
    """
    Selects the 20 materials from the test set if they are available.
    """
    apply_preset_test_set_selection(available_files, "render_selected", "预设测试材质")
    return

    selected = []
    for preset in TEST_SET_20:
        # Check if any available file matches the preset name (ignoring extension)
        found = False
        for f in available_files:
            if os.path.splitext(f)[0] == preset:
                selected.append(f)
                found = True
                break
        if not found:
            # Try fuzzy match if exact match fails
            for f in available_files:
                if preset in f:
                    selected.append(f)
                    found = True
                    break
    
    if selected:
        st.session_state.render_selected = list(set(selected)) # Remove duplicates
        st.success(f"已选中 {len(st.session_state.render_selected)} 个预设测试材质")
    else:
        st.warning("当前目录未找到预设测试集中的材质文件")
    st.rerun()
