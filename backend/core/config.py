from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
RUNTIME_ROOT = BACKEND_ROOT / "runtime"
TASKS_ROOT = RUNTIME_ROOT / "tasks"
LOGS_ROOT = RUNTIME_ROOT / "logs"
OUTPUTS_ROOT = PROJECT_ROOT / "data" / "outputs"


for path in (RUNTIME_ROOT, TASKS_ROOT, LOGS_ROOT):
    path.mkdir(parents=True, exist_ok=True)


API_PREFIX = "/api/v1"
MEDIA_OUTPUTS_PREFIX = "/media/outputs"
