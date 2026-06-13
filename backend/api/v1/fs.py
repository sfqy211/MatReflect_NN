import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.common import FileListPathRequest, FileListRequest, FileListResponse
from backend.services.file_service import list_files, list_files_by_path


router = APIRouter(tags=["fs"])


@router.post("/fs/list", response_model=FileListResponse)
def file_list(request: FileListRequest) -> FileListResponse:
    try:
        return list_files(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown path_key: {request.path_key}") from exc


@router.post("/fs/list-path", response_model=FileListResponse)
def file_list_by_path(request: FileListPathRequest) -> FileListResponse:
    try:
        return list_files_by_path(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class RevealRequest(BaseModel):
    path: str


@router.post("/fs/reveal-in-explorer")
def reveal_in_explorer(request: RevealRequest) -> dict:
    target = Path(request.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"路径不存在: {request.path}")
    if sys.platform == "win32":
        if target.is_file():
            subprocess.Popen(["explorer", "/select,", str(target)])
        else:
            subprocess.Popen(["explorer", str(target)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target.parent if target.is_file() else target)])
    return {"ok": True}
