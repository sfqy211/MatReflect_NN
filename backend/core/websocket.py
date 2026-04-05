from collections import defaultdict
from typing import DefaultDict

from fastapi import WebSocket


class WebSocketHub:
    def __init__(self) -> None:
        self._connections: DefaultDict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        if task_id not in self._connections:
            return
        self._connections[task_id] = [conn for conn in self._connections[task_id] if conn is not websocket]
        if not self._connections[task_id]:
            del self._connections[task_id]

    async def broadcast(self, task_id: str, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in self._connections.get(task_id, []):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(task_id, websocket)


websocket_hub = WebSocketHub()
