"""PTY WebSocket 端点。"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from backend.services.terminal_service import terminal_service


router = APIRouter(tags=["terminal"])

# 断连后保留会话的秒数（允许浏览器刷新/网络抖动后重连）
SESSION_TTL = 30


@router.websocket("/ws/pty/{session_id}")
async def pty_websocket(
    websocket: WebSocket,
    session_id: str,
    conda_env: str = Query(default=""),
    working_dir: str = Query(default=""),
) -> None:
    await websocket.accept()

    session = terminal_service.get_session(session_id)
    if not session:
        session = terminal_service.create_session(
            working_dir=working_dir,
            conda_env=conda_env,
        )
        await session.start()

    # 标记已连接（取消待销毁的 TTL 任务由 _delayed_close 自然处理）
    session._connected = True

    output_task: asyncio.Task | None = None
    try:
        await websocket.send_text(json.dumps({"type": "ready", "session_id": session.session_id}))

        async def send_output() -> None:
            try:
                while session._active:
                    data = await session.read_output()
                    if data:
                        await websocket.send_text(json.dumps({"type": "output", "data": data}))
                    await asyncio.sleep(0.01)
            except (WebSocketDisconnect, Exception):
                pass
        output_task = asyncio.create_task(send_output())

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "input":
                    await session.write(msg.get("data", ""))
                elif msg.get("type") == "resize":
                    pass
            except json.JSONDecodeError:
                await session.write(raw)
    except WebSocketDisconnect:
        pass
    finally:
        session._connected = False
        if output_task is not None:
            output_task.cancel()
            try:
                await output_task
            except asyncio.CancelledError:
                pass
        # 断连后延迟销毁会话，允许前端重连
        asyncio.create_task(_delayed_close(session.session_id, SESSION_TTL))


async def _delayed_close(session_id: str, ttl: int) -> None:
    """延迟关闭会话：若 TTL 内无重连则销毁。"""
    await asyncio.sleep(ttl)
    session = terminal_service.get_session(session_id)
    if not session:
        return
    # 仅当仍无 WebSocket 连接时才销毁
    if not session._connected:
        terminal_service.close_session(session_id)
