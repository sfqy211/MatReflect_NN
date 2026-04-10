from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.core.config import MEDIA_OUTPUTS_PREFIX, OUTPUTS_ROOT, PROJECT_ROOT
from backend.core.paths import resolve_safe_path
from backend.models.common import (
    FileListItem,
    FileListPathRequest,
    FileListRequest,
    FileListResponse,
)


def build_preview_url(path: Path) -> Optional[str]:
    try:
        relative = path.resolve().relative_to(OUTPUTS_ROOT.resolve())
    except ValueError:
        return None
    return f"{MEDIA_OUTPUTS_PREFIX}/{relative.as_posix()}"


def list_files(request: FileListRequest) -> FileListResponse:
    return _build_listing(resolve_safe_path(request.path_key), request.path_key, request.page, request.page_size, request.suffix, request.search)


def list_files_by_path(request: FileListPathRequest) -> FileListResponse:
    directory = resolve_workspace_path(request.directory)
    return _build_listing(directory, "workspace_path", request.page, request.page_size, request.suffix, request.search)


def resolve_workspace_path(path_value: str) -> Path:
    raw_path = Path(path_value)
    candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    resolved = candidate.resolve(strict=False)
    project_root = PROJECT_ROOT.resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside project root: {path_value}") from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _build_listing(
    base_path: Path,
    path_key: str,
    page: int,
    page_size: int,
    suffix: list[str],
    search: str,
) -> FileListResponse:
    base_path.mkdir(parents=True, exist_ok=True)

    entries = sorted(base_path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    if search:
        query = search.lower()
        entries = [entry for entry in entries if query in entry.name.lower()]
    if suffix:
        allowed = {item.lower() for item in suffix}
        entries = [entry for entry in entries if entry.is_dir() or entry.suffix.lower() in allowed]

    total = len(entries)
    start = (page - 1) * page_size
    end = start + page_size
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
        path_key=path_key,
        resolved_path=str(base_path.resolve()),
        page=page,
        page_size=page_size,
        total=total,
        items=items,
    )
