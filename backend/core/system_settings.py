from __future__ import annotations

import json
from pathlib import Path
from typing import List
from uuid import uuid4

from backend.core.config import PROJECT_ROOT, RUNTIME_ROOT
from backend.models.system import SystemDependencySetting, SystemSettings


SYSTEM_SETTINGS_PATH = RUNTIME_ROOT / "system_settings.json"


def _default_dependencies(work_dir: Path) -> List[SystemDependencySetting]:
    return [
        SystemDependencySetting(id="dep-bin", label="依赖 bin", path=str((work_dir / "dependencies" / "bin").resolve())),
        SystemDependencySetting(id="dep-lib", label="依赖 lib", path=str((work_dir / "dependencies" / "lib").resolve())),
    ]


def build_default_system_settings() -> SystemSettings:
    work_dir = (PROJECT_ROOT / "mitsuba").resolve()
    mitsuba_dir = (work_dir / "dist").resolve()
    return SystemSettings(
        project_root=str(PROJECT_ROOT.resolve()),
        mitsuba_exe=str((mitsuba_dir / "mitsuba.exe").resolve()),
        mtsutil_exe=str((mitsuba_dir / "mtsutil.exe").resolve()),
        preset_label="Default SCons Parallel Build",
        conda_env="mitsuba-build",
        compile_cmd="scons --parallelize",
        vcvarsall_path=r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat",
        work_dir=str(work_dir),
        dependencies=_default_dependencies(work_dir),
    )


def _normalize_dependency(raw: SystemDependencySetting) -> SystemDependencySetting:
    dep_id = raw.id.strip() or f"dep-{uuid4().hex[:8]}"
    label = raw.label.strip() or dep_id
    path = raw.path.strip()
    return SystemDependencySetting(id=dep_id, label=label, path=path)


def _coerce_settings(raw_data: dict) -> SystemSettings:
    defaults = build_default_system_settings()
    dependencies_data = raw_data.get("dependencies", [])
    dependencies = []
    for entry in dependencies_data:
        try:
            dependency = SystemDependencySetting.model_validate(entry)
        except Exception:
            continue
        dependencies.append(_normalize_dependency(dependency))
    if not dependencies:
        dependencies = defaults.dependencies

    return SystemSettings(
        project_root=str(raw_data.get("project_root") or defaults.project_root),
        mitsuba_exe=str(raw_data.get("mitsuba_exe") or defaults.mitsuba_exe),
        mtsutil_exe=str(raw_data.get("mtsutil_exe") or defaults.mtsutil_exe),
        preset_label=str(raw_data.get("preset_label") or defaults.preset_label),
        conda_env=str(raw_data.get("conda_env") or defaults.conda_env),
        compile_cmd=str(raw_data.get("compile_cmd") or defaults.compile_cmd),
        vcvarsall_path=str(raw_data.get("vcvarsall_path") or defaults.vcvarsall_path),
        work_dir=str(raw_data.get("work_dir") or defaults.work_dir),
        dependencies=dependencies,
    )


def load_system_settings() -> SystemSettings:
    defaults = build_default_system_settings()
    if not SYSTEM_SETTINGS_PATH.exists():
        return defaults
    try:
        raw_data = json.loads(SYSTEM_SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    if not isinstance(raw_data, dict):
        return defaults
    return _coerce_settings(raw_data)


def save_system_settings(settings: SystemSettings) -> SystemSettings:
    normalized = _coerce_settings(settings.model_dump())
    SYSTEM_SETTINGS_PATH.write_text(json.dumps(normalized.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized
