from pathlib import Path

from .config import PROJECT_ROOT
from .system_settings import load_system_settings


def get_mitsuba_paths():
    settings = load_system_settings()
    mitsuba_exe = Path(settings.mitsuba_exe).expanduser()
    mtsutil_exe = Path(settings.mtsutil_exe).expanduser()
    if mitsuba_exe.is_absolute():
        mitsuba_dir = mitsuba_exe.parent
    else:
        mitsuba_dir = (PROJECT_ROOT / mitsuba_exe).resolve().parent
        mitsuba_exe = mitsuba_dir / mitsuba_exe.name
    if not mitsuba_dir.exists():
        local_dir = PROJECT_ROOT / "mitsuba" / "dist"
        mitsuba_dir = local_dir if local_dir.exists() else Path(r"d:\mitsuba\dist")
        mitsuba_exe = mitsuba_dir / "mitsuba.exe"
        mtsutil_exe = mitsuba_dir / "mtsutil.exe"
    elif not mtsutil_exe.is_absolute():
        mtsutil_exe = (PROJECT_ROOT / mtsutil_exe).resolve()
    return {
        "mitsuba_dir": mitsuba_dir,
        "mitsuba_exe": mitsuba_exe,
        "mtsutil_exe": mtsutil_exe,
    }


SAFE_PATHS = {
    "render_outputs_binary_png": PROJECT_ROOT / "data" / "outputs" / "binary" / "png",
    "render_outputs_fullbin_png": PROJECT_ROOT / "data" / "outputs" / "fullbin" / "png",
    "render_outputs_npy_png": PROJECT_ROOT / "data" / "outputs" / "npy" / "png",
    "analysis_grids": PROJECT_ROOT / "data" / "outputs" / "grids",
    "analysis_comparisons": PROJECT_ROOT / "data" / "outputs" / "comparisons",
    "train_hyper_extracted_pts": PROJECT_ROOT / "HyperBRDF" / "results" / "extracted_pts",
    "render_outputs_binary_exr": PROJECT_ROOT / "data" / "outputs" / "binary" / "exr",
    "render_outputs_fullbin_exr": PROJECT_ROOT / "data" / "outputs" / "fullbin" / "exr",
    "render_outputs_npy_exr": PROJECT_ROOT / "data" / "outputs" / "npy" / "exr",
    "inputs_binary": PROJECT_ROOT / "data" / "inputs" / "binary",
    "inputs_fullbin": PROJECT_ROOT / "data" / "inputs" / "fullbin",
    "inputs_npy": PROJECT_ROOT / "data" / "inputs" / "npy",
    "scene_xml": PROJECT_ROOT / "scene" / "assets",
}


def resolve_safe_path(path_key: str) -> Path:
    if path_key not in SAFE_PATHS:
        raise KeyError(path_key)
    return SAFE_PATHS[path_key]
