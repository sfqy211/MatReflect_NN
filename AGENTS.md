# AGENTS.md

## 1. 项目定位

`MatReflect_NN` 是一个运行在 Windows 本机上的材质研究工作台。当前采用“V2 主入口 + V1 迁移期保留代码”的结构：

- V2：`React + FastAPI` 工作台，默认入口
- V1：`Streamlit` 旧版工作流，仅用于迁移核对，不再作为公开推荐入口

它把以下链路串起来：

1. 使用 Mitsuba 0.6 渲染 MERL / FullBin / NBRDF 材质。
2. 使用 Neural-BRDF 训练 `.binary -> .npy` 权重。
3. ?? HyperBRDF ?? `.binary -> checkpoint.pt -> ???? .pt -> .fullbin`?
4. 对渲染结果做预览、量化评估、网格拼图和对比拼图。

这不是一个纯 Python 库，而是“前端工作台 + 后端任务编排 + 多环境脚本 + 本地数据/结果目录”的集成项目。

## 2. 运行前提

- 默认平台：Windows + PowerShell。
- 默认入口：
  - 开发模式：`scripts/start_v2_dev.ps1`
  - 生产模式：`scripts/start_v2_prod.ps1`
- V1 旧入口：`app.py`，仓库内仍保留，但不作为默认运行方式。
- 项目大量依赖 Conda 多环境隔离。
- README 中当前约定的关键环境：
- `matreflect`：V2 backend、V1 旧入口、渲染、分析。
  - `mitsuba-build`：Mitsuba 编译，Python 2.7 + SCons。
  - `nbrdf-train`：Neural-BRDF 训练。
  - `hyperbrdf`：HyperBRDF 训练与推理。

不要假设所有功能都能在当前 Python 环境直接运行。训练页大量通过 `conda run -n ...` 调外部环境。

## 3. 目录事实

### 3.1 主工作区

- `frontend/`：V2 React 前端，当前默认 UI。
- `backend/`：V2 FastAPI 后端、任务接口、WebSocket、静态托管。
- `app.py`：V1 Streamlit 旧入口。
- `pages/`：V1 Streamlit 旧多页面入口。
- `pages/_modules/`：V1 页面逻辑与旧 action。
- `scripts/`：启动脚本与本地批处理脚本。
- `scene/`：Mitsuba 场景 XML、环境贴图、OBJ 资源。

### 3.2 模型相关目录

- `Neural-BRDF/`：Neural-BRDF 上游代码与集成说明。
- `HyperBRDF/`：原版 HyperBRDF。

### 3.3 本地数据与结果目录

- `data/inputs/binary/`：MERL `.binary` 原始材质。
- `data/inputs/npy/`：Neural-BRDF 权重，文件名成组出现，如 `mat_fc1.npy` 到 `mat_b3.npy`。
- `data/inputs/fullbin/`?HyperBRDF ???? `.fullbin`?
- `data/outputs/binary|npy|fullbin/{exr,png}/`：渲染输出。
- `data/outputs/grids/`、`data/outputs/comparisons/`：分析页生成的拼图。
- `data/batch_temp_xmls/`：渲染时动态生成的临时 XML，不应手动维护。

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

但这个仓库里有一部分上述目录已经存在并且当前副本中可见，有些内容还是已跟踪的。处理原则：

- 把这些目录视为“本地运行依赖 + 实验资产 + 上游代码混合区”。
- 不要因为它们在 `.gitignore` 里就假设可以随意清空或重建。
- 尤其不要删除：
  - `data/inputs/*`
  - `data/outputs/*`
  - `HyperBRDF/results/*`
  - `mitsuba/dist/*`

## 5. 优先修改位置

大多数集成任务现在优先改这里：

- `frontend/src/components/`
- `frontend/src/features/`
- `frontend/src/lib/`
- `backend/api/v1/`
- `backend/services/`
- `backend/models/`
- `backend/core/`
- `scripts/start_v2_*.ps1`

只有在任务明确落在 V1 兼容层或需要核对旧实现时，再优先改这里：

- `pages/_modules/render_tool_actions.py`
- `pages/_modules/render_tool_page.py`
- `pages/_modules/training_actions.py`
- `pages/_modules/training_neural_tab.py`
- `pages/_modules/training_hyper_tab.py`
- `pages/_modules/analysis_page.py`
- `pages/_modules/__init__.py`
- `scene/dj_xml/*.xml`

除非任务明确要求，否则不要优先大改：

- `mitsuba/src/`、`mitsuba/dist/` 下的第三方渲染器源码与编译产物。
- `Neural-BRDF/` 原始上游训练逻辑。
- `HyperBRDF/` 原版基线逻辑。


## 6. 当前代码中的关键耦合

### 6.1 渲染链路

