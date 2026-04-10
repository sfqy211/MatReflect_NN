import mimetypes

import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.api.v1 import analysis, fs, render, system, train
from backend.core.config import (
    API_PREFIX,
    MEDIA_OUTPUTS_PREFIX,
    OUTPUTS_ROOT,
    PROJECT_ROOT,
)
from backend.core.runtime_logging import configure_runtime_logging, log_runtime
from backend.core.websocket import websocket_hub
from backend.services.task_manager import task_manager
from backend.services.metrics_service import metrics_service


# Windows may inherit an incorrect .js MIME type from the registry, which breaks
# module script execution in WebView2 and production browsers.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("application/wasm", ".wasm")
configure_runtime_logging()

app = FastAPI(title="MatReflect_NN Backend", version="0.1.0")
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix=API_PREFIX)
app.include_router(fs.router, prefix=API_PREFIX)
app.include_router(render.router, prefix=API_PREFIX)
app.include_router(train.router, prefix=API_PREFIX)
app.include_router(analysis.router, prefix=API_PREFIX)
app.mount(
    MEDIA_OUTPUTS_PREFIX, StaticFiles(directory=OUTPUTS_ROOT), name="media-outputs"
)


@app.on_event("startup")
async def startup_event():
    log_runtime(f"Backend startup. Project root: {PROJECT_ROOT}")
    metrics_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    log_runtime("Backend shutdown.")
    metrics_service.stop()

@app.websocket("/ws/system/metrics")
async def metrics_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = metrics_service.subscribe()
    try:
        while True:
            data = await queue.get()
            await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        pass
    finally:
        metrics_service.unsubscribe(queue)

@app.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str) -> None:
    await websocket_hub.connect(task_id, websocket)
    try:
        await task_manager.emit_snapshot(task_id)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_hub.disconnect(task_id, websocket)


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    async def frontend_placeholder() -> PlainTextResponse:
        return PlainTextResponse(
            "V2 frontend build not found. Run `cd frontend && npm run build` for production mode, "
            "or start the Vite dev server for development mode."
        )
