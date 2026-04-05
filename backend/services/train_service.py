import asyncio
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from backend.core.config import LOGS_ROOT, PROJECT_ROOT
from backend.models.common import TaskDetailResponse
from backend.models.train import (
    HyperDecodeRequest,
    HyperExtractRequest,
    HyperTrainRunRequest,
    NeuralKerasTrainRequest,
    NeuralPytorchTrainRequest,
    TrainModelItem,
    TrainModelsResponse,
    TrainProjectVariant,
    TrainRunSummary,
    TrainRunsResponse,
)
from backend.services.task_manager import task_manager


NEURAL_BRDF_DIR = PROJECT_ROOT / "Neural-BRDF"
HYPER_BRDF_DIR = PROJECT_ROOT / "HyperBRDF"
DECOUPLED_HB_DIR = PROJECT_ROOT / "DecoupledHyperBRDF"
DATA_INPUTS_BRDFS = PROJECT_ROOT / "data" / "inputs" / "binary"
DATA_INPUTS_FULLBIN = PROJECT_ROOT / "data" / "inputs" / "fullbin"
DATA_INPUTS_NPY = PROJECT_ROOT / "data" / "inputs" / "npy"
DATA_INTERMEDIATE_H5 = NEURAL_BRDF_DIR / "data" / "merl_nbrdf"
BINARY_TO_NBRDF_DIR = NEURAL_BRDF_DIR / "binary_to_nbrdf"
PYTORCH_SCRIPT = BINARY_TO_NBRDF_DIR / "pytorch_code" / "train_NBRDF_pytorch.py"
KERAS_SCRIPT = BINARY_TO_NBRDF_DIR / "binary_to_nbrdf.py"
H5_TO_NPY_SCRIPT = BINARY_TO_NBRDF_DIR / "h5_to_npy.py"


HB_PROJECTS = {
    "hyperbrdf": {
        "label": "HyperBRDF",
        "dir": HYPER_BRDF_DIR,
        "main_script": HYPER_BRDF_DIR / "main.py",
        "test_script": HYPER_BRDF_DIR / "test.py",
        "pt_to_fullbin_script": HYPER_BRDF_DIR / "pt_to_fullmerl.py",
        "default_model": HYPER_BRDF_DIR / "results" / "test" / "MERL" / "checkpoint.pt",
        "default_results_dir": HYPER_BRDF_DIR / "results",
        "default_extract_dir": HYPER_BRDF_DIR / "results" / "extracted_pts",
    },
    "decoupled": {
        "label": "DecoupledHyperBRDF",
        "dir": DECOUPLED_HB_DIR,
        "main_script": DECOUPLED_HB_DIR / "main.py",
        "test_script": DECOUPLED_HB_DIR / "test.py",
        "pt_to_fullbin_script": DECOUPLED_HB_DIR / "pt_to_fullmerl.py",
        "default_model": DECOUPLED_HB_DIR / "results" / "test" / "MERL" / "checkpoint.pt",
        "default_results_dir": DECOUPLED_HB_DIR / "results",
        "default_extract_dir": DECOUPLED_HB_DIR / "results" / "extracted_pts",
    },
}


