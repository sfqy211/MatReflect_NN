from __future__ import annotations

import asyncio
import json
import locale
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from backend.core.config import LOGS_ROOT, PROJECT_ROOT
from backend.core.conda import find_conda_command
from backend.core.paths import SAFE_PATHS, get_mitsuba_paths
from backend.core.runtime_logging import log_task_message
from backend.core.system_settings import build_default_system_settings, load_system_settings, save_system_settings
from backend.core.threaded_subprocess import process_is_running, run_process_streaming, terminate_process
from backend.models.common import TaskDetailResponse
from backend.models.system import (
    SystemCompileDefaults,
    SystemCompileRequest,
    SystemDependencyCheck,
    SystemDependencySetting,
    SystemSettings,
    SystemSettingsRequest,
    SystemSettingsResponse,
    SystemSummaryResponse,
    SystemVirtualEnvCheck,
    SystemVirtualEnvSetting,
)
from backend.services.task_manager import task_manager


DEFAULT_VCVARSALL_PATH = r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat"


def decode_subprocess_output(raw: Optional[Union[bytes, str]]) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    preferred = locale.getpreferredencoding(False) or "utf-8"
    candidates: list[str] = []
    for encoding in ("utf-8", preferred, "gb18030", "cp936"):
        if encoding and encoding.lower() not in {candidate.lower() for candidate in candidates}:
            candidates.append(encoding)
    for encoding in candidates:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def build_serial_compile_command(compile_cmd: str) -> Optional[str]:
    if not compile_cmd or "scons" not in compile_cmd.lower():
        return None
    serial_cmd = re.sub(r"(?i)(^|\s)-j\s*\d+", r"\1-j1", compile_cmd)
    serial_cmd = re.sub(r"(?i)(^|\s)--jobs(?:=|\s*)\d+", r"\1--jobs=1", serial_cmd)
    if serial_cmd == compile_cmd:
        serial_cmd = f"{compile_cmd} -j1"
    return serial_cmd


def has_manifest_access_denied(log_lines: List[str]) -> bool:
    joined = "\n".join(log_lines).lower()
    patterns = [
        "mt.exe : general error c101008d",
        "failed to write the updated manifest",
        "error 31",
        "access is denied",
        "拒绝访问",
    ]
    return any(pattern in joined for pattern in patterns)


