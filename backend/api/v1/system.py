from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.models.common import HealthResponse, TaskDetailResponse, TaskStartResponse, TaskStopRequest
from backend.models.system import SystemCompileRequest, SystemSummaryResponse
from backend.services.system_service import system_service


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(timestamp=datetime.now())


@router.get("/system/summary", response_model=SystemSummaryResponse)
def system_summary() -> SystemSummaryResponse:
    return system_service.get_summary()


@router.post("/system/compile", response_model=TaskStartResponse)
async def system_compile(request: SystemCompileRequest) -> TaskStartResponse:
    try:
        record = await system_service.start_compile(request)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/system/compile/stop", response_model=TaskStartResponse)
async def system_compile_stop(request: TaskStopRequest) -> TaskStartResponse:
    stopped = await system_service.stop_task(request.task_id)
    if not stopped:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {request.task_id}")
    detail = system_service.get_task_detail(request.task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {request.task_id}")
    return TaskStartResponse(task_id=detail.record.task_id, status=detail.record.status)


@router.get("/system/compile/tasks/{task_id}", response_model=TaskDetailResponse)
def system_compile_task_detail(task_id: str) -> TaskDetailResponse:
    detail = system_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return detail
