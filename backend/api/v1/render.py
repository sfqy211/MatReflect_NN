from fastapi import APIRouter, HTTPException, Query

from backend.models.render import (
    RenderBatchRequest,
    RenderConvertRequest,
    RenderFilesResponse,
    RenderMode,
    RenderOutputFilesResponse,
    RenderScenesResponse,
    TaskStartResponse,
    TaskStopRequest,
)
from backend.services.render_service import render_service


router = APIRouter(tags=["render"])


@router.get("/render/scenes", response_model=RenderScenesResponse)
def render_scenes() -> RenderScenesResponse:
    return render_service.list_scenes()


@router.get("/render/files", response_model=RenderFilesResponse)
def render_files(
    render_mode: RenderMode,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=200, ge=1, le=500),
    search: str = "",
) -> RenderFilesResponse:
    return render_service.list_input_files(render_mode, page=page, page_size=page_size, search=search)


@router.get("/render/outputs", response_model=RenderOutputFilesResponse)
def render_outputs(
    render_mode: RenderMode,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=200),
) -> RenderOutputFilesResponse:
    return render_service.list_output_files(render_mode, page=page, page_size=page_size)


@router.post("/render/batch", response_model=TaskStartResponse)
async def render_batch(request: RenderBatchRequest) -> TaskStartResponse:
    record = await render_service.start_batch(request)
    return TaskStartResponse(task_id=record.task_id, status=record.status)


@router.post("/render/stop", response_model=TaskStartResponse)
async def render_stop(request: TaskStopRequest) -> TaskStartResponse:
    stopped = await render_service.stop_task(request.task_id)
    if not stopped:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {request.task_id}")
    record = render_service.get_task_detail(request.task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {request.task_id}")
    return TaskStartResponse(task_id=record.record.task_id, status=record.record.status)


@router.post("/render/convert", response_model=TaskStartResponse)
async def render_convert(request: RenderConvertRequest) -> TaskStartResponse:
    record = await render_service.start_convert(request)
    return TaskStartResponse(task_id=record.task_id, status=record.status)


@router.get("/render/tasks/{task_id}")
def render_task_detail(task_id: str) -> dict:
    detail = render_service.get_task_detail(task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return detail.model_dump()
