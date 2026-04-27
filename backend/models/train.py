from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import TaskDetailResponse, TaskStatus


TrainModelKey = str
TrainProjectVariant = str
TrainDataset = Literal["MERL", "EPFL"]
NeuralTrainEngine = Literal["pytorch", "keras"]
TrainModelCategory = Literal["neural", "hyper", "custom"]
TrainModelAdapter = Literal["neural-pytorch", "neural-keras", "hyper-family", "custom-cli"]


class ModelParameter(BaseModel):
    key: str
    label: str
    type: Literal["int", "float", "str", "bool", "select"] = "str"
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    options: Optional[List[str]] = None


class TrainModelItem(BaseModel):
    key: str
    label: str
    category: TrainModelCategory
    adapter: TrainModelAdapter
    built_in: bool = False
    description: str = ""
    supports_training: bool = True
    supports_extract: bool = False
    supports_decode: bool = False
    supports_runs: bool = False
    supports_reconstruction: bool = False
    model_dir: str = ""
    requirements_path: str = ""
    commands_doc: str = ""
    parameters: List[ModelParameter] = Field(default_factory=list)
    render_modes: List[str] = Field(default_factory=list)
    default_paths: Dict[str, str] = Field(default_factory=dict)
    runtime: Dict[str, str] = Field(default_factory=dict)
    adapter_options: Dict[str, Any] = Field(default_factory=dict)


class TrainModelsResponse(BaseModel):
    items: List[TrainModelItem] = Field(default_factory=list)


class TrainRunSummary(BaseModel):
    model_key: TrainModelKey
    label: str
    adapter: TrainModelAdapter
    run_name: str
    run_dir: str
    checkpoint_path: str
    dataset: str
    completed_epochs: int = 0
    updated_at: datetime
    has_checkpoint: bool = False
    args: Dict[str, Any] = Field(default_factory=dict)


class TrainRunsResponse(BaseModel):
    total: int
    items: List[TrainRunSummary] = Field(default_factory=list)


class NeuralPytorchTrainRequest(BaseModel):
    model_key: TrainModelKey = "neural-pytorch"
    merl_dir: str
    selected_materials: List[str] = Field(default_factory=list)
    epochs: int = Field(default=100, ge=1, le=100000)
    output_dir: str
    device: Literal["cpu", "cuda"] = "cpu"


class NeuralKerasTrainRequest(BaseModel):
    model_key: TrainModelKey = "neural-keras"
    merl_dir: str
    selected_materials: List[str] = Field(default_factory=list)
    cuda_device: str = "0"
    h5_output_dir: str
    npy_output_dir: str


class NeuralH5ConvertRequest(BaseModel):
    model_key: TrainModelKey = "neural-keras"
    h5_dir: str
    selected_h5_files: List[str] = Field(default_factory=list)
    npy_output_dir: str
    conda_env: str = ""


class HyperTrainRunRequest(BaseModel):
    model_key: TrainModelKey = "hyperbrdf"
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


class HyperExtractRequest(BaseModel):
    model_key: TrainModelKey = "hyperbrdf"
    merl_dir: str
    selected_materials: List[str] = Field(default_factory=list)
    model_path: str
    output_dir: str
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    sparse_samples: int = Field(default=4000, ge=1, le=1000000)


class HyperDecodeRequest(BaseModel):
    model_key: TrainModelKey = "hyperbrdf"
    pt_dir: str
    selected_pts: List[str] = Field(default_factory=list)
    output_dir: str
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    cuda_device: str = "0"


class ReconstructRequest(BaseModel):
    model_key: str
    checkpoint_path: str = ""
    merl_dir: str
    output_dir: str = ""
    selected_materials: List[str] = Field(default_factory=list)
    conda_env: str = ""
    dataset: TrainDataset = "MERL"
    sparse_samples: int = Field(default=4000, ge=1, le=1000000)
    cuda_device: str = "0"
    neural_device: Literal["cpu", "cuda"] = "cpu"
    neural_epochs: int = 100
    scene_path: str = ""
    integrator_type: str = "bdpt"
    sample_count: int = 256
    auto_convert: bool = True
    skip_existing: bool = False
    custom_cmd: Optional[str] = None
    render_after_reconstruct: bool = False


class TrainTaskStartResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TrainTaskStopRequest(BaseModel):
    task_id: str


class TrainTaskDetailResponse(TaskDetailResponse):
    pass
