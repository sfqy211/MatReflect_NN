"""终端服务：subprocess 交互终端。"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


def _find_conda() -> str | None:
    """查找 conda.bat 路径。"""
    candidates = [
        os.environ.get("CONDA_EXE", ""),
        shutil.which("conda") or "",
        shutil.which("conda.bat") or "",
    ]
    home = Path.home()
    for root_name in ("miniconda3", "anaconda3", "miniforge3", "mambaforge"):
        candidates.append(str(home / root_name / "condabin" / "conda.bat"))
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def _build_shell_cmd(conda_env: str = "") -> tuple[list[str], bool]:
    """构建 shell 启动命令。返回 (cmd_list, use_shell)。"""
    shell_cmd = os.environ.get("COMSPEC", "cmd.exe")
    if not conda_env:
        return [shell_cmd], False

    conda = _find_conda()
    if conda:
        # conda run 比 cmd /K "conda activate" 更可靠
        return [conda, "run", "--no-capture-output", "-n", conda_env, shell_cmd], True

    # 回退：尝试 conda activate（依赖 conda init hook）
    return [shell_cmd, "/K", f"conda activate {conda_env}"], False


class PtySession:
    """单个终端会话。"""

    def __init__(self, session_id: str, working_dir: str = "", conda_env: str = "") -> None:
        self.session_id = session_id
        self.working_dir = working_dir
        self.conda_env = conda_env
        self.process: subprocess.Popen | None = None
        self.output_queue: asyncio.Queue[str] = asyncio.Queue()
        self._active = False
        self._connected = False  # 是否有 WebSocket 连接

    async def start(self) -> None:
        """启动终端进程。"""
        self._active = True

        # 校验工作目录
        cwd = self.working_dir or None
        if cwd and not Path(cwd).is_dir():
            await self.output_queue.put(f"[终端错误] 工作目录不存在: {cwd}\r\n")
            self._active = False
            return

        cmd, use_shell = _build_shell_cmd(self.conda_env)

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                bufsize=0,
                shell=use_shell,
            )
            asyncio.create_task(self._read_output())

            if self.conda_env:
                await self.output_queue.put(f"[终端] Conda 环境: {self.conda_env}\r\n")
            await self.output_queue.put(f"[终端] 会话 {self.session_id} 已就绪\r\n")
        except Exception as exc:
            await self.output_queue.put(f"[终端错误] 启动失败: {exc}\r\n")
            self._active = False

    async def _read_output(self) -> None:
        """从进程 stdout 持续读取输出（块读取）。"""
        if not self.process or not self.process.stdout:
            return
        loop = asyncio.get_event_loop()
        try:
            while self._active:
                data = await loop.run_in_executor(
                    None, self.process.stdout.read, 4096
                )
                if not data:
                    if self.process.poll() is not None:
                        await self.output_queue.put(
                            f"\r\n[终端] 进程已退出 (code {self.process.returncode})\r\n"
                        )
                        self._active = False
                        break
                    continue
                await self.output_queue.put(data.decode("utf-8", errors="replace"))
        except Exception:
            self._active = False

    async def write(self, data: str) -> None:
        """向进程 stdin 写入数据。"""
        if not self.process or not self.process.stdin:
            return
        if self.process.poll() is not None:
            return

        # Normalize line endings: cmd.exe needs \r\n to process a command.
        to_send = data.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_stdin, to_send.encode("utf-8"))
        except Exception as exc:
            await self.output_queue.put(f"\r\n[终端] 写入失败: {exc}\r\n")

    def _write_stdin(self, data: bytes) -> None:
        if not self.process or not self.process.stdin:
            return
        self.process.stdin.write(data)
        self.process.stdin.flush()

    async def read_output(self) -> str | None:
        """非阻塞读取输出。"""
        try:
            return self.output_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def close(self) -> None:
        """关闭终端会话及其子进程树。"""
        self._active = False
        if not self.process:
            return
        try:
            if sys.platform == "win32":
                # Windows: terminate 不会杀子进程，用 taskkill /T 杀进程树
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                self.process.terminate()
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass


class TerminalService:
    """终端会话管理器。"""

    def __init__(self) -> None:
        self.sessions: dict[str, PtySession] = {}

    def create_session(self, working_dir: str = "", conda_env: str = "") -> PtySession:
        session_id = str(uuid.uuid4())[:8]
        session = PtySession(session_id, working_dir, conda_env)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> PtySession | None:
        return self.sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        session = self.sessions.pop(session_id, None)
        if session:
            session.close()


terminal_service = TerminalService()