- 渲染页默认从 `scene/dj_xml/` 选 XML。
- `render_tool_actions.py` 会在运行时改写 XML：
  - 自动把相对资源路径改成绝对路径。
  - 自动把 `ldrfilm` 改成 `hdrfilm`。
  - 自动改 `integrator` 和 `sampleCount`。
  - 自动定位 `id="Material"` 的 `bsdf` 节点并替换材质类型。
- 输出文件默认带时间戳后缀：`%d_%H%M%S`。
- `skip_existing` 的判定不是精确文件名匹配，而是按材质名+后缀前缀匹配。

如果改动渲染文件命名规则、目录规则或材质替换规则，必须同时检查分析页的匹配逻辑。

### 6.2 Neural-BRDF 链路

- V2 / V1 最终都会把 `.binary` 送给 `Neural-BRDF/binary_to_nbrdf/pytorch_code/train_NBRDF_pytorch.py`。
- PyTorch 版本直接输出 6 个 `.npy` 文件。
- Keras 版本先产出 `.h5/.json`，再调用 `h5_to_npy.py` 转换。
- NBRDF 渲染依赖 Mitsuba 插件 `nbrdf_npy.dll`，并要求 XML 中 `nn_basename` 指向权重前缀。

### 6.3 HyperBRDF ??

- 当前主链路通过 `backend/services/train_service.py` 统一调度：
  - `main.py` 训练
  - `test.py` 提取材质参数 `.pt`
  - `pt_to_fullmerl.py` 转 `.fullbin`
- V1 兼容链路仍存在于 `pages/_modules/training_actions.py`
- `fit_analytic_teacher.py` 仍属于 Decoupled 研究能力，但暂未单独迁成 V2 独立面板
- Decoupled 版本已经扩展了：
  - analytic / residual / gate 相关超参数
- `training_hyper_tab.py` 会读取 `results/**/args.txt` 和 `train_loss.csv` 反推训练信息。

如果改 `.pt` 参数格式或训练产物布局，必须同时改：

- `training_actions.py`
- `training_hyper_tab.py`
- `HyperBRDF/test.py`
- `HyperBRDF/pt_to_fullmerl.py`

## 7. 编辑约束

- 优先保持 Windows 兼容。
- 路径处理优先使用 `pathlib.Path` 或显式 `os.path`，不要混入只适合 Unix 的假设。
- UI 文案当前以中文为主，可以保留必要英文括注，编码使用UTF-8。
- 不要把本地绝对路径硬编码得更死，除非该文件本来就是本地脚本。
- `scripts/test_example_mitsuba_variants.ps1` 明显是本地实验脚本，含仓库外 Mitsuba 路径；除非用户明确要求，不要把它“标准化”为通用方案。
- 为避免Windows系统下补丁体积太大无法直接写入，在有大量代码写入时使用分块写入，超过500行以上，请分块写入。

## 8. 验证建议

优先做最小闭环验证，不要默认跑重训练。

### 8.1 UI / 集成改动

- 在 `matreflect` 环境下运行：
  - V2 开发：`scripts/start_v2_dev.ps1`
  - V2 生产：`scripts/start_v2_prod.ps1`
  - V1 旧入口：仅在迁移核对场景下按需使用

### 8.1.1 编译辅助改动

- 先验证：
  - V2 设置页是否能读取到 `compile_defaults`
  - 是否能在设置页启动 Mitsuba 编译任务
  - WebSocket 日志是否持续推送
  - 停止编译后任务状态是否变为 `cancelled`

### 8.2 渲染改动

- 先验证：
  - Mitsuba 路径能否被 `pages/_modules/__init__.py` 检测到。
  - `scene/dj_xml/*.xml` 是否仍有 `id="Material"`。
  - 生成的临时 XML 是否落在 `data/batch_temp_xmls/`。

### 8.3 训练改动

- Neural-BRDF：优先单材质、小 epoch。
- HyperBRDF / Decoupled：优先单材质提取或小规模训练子集，不要直接跑全量 100 epoch。

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
- V1 主应用：`app.py`
- V2 设置页容器：`frontend/src/components/WorkspaceCanvas.tsx`
- V2 渲染逻辑：`backend/api/v1/render.py`、`backend/services/`
- V2 系统与编译逻辑：`backend/api/v1/system.py`、`backend/services/system_service.py`
- V2 训练编排：`backend/services/train_service.py`
- V2 分析页：`frontend/src/components/AnalysisWorkbench.tsx`
- V1 渲染逻辑：`pages/_modules/render_tool_actions.py`
- V1 训练编排：`pages/_modules/training_actions.py`
- V1 分析页：`pages/_modules/analysis_page.py`
- HyperBRDF 基线训练：`HyperBRDF/main.py`
- V2 启动脚本：`scripts/start_v2_dev.ps1`
- V1 旧启动脚本：`scripts/start_matreflect.ps1`
