# 网络模型接入开发规范

## 1. 目标

V2 的“网络模型管理”已改为注册表驱动：

- 内建模型继续保留：
  - `neural-pytorch`
  - `neural-keras`
  - `hyperbrdf`
- 开发者可以动态新增或删除自研模型。
- 固定材质库仍然是 `data/inputs/binary` 下的 100 个材质。
- “预设 20 材质”仍为前端固定集合，不随模型变化。

注册表文件：

- `backend/config/model_registry.json`

说明：

- 该文件只保存“自定义模型”。
- 内建模型由后端代码注入，不能删除。

## 2. 适配器类型

当前系统支持 3 类适配器：

1. `neural-pytorch`
   - 用于 `.binary -> .npy`
   - 单材质循环训练
   - 典型代表：Neural-BRDF PyTorch

2. `neural-keras`
   - 用于 `.binary -> .h5/.json -> .npy`
   - 先训练，再执行 h5 转 npy
   - 典型代表：Neural-BRDF Keras

3. `hyper-family`
   - 用于 `.binary -> checkpoint.pt -> 材质参数 .pt -> .fullbin`
   - 支持训练、参数提取、fullbin 解码
   - 典型代表：HyperBRDF 及兼容该脚本协议的同类模型

如果自研模型不满足以上任一流程，就不要直接接入当前系统，先扩展新的适配器。

## 3. 注册表字段

每个模型项包含以下核心字段：

```json
{
  "key": "my_model",
  "label": "My Model",
  "category": "hyper",
  "adapter": "hyper-family",
  "description": "简要说明",
  "supports_training": true,
  "supports_extract": true,
  "supports_decode": true,
  "supports_runs": true,
  "default_paths": {},
  "runtime": {},
  "adapter_options": {}
}
```

字段约束：

- `key`
  - 只能用小写字母、数字、下划线、短横线
  - 不能与内建 key 冲突
- `category`
  - `neural-pytorch` / `neural-keras` 必须是 `neural`
  - `hyper-family` 必须是 `hyper`
- 所有路径必须位于项目根目录内

## 4. 路径规范

所有运行路径都必须放在项目目录内，推荐使用相对路径，例如：

- `MyModel/main.py`
- `MyModel/test.py`
- `MyModel/pt_to_fullmerl.py`
- `MyModel/results`

不要注册仓库外绝对路径。

原因：

- 后端会校验路径必须位于项目根目录下
- 前端的 PT 文件浏览接口也只允许浏览项目根目录内的目录

## 5. 各适配器最小要求

### 5.1 `neural-pytorch`

最少需要：

- `runtime.train_script`
- `default_paths.materials_dir`
- `default_paths.output_dir`

建议同时提供：

- `runtime.conda_env`
- `runtime.working_dir`

训练脚本调用方式必须兼容：

```bash
python train_script.py <binary_path> --outpath <output_dir> --epochs <n> --device <cpu|cuda>
```

输出要求：

- 产出 Mitsuba 可用的 `.npy` 权重文件

### 5.2 `neural-keras`

最少需要：

- `runtime.train_script`
- `runtime.convert_script`
- `default_paths.materials_dir`
- `default_paths.h5_output_dir`
- `default_paths.npy_output_dir`

训练脚本调用方式必须兼容：

```bash
python train_script.py <binary1> <binary2> ... --cuda_device <id>
```

转换脚本调用方式必须兼容：

```bash
python convert_script.py <file1.h5> <file2.h5> ... --destdir <npy_output_dir>
```

输出要求：

- 训练阶段生成 `.h5`
- 转换阶段生成 `.npy`

### 5.3 `hyper-family`

最少需要：

- `runtime.train_script`
- `runtime.working_dir`

如果启用参数提取：

- `supports_extract = true`
- `runtime.extract_script`
- `default_paths.extract_dir`

如果启用 fullbin 解码：

- `supports_decode = true`
- `runtime.decode_script`
- `default_paths.extract_dir`

如果启用运行记录扫描：

- `supports_runs = true`
- `default_paths.results_dir`

