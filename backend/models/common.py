from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "running", "success", "failed", "cancelled"]


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime


class SystemSummaryResponse(BaseModel):
    project_root: str
    mitsuba_dir: str
    mitsuba_exe: str
    mtsutil_exe: str
    mitsuba_exists: bool
    mtsutil_exists: bool
    available_modules: list[str]
    available_path_keys: list[str]


class FileListRequest(BaseModel):
    path_key: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=40, ge=1, le=500)
    suffix: list[str] = Field(default_factory=list)
    search: str = ""


class FileListPathRequest(BaseModel):
    directory: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=40, ge=1, le=500)
    suffix: list[str] = Field(default_factory=list)
    search: str = ""


class FileListItem(BaseModel):
    name: str
    path: str
    size: int
    modified_at: datetime
    is_dir: bool
    preview_url: Optional[str] = None


class FileListResponse(BaseModel):
    path_key: str
    resolved_path: str
    page: int
    page_size: int
    total: int
    items: list[FileListItem]


class TaskRecord(BaseModel):
    task_id: str
    task_type: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: TaskStatus = "pending"
    progress: int = 0
    message: str = ""
    log_path: Optional[str] = None
    result_payload: dict[str, Any] = Field(default_factory=dict)


class TaskDetailResponse(BaseModel):
    record: TaskRecord
    logs: list[str] = Field(default_factory=list)


class TaskEvent(BaseModel):
    task_id: str
    event: Literal["snapshot", "log", "done"]
    status: TaskStatus
    progress: int
    message: str = ""
    result_payload: dict[str, Any] = Field(default_factory=dict)


class TaskStartResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStopRequest(BaseModel):
    task_id: str
