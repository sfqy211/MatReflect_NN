from __future__ import annotations

import asyncio
import locale
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from backend.core.config import LOGS_ROOT, OUTPUTS_ROOT, PROJECT_ROOT, RUNTIME_ROOT
from backend.core.paths import get_mitsuba_paths
from backend.models.common import FileListItem, TaskDetailResponse
from backend.models.render import (
    RenderBatchRequest,
    RenderConvertRequest,
    RenderFilesResponse,
    RenderMode,
    RenderOutputFilesResponse,
    RenderSceneItem,
    RenderScenesResponse,
)
from backend.services.file_service import build_preview_url
from backend.services.task_manager import task_manager


MERL_STANDARD_FILE_SIZE = 12 + 90 * 90 * 180 * 3 * 8
MERL_FULL_FILE_SIZE = 12 + 90 * 90 * 360 * 3 * 8
TEMP_XML_ROOT = RUNTIME_ROOT / "render_xml"
TEMP_XML_ROOT.mkdir(parents=True, exist_ok=True)


def decode_subprocess_output(raw: bytes | str | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    preferred = locale.getpreferredencoding(False) or "utf-8"
    candidates: list[str] = []
    for encoding in ("utf-8", preferred, "gb18030", "cp936"):
        if encoding and encoding.lower() not in {candidate.lower() for candidate in candidates}:
            candidates.append(encoding)
    for encoding in candidates:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect_merl_variant(file_path: Path) -> str | None:
    try:
        file_size = file_path.stat().st_size
    except OSError:
        return None
    if file_size == MERL_STANDARD_FILE_SIZE:
        return "merl"
    if file_size == MERL_FULL_FILE_SIZE:
        return "fullmerl"
    return None


def has_merl_accelerated(mitsuba_dir: Path) -> bool:
    return (mitsuba_dir / "plugins" / "merl_accelerated.dll").exists()


def get_scene_search_dirs() -> list[Path]:
    return [
        PROJECT_ROOT / "scene" / "dj_xml",
        PROJECT_ROOT / "scene" / "old_xml",
    ]


def list_scene_xmls() -> list[Path]:
    results: list[Path] = []
    for scene_dir in get_scene_search_dirs():
        if scene_dir.exists():
            results.extend(sorted(scene_dir.glob("*.xml")))
    return results


def get_default_scene_path() -> Path | None:
    preferred = PROJECT_ROOT / "scene" / "old_xml" / "scene_merl.xml"
    if preferred.exists():
        return preferred
    fallback = PROJECT_ROOT / "scene" / "scene_merl.xml"
    if fallback.exists():
        return fallback
    candidates = list_scene_xmls()
    return candidates[0] if candidates else None


def normalize_npy_base_path(file_path: Path) -> str:
    base_path = str(file_path)
    if base_path.endswith("fc1.npy"):
        return base_path[:-7]
    if base_path.endswith(".npy"):
        return base_path[:-4]
    return base_path


def split_rgb_base_paths(base_path: str) -> tuple[str, str, str]:
    trimmed = base_path[:-1] if base_path.endswith("_") else base_path
    tail = os.path.basename(trimmed).lower()
    if tail.endswith("_r") or tail.endswith("_g") or tail.endswith("_b"):
        prefix = trimmed[:-2]
        return f"{prefix}_r", f"{prefix}_g", f"{prefix}_b"
    return trimmed, trimmed, trimmed


def is_placeholder_value(value: str | None) -> bool:
    return isinstance(value, str) and value.strip().startswith("$")


def resolve_scene_resource(scene_dir: Path, value: str) -> Path:
    cleaned = value.replace("\\", "/")
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    candidates = [
        (scene_dir / cleaned).resolve(),
        (PROJECT_ROOT / cleaned).resolve(),
        (PROJECT_ROOT / "scene" / cleaned).resolve(),
        (scene_dir / Path(cleaned).name).resolve(),
    ]
    if "dj_xml/" in cleaned:
        candidates.append((scene_dir / cleaned.split("dj_xml/")[-1]).resolve())
    if "old_xml/" in cleaned:
        candidates.append((scene_dir / cleaned.split("old_xml/")[-1]).resolve())
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def ensure_hdr_film(root: ET.Element) -> None:
    film_node = root.find(".//film")
    if film_node is not None and film_node.get("type") == "ldrfilm":
        film_node.set("type", "hdrfilm")


def find_target_bsdf(root: ET.Element) -> ET.Element | None:
    for bsdf in root.iter("bsdf"):
        if bsdf.get("id") == "Material":
            return bsdf
    preferred_types = {
        "merl",
        "fullmerl",
        "nbrdf_npy",
        "merl_accelerated",
        "SIREN_h21l5_nbrdf_npy",
        "SIREN_gray_h21l5_nbrdf_npy",
    }
    for bsdf in root.iter("bsdf"):
        if bsdf.get("type") in preferred_types:
            return bsdf
    return None


def configure_bsdf_smart(bsdf_node: ET.Element, filename: str) -> None:
    for child in list(bsdf_node):
        if child.tag == "bsdf":
            bsdf_node.remove(child)
    name = filename.lower()
    is_metal = False
    metal_material = "Cu"
    if "gold" in name:
        is_metal = True
        metal_material = "Au"
    elif "silver" in name:
        is_metal = True
        metal_material = "Ag"
    elif "aluminium" in name or "alum-" in name:
        is_metal = True
        metal_material = "Al"
    elif "chrome" in name or "steel" in name or "ss440" in name:
        is_metal = True
        metal_material = "Cr"
    elif "nickel" in name:
        is_metal = True
        metal_material = "Cr"
    elif "tungsten" in name:
        is_metal = True
        metal_material = "W"
    elif "brass" in name or "bronze" in name or "copper" in name:
        is_metal = True
        metal_material = "Cu"
    elif "hematite" in name:
        is_metal = True
        metal_material = "Cr"
    elif "metallic" in name:
        is_metal = True
        metal_material = "Al"
    if is_metal:
        guide = ET.SubElement(bsdf_node, "bsdf", {"type": "roughconductor"})
        ET.SubElement(guide, "string", {"name": "material", "value": metal_material})
        alpha_val = "0.02"
        if "mirror" in name or "polished" in name or "smooth" in name or "specular" in name:
            alpha_val = "0.005"
        elif "chrome" in name or "steel" in name or "silver" in name or "gold" in name:
            alpha_val = "0.01"
        elif "alum" in name or "aluminium" in name or "aluminum" in name:
            alpha_val = "0.015"
        elif "brushed" in name or "matte" in name or "satin" in name:
            alpha_val = "0.05"
        elif "rough" in name:
            alpha_val = "0.1"
        ET.SubElement(guide, "float", {"name": "alpha", "value": alpha_val})
        return
    guide = ET.SubElement(bsdf_node, "bsdf", {"type": "roughplastic"})
    ET.SubElement(guide, "string", {"name": "intIOR", "value": "polypropylene"})
    ET.SubElement(guide, "spectrum", {"name": "diffuseReflectance", "value": "0.5 0.5 0.5"})
    ET.SubElement(guide, "float", {"name": "alpha", "value": "0.1"})


def update_bsdf_for_mode(
    bsdf_node: ET.Element,
    render_mode: RenderMode,
    file_path: Path,
    filename: str,
    mitsuba_dir: Path,
) -> str:
    existing_type = bsdf_node.get("type", "")
    name_keys = {"filename", "binary", "nn_basename", "nn_basename_r", "nn_basename_g", "nn_basename_b"}
    for child in list(bsdf_node):
        if child.get("name") in name_keys:
            bsdf_node.remove(child)
    if render_mode == "brdfs":
        if existing_type == "merl_accelerated" and has_merl_accelerated(mitsuba_dir):
            bsdf_node.set("type", "merl_accelerated")
            ET.SubElement(bsdf_node, "string", {"name": "filename", "value": str(file_path).replace("\\", "/")})
            selected_type = "merl_accelerated"
        else:
            bsdf_node.set("type", "merl")
            ET.SubElement(bsdf_node, "string", {"name": "binary", "value": str(file_path).replace("\\", "/")})
            selected_type = "merl"
        configure_bsdf_smart(bsdf_node, filename)
        return selected_type
    if render_mode == "fullbin":
        detected_type = detect_merl_variant(file_path)
        if detected_type == "merl":
            bsdf_node.set("type", "merl")
            ET.SubElement(bsdf_node, "string", {"name": "binary", "value": str(file_path).replace("\\", "/")})
        else:
            bsdf_node.set("type", "fullmerl")
            ET.SubElement(bsdf_node, "string", {"name": "filename", "value": str(file_path).replace("\\", "/")})
        configure_bsdf_smart(bsdf_node, filename)
        return detected_type or "fullmerl_unknown"
    base_path = normalize_npy_base_path(file_path)
    for child in list(bsdf_node):
        if child.tag == "bsdf":
            bsdf_node.remove(child)
    if existing_type == "SIREN_gray_h21l5_nbrdf_npy":
        bsdf_node.set("type", existing_type)
        r_path, g_path, b_path = split_rgb_base_paths(base_path)
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename_r", "value": r_path})
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename_g", "value": g_path})
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename_b", "value": b_path})
    else:
        bsdf_node.set("type", existing_type if existing_type.startswith("SIREN_") else "nbrdf_npy")
        ET.SubElement(bsdf_node, "string", {"name": "nn_basename", "value": base_path})
    if not any(child.get("name") == "reflectance" for child in bsdf_node):
        ET.SubElement(bsdf_node, "spectrum", {"name": "reflectance", "value": "0.5"})
    return bsdf_node.get("type", "nbrdf_npy")


def update_integrator_and_sampler(root: ET.Element, integrator_type: str, sample_count: int) -> None:
    integrator_node = root.find("integrator")
    if integrator_node is not None:
        integrator_node.set("type", integrator_type)
    sampler_node = root.find(".//sampler")
    if sampler_node is None:
        return
    for int_node in sampler_node.findall("integer"):
        if int_node.get("name") == "sampleCount":
            int_node.set("value", str(sample_count))
            return


class RenderService:
    def __init__(self) -> None:
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    def _input_dir(self, render_mode: RenderMode) -> Path:
        return {
            "brdfs": PROJECT_ROOT / "data" / "inputs" / "binary",
            "fullbin": PROJECT_ROOT / "data" / "inputs" / "fullbin",
            "npy": PROJECT_ROOT / "data" / "inputs" / "npy",
        }[render_mode]

    def _output_dir(self, render_mode: RenderMode) -> Path:
        return {
            "brdfs": OUTPUTS_ROOT / "binary",
            "fullbin": OUTPUTS_ROOT / "fullbin",
            "npy": OUTPUTS_ROOT / "npy",
        }[render_mode]

    def _output_path_key(self, render_mode: RenderMode) -> str:
        return {
            "brdfs": "render_outputs_binary_png",
            "fullbin": "render_outputs_fullbin_png",
            "npy": "render_outputs_npy_png",
        }[render_mode]

    def list_scenes(self) -> RenderScenesResponse:
        default_scene = get_default_scene_path()
        items = [
            RenderSceneItem(
                label=scene_path.name,
                path=scene_path.as_posix(),
                is_default=default_scene == scene_path,
            )
            for scene_path in list_scene_xmls()
        ]
        return RenderScenesResponse(
            default_scene=default_scene.as_posix() if default_scene else None,
            items=items,
        )

    def list_input_files(self, render_mode: RenderMode, page: int = 1, page_size: int = 200, search: str = "") -> RenderFilesResponse:
        input_dir = self._input_dir(render_mode)
        input_dir.mkdir(parents=True, exist_ok=True)
        if render_mode == "npy":
            entries = sorted(input_dir.glob("*fc1.npy"))
        elif render_mode == "brdfs":
            entries = sorted(input_dir.glob("*.binary"))
        else:
            entries = sorted(input_dir.glob("*.fullbin"))
        if search:
            entries = [entry for entry in entries if search.lower() in entry.name.lower()]
        total = len(entries)
        paged = entries[(page - 1) * page_size : page * page_size]
        items = [
            FileListItem(
                name=entry.name,
                path=str(entry.resolve()),
                size=entry.stat().st_size,
                modified_at=datetime.fromtimestamp(entry.stat().st_mtime),
                is_dir=False,
            )
            for entry in paged
        ]
        return RenderFilesResponse(
            render_mode=render_mode,
            input_dir=str(input_dir.resolve()),
            total=total,
            items=items,
        )

    def list_output_files(self, render_mode: RenderMode, page: int = 1, page_size: int = 24) -> RenderOutputFilesResponse:
        output_dir = self._output_dir(render_mode) / "png"
        output_dir.mkdir(parents=True, exist_ok=True)
        entries = sorted(output_dir.glob("*.png"), key=lambda entry: entry.stat().st_mtime, reverse=True)
        total = len(entries)
        paged = entries[(page - 1) * page_size : page * page_size]
        items = [
            FileListItem(
                name=entry.name,
                path=str(entry.resolve()),
                size=entry.stat().st_size,
                modified_at=datetime.fromtimestamp(entry.stat().st_mtime),
                is_dir=False,
                preview_url=build_preview_url(entry),
            )
            for entry in paged
        ]
        return RenderOutputFilesResponse(
            render_mode=render_mode,
            path_key=self._output_path_key(render_mode),
            resolved_path=str(output_dir.resolve()),
            total=total,
            items=items,
        )

    def _resolve_scene_path(self, requested_path: str) -> Path:
        candidates = list_scene_xmls()
        if not candidates:
            raise FileNotFoundError("No scene xml found")
        requested = Path(requested_path)
        for candidate in candidates:
            if requested == candidate or requested.as_posix() == candidate.as_posix():
                return candidate
            try:
                if requested.as_posix() == candidate.relative_to(PROJECT_ROOT).as_posix():
                    return candidate
            except ValueError:
                continue
        raise FileNotFoundError(f"Unknown scene path: {requested_path}")

    def _parse_progress(self, line: str, index: int, total: int) -> int | None:
        if "Rendering: [" not in line:
            return None
        match = re.search(r"\[(.+)\]", line)
        if not match:
            return None
        content = match.group(1)
        total_width = len(content)
        if total_width == 0:
            return None
        done_count = content.count("+")
        percent = done_count / total_width
        overall_percent = (index + percent) / total
        return min(99, int(overall_percent * 100))

    async def _write_log(self, task_id: str, log_path: Path, message: str, *, status: str | None = None, progress: int | None = None, event: str = "log", result_payload: dict | None = None) -> None:
        clean_message = message.replace("\r", "").replace("\b", "")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(clean_message + "\n")
        await task_manager.update(
            task_id,
            status=status,
            progress=progress,
            message=clean_message,
            log_path=str(log_path),
            result_payload=result_payload,
            event=event,
        )

    async def start_batch(self, request: RenderBatchRequest):
        log_path = LOGS_ROOT / f"render_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("render", "Render task queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_batch(record.task_id, request, log_path, cancel_event))
        return record

    async def stop_task(self, task_id: str) -> bool:
        record = task_manager.get(task_id)
        if record is None:
            return False
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event is not None:
            cancel_event.set()
        process = self._processes.get(task_id)
        if process and process.returncode is None:
            process.terminate()
        await task_manager.update(task_id, status="cancelled", message="Cancellation requested", event="log")
        return True

    async def start_convert(self, request: RenderConvertRequest):
        log_path = LOGS_ROOT / f"convert_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("convert", "Convert task queued", log_path=str(log_path))
        asyncio.create_task(self._run_convert(record.task_id, request, log_path))
        return record

    def get_task_detail(self, task_id: str, limit: int = 200) -> TaskDetailResponse | None:
        record = task_manager.get(task_id)
        if record is None:
            return None
        logs: list[str] = []
        if record.log_path and Path(record.log_path).exists():
            lines = Path(record.log_path).read_text(encoding="utf-8", errors="replace").splitlines()
            logs = lines[-limit:]
        return TaskDetailResponse(record=record, logs=logs)

    async def _run_batch(self, task_id: str, request: RenderBatchRequest, log_path: Path, cancel_event: asyncio.Event) -> None:
        try:
            scene_path = self._resolve_scene_path(request.scene_path)
            input_dir = self._input_dir(request.render_mode)
            output_dir = self._output_dir(request.render_mode)
            output_dir.mkdir(parents=True, exist_ok=True)
            exr_dir = output_dir / "exr"
            png_dir = output_dir / "png"
            exr_dir.mkdir(parents=True, exist_ok=True)
            png_dir.mkdir(parents=True, exist_ok=True)

            if not request.selected_files:
                await self._write_log(task_id, log_path, "未选择渲染文件", status="failed", progress=100, event="done")
                return

            paths = get_mitsuba_paths()
            mitsuba_exe = paths["mitsuba_exe"]
            mtsutil_exe = paths["mtsutil_exe"]
            mitsuba_dir = paths["mitsuba_dir"]
            if not mitsuba_exe.exists():
                await self._write_log(task_id, log_path, f"未找到 Mitsuba 可执行文件: {mitsuba_exe}", status="failed", progress=100, event="done")
                return

            scene_xml_text = scene_path.read_text(encoding="utf-8")
            timestamp = datetime.now().strftime("%d_%H%M%S")
            total = len(request.selected_files)
            generated_pngs: list[str] = []

            await self._write_log(task_id, log_path, "渲染任务已启动", status="running", progress=0)

            for index, filename in enumerate(request.selected_files):
                if cancel_event.is_set():
                    await self._write_log(task_id, log_path, "渲染已停止", status="cancelled", progress=min(99, int(index / total * 100)), event="done")
                    return

                file_path = input_dir / filename
                if not file_path.exists():
                    await self._write_log(task_id, log_path, f"跳过不存在的输入文件: {filename}")
                    continue

                basename = file_path.stem
                exr_out = exr_dir / f"{basename}_{timestamp}.exr"
                png_out = png_dir / f"{basename}_{timestamp}.png"

                if request.skip_existing:
                    target_dir = png_dir if request.auto_convert else exr_dir
                    suffix = ".png" if request.auto_convert else ".exr"
                    if any(
                        (entry.stem == basename or entry.stem.startswith(f"{basename}_")) and entry.suffix.lower() == suffix
                        for entry in target_dir.glob(f"*{suffix}")
                    ):
                        await self._write_log(
                            task_id,
                            log_path,
                            f"[{index + 1}/{total}] 跳过已存在结果: {basename}",
                            progress=min(99, int((index + 1) / total * 100)),
                        )
                        continue

                root = ET.fromstring(scene_xml_text)
                update_integrator_and_sampler(root, request.integrator_type, request.sample_count)
                ensure_hdr_film(root)
                scene_dir = scene_path.parent

                for string_node in root.iter("string"):
                    if string_node.get("name") == "filename":
                        value = string_node.get("value")
                        if value and not os.path.isabs(value) and not is_placeholder_value(value):
                            resolved = resolve_scene_resource(scene_dir, value)
                            string_node.set("value", resolved.as_posix())

                target_bsdf = find_target_bsdf(root)
                if target_bsdf is None:
                    await self._write_log(task_id, log_path, "场景中未找到可替换材质节点", status="failed", progress=100, event="done")
                    return

                selected_type = update_bsdf_for_mode(target_bsdf, request.render_mode, file_path, filename, mitsuba_dir)
                tree = ET.ElementTree(root)
                temp_xml = TEMP_XML_ROOT / f"{basename}_{timestamp}_{index}.xml"
                tree.write(temp_xml, encoding="utf-8", xml_declaration=True)

                if request.custom_cmd:
                    final_cmd = (
                        request.custom_cmd.replace("{mitsuba}", mitsuba_exe.as_posix())
                        .replace("{input}", temp_xml.as_posix())
                        .replace("{output}", exr_out.as_posix())
                    )
                    cmd = final_cmd.split()
                else:
                    cmd = [str(mitsuba_exe), "-o", str(exr_out), str(temp_xml)]

                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                env["PATH"] = str(mitsuba_dir) + os.pathsep + env.get("PATH", "")
                await self._write_log(task_id, log_path, f"[{index + 1}/{total}] 渲染 {filename} ({selected_type})")

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env,
                )
                self._processes[task_id] = process

                while True:
                    if cancel_event.is_set():
                        if process.returncode is None:
                            process.terminate()
                            await process.wait()
                        await self._write_log(task_id, log_path, "渲染已停止", status="cancelled", progress=min(99, int(index / total * 100)), event="done")
                        return
                    try:
                        line = (
                            await asyncio.wait_for(process.stdout.readline(), timeout=0.5)
                            if process.stdout
                            else b""
                        )
                    except asyncio.TimeoutError:
                        if process.returncode is not None:
                            break
                        continue
                    if not line:
                        if process.returncode is None:
                            await asyncio.sleep(0.1)
                            continue
                        break
                    text = decode_subprocess_output(line).strip()
                    if text:
                        parsed_progress = self._parse_progress(text, index, total)
                        await self._write_log(task_id, log_path, text, progress=parsed_progress)

                return_code = await process.wait()
                self._processes.pop(task_id, None)
                if return_code != 0:
                    await self._write_log(task_id, log_path, f"渲染失败，退出码: {return_code}", status="failed", progress=100, event="done")
                    return

                if exr_out.exists():
                    await self._write_log(task_id, log_path, f"EXR 输出完成: {exr_out.name}")
                    if request.auto_convert:
                        if not mtsutil_exe.exists():
                            await self._write_log(task_id, log_path, f"未找到 mtsutil: {mtsutil_exe}")
                        else:
                            convert_process = await asyncio.create_subprocess_exec(
                                str(mtsutil_exe),
                                "tonemap",
                                "-o",
                                str(png_out),
                                str(exr_out),
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.STDOUT,
                                env=env,
                            )
                            convert_output, _ = await convert_process.communicate()
                            text = decode_subprocess_output(convert_output).strip()
                            if text:
                                await self._write_log(task_id, log_path, text)
                            if convert_process.returncode == 0 and png_out.exists():
                                generated_pngs.append(png_out.name)
                                await self._write_log(task_id, log_path, f"PNG 输出完成: {png_out.name}")
                else:
                    fallback_png = exr_out.with_suffix(".png")
                    if fallback_png.exists():
                        fallback_png.replace(png_out)
                        generated_pngs.append(png_out.name)
                        await self._write_log(task_id, log_path, f"PNG 输出完成: {png_out.name}")
                    else:
                        await self._write_log(task_id, log_path, "未找到 EXR/PNG 输出")

                await task_manager.update(
                    task_id,
                    status="running",
                    progress=min(99, int((index + 1) / total * 100)),
                    message=f"已完成 {index + 1}/{total}: {filename}",
                    result_payload={
                        "render_mode": request.render_mode,
                        "output_path_key": self._output_path_key(request.render_mode),
                        "generated_pngs": generated_pngs,
                    },
                    event="log",
                )

            await self._write_log(
                task_id,
                log_path,
                "渲染任务完成",
                status="success",
                progress=100,
                event="done",
                result_payload={
                    "render_mode": request.render_mode,
                    "output_path_key": self._output_path_key(request.render_mode),
                    "generated_pngs": generated_pngs,
                },
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"渲染任务异常: {exc}", status="failed", progress=100, event="done")
        finally:
            self._processes.pop(task_id, None)
            self._cancel_events.pop(task_id, None)

    async def _run_convert(self, task_id: str, request: RenderConvertRequest, log_path: Path) -> None:
        try:
            paths = get_mitsuba_paths()
            mtsutil_exe = paths["mtsutil_exe"]
            if not mtsutil_exe.exists():
                await self._write_log(task_id, log_path, f"未找到 mtsutil: {mtsutil_exe}", status="failed", progress=100, event="done")
                return
            output_dir = self._output_dir(request.render_mode)
            exr_dir = output_dir / "exr"
            png_dir = output_dir / "png"
            png_dir.mkdir(parents=True, exist_ok=True)
            candidates = sorted(exr_dir.glob("*.exr"))
            if request.filenames:
                requested = set(request.filenames)
                candidates = [entry for entry in candidates if entry.name in requested]
            if not candidates:
                await self._write_log(task_id, log_path, "没有可转换的 EXR 文件", status="failed", progress=100, event="done")
                return
            await self._write_log(task_id, log_path, "EXR 转 PNG 已启动", status="running", progress=0)
            total = len(candidates)
            generated_pngs: list[str] = []
            for index, entry in enumerate(candidates):
                png_out = png_dir / f"{entry.stem}.png"
                process = await asyncio.create_subprocess_exec(
                    str(mtsutil_exe),
                    "tonemap",
                    "-o",
                    str(png_out),
                    str(entry),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                output, _ = await process.communicate()
                text = decode_subprocess_output(output).strip()
                if text:
                    await self._write_log(task_id, log_path, text)
                if process.returncode == 0 and png_out.exists():
                    generated_pngs.append(png_out.name)
                    await self._write_log(task_id, log_path, f"已转换: {entry.name}", progress=min(99, int((index + 1) / total * 100)))
                else:
                    await self._write_log(task_id, log_path, f"转换失败: {entry.name}")
            await self._write_log(
                task_id,
                log_path,
                "EXR 转 PNG 完成",
                status="success",
                progress=100,
                event="done",
                result_payload={
                    "render_mode": request.render_mode,
                    "output_path_key": self._output_path_key(request.render_mode),
                    "generated_pngs": generated_pngs,
                },
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"转换任务异常: {exc}", status="failed", progress=100, event="done")


render_service = RenderService()
