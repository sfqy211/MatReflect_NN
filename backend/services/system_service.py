from __future__ import annotations

import asyncio
import locale
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from backend.core.config import LOGS_ROOT, PROJECT_ROOT
from backend.core.paths import SAFE_PATHS, get_mitsuba_paths
from backend.models.common import TaskDetailResponse
from backend.models.system import SystemCompileDefaults, SystemCompileRequest, SystemSummaryResponse
from backend.services.task_manager import task_manager


DEFAULT_VCVARSALL_PATH = r"C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\VC\Auxiliary\Build\vcvarsall.bat"


def decode_subprocess_output(raw: bytes | str | None) -> str:
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


def build_serial_compile_command(compile_cmd: str) -> str | None:
    if not compile_cmd or "scons" not in compile_cmd.lower():
        return None
    serial_cmd = re.sub(r"(?i)(^|\s)-j\s*\d+", r"\1-j1", compile_cmd)
    serial_cmd = re.sub(r"(?i)(^|\s)--jobs(?:=|\s*)\d+", r"\1--jobs=1", serial_cmd)
    if serial_cmd == compile_cmd:
        serial_cmd = f"{compile_cmd} -j1"
    return serial_cmd


def has_manifest_access_denied(log_lines: list[str]) -> bool:
    joined = "\n".join(log_lines).lower()
    patterns = [
        "mt.exe : general error c101008d",
        "failed to write the updated manifest",
        "error 31",
        "拒绝访问",
        "access is denied",
    ]
    return any(pattern in joined for pattern in patterns)


