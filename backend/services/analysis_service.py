from __future__ import annotations

import math
import re
import sys
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
    MaterialMetricItem,
    MetricSummary,
)
from backend.models.common import FileListItem
from backend.services.file_service import build_preview_url, resolve_workspace_path


_FONT_CANDIDATES = (
    ["msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"]
    if sys.platform == "win32"
    else ["NotoSansCJK-Regular.ttc", "NotoSansCJK.otf", "DroidSansFallbackFull.ttf"]
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font that supports CJK characters, falling back to default."""
    if sys.platform == "win32":
        fonts_dir = Path("C:/Windows/Fonts")
        for name in _FONT_CANDIDATES:
            try:
                return ImageFont.truetype(str(fonts_dir / name), size)
            except OSError:
                continue
    else:
        for name in _FONT_CANDIDATES:
            for prefix in ("/usr/share/fonts", "/usr/local/share/fonts"):
                try:
                    return ImageFont.truetype(f"{prefix}/{name}", size)
                except OSError:
                    continue
    return ImageFont.load_default()


DEFAULT_SET_LABELS: dict[AnalysisImageSet, str] = {
    "brdfs": "GT / 参考值",
    "fullbin": "HyperBRDF 输出",
    "npy": "Neural-BRDF 输出",
    "snbrdf": "HyperSNBRDF 输出",
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


def calc_single_pair(img1: np.ndarray, img2: np.ndarray) -> dict[str, float]:
    img1_f = img1.astype(np.float64)
    img2_f = img2.astype(np.float64)

    mse = float(np.mean((img1_f - img2_f) ** 2))
    psnr = 10.0 * np.log10(255.0 ** 2 / mse) if mse > 0 else 100.0
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(img1_f - img2_f)))

    try:
        ssim = float(metrics.structural_similarity(img1, img2, data_range=255, channel_axis=2))
    except TypeError:
        ssim = float(metrics.structural_similarity(img1, img2, data_range=255, multichannel=True))

    lab1 = color.rgb2lab(img1)
    lab2 = color.rgb2lab(img2)
    delta_e = float(np.mean(color.deltaE_ciede2000(lab1, lab2)))

    return {"psnr": psnr, "ssim": ssim, "delta_e": delta_e, "rmse": rmse, "mae": mae}


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
            "brdfs": resolve_path(settings.merl_render_dir) / "png",
            "fullbin": resolve_path(settings.hyperbrdf_render_dir) / "png",
            "npy": resolve_path(settings.nbrdf_render_dir) / "png",
            "snbrdf": resolve_path(settings.snbrdf_render_dir) / "png",
            "grids": resolve_path(settings.grids_dir),
            "comparisons": resolve_path(settings.comparisons_dir),
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

        has_method3 = request.method3_set is not None
        method3_index: dict[str, Path] = {}
        if has_method3:
            method3_dir = self._resolve_directory(request.method3_set, request.method3_dir)
            method3_index = self._material_index_from_dir(method3_dir)

        gt_label = request.gt_label.strip() or DEFAULT_SET_LABELS[request.gt_set]
        method1_label = request.method1_label.strip() or DEFAULT_SET_LABELS[request.method1_set]
        method2_label = request.method2_label.strip() or DEFAULT_SET_LABELS[request.method2_set]
        pair_label_gt_m1 = self._comparison_title(gt_label, method1_label)
        pair_label_gt_m2 = self._comparison_title(gt_label, method2_label)
        pair_label_gt_m3 = self._comparison_title(gt_label, request.method3_label.strip() or DEFAULT_SET_LABELS.get(request.method3_set or "snbrdf", "M3")) if has_method3 else None

        all_metric_keys = ["psnr", "ssim", "delta_e", "rmse", "mae"]
        selected_metrics = set(request.metrics) if request.metrics else {"psnr", "ssim", "delta_e"}

        materials = request.selected_materials or sorted(gt_index.keys())
        accum_gt_m1: dict[str, float] = {k: 0.0 for k in all_metric_keys}
        accum_gt_m2: dict[str, float] = {k: 0.0 for k in all_metric_keys}
        accum_gt_m3: dict[str, float] | None = {k: 0.0 for k in all_metric_keys} if has_method3 else None
        processed = 0
        skipped: list[str] = []
        per_material: list[MaterialMetricItem] = []

        def _filter_summary(accum: dict[str, float], count: int) -> MetricSummary:
            avg = {k: v / count for k, v in accum.items()}
            return MetricSummary(**{k: round(avg[k], 6) for k in selected_metrics})

        for material in materials:
            gt_path = gt_index.get(material)
            method1_path = method1_index.get(material)
            method2_path = method2_index.get(material)
            if not gt_path or not method1_path or not method2_path:
                skipped.append(material)
                continue
            if has_method3 and not method3_index.get(material):
                skipped.append(material)
                continue

            img_gt_rgb = self._load_rgb(gt_path)
            img_m1_rgb = self._load_rgb(method1_path)
            img_m2_rgb = self._load_rgb(method2_path)
            if img_gt_rgb is None or img_m1_rgb is None or img_m2_rgb is None:
                skipped.append(material)
                continue

            img_m3_rgb = None
            if has_method3:
                img_m3_rgb = self._load_rgb(method3_index[material])
                if img_m3_rgb is None:
                    skipped.append(material)
                    continue

            if img_gt_rgb.shape != img_m1_rgb.shape:
                img_m1_rgb = cv2.resize(img_m1_rgb, (img_gt_rgb.shape[1], img_gt_rgb.shape[0]))
            if img_gt_rgb.shape != img_m2_rgb.shape:
                img_m2_rgb = cv2.resize(img_m2_rgb, (img_gt_rgb.shape[1], img_gt_rgb.shape[0]))
            if img_m3_rgb is not None and img_gt_rgb.shape != img_m3_rgb.shape:
                img_m3_rgb = cv2.resize(img_m3_rgb, (img_gt_rgb.shape[1], img_gt_rgb.shape[0]))

            r_gt_m1 = calc_single_pair(img_gt_rgb, img_m1_rgb)
            r_gt_m2 = calc_single_pair(img_gt_rgb, img_m2_rgb)

            for k in all_metric_keys:
                accum_gt_m1[k] += r_gt_m1[k]
                accum_gt_m2[k] += r_gt_m2[k]

            def _make_summary(r: dict[str, float]) -> MetricSummary:
                return MetricSummary(**{k: round(r[k], 6) for k in selected_metrics})

            material_metrics: dict[str, MetricSummary] = {
                pair_label_gt_m1: _make_summary(r_gt_m1),
                pair_label_gt_m2: _make_summary(r_gt_m2),
            }

            if img_m3_rgb is not None and accum_gt_m3 is not None:
                r_gt_m3 = calc_single_pair(img_gt_rgb, img_m3_rgb)
                for k in all_metric_keys:
                    accum_gt_m3[k] += r_gt_m3[k]
                material_metrics[pair_label_gt_m3] = _make_summary(r_gt_m3)

            per_material.append(MaterialMetricItem(material=material, metrics=material_metrics))
            processed += 1

        if processed == 0:
            return EvaluationResponse(processed_count=0, skipped=skipped)

        comparisons = [
            EvaluationPairResult(label=pair_label_gt_m1, metrics=_filter_summary(accum_gt_m1, processed)),
            EvaluationPairResult(label=pair_label_gt_m2, metrics=_filter_summary(accum_gt_m2, processed)),
        ]

        if has_method3 and accum_gt_m3 is not None:
            comparisons.append(EvaluationPairResult(label=pair_label_gt_m3, metrics=_filter_summary(accum_gt_m3, processed)))

        return EvaluationResponse(
            processed_count=processed,
            skipped=skipped,
            comparisons=comparisons,
            per_material=per_material,
        )

    def generate_grid(self, request: GridRequest) -> GeneratedImageResponse:
        source_dir = self._resolve_directory(request.image_set, request.source_dir)
        source_index = self._material_index_from_dir(source_dir)
        selected = sorted(request.selected_materials) if request.selected_materials else sorted(source_index.keys())
        files = [source_index[material] for material in selected if material in source_index]
        if not files:
            raise ValueError("No images available for grid generation.")

        cols = math.ceil(math.sqrt(len(files)))
        rows = math.ceil(len(files) / cols)
        text_height = 30 if request.show_names else 0

        # Resize first image to get exact cell dimensions
        with Image.open(files[0]) as sample:
            src_w, src_h = sample.size
            scale = request.scale_percent / 100.0
            cell_w = round(src_w * scale)
            cell_h = round(src_h * scale)
            resized_first = sample.resize((cell_w, cell_h), Image.LANCZOS)
            cell_w, cell_h = resized_first.size

        width = cols * cell_w + (cols + 1) * request.padding
        height = rows * (cell_h + text_height) + (rows + 1) * request.padding
        grid_img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(grid_img)
        font = _load_font(14)

        for idx, file_path in enumerate(files):
            with Image.open(file_path) as image:
                resized = image.resize((cell_w, cell_h), Image.LANCZOS)
                col = idx % cols
                row = idx // cols
                x = request.padding + col * (cell_w + request.padding)
                y = request.padding + row * (cell_h + text_height + request.padding)
                grid_img.paste(resized, (x, y))
                if request.show_names:
                    name_text = normalize_material_name(file_path.name)
                    if len(name_text) > 25:
                        name_text = name_text[:22] + "..."
                    bbox = draw.textbbox((0, 0), name_text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_x = x + (cell_w - text_w) / 2
                    text_y = y + cell_h + 5
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
            materials = sorted(request.selected_materials)
        else:
            common = set.intersection(*(set(index.keys()) for index in indexes.values())) if indexes else set()
            materials = sorted(common)
        if not materials:
            raise ValueError("No materials available for comparison generation.")

        scale = request.scale_percent / 100.0
        font = _load_font(round(20 * scale))
        title_font = _load_font(round(36 * scale))

        processed_rows: list[Image.Image] = []
        skipped: list[str] = []
        row_pad = round(2 * scale)
        header_height = 28 if request.show_label else 0

        # Calculate name_width from the longest material name (before rotation)
        if request.show_filename and materials:
            tmp = Image.new("RGBA", (1, 1))
            tmp_draw = ImageDraw.Draw(tmp)
            max_th = max(
                tmp_draw.textbbox((0, 0), m.upper(), font=title_font)[3]
                for m in materials
            )
            name_width = max_th + 16
        else:
            name_width = 0

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
            orig_w, orig_h = current_images[0].size
            cell_w = round(orig_w * scale)
            cell_h = round(orig_h * scale)
            for idx in range(len(current_images)):
                current_images[idx] = current_images[idx].resize((cell_w, cell_h), Image.LANCZOS)

            # Images are flush against each other (no horizontal gap)
            row_w = name_width + cell_w * len(current_images)
            row_h = cell_h + row_pad * 2
            row_img = Image.new("RGB", (row_w, row_h), (255, 255, 255))

            if request.show_filename:
                label = material.upper()
                # Scale font down if rotated text would exceed row height
                fit_font = title_font
                for try_size in range(title_font.size, 6, -2):
                    test_font = _load_font(try_size)
                    test_bbox = test_font.getbbox(label)
                    if test_bbox[2] - test_bbox[0] + 12 <= row_h:
                        fit_font = test_font
                        break
                bbox = fit_font.getbbox(label)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                # Use generous padding to avoid clipping from font internal margins
                pad = 12
                cw, ch = tw + pad * 2, th + pad * 2
                text_img = Image.new("RGBA", (cw, ch), (255, 255, 255, 0))
                text_draw = ImageDraw.Draw(text_img)
                text_draw.text((pad, pad), label, font=fit_font, fill=(0, 0, 0))
                rotated = text_img.rotate(90, expand=True)
                row_img.paste(rotated, ((name_width - rotated.width) // 2, (row_h - rotated.height) // 2), rotated)

            for idx, image in enumerate(current_images):
                x = name_width + idx * cell_w
                row_img.paste(image, (x, row_pad))
                image.close()
            processed_rows.append(row_img)

        if not processed_rows:
            raise ValueError("No comparison rows were generated.")

        total_width = processed_rows[0].width
        merged_height = sum(image.height for image in processed_rows) + header_height
        merged = Image.new("RGB", (total_width, merged_height), (255, 255, 255))
        current_y = 0

        if request.show_label:
            header_font = _load_font(14)
            header = Image.new("RGB", (total_width, header_height), (240, 240, 240))
            draw = ImageDraw.Draw(header)
            sample_width = processed_rows[0].width - name_width
            col_width = sample_width // len(valid_columns) if valid_columns else 0
            for idx, (label, _directory) in enumerate(valid_columns):
                bbox = draw.textbbox((0, 0), label, font=header_font)
                text_w = bbox[2] - bbox[0]
                text_x = name_width + idx * col_width + (col_width - text_w) / 2
                text_y = (header_height - (bbox[3] - bbox[1])) / 2
                draw.text((text_x, text_y), label, fill=(0, 0, 0), font=header_font)
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
