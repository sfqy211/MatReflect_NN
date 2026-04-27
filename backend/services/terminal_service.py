"""PTY 终端服务：管理终端会话，支持 Windows conpty。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any


class PtySession:
    """单个 PTY 会话。"""

    def __init__(self, session_id: str, working_dir: str = "", conda_env: str = "") -> None:
        self.session_id = session_id
        self.working_dir = working_dir
        self.conda_env = conda_env
        self.process: Any = None
        self.output_queue: asyncio.Queue[str] = asyncio.Queue()
        self._active = False

    async def start(self) -> None:
        """启动 PTY 进程。"""
        try:
            from pywinpty import PTY  # type: ignore
        except ImportError:
            # Fallback: 使用 subprocess 模拟
            self._active = True
            await self.output_queue.put(f"[终端] pywinpty 未安装，使用简化模式\r\n")
            if self.conda_env:
                await self.output_queue.put(f"[终端] Conda 环境: {self.conda_env}\r\n")
            if self.working_dir:
                await self.output_queue.put(f"[终端] 工作目录: {self.working_dir}\r\n")
            await self.output_queue.put(f"[终端] 会话 {self.session_id} 已就绪\r\n")
            return

        try:
            self.process = PTY(80, 24)
            if self.working_dir:
                self.process.set_cwd(self.working_dir)
            self._active = True

            # 读取输出的后台任务
            asyncio.create_task(self._read_output())
        except Exception as exc:
            await self.output_queue.put(f"[终端错误] {exc}\r\n")

    async def _read_output(self) -> None:
        """从 PTY 读取输出并放入队列。"""
        if not self.process:
            return
        try:
            while self._active:
                # pywinpty 的 read 是同步的，需要用 run_in_executor
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.read, 4096
                )
                if data:
                    await self.output_queue.put(data)
                else:
                    await asyncio.sleep(0.01)
        except Exception:
            self._active = False

    async def write(self, data: str) -> None:
        """向 PTY 写入数据。"""
        if self.process:
            try:
                self.process.write(data)
            except Exception:
                pass
        else:
            # 简化模式：直接放入输出队列模拟回显
            await self.output_queue.put(data)

    async def read_output(self) -> str | None:
        """非阻塞读取输出。"""
        try:
            return self.output_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def close(self) -> None:
        """关闭 PTY 会话。"""
        self._active = False
        if self.process:
            try:
                self.process.close()
            except Exception:
                pass


class TerminalService:
    """PTY 终端会话管理器。"""

    def __init__(self) -> None:
        self.sessions: dict[str, PtySession] = {}

    def create_session(self, working_dir: str = "", conda_env: str = "") -> PtySession:
        """创建新的终端会话。"""
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
