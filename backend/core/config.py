import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _env_path(name: str, fallback: Path) -> Path:
    raw_value = os.environ.get(name, "").strip()
    if raw_value:
        return Path(raw_value).expanduser().resolve()
    return fallback.resolve()


PROJECT_ROOT = _env_path("MATREFLECT_PROJECT_ROOT", BACKEND_ROOT.parent)
RUNTIME_ROOT = _env_path("MATREFLECT_RUNTIME_ROOT", PROJECT_ROOT / "backend" / "runtime")
TASKS_ROOT = RUNTIME_ROOT / "tasks"
LOGS_ROOT = RUNTIME_ROOT / "logs"
OUTPUTS_ROOT = _env_path("MATREFLECT_OUTPUTS_ROOT", PROJECT_ROOT / "data" / "outputs")


for path in (RUNTIME_ROOT, TASKS_ROOT, LOGS_ROOT):
    path.mkdir(parents=True, exist_ok=True)


API_PREFIX = "/api/v1"
MEDIA_OUTPUTS_PREFIX = "/media/outputs"
