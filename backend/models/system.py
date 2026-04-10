from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SystemDependencySetting(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=1024)


class SystemDependencyCheck(BaseModel):
    id: str
    label: str
    path: str
    exists: bool
    is_dir: bool
    is_file: bool
    status: str
    message: str


class SystemVirtualEnvSetting(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=128)
    manager: str = Field(default="conda", min_length=1, max_length=32)
    env_name: str = Field(min_length=1, max_length=128)
    role: str = Field(default="", max_length=128)


class SystemVirtualEnvCheck(BaseModel):
    id: str
    label: str
    manager: str
    env_name: str
    role: str
    exists: bool
    status: str
    message: str
    prefix: str = ""


class SystemSettings(BaseModel):
    project_root: str
    mitsuba_exe: str
    mtsutil_exe: str
    preset_label: str
    conda_env: str
    compile_cmd: str
    vcvarsall_path: str
    work_dir: str
    dependencies: List[SystemDependencySetting] = Field(default_factory=list)
    virtual_envs: List[SystemVirtualEnvSetting] = Field(default_factory=list)


class SystemCompileDefaults(BaseModel):
    preset_label: str
    compile_cmd: str
    conda_env: str
    vcvarsall_path: str
    work_dir: str
    dep_bin: str
    dep_lib: str
    dependency_paths: List[str] = Field(default_factory=list)


class SystemSettingsResponse(BaseModel):
    settings: SystemSettings
    checks: List[SystemDependencyCheck] = Field(default_factory=list)
    env_checks: List[SystemVirtualEnvCheck] = Field(default_factory=list)


class SystemSummaryResponse(BaseModel):
    project_root: str
    mitsuba_dir: str
    mitsuba_exe: str
    mtsutil_exe: str
    mitsuba_exists: bool
    mtsutil_exists: bool
    available_modules: List[str]
    available_path_keys: List[str]
    compile_defaults: SystemCompileDefaults
    settings: SystemSettings
    checks: List[SystemDependencyCheck] = Field(default_factory=list)
    env_checks: List[SystemVirtualEnvCheck] = Field(default_factory=list)


class SystemSettingsRequest(BaseModel):
    project_root: str = Field(default="", max_length=1024)
    mitsuba_exe: str = Field(default="", max_length=1024)
    mtsutil_exe: str = Field(default="", max_length=1024)
    compile_cmd: str = Field(default="scons --parallelize", min_length=1, max_length=512)
    conda_env: str = Field(default="mitsuba-build", min_length=1, max_length=128)
    preset_label: str = Field(default="Default SCons Parallel Build", max_length=128)
    vcvarsall_path: str = Field(default="", max_length=1024)
    work_dir: str = Field(default="", max_length=1024)
    dependencies: List[SystemDependencySetting] = Field(default_factory=list)
    virtual_envs: List[SystemVirtualEnvSetting] = Field(default_factory=list)


class SystemCompileRequest(BaseModel):
    compile_cmd: str = Field(default="scons --parallelize", min_length=1, max_length=512)
    conda_env: str = Field(default="mitsuba-build", min_length=1, max_length=128)
    compile_label: str = Field(default="Default SCons Parallel Build", max_length=128)
    vcvarsall_path: str = Field(default="", max_length=1024)
    work_dir: str = Field(default="", max_length=1024)
    dependency_paths: List[str] = Field(default_factory=list)
