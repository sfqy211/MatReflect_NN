"""自定义模型导入服务：目录扫描、虚拟环境创建、动态注册。"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from backend.core.config import PROJECT_ROOT
from backend.core.conda import find_conda_command
from backend.models.train import ModelParameter, TrainModelItem
from backend.services.model_registry import model_registry_service


class ModelImportRequest(BaseModel):
    source_dir: str
    model_key: str
    label: str
    description: str = ""
    commands_doc_filename: str = "COMMANDS.md"
    train_script: str = ""
    train_args_template: str = ""
    reconstruct_script: str = ""
    reconstruct_args_template: str = ""
    supports_training: bool = True
    supports_reconstruction: bool = False
    supports_extract: bool = False
    supports_decode: bool = False
    supports_runs: bool = False
    render_modes: list[str] = []
    parameters: list[ModelParameter] = []


class ModelImportResponse(BaseModel):
    model_key: str
    model_dir: str
    requirements_path: str
    commands_doc: str
    conda_env: str
    status: str  # "imported" | "env_pending"


class ModelEnvStatusResponse(BaseModel):
    model_key: str
    conda_env: str
    env_exists: bool
    env_prefix: str = ""


class ModelImportService:
    # 允许的导入源路径
    SAFE_IMPORT_PATHS = [PROJECT_ROOT / "models", PROJECT_ROOT / "temp_uploads"]

    def import_model(self, request: ModelImportRequest) -> ModelImportResponse:
        source = Path(request.source_dir).resolve()

        # 路径安全校验：源目录必须在允许范围内
        if not any(source.is_relative_to(p) for p in self.SAFE_IMPORT_PATHS):
            raise ValueError(f"Source directory must be under allowed paths: {[str(p) for p in self.SAFE_IMPORT_PATHS]}")

        if not source.is_dir():
            raise ValueError(f"Source directory does not exist: {request.source_dir}")

        # Copy to models/ directory
        dest = PROJECT_ROOT / "models" / request.model_key
        if dest.exists():
            raise ValueError(f"Model directory already exists: {dest}")
        shutil.copytree(str(source), str(dest))

        # Check for requirements.txt
        requirements_file = dest / "requirements.txt"
        requirements_path = str(requirements_file) if requirements_file.exists() else ""

        # Check for commands doc
        commands_doc_file = dest / request.commands_doc_filename
        commands_doc = str(commands_doc_file) if commands_doc_file.exists() else ""

        # Generate conda env name
        conda_env = self._make_env_name(request.model_key)

        # Create model_config.json in the model directory
        config = {
            "key": request.model_key,
            "label": request.label,
            "description": request.description,
            "commands_doc": request.commands_doc_filename,
            "runtime": {
                "conda_env": conda_env,
                "working_dir": str(dest),
            },
        }
        if request.train_script:
            config["runtime"]["train_script"] = request.train_script
            config["runtime"]["train_args_template"] = request.train_args_template
        if request.reconstruct_script:
            config["runtime"]["reconstruct_script"] = request.reconstruct_script
            config["runtime"]["reconstruct_args_template"] = request.reconstruct_args_template

        config_path = dest / "model_config.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

        # Register in model_registry
        model_item = TrainModelItem(
            key=request.model_key,
            label=request.label,
            category="custom",
            adapter="custom-cli",
            built_in=False,
            description=request.description,
            supports_training=request.supports_training,
            supports_extract=request.supports_extract,
            supports_decode=request.supports_decode,
            supports_runs=request.supports_runs,
            supports_reconstruction=request.supports_reconstruction,
            model_dir=str(dest),
            requirements_path=requirements_path,
            commands_doc=commands_doc,
            parameters=request.parameters,
            render_modes=request.render_modes,
            default_paths={},
            runtime={
                "conda_env": conda_env,
                "working_dir": str(dest),
                "train_script": request.train_script,
                "train_args_template": request.train_args_template,
                "reconstruct_script": request.reconstruct_script,
                "reconstruct_args_template": request.reconstruct_args_template,
            },
        )
        model_registry_service.register_model(model_item)

        return ModelImportResponse(
            model_key=request.model_key,
            model_dir=str(dest),
            requirements_path=requirements_path,
            commands_doc=commands_doc,
            conda_env=conda_env,
            status="imported",
        )

    def delete_model(self, model_key: str) -> None:
        """删除自定义模型（先注销注册，再删除目录，保证事务性）。"""
        model = model_registry_service.get_model(model_key)
        if model.built_in:
            raise ValueError(f"Cannot delete built-in model: {model_key}")

        model_dir = Path(model.model_dir) if model.model_dir else PROJECT_ROOT / "models" / model_key

        # 先注销注册（如果后续删除目录失败，注册已移除但至少不会有残留的悬空引用）
        model_registry_service.unregister_model(model_key)

        # 再删除目录
        if model_dir.exists() and model_dir.is_dir():
            # Safety check: only delete under models/
            try:
                model_dir.relative_to(PROJECT_ROOT / "models")
            except ValueError:
                raise ValueError(f"Model directory is not under models/: {model_dir}")
            shutil.rmtree(model_dir)

    def get_env_status(self, model_key: str) -> ModelEnvStatusResponse:
        """查询模型虚拟环境状态。"""
        model = model_registry_service.get_model(model_key)
        conda_env = model.runtime.get("conda_env", "")
        env_exists = False
        env_prefix = ""
        if conda_env:
            conda_exe = find_conda_command()
            if conda_exe:
                import subprocess
                try:
                    result = subprocess.run(
                        [str(conda_exe), "env", "list", "--json"],
                        capture_output=True, text=True, timeout=30,
                    )
                    envs_data = json.loads(result.stdout)
                    for env_path in envs_data.get("envs", []):
                        if Path(env_path).name == conda_env:
                            env_exists = True
                            env_prefix = env_path
                            break
                except Exception:
                    pass

        return ModelEnvStatusResponse(
            model_key=model_key,
            conda_env=conda_env,
            env_exists=env_exists,
            env_prefix=env_prefix,
        )

    async def setup_env(self, model_key: str) -> str:
        """为模型创建 Conda 虚拟环境（异步，可能耗时）。"""
        model = model_registry_service.get_model(model_key)
        conda_env = model.runtime.get("conda_env", "")
        if not conda_env:
            raise ValueError(f"Model has no conda_env configured: {model_key}")

        requirements_path = model.requirements_path
        if not requirements_path or not Path(requirements_path).exists():
            raise ValueError(f"No requirements.txt found for model: {model_key}")

        conda_exe = find_conda_command()
        if not conda_exe:
            raise ValueError("Conda executable not found on system PATH")

        import subprocess
        # Create conda env with Python
        create_cmd = [
            str(conda_exe), "create", "-n", conda_env,
            "python=3.10", "-y",
        ]
        subprocess.run(create_cmd, capture_output=True, text=True, timeout=600)

        # Install requirements
        pip_cmd = [
            str(conda_exe), "run", "-n", conda_env,
            "pip", "install", "-r", requirements_path,
        ]
        subprocess.run(pip_cmd, capture_output=True, text=True, timeout=600)

        return conda_env

    def _make_env_name(self, model_key: str) -> str:
        short_hash = hashlib.md5(model_key.encode()).hexdigest()[:8]
        return f"matreflect-custom-{short_hash}"


model_import_service = ModelImportService()
