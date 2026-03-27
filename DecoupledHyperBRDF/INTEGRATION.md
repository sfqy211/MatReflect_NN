# HyperBRDF 插件集成指南

本指南旨在帮助您将 **HyperBRDF** 项目作为一个插件集成到更大的材质渲染与处理流水线中（如基于 Mitsuba 的大项目）。

## 1. 核心流水线流程

HyperBRDF 的主要作用是：**通过少量的采样点（Sparse Samples）重建出高质量的连续 BRDF 表示**，并能导出为标准的 `.fullbin` 格式。

集成流程分为以下三个主要阶段：

### 阶段 A：训练基础超网络 (One-time)
如果您需要针对特定类型的数据集（如 MERL 或 RGL）训练自己的生成器，请运行：
```bash
python main.py --destdir results/my_model --binary data/merl_data/ --dataset MERL --epochs 100
```
- **输入**: `.binary` 格式的材质数据集文件夹。
- **输出**: `results/my_model/MERL/checkpoint.pt`（这是后续步骤的核心模型）。

### 阶段 B：材质参数提取 (Encoding)
对于新的材质（即使只有部分采样数据），使用训练好的模型提取其在潜在空间（Latent Space）中的参数：
```bash
python test.py --model results/my_model/MERL/checkpoint.pt --binary data/new_material.binary --destdir results/extracted_pts/ --dataset MERL
```
- **输入**: 模型权重 `.pt` 和目标材质 `.binary`。
- **输出**: 材质特定的参数文件 `new_material.pt`（大小仅约 160KB，极大压缩）。

### 阶段 C：完整重建 (Decoding to Fullbin)
将提取的参数转换为 Mitsuba 或其他渲染器可读的完整 MERL 格式：
```bash
python pt_to_fullmerl.py results/extracted_pts/ results/full_reconstructions/ --dataset MERL
```
- **输入**: 材质参数文件夹 `.pt`。
- **输出**: `.fullbin` 文件（包含 180x90x90 个采样点，可直接用于渲染）。

---

## 2. Python API 集成示例

如果您希望在大项目中通过 Python 直接调用 HyperBRDF 的功能，可以参考以下封装：

```python
import subprocess
import os

class HyperBRDFPlugin:
    def __init__(self, project_root, model_path):
        self.root = project_root
        self.model_path = model_path
        self.python_exe = "python" # 或您的虚拟环境路径

    def extract_material_params(self, binary_path, output_dir):
        """将 .binary 转换为 .pt 参数"""
        cmd = [
            self.python_exe, os.path.join(self.root, "test.py"),
            "--model", self.model_path,
            "--binary", binary_path,
            "--destdir", output_dir,
            "--dataset", "MERL"
        ]
        subprocess.run(cmd, check=True)

    def convert_to_fullbin(self, pt_dir, fullbin_dir):
        """将 .pt 转换为 .fullbin"""
        cmd = [
            self.python_exe, os.path.join(self.root, "pt_to_fullmerl.py"),
            pt_dir, fullbin_dir,
            "--dataset", "MERL"
        ]
        subprocess.run(cmd, check=True)

# 使用示例
# plugin = HyperBRDFPlugin("./HyperBRDF", "./results/test/MERL/checkpoint.pt")
# plugin.extract_material_params("./data/alum-bronze.binary", "./my_results/pts")
# plugin.convert_to_fullbin("./my_results/pts", "./my_results/fullbin")
```

---

## 3. 注意事项与依赖关系

1.  **中位数依赖**: `pt_to_fullmerl.py` 在运行过程中需要访问 `data/merl_median.binary` 或 `data/epfl_median.npy`。请确保在调用前已运行 `python compute_median.py`。
2.  **Mitsuba 集成**: 导出的 `.fullbin` 文件符合 MERL 采样格式。在 Mitsuba 中，您可以使用 `measured` BSDF 插件加载这些文件。
3.  **设备支持**: 脚本会自动检测 CUDA。如果需要强制指定设备，可以修改 `utils/common.py` 中的 `get_device` 函数。
4.  **潜在空间**: 本项目固定使用 40 维潜在空间，这是模型架构（`models.py`）中定义的，不建议在不重新训练的情况下更改。

---

## 4. 目录结构规范
建议的大项目集成结构：
```text
MainProject/
├── HyperBRDF/          # 本项目作为子模块
├── data/               # 存放您的 .binary 原始数据
├── models/             # 存放训练好的 checkpoint.pt
└── output/             # 存放生成的 .pt 和 .fullbin
```
