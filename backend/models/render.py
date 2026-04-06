from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import FileListItem, TaskStatus


RenderMode = Literal["brdfs", "fullbin", "npy"]


class RenderSceneItem(BaseModel):
    label: str
    path: str
    is_default: bool = False


class RenderScenesResponse(BaseModel):
    default_scene: Optional[str] = None
    items: list[RenderSceneItem] = Field(default_factory=list)


class RenderFilesResponse(BaseModel):
    render_mode: RenderMode
    input_dir: str
    total: int
    items: list[FileListItem] = Field(default_factory=list)


class RenderOutputFilesResponse(BaseModel):
    render_mode: RenderMode
    path_key: str
    resolved_path: str
    total: int
    items: list[FileListItem] = Field(default_factory=list)


class RenderBatchRequest(BaseModel):
    render_mode: RenderMode
    scene_path: str
    selected_files: list[str] = Field(default_factory=list)
    integrator_type: str = "bdpt"
    sample_count: int = Field(default=256, ge=1, le=8192)
    auto_convert: bool = True
    skip_existing: bool = False
    custom_cmd: Optional[str] = None


class RenderConvertRequest(BaseModel):
    render_mode: RenderMode
    filenames: list[str] = Field(default_factory=list)


class TaskStartResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStopRequest(BaseModel):
    task_id: str
