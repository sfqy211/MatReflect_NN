from datetime import datetime

from fastapi import APIRouter

from backend.core.config import PROJECT_ROOT
from backend.core.paths import SAFE_PATHS, get_mitsuba_paths
from backend.models.common import HealthResponse, SystemSummaryResponse
from backend.services.task_manager import task_manager


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(timestamp=datetime.now())


@router.get("/system/summary", response_model=SystemSummaryResponse)
def system_summary() -> SystemSummaryResponse:
    paths = get_mitsuba_paths()
    return SystemSummaryResponse(
        project_root=str(PROJECT_ROOT.resolve()),
        mitsuba_dir=str(paths["mitsuba_dir"]),
        mitsuba_exe=str(paths["mitsuba_exe"]),
        mtsutil_exe=str(paths["mtsutil_exe"]),
        mitsuba_exists=paths["mitsuba_exe"].exists(),
        mtsutil_exists=paths["mtsutil_exe"].exists(),
        available_modules=["render", "analysis", "models"],
        available_path_keys=sorted(SAFE_PATHS.keys()),
    )


@router.post("/system/demo-task")
async def demo_task() -> dict:
    record = await task_manager.start_demo_task()
    return {"task_id": record.task_id, "status": record.status}
