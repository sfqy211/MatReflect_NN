from __future__ import annotations

import json
import warnings
from pathlib import Path

from backend.core.config import PROJECT_ROOT
from backend.models.train import TrainModelItem

MODEL_REGISTRY_CONFIG = PROJECT_ROOT / "backend" / "config" / "model_registry.json"


def _load_models_from_config() -> list[TrainModelItem]:
    """从 backend/config/model_registry.json 加载模型定义。"""
    if not MODEL_REGISTRY_CONFIG.exists():
        warnings.warn(f"Model registry config not found: {MODEL_REGISTRY_CONFIG}")
        return []
    try:
        raw = json.loads(MODEL_REGISTRY_CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.warn(f"Failed to load model registry: {exc}")
        return []
    items: list[TrainModelItem] = []
    for entry in raw.get("models", []):
        try:
            items.append(TrainModelItem.model_validate(entry))
        except Exception as exc:
            warnings.warn(f"Invalid model entry skipped: {exc}")
    return items


def _save_models_to_config(items: list[TrainModelItem]) -> None:
    """将模型列表保存回 model_registry.json。"""
    raw = {"models": [item.model_dump() for item in items]}
    MODEL_REGISTRY_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    MODEL_REGISTRY_CONFIG.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ModelRegistryService:
    def list_models(self) -> list[TrainModelItem]:
        items = self._load_from_config()
        items.sort(key=lambda item: (0 if item.built_in else 1, item.category, item.label.lower()))
        return items

    def get_model(self, model_key: str) -> TrainModelItem:
        for item in self.list_models():
            if item.key == model_key:
                return item
        raise KeyError(model_key)

    def register_model(self, model: TrainModelItem) -> None:
        """注册一个新模型（仅非内建模型）。"""
        items = self._load_from_config()
        if any(item.key == model.key for item in items):
            raise ValueError(f"Model key already exists: {model.key}")
        items.append(model)
        _save_models_to_config(items)

    def unregister_model(self, model_key: str) -> None:
        """移除一个非内建模型。"""
        items = self._load_from_config()
        target = None
        for item in items:
            if item.key == model_key:
                if item.built_in:
                    raise ValueError(f"Cannot remove built-in model: {model_key}")
                target = item
                break
        if target is None:
            raise KeyError(model_key)
        items.remove(target)
        _save_models_to_config(items)

    def update_model(self, model_key: str, patch: dict) -> TrainModelItem:
        """更新模型配置（仅非内建模型）。"""
        items = self._load_from_config()
        for idx, item in enumerate(items):
            if item.key == model_key:
                if item.built_in:
                    raise ValueError(f"Cannot modify built-in model: {model_key}")
                updated = item.model_copy(update=patch)
                items[idx] = updated
                _save_models_to_config(items)
                return updated
        raise KeyError(model_key)

    def _load_from_config(self) -> list[TrainModelItem]:
        return _load_models_from_config()


model_registry_service = ModelRegistryService()
