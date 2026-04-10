# 网络模型代码接入规范

## 1. 说明

本项目当前不再支持通过前端页面或接口动态注册“自建模型”。

原因很直接：

- 新模型的训练参数、运行目录、提取脚本、解码脚本、Mitsuba 对接方式差异过大。
- 仅靠一套通用表单无法稳定覆盖不同模型的真实需求。
- 为避免错误配置导致训练、提取、渲染链路失效，新增模型统一改为“修改代码接入”。

因此，“网络模型管理”页只展示项目内已接入的内建模型，不提供新增或删除模型的 UI。

## 2. 当前已接入模型

当前模型由后端代码内建定义，位置：

- `backend/services/model_registry.py`

注意：

- 当前已经没有可编辑的外部模型注册表文件
- 也没有 `backend/config/model_registry.json` 这类动态注册入口

目前保留的模型项：

- `neural-pytorch`
- `neural-keras`
- `hyperbrdf`

这些模型会直接出现在前端“网络模型管理”页中。

## 3. 新模型接入原则

如果要接入新的自研模型，不是写注册表，也不是改配置文件，而是直接修改代码。

建议顺序：

1. 先确认新模型属于哪一类流程。
2. 再决定是复用现有适配器，还是新增适配器。
3. 最后把模型写入后端内建模型列表，并补齐训练/提取/解码链路。

## 4. 现有适配器类型

### 4.1 `neural-pytorch`

适用流程：

- `.binary -> .npy`

典型特征：

- 训练脚本直接输出 Mitsuba 可用的 `.npy`
- 通常按单材质循环训练

### 4.2 `neural-keras`

适用流程：

- `.binary -> .h5/.json -> .npy`

典型特征：

- 先训练出 `.h5`
- 再执行 `h5 -> npy` 转换

### 4.3 `hyper-family`

适用流程：

- `.binary -> checkpoint.pt -> 材质参数 .pt -> .fullbin`

典型特征：

- 支持训练
- 支持参数提取
- 支持 `.pt -> .fullbin` 解码
- 支持扫描运行记录

如果你的模型不满足以上任一协议，就不要硬塞进现有结构，应新增新的适配器类型。

## 5. 接入新模型时必须修改的位置

### 5.1 模型注册表定义

修改：

- `backend/services/model_registry.py`

在 `_builtin_models()` 中新增一个 `TrainModelItem`。

最少需要明确：

- `key`
- `label`
- `category`
- `adapter`
- `description`
- `supports_training`
- `supports_extract`
- `supports_decode`
- `supports_runs`
- `default_paths`
- `runtime`

## 5.2 训练编排

检查并按需修改：

- `backend/services/train_service.py`

需要确认新模型是否能直接复用：

- `start_neural_pytorch`
- `start_neural_keras`
- `start_neural_h5_convert`
- `start_hyper_run`
- `start_hyper_extract`
- `start_hyper_decode`

如果命令行参数协议不同，就要新增独立分支或新增新的任务入口。

## 5.3 接口层

检查并按需修改：

- `backend/api/v1/train.py`

如果只是复用已有训练协议，通常不用新增接口。

如果新模型需要新的训练/提取/解码参数，就应新增对应请求模型和 API 路由。

## 5.4 数据模型

检查并按需修改：

- `backend/models/train.py`

当现有请求结构无法承载新模型参数时，在这里增加新的请求模型字段或新增请求类型。

## 5.5 前端模型管理页

检查并按需修改：

- `frontend/src/components/ModelsWorkbench.tsx`
- `frontend/src/components/ModuleRail.tsx`
- `frontend/src/features/models/useModelsWorkbench.ts`
- `frontend/src/types/api.ts`

需要确认：

- 模型是否要出现在左侧模型列表中
- 训练表单是否需要新增字段
- 参数提取/解码区是否需要新增交互
- 运行记录是否需要显示

## 5.6 前端渲染工作台

如果新模型不仅要训练，还要进入“渲染可视化工作台”，还需要检查：

- `frontend/src/components/RenderWorkbench.tsx`
- `frontend/src/types/api.ts`
- `backend/models/render.py`
- `backend/services/render_service.py`

尤其要确认：

- 新模型在前端对应哪个 `sourceModel`
- 对应哪个 `render_mode`
- 是否需要 checkpoint
- 是否复用现有 `reconstruct` 流程
- Mitsuba 输入类型是 `.binary` / `.npy` / `.fullbin` 还是新的格式

## 6. 推荐的模型定义方式

下面是一个新增超网络类模型时的参考结构：

```python
TrainModelItem(
    key="my-hyper-model",
    label="My Hyper Model",
    category="hyper",
    adapter="hyper-family",
    built_in=True,
    description="自研超网络 BRDF 模型。",
    supports_training=True,
    supports_extract=True,
    supports_decode=True,
    supports_runs=True,
    default_paths={
        "materials_dir": "data/inputs/binary",
        "results_dir": "MyHyperModel/results",
        "extract_dir": "MyHyperModel/results/extracted_pts",
        "checkpoint": "MyHyperModel/results/test/MERL/checkpoint.pt",
    },
    runtime={
        "conda_env": "my-hyper-model",
        "working_dir": "MyHyperModel",
        "train_script": "MyHyperModel/main.py",
        "extract_script": "MyHyperModel/test.py",
        "decode_script": "MyHyperModel/pt_to_fullmerl.py",
    },
)
```

## 7. 路径与目录建议

建议把新模型代码放在项目根目录下独立目录中，例如：

```text
MyHyperModel/
  main.py
  test.py
  pt_to_fullmerl.py
  results/
    extracted_pts/
```

建议保持路径风格与现有项目一致：

- 脚本路径写项目相对路径
- 结果目录写项目相对路径
- 不要依赖项目外的绝对路径

## 8. 什么情况下必须新增适配器

以下情况不要强行复用现有 `neural-pytorch` / `neural-keras` / `hyper-family`：

- 训练命令参数完全不同
- 输出产物不是 `.npy` / `.pt` / `.fullbin`
- 提取阶段不接受当前的 `checkpoint + materials + output_dir` 协议
- 解码阶段不是 `pt -> fullbin`
- 运行记录目录结构与当前扫描逻辑不兼容

这时应：

1. 在 `backend/models/train.py` 增加新的适配器类型或新的请求模型。
2. 在 `backend/services/train_service.py` 增加新的执行逻辑。
3. 在 `backend/api/v1/train.py` 增加新的接口。
4. 在前端训练页补对应表单与调用逻辑。

## 9. 验证建议

接入新模型后，按最小闭环验证：

1. 确认模型能在“网络模型管理”页正常显示。
2. 确认默认路径会正确回填。
3. 先跑单材质、小 epoch、小样本。
4. 如果支持运行记录，确认可扫描 `args.txt` 和 `checkpoint.pt`。
5. 如果支持参数提取，确认能生成 `.pt`。
6. 如果支持解码，确认能生成 `.fullbin`。
7. 如果接入渲染链路，确认 Mitsuba 输入类型、场景 XML 选择、输出命名与分析匹配都正确。

## 10. 不建议的做法

- 不要再尝试通过 UI 动态添加模型。
- 不要引入“万能表单”来覆盖所有模型。
- 不要把模型目录放到项目根目录外。
- 不要只改前端，不改后端执行逻辑。
- 不要只改后端模型列表，不核对训练/提取/解码参数协议。

## 11. 结论

本项目接入新模型的标准方式是：

- 开发者自行修改代码接入

而不是：

- 让最终用户在界面中填写配置后动态注册

这样做更符合当前项目的研究型工具属性，也更容易保证训练、重建、渲染、分析整条链路的一致性。
