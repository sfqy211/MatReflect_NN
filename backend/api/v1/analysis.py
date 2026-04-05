from fastapi import APIRouter, HTTPException, Query

from backend.models.analysis import (
    AnalysisImageSet,
    AnalysisImagesResponse,
    ComparisonRequest,
    EvaluationRequest,
    EvaluationResponse,
    GeneratedImageResponse,
    GridRequest,
)
from backend.services.analysis_service import analysis_service


router = APIRouter(tags=["analysis"])


@router.get("/analysis/images", response_model=AnalysisImagesResponse)
def analysis_images(
    image_set: AnalysisImageSet,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=200),
    search: str = "",
) -> AnalysisImagesResponse:
    return analysis_service.list_images(image_set, page=page, page_size=page_size, search=search)


@router.post("/analysis/evaluate", response_model=EvaluationResponse)
def analysis_evaluate(request: EvaluationRequest) -> EvaluationResponse:
    try:
        return analysis_service.evaluate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analysis/grid", response_model=GeneratedImageResponse)
def analysis_grid(request: GridRequest) -> GeneratedImageResponse:
    try:
        return analysis_service.generate_grid(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analysis/comparison", response_model=GeneratedImageResponse)
def analysis_comparison(request: ComparisonRequest) -> GeneratedImageResponse:
    try:
        return analysis_service.generate_comparison(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
