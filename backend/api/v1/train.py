from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models.train import (
    HyperDecodeRequest,
    HyperExtractRequest,
    HyperTrainRunRequest,
    NeuralH5ConvertRequest,
    NeuralKerasTrainRequest,
    NeuralPytorchTrainRequest,
    ReconstructRequest,
    TrainModelsResponse,
    TrainRunsResponse,
    TrainTaskDetailResponse,
    TrainTaskStartResponse,
    TrainTaskStopRequest,
)
from backend.services.train_service import train_service


router = APIRouter(tags=["train"])


@router.get("/train/models", response_model=TrainModelsResponse)
def train_models() -> TrainModelsResponse:
    return train_service.list_models()


@router.get("/train/runs", response_model=TrainRunsResponse)
def train_runs(
    model_key: Optional[str] = Query(default=None),
    project_variant: Optional[str] = Query(default=None),
) -> TrainRunsResponse:
    selected_key = None
    if model_key is not None:
        normalized = model_key.strip()
        selected_key = normalized or "__empty__"
    elif project_variant is not None:
        normalized = project_variant.strip()
        selected_key = normalized or "__empty__"
    if selected_key == "__empty__":
        return TrainRunsResponse(total=0, items=[])
    try:
        return train_service.list_runs(model_key=selected_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown model_key: {selected_key}") from exc


@router.get("/train/tasks/{task_id}", response_model=TrainTaskDetailResponse)
def train_task_detail(task_id: str) -> TrainTaskDetailResponse:
    detail = train_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return TrainTaskDetailResponse(**detail.model_dump())


@router.post("/train/stop", response_model=TrainTaskStartResponse)
async def train_stop(request: TrainTaskStopRequest) -> TrainTaskStartResponse:
    stopped = await train_service.stop_task(request.task_id)
    if not stopped:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {request.task_id}")
    detail = train_service.get_task_detail(request.task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {request.task_id}")
    return TrainTaskStartResponse(task_id=detail.record.task_id, status=detail.record.status)


@router.post("/train/neural/pytorch", response_model=TrainTaskStartResponse)
async def train_neural_pytorch(request: NeuralPytorchTrainRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_neural_pytorch(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/neural/keras", response_model=TrainTaskStartResponse)
async def train_neural_keras(request: NeuralKerasTrainRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_neural_keras(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/neural/keras/convert", response_model=TrainTaskStartResponse)
async def train_neural_keras_convert(request: NeuralH5ConvertRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_neural_h5_convert(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/hyper/run", response_model=TrainTaskStartResponse)
async def train_hyper_run(request: HyperTrainRunRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_hyper_run(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/hyper/extract", response_model=TrainTaskStartResponse)
async def train_hyper_extract(request: HyperExtractRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_hyper_extract(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/hyper/decode", response_model=TrainTaskStartResponse)
async def train_hyper_decode(request: HyperDecodeRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_hyper_decode(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/reconstruct", response_model=TrainTaskStartResponse)
async def train_reconstruct(request: ReconstructRequest) -> TrainTaskStartResponse:
    try:
        record = await train_service.start_reconstruct(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)
