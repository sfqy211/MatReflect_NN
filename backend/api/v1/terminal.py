"""PTY WebSocket 端点。"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.terminal_service import terminal_service


router = APIRouter(tags=["terminal"])


@router.websocket("/ws/pty/{session_id}")
async def pty_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    session = terminal_service.get_session(session_id)
    if not session:
        # Auto-create session
        session = terminal_service.create_session()
        await session.start()

    try:
        # Send initial prompt
        await websocket.send_text(json.dumps({"type": "ready", "session_id": session.session_id}))

        # Read loop (output from PTY → WebSocket)
        async def send_output() -> None:
            while session._active:
                data = await session.read_output()
                if data:
                    await websocket.send_text(json.dumps({"type": "output", "data": data}))
                await asyncio.sleep(0.01)
        output_task = asyncio.create_task(send_output())

        # Write loop (WebSocket → PTY)
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "input":
                    await session.write(msg.get("data", ""))
                elif msg.get("type") == "resize":
                    # Future: handle terminal resize
                    pass
            except json.JSONDecodeError:
                # Plain text input
                await session.write(raw)
    except WebSocketDisconnect:
        pass
    finally:
        output_task.cancel()
        terminal_service.close_session(session.session_id)
