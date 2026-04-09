from __future__ import annotations

from pydantic import BaseModel, Field


class SystemCompileDefaults(BaseModel):
    preset_label: str
    compile_cmd: str
    conda_env: str
    vcvarsall_path: str
    work_dir: str
    dep_bin: str
    dep_lib: str


class SystemSummaryResponse(BaseModel):
    project_root: str
    mitsuba_dir: str
    mitsuba_exe: str
    mtsutil_exe: str
    mitsuba_exists: bool
    mtsutil_exists: bool
    available_modules: list[str]
    available_path_keys: list[str]
    compile_defaults: SystemCompileDefaults


class SystemCompileRequest(BaseModel):
    compile_cmd: str = Field(default="scons --parallelize", min_length=1, max_length=512)
    conda_env: str = Field(default="mitsuba-build", min_length=1, max_length=128)
    compile_label: str = Field(default="默认 SCons 并行编译", max_length=128)
    vcvarsall_path: str = Field(default="", max_length=512)
