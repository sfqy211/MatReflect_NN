from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import TaskDetailResponse, TaskStatus


TrainModelKey = str
TrainProjectVariant = str
TrainDataset = Literal["MERL", "EPFL"]
NeuralTrainEngine = Literal["pytorch", "keras"]
TrainModelCategory = Literal["neural", "hyper", "custom"]
TrainModelAdapter = Literal["neural-pytorch", "neural-keras", "hyper-family", "hypersnbrdf", "custom-cli"]


class ModelParameter(BaseModel):
    key: str
    label: str
    type: Literal["int", "float", "str", "bool", "select"] = "str"
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    options: Optional[List[str]] = None


# ─── operations-driven 新 schema ──────────────────────────────────────────────

class OperationArgDef(BaseModel):
    """命令行参数定义。
    
    - flag 非空时作为 CLI flag 前缀（如 --outpath），空时作为位置参数。
    - source 指定变量路径：request.xxx / runtime.xxx / default_paths.xxx / item / item.stem / item.path
    - condition_source 指定一个布尔变量名，仅当其值为真时才添加此参数（用于 --keepon 类 flag）。
    - default 在 source 值为空时使用。
    - raw_value 完全不经过变量解析，直接使用。
    """
    flag: str = ""
    source: str = ""
    default: Any = None
    condition_source: str = ""
    raw_value: str = ""


class PostActionDef(BaseModel):
    """操作后处理定义（如 neural-keras 训练后归档 h5/json/lossplot）。"""
    type: str = ""                    # "move_files"
    description: str = ""
    patterns: list[str] = []          # ["*.h5", "*.json", "lossplot_*.png"]
    source_dir_source: str = ""       # "cwd" → 使用命令的工作目录
    dest_dir_source: str = ""         # 目标目录变量，如 "request.h5_output_dir"


class OperationDef(BaseModel):
    """操作定义（来自 model_registry.json 的 operations 字段）。
    
    支持单步和多步两种模式：
    - 单步：直接使用 script + args + loop_source 等字段。
    - 多步：设置 sub_operations = ["extract", "decode"]，steps 留空。
    """
    label: str = ""
    description: str = ""
    # 单步字段
    script: str = ""
    args: list[OperationArgDef] = Field(default_factory=list)
    working_dir: str = ""
    conda_env: str = ""                 # 可选：覆盖 model.runtime.conda_env
    loop_source: str = ""               # "request.selected_materials"
    loop_var: str = "item"
    merge_inputs: bool = False          # 循环模式下合并所有项为位置参数
    input_dir_source: str = ""          # "request.merl_dir" / "request.h5_dir" / "request.pt_dir"
    cuda_visible_source: str = ""       # "request.cuda_device"
    post_actions: list[PostActionDef] = Field(default_factory=list)
    output_transform_type: str = ""     # "selected_materials_to_pt"
    # 多步字段
    sub_operations: list[str] = Field(default_factory=list)


class GenericOperationRequest(BaseModel):
    """通用操作执行请求。
    
    所有字段均为必填/显式 — 前端必须提供 model_key、operation、params。
    """
    model_key: str
    operation: str
    params: Dict[str, Any]


class GenericOperationResponse(BaseModel):
    task_id: str
    status: TaskStatus


class PreviewCommandRequest(BaseModel):
    """预览命令请求。
    
    model_key / operation / params 均为必填。
    item 可选：指定单条循环项名称进行预览。
    """
    model_key: str
    operation: str
    params: Dict[str, Any]
    item: Optional[str] = None


class PreviewCommandItem(BaseModel):
    """单条预览命令描述。"""
    step_index: int
    step_label: str = ""
    command: list[str] = Field(default_factory=list)
    cwd: str = ""
    conda_env: str = ""


class PreviewCommandResponse(BaseModel):
    """预览响应。
    
    - commands：渲染后的命令列表（含循环展开）
    - has_loop：是否存在循环项（前端可用此判断是否需要确认对话框）
    - model_key / operation：回显请求来源
    """
    model_key: str
    operation: str
    commands: list[PreviewCommandItem]
    total_commands: int
    has_loop: bool


# ─── 原有 schema（保留兼容） ──────────────────────────────────────────────────

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
    # 新增 operations 字段（可选，旧模型/旧 config 兼容）
    operations: Dict[str, OperationDef] = Field(default_factory=dict)


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
