from fastapi import APIRouter, HTTPException, Query

from backend.models.train import (
    HyperDecodeRequest,
    HyperExtractRequest,
    HyperTrainRunRequest,
    NeuralKerasTrainRequest,
    NeuralPytorchTrainRequest,
    TrainModelsResponse,
    TrainProjectVariant,
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
def train_runs(project_variant: TrainProjectVariant | None = Query(default=None)) -> TrainRunsResponse:
    return train_service.list_runs(project_variant=project_variant)


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
    record = await train_service.start_neural_pytorch(request)
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/neural/keras", response_model=TrainTaskStartResponse)
async def train_neural_keras(request: NeuralKerasTrainRequest) -> TrainTaskStartResponse:
    record = await train_service.start_neural_keras(request)
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/hyper/run", response_model=TrainTaskStartResponse)
async def train_hyper_run(request: HyperTrainRunRequest) -> TrainTaskStartResponse:
    record = await train_service.start_hyper_run(request)
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/hyper/extract", response_model=TrainTaskStartResponse)
async def train_hyper_extract(request: HyperExtractRequest) -> TrainTaskStartResponse:
    record = await train_service.start_hyper_extract(request)
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/train/hyper/decode", response_model=TrainTaskStartResponse)
async def train_hyper_decode(request: HyperDecodeRequest) -> TrainTaskStartResponse:
    record = await train_service.start_hyper_decode(request)
    return TrainTaskStartResponse(task_id=record.task_id, status=record.status)
