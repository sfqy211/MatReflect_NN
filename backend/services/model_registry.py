from __future__ import annotations

import json
import re
from pathlib import Path

from backend.core.config import PROJECT_ROOT
from backend.models.train import TrainModelCreateRequest, TrainModelItem


MODEL_REGISTRY_PATH = PROJECT_ROOT / "backend" / "config" / "model_registry.json"
MODEL_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def _builtin_models() -> list[TrainModelItem]:
    return [
        TrainModelItem(
            key="neural-pytorch",
            label="Neural-BRDF / PyTorch",
            category="neural",
            adapter="neural-pytorch",
            built_in=True,
            description="Neural-BRDF PyTorch 训练入口，输出 Mitsuba 可用的 .npy 权重。",
            supports_training=True,
            supports_extract=False,
            supports_decode=False,
            supports_runs=False,
            default_paths={
                "materials_dir": "data/inputs/binary",
                "output_dir": "data/inputs/npy",
            },
            runtime={
                "conda_env": "nbrdf-train",
                "working_dir": "Neural-BRDF/binary_to_nbrdf",
                "train_script": "Neural-BRDF/binary_to_nbrdf/pytorch_code/train_NBRDF_pytorch.py",
            },
        ),
        TrainModelItem(
            key="neural-keras",
            label="Neural-BRDF / Keras",
            category="neural",
            adapter="neural-keras",
            built_in=True,
            description="Neural-BRDF Keras 训练入口，先输出 .h5/.json，再转换为 .npy。",
            supports_training=True,
            supports_extract=False,
            supports_decode=False,
            supports_runs=False,
            default_paths={
                "materials_dir": "data/inputs/binary",
                "h5_output_dir": "Neural-BRDF/data/merl_nbrdf",
                "npy_output_dir": "data/inputs/npy",
            },
            runtime={
                "conda_env": "nbrdf-train",
                "working_dir": "Neural-BRDF/binary_to_nbrdf",
                "train_script": "Neural-BRDF/binary_to_nbrdf/binary_to_nbrdf.py",
                "convert_script": "Neural-BRDF/binary_to_nbrdf/h5_to_npy.py",
            },
        ),
        TrainModelItem(
            key="hyperbrdf",
            label="HyperBRDF",
            category="hyper",
            adapter="hyper-family",
            built_in=True,
            description="HyperBRDF 基线模型，支持训练、参数提取和 .fullbin 解码。",
            supports_training=True,
            supports_extract=True,
            supports_decode=True,
            supports_runs=True,
            default_paths={
                "materials_dir": "data/inputs/binary",
                "results_dir": "HyperBRDF/results",
                "extract_dir": "HyperBRDF/results/extracted_pts",
                "checkpoint": "HyperBRDF/results/test/MERL/checkpoint.pt",
            },
            runtime={
                "conda_env": "hyperbrdf",
                "working_dir": "HyperBRDF",
                "train_script": "HyperBRDF/main.py",
                "extract_script": "HyperBRDF/test.py",
                "decode_script": "HyperBRDF/pt_to_fullmerl.py",
            },
        ),
    ]


