from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import shlex

from backend.core.conda import build_python_runner
from backend.core.config import LOGS_ROOT, PROJECT_ROOT
from backend.core.runtime_logging import format_command, log_task_message
from backend.core.threaded_subprocess import process_is_running, run_process_streaming, terminate_process
from backend.models.common import TaskDetailResponse
from backend.models.train import (
    HyperDecodeRequest,
    HyperExtractRequest,
    HyperTrainRunRequest,
    NeuralH5ConvertRequest,
    NeuralKerasTrainRequest,
    NeuralPytorchTrainRequest,
    ReconstructRequest,
    TrainModelItem,
    TrainModelsResponse,
    TrainRunSummary,
    TrainRunsResponse,
)
from backend.services.model_registry import model_registry_service
from backend.services.task_manager import task_manager


def decode_subprocess_output(raw: Optional[Union[bytes, str]]) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8", "gb18030", "cp936"):
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


class TrainService:
    def __init__(self) -> None:
        self._processes: dict[str, Any] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def list_models(self) -> TrainModelsResponse:
        return TrainModelsResponse(items=model_registry_service.list_models())

    def list_runs(self, model_key: Optional[str] = None) -> TrainRunsResponse:
        if model_key:
            model = self._get_model(model_key)
            if model.adapter != "hyper-family" or not model.supports_runs:
                return TrainRunsResponse(total=0, items=[])
            model_items = [model]
        else:
            model_items = model_registry_service.list_models()
        items: list[TrainRunSummary] = []
        for model in model_items:
            if model.adapter != "hyper-family" or not model.supports_runs:
                continue
            results_dir_value = model.default_paths.get("results_dir", "").strip()
            if not results_dir_value:
                continue
            results_dir = self._resolve_project_path(results_dir_value, must_exist=False)
            if not results_dir.exists():
                continue
            for args_path in results_dir.rglob("args.txt"):
                run_dir = args_path.parent
                checkpoint_path = run_dir / "checkpoint.pt"
                args_data = self._read_args(args_path)
                try:
                    run_name = str(run_dir.relative_to(results_dir))
                except ValueError:
                    run_name = run_dir.name
                items.append(
                    TrainRunSummary(
                        model_key=model.key,
                        label=model.label,
                        adapter=model.adapter,
                        run_name=run_name,
                        run_dir=str(run_dir.resolve()),
                        checkpoint_path=str(checkpoint_path.resolve()),
                        dataset=str(args_data.get("dataset", "MERL")),
                        completed_epochs=self._completed_epochs(run_dir),
                        updated_at=datetime.fromtimestamp(run_dir.stat().st_mtime),
                        has_checkpoint=checkpoint_path.exists(),
                        args=args_data,
                    )
                )
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return TrainRunsResponse(total=len(items), items=items)

    def get_task_detail(self, task_id: str, limit: int = 200) -> Optional[TaskDetailResponse]:
        record = task_manager.get(task_id)
        if record is None:
            return None
        logs: list[str] = []
        if record.log_path and Path(record.log_path).exists():
            logs = Path(record.log_path).read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        return TaskDetailResponse(record=record, logs=logs)

    async def stop_task(self, task_id: str) -> bool:
        record = task_manager.get(task_id)
        if record is None:
            return False
        cancel_event = self._cancel_events.get(task_id)
        if cancel_event is not None:
            cancel_event.set()
        process = self._processes.get(task_id)
        if process_is_running(process):
            terminate_process(process)
        await task_manager.update(task_id, status="cancelled", message="Cancellation requested", event="log")
        return True

    async def start_neural_pytorch(self, request: NeuralPytorchTrainRequest):
        model = self._require_model_adapter(request.model_key, "neural-pytorch")
        log_path = LOGS_ROOT / f"train_neural_pytorch_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_neural_pytorch", f"{model.label} queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_neural_pytorch(record.task_id, model, request, log_path, cancel_event))
        return record

    async def start_neural_keras(self, request: NeuralKerasTrainRequest):
        model = self._require_model_adapter(request.model_key, "neural-keras")
        log_path = LOGS_ROOT / f"train_neural_keras_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_neural_keras", f"{model.label} queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_neural_keras(record.task_id, model, request, log_path, cancel_event))
        return record

    async def start_neural_h5_convert(self, request: NeuralH5ConvertRequest):
        model = self._require_model_adapter(request.model_key, "neural-keras")
        log_path = LOGS_ROOT / f"train_neural_h5_convert_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_neural_h5_convert", f"{model.label} h5 conversion queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_neural_h5_convert(record.task_id, model, request, log_path, cancel_event))
        return record

    async def start_hyper_run(self, request: HyperTrainRunRequest):
        model = self._require_model_adapter(request.model_key, "hyper-family")
        if not model.supports_training:
            raise ValueError(f"模型不支持训练: {model.key}")
        log_path = LOGS_ROOT / f"train_hyper_run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_hyper_run", f"{model.label} training queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_hyper_train(record.task_id, model, request, log_path, cancel_event))
        return record

    async def start_hyper_extract(self, request: HyperExtractRequest):
        model = self._require_model_adapter(request.model_key, "hyper-family")
        if not model.supports_extract:
            raise ValueError(f"模型不支持参数提取: {model.key}")
        log_path = LOGS_ROOT / f"train_hyper_extract_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_hyper_extract", f"{model.label} extraction queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_hyper_extract(record.task_id, model, request, log_path, cancel_event))
        return record

    async def start_hyper_decode(self, request: HyperDecodeRequest):
        model = self._require_model_adapter(request.model_key, "hyper-family")
        if not model.supports_decode:
            raise ValueError(f"模型不支持 fullbin 解码: {model.key}")
        log_path = LOGS_ROOT / f"train_hyper_decode_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_hyper_decode", f"{model.label} decode queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_hyper_decode(record.task_id, model, request, log_path, cancel_event))
        return record

    async def start_reconstruct(self, request: ReconstructRequest):
        """启动重建任务（从模型管理页调用）。"""
        model = self._get_model(request.model_key)
        if not model.supports_reconstruction:
            raise ValueError(f"模型不支持重建: {model.key}")
        log_path = LOGS_ROOT / f"reconstruct_{request.model_key}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("reconstruct", f"{model.label} 重建排队中", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_reconstruct(record.task_id, model, request, log_path, cancel_event))
        return record

    def _get_model(self, model_key: str) -> TrainModelItem:
        return model_registry_service.get_model(model_key)

    def _require_model_adapter(self, model_key: str, adapter: str) -> TrainModelItem:
        model = self._get_model(model_key)
        if model.adapter != adapter:
            raise ValueError(f"模型 {model_key} 的适配器为 {model.adapter}，不能按 {adapter} 流程执行。")
        return model

    def _read_args(self, args_path: Path) -> dict[str, Any]:
        try:
            return json.loads(args_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _completed_epochs(self, run_dir: Path) -> int:
        train_loss = run_dir / "train_loss.csv"
        if not train_loss.exists():
            return 0
        try:
            line_count = len(train_loss.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            return 0
        return max(line_count - 1, 0)

    async def _write_log(
        self,
        task_id: str,
        log_path: Path,
        message: str,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        event: str = "log",
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        clean_message = message.replace("\r", "").replace("\b", "")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(clean_message + "\n")
        log_task_message("train", task_id, clean_message)
        await task_manager.update(
            task_id,
            status=status,
            progress=progress,
            message=clean_message,
            log_path=str(log_path),
            result_payload=result_payload,
            event=event,
        )

    async def _run_command(
        self,
        task_id: str,
        log_path: Path,
        cmd: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        progress: Optional[int] = None,
        start_message: str,
        use_shell: bool = False,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> int:
        await self._write_log(task_id, log_path, start_message, status="running", progress=progress)
        await self._write_log(task_id, log_path, format_command(cmd, cwd=cwd, use_shell=use_shell), progress=progress)
        async def handle_output(line: bytes) -> None:
            text = decode_subprocess_output(line).strip()
            if text:
                await self._write_log(task_id, log_path, text, progress=progress)

        return await run_process_streaming(
            cmd,
            cwd=cwd,
            env=env,
            use_shell=use_shell,
            cancel_event=cancel_event,
            process_store=self._processes,
            process_key=task_id,
            on_output=handle_output,
        )

    def _make_env(self, model: TrainModelItem, *, include_script_parent: str = "") -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        pythonpath_parts: list[str] = [str(PROJECT_ROOT)]
        working_dir_value = model.runtime.get("working_dir", "").strip()
        if working_dir_value:
            pythonpath_parts.append(str(self._resolve_project_path(working_dir_value, must_exist=True)))
        if include_script_parent:
            pythonpath_parts.append(str(self._resolve_project_path(include_script_parent, must_exist=True)))
        existing = env.get("PYTHONPATH", "")
        if existing:
            pythonpath_parts.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(part for part in pythonpath_parts if part)
        return env

    def _python_runner(self, conda_env: Optional[str] = None) -> tuple[list[str], bool]:
        return build_python_runner(conda_env)

    def _resolve_project_path(self, path_value: str, *, must_exist: bool) -> Path:
        raw_path = Path(path_value)
        candidate = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        resolved = candidate.resolve(strict=False)
        project_root = PROJECT_ROOT.resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"Path must stay inside project root: {path_value}") from exc
        if must_exist and not resolved.exists():
            raise FileNotFoundError(resolved)
        return resolved

    def _working_dir_for(self, model: TrainModelItem) -> Path:
        working_dir_value = model.runtime.get("working_dir", "").strip()
        if working_dir_value:
            return self._resolve_project_path(working_dir_value, must_exist=True)
        train_script = model.runtime.get("train_script", "").strip()
        if train_script:
            return self._resolve_project_path(train_script, must_exist=True).parent
        return PROJECT_ROOT

    def _supports_sparse_samples(self, model: TrainModelItem) -> bool:
        return model.adapter == "hyper-family"

    async def _run_neural_pytorch(
        self,
        task_id: str,
        model: TrainModelItem,
        request: NeuralPytorchTrainRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            ensure_exists(merl_dir)
            if not request.selected_materials:
                raise ValueError("未选择材质文件。")
            output_dir = Path(request.output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            train_script = self._resolve_project_path(model.runtime["train_script"], must_exist=True)
            relative_parent = str(train_script.parent.relative_to(PROJECT_ROOT))
            env = self._make_env(model, include_script_parent=relative_parent)
            runner, _ = self._python_runner(model.runtime.get("conda_env", "").strip())

            total = len(request.selected_materials)
            generated: list[str] = []
            for index, material in enumerate(request.selected_materials):
                material_path = merl_dir / material
                ensure_exists(material_path, file_ok=True)
                cmd = [
                    *runner,
                    str(train_script),
                    str(material_path),
                    "--outpath",
                    str(output_dir),
                    "--epochs",
                    str(request.epochs),
                    "--device",
                    request.device,
                ]
                return_code = await self._run_command(
                    task_id,
                    log_path,
                    cmd,
                    cwd=self._working_dir_for(model),
                    env=env,
                    progress=min(95, int(index / total * 100)),
                    start_message=f"[{index + 1}/{total}] Start {model.label}: {material}",
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    await self._write_log(
                        task_id,
                        log_path,
                        f"Training failed for {material} (exit code: {return_code}).",
                        status="failed",
                        progress=100,
                        event="done",
                    )
                    return
                generated.append(material_path.stem)

            await self._write_log(
                task_id,
                log_path,
                f"{model.label} training completed.",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "materials": generated, "model_key": model.key},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Training task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_neural_keras(
        self,
        task_id: str,
        model: TrainModelItem,
        request: NeuralKerasTrainRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            ensure_exists(merl_dir)
            if not request.selected_materials:
                raise ValueError("未选择材质文件。")
            h5_output_dir = Path(request.h5_output_dir).resolve()
            npy_output_dir = Path(request.npy_output_dir).resolve()
            h5_output_dir.mkdir(parents=True, exist_ok=True)
            npy_output_dir.mkdir(parents=True, exist_ok=True)

            train_script = self._resolve_project_path(model.runtime["train_script"], must_exist=True)
            convert_script = self._resolve_project_path(model.runtime["convert_script"], must_exist=True)
            relative_parent = str(train_script.parent.relative_to(PROJECT_ROOT))
            env = self._make_env(model, include_script_parent=relative_parent)
            env["CUDA_VISIBLE_DEVICES"] = request.cuda_device
            runner, _ = self._python_runner(model.runtime.get("conda_env", "").strip())

            binary_paths = [str((merl_dir / material).resolve()) for material in request.selected_materials]
            for binary_path in binary_paths:
                ensure_exists(Path(binary_path), file_ok=True)

            train_cmd = [*runner, str(train_script), *binary_paths, "--cuda_device", request.cuda_device]
            train_return = await self._run_command(
                task_id,
                log_path,
                train_cmd,
                cwd=self._working_dir_for(model),
                env=env,
                progress=15,
                start_message=f"Start {model.label} training.",
                cancel_event=cancel_event,
            )
            if train_return == -1:
                await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                return
            if train_return != 0:
                await self._write_log(
                    task_id,
                    log_path,
                    f"Keras training failed (exit code: {train_return}).",
                    status="failed",
                    progress=100,
                    event="done",
                )
                return

            h5_paths: list[str] = []
            work_dir = self._working_dir_for(model)
            for material in request.selected_materials:
                basename = Path(material).stem
                src_h5 = work_dir / f"{basename}.h5"
                src_json = work_dir / f"{basename}.json"
                src_loss = work_dir / f"lossplot_{basename}.png"
                target_h5 = h5_output_dir / f"{basename}.h5"
                if src_h5.exists():
                    shutil.move(str(src_h5), str(target_h5))
                    if src_json.exists():
                        shutil.move(str(src_json), str(h5_output_dir / f"{basename}.json"))
                    if src_loss.exists():
                        shutil.move(str(src_loss), str(h5_output_dir / f"lossplot_{basename}.png"))
                    h5_paths.append(str(target_h5))
                    await self._write_log(task_id, log_path, f"Archived intermediate file: {basename}.h5", progress=45)

            if not h5_paths:
                await self._write_log(
                    task_id,
                    log_path,
                    "Training completed but no .h5 outputs were found.",
                    status="failed",
                    progress=100,
                    event="done",
                )
                return

            convert_cmd = [*runner, str(convert_script), *h5_paths, "--destdir", str(npy_output_dir)]
            convert_return = await self._run_command(
                task_id,
                log_path,
                convert_cmd,
                cwd=self._working_dir_for(model),
                env=env,
                progress=65,
                start_message=f"Start {model.label} h5 -> npy conversion.",
                cancel_event=cancel_event,
            )
            if convert_return == -1:
                await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                return
            if convert_return != 0:
                await self._write_log(
                    task_id,
                    log_path,
                    f"h5 -> npy conversion failed (exit code: {convert_return}).",
                    status="failed",
                    progress=100,
                    event="done",
                )
                return

            await self._write_log(
                task_id,
                log_path,
                f"{model.label} training and conversion completed.",
                status="success",
                progress=100,
                event="done",
                result_payload={
                    "h5_output_dir": str(h5_output_dir),
                    "npy_output_dir": str(npy_output_dir),
                    "count": len(h5_paths),
                    "model_key": model.key,
                },
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Training task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_neural_h5_convert(
        self,
        task_id: str,
        model: TrainModelItem,
        request: NeuralH5ConvertRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            h5_dir = Path(request.h5_dir).resolve()
            npy_output_dir = Path(request.npy_output_dir).resolve()
            ensure_exists(h5_dir)
            if not request.selected_h5_files:
                raise ValueError("No .h5 files selected.")
            npy_output_dir.mkdir(parents=True, exist_ok=True)

            convert_script = self._resolve_project_path(model.runtime["convert_script"], must_exist=True)
            env = self._make_env(model, include_script_parent=str(convert_script.parent.relative_to(PROJECT_ROOT)))
            conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
            runner, _ = self._python_runner(conda_env)

            h5_paths: list[str] = []
            for file_name in request.selected_h5_files:
                h5_path = h5_dir / file_name
                ensure_exists(h5_path, file_ok=True)
                h5_paths.append(str(h5_path))

            convert_cmd = [*runner, str(convert_script), *h5_paths, "--destdir", str(npy_output_dir)]
            convert_return = await self._run_command(
                task_id,
                log_path,
                convert_cmd,
                cwd=self._working_dir_for(model),
                env=env,
                progress=25,
                start_message=f"Start {model.label} h5 -> npy conversion.",
                cancel_event=cancel_event,
            )
            if convert_return == -1:
                await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                return
            if convert_return != 0:
                await self._write_log(
                    task_id,
                    log_path,
                    f"h5 -> npy conversion failed (exit code: {convert_return}).",
                    status="failed",
                    progress=100,
                    event="done",
                )
                return

            await self._write_log(
                task_id,
                log_path,
                f"{model.label} h5 conversion completed.",
                status="success",
                progress=100,
                event="done",
                result_payload={
                    "h5_dir": str(h5_dir),
                    "npy_output_dir": str(npy_output_dir),
                    "count": len(h5_paths),
                    "model_key": model.key,
                },
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Conversion task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_hyper_train(
        self,
        task_id: str,
        model: TrainModelItem,
        request: HyperTrainRunRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            output_dir = Path(request.output_dir).resolve()
            ensure_exists(merl_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            train_script = self._resolve_project_path(model.runtime["train_script"], must_exist=True)
            env = self._make_env(model)
            conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
            runner, _ = self._python_runner(conda_env)

            cmd = [
                *runner,
                str(train_script),
                "--destdir",
                str(output_dir),
                "--binary",
                str(merl_dir),
                "--dataset",
                request.dataset,
                "--epochs",
                str(request.epochs),
                "--sparse_samples",
                str(request.sparse_samples),
                "--kl_weight",
                str(request.kl_weight),
                "--fw_weight",
                str(request.fw_weight),
                "--lr",
                str(request.lr),
                "--train_subset",
                str(request.train_subset),
                "--train_seed",
                str(request.train_seed),
            ]
            if request.keepon:
                cmd.append("--keepon")

            return_code = await self._run_command(
                task_id,
                log_path,
                cmd,
                cwd=self._working_dir_for(model),
                env=env,
                progress=5,
                start_message=f"Start {model.label} training.",
                cancel_event=cancel_event,
            )
            if return_code == -1:
                await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                return
            if return_code != 0:
                await self._write_log(
                    task_id,
                    log_path,
                    f"Training failed (exit code: {return_code}).",
                    status="failed",
                    progress=100,
                    event="done",
                )
                return

            await self._write_log(
                task_id,
                log_path,
                f"{model.label} training completed.",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "model_key": model.key},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Training task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_hyper_extract(
        self,
        task_id: str,
        model: TrainModelItem,
        request: HyperExtractRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            model_path = Path(request.model_path).resolve()
            output_dir = Path(request.output_dir).resolve()
            ensure_exists(merl_dir)
            ensure_exists(model_path, file_ok=True)
            if request.dataset == "MERL" and not request.selected_materials:
                raise ValueError("未选择材质文件。")
            output_dir.mkdir(parents=True, exist_ok=True)

            extract_script = self._resolve_project_path(model.runtime["extract_script"], must_exist=True)
            env = self._make_env(model)
            conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
            runner, _ = self._python_runner(conda_env)

            if request.dataset == "EPFL":
                cmd = [
                    *runner,
                    str(extract_script),
                    "--model",
                    str(model_path),
                    "--binary",
                    str(merl_dir),
                    "--destdir",
                    str(output_dir),
                    "--dataset",
                    "EPFL",
                ]
                if self._supports_sparse_samples(model):
                    cmd.extend(["--sparse_samples", str(request.sparse_samples)])
                return_code = await self._run_command(
                    task_id,
                    log_path,
                    cmd,
                    cwd=self._working_dir_for(model),
                    env=env,
                    progress=10,
                    start_message=f"Start {model.label} extraction for EPFL.",
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    await self._write_log(
                        task_id,
                        log_path,
                        f"Extraction failed (exit code: {return_code}).",
                        status="failed",
                        progress=100,
                        event="done",
                    )
                    return
                processed = ["EPFL"]
            else:
                processed = []
                total = len(request.selected_materials)
                for index, material in enumerate(request.selected_materials):
                    binary_path = merl_dir / material
                    ensure_exists(binary_path, file_ok=True)
                    cmd = [
                        *runner,
                        str(extract_script),
                        "--model",
                        str(model_path),
                        "--binary",
                        str(binary_path),
                        "--destdir",
                        str(output_dir),
                        "--dataset",
                        "MERL",
                    ]
                    if self._supports_sparse_samples(model):
                        cmd.extend(["--sparse_samples", str(request.sparse_samples)])
                    return_code = await self._run_command(
                        task_id,
                        log_path,
                        cmd,
                        cwd=self._working_dir_for(model),
                        env=env,
                        progress=min(95, int(index / total * 100)),
                        start_message=f"[{index + 1}/{total}] Extract parameters: {material}",
                        cancel_event=cancel_event,
                    )
                    if return_code == -1:
                        await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                        return
                    if return_code != 0:
                        await self._write_log(
                            task_id,
                            log_path,
                            f"Extraction failed for {material} (exit code: {return_code}).",
                            status="failed",
                            progress=100,
                            event="done",
                        )
                        return
                    processed.append(material)

            await self._write_log(
                task_id,
                log_path,
                f"{model.label} extraction completed.",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "model_key": model.key, "processed": processed},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Extraction task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_hyper_decode(
        self,
        task_id: str,
        model: TrainModelItem,
        request: HyperDecodeRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            pt_dir = Path(request.pt_dir).resolve()
            output_dir = Path(request.output_dir).resolve()
            ensure_exists(pt_dir)
            if not request.selected_pts:
                raise ValueError("未选择 .pt 文件。")
            output_dir.mkdir(parents=True, exist_ok=True)

            decode_script = self._resolve_project_path(model.runtime["decode_script"], must_exist=True)
            env = self._make_env(model)
            env["CUDA_VISIBLE_DEVICES"] = request.cuda_device
            conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
            runner, _ = self._python_runner(conda_env)

            total = len(request.selected_pts)
            processed: list[str] = []
            for index, pt_name in enumerate(request.selected_pts):
                pt_path = pt_dir / pt_name
                ensure_exists(pt_path, file_ok=True)
                cmd = [
                    *runner,
                    str(decode_script),
                    str(pt_path),
                    str(output_dir),
                    "--dataset",
                    request.dataset,
                    "--cuda_device",
                    request.cuda_device,
                ]
                return_code = await self._run_command(
                    task_id,
                    log_path,
                    cmd,
                    cwd=self._working_dir_for(model),
                    env=env,
                    progress=min(95, int(index / total * 100)),
                    start_message=f"[{index + 1}/{total}] Decode fullbin: {pt_name}",
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    await self._write_log(
                        task_id,
                        log_path,
                        f"Decode failed for {pt_name} (exit code: {return_code}).",
                        status="failed",
                        progress=100,
                        event="done",
                    )
                    return
                processed.append(pt_name)

            await self._write_log(
                task_id,
                log_path,
                f"{model.label} decode completed.",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "model_key": model.key, "processed": processed},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"Decode task failed: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_reconstruct(
        self,
        task_id: str,
        model: TrainModelItem,
        request: ReconstructRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        """执行重建任务。根据模型适配器分派不同的重建逻辑。"""
        try:
            merl_dir = Path(request.merl_dir).resolve()
            ensure_exists(merl_dir)
            if not request.selected_materials:
                raise ValueError("未选择材质文件。")

            if model.adapter == "neural-pytorch":
                output_dir = Path(request.output_dir or "data/inputs/npy").resolve()
                output_dir.mkdir(parents=True, exist_ok=True)

                train_script = self._resolve_project_path(model.runtime["train_script"], must_exist=True)
                relative_parent = str(train_script.parent.relative_to(PROJECT_ROOT))
                env = self._make_env(model, include_script_parent=relative_parent)
                conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
                runner, _ = self._python_runner(conda_env)

                total = len(request.selected_materials)
                generated: list[str] = []
                for index, material in enumerate(request.selected_materials):
                    material_path = merl_dir / material
                    ensure_exists(material_path, file_ok=True)
                    cmd = [
                        *runner,
                        str(train_script),
                        str(material_path),
                        "--outpath",
                        str(output_dir),
                        "--epochs",
                        str(request.neural_epochs),
                        "--device",
                        request.neural_device,
                    ]
                    return_code = await self._run_command(
                        task_id, log_path, cmd,
                        cwd=self._working_dir_for(model), env=env,
                        progress=min(95, int(index / total * 100)),
                        start_message=f"[{index + 1}/{total}] 重建 {model.label}: {material}",
                        cancel_event=cancel_event,
                    )
                    if return_code == -1:
                        await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                        return
                    if return_code != 0:
                        await self._write_log(task_id, log_path, f"重建失败: {material} (exit code: {return_code})", status="failed", progress=100, event="done")
                        return
                    generated.append(material_path.stem)

                await self._write_log(task_id, log_path, f"{model.label} 重建完成。", status="success", progress=100, event="done",
                    result_payload={"output_dir": str(output_dir), "model_key": model.key, "materials": generated})

            elif model.adapter == "hyper-family":
                # HyperBRDF 重建 = extract + decode
                checkpoint_path = Path(request.checkpoint_path).resolve() if request.checkpoint_path else None
                if not checkpoint_path or not checkpoint_path.exists():
                    raise ValueError("HyperBRDF 重建需要有效的 Checkpoint 路径")

                extract_dir = Path(model.default_paths.get("extract_dir", "models/HyperBRDF/results/extracted_pts")).resolve()
                extract_dir.mkdir(parents=True, exist_ok=True)
                fullbin_output_dir = Path(request.output_dir or "data/inputs/fullbin").resolve()
                fullbin_output_dir.mkdir(parents=True, exist_ok=True)

                # Step 1: Extract
                extract_script = self._resolve_project_path(model.runtime["extract_script"], must_exist=True)
                env = self._make_env(model)
                conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
                runner, _ = self._python_runner(conda_env)

                total = len(request.selected_materials)
                pt_files: list[str] = []
                for index, material in enumerate(request.selected_materials):
                    binary_path = merl_dir / material
                    ensure_exists(binary_path, file_ok=True)
                    cmd = [
                        *runner, str(extract_script),
                        "--model", str(checkpoint_path),
                        "--binary", str(binary_path),
                        "--destdir", str(extract_dir),
                        "--dataset", request.dataset,
                    ]
                    if self._supports_sparse_samples(model):
                        cmd.extend(["--sparse_samples", str(request.sparse_samples)])
                    return_code = await self._run_command(
                        task_id, log_path, cmd,
                        cwd=self._working_dir_for(model), env=env,
                        progress=min(45, int(index / total * 50)),
                        start_message=f"[{index + 1}/{total}] 提取参数: {material}",
                        cancel_event=cancel_event,
                    )
                    if return_code == -1:
                        await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                        return
                    if return_code != 0:
                        await self._write_log(task_id, log_path, f"提取失败: {material}", status="failed", progress=100, event="done")
                        return
                    pt_name = f"{Path(material).stem}.pt"
                    pt_files.append(pt_name)

                # Step 2: Decode
                decode_script = self._resolve_project_path(model.runtime["decode_script"], must_exist=True)
                env["CUDA_VISIBLE_DEVICES"] = request.cuda_device

                for index, pt_name in enumerate(pt_files):
                    pt_path = extract_dir / pt_name
                    if not pt_path.exists():
                        await self._write_log(task_id, log_path, f"跳过缺失的 PT 文件: {pt_name}", progress=50 + int(index / len(pt_files) * 45))
                        continue
                    cmd = [
                        *runner, str(decode_script),
                        str(pt_path), str(fullbin_output_dir),
                        "--dataset", request.dataset,
                        "--cuda_device", request.cuda_device,
                    ]
                    return_code = await self._run_command(
                        task_id, log_path, cmd,
                        cwd=self._working_dir_for(model), env=env,
                        progress=min(95, 50 + int(index / len(pt_files) * 45)),
                        start_message=f"[{index + 1}/{len(pt_files)}] 解码: {pt_name}",
                        cancel_event=cancel_event,
                    )
                    if return_code == -1:
                        await self._write_log(task_id, log_path, "Task cancelled.", status="cancelled", progress=100, event="done")
                        return
                    if return_code != 0:
                        await self._write_log(task_id, log_path, f"解码失败: {pt_name}", status="failed", progress=100, event="done")
                        return

                await self._write_log(task_id, log_path, f"{model.label} 重建完成。", status="success", progress=100, event="done",
                    result_payload={"output_dir": str(fullbin_output_dir), "model_key": model.key})

            elif model.adapter == "custom-cli":
                # Custom model reconstruction via command line
                reconstruct_script = model.runtime.get("reconstruct_script", "").strip()
                reconstruct_args_template = model.runtime.get("reconstruct_args_template", "").strip()
                if not reconstruct_script:
                    raise ValueError(f"自定义模型未配置重建脚本: {model.key}")

                output_dir = Path(request.output_dir).resolve() if request.output_dir else PROJECT_ROOT / "data" / "outputs" / model.key
                output_dir.mkdir(parents=True, exist_ok=True)

                script_path = self._resolve_project_path(reconstruct_script, must_exist=True)
                env = self._make_env(model)
                conda_env = request.conda_env.strip() or model.runtime.get("conda_env", "").strip()
                runner, _ = self._python_runner(conda_env)

                # Build command from template - use shlex.split for safe argument parsing
                args_str = reconstruct_args_template
                for material in request.selected_materials:
                    material_path = merl_dir / material
                    # Quote user-supplied values to prevent template injection
                    safe_kwargs = {
                        "data_dir": str(merl_dir),
                        "input": str(material_path),
                        "output": str(output_dir),
                        "checkpoint": request.checkpoint_path,
                        "material": material,
                    }
                    cmd_str = args_str.format(**safe_kwargs)
                    cmd = [*runner, str(script_path)] + shlex.split(cmd_str)
                    return_code = await self._run_command(
                        task_id, log_path, cmd,
                        cwd=self._working_dir_for(model), env=env,
                        progress=50,
                        start_message=f"自定义模型重建: {material}",
                        cancel_event=cancel_event,
                    )
                    if return_code != 0:
                        await self._write_log(task_id, log_path, f"重建失败: {material}", status="failed", progress=100, event="done")
                        return

                await self._write_log(task_id, log_path, f"{model.label} 重建完成。", status="success", progress=100, event="done",
                    result_payload={"output_dir": str(output_dir), "model_key": model.key})
            else:
                raise ValueError(f"不支持的适配器类型: {model.adapter}")

        except Exception as exc:
            await self._write_log(task_id, log_path, f"重建任务失败: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)


train_service = TrainService()
