from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage import color, metrics

from backend.core.config import OUTPUTS_ROOT, PROJECT_ROOT
from backend.core.system_settings import load_system_settings
from backend.models.analysis import (
    AnalysisImageSet,
    AnalysisImagesResponse,
    ComparisonColumn,
    ComparisonRequest,
    DeleteImageRequest,
    DeleteImageResponse,
    EvaluationPairResult,
    EvaluationRequest,
    EvaluationResponse,
    GeneratedImageResponse,
    GridRequest,
    MetricSummary,
)
from backend.models.common import FileListItem
from backend.services.file_service import build_preview_url, resolve_workspace_path


DEFAULT_SET_LABELS: dict[AnalysisImageSet, str] = {
    "brdfs": "GT / 参考值",
    "fullbin": "HyperBRDF 输出",
    "npy": "Neural-BRDF 输出",
    "grids": "Grids",
    "comparisons": "Comparisons",
}


def normalize_material_name(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = re.sub(r"_(?:\d{8}|\d{1,2})_\d{6}$", "", stem)
    stem = re.sub(r"_fc1$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\.fullbin$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\.binary$", "", stem, flags=re.IGNORECASE)
    return stem


def build_file_item(path: Path) -> FileListItem:
    stat = path.stat()
    return FileListItem(
        name=path.name,
        path=str(path.resolve()),
        size=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
        is_dir=False,
        preview_url=build_preview_url(path),
    )


def calc_single_pair(img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
    psnr = metrics.peak_signal_noise_ratio(img1, img2, data_range=255)
    try:
        ssim = metrics.structural_similarity(img1, img2, data_range=255, channel_axis=2)
    except TypeError:
        ssim = metrics.structural_similarity(img1, img2, data_range=255, multichannel=True)
    lab1 = color.rgb2lab(img1)
    lab2 = color.rgb2lab(img2)
    delta_e = float(np.mean(color.deltaE_ciede2000(lab1, lab2)))
    return np.array([psnr, ssim, delta_e], dtype=np.float64)


class AnalysisService:
    def __init__(self) -> None:
        for path in self._set_dirs().values():
            path.mkdir(parents=True, exist_ok=True)

    def _set_dirs(self) -> dict[AnalysisImageSet, Path]:
        settings = load_system_settings()
        project_root = Path(settings.project_root).resolve()

        def resolve_path(path_value: str) -> Path:
            raw_path = Path(path_value).expanduser()
            return (raw_path if raw_path.is_absolute() else project_root / raw_path).resolve(strict=False)

        return {
            "brdfs": resolve_path(settings.brdf_output_dir) / "png",
            "fullbin": resolve_path(settings.fullbin_output_dir) / "png",
            "npy": resolve_path(settings.npy_output_dir) / "png",
            "grids": resolve_path(settings.grids_output_dir),
            "comparisons": resolve_path(settings.comparisons_output_dir),
        }

    def _dir_for(self, image_set: AnalysisImageSet) -> Path:
        return self._set_dirs()[image_set]

    def _resolve_directory(self, image_set: Optional[AnalysisImageSet] = None, directory: str = "") -> Path:
        if directory.strip():
            resolved = resolve_workspace_path(directory.strip())
            resolved.mkdir(parents=True, exist_ok=True)
            return resolved
        if image_set is None:
            raise ValueError("Missing image_set or directory.")
        resolved = self._dir_for(image_set)
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def _resolve_workspace_path(self, path_value: str) -> Path:
        raw_path = Path(path_value)
        candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        resolved = candidate.resolve(strict=False)
        project_root = PROJECT_ROOT.resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"Path must stay inside project root: {path_value}") from exc
        return resolved

    def _list_pngs_from_dir(self, target_dir: Path) -> list[Path]:
        target_dir.mkdir(parents=True, exist_ok=True)
        return sorted(target_dir.glob("*.png"), key=lambda path: path.stat().st_mtime, reverse=True)

    def _material_index_from_dir(self, target_dir: Path) -> dict[str, Path]:
        index: dict[str, Path] = {}
        for path in self._list_pngs_from_dir(target_dir):
            material = normalize_material_name(path.name)
            index.setdefault(material, path)
        return index

    def _column_label(self, column: ComparisonColumn) -> str:
        if column.label.strip():
            return column.label.strip()
        if column.image_set:
            return DEFAULT_SET_LABELS[column.image_set]
        if column.directory.strip():
            return Path(column.directory).name or "Custom"
        return "Column"

    def _comparison_title(self, label_a: str, label_b: str) -> str:
        return f"{label_a} vs {label_b}"

    def _load_rgb(self, image_path: Path) -> Optional[np.ndarray]:
        image = cv2.imread(str(image_path))
        if image is None:
            return None
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def list_images(
        self,
        image_set: AnalysisImageSet,
        page: int = 1,
        page_size: int = 24,
        search: str = "",
        directory: str = "",
    ) -> AnalysisImagesResponse:
        resolved_dir = self._resolve_directory(image_set, directory)
        entries = self._list_pngs_from_dir(resolved_dir)
        if search:
            entries = [entry for entry in entries if search.lower() in entry.name.lower()]
        total = len(entries)
        paged = entries[(page - 1) * page_size : page * page_size]
        return AnalysisImagesResponse(
            image_set=image_set,
            resolved_path=str(resolved_dir.resolve()),
            total=total,
            items=[build_file_item(path) for path in paged],
        )

    def delete_image(self, request: DeleteImageRequest) -> DeleteImageResponse:
        deleted: list[str] = []
        missing: list[str] = []

        for img_path_str in request.image_paths:
            image_path = self._resolve_workspace_path(img_path_str)
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue # Skip invalid files but don't crash the whole batch

            if image_path.exists():
                image_path.unlink()
                deleted.append(str(image_path))
            else:
                missing.append(str(image_path))

            if request.delete_matching_exr:
                exr_dir = image_path.parent.parent / "exr" if image_path.parent.name.lower() == "png" else image_path.parent
                exr_path = exr_dir / f"{image_path.stem}.exr"
                try:
                    exr_path = self._resolve_workspace_path(str(exr_path))
                    if exr_path.exists():
                        exr_path.unlink()
                        deleted.append(str(exr_path))
                    else:
                        missing.append(str(exr_path))
                except ValueError:
                    pass # Ignore resolution errors for EXR in batch

        return DeleteImageResponse(deleted=deleted, missing=missing)

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        gt_dir = self._resolve_directory(request.gt_set, request.gt_dir)
        method1_dir = self._resolve_directory(request.method1_set, request.method1_dir)
        method2_dir = self._resolve_directory(request.method2_set, request.method2_dir)

        gt_index = self._material_index_from_dir(gt_dir)
        method1_index = self._material_index_from_dir(method1_dir)
        method2_index = self._material_index_from_dir(method2_dir)

        materials = request.selected_materials or sorted(gt_index.keys())
        metrics_gt_m1 = np.zeros(3, dtype=np.float64)
        metrics_gt_m2 = np.zeros(3, dtype=np.float64)
        metrics_m1_m2 = np.zeros(3, dtype=np.float64)
        processed = 0
        skipped: list[str] = []

        for material in materials:
            gt_path = gt_index.get(material)
            method1_path = method1_index.get(material)
            method2_path = method2_index.get(material)
            if not gt_path or not method1_path or not method2_path:
                skipped.append(material)
                continue

            img_gt_rgb = self._load_rgb(gt_path)
            img_m1_rgb = self._load_rgb(method1_path)
            img_m2_rgb = self._load_rgb(method2_path)
            if img_gt_rgb is None or img_m1_rgb is None or img_m2_rgb is None:
                skipped.append(material)
                continue

            if img_gt_rgb.shape != img_m1_rgb.shape:
                img_m1_rgb = cv2.resize(img_m1_rgb, (img_gt_rgb.shape[1], img_gt_rgb.shape[0]))
            if img_gt_rgb.shape != img_m2_rgb.shape:
                img_m2_rgb = cv2.resize(img_m2_rgb, (img_gt_rgb.shape[1], img_gt_rgb.shape[0]))

            metrics_gt_m1 += calc_single_pair(img_gt_rgb, img_m1_rgb)
            metrics_gt_m2 += calc_single_pair(img_gt_rgb, img_m2_rgb)
            metrics_m1_m2 += calc_single_pair(img_m1_rgb, img_m2_rgb)
            processed += 1

        if processed == 0:
            return EvaluationResponse(processed_count=0, skipped=skipped)

        def summary(values: np.ndarray) -> MetricSummary:
            averaged = values / processed
            return MetricSummary(psnr=float(averaged[0]), ssim=float(averaged[1]), delta_e=float(averaged[2]))

        gt_label = request.gt_label.strip() or DEFAULT_SET_LABELS[request.gt_set]
        method1_label = request.method1_label.strip() or DEFAULT_SET_LABELS[request.method1_set]
        method2_label = request.method2_label.strip() or DEFAULT_SET_LABELS[request.method2_set]

        return EvaluationResponse(
            processed_count=processed,
            skipped=skipped,
            comparisons=[
                EvaluationPairResult(label=self._comparison_title(gt_label, method1_label), metrics=summary(metrics_gt_m1)),
                EvaluationPairResult(label=self._comparison_title(gt_label, method2_label), metrics=summary(metrics_gt_m2)),
                EvaluationPairResult(label=self._comparison_title(method1_label, method2_label), metrics=summary(metrics_m1_m2)),
            ],
        )

    def generate_grid(self, request: GridRequest) -> GeneratedImageResponse:
        source_dir = self._resolve_directory(request.image_set, request.source_dir)
        source_index = self._material_index_from_dir(source_dir)
        selected = request.selected_materials or list(source_index.keys())
        files = [source_index[material] for material in selected if material in source_index]
        if not files:
            raise ValueError("No images available for grid generation.")

        cols = math.ceil(math.sqrt(len(files)))
        rows = math.ceil(len(files) / cols)
        text_height = 30 if request.show_names else 0
        with Image.open(files[0]) as sample:
            aspect = sample.height / sample.width
        cell_height = int(request.cell_width * aspect)
        width = cols * request.cell_width + (cols + 1) * request.padding
        height = rows * (cell_height + text_height) + (rows + 1) * request.padding
        grid_img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(grid_img)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except OSError:
            font = ImageFont.load_default()

        for idx, file_path in enumerate(files):
            with Image.open(file_path) as image:
                resized = image.resize((request.cell_width, cell_height), Image.LANCZOS)
                col = idx % cols
                row = idx // cols
                x = request.padding + col * (request.cell_width + request.padding)
                y = request.padding + row * (cell_height + text_height + request.padding)
                grid_img.paste(resized, (x, y))
                if request.show_names:
                    name_text = normalize_material_name(file_path.name)
                    if len(name_text) > 25:
                        name_text = name_text[:22] + "..."
                    bbox = draw.textbbox((0, 0), name_text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_x = x + (request.cell_width - text_w) / 2
                    text_y = y + cell_height + 5
                    draw.text((text_x, text_y), name_text, fill=(0, 0, 0), font=font)

        output_dir = self._resolve_directory("grids", request.output_dir)
        output_path = output_dir / request.output_name
        grid_img.save(output_path)
        return GeneratedImageResponse(item=build_file_item(output_path), processed_count=len(files))

    def generate_comparison(self, request: ComparisonRequest) -> GeneratedImageResponse:
        valid_columns: list[tuple[str, Path]] = []
        for column in request.columns:
            resolved_dir = self._resolve_directory(column.image_set, column.directory)
            valid_columns.append((self._column_label(column), resolved_dir))
        if not valid_columns:
            raise ValueError("No valid comparison columns configured.")

        indexes = {label: self._material_index_from_dir(directory) for label, directory in valid_columns}
        if request.selected_materials:
            materials = request.selected_materials
        else:
            common = set.intersection(*(set(index.keys()) for index in indexes.values())) if indexes else set()
            materials = sorted(common)
        if not materials:
            raise ValueError("No materials available for comparison generation.")

        try:
            font = ImageFont.truetype("arial.ttf", 20)
            title_font = ImageFont.truetype("arial.ttf", 24)
        except OSError:
            font = ImageFont.load_default()
            title_font = font

        processed_rows: list[Image.Image] = []
        skipped: list[str] = []
        padding = 10
        header_height = 40 if request.show_label else 0
        name_width = 60 if request.show_filename else 0

        for material in materials:
            current_paths: list[Path] = []
            for label, _directory in valid_columns:
                match = indexes[label].get(material)
                if not match:
                    current_paths = []
                    break
                current_paths.append(match)
            if not current_paths:
                skipped.append(material)
                continue

            current_images = [Image.open(path) for path in current_paths]
            width, height = current_images[0].size
            for idx in range(1, len(current_images)):
                current_images[idx] = current_images[idx].resize((width, height), Image.LANCZOS)

            row_w = name_width + width * len(current_images) + padding * (len(current_images) + 1)
            row_h = height + padding * 2
            row_img = Image.new("RGB", (row_w, row_h), (255, 255, 255))

            if request.show_filename:
                text_img = Image.new("RGBA", (220, 60), (255, 255, 255, 0))
                text_draw = ImageDraw.Draw(text_img)
                text_draw.text((0, 0), material, font=title_font, fill=(0, 0, 0))
                rotated = text_img.rotate(90, expand=True)
                row_img.paste(rotated, ((name_width - rotated.width) // 2, (row_h - rotated.height) // 2), rotated)

            for idx, image in enumerate(current_images):
                x = name_width + padding + idx * (width + padding)
                row_img.paste(image, (x, padding))
                image.close()
            processed_rows.append(row_img)

        if not processed_rows:
            raise ValueError("No comparison rows were generated.")

        total_width = processed_rows[0].width
        merged_height = sum(image.height for image in processed_rows) + header_height
        merged = Image.new("RGB", (total_width, merged_height), (255, 255, 255))
        current_y = 0

        if request.show_label:
            header = Image.new("RGB", (total_width, header_height), (255, 255, 255))
            draw = ImageDraw.Draw(header)
            sample_width = processed_rows[0].width - name_width - padding * (len(valid_columns) + 1)
            col_width = sample_width // len(valid_columns) if valid_columns else 0
            for idx, (label, _directory) in enumerate(valid_columns):
                bbox = draw.textbbox((0, 0), label, font=title_font)
                text_w = bbox[2] - bbox[0]
                text_x = name_width + padding + idx * (col_width + padding) + (col_width - text_w) / 2
                text_y = (header_height - (bbox[3] - bbox[1])) / 2
                draw.text((text_x, text_y), label, fill=(0, 0, 0), font=title_font)
            merged.paste(header, (0, 0))
            current_y += header_height

        for row in processed_rows:
            merged.paste(row, (0, current_y))
            current_y += row.height

        output_dir = self._resolve_directory("comparisons", request.output_dir)
        output_path = output_dir / request.output_name
        merged.save(output_path)
        return GeneratedImageResponse(item=build_file_item(output_path), processed_count=len(processed_rows), skipped=skipped)


analysis_service = AnalysisService()