def decode_subprocess_output(raw: bytes | str | None) -> str:
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
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def _project_config(self, project_variant: TrainProjectVariant) -> dict:
        return HB_PROJECTS[project_variant]

    def _default_conda_env(self, project_variant: TrainProjectVariant) -> str:
        return "decoupledhyperbrdf" if project_variant == "decoupled" else "hyperbrdf"

    def list_models(self) -> TrainModelsResponse:
        return TrainModelsResponse(
            items=[
                TrainModelItem(
                    key="neural-pytorch",
                    label="Neural-BRDF / PyTorch",
                    category="neural",
                    supports_training=True,
                    supports_extract=False,
                    supports_decode=False,
                    supports_runs=False,
                    default_paths={
                        "materials_dir": str(DATA_INPUTS_BRDFS),
                        "output_dir": str(DATA_INPUTS_NPY),
                    },
                ),
                TrainModelItem(
                    key="neural-keras",
                    label="Neural-BRDF / Keras",
                    category="neural",
                    supports_training=True,
                    supports_extract=False,
                    supports_decode=False,
                    supports_runs=False,
                    default_paths={
                        "materials_dir": str(DATA_INPUTS_BRDFS),
                        "h5_output_dir": str(DATA_INTERMEDIATE_H5),
                        "npy_output_dir": str(DATA_INPUTS_NPY),
                    },
                ),
                TrainModelItem(
                    key="hyperbrdf",
                    label="HyperBRDF",
                    category="hyper",
                    supports_training=True,
                    supports_extract=True,
                    supports_decode=True,
                    supports_runs=True,
                    default_paths={
                        "results_dir": str(HB_PROJECTS["hyperbrdf"]["default_results_dir"]),
                        "extract_dir": str(HB_PROJECTS["hyperbrdf"]["default_extract_dir"]),
                        "checkpoint": str(HB_PROJECTS["hyperbrdf"]["default_model"]),
                    },
                ),
                TrainModelItem(
                    key="decoupled",
                    label="DecoupledHyperBRDF",
                    category="hyper",
                    supports_training=True,
                    supports_extract=True,
                    supports_decode=True,
                    supports_runs=True,
                    default_paths={
                        "results_dir": str(HB_PROJECTS["decoupled"]["default_results_dir"]),
                        "extract_dir": str(HB_PROJECTS["decoupled"]["default_extract_dir"]),
                        "checkpoint": str(HB_PROJECTS["decoupled"]["default_model"]),
                    },
                ),
            ]
        )

    def list_runs(self, project_variant: TrainProjectVariant | None = None) -> TrainRunsResponse:
        variants = [project_variant] if project_variant else ["hyperbrdf", "decoupled"]
        items: list[TrainRunSummary] = []
        for variant in variants:
            if variant is None:
                continue
            config = self._project_config(variant)
            results_dir = Path(config["default_results_dir"])
            if not results_dir.exists():
                continue
            for args_path in results_dir.rglob("args.txt"):
                run_dir = args_path.parent
                checkpoint_path = run_dir / "checkpoint.pt"
                args_data = self._read_args(args_path)
                items.append(
                    TrainRunSummary(
                        project_variant=variant,
                        label=config["label"],
                        run_name=str(run_dir.relative_to(results_dir)),
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

    def get_task_detail(self, task_id: str, limit: int = 200) -> TaskDetailResponse | None:
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
        if process and process.returncode is None:
            process.terminate()
        await task_manager.update(task_id, status="cancelled", message="Cancellation requested", event="log")
        return True

    async def start_neural_pytorch(self, request: NeuralPytorchTrainRequest):
        log_path = LOGS_ROOT / f"train_neural_pytorch_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_neural_pytorch", "Neural-BRDF PyTorch queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_neural_pytorch(record.task_id, request, log_path, cancel_event))
        return record

    async def start_neural_keras(self, request: NeuralKerasTrainRequest):
        log_path = LOGS_ROOT / f"train_neural_keras_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_neural_keras", "Neural-BRDF Keras queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_neural_keras(record.task_id, request, log_path, cancel_event))
        return record

    async def start_hyper_run(self, request: HyperTrainRunRequest):
        log_path = LOGS_ROOT / f"train_hyper_run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_hyper_run", "HyperBRDF training queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_hyper_train(record.task_id, request, log_path, cancel_event))
        return record

    async def start_hyper_extract(self, request: HyperExtractRequest):
        log_path = LOGS_ROOT / f"train_hyper_extract_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_hyper_extract", "HyperBRDF extraction queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_hyper_extract(record.task_id, request, log_path, cancel_event))
        return record

    async def start_hyper_decode(self, request: HyperDecodeRequest):
        log_path = LOGS_ROOT / f"train_hyper_decode_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"
        record = task_manager.create("train_hyper_decode", "HyperBRDF decode queued", log_path=str(log_path))
        cancel_event = asyncio.Event()
        self._cancel_events[record.task_id] = cancel_event
        asyncio.create_task(self._run_hyper_decode(record.task_id, request, log_path, cancel_event))
        return record

    def _read_args(self, args_path: Path) -> dict:
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
        status: str | None = None,
        progress: int | None = None,
        event: str = "log",
        result_payload: dict | None = None,
    ) -> None:
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
            process = await asyncio.create_subprocess_shell(
                subprocess.list2cmdline(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd),
                env=env,
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd),
                env=env,
            )
        self._processes[task_id] = process
        try:
            while True:
                if cancel_event and cancel_event.is_set():
                    if process.returncode is None:
                        process.terminate()
                        await process.wait()
                    return -1
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
                    await self._write_log(task_id, log_path, text, progress=progress)
            return await process.wait()
        finally:
            self._processes.pop(task_id, None)

    def _make_neural_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        pythonpath_parts = [str(BINARY_TO_NBRDF_DIR), str(PYTORCH_SCRIPT.parent), env.get("PYTHONPATH", "")]
        env["PYTHONPATH"] = os.pathsep.join(part for part in pythonpath_parts if part)
        return env

    def _make_hyper_env(self, project_variant: TrainProjectVariant) -> dict[str, str]:
        config = self._project_config(project_variant)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            [str(PROJECT_ROOT), str(config["dir"]), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        return env

    def _python_runner(self, conda_env: str | None = None) -> tuple[list[str], bool]:
        conda = shutil.which("conda")
        if conda and conda_env:
            return [conda, "run", "--no-capture-output", "-n", conda_env, "python"], True
        return [sys.executable], False

    async def _run_neural_pytorch(
        self,
        task_id: str,
        request: NeuralPytorchTrainRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            ensure_exists(merl_dir)
            if not request.selected_materials:
                raise ValueError("未选择材质文件")
            output_dir = Path(request.output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            env = self._make_neural_env()
            total = len(request.selected_materials)
            generated: list[str] = []
            for index, material in enumerate(request.selected_materials):
                material_path = merl_dir / material
                ensure_exists(material_path, file_ok=True)
                cmd = [
                    "python",
                    str(PYTORCH_SCRIPT),
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
                    cwd=PYTORCH_SCRIPT.parent,
                    env=env,
                    progress=min(95, int(index / total * 100)),
                    start_message=f"[{index + 1}/{total}] 启动 Neural-BRDF PyTorch 训练: {material}",
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    await self._write_log(task_id, log_path, f"训练失败: {material} (退出码: {return_code})", status="failed", progress=100, event="done")
                    return
                generated.append(material_path.stem)
            await self._write_log(
                task_id,
                log_path,
                "Neural-BRDF PyTorch 训练完成",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "materials": generated},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"训练任务异常: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_neural_keras(
        self,
        task_id: str,
        request: NeuralKerasTrainRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            merl_dir = Path(request.merl_dir).resolve()
            ensure_exists(merl_dir)
            if not request.selected_materials:
                raise ValueError("未选择材质文件")
            h5_output_dir = Path(request.h5_output_dir).resolve()
            npy_output_dir = Path(request.npy_output_dir).resolve()
            h5_output_dir.mkdir(parents=True, exist_ok=True)
            npy_output_dir.mkdir(parents=True, exist_ok=True)
            env = self._make_neural_env()
            env["CUDA_VISIBLE_DEVICES"] = request.cuda_device
            binary_paths = [str((merl_dir / material).resolve()) for material in request.selected_materials]
            for binary_path in binary_paths:
                ensure_exists(Path(binary_path), file_ok=True)
            runner, use_shell = self._python_runner("nbrdf-train")
            train_cmd = [
                *runner,
                str(KERAS_SCRIPT),
                *binary_paths,
                "--cuda_device",
                request.cuda_device,
            ]
            train_return = await self._run_command(
                task_id,
                log_path,
                train_cmd,
                cwd=BINARY_TO_NBRDF_DIR,
                env=env,
                progress=15,
                start_message="启动 Neural-BRDF Keras 训练",
                use_shell=use_shell,
                cancel_event=cancel_event,
            )
            if train_return == -1:
                await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                return
            if train_return != 0:
                await self._write_log(task_id, log_path, f"Keras 训练失败 (退出码: {train_return})", status="failed", progress=100, event="done")
                return

            h5_paths: list[str] = []
            for material in request.selected_materials:
                basename = Path(material).stem
                src_h5 = BINARY_TO_NBRDF_DIR / f"{basename}.h5"
                src_json = BINARY_TO_NBRDF_DIR / f"{basename}.json"
                src_loss = BINARY_TO_NBRDF_DIR / f"lossplot_{basename}.png"
                target_h5 = h5_output_dir / f"{basename}.h5"
                if src_h5.exists():
                    shutil.move(str(src_h5), str(target_h5))
                    if src_json.exists():
                        shutil.move(str(src_json), str(h5_output_dir / f"{basename}.json"))
                    if src_loss.exists():
                        shutil.move(str(src_loss), str(h5_output_dir / f"lossplot_{basename}.png"))
                    h5_paths.append(str(target_h5))
                    await self._write_log(task_id, log_path, f"已归档中间文件: {basename}.h5", progress=45)
            if not h5_paths:
                await self._write_log(task_id, log_path, "训练完成但未找到生成的 .h5 文件", status="failed", progress=100, event="done")
                return

            convert_cmd = [
                *runner,
                str(H5_TO_NPY_SCRIPT),
                *h5_paths,
                "--destdir",
                str(npy_output_dir),
            ]
            convert_return = await self._run_command(
                task_id,
                log_path,
                convert_cmd,
                cwd=BINARY_TO_NBRDF_DIR,
                env=env,
                progress=65,
                start_message="启动 h5 -> npy 转换",
                use_shell=use_shell,
                cancel_event=cancel_event,
            )
            if convert_return == -1:
                await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                return
            if convert_return != 0:
                await self._write_log(task_id, log_path, f"h5 -> npy 转换失败 (退出码: {convert_return})", status="failed", progress=100, event="done")
                return
            await self._write_log(
                task_id,
                log_path,
                "Neural-BRDF Keras 训练与转换完成",
                status="success",
                progress=100,
                event="done",
                result_payload={"h5_output_dir": str(h5_output_dir), "npy_output_dir": str(npy_output_dir), "count": len(h5_paths)},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"训练任务异常: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_hyper_train(
        self,
        task_id: str,
        request: HyperTrainRunRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            config = self._project_config(request.project_variant)
            merl_dir = Path(request.merl_dir).resolve()
            output_dir = Path(request.output_dir).resolve()
            ensure_exists(merl_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            env = self._make_hyper_env(request.project_variant)
            runner, use_shell = self._python_runner(request.conda_env or self._default_conda_env(request.project_variant))
            cmd = [
                *runner,
                str(config["main_script"]),
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
            if request.project_variant == "decoupled":
                cmd.extend(
                    [
                        "--model_type",
                        request.model_type,
                        "--sampling_mode",
                        request.sampling_mode,
                        "--analytic_lobes",
                        str(request.analytic_lobes),
                        "--analytic_loss_weight",
                        str(request.analytic_loss_weight),
                        "--residual_loss_weight",
                        str(request.residual_loss_weight),
                        "--spec_loss_weight",
                        str(request.spec_loss_weight),
                        "--gate_reg_weight",
                        str(request.gate_reg_weight),
                        "--spec_percentile",
                        str(request.spec_percentile),
                        "--gate_bias_init",
                        str(request.gate_bias_init),
                        "--stage_a_epochs",
                        str(request.stage_a_epochs),
                        "--stage_b_ramp_epochs",
                        str(request.stage_b_ramp_epochs),
                    ]
                )
                if request.teacher_dir:
                    cmd.extend(["--teacher_dir", request.teacher_dir])
                if request.baseline_checkpoint:
                    cmd.extend(["--baseline_checkpoint", request.baseline_checkpoint])
            return_code = await self._run_command(
                task_id,
                log_path,
                cmd,
                cwd=Path(config["dir"]),
                env=env,
                progress=5,
                start_message=f"启动 {config['label']} 训练",
                use_shell=use_shell,
                cancel_event=cancel_event,
            )
            if return_code == -1:
                await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                return
            if return_code != 0:
                await self._write_log(task_id, log_path, f"训练失败 (退出码: {return_code})", status="failed", progress=100, event="done")
                return
            await self._write_log(
                task_id,
                log_path,
                f"{config['label']} 训练完成",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "project_variant": request.project_variant},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"训练任务异常: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_hyper_extract(
        self,
        task_id: str,
        request: HyperExtractRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            config = self._project_config(request.project_variant)
            merl_dir = Path(request.merl_dir).resolve()
            model_path = Path(request.model_path).resolve()
            output_dir = Path(request.output_dir).resolve()
            ensure_exists(merl_dir)
            ensure_exists(model_path, file_ok=True)
            if request.dataset == "MERL" and not request.selected_materials:
                raise ValueError("未选择材质文件")
            output_dir.mkdir(parents=True, exist_ok=True)
            env = self._make_hyper_env(request.project_variant)
            runner, use_shell = self._python_runner(request.conda_env or self._default_conda_env(request.project_variant))
            if request.dataset == "EPFL":
                cmd = [
                    *runner,
                    str(config["test_script"]),
                    "--model",
                    str(model_path),
                    "--binary",
                    str(merl_dir),
                    "--destdir",
                    str(output_dir),
                    "--dataset",
                    "EPFL",
                ]
                if request.project_variant == "decoupled":
                    cmd.extend(["--sparse_samples", str(request.sparse_samples)])
                return_code = await self._run_command(
                    task_id,
                    log_path,
                    cmd,
                    cwd=Path(config["dir"]),
                    env=env,
                    progress=10,
                    start_message=f"启动 {config['label']} 参数提取: EPFL",
                    use_shell=use_shell,
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    await self._write_log(task_id, log_path, f"参数提取失败 (退出码: {return_code})", status="failed", progress=100, event="done")
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
                        str(config["test_script"]),
                        "--model",
                        str(model_path),
                        "--binary",
                        str(binary_path),
                        "--destdir",
                        str(output_dir),
                        "--dataset",
                        "MERL",
                    ]
                    if request.project_variant == "decoupled":
                        cmd.extend(["--sparse_samples", str(request.sparse_samples)])
                    return_code = await self._run_command(
                        task_id,
                        log_path,
                        cmd,
                        cwd=Path(config["dir"]),
                        env=env,
                        progress=min(95, int(index / total * 100)),
                        start_message=f"[{index + 1}/{total}] 启动参数提取: {material}",
                        use_shell=use_shell,
                        cancel_event=cancel_event,
                    )
                    if return_code == -1:
                        await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                        return
                    if return_code != 0:
                        await self._write_log(task_id, log_path, f"参数提取失败: {material} (退出码: {return_code})", status="failed", progress=100, event="done")
                        return
                    processed.append(material)
            await self._write_log(
                task_id,
                log_path,
                f"{config['label']} 参数提取完成",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "project_variant": request.project_variant, "processed": processed},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"参数提取异常: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)

    async def _run_hyper_decode(
        self,
        task_id: str,
        request: HyperDecodeRequest,
        log_path: Path,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            config = self._project_config(request.project_variant)
            pt_dir = Path(request.pt_dir).resolve()
            output_dir = Path(request.output_dir).resolve()
            ensure_exists(pt_dir)
            if not request.selected_pts:
                raise ValueError("未选择 .pt 文件")
            output_dir.mkdir(parents=True, exist_ok=True)
            env = self._make_hyper_env(request.project_variant)
            env["CUDA_VISIBLE_DEVICES"] = request.cuda_device
            runner, use_shell = self._python_runner(request.conda_env or self._default_conda_env(request.project_variant))
            total = len(request.selected_pts)
            processed: list[str] = []
            for index, pt_name in enumerate(request.selected_pts):
                pt_path = pt_dir / pt_name
                ensure_exists(pt_path, file_ok=True)
                cmd = [
                    *runner,
                    str(config["pt_to_fullbin_script"]),
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
                    cwd=Path(config["dir"]),
                    env=env,
                    progress=min(95, int(index / total * 100)),
                    start_message=f"[{index + 1}/{total}] 启动 fullbin 解码: {pt_name}",
                    use_shell=use_shell,
                    cancel_event=cancel_event,
                )
                if return_code == -1:
                    await self._write_log(task_id, log_path, "任务已取消", status="cancelled", progress=100, event="done")
                    return
                if return_code != 0:
                    await self._write_log(task_id, log_path, f"fullbin 解码失败: {pt_name} (退出码: {return_code})", status="failed", progress=100, event="done")
                    return
                processed.append(pt_name)
            await self._write_log(
                task_id,
                log_path,
                f"{config['label']} fullbin 解码完成",
                status="success",
                progress=100,
                event="done",
                result_payload={"output_dir": str(output_dir), "project_variant": request.project_variant, "processed": processed},
            )
        except Exception as exc:
            await self._write_log(task_id, log_path, f"fullbin 解码异常: {exc}", status="failed", progress=100, event="done")
        finally:
            self._cancel_events.pop(task_id, None)


train_service = TrainService()
