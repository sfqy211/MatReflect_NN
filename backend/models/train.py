from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.models.common import TaskDetailResponse, TaskStatus


TrainProjectVariant = Literal["hyperbrdf", "decoupled"]
TrainDataset = Literal["MERL", "EPFL"]
NeuralTrainEngine = Literal["pytorch", "keras"]


class TrainModelItem(BaseModel):
    key: str
    label: str
    category: str
    supports_training: bool = True
    supports_extract: bool = False
    supports_decode: bool = False
    supports_runs: bool = False
    default_paths: dict[str, str] = Field(default_factory=dict)


class TrainModelsResponse(BaseModel):
    items: list[TrainModelItem] = Field(default_factory=list)


class TrainRunSummary(BaseModel):
    project_variant: TrainProjectVariant
    label: str
    run_name: str
    run_dir: str
    checkpoint_path: str
    dataset: str
    completed_epochs: int = 0
    updated_at: datetime
    has_checkpoint: bool = False
    args: dict[str, Any] = Field(default_factory=dict)


class TrainRunsResponse(BaseModel):
    total: int
    items: list[TrainRunSummary] = Field(default_factory=list)


class NeuralPytorchTrainRequest(BaseModel):
    merl_dir: str
    selected_materials: list[str] = Field(default_factory=list)
    epochs: int = Field(default=100, ge=1, le=100000)
    output_dir: str
    device: Literal["cpu", "cuda"] = "cpu"


class NeuralKerasTrainRequest(BaseModel):
    merl_dir: str
    selected_materials: list[str] = Field(default_factory=list)
    cuda_device: str = "0"
    h5_output_dir: str
    npy_output_dir: str


class HyperTrainRunRequest(BaseModel):
    project_variant: TrainProjectVariant = "hyperbrdf"
    merl_dir: str
    output_dir: str
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    epochs: int = Field(default=100, ge=1, le=100000)
    sparse_samples: int = Field(default=4000, ge=1, le=1000000)
    kl_weight: float = 0.1
    fw_weight: float = 0.1
    lr: float = Field(default=5e-5, gt=0)
    keepon: bool = False
    train_subset: int = Field(default=0, ge=0)
    train_seed: int = Field(default=42, ge=0)
    model_type: Literal["baseline", "decoupled"] = "decoupled"
    sampling_mode: Literal["random", "hybrid"] = "hybrid"
    teacher_dir: str = ""
    analytic_lobes: Literal[1, 2] = 1
    baseline_checkpoint: str = ""
    analytic_loss_weight: float = 0.1
    residual_loss_weight: float = 0.1
    spec_loss_weight: float = 0.2
    gate_reg_weight: float = 0.05
    spec_percentile: float = Field(default=0.9, ge=0.5, le=0.999)
    gate_bias_init: float = -2.0
    stage_a_epochs: int = Field(default=10, ge=0)
    stage_b_ramp_epochs: int = Field(default=20, ge=0)


class HyperExtractRequest(BaseModel):
    project_variant: TrainProjectVariant = "hyperbrdf"
    merl_dir: str
    selected_materials: list[str] = Field(default_factory=list)
    model_path: str
    output_dir: str
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    sparse_samples: int = Field(default=4000, ge=1, le=1000000)


class HyperDecodeRequest(BaseModel):
    project_variant: TrainProjectVariant = "hyperbrdf"
    pt_dir: str
    selected_pts: list[str] = Field(default_factory=list)
    output_dir: str
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    cuda_device: str = "0"


class TrainTaskStartResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TrainTaskStopRequest(BaseModel):
    task_id: str


class TrainTaskDetailResponse(TaskDetailResponse):
    pass
