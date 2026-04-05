from typing import Literal

from pydantic import BaseModel, Field

from backend.models.common import FileListItem


AnalysisImageSet = Literal["brdfs", "fullbin", "npy", "grids", "comparisons"]


class AnalysisImagesResponse(BaseModel):
    image_set: AnalysisImageSet
    resolved_path: str
    total: int
    items: list[FileListItem] = Field(default_factory=list)


class MetricSummary(BaseModel):
    psnr: float
    ssim: float
    delta_e: float


class EvaluationPairResult(BaseModel):
    label: str
    metrics: MetricSummary


class EvaluationResponse(BaseModel):
    processed_count: int
    skipped: list[str] = Field(default_factory=list)
    comparisons: list[EvaluationPairResult] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    gt_set: AnalysisImageSet = "brdfs"
    method1_set: AnalysisImageSet = "fullbin"
    method2_set: AnalysisImageSet = "npy"
    selected_materials: list[str] = Field(default_factory=list)


class GridRequest(BaseModel):
    image_set: AnalysisImageSet = "brdfs"
    output_name: str = "merged_grid.png"
    show_names: bool = True
    cell_width: int = Field(default=256, ge=64, le=1024)
    padding: int = Field(default=10, ge=0, le=100)
    selected_materials: list[str] = Field(default_factory=list)


class ComparisonColumn(BaseModel):
    image_set: AnalysisImageSet
    label: str


class ComparisonRequest(BaseModel):
    columns: list[ComparisonColumn] = Field(default_factory=list)
    selected_materials: list[str] = Field(default_factory=list)
    show_label: bool = True
    show_filename: bool = True
    output_name: str = "merged_comparison.png"


class GeneratedImageResponse(BaseModel):
    item: FileListItem
    processed_count: int
    skipped: list[str] = Field(default_factory=list)