训练脚本调用方式必须兼容：

```bash
python main.py \
  --destdir <output_dir> \
  --binary <merl_dir> \
  --dataset <MERL|EPFL> \
  --epochs <n> \
  --sparse_samples <n> \
  --kl_weight <v> \
  --fw_weight <v> \
  --lr <v> \
  --train_subset <n> \
  --train_seed <n>
```

如果模型支持解耦扩展参数，还需要兼容：

- `--analytic_lobes`

此能力通过：

```json
"adapter_options": {}
```

来开启。

参数提取脚本调用方式必须兼容：

```bash
python test.py --model <checkpoint> --binary <binary_or_dir> --destdir <output_dir> --dataset <MERL|EPFL>
```

如果脚本支持稀疏采样，还应兼容：

```bash
--sparse_samples <n>
```

解码脚本调用方式必须兼容：

```bash
python pt_to_fullmerl.py <pt_path> <output_dir> --dataset <MERL|EPFL> --cuda_device <id>
```

运行记录目录规范：

- `results_dir` 下每个训练 run 目录内应包含：
  - `args.txt`
  - `checkpoint.pt`
- 如果存在 `train_loss.csv`，系统会据此统计已完成 epoch 数

## 6. 建议目录结构

以一个可训练、可提取、可解码的自研超网络模型为例：

```text
MyBRDFModel/
  main.py
  test.py
  pt_to_fullmerl.py
  results/
    extracted_pts/
```

推荐注册值：

```json
{
  "key": "my-brdf-model",
  "label": "My BRDF Model",
  "category": "hyper",
  "adapter": "hyper-family",
  "description": "自研 BRDF 模型",
  "supports_training": true,
  "supports_extract": true,
  "supports_decode": true,
  "supports_runs": true,
  "default_paths": {
    "materials_dir": "data/inputs/binary",
    "results_dir": "MyBRDFModel/results",
    "extract_dir": "MyBRDFModel/results/extracted_pts",
    "checkpoint": "MyBRDFModel/results/test/MERL/checkpoint.pt"
  },
  "runtime": {
    "conda_env": "my-brdf-model",
    "working_dir": "MyBRDFModel",
    "train_script": "MyBRDFModel/main.py",
    "extract_script": "MyBRDFModel/test.py",
    "decode_script": "MyBRDFModel/pt_to_fullmerl.py"
  },
  "adapter_options": {}
}
```

## 7. 添加方式

### 7.1 使用前端 UI 添加

进入“网络模型管理”页：

1. 点击“添加自研模型”
2. 选择适配器
3. 填写脚本、结果目录、Conda 环境等信息
4. 保存模型

### 7.2 使用接口添加

接口：

- `POST /api/v1/train/models`

删除接口：

- `DELETE /api/v1/train/models/{model_key}`

查询模型：

- `GET /api/v1/train/models`

查询运行记录：

- `GET /api/v1/train/runs?model_key=<key>`

## 8. 与材质库的关系

这次改造只开放“模型”动态化，不开放“材质库”动态化：

- 100 个 MERL 材质仍是固定输入资产
- 预设 20 材质仍为固定实验子集
- 自研模型需要适配这套固定材质资产

这意味着：

- 模型可以换
- 训练/提取/解码脚本可以换
- 材质资产集合不换

## 9. 验证建议

新增模型后，按最小闭环验证：

1. 在“网络模型管理”页面确认模型已出现
2. 确认切换模型后默认路径是否正确回填
3. 如果支持运行记录，确认 run 列表能读出 `args.txt`
4. 如果支持参数提取，确认 PT 目录能列出 `.pt`
5. 优先跑单材质、小 epoch、小样本验证，不要直接跑全量实验

## 10. 不建议的做法

- 不要复用内建模型的 key
- 不要把路径指向项目根目录外
- 不要接入与现有适配器 CLI 完全不兼容的脚本
- 不要把固定材质库改成跟模型绑定的私有材质集合

如果需要支持全新的训练/提取/解码协议，应先新增后端适配器，再开放给 UI 注册表。
