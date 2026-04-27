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


class ModelRegistryService:
    def list_models(self) -> list[TrainModelItem]:
        items = self._load_from_config()
        items.sort(key=lambda item: (item.category, item.label.lower()))
        return items

    def get_model(self, model_key: str) -> TrainModelItem:
        for item in self.list_models():
            if item.key == model_key:
                return item
        raise KeyError(model_key)

    def _load_from_config(self) -> list[TrainModelItem]:
        return _load_models_from_config()


model_registry_service = ModelRegistryService()
