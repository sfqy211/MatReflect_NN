# 训练链路

## 核心文件

- 后端：`backend/api/v1/train.py` + `backend/services/train_service.py`
- 模型定义：`backend/services/model_registry.py`
- 前端：`frontend/src/components/ModelsWorkbench.tsx` + `frontend/src/features/models/useModelsWorkbench.ts`

## 内建模型

模型通过 `model_registry.py` 代码内建，共三个：

| key | 标签 | adapter | 能力 |
|---|---|---|---|
| `neural-pytorch` | Neural-BRDF / PyTorch | `neural-pytorch` | 训练 |
| `neural-keras` | Neural-BRDF / Keras | `neural-keras` | 训练、H5→NPY |
| `hyperbrdf` | HyperBRDF | `hyper-family` | 训练、提取、解码、运行记录 |

## Neural-BRDF (PyTorch)

- 脚本：`Neural-BRDF/binary_to_nbrdf/pytorch_code/train_NBRDF_pytorch.py`
- 流程：`.binary → .npy`
- API：`POST /api/v1/train/neural/pytorch`
- 可指定 `--epochs`、`--device`

## Neural-BRDF (Keras)

- 训练脚本：`Neural-BRDF/binary_to_nbrdf/binary_to_nbrdf.py`
- 转换脚本：`Neural-BRDF/binary_to_nbrdf/h5_to_npy.py`
- 流程：`.binary → .h5 + .json → .npy`
- API：`POST /api/v1/train/neural/keras`（训练） + `POST /api/v1/train/neural/keras/convert`（独立转换）

## HyperBRDF

- 训练脚本：`HyperBRDF/main.py`
- 提取脚本：`HyperBRDF/test.py`
- 解码脚本：`HyperBRDF/pt_to_fullmerl.py`
- API：
  - `POST /api/v1/train/hyper/run` — 训练
  - `POST /api/v1/train/hyper/extract` — 参数提取（`.binary → .pt`）
  - `POST /api/v1/train/hyper/decode` — 解码（`.pt → .fullbin`）
- 支持数据集：`MERL` / `EPFL`

## 运行记录

模型管理页的运行记录来自 `results_dir` 下递归扫描 `args.txt`：
- 同级检查 `checkpoint.pt`
- 若存在 `train_loss.csv`，估算 epoch 数
- 当前仅 `hyper-family` adapter 支持运行记录

## 当前模型页不支持

- 动态注册新模型
- 动态删除模型

如需接入新模型，当前标准做法是修改 `model_registry.py`。
