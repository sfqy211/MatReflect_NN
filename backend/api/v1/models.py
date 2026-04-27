"""自定义模型导入 API 路由。"""

from fastapi import APIRouter, HTTPException

from backend.models.train import TrainModelItem
from backend.services.model_import_service import (
    ModelImportRequest,
    ModelImportResponse,
    ModelEnvStatusResponse,
    model_import_service,
)
from backend.services.model_registry import model_registry_service


router = APIRouter(tags=["models"])


@router.post("/models/import", response_model=ModelImportResponse)
def import_model(request: ModelImportRequest) -> ModelImportResponse:
    try:
        return model_import_service.import_model(request)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/models/{model_key}")
def delete_model(model_key: str) -> dict:
    try:
        model_import_service.delete_model(model_key)
        return {"status": "deleted", "model_key": model_key}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models/{model_key}/config", response_model=TrainModelItem)
def get_model_config(model_key: str) -> TrainModelItem:
    try:
        return model_registry_service.get_model(model_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_key}") from exc


@router.put("/models/{model_key}/config", response_model=TrainModelItem)
def update_model_config(model_key: str, patch: dict) -> TrainModelItem:
    try:
        return model_registry_service.update_model(model_key, patch)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models/{model_key}/env-status", response_model=ModelEnvStatusResponse)
def model_env_status(model_key: str) -> ModelEnvStatusResponse:
    try:
        return model_import_service.get_env_status(model_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_key}") from exc


@router.post("/models/{model_key}/setup-env")
async def setup_model_env(model_key: str) -> dict:
    try:
        conda_env = await model_import_service.setup_env(model_key)
        return {"status": "env_created", "model_key": model_key, "conda_env": conda_env}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