class ModelRegistryService:
    def __init__(self, registry_path: Path = MODEL_REGISTRY_PATH) -> None:
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.write_text("[]\n", encoding="utf-8")

    def list_models(self) -> list[TrainModelItem]:
        items = [*self._load_builtins(), *self._load_custom_models()]
        items.sort(key=lambda item: (not item.built_in, item.category, item.label.lower()))
        return items

    def get_model(self, model_key: str) -> TrainModelItem:
        for item in self.list_models():
            if item.key == model_key:
                return item
        raise KeyError(model_key)

    def create_model(self, request: TrainModelCreateRequest) -> TrainModelItem:
        key = request.key.strip().lower()
        if not MODEL_KEY_PATTERN.match(key):
            raise ValueError("模型 key 只能包含小写字母、数字、下划线和短横线，且必须以字母或数字开头。")
        if any(item.key == key for item in self.list_models()):
            raise ValueError(f"模型 key 已存在: {key}")

        item = TrainModelItem(
            key=key,
            label=request.label.strip(),
            category=request.category,
            adapter=request.adapter,
            built_in=False,
            description=request.description.strip(),
            supports_training=request.supports_training,
            supports_extract=request.supports_extract,
            supports_decode=request.supports_decode,
            supports_runs=request.supports_runs,
            default_paths={k: v.strip() for k, v in request.default_paths.items() if v.strip()},
            runtime={k: v.strip() for k, v in request.runtime.items() if v.strip()},
            adapter_options=request.adapter_options,
        )
        self._validate_model(item)

        custom_models = self._load_custom_models()
        custom_models.append(item)
        self._save_custom_models(custom_models)
        return item

    def delete_model(self, model_key: str) -> None:
        if any(item.key == model_key for item in self._load_builtins()):
            raise ValueError(f"内建模型不允许删除: {model_key}")

        custom_models = self._load_custom_models()
        remaining = [item for item in custom_models if item.key != model_key]
        if len(remaining) == len(custom_models):
            raise KeyError(model_key)
        self._save_custom_models(remaining)

    def _load_builtins(self) -> list[TrainModelItem]:
        return _builtin_models()

    def _load_custom_models(self) -> list[TrainModelItem]:
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = []
        items: list[TrainModelItem] = []
        for payload in data:
            try:
                item = TrainModelItem.model_validate(payload)
            except Exception:
                continue
            item.built_in = False
            items.append(item)
        return items

    def _save_custom_models(self, items: list[TrainModelItem]) -> None:
        payload = [item.model_dump(mode="json") for item in items if not item.built_in]
        self.registry_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _validate_model(self, item: TrainModelItem) -> None:
        expected_category = "hyper" if item.adapter == "hyper-family" else "neural"
        if item.category != expected_category:
            raise ValueError(f"适配器 {item.adapter} 只能用于 {expected_category} 类模型。")

        required_runtime = ["train_script"] if item.supports_training else []
        if item.adapter == "neural-keras":
            required_runtime.append("convert_script")
        if item.adapter == "hyper-family" and item.supports_extract:
            required_runtime.append("extract_script")
        if item.adapter == "hyper-family" and item.supports_decode:
            required_runtime.append("decode_script")
        if item.adapter == "hyper-family":
            required_runtime.append("working_dir")

        for field in required_runtime:
            value = item.runtime.get(field, "").strip()
            if not value:
                raise ValueError(f"runtime.{field} 为必填项。")
            resolved = self._resolve_project_path(value)
            if field.endswith("_script") and not resolved.is_file():
                raise ValueError(f"{field} 不存在或不是文件: {value}")
            if field == "working_dir" and not resolved.is_dir():
                raise ValueError(f"working_dir 不存在或不是目录: {value}")

        if item.adapter == "hyper-family" and item.supports_runs and not item.default_paths.get("results_dir", "").strip():
            raise ValueError("支持运行记录的超网络模型必须提供 default_paths.results_dir。")
        if item.adapter == "hyper-family" and (item.supports_extract or item.supports_decode):
            if not item.default_paths.get("extract_dir", "").strip():
                raise ValueError("支持参数提取或解码的超网络模型必须提供 default_paths.extract_dir。")

        for path_value in item.runtime.values():
            self._resolve_project_path(path_value)
        for path_value in item.default_paths.values():
            if path_value:
                self._resolve_project_path(path_value, must_exist=False)

    def _resolve_project_path(self, path_value: str, *, must_exist: bool = True) -> Path:
        raw_path = Path(path_value)
        candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        resolved = candidate.resolve(strict=False)
        project_root = PROJECT_ROOT.resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"路径必须位于项目根目录内: {path_value}") from exc
        if must_exist and not resolved.exists():
            raise ValueError(f"路径不存在: {path_value}")
        return resolved


model_registry_service = ModelRegistryService()