class SystemService:
    def __init__(self) -> None:
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def _compile_work_dir(self) -> Path:
        mitsuba_root = PROJECT_ROOT / "mitsuba"
        if (mitsuba_root / "SConstruct").exists():
            return mitsuba_root
        return PROJECT_ROOT

    def get_compile_defaults(self) -> SystemCompileDefaults:
        work_dir = self._compile_work_dir()
        return SystemCompileDefaults(
            preset_label="默认 SCons 并行编译",
            compile_cmd="scons --parallelize",
            conda_env="mitsuba-build",
            vcvarsall_path=DEFAULT_VCVARSALL_PATH,
            work_dir=str(work_dir.resolve()),
            dep_bin=str((work_dir / "dependencies" / "bin").resolve()),
            dep_lib=str((work_dir / "dependencies" / "lib").resolve()),
        )

    def get_summary(self) -> SystemSummaryResponse:
        paths = get_mitsuba_paths()
        return SystemSummaryResponse(
            project_root=str(PROJECT_ROOT.resolve()),
            mitsuba_dir=str(paths["mitsuba_dir"]),
            mitsuba_exe=str(paths["mitsuba_exe"]),
            mtsutil_exe=str(paths["mtsutil_exe"]),
            mitsuba_exists=paths["mitsuba_exe"].exists(),
            mtsutil_exists=paths["mtsutil_exe"].exists(),
            available_modules=["render", "analysis", "models", "settings"],
            available_path_keys=sorted(SAFE_PATHS.keys()),
            compile_defaults=self.get_compile_defaults(),
        )

    def get_task_detail(self, task_id: str, limit: int = 240) -> TaskDetailResponse | None:
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
        if process and process.returncode is None:
            process.terminate()
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
        status: str | None = None,
        progress: int | None = None,
        event: str = "log",
        result_payload: dict | None = None,
    ) -> None:
        clean_message = message.replace("\r", "").replace("\b", "")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(clean_message + "\n")
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
        vswhere = Path(os.path.expandvars(r"${ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"))
        if not vswhere.exists():
            vswhere = Path(os.path.expandvars(r"${ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe"))
        if not vswhere.exists():
            raise FileNotFoundError("未找到 vswhere.exe")
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
            raise FileNotFoundError("未找到安装了 VC++ 工具集的 Visual Studio")
        vcvarsall = Path(vs_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        if not vcvarsall.exists():
            raise FileNotFoundError(f"未找到 vcvarsall.bat: {vcvarsall}")
        return str(vcvarsall)

    def _resolve_vcvarsall(self, requested_path: str) -> str:
        candidate = requested_path.strip() or DEFAULT_VCVARSALL_PATH
        if candidate.lower().endswith(".lnk"):
            resolved = self._resolve_vcvarsall_from_shortcut(candidate)
            if resolved:
                return resolved
            raise FileNotFoundError("无法从快捷方式解析 vcvarsall.bat，请检查链接目标")
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
        dep_bin: Path,
        dep_lib: Path,
        work_dir: Path,
        compile_cmd: str,
        cancel_event: asyncio.Event,
    ) -> tuple[int, list[str]]:
        bat_file = LOGS_ROOT / f"{task_id}_compile.bat"
        exit_code_file = LOGS_ROOT / f"{task_id}_compile_exit_code.txt"
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
set PATH={dep_bin};{dep_lib};%PATH%
call {compile_cmd}
set "BUILD_ERROR=%errorlevel%"
echo [4/4] Done (errorlevel %BUILD_ERROR%)
echo %BUILD_ERROR%> "{exit_code_file}"
exit /b %BUILD_ERROR%
"""
        bat_file.write_text(bat_content, encoding="utf-8")
        await self._write_log(task_id, log_path, f"生成构建脚本: {bat_file}", progress=15)

        output_lines: list[str] = []
        process = await asyncio.create_subprocess_exec(
            "cmd",
            "/c",
            str(bat_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(work_dir),
        )
        self._processes[task_id] = process
        try:
            while True:
                if cancel_event.is_set():
                    if process.returncode is None:
                        process.terminate()
                        await process.wait()
                    return -1, output_lines
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.5) if process.stdout else b""
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        break
                    continue
                if not line:
                    if process.returncode is None:
                        await asyncio.sleep(0.1)
                        continue
                    break
                text = decode_subprocess_output(line).strip()
                if text:
                    output_lines.append(text)
                    await self._write_log(task_id, log_path, text, progress=55)
            final_exit_code = await process.wait()
        finally:
            self._processes.pop(task_id, None)

        if exit_code_file.exists():
            try:
                final_exit_code = int(exit_code_file.read_text(encoding="utf-8", errors="replace").strip())
            except Exception:
                pass
            exit_code_file.unlink(missing_ok=True)
        bat_file.unlink(missing_ok=True)
        await self._write_log(task_id, log_path, f"构建脚本退出码: {process.returncode}", progress=80)
        await self._write_log(task_id, log_path, f"最终退出码: {final_exit_code}", progress=82)
        return final_exit_code, output_lines

    async def _run_compile(
        self,
        task_id: str,
        request: SystemCompileRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        defaults = self.get_compile_defaults()
        result_payload = {
            "compile_cmd": request.compile_cmd,
            "compile_label": request.compile_label,
            "conda_env": request.conda_env,
            "work_dir": defaults.work_dir,
        }
        try:
            await self._write_log(
                task_id,
                log_path,
                f"编译任务已创建: {request.compile_label}",
                status="running",
                progress=5,
                result_payload=result_payload,
            )
            vcvarsall = self._resolve_vcvarsall(request.vcvarsall_path)
            work_dir = Path(defaults.work_dir)
            dep_bin = Path(defaults.dep_bin)
            dep_lib = Path(defaults.dep_lib)
            conda_cmd = os.environ.get("CONDA_EXE") or shutil.which("conda") or "conda"

            await self._write_log(task_id, log_path, f"vcvarsall 路径: {vcvarsall}", progress=10, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"编译工作目录: {work_dir}", progress=11, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"编译命令: {request.compile_cmd}", progress=12, result_payload=result_payload)
            await self._write_log(task_id, log_path, f"Conda 运行器: {conda_cmd}", progress=13, result_payload=result_payload)
            await self._write_log(task_id, log_path, "开始执行编译", progress=14, result_payload=result_payload)

            final_exit_code, output_lines = await self._run_compile_attempt(
                task_id,
                log_path,
                vcvarsall=vcvarsall,
                conda_cmd=conda_cmd,
                conda_env=request.conda_env,
                dep_bin=dep_bin,
                dep_lib=dep_lib,
                work_dir=work_dir,
                compile_cmd=request.compile_cmd,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                return
            if final_exit_code != 0 and has_manifest_access_denied(output_lines):
                serial_cmd = build_serial_compile_command(request.compile_cmd)
                if serial_cmd and serial_cmd != request.compile_cmd:
                    await self._write_log(task_id, log_path, "检测到 mt.exe manifest 写入冲突，2 秒后使用串行增量补编译", progress=86)
                    await asyncio.sleep(2)
                    await self._write_log(task_id, log_path, f"串行补编译命令: {serial_cmd}", progress=88)
                    final_exit_code, _ = await self._run_compile_attempt(
                        task_id,
                        log_path,
                        vcvarsall=vcvarsall,
                        conda_cmd=conda_cmd,
                        conda_env=request.conda_env,
                        dep_bin=dep_bin,
                        dep_lib=dep_lib,
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
                    "编译成功",
                    status="success",
                    progress=100,
                    event="done",
                    result_payload={**result_payload, "vcvarsall_path": vcvarsall},
                )
            else:
                await self._write_log(
                    task_id,
                    log_path,
                    "编译失败",
                    status="failed",
                    progress=100,
                    event="done",
                    result_payload={**result_payload, "vcvarsall_path": vcvarsall},
                )
        except Exception as exc:
            await self._write_log(
                task_id,
                log_path,
                f"编译异常: {exc}",
                status="failed",
                progress=100,
                event="done",
                result_payload=result_payload,
            )
        finally:
            self._cancel_events.pop(task_id, None)


system_service = SystemService()
