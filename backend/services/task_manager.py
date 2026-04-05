import asyncio
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from backend.core.config import TASKS_ROOT
from backend.core.websocket import websocket_hub
from backend.models.common import TaskEvent, TaskRecord


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._load_existing()

    def _task_file(self, task_id: str) -> Path:
        return TASKS_ROOT / f"{task_id}.json"

    def _load_existing(self) -> None:
        for task_file in TASKS_ROOT.glob("*.json"):
            try:
                payload = json.loads(task_file.read_text(encoding="utf-8"))
                record = TaskRecord.model_validate(payload)
                self._tasks[record.task_id] = record
            except Exception:
                continue

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def create(self, task_type: str, message: str = "", log_path: str | None = None) -> TaskRecord:
        task_id = f"{task_type}_{uuid4().hex[:8]}"
        record = TaskRecord(
            task_id=task_id,
            task_type=task_type,
            created_at=datetime.now(),
            status="pending",
            progress=0,
            message=message,
            log_path=log_path,
        )
        self._tasks[task_id] = record
        self._save(record)
        return record

    def _save(self, record: TaskRecord) -> None:
        self._task_file(record.task_id).write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

    async def emit_snapshot(self, task_id: str) -> None:
        record = self._tasks.get(task_id)
        if not record:
            return
        await websocket_hub.broadcast(
            task_id,
            TaskEvent(
                task_id=task_id,
                event="snapshot",
                status=record.status,
                progress=record.progress,
                message=record.message,
                result_payload=record.result_payload,
            ).model_dump(),
        )

    async def update(
        self,
        task_id: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        message: str | None = None,
        log_path: str | None = None,
        result_payload: dict | None = None,
        event: str = "log",
    ) -> TaskRecord | None:
        record = self._tasks.get(task_id)
        if not record:
            return None
        if status is not None:
            record.status = status
            if status == "running" and record.started_at is None:
                record.started_at = datetime.now()
            if status in {"success", "failed", "cancelled"}:
                record.finished_at = datetime.now()
        if progress is not None:
            record.progress = progress
        if message is not None:
            record.message = message
        if log_path is not None:
            record.log_path = log_path
        if result_payload is not None:
            record.result_payload = result_payload
        self._save(record)
        await websocket_hub.broadcast(
            task_id,
            TaskEvent(
                task_id=task_id,
                event=event,  # type: ignore[arg-type]
                status=record.status,
                progress=record.progress,
                message=record.message,
                result_payload=record.result_payload,
            ).model_dump(),
        )
        return record

    async def start_demo_task(self) -> TaskRecord:
        record = self.create("demo", "Demo task created")
        asyncio.create_task(self._run_demo(record.task_id))
        return record

    async def _run_demo(self, task_id: str) -> None:
        await self.update(task_id, status="running", progress=0, message="Starting demo task")
        steps = [
            (15, "Scanning workspace"),
            (35, "Loading data directories"),
            (60, "Preparing task streams"),
            (85, "Finalizing snapshot"),
            (100, "Demo task completed"),
        ]
        for progress, message in steps:
            await asyncio.sleep(0.6)
            event = "done" if progress == 100 else "log"
            status = "success" if progress == 100 else "running"
            await self.update(task_id, status=status, progress=progress, message=message, event=event)


task_manager = TaskManager()
