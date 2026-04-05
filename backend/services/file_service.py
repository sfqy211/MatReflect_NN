from datetime import datetime

from backend.core.config import MEDIA_OUTPUTS_PREFIX, OUTPUTS_ROOT
from backend.core.paths import resolve_safe_path
from backend.models.common import FileListItem, FileListRequest, FileListResponse


def build_preview_url(path) -> str | None:
    try:
        relative = path.resolve().relative_to(OUTPUTS_ROOT.resolve())
    except ValueError:
        return None
    return f"{MEDIA_OUTPUTS_PREFIX}/{relative.as_posix()}"


def list_files(request: FileListRequest) -> FileListResponse:
    base_path = resolve_safe_path(request.path_key)
    base_path.mkdir(parents=True, exist_ok=True)

    entries = sorted(base_path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    if request.search:
        query = request.search.lower()
        entries = [entry for entry in entries if query in entry.name.lower()]
    if request.suffix:
        allowed = {suffix.lower() for suffix in request.suffix}
        entries = [
            entry for entry in entries
            if entry.is_dir() or entry.suffix.lower() in allowed
        ]

    total = len(entries)
    start = (request.page - 1) * request.page_size
    end = start + request.page_size
    paged = entries[start:end]

    items = [
        FileListItem(
            name=entry.name,
            path=str(entry.resolve()),
            size=0 if entry.is_dir() else entry.stat().st_size,
            modified_at=datetime.fromtimestamp(entry.stat().st_mtime),
            is_dir=entry.is_dir(),
            preview_url=None if entry.is_dir() else build_preview_url(entry),
        )
        for entry in paged
    ]

    return FileListResponse(
        path_key=request.path_key,
        resolved_path=str(base_path.resolve()),
        page=request.page,
        page_size=request.page_size,
        total=total,
        items=items,
    )
