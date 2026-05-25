from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import FileListItem


AnalysisImageSet = Literal["brdfs", "fullbin", "npy", "snbrdf", "grids", "comparisons"]


class AnalysisImagesResponse(BaseModel):
    image_set: AnalysisImageSet
    resolved_path: str
    total: int
    items: list[FileListItem] = Field(default_factory=list)


class AnalysisSource(BaseModel):
    image_set: Optional[AnalysisImageSet] = None
    directory: str = ""
    label: str = ""


class MetricSummary(BaseModel):
    psnr: float = 0.0
    ssim: float = 0.0
    delta_e: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0


class EvaluationPairResult(BaseModel):
    label: str
    metrics: MetricSummary


class MaterialMetricItem(BaseModel):
    material: str
    metrics: dict[str, MetricSummary]


class EvaluationResponse(BaseModel):
    processed_count: int
    skipped: list[str] = Field(default_factory=list)
    comparisons: list[EvaluationPairResult] = Field(default_factory=list)
    per_material: list[MaterialMetricItem] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    gt_set: AnalysisImageSet = "brdfs"
    method1_set: AnalysisImageSet = "fullbin"
    method2_set: AnalysisImageSet = "npy"
    method3_set: Optional[AnalysisImageSet] = None
    gt_dir: str = ""
    method1_dir: str = ""
    method2_dir: str = ""
    method3_dir: str = ""
    gt_label: str = "GT / BRDF"
    method1_label: str = "FullBin"
    method2_label: str = "NPY"
    method3_label: str = ""
    selected_materials: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=lambda: ["psnr", "ssim", "delta_e"])


class GridRequest(BaseModel):
    image_set: AnalysisImageSet = "brdfs"
    source_dir: str = ""
    output_dir: str = ""
    output_name: str = "merged_grid.png"
    show_names: bool = True
    cell_width: int = Field(default=256, ge=64, le=1024)
    padding: int = Field(default=10, ge=0, le=100)
    selected_materials: list[str] = Field(default_factory=list)


class ComparisonColumn(BaseModel):
    image_set: Optional[AnalysisImageSet] = None
    directory: str = ""
    label: str


class ComparisonRequest(BaseModel):
    columns: list[ComparisonColumn] = Field(default_factory=list)
    selected_materials: list[str] = Field(default_factory=list)
    show_label: bool = True
    show_filename: bool = True
    output_dir: str = ""
    output_name: str = "merged_comparison.png"


class GeneratedImageResponse(BaseModel):
    item: FileListItem
    processed_count: int
    skipped: list[str] = Field(default_factory=list)


class DeleteImageRequest(BaseModel):
    image_paths: list[str]
    delete_matching_exr: bool = True


class DeleteImageResponse(BaseModel):
    deleted: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
