from __future__ import annotations

from backend.models.train import TrainModelItem


def _builtin_models() -> list[TrainModelItem]:
    return [
        TrainModelItem(
            key="neural-pytorch",
            label="Neural-BRDF / PyTorch",
            category="neural",
            adapter="neural-pytorch",
            built_in=True,
            description="Neural-BRDF PyTorch 训练入口，输出 Mitsuba 可用的 .npy 权重。",
            supports_training=True,
            supports_extract=False,
            supports_decode=False,
            supports_runs=False,
            default_paths={
                "materials_dir": "data/inputs/binary",
                "output_dir": "data/inputs/npy",
            },
            runtime={
                "conda_env": "nbrdf-train",
                "working_dir": "Neural-BRDF/binary_to_nbrdf",
                "train_script": "Neural-BRDF/binary_to_nbrdf/pytorch_code/train_NBRDF_pytorch.py",
            },
        ),
        TrainModelItem(
            key="neural-keras",
            label="Neural-BRDF / Keras",
            category="neural",
            adapter="neural-keras",
            built_in=True,
            description="Neural-BRDF Keras 训练入口，先输出 .h5/.json，再转换为 .npy。",
            supports_training=True,
            supports_extract=False,
            supports_decode=False,
            supports_runs=False,
            default_paths={
                "materials_dir": "data/inputs/binary",
                "h5_output_dir": "Neural-BRDF/data/merl_nbrdf",
                "npy_output_dir": "data/inputs/npy",
            },
            runtime={
                "conda_env": "nbrdf-train",
                "working_dir": "Neural-BRDF/binary_to_nbrdf",
                "train_script": "Neural-BRDF/binary_to_nbrdf/binary_to_nbrdf.py",
                "convert_script": "Neural-BRDF/binary_to_nbrdf/h5_to_npy.py",
            },
        ),
        TrainModelItem(
            key="hyperbrdf",
            label="HyperBRDF",
            category="hyper",
            adapter="hyper-family",
            built_in=True,
            description="HyperBRDF 基线模型，支持训练、参数提取和 .fullbin 解码。",
            supports_training=True,
            supports_extract=True,
            supports_decode=True,
            supports_runs=True,
            default_paths={
                "materials_dir": "data/inputs/binary",
                "results_dir": "HyperBRDF/results",
                "extract_dir": "HyperBRDF/results/extracted_pts",
                "checkpoint": "HyperBRDF/results/test/MERL/checkpoint.pt",
            },
            runtime={
                "conda_env": "hyperbrdf",
                "working_dir": "HyperBRDF",
                "train_script": "HyperBRDF/main.py",
                "extract_script": "HyperBRDF/test.py",
                "decode_script": "HyperBRDF/pt_to_fullmerl.py",
            },
        ),
    ]


class ModelRegistryService:
    def list_models(self) -> list[TrainModelItem]:
        items = self._load_builtins()
        items.sort(key=lambda item: (item.category, item.label.lower()))
        return items

    def get_model(self, model_key: str) -> TrainModelItem:
        for item in self.list_models():
            if item.key == model_key:
                return item
        raise KeyError(model_key)

    def _load_builtins(self) -> list[TrainModelItem]:
        return _builtin_models()


model_registry_service = ModelRegistryService()
