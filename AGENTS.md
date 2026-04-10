# AGENTS.md

## 1. 项目定位

`MatReflect_NN` 是一个运行在 Windows 本机上的材质研究工作台，当前只保留 V2 架构：

- 前端：`React + Vite`
- 后端：`FastAPI + WebSocket`

它串联以下链路：

1. 使用 Mitsuba 0.6 渲染 MERL / FullBin / NBRDF 材质。
2. 使用 Neural-BRDF 训练 `.binary -> .npy` 权重。
3. 使用 HyperBRDF 完成 `.binary -> checkpoint.pt -> .pt -> .fullbin`。
4. 对渲染结果做预览、量化评估、网格拼图和对比拼图。

这不是一个纯 Python 库，而是“前端工作台 + 后端任务编排 + 多环境脚本 + 本地数据/结果目录”的集成项目。

## 2. 运行前提

- 默认平台：Windows + PowerShell。
- 默认入口：
  - 开发模式：`scripts/start_v2_dev.ps1`
  - 生产模式：`scripts/start_v2_prod.ps1`
- 项目大量依赖 Conda 多环境隔离。
- 当前关键环境：
  - `matreflect`：V2 backend、渲染、分析。
  - `mitsuba-build`：Mitsuba 编译，Python 2.7 + SCons。
  - `nbrdf-train`：Neural-BRDF 训练与 `h5 -> npy` 转换。
  - `hyperbrdf`：HyperBRDF 训练、参数提取、解码。

不要假设所有功能都能在当前 Python 环境直接运行。训练页大量通过 `conda run -n ...` 调外部环境。

## 3. 目录事实

### 3.1 主工作区

- `frontend/`：V2 React 前端。
- `backend/`：V2 FastAPI 后端、任务接口、WebSocket、静态托管。
- `scripts/`：启动脚本与本地批处理脚本。
- `scene/`：Mitsuba 场景 XML、环境贴图、OBJ 资源。

### 3.2 模型相关目录

- `Neural-BRDF/`：Neural-BRDF 上游代码与集成说明。
- `HyperBRDF/`：HyperBRDF 上游代码。

### 3.3 本地数据与结果目录

- `data/inputs/binary/`：MERL `.binary` 原始材质。
- `data/inputs/npy/`：Neural-BRDF 权重。
- `data/inputs/fullbin/`：HyperBRDF 解码得到的 `.fullbin`。
- `data/outputs/binary|npy|fullbin/{exr,png}/`：渲染输出。
- `data/outputs/grids/`、`data/outputs/comparisons/`：分析模块生成的拼图。
- `data/batch_temp_xmls/`：渲染时动态生成的临时 XML。

## 4. `.gitignore` 的实际含义

根 `.gitignore` 忽略了这些路径：

- `data/`
- `__pycache__/`
- `*.log`
- `mitsuba/`
- `HyperBRDF/`
- `Neural-BRDF/`
- `.vscode/`
- `.claude`
- `results/`
- `mitsuba_merl_npy_fullbin/`

处理原则：

- 把这些目录视为“本地运行依赖 + 实验资产 + 上游代码混合区”。
- 不要因为它们在 `.gitignore` 里就假设可以随意清空或重建。
- 尤其不要删除：
  - `data/inputs/*`
  - `data/outputs/*`
  - `HyperBRDF/results/*`
  - `mitsuba/dist/*`

## 5. 优先修改位置

大多数集成任务优先改这里：

- `frontend/src/components/`
- `frontend/src/features/`
- `frontend/src/lib/`
- `frontend/src/types/`
- `backend/api/v1/`
- `backend/services/`
- `backend/models/`
- `backend/core/`
- `scripts/start_v2_*.ps1`

除非任务明确要求，否则不要优先大改：

- `mitsuba/src/`、`mitsuba/dist/` 下的第三方渲染器源码与编译产物。
- `Neural-BRDF/` 原始上游训练逻辑。
- `HyperBRDF/` 原版基线逻辑。

## 6. 当前代码中的关键耦合

### 6.1 渲染链路

- 渲染页默认从 `scene/dj_xml/` 选 XML。
- 后端会在运行时改写 XML：
  - 把相对资源路径改成绝对路径。
  - 把 `ldrfilm` 改成 `hdrfilm`。
  - 改 `integrator` 和 `sampleCount`。
  - 定位 `id="Material"` 的 `bsdf` 节点并替换材质类型。
