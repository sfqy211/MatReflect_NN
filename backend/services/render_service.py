from __future__ import annotations

import asyncio
import locale
import os
import re
import shutil
import subprocess
import sys
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
    RenderReconstructRequest,
    RenderSceneItem,
    RenderScenesResponse,
)
from backend.models.train import TrainProjectVariant
from backend.services.file_service import build_preview_url
from backend.services.task_manager import task_manager


MERL_STANDARD_FILE_SIZE = 12 + 90 * 90 * 180 * 3 * 8
MERL_FULL_FILE_SIZE = 12 + 90 * 90 * 360 * 3 * 8
TEMP_XML_ROOT = RUNTIME_ROOT / "render_xml"
TEMP_XML_ROOT.mkdir(parents=True, exist_ok=True)

NEURAL_BRDF_DIR = PROJECT_ROOT / "Neural-BRDF"
HYPER_BRDF_DIR = PROJECT_ROOT / "HyperBRDF"
DATA_INPUTS_NPY = PROJECT_ROOT / "data" / "inputs" / "npy"
DATA_INPUTS_FULLBIN = PROJECT_ROOT / "data" / "inputs" / "fullbin"
BINARY_TO_NBRDF_DIR = NEURAL_BRDF_DIR / "binary_to_nbrdf"
PYTORCH_SCRIPT = BINARY_TO_NBRDF_DIR / "pytorch_code" / "train_NBRDF_pytorch.py"

HB_RENDER_PROJECTS: dict[TrainProjectVariant, dict[str, Path | str]] = {
    "hyperbrdf": {
        "label": "HyperBRDF",
        "dir": HYPER_BRDF_DIR,
        "test_script": HYPER_BRDF_DIR / "test.py",
        "pt_to_fullbin_script": HYPER_BRDF_DIR / "pt_to_fullmerl.py",
    },
}


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


def ensure_exists(path: Path, *, file_ok: bool = False) -> None:
    if file_ok:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        return
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(path)


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


def get_default_scene_path(render_mode: RenderMode = "brdfs") -> Path | None:
    preferred_candidates: list[Path] = []
    if render_mode == "fullbin":
        preferred_candidates.append(PROJECT_ROOT / "scene" / "dj_xml" / "hyperbrdf_ref.xml")
        preferred_candidates.append(PROJECT_ROOT / "scene" / "dj_xml" / "scene_universal.xml")
    else:
        preferred_candidates.append(PROJECT_ROOT / "scene" / "dj_xml" / "scene_universal.xml")
        if render_mode == "npy":
            preferred_candidates.append(PROJECT_ROOT / "scene" / "dj_xml" / "scene_test_nbrdf_npy.xml")
        else:
            preferred_candidates.append(PROJECT_ROOT / "scene" / "dj_xml" / "scene_test_merl_accelerated.xml")
    preferred_candidates.extend(
        [
            PROJECT_ROOT / "scene" / "old_xml" / "scene_merl.xml",
            PROJECT_ROOT / "scene" / "scene_merl.xml",
        ]
    )
    for candidate in preferred_candidates:
        if candidate.exists():
            return candidate
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
    for bsdf in root.iter("bsdf"):
        if bsdf.get("type") in {"merl", "fullmerl", "nbrdf_npy", "merl_accelerated", "SIREN_h21l5_nbrdf_npy", "SIREN_gray_h21l5_nbrdf_npy"}:
            return bsdf
    return None


def configure_bsdf_smart(bsdf_node: ET.Element, filename: str) -> None:
    for child in list(bsdf_node):
        if child.tag == "bsdf":
            bsdf_node.remove(child)
    guide = ET.SubElement(bsdf_node, "bsdf", {"type": "roughplastic"})
    ET.SubElement(guide, "string", {"name": "intIOR", "value": "polypropylene"})
    ET.SubElement(guide, "spectrum", {"name": "diffuseReflectance", "value": "0.5 0.5 0.5"})
    alpha = "0.1"
    lowered = filename.lower()
    if any(token in lowered for token in ("chrome", "steel", "gold", "silver", "mirror")):
        guide.set("type", "roughconductor")
        for child in list(guide):
            guide.remove(child)
        ET.SubElement(guide, "string", {"name": "material", "value": "Cr"})
        alpha = "0.01"
    ET.SubElement(guide, "float", {"name": "alpha", "value": alpha})


