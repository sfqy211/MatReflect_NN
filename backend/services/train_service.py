from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.models.train import PostActionDef

from backend.core.command_renderer import (
    _build_context,
    get_operation,
    render_commands,
    render_preview,
    resolve_source,
)
from backend.core.config import LOGS_ROOT, PROJECT_ROOT
from backend.core.runtime_logging import format_command, log_task_message
from backend.core.threaded_subprocess import process_is_running, run_process_streaming, terminate_process
from backend.models.common import TaskDetailResponse, TaskRecord
from backend.models.train import (
    HyperDecodeRequest,
    HyperExtractRequest,
    HyperTrainRunRequest,
    NeuralH5ConvertRequest,
    NeuralKerasTrainRequest,
    NeuralPytorchTrainRequest,
    OperationDef,
    PreviewCommandItem,
    PreviewCommandResponse,
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

    # ─── 通用操作入口（新） ──────────────────────────────────────────────────

    async def start_operation(
        self,
        model_key: str,
        operation_id: str,
        params: dict,
        *,
        task_type: str = "operation",
        task_label: str = "",
        log_path: Optional[Path] = None,
    ) -> TaskRecord:
        """通用操作执行入口。
        
        Args:
            model_key: 模型 key
            operation_id: 操作 ID（如 "train", "extract", "decode", "reconstruct"）
            params: 请求参数 dict
            task_type: 任务类型（用于 task_manager.create）
            task_label: 任务显示标签
            log_path: 日志路径，为空则自动生成
        """
        model = self._get_model(model_key)
        op = get_operation(model, operation_id)
        if not op:
            valid_ops = list(model.operations.keys())
            raise ValueError(f"模型 {model_key} 未定义操作 '{operation_id}'，可用: {valid_ops}")

        label = task_label or op.label or operation_id
        effective_log_path = log_path if log_path is not None else LOGS_ROOT / f"{task_type}_{operation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create(task_type, f"{model.label} {label} 排队中", log_path=str(effective_log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(
            self._run_operation(record.task_id, model, operation_id, params, effective_log_path, cancel_event, task_label=label)
        )
        return record

    def preview_command(
        self,
        model_key: str,
        operation_id: str,
        params: dict,
        single_item: Optional[str] = None,
    ) -> PreviewCommandResponse:
        """预览操作命令（不执行）。"""
        model = self._get_model(model_key)
        preview_items = render_preview(model, operation_id, params, single_item=single_item)
        commands = []
        for item in preview_items:
            commands.append(PreviewCommandItem(
                step_index=len(commands),
                step_label=item.get("label", ""),
                command=item.get("command", []),
                cwd=item.get("cwd", ""),
                conda_env=item.get("conda_env", ""),
            ))
        return PreviewCommandResponse(
            model_key=model_key,
            operation=operation_id,
            commands=commands,
            total_commands=len(commands),
            has_loop=any(cmd.get("item") is not None for cmd in preview_items),
        )

    # ─── 通用操作执行器 ──────────────────────────────────────────────────────

    async def _run_operation(
        self,
        task_id: str,
        model: TrainModelItem,
        operation_id: str,
        params: dict,
        log_path: Path,
        cancel_event: asyncio.Event,
        *,
        task_label: str = "",
        progress_start: int = 0,
        progress_range: int = 95,
        is_sub_op: bool = False,
        parent_ctx: Optional[dict] = None,
    ) -> None:
        """通用操作执行器，支持单步、多步子操作、post_action、output_transform。

        当 is_sub_op=True 时，表示本操作是子操作链中的一环：
        - 执行成功时不写 status=success + event=done（由最外层任务统一写）
        - 执行失败/取消时照常写（整个任务终止）
        """
        try:
            op = get_operation(model, operation_id)
            if not op:
                valid_ops = list(model.operations.keys())
                raise ValueError(f"模型 {model.key} 未定义操作 '{operation_id}'，可用: {valid_ops}")

            label_prefix = task_label or op.label or operation_id

            # ── 多步子操作（Workflow） ──────────────────────────────────────
            if op.sub_operations:
                await self._run_sub_operations(
                    task_id=task_id,
                    model=model,
                    operation=op,
                    params=params,
                    log_path=log_path,
                    cancel_event=cancel_event,
                    task_label=label_prefix,
                    progress_start=progress_start,
                    progress_range=progress_range,
                )
                # 子操作全部完成后，由最外层 (is_sub_op=False) 写 success/done
                if not is_sub_op:
                    payload = self._build_result_payload(model, operation_id, params, [])
                    payload["sub_operations"] = op.sub_operations
                    await self._write_log(
                        task_id, log_path,
                        f"{label_prefix} 完成。",
                        status="success", progress=100, event="done",
                        result_payload=payload,
                    )
                return  # 子操作完成后不再执行单步逻辑

            # ── 单步渲染命令 ────────────────────────────────────────────────
            commands = render_commands(op, model, params)
            total = len(commands)

            for idx, cmd_info in enumerate(commands):
                cmd = cmd_info["command"]
                cwd_str = cmd_info.get("cwd", "")
                item_name = cmd_info.get("item")

                # Environment
                env = self._make_env(model)
                if op.cuda_visible_source:
                    ctx_for_resolve = _build_context(model, params, op)
                    cuda_val = resolve_source(op.cuda_visible_source, ctx_for_resolve)
                    if cuda_val:
                        env["CUDA_VISIBLE_DEVICES"] = str(cuda_val)

                cwd = Path(cwd_str) if cwd_str else self._working_dir_for(model)
                progress = progress_start
                if total > 1:
                    progress = progress_start + int((idx / total) * progress_range)

                step_label = cmd_info.get("label", f"{label_prefix} [{idx + 1}/{total}]")
                if item_name:
                    step_label = f"{label_prefix}: {item_name} [{idx + 1}/{total}]"

                return_code = await self._run_command(
                    task_id, log_path, cmd,
                    cwd=cwd, env=env,
                    progress=progress,
                    start_message=step_label,
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "任务已取消。", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    msg = f"操作失败 (exit code: {return_code})"
                    if item_name:
                        msg = f"处理 {item_name} 失败 (exit code: {return_code})"
                    await self._write_log(task_id, log_path, msg, status="failed", progress=100, event="done")
                    return

            # ── 后处理（Post-actions） ──────────────────────────────────────
            if op.post_actions:
                for action in op.post_actions:
                    try:
                        await self._run_post_action(
                            task_id, model, op, params, action, log_path, cancel_event,
                            progress=progress_start + progress_range,
                        )
                    except Exception as exc:
                        await self._write_log(
                            task_id, log_path,
                            f"后处理失败: {exc}", status="failed", progress=100, event="done",
                        )
                        return

            # ── 结果 ────────────────────────────────────────────────────────
            # is_sub_op 时仅写进度更新，不写 success/done（由最外层统一写）
            if not is_sub_op:
                payload = self._build_result_payload(model, operation_id, params, commands)
                await self._write_log(
                    task_id, log_path,
                    f"{label_prefix} 完成。",
                    status="success", progress=100, event="done",
                    result_payload=payload,
                )
            else:
                await self._write_log(
                    task_id, log_path,
                    f"{label_prefix} 完成（子操作）。",
                    progress=progress_start + progress_range,
                )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"任务失败: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_sub_operations(
        self,
        task_id: str,
        model: TrainModelItem,
        operation: OperationDef,
        params: dict,
        log_path: Path,
        cancel_event: asyncio.Event,
        *,
        task_label: str = "",
        progress_start: int = 0,
        progress_range: int = 95,
    ) -> None:
        """顺序执行子操作链。"""
        sub_ids = operation.sub_operations
        sub_count = len(sub_ids)
        current_params = dict(params)

        for idx, sub_id in enumerate(sub_ids):
            sub_op = get_operation(model, sub_id)
            if not sub_op:
                await self._write_log(
                    task_id, log_path,
                    f"子操作 '{sub_id}' 未定义（模型: {model.key}）",
                    status="failed", progress=100, event="done",
                )
                return

            sub_range = progress_range // sub_count
            sub_start = progress_start + idx * sub_range

            # 应用 output_transform（用于子操作间数据传递）
            if idx > 0 and operation.output_transform_type:
                transformed = self._apply_output_transform(
                    operation, sub_id, current_params, model
                )
                if transformed:
                    current_params.update(transformed)

            sub_label = f"{task_label}/{sub_op.label}" if task_label else sub_op.label

            await self._write_log(
                task_id, log_path,
                f"[{idx + 1}/{sub_count}] 开始子操作: {sub_label}",
                progress=sub_start,
            )

            await self._run_operation(
                task_id=task_id,
                model=model,
                operation_id=sub_id,
                params=current_params,
                log_path=log_path,
                cancel_event=cancel_event,
                task_label=sub_label,
                progress_start=sub_start,
                progress_range=sub_range,
                is_sub_op=True,
                parent_ctx={"params": current_params},
            )

            # Check if cancelled/failed after sub operation
            record = task_manager.get(task_id)
            if record and record.status in ("cancelled", "failed"):
                return

        # 子操作全部完成 — 仅写进度，不写 event=done（由最外层 _run_operation 的 is_sub_op=False 负责）
        await self._write_log(
            task_id, log_path,
            f"{task_label} 所有子操作完成。" if task_label else "所有子操作完成。",
            progress=progress_start + progress_range,
        )

    def _apply_output_transform(
        self,
        operation: OperationDef,
        next_sub_id: str,
        current_params: dict,
        model: TrainModelItem,
    ) -> dict:
        """应用 output_transform 在子操作间传递数据。
        
        当前支持：
        - selected_materials_to_pt: selected_materials → .pt 文件名列表，设为对应子操作的 loop_source
        
        遇到未知 transform_type 时显式抛错，避免配置错误悄悄通过。
        """
        transform_type = operation.output_transform_type
        if not transform_type:
            return {}

        if transform_type == "selected_materials_to_pt":
            selected = current_params.get("selected_materials", [])
            if not selected:
                return {}
            pt_names = [f"{Path(m).stem}.pt" for m in selected]
            # 确定 pt_dir：使用 default_paths.extract_dir 或 output_dir
            pt_dir = model.default_paths.get("extract_dir", "")
            if not pt_dir:
                pt_dir = current_params.get("output_dir", "")
            return {
                "selected_pts": pt_names,
                "pt_dir": pt_dir,
            }

        raise ValueError(
            f"未知的 output_transform_type: '{transform_type}'。"
            f"模型 {model.key} 操作中定义了不支持的转换类型。"
        )

    async def _run_post_action(
        self,
        task_id: str,
        model: TrainModelItem,
        operation: OperationDef,
        params: dict,
        action: "PostActionDef",
        log_path: Path,
        cancel_event: asyncio.Event,
        *,
        progress: int = 90,
    ) -> None:
        """执行操作后处理（如 move_files）。
        
        注意：当前 post_action 中的 pattern 占位符使用 Python str.replace 风格
        （{item} / {item.stem}），而非 command_renderer 的 {{var}} 模板语法。
        若未来需要统一，建议将 post_action 的 pattern 也迁移至 {{var}} 语法。
        """
        if action.type == "move_files":
            ctx = _build_context(model, params, operation)
            source_dir_str = resolve_source(action.source_dir_source, ctx) if action.source_dir_source else ""
            dest_dir_str = resolve_source(action.dest_dir_source, ctx) if action.dest_dir_source else ""

            if not dest_dir_str:
                await self._write_log(task_id, log_path, "后处理: 目标目录为空，跳过。", progress=progress)
                return

            source_dir = Path(source_dir_str) if source_dir_str else self._working_dir_for(model)
            dest_dir = Path(dest_dir_str)
            if not dest_dir.is_absolute():
                dest_dir = (PROJECT_ROOT / dest_dir).resolve()

            # 遍历每个 loop 项，移动对应的文件
            loop_source = operation.loop_source
            items = params.get(loop_source.replace("request.", ""), []) if loop_source else []
            if not items and operation.merge_inputs:
                items = params.get("selected_materials", [])

            dest_dir.mkdir(parents=True, exist_ok=True)
            moved_count = 0
            for item_name in items:
                item_stem = Path(item_name).stem if item_name else ""
                for pattern in action.patterns:
                    resolved_pattern = pattern.replace("{item.stem}", item_stem).replace("{item}", str(item_name))
                    for f in source_dir.glob(resolved_pattern):
                        dest_path = dest_dir / f.name
                        shutil.move(str(f), str(dest_path))
                        moved_count += 1
                        await self._write_log(
                            task_id, log_path,
                            f"归档: {f.name} → {dest_dir}",
                            progress=progress,
                        )

            if moved_count == 0:
                await self._write_log(
                    task_id, log_path,
                    f"后处理: 没有匹配的文件（模式: {action.patterns}）",
                    progress=progress,
                )
            else:
                await self._write_log(
                    task_id, log_path,
                    f"后处理完成: 已移动 {moved_count} 个文件",
                    progress=progress,
                )

    def _build_result_payload(
        self,
        model: TrainModelItem,
        operation_id: str,
        params: dict,
        commands: list[dict],
    ) -> dict:
        """构建通用结果 payload。"""
        payload: dict = {
            "model_key": model.key,
            "operation": operation_id,
        }
        # 尝试提取输出目录
        for key in ("output_dir", "npy_output_dir", "h5_output_dir"):
            val = params.get(key)
            if val:
                payload[key] = str(val)
                break
        # 如果有子操作，标记完成
        op = get_operation(model, operation_id)
        if op and op.sub_operations:
            payload["sub_operations"] = op.sub_operations
        return payload

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
        """旧端点包装：转换为通用操作 (train)。"""
        model = self._require_model_adapter(request.model_key, "neural-pytorch")
        params = {
            "merl_dir": request.merl_dir,
            "selected_materials": request.selected_materials,
            "epochs": request.epochs,
            "output_dir": request.output_dir,
            "device": request.device,
        }
        log_path = LOGS_ROOT / f"train_neural_pytorch_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="train",
            params=params,
            task_type="train_neural_pytorch",
            task_label="训练 (PyTorch)",
            log_path=log_path,
        )

    async def start_neural_keras(self, request: NeuralKerasTrainRequest):
        """旧端点包装：转换为通用操作 (train)。"""
        model = self._require_model_adapter(request.model_key, "neural-keras")
        params = {
            "merl_dir": request.merl_dir,
            "selected_materials": request.selected_materials,
            "cuda_device": request.cuda_device,
            "h5_output_dir": request.h5_output_dir,
            "npy_output_dir": request.npy_output_dir,
        }
        log_path = LOGS_ROOT / f"train_neural_keras_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="train",
            params=params,
            task_type="train_neural_keras",
            task_label="训练 (Keras)",
            log_path=log_path,
        )

    async def start_neural_h5_convert(self, request: NeuralH5ConvertRequest):
        """旧端点包装：转换为通用操作 (convert)。"""
        model = self._require_model_adapter(request.model_key, "neural-keras")
        params = {
            "h5_dir": request.h5_dir,
            "selected_h5_files": request.selected_h5_files,
            "npy_output_dir": request.npy_output_dir,
        }
        log_path = LOGS_ROOT / f"train_neural_h5_convert_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="convert",
            params=params,
            task_type="train_neural_h5_convert",
            task_label="H5→NPY 转换",
            log_path=log_path,
        )

    async def start_hyper_run(self, request: HyperTrainRunRequest):
        """旧端点包装：转换为通用操作 (train)。"""
        model = self._require_model_adapter(request.model_key, "hyper-family")
        if not model.supports_training:
            raise ValueError(f"模型不支持训练: {model.key}")
        params = {
            "merl_dir": request.merl_dir,
            "output_dir": request.output_dir,
            "dataset": request.dataset,
            "epochs": request.epochs,
            "sparse_samples": request.sparse_samples,
            "kl_weight": request.kl_weight,
            "fw_weight": request.fw_weight,
            "lr": request.lr,
            "keepon": request.keepon,
            "train_subset": request.train_subset,
            "train_seed": request.train_seed,
        }
        log_path = LOGS_ROOT / f"train_hyper_run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="train",
            params=params,
            task_type="train_hyper_run",
            task_label="训练 (HyperBRDF)",
            log_path=log_path,
        )

    async def start_hyper_extract(self, request: HyperExtractRequest):
        """旧端点包装：转换为通用操作 (extract)。"""
        model = self._require_model_adapter(request.model_key, "hyper-family")
        if not model.supports_extract:
            raise ValueError(f"模型不支持参数提取: {model.key}")
        params = {
            "merl_dir": request.merl_dir,
            "selected_materials": request.selected_materials,
            "checkpoint_path": request.model_path,  # 统一命名到 checkpoint_path
            "output_dir": request.output_dir,
            "dataset": request.dataset,
            "sparse_samples": request.sparse_samples,
        }
        log_path = LOGS_ROOT / f"train_hyper_extract_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="extract",
            params=params,
            task_type="train_hyper_extract",
            task_label="参数提取",
            log_path=log_path,
        )

    async def start_hyper_decode(self, request: HyperDecodeRequest):
        """旧端点包装：转换为通用操作 (decode)。"""
        model = self._require_model_adapter(request.model_key, "hyper-family")
        if not model.supports_decode:
            raise ValueError(f"模型不支持 fullbin 解码: {model.key}")
        params = {
            "pt_dir": request.pt_dir,
            "selected_pts": request.selected_pts,
            "output_dir": request.output_dir,
            "dataset": request.dataset,
            "cuda_device": request.cuda_device,
        }
        log_path = LOGS_ROOT / f"train_hyper_decode_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="decode",
            params=params,
            task_type="train_hyper_decode",
            task_label="FullBin 解码",
            log_path=log_path,
        )

    async def start_reconstruct(self, request: ReconstructRequest):
        """旧端点包装：转换为通用操作 (reconstruct)。"""
        model = self._get_model(request.model_key)
        if not model.supports_reconstruction:
            raise ValueError(f"模型不支持重建: {model.key}")
        params = {
            "checkpoint_path": request.checkpoint_path,
            "merl_dir": request.merl_dir,
            "output_dir": request.output_dir,
            "selected_materials": request.selected_materials,
            "dataset": request.dataset,
            "sparse_samples": request.sparse_samples,
            "cuda_device": request.cuda_device,
            "neural_device": request.neural_device,
            "neural_epochs": request.neural_epochs,
        }
        log_path = LOGS_ROOT / f"reconstruct_{request.model_key}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        return await self.start_operation(
            model_key=request.model_key,
            operation_id="reconstruct",
            params=params,
            task_type="reconstruct",
            task_label="重建",
            log_path=log_path,
        )

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

    # ─── 旧 per-adapter 执行方法已删除 ───────────────────────────────────────
    # _run_neural_pytorch / _run_neural_keras / _run_neural_h5_convert /
    # _run_hyper_train / _run_hyper_extract / _run_hyper_decode / _run_reconstruct
    # 均已迁移至通用 _run_operation + operations 定义。
    # 旧 start_* wrapper 通过参数转换调用 start_operation → _run_operation。


train_service = TrainService()
