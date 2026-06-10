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
    "renders_merl_png": PROJECT_ROOT / "data" / "renders" / "merl" / "png",
    "renders_hyperbrdf_png": PROJECT_ROOT / "data" / "renders" / "hyperbrdf" / "png",
    "renders_neural_brdf_png": PROJECT_ROOT / "data" / "renders" / "neural-brdf" / "png",
    "renders_hypersnbrdf_png": PROJECT_ROOT / "data" / "renders" / "hypersnbrdf" / "png",
    "analysis_grids": PROJECT_ROOT / "data" / "analysis" / "grids",
    "analysis_comparisons": PROJECT_ROOT / "data" / "analysis" / "comparisons",
    "train_hyper_extracted_pts": PROJECT_ROOT / "models" / "HyperBRDF" / "results" / "extracted_pts",
    "renders_merl_exr": PROJECT_ROOT / "data" / "renders" / "merl" / "exr",
    "renders_hyperbrdf_exr": PROJECT_ROOT / "data" / "renders" / "hyperbrdf" / "exr",
    "renders_neural_brdf_exr": PROJECT_ROOT / "data" / "renders" / "neural-brdf" / "exr",
    "materials": PROJECT_ROOT / "data" / "materials",
    "render_input_hyperbrdf": PROJECT_ROOT / "data" / "render-input" / "hyperbrdf",
    "render_input_neural_brdf": PROJECT_ROOT / "data" / "render-input" / "neural-brdf",
    "scene_xml": PROJECT_ROOT / "scene" / "assets",
}


def resolve_safe_path(path_key: str) -> Path:
    if path_key not in SAFE_PATHS:
        raise KeyError(path_key)
    return SAFE_PATHS[path_key]