def update_bsdf_for_mode(
    bsdf_node: ET.Element,
    render_mode: RenderMode,
    file_path: Path,
    filename: str,
    mitsuba_dir: Path,
) -> str:
    existing_type = bsdf_node.get("type", "")
    for child in list(bsdf_node):
        if child.get("name") in {"filename", "binary", "nn_basename", "nn_basename_r", "nn_basename_g", "nn_basename_b"}:
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
        if detect_merl_variant(file_path) == "merl":
            bsdf_node.set("type", "merl")
            ET.SubElement(bsdf_node, "string", {"name": "binary", "value": str(file_path).replace("\\", "/")})
            selected_type = "merl"
        else:
            bsdf_node.set("type", "fullmerl")
            ET.SubElement(bsdf_node, "string", {"name": "filename", "value": str(file_path).replace("\\", "/")})
            selected_type = "fullmerl"
        configure_bsdf_smart(bsdf_node, filename)
        return selected_type
    base_path = normalize_npy_base_path(file_path)
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

    def _project_config(self, project_variant: TrainProjectVariant) -> dict[str, Path | str]:
        return HB_RENDER_PROJECTS[project_variant]

    def _default_conda_env(self, project_variant: TrainProjectVariant) -> str:
        return "hyperbrdf"

    def _make_hyper_env(self, project_variant: TrainProjectVariant) -> dict[str, str]:
        config = self._project_config(project_variant)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([str(PROJECT_ROOT), str(config["dir"]), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        return env

    def _make_neural_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([str(BINARY_TO_NBRDF_DIR), str(PYTORCH_SCRIPT.parent), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        return env

    def _python_runner(self, conda_env: str | None = None) -> tuple[list[str], bool]:
        conda = shutil.which("conda")
        if conda and conda_env:
            return [conda, "run", "--no-capture-output", "-n", conda_env, "python"], True
        return [sys.executable], False

    def list_scenes(self, render_mode: RenderMode = "brdfs") -> RenderScenesResponse:
        default_scene = get_default_scene_path(render_mode)
        return RenderScenesResponse(
            default_scene=default_scene.as_posix() if default_scene else None,
            items=[
                RenderSceneItem(label=scene_path.name, path=scene_path.as_posix(), is_default=scene_path == default_scene)
                for scene_path in list_scene_xmls()
            ],
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
        paged = entries[(page - 1) * page_size : page * page_size]
        return RenderFilesResponse(
            render_mode=render_mode,
            input_dir=str(input_dir.resolve()),
            total=len(entries),
            items=[
                FileListItem(
                    name=entry.name,
                    path=str(entry.resolve()),
                    size=entry.stat().st_size,
                    modified_at=datetime.fromtimestamp(entry.stat().st_mtime),
                    is_dir=False,
                )
                for entry in paged
            ],
        )

    def list_output_files(self, render_mode: RenderMode, page: int = 1, page_size: int = 24) -> RenderOutputFilesResponse:
        output_dir = self._output_dir(render_mode) / "png"
        output_dir.mkdir(parents=True, exist_ok=True)
        entries = sorted(output_dir.glob("*.png"), key=lambda entry: entry.stat().st_mtime, reverse=True)
        paged = entries[(page - 1) * page_size : page * page_size]
        return RenderOutputFilesResponse(
            render_mode=render_mode,
            path_key=self._output_path_key(render_mode),
            resolved_path=str(output_dir.resolve()),
            total=len(entries),
            items=[
                FileListItem(
                    name=entry.name,
                    path=str(entry.resolve()),
                    size=entry.stat().st_size,
                    modified_at=datetime.fromtimestamp(entry.stat().st_mtime),
                    is_dir=False,
                    preview_url=build_preview_url(entry),
                )
                for entry in paged
            ],
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
        return min(99, int(((index + content.count("+") / total_width) / total) * 100))

    async def _write_log(
        self,
        task_id: str,
        log_path: Path,
        message: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        event: str = "log",
        result_payload: dict | None = None,
    ) -> None:
        clean_message = message.replace("\r", "").replace("\b", "")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(clean_message + "\n")
        await task_manager.update(task_id, status=status, progress=progress, message=clean_message, log_path=str(log_path), result_payload=result_payload, event=event)

    async def _run_command(
        self,
        task_id: str,
        log_path: Path,
        cmd: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        progress: int | None = None,
        start_message: str,
        use_shell: bool = False,
        cancel_event: asyncio.Event | None = None,
    ) -> int:
        await self._write_log(task_id, log_path, start_message, status="running", progress=progress)
        if use_shell:
            process = await asyncio.create_subprocess_shell(subprocess.list2cmdline(cmd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=str(cwd), env=env)
        else:
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=str(cwd), env=env)
        self._processes[task_id] = process
        try:
            while True:
                if cancel_event and cancel_event.is_set():
                    if process.returncode is None:
                        process.terminate()
                        await process.wait()
                    return -1
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.5) if process.stdout else b""
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
                    await self._write_log(task_id, log_path, text, progress=progress)
            return await process.wait()
        finally:
            self._processes.pop(task_id, None)

    async def start_batch(self, request: RenderBatchRequest):
        log_path = LOGS_ROOT / f"render_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("render", "Render task queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_batch(record.task_id, request, log_path, cancel_event))
        return record

    async def start_reconstruct(self, request: RenderReconstructRequest):
        log_path = LOGS_ROOT / f"render_reconstruct_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("render_reconstruct", "Reconstruct task queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_reconstruct(record.task_id, request, log_path, cancel_event))
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
            logs = Path(record.log_path).read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        return TaskDetailResponse(record=record, logs=logs)

    async def _run_batch(self, task_id: str, request: RenderBatchRequest, log_path: Path, cancel_event: asyncio.Event) -> None:
        try:
            await self._execute_render_batch(task_id, request, log_path, cancel_event)
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Render task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)
            self._processes.pop(task_id, None)

    async def _run_reconstruct(self, task_id: str, request: RenderReconstructRequest, log_path: Path, cancel_event: asyncio.Event) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            ensure_exists(merl_dir)
            if not request.selected_materials:
                await self._write_log(task_id, log_path, "No MERL materials selected", status="failed", progress=100, event="done")
                return

            if request.model_key == "neural":
                output_dir = Path(request.output_dir).resolve() if request.output_dir else DATA_INPUTS_NPY
                output_dir.mkdir(parents=True, exist_ok=True)
                env = self._make_neural_env()
                runner, use_shell = self._python_runner("nbrdf-train")
                generated_files: list[str] = []
                total = len(request.selected_materials)
                for index, material in enumerate(request.selected_materials):
                    binary_path = merl_dir / material
                    ensure_exists(binary_path, file_ok=True)
                    cmd = [*runner, str(PYTORCH_SCRIPT), str(binary_path), "--outpath", str(output_dir), "--epochs", str(request.neural_epochs), "--device", request.neural_device]
                    return_code = await self._run_command(task_id, log_path, cmd, cwd=PYTORCH_SCRIPT.parent, env=env, progress=min(95, int(index / total * 100)), start_message=f"[{index + 1}/{total}] Reconstruct NBRDF: {material}", use_shell=use_shell, cancel_event=cancel_event)
                    if return_code != 0:
                        await self._write_log(task_id, log_path, f"Neural reconstruction failed: {material}", status="failed", progress=100, event="done")
                        return
                    generated_files.append(f"{Path(material).stem}_fc1.npy")
                await self._write_log(task_id, log_path, "Neural-BRDF reconstruction completed", status="success", progress=100, event="done", result_payload={"pipeline": "reconstruct_only", "model_key": request.model_key, "output_dir": str(output_dir), "generated_files": generated_files})
                return

            project_variant = request.model_key
            config = self._project_config(project_variant)
            checkpoint_path = Path(request.checkpoint_path).resolve()
            ensure_exists(checkpoint_path, file_ok=True)
            output_dir = Path(request.output_dir).resolve() if request.output_dir else DATA_INPUTS_FULLBIN
            output_dir.mkdir(parents=True, exist_ok=True)
            pt_dir = (RUNTIME_ROOT / "render_pipeline" / task_id / "pt").resolve()
            pt_dir.mkdir(parents=True, exist_ok=True)
            env = self._make_hyper_env(project_variant)
            runner, use_shell = self._python_runner(request.conda_env or self._default_conda_env(project_variant))
            extracted_pts: list[str] = []
            total = len(request.selected_materials)

            for index, material in enumerate(request.selected_materials):
                binary_path = merl_dir / material
                ensure_exists(binary_path, file_ok=True)
                before_pts = {entry.name for entry in pt_dir.glob("*.pt")}
                cmd = [*runner, str(config["test_script"]), "--model", str(checkpoint_path), "--binary", str(binary_path), "--destdir", str(pt_dir), "--dataset", request.dataset]
                return_code = await self._run_command(task_id, log_path, cmd, cwd=Path(config["dir"]), env=env, progress=min(45, 5 + int(index / total * 40)), start_message=f"[{index + 1}/{total}] Extract PT: {material}", use_shell=use_shell, cancel_event=cancel_event)
                if return_code != 0:
                    await self._write_log(task_id, log_path, f"PT extraction failed: {material}", status="failed", progress=100, event="done")
                    return
                after_pts = {entry.name for entry in pt_dir.glob("*.pt")}
                extracted_pts.extend(sorted((after_pts - before_pts) or {f"{Path(material).stem}.pt"}))

            env["CUDA_VISIBLE_DEVICES"] = request.cuda_device
            generated_fullbins: list[str] = []
            total_pts = max(len(extracted_pts), 1)
            for index, pt_name in enumerate(extracted_pts):
                pt_path = pt_dir / pt_name
                ensure_exists(pt_path, file_ok=True)
                before_fullbins = {entry.name for entry in output_dir.glob("*.fullbin")}
                cmd = [*runner, str(config["pt_to_fullbin_script"]), str(pt_path), str(output_dir), "--dataset", request.dataset, "--cuda_device", request.cuda_device]
                return_code = await self._run_command(task_id, log_path, cmd, cwd=Path(config["dir"]), env=env, progress=min(95, 48 + int(index / total_pts * 47)), start_message=f"[{index + 1}/{total_pts}] Decode FullBin: {pt_name}", use_shell=use_shell, cancel_event=cancel_event)
                if return_code != 0:
                    await self._write_log(task_id, log_path, f"FullBin decode failed: {pt_name}", status="failed", progress=100, event="done")
                    return
                after_fullbins = {entry.name for entry in output_dir.glob("*.fullbin")}
                generated_fullbins.extend(sorted((after_fullbins - before_fullbins) or {f"{Path(pt_name).stem}.fullbin"}))

            if request.render_after_reconstruct:
                render_request = RenderBatchRequest(render_mode="fullbin", scene_path=request.scene_path, selected_files=generated_fullbins, integrator_type=request.integrator_type, sample_count=request.sample_count, auto_convert=request.auto_convert, skip_existing=request.skip_existing, custom_cmd=request.custom_cmd)
                await self._execute_render_batch(task_id, render_request, log_path, cancel_event, input_dir_override=output_dir, progress_offset=80, progress_span=20, start_message="Reconstruction finished. Start Mitsuba rendering.", result_payload_extra={"pipeline": "reconstruct_render", "model_key": request.model_key, "output_dir": str(output_dir)})
                return

            await self._write_log(task_id, log_path, f"{config['label']} reconstruction completed", status="success", progress=100, event="done", result_payload={"pipeline": "reconstruct_only", "model_key": request.model_key, "output_dir": str(output_dir), "generated_files": generated_fullbins})
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Reconstruct task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)
            self._processes.pop(task_id, None)

    async def _execute_render_batch(self, task_id: str, request: RenderBatchRequest, log_path: Path, cancel_event: asyncio.Event, *, input_dir_override: Path | None = None, progress_offset: int = 0, progress_span: int = 100, start_message: str = "Render task started", result_payload_extra: dict | None = None) -> None:
        scene_path = self._resolve_scene_path(request.scene_path)
        input_dir = input_dir_override or self._input_dir(request.render_mode)
        output_dir = self._output_dir(request.render_mode)
        exr_dir = output_dir / "exr"
        png_dir = output_dir / "png"
        exr_dir.mkdir(parents=True, exist_ok=True)
        png_dir.mkdir(parents=True, exist_ok=True)
        if not request.selected_files:
            await self._write_log(task_id, log_path, "No render inputs selected", status="failed", progress=100, event="done")
            return
        paths = get_mitsuba_paths()
        mitsuba_exe = paths["mitsuba_exe"]
        mtsutil_exe = paths["mtsutil_exe"]
        mitsuba_dir = paths["mitsuba_dir"]
        scene_xml_text = scene_path.read_text(encoding="utf-8")
        total = len(request.selected_files)
        generated_pngs: list[str] = []
        result_payload = {"render_mode": request.render_mode, "output_path_key": self._output_path_key(request.render_mode), "generated_pngs": generated_pngs, **(result_payload_extra or {})}
        await self._write_log(task_id, log_path, start_message, status="running", progress=progress_offset, result_payload=result_payload)
        timestamp = datetime.now().strftime("%d_%H%M%S")

        for index, filename in enumerate(request.selected_files):
            file_path = input_dir / filename
            if not file_path.exists():
                continue
            root = ET.fromstring(scene_xml_text)
            update_integrator_and_sampler(root, request.integrator_type, request.sample_count)
            ensure_hdr_film(root)
            for string_node in root.iter("string"):
                if string_node.get("name") == "filename":
                    value = string_node.get("value")
                    if value and not os.path.isabs(value) and not is_placeholder_value(value):
                        string_node.set("value", resolve_scene_resource(scene_path.parent, value).as_posix())
            target_bsdf = find_target_bsdf(root)
            if target_bsdf is None:
                await self._write_log(task_id, log_path, "Material node not found in scene", status="failed", progress=100, event="done", result_payload=result_payload)
                return
            selected_type = update_bsdf_for_mode(target_bsdf, request.render_mode, file_path, filename, mitsuba_dir)
            temp_xml = TEMP_XML_ROOT / f"{file_path.stem}_{timestamp}_{index}.xml"
            ET.ElementTree(root).write(temp_xml, encoding="utf-8", xml_declaration=True)
            exr_out = exr_dir / f"{file_path.stem}_{timestamp}.exr"
            png_out = png_dir / f"{file_path.stem}_{timestamp}.png"
            cmd = [str(mitsuba_exe), "-o", str(exr_out), str(temp_xml)]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PATH"] = str(mitsuba_dir) + os.pathsep + env.get("PATH", "")
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env)
            self._processes[task_id] = process
            while True:
                line = await process.stdout.readline() if process.stdout else b""
                if not line:
                    break
                text = decode_subprocess_output(line).strip()
                if text:
                    parsed = self._parse_progress(text, index, total)
                    progress = progress_offset + int((parsed or 0) * progress_span / 100)
                    await self._write_log(task_id, log_path, text, progress=min(99, progress), result_payload=result_payload)
            if await process.wait() != 0:
                await self._write_log(task_id, log_path, f"Render failed: {filename}", status="failed", progress=100, event="done", result_payload=result_payload)
                return
            await self._write_log(task_id, log_path, f"Rendered {filename} ({selected_type})", result_payload=result_payload)
            if request.auto_convert and exr_out.exists() and mtsutil_exe.exists():
                convert = await asyncio.create_subprocess_exec(str(mtsutil_exe), "tonemap", "-o", str(png_out), str(exr_out), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env)
                await convert.communicate()
                if png_out.exists():
                    generated_pngs.append(png_out.name)
            await task_manager.update(task_id, status="running", progress=min(99, progress_offset + int((index + 1) / total * progress_span)), message=f"Completed {index + 1}/{total}: {filename}", result_payload=result_payload, event="log")

        await self._write_log(task_id, log_path, "Render task completed", status="success", progress=100, event="done", result_payload=result_payload)

    async def _run_convert(self, task_id: str, request: RenderConvertRequest, log_path: Path) -> None:
        try:
            mtsutil_exe = get_mitsuba_paths()["mtsutil_exe"]
            output_dir = self._output_dir(request.render_mode)
            exr_dir = output_dir / "exr"
            png_dir = output_dir / "png"
            png_dir.mkdir(parents=True, exist_ok=True)
            candidates = sorted(exr_dir.glob("*.exr"))
            if request.filenames:
                requested = set(request.filenames)
                candidates = [entry for entry in candidates if entry.name in requested]
            if not candidates:
                await self._write_log(task_id, log_path, "No EXR files to convert", status="failed", progress=100, event="done")
                return
            for index, entry in enumerate(candidates):
                png_out = png_dir / f"{entry.stem}.png"
                process = await asyncio.create_subprocess_exec(str(mtsutil_exe), "tonemap", "-o", str(png_out), str(entry), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                await process.communicate()
                await self._write_log(task_id, log_path, f"Converted {entry.name}", progress=min(99, int((index + 1) / len(candidates) * 100)))
            await self._write_log(task_id, log_path, "EXR to PNG conversion completed", status="success", progress=100, event="done")
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Convert task failed: {exc}", status="failed", progress=100, event="done")


render_service = RenderService()
