from __future__ import annotations

import json
from pathlib import Path
from typing import List
from uuid import uuid4

from backend.core.config import PROJECT_ROOT, RUNTIME_ROOT
from backend.models.system import SystemDependencySetting, SystemSettings, SystemVirtualEnvSetting


SYSTEM_SETTINGS_PATH = RUNTIME_ROOT / "system_settings.json"


def _default_dependencies(work_dir: Path) -> List[SystemDependencySetting]:
    return [
        SystemDependencySetting(id="dep-bin", label="依赖 bin", path=str((work_dir / "dependencies" / "bin").resolve())),
        SystemDependencySetting(id="dep-lib", label="依赖 lib", path=str((work_dir / "dependencies" / "lib").resolve())),
    ]


def _default_virtual_envs() -> List[SystemVirtualEnvSetting]:
    return [
        SystemVirtualEnvSetting(id="env-matreflect", label="项目主环境", manager="conda", env_name="matreflect", role="项目后端 / 桌面封装"),
        SystemVirtualEnvSetting(id="env-mitsuba-build", label="Mitsuba 编译环境", manager="conda", env_name="mitsuba-build", role="Mitsuba 编译"),
        SystemVirtualEnvSetting(id="env-nbrdf-train", label="Neural-BRDF 环境", manager="conda", env_name="nbrdf-train", role="Neural-BRDF 训练与转换"),
        SystemVirtualEnvSetting(id="env-hyperbrdf", label="HyperBRDF 环境", manager="conda", env_name="hyperbrdf", role="HyperBRDF 训练 / 提取 / 解码"),
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
        virtual_envs=_default_virtual_envs(),
    )


def _normalize_dependency(raw: SystemDependencySetting) -> SystemDependencySetting:
    dep_id = raw.id.strip() or f"dep-{uuid4().hex[:8]}"
    label = raw.label.strip() or dep_id
    path = raw.path.strip()
    return SystemDependencySetting(id=dep_id, label=label, path=path)


def _normalize_virtual_env(raw: SystemVirtualEnvSetting) -> SystemVirtualEnvSetting:
    env_id = raw.id.strip() or f"env-{uuid4().hex[:8]}"
    label = raw.label.strip() or env_id
    manager = raw.manager.strip() or "conda"
    env_name = raw.env_name.strip()
    role = raw.role.strip()
    return SystemVirtualEnvSetting(id=env_id, label=label, manager=manager, env_name=env_name, role=role)


def _coerce_settings(raw_data: dict) -> SystemSettings:
    defaults = build_default_system_settings()
    dependencies_data = raw_data.get("dependencies", [])
    virtual_envs_data = raw_data.get("virtual_envs", [])
    dependencies = []
    virtual_envs = []
    for entry in dependencies_data:
        try:
            dependency = SystemDependencySetting.model_validate(entry)
        except Exception:
            continue
        dependencies.append(_normalize_dependency(dependency))
    if not dependencies:
        dependencies = defaults.dependencies
    for entry in virtual_envs_data:
        try:
            virtual_env = SystemVirtualEnvSetting.model_validate(entry)
        except Exception:
            continue
        if virtual_env.env_name.strip():
            virtual_envs.append(_normalize_virtual_env(virtual_env))
    if not virtual_envs:
        virtual_envs = defaults.virtual_envs

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
        virtual_envs=virtual_envs,
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