- 输出文件默认带时间戳后缀：`%d_%H%M%S`。
- `skip_existing` 不是精确文件名匹配，而是按材质名+后缀前缀匹配。

如果改动渲染文件命名规则、目录规则或材质替换规则，必须同时检查分析页的匹配逻辑。

### 6.2 Neural-BRDF 链路

- V2 会把 `.binary` 送给 `Neural-BRDF/binary_to_nbrdf/pytorch_code/train_NBRDF_pytorch.py`。
- PyTorch 版本直接输出 6 个 `.npy` 文件。
- Keras 版本先产出 `.h5/.json`，再调用 `h5_to_npy.py` 转换。
- `h5_to_npy.py` 当前已为仓库内环境兼容做过适配。
- NBRDF 渲染依赖 Mitsuba 插件 `nbrdf_npy.dll`，并要求 XML 中 `nn_basename` 指向权重前缀。

### 6.3 HyperBRDF 链路

- 当前主链路通过 `backend/services/train_service.py` 统一调度：
  - `main.py` 训练
  - `test.py` 提取材质参数 `.pt`
  - `pt_to_fullmerl.py` 转 `.fullbin`
- 如果改 `.pt` 参数格式或训练产物布局，必须同时检查：
  - `backend/services/train_service.py`
  - `backend/services/model_registry.py`
  - `HyperBRDF/test.py`
  - `HyperBRDF/pt_to_fullmerl.py`

## 7. 编辑约束

- 优先保持 Windows 兼容。
- 路径处理优先使用 `pathlib.Path` 或显式 `os.path`。
- UI 文案当前以中文为主，可以保留必要英文括注，编码使用 UTF-8。
- 不要把本地绝对路径硬编码得更死，除非该文件本来就是本地脚本。
- `scripts/test_example_mitsuba_variants.ps1` 是本地实验脚本；除非用户明确要求，不要把它标准化为通用方案。
- 为避免 Windows 下补丁体积过大，在有大量代码写入时使用分块写入。

## 8. 验证建议

优先做最小闭环验证，不要默认跑重训练。

### 8.1 UI / 集成改动

- 在 `matreflect` 环境下运行：
  - `scripts/start_v2_dev.ps1`
  - `scripts/start_v2_prod.ps1`

### 8.2 渲染改动

- 检查：
  - `scene/dj_xml/*.xml` 是否仍有 `id="Material"`。
  - 生成的临时 XML 是否落在 `data/batch_temp_xmls/`。
  - 默认场景是否仍符合当前材质类型分流逻辑。

### 8.3 训练改动

- Neural-BRDF：优先单材质、小 epoch 或单个 `.h5` 转换。
- HyperBRDF：优先单材质提取或小规模训练子集，不要直接跑全量 100 epoch。

### 8.4 分析改动

- 检查：
  - 图片预览是否还能找到 `png` 目录。
  - 量化评估是否还能匹配 GT / FullBin / NPY 文件名。
  - 对比拼图是否还能处理带时间戳文件名。

## 9. 给后续代理的工作方式建议

1. 先看 `git status`，不要覆盖用户本地实验修改。
2. 先分清任务落在哪一层：
   - UI 集成层
   - 训练编排层
   - 模型实现层
   - Mitsuba 场景/插件层
3. 涉及输出命名、目录结构或参数格式时，沿链路检查上下游。
4. 不要把 `data/`、`results/`、`mitsuba/dist/` 当作可随意重建的缓存。
5. 只有在任务明确要求时，才深入修改 `mitsuba/`、`HyperBRDF/`、`Neural-BRDF/` 的上游基础代码。

## 10. 常用入口

- V2 前端入口：`frontend/src/App.tsx`
- V2 后端入口：`backend/main.py`
- V2 渲染逻辑：`backend/api/v1/render.py`、`backend/services/render_service.py`
- V2 系统与编译逻辑：`backend/api/v1/system.py`、`backend/services/system_service.py`
- V2 训练编排：`backend/services/train_service.py`
- V2 分析页：`frontend/src/components/AnalysisWorkbench.tsx`
- HyperBRDF 基线训练：`HyperBRDF/main.py`
- V2 启动脚本：`scripts/start_v2_dev.ps1`
- V2 生产脚本：`scripts/start_v2_prod.ps1`
