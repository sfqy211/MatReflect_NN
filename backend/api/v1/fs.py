from fastapi import APIRouter, HTTPException

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