class SystemService:
    def __init__(self) -> None:
        self._processes: dict[str, Any] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def _resolve_path(self, path_value: str, base_dir: Optional[Path] = None) -> Path:
        raw_path = Path(path_value).expanduser()
        if raw_path.is_absolute():
            return raw_path.resolve(strict=False)
        anchor = base_dir or PROJECT_ROOT
        return (anchor / raw_path).resolve(strict=False)

    def _dependency_paths(self, settings: SystemSettings) -> List[Path]:
        project_root = self._resolve_path(settings.project_root)
        return [self._resolve_path(dependency.path, project_root) for dependency in settings.dependencies if dependency.path.strip()]

    def _conda_env_prefix_map(self) -> tuple[dict[str, str], Optional[str]]:
        conda_cmd = find_conda_command()
        if not conda_cmd:
            return {}, "未检测到 conda 命令"
        use_cmd = conda_cmd.lower().endswith((".bat", ".cmd"))
        cmd = ["cmd", "/c", conda_cmd, "env", "list", "--json"] if use_cmd else [conda_cmd, "env", "list", "--json"]
        try:
            output = subprocess.check_output(
                cmd,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
            )
        except Exception as exc:
            return {}, f"读取 conda 环境失败: {exc}"
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            return {}, "conda env list 返回内容无法解析"
        env_prefixes = {}
        for prefix in payload.get("envs", []):
            prefix_path = Path(prefix)
            env_prefixes[prefix_path.name] = str(prefix_path)
        return env_prefixes, None

    def _check_path(self, key: str, label: str, path_value: str, *, expect: str, base_dir: Optional[Path]) -> SystemDependencyCheck:
        if not path_value.strip():
            return SystemDependencyCheck(
                id=key,
                label=label,
                path="",
                exists=False,
                is_dir=False,
                is_file=False,
                status="warning",
                message="未配置",
            )
        resolved = self._resolve_path(path_value, base_dir)
        exists = resolved.exists()
        is_dir = resolved.is_dir()
        is_file = resolved.is_file()
        if not exists:
            status = "missing"
            message = "路径不存在"
        elif expect == "dir" and not is_dir:
            status = "invalid"
            message = "应为目录"
        elif expect == "file" and not is_file:
            status = "invalid"
            message = "应为文件"
        else:
            status = "ok"
            message = "正常"
        return SystemDependencyCheck(
            id=key,
            label=label,
            path=str(resolved),
            exists=exists,
            is_dir=is_dir,
            is_file=is_file,
            status=status,
            message=message,
        )

    def _build_checks(self, settings: SystemSettings) -> List[SystemDependencyCheck]:
        project_root = self._resolve_path(settings.project_root)
        checks = [
            self._check_path("project_root", "项目路径", settings.project_root, expect="dir", base_dir=PROJECT_ROOT),
            self._check_path("mitsuba_exe", "Mitsuba EXE", settings.mitsuba_exe, expect="file", base_dir=project_root),
            self._check_path("mtsutil_exe", "mtsutil EXE", settings.mtsutil_exe, expect="file", base_dir=project_root),
            self._check_path("binary_input_dir", "MERL 输入目录", settings.binary_input_dir, expect="dir", base_dir=project_root),
            self._check_path("npy_input_dir", "NPY 输入目录", settings.npy_input_dir, expect="dir", base_dir=project_root),
            self._check_path("fullbin_input_dir", "FullBin 输入目录", settings.fullbin_input_dir, expect="dir", base_dir=project_root),
            self._check_path("brdf_output_dir", "BRDF 输出根目录", settings.brdf_output_dir, expect="dir", base_dir=project_root),
            self._check_path("npy_output_dir", "NPY 输出根目录", settings.npy_output_dir, expect="dir", base_dir=project_root),
            self._check_path("fullbin_output_dir", "FullBin 输出根目录", settings.fullbin_output_dir, expect="dir", base_dir=project_root),
            self._check_path("grids_output_dir", "网格拼图输出目录", settings.grids_output_dir, expect="dir", base_dir=project_root),
            self._check_path("comparisons_output_dir", "对比拼图输出目录", settings.comparisons_output_dir, expect="dir", base_dir=project_root),
            self._check_path("work_dir", "编译工作目录", settings.work_dir, expect="dir", base_dir=project_root),
        ]
        if settings.vcvarsall_path.strip():
            checks.append(self._check_path("vcvarsall_path", "vcvarsall", settings.vcvarsall_path, expect="file", base_dir=project_root))
        else:
            checks.append(
                SystemDependencyCheck(
                    id="vcvarsall_path",
                    label="vcvarsall",
                    path="",
                    exists=False,
                    is_dir=False,
                    is_file=False,
                    status="warning",
                    message="留空时将在编译时自动探测",
                )
            )
        for dependency in settings.dependencies:
            checks.append(self._check_path(dependency.id, dependency.label, dependency.path, expect="dir", base_dir=project_root))
        return checks

    def _build_env_checks(self, settings: SystemSettings) -> List[SystemVirtualEnvCheck]:
        env_prefixes, error_message = self._conda_env_prefix_map()
        checks: List[SystemVirtualEnvCheck] = []
        for env in settings.virtual_envs:
            if env.manager != "conda":
                checks.append(
                    SystemVirtualEnvCheck(
                        id=env.id,
                        label=env.label,
                        manager=env.manager,
                        env_name=env.env_name,
                        role=env.role,
                        exists=False,
                        status="unsupported",
                        message=f"暂不支持的环境管理器: {env.manager}",
                        prefix="",
                    )
                )
                continue
            if error_message:
                checks.append(
                    SystemVirtualEnvCheck(
                        id=env.id,
                        label=env.label,
                        manager=env.manager,
                        env_name=env.env_name,
                        role=env.role,
                        exists=False,
                        status="warning",
                        message=error_message,
                        prefix="",
                    )
                )
                continue
            prefix = env_prefixes.get(env.env_name, "")
            exists = bool(prefix)
            checks.append(
                SystemVirtualEnvCheck(
                    id=env.id,
                    label=env.label,
                    manager=env.manager,
                    env_name=env.env_name,
                    role=env.role,
                    exists=exists,
                    status="ok" if exists else "missing",
                    message="环境可用" if exists else "未找到该 conda 环境",
                    prefix=prefix,
                )
            )
        return checks

    def _coerce_settings_request(self, request: SystemSettingsRequest) -> SystemSettings:
        defaults = build_default_system_settings()
        dependencies = [SystemDependencySetting.model_validate(item.model_dump()) for item in request.dependencies if item.path.strip()]
        virtual_envs = [SystemVirtualEnvSetting.model_validate(item.model_dump()) for item in request.virtual_envs if item.env_name.strip()]
        return SystemSettings(
            project_root=request.project_root.strip() or defaults.project_root,
            mitsuba_exe=request.mitsuba_exe.strip() or defaults.mitsuba_exe,
            mtsutil_exe=request.mtsutil_exe.strip() or defaults.mtsutil_exe,
            binary_input_dir=request.binary_input_dir.strip() or defaults.binary_input_dir,
            npy_input_dir=request.npy_input_dir.strip() or defaults.npy_input_dir,
            fullbin_input_dir=request.fullbin_input_dir.strip() or defaults.fullbin_input_dir,
            brdf_output_dir=request.brdf_output_dir.strip() or defaults.brdf_output_dir,
            npy_output_dir=request.npy_output_dir.strip() or defaults.npy_output_dir,
            fullbin_output_dir=request.fullbin_output_dir.strip() or defaults.fullbin_output_dir,
            grids_output_dir=request.grids_output_dir.strip() or defaults.grids_output_dir,
            comparisons_output_dir=request.comparisons_output_dir.strip() or defaults.comparisons_output_dir,
            preset_label=request.preset_label.strip() or defaults.preset_label,
            conda_env=request.conda_env.strip() or defaults.conda_env,
            compile_cmd=request.compile_cmd.strip() or defaults.compile_cmd,
            vcvarsall_path=request.vcvarsall_path.strip(),
            work_dir=request.work_dir.strip() or defaults.work_dir,
            dependencies=dependencies or defaults.dependencies,
            virtual_envs=virtual_envs or defaults.virtual_envs,
        )

    def _compile_defaults_from_settings(self, settings: SystemSettings) -> SystemCompileDefaults:
        dependency_paths = [str(path) for path in self._dependency_paths(settings)]
        dep_bin = next((dependency.path for dependency in settings.dependencies if "bin" in dependency.label.lower() or dependency.id == "dep-bin"), "")
        dep_lib = next((dependency.path for dependency in settings.dependencies if "lib" in dependency.label.lower() or dependency.id == "dep-lib"), "")
        return SystemCompileDefaults(
            preset_label=settings.preset_label,
            compile_cmd=settings.compile_cmd,
            conda_env=settings.conda_env,
            vcvarsall_path=settings.vcvarsall_path,
            work_dir=settings.work_dir,
            dep_bin=dep_bin,
            dep_lib=dep_lib,
            dependency_paths=dependency_paths,
        )

    def get_settings_response(self) -> SystemSettingsResponse:
        settings = load_system_settings()
        return SystemSettingsResponse(settings=settings, checks=self._build_checks(settings), env_checks=self._build_env_checks(settings))

    def save_settings(self, request: SystemSettingsRequest) -> SystemSettingsResponse:
        settings = self._coerce_settings_request(request)
        saved = save_system_settings(settings)
        return SystemSettingsResponse(settings=saved, checks=self._build_checks(saved), env_checks=self._build_env_checks(saved))

    def check_settings(self, request: SystemSettingsRequest) -> SystemSettingsResponse:
        settings = self._coerce_settings_request(request)
        return SystemSettingsResponse(settings=settings, checks=self._build_checks(settings), env_checks=self._build_env_checks(settings))

    def get_summary(self) -> SystemSummaryResponse:
        settings = load_system_settings()
        paths = get_mitsuba_paths()
        checks = self._build_checks(settings)
        return SystemSummaryResponse(
            project_root=settings.project_root,
            mitsuba_dir=str(paths["mitsuba_dir"]),
            mitsuba_exe=str(paths["mitsuba_exe"]),
            mtsutil_exe=str(paths["mtsutil_exe"]),
            mitsuba_exists=paths["mitsuba_exe"].exists(),
            mtsutil_exists=paths["mtsutil_exe"].exists(),
            available_modules=["render", "analysis", "models", "settings"],
            available_path_keys=sorted(SAFE_PATHS.keys()),
            compile_defaults=self._compile_defaults_from_settings(settings),
            settings=settings,
            checks=checks,
            env_checks=self._build_env_checks(settings),
        )

    def get_task_detail(self, task_id: str, limit: int = 240) -> Optional[TaskDetailResponse]:
        record = task_manager.get(task_id)
        if record is None:
            return None
        logs: list[str] = []
        if record.log_path and Path(record.log_path).exists():
            logs = Path(record.log_path).read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        return TaskDetailResponse(record=record, logs=logs)

    async def stop_task(self, task_id: str) -> bool:
        record = task_manager.get(task_id)
        if record is None:
            return False
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event is not None:
            cancel_event.set()
        process = self._processes.get(task_id)
        if process_is_running(process):
            terminate_process(process)
        await task_manager.update(task_id, status="cancelled", message="Cancellation requested", event="log")
        return True

    async def start_compile(self, request: SystemCompileRequest):
        log_path = LOGS_ROOT / f"mitsuba_compile_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("system_compile", f"{request.compile_label} queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_compile(record.task_id, request, log_path, cancel_event))
        return record

    async def _write_log(
        self,
        task_id: str,
        log_path: Path,
        message: str,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        event: str = "log",
        result_payload: Optional[dict] = None,
    ) -> None:
        clean_message = message.replace("\r", "").replace("\b", "")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(clean_message + "\n")
        log_task_message("system", task_id, clean_message)
        await task_manager.update(
            task_id,
            status=status,
            progress=progress,
            message=clean_message,
            log_path=str(log_path),
            result_payload=result_payload,
            event=event,
        )

    def _resolve_vcvarsall_from_shortcut(self, lnk_path: str) -> str:
        shortcut = Path(lnk_path)
        if not shortcut.exists():
            return ""
        escaped = str(shortcut).replace("'", "''")
        ps_script = (
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{escaped}');"
            "Write-Output $s.TargetPath; Write-Output $s.Arguments"
        )
        try:
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_script],
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
            ).splitlines()
        except Exception:
            return ""
        target = output[0].strip() if output else ""
        args = output[1].strip() if len(output) > 1 else ""
        if target.lower().endswith("vcvarsall.bat") and Path(target).exists():
            return target
        if args:
            match = re.search(r'([A-Za-z]:\\[^"]*vcvarsall\.bat)', args, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if Path(candidate).exists():
                    return candidate
        return ""

    def _auto_detect_vcvarsall(self) -> str:
        installer_roots = [
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("ProgramFiles", ""),
        ]
        vswhere = Path()
        for root in installer_roots:
            if not root:
                continue
            candidate = Path(root) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
            if candidate.exists():
                vswhere = candidate
                break
        if not vswhere:
            raise FileNotFoundError("vswhere.exe not found")

        cmd = [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ]
        vs_path = subprocess.check_output(
            cmd,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
        ).strip()
        if not vs_path:
            raise FileNotFoundError("No Visual Studio installation with VC++ tools was found")
        vcvarsall = Path(vs_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        if not vcvarsall.exists():
            raise FileNotFoundError(f"vcvarsall.bat not found: {vcvarsall}")
        return str(vcvarsall)

    def _resolve_vcvarsall(self, requested_path: str) -> str:
        candidate = requested_path.strip() or DEFAULT_VCVARSALL_PATH
        if candidate.lower().endswith(".lnk"):
            resolved = self._resolve_vcvarsall_from_shortcut(candidate)
            if resolved:
                return resolved
            raise FileNotFoundError("Failed to resolve vcvarsall.bat from shortcut")
        if candidate and Path(candidate).exists():
            return candidate
        return self._auto_detect_vcvarsall()

    async def _run_compile_attempt(
        self,
        task_id: str,
        log_path: Path,
        *,
        vcvarsall: str,
        conda_cmd: str,
        conda_env: str,
        dependency_paths: List[Path],
        work_dir: Path,
        compile_cmd: str,
        cancel_event: asyncio.Event,
    ) -> Tuple[int, List[str]]:
        bat_file = LOGS_ROOT / f"{task_id}_compile.bat"
        exit_code_file = LOGS_ROOT / f"{task_id}_compile_exit_code.txt"
        dependency_prefix = ";".join(str(path) for path in dependency_paths)
        bat_content = f"""@echo off
cd /d "{work_dir}"
setlocal EnableExtensions
echo 99> "{exit_code_file}"
echo [1/4] Setting up Visual Studio environment...
call "{vcvarsall}" x64
echo [1/4] Done (errorlevel %%errorlevel%%)

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
echo [2/4] Done (errorlevel %%errorlevel%%)

echo [3/4] Toolchain Info:
where python || echo python not found
python --version || echo python version failed
where scons || echo scons not found
call scons --version || echo scons version failed
where cl || echo cl not found
echo [3/4] Done (errorlevel %%errorlevel%%)

echo [4/4] Running build command
echo WorkDir: {work_dir}
echo Command: {compile_cmd}
set PATH={dependency_prefix};%PATH%
call {compile_cmd}
set "BUILD_ERROR=%errorlevel%"
echo [4/4] Done (errorlevel %BUILD_ERROR%)
echo %BUILD_ERROR%> "{exit_code_file}"
exit /b %BUILD_ERROR%
"""
        bat_file.write_text(bat_content, encoding="utf-8")
        await self._write_log(task_id, log_path, f"Generated build script: {bat_file}", progress=15)

        output_lines: list[str] = []

        async def handle_output(line: bytes) -> None:
            text = decode_subprocess_output(line).strip()
            if text:
                output_lines.append(text)
                await self._write_log(task_id, log_path, text, progress=55)

        final_exit_code = await run_process_streaming(
            ["cmd", "/c", str(bat_file)],
            cwd=work_dir,
            cancel_event=cancel_event,
            process_store=self._processes,
            process_key=task_id,
            on_output=handle_output,
        )
        if final_exit_code == -1:
            bat_file.unlink(missing_ok=True)
            exit_code_file.unlink(missing_ok=True)
            return -1, output_lines

        if exit_code_file.exists():
            try:
                final_exit_code = int(exit_code_file.read_text(encoding="utf-8", errors="replace").strip())
            except Exception:
                pass
            exit_code_file.unlink(missing_ok=True)
        bat_file.unlink(missing_ok=True)
        await self._write_log(task_id, log_path, f"Build script exit code: {final_exit_code}", progress=80)
        await self._write_log(task_id, log_path, f"Final exit code: {final_exit_code}", progress=82)
        return final_exit_code, output_lines

    async def _run_compile(
        self,
        task_id: str,
        request: SystemCompileRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        settings = load_system_settings()
        base_dir = self._resolve_path(settings.project_root)
        work_dir = self._resolve_path(request.work_dir.strip() or settings.work_dir, base_dir)
        dependency_paths = [self._resolve_path(path_value, base_dir) for path_value in request.dependency_paths] or self._dependency_paths(settings)
        result_payload = {
            "compile_cmd": request.compile_cmd,
            "compile_label": request.compile_label,
            "conda_env": request.conda_env,
            "work_dir": str(work_dir),
            "dependency_paths": [str(path) for path in dependency_paths],
        }
        try:
            await self._write_log(
                task_id,
                log_path,
                f"Compile task created: {request.compile_label}",
                status="running",
                progress=5,
                result_payload=result_payload,
            )
            vcvarsall = self._resolve_vcvarsall(request.vcvarsall_path or settings.vcvarsall_path)
            conda_cmd = os.environ.get("CONDA_EXE") or shutil.which("conda") or "conda"

            await self._write_log(task_id, log_path, f"vcvarsall path: {vcvarsall}", progress=10, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"Compile working directory: {work_dir}", progress=11, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"Compile command: {request.compile_cmd}", progress=12, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"Conda executable: {conda_cmd}", progress=13, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"Dependency paths: {', '.join(str(path) for path in dependency_paths) if dependency_paths else '(none)'}", progress=14, result_payload=result_payload)

            final_exit_code, output_lines = await self._run_compile_attempt(
                task_id,
                log_path,
                vcvarsall=vcvarsall,
                conda_cmd=conda_cmd,
                conda_env=request.conda_env,
                dependency_paths=dependency_paths,
                work_dir=work_dir,
                compile_cmd=request.compile_cmd,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                return
            if final_exit_code != 0 and has_manifest_access_denied(output_lines):
                serial_cmd = build_serial_compile_command(request.compile_cmd)
                if serial_cmd and serial_cmd != request.compile_cmd:
                    await self._write_log(task_id, log_path, "Manifest conflict detected, retrying with serial compile", progress=86)
                    await asyncio.sleep(2)
                    await self._write_log(task_id, log_path, f"Serial retry command: {serial_cmd}", progress=88)
                    final_exit_code, _ = await self._run_compile_attempt(
                        task_id,
                        log_path,
                        vcvarsall=vcvarsall,
                        conda_cmd=conda_cmd,
                        conda_env=request.conda_env,
                        dependency_paths=dependency_paths,
                        work_dir=work_dir,
                        compile_cmd=serial_cmd,
                        cancel_event=cancel_event,
                    )
            record = task_manager.get(task_id)
            if record and record.status == "cancelled":
                return
            if final_exit_code == 0:
                await self._write_log(
                    task_id,
                    log_path,
                    "Compile succeeded",
                    status="success",
                    progress=100,
                    event="done",
                    result_payload={**result_payload, "vcvarsall_path": vcvarsall},
                )
            else:
                await self._write_log(
                    task_id,
                    log_path,
                    "Compile failed",
                    status="failed",
                    progress=100,
                    event="done",
                    result_payload={**result_payload, "vcvarsall_path": vcvarsall},
                )
        except Exception as exc:
            await self._write_log(
                task_id,
                log_path,
                f"Compile exception: {exc}",
                status="failed",
                progress=100,
                event="done",
                result_payload=result_payload,
            )
        finally:
            self._cancel_events.pop(task_id, None)


system_service = SystemService()
