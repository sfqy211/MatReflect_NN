from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import FileListItem, TaskStatus
from backend.models.train import TrainDataset


RenderMode = Literal["brdfs", "fullbin", "npy"]
RenderReconstructModel = Literal["neural", "hyperbrdf", "decoupled"]


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


class RenderReconstructRequest(BaseModel):
    model_key: RenderReconstructModel
    checkpoint_path: str = ""
    merl_dir: str
    output_dir: str = ""
    selected_materials: list[str] = Field(default_factory=list)
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    sparse_samples: int = Field(default=4000, ge=1, le=1_000_000)
    cuda_device: str = "0"
    neural_device: Literal["cpu", "cuda"] = "cpu"
    neural_epochs: int = Field(default=100, ge=1, le=100000)
    scene_path: str = ""
    integrator_type: str = "bdpt"
    sample_count: int = Field(default=256, ge=1, le=8192)
    auto_convert: bool = True
    skip_existing: bool = False
    custom_cmd: Optional[str] = None
    render_after_reconstruct: bool = False


class TaskStartResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStopRequest(BaseModel):
    task_id: str
