from pathlib import Path

def get_project_root():
    return Path(__file__).resolve().parents[2]

def get_mitsuba_paths(root_dir=None):
    base_root = Path(root_dir) if root_dir else get_project_root()
    local_dir = base_root / "mitsuba" / "dist"
    mitsuba_dir = local_dir if local_dir.exists() else Path(r"d:\mitsuba\dist")
    return mitsuba_dir, mitsuba_dir / "mitsuba.exe", mitsuba_dir / "mtsutil.exe"
