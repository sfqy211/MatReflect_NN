from pathlib import Path

from .config import PROJECT_ROOT


def get_mitsuba_paths():
    local_dir = PROJECT_ROOT / "mitsuba" / "dist"
    mitsuba_dir = local_dir if local_dir.exists() else Path(r"d:\mitsuba\dist")
    return {
        "mitsuba_dir": mitsuba_dir,
        "mitsuba_exe": mitsuba_dir / "mitsuba.exe",
        "mtsutil_exe": mitsuba_dir / "mtsutil.exe",
    }


SAFE_PATHS = {
    "render_outputs_binary_png": PROJECT_ROOT / "data" / "outputs" / "binary" / "png",
    "render_outputs_fullbin_png": PROJECT_ROOT / "data" / "outputs" / "fullbin" / "png",
    "render_outputs_npy_png": PROJECT_ROOT / "data" / "outputs" / "npy" / "png",
    "render_outputs_binary_exr": PROJECT_ROOT / "data" / "outputs" / "binary" / "exr",
    "render_outputs_fullbin_exr": PROJECT_ROOT / "data" / "outputs" / "fullbin" / "exr",
    "render_outputs_npy_exr": PROJECT_ROOT / "data" / "outputs" / "npy" / "exr",
    "inputs_binary": PROJECT_ROOT / "data" / "inputs" / "binary",
    "inputs_fullbin": PROJECT_ROOT / "data" / "inputs" / "fullbin",
    "inputs_npy": PROJECT_ROOT / "data" / "inputs" / "npy",
    "scene_xml": PROJECT_ROOT / "scene" / "dj_xml",
}


def resolve_safe_path(path_key: str) -> Path:
    if path_key not in SAFE_PATHS:
        raise KeyError(path_key)
    return SAFE_PATHS[path_key]
