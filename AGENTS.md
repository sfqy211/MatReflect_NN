# AGENTS.md

## 1. 项目定位

`MatReflect_NN` 当前是一个仅保留 V2 架构的 Windows 本地材质研究工作台。

核心组成：

- 前端：`React + Vite`
- 后端：`FastAPI + WebSocket`
- 桌面封装：`pywebview + PyInstaller`
- 训练 / 渲染调度：多 `Conda` 环境 + 本地 Mitsuba / 上游模型代码

它不是一个纯 Python 包，也不是单纯的前端项目，而是一个“本地工作台 + 任务编排 + 第三方研究代码集成 + 本地数据资产目录”的集成系统。

当前主链路包括：

1. MERL `.binary` / NBRDF `.npy` / FullBin `.fullbin` 的 Mitsuba 渲染。
2. Neural-BRDF 的训练与 `h5 -> npy` 转换。
3. HyperBRDF 的训练、参数提取、`pt -> fullbin` 解码。
4. 渲染结果的预览、量化评估、网格拼图、对比拼图。
5. Mitsuba 编译辅助、依赖路径管理、虚拟环境管理、桌面模式启动。

## 2. 当前真实架构

### 2.1 前端模块

当前前端只保留四个工作模块：

- `render`：渲染可视化工作台
- `analysis`：材质结果分析
- `models`：网络模型管理
- `settings`：系统设置

主入口：

- `frontend/src/App.tsx`
- `frontend/src/components/WorkspaceCanvas.tsx`
- `frontend/src/components/ModuleRail.tsx`

### 2.2 后端模块

后端统一挂在 `backend/main.py`：

- API 前缀：`/api/v1`
- 媒体输出挂载：`/media/outputs`
- WebSocket：
  - `/ws/tasks/{task_id}`
  - `/ws/system/metrics`

后端路由：

- `backend/api/v1/render.py`
- `backend/api/v1/analysis.py`
- `backend/api/v1/train.py`
- `backend/api/v1/system.py`
- `backend/api/v1/fs.py`

### 2.3 桌面模式

当前桌面模式已经是正式链路的一部分，不是临时实验：

- 启动器：`desktop/launcher.py`
- 启动脚本：`scripts/start_v2_desktop.ps1`
- 打包脚本：`scripts/build_v2_desktop.ps1`

桌面模式会：

- 先使用已有 `frontend/dist`
- 在本地线程内启动 FastAPI
- 再用 `pywebview` 打开窗口

它依赖当前工作区，不会把 `data/`、`scene/`、`mitsuba/`、Conda 环境全部重新打包成独立资源。

## 3. 运行前提

- 默认平台：Windows + PowerShell
- 默认 Conda：Miniconda / Anaconda
- 当前关键环境：
  - `matreflect`：后端、分析、桌面封装
  - `mitsuba-build`：Mitsuba 编译
  - `nbrdf-train`：Neural-BRDF 训练 / 转换
  - `hyperbrdf`：HyperBRDF 训练 / 提取 / 解码

常用入口：

- 开发模式：`scripts/start_v2_dev.ps1`
- 生产模式：`scripts/start_v2_prod.ps1`
- 桌面模式：`scripts/start_v2_desktop.ps1`
- 桌面打包：`scripts/build_v2_desktop.ps1`

重要事实：

- `scripts/start_v2_dev.ps1` 会分别拉起后端和前端两个 PowerShell 窗口。
- 开发模式后端实际通过 `python -m backend.run_server` 启动，而不是直接 `uvicorn backend.main:app`。
- `backend/run_server.py` 会显式设置 Windows `ProactorEventLoopPolicy`，这是为了兼容子进程调用。

## 4. 目录事实

### 4.1 核心工作区

- `frontend/`：V2 React 前端
- `backend/`：V2 FastAPI 后端
- `desktop/`：桌面启动器、PyInstaller spec、桌面说明
- `scripts/`：开发 / 生产 / 桌面 / 打包脚本
- `scene/`：Mitsuba XML、环境图、OBJ

### 4.2 上游模型代码

- `Neural-BRDF/`
- `HyperBRDF/`
- `mitsuba/`

这些目录多数属于本地依赖或上游代码，不应当默认进行大改。

### 4.3 数据目录

- `data/inputs/binary/`：MERL `.binary`
- `data/inputs/npy/`：Neural-BRDF 权重
- `data/inputs/fullbin/`：FullBin 输入
- `data/outputs/binary/{exr,png}/`
- `data/outputs/npy/{exr,png}/`
- `data/outputs/fullbin/{exr,png}/`
- `data/outputs/grids/`
- `data/outputs/comparisons/`

### 4.4 运行时目录

当前项目真实使用的运行时目录是：

- `backend/runtime/logs/`
- `backend/runtime/tasks/`
- `backend/runtime/render_xml/`
- `backend/runtime/system_settings.json`

不要再把旧文档中的 `data/batch_temp_xmls/` 当成当前路径。  
当前渲染临时 XML 写入的是 `backend/runtime/render_xml/`。

## 5. `.gitignore` 的实际含义

当前根 `.gitignore` 忽略了这些关键目录：

- `data/`
- `mitsuba/`
- `HyperBRDF/`
- `Neural-BRDF/`
- `backend/runtime/`
- `frontend/node_modules/`
- `frontend/dist/`
- `desktop/build/`
- `desktop/dist/`
- `*.log`

处理原则：

- 忽略不等于可以随意删除。
- 这些目录里同时包含：
  - 本地依赖
  - 用户实验资产
  - 运行输出
  - 构建产物
  - 任务日志

尤其不要默认清理：

- `data/inputs/*`
- `data/outputs/*`
- `HyperBRDF/results/*`
- `mitsuba/dist/*`
- `backend/runtime/system_settings.json`
- `backend/runtime/tasks/*`

## 6. 当前代码中的关键事实

### 6.1 模型管理为“代码内建”

真实定义位置：

- `backend/services/model_registry.py`

当前内建模型只有：

- `neural-pytorch`
- `neural-keras`
- `hyperbrdf`

如果未来要接入新模型，当前标准做法是直接修改代码，而不是写注册表。

### 6.2 设置页已经接管系统配置

设置页当前不是静态展示页，而是正式配置入口。

配置模型：

- `backend/models/system.py`
- `backend/core/system_settings.py`
- `backend/services/system_service.py`

当前可持久化的内容包括：

- 项目路径
- `mitsuba.exe`
- `mtsutil.exe`
- Mitsuba 编译命令
- `vcvarsall` 路径
- 编译工作目录
- 依赖路径列表
- 虚拟环境列表

配置保存位置：

- `backend/runtime/system_settings.json`

路径解析入口：

- `backend/core/paths.py`

`get_mitsuba_paths()` 会优先读设置；如果设置失效，会回退到：

- 项目内 `mitsuba/dist`
- 否则 `d:\mitsuba\dist`

### 6.3 后端任务是持久化的

任务管理不是内存态临时对象，而是会写磁盘：

- `backend/services/task_manager.py`

行为要点：

- 每个任务会写入 `backend/runtime/tasks/*.json`
- 日志写入 `backend/runtime/logs/*.log`
- WebSocket 会推送 `snapshot/log/done`
- 服务重启后，之前处于 `pending/running` 的任务会被标记为 `failed`

### 6.4 子进程调用已经切到线程封装

当前渲染 / 训练 / 编译都不再直接依赖 `asyncio.create_subprocess_exec`。

统一封装：

- `backend/core/threaded_subprocess.py`

这样做的原因是：

- Windows + Uvicorn reload + asyncio 子进程在本项目里容易出兼容问题
- 之前出现过 `NotImplementedError`

如果未来修改任务执行逻辑，优先复用：

- `run_process_streaming`
- `terminate_process`

不要轻易改回原生 `asyncio.create_subprocess_*`

## 7. 渲染链路

核心文件：

- `backend/api/v1/render.py`
- `backend/services/render_service.py`
- `frontend/src/components/RenderWorkbench.tsx`

### 7.1 输入模式

当前渲染模式由模型映射得到：

- `gt` -> `brdfs`
- `neural` -> `npy`
- `hyperbrdf` -> `fullbin`

渲染页当前工作模式只有：

- `仅渲染`
- `仅重建`

虽然 `backend/services/render_service.py` 仍保留 `render_after_reconstruct` 支持，但前端当前没有开放“重建并渲染”按钮。

### 7.2 默认场景

默认场景选择逻辑在 `render_service.py`：

- `fullbin` 优先 `scene/dj_xml/hyperbrdf_ref.xml`
- 其它模式优先 `scene/dj_xml/scene_universal.xml`
- 仍会回退搜索 `scene/old_xml/`

### 7.3 运行时 XML 改写

后端渲染前会：

- 读取原始 XML
- 将相对资源路径改为绝对路径
- 将 `ldrfilm` 替换为 `hdrfilm`
- 更新 `integrator`
- 更新 `sampleCount`
- 查找 `id="Material"` 或兼容类型的 `bsdf`
- 按输入类型重写材质节点

关键函数：

- `find_target_bsdf`
- `update_bsdf_for_mode`
- `update_integrator_and_sampler`

### 7.4 FullBin / Binary 的特殊逻辑

`fullbin` 模式并不意味着所有文件都一定走 `fullmerl`：

- 若文件尺寸匹配标准 MERL `.binary`
- `render_service.py` 会自动改用 `merl`

也就是说：

- `data/inputs/fullbin/` 中如果混入 `.binary`
- 当前代码仍可能按 MERL 路径渲染

### 7.5 输出命名

当前渲染输出命名规则已经改为：

- `材质名_YYYYMMDD_HHMMSS`

例如：

- `chrome_20260410_143015.png`

当前这套新命名由以下代码共同处理：

- 后端生成：`backend/services/render_service.py`
- 前端解析：`frontend/src/lib/fileNames.ts`
- 分析匹配：`backend/services/analysis_service.py`

兼容性事实：

- 前端与分析模块仍兼容旧格式 `材质名_DD_HHMMSS`
- 修改命名规则时，必须同时检查这三处

## 8. 训练链路

核心文件：

- `backend/api/v1/train.py`
- `backend/services/train_service.py`
- `frontend/src/components/ModelsWorkbench.tsx`

### 8.1 Neural-BRDF

PyTorch：

- 脚本：`Neural-BRDF/binary_to_nbrdf/pytorch_code/train_NBRDF_pytorch.py`
- 输出：`.npy`

Keras：

- 训练脚本：`Neural-BRDF/binary_to_nbrdf/binary_to_nbrdf.py`
- 转换脚本：`Neural-BRDF/binary_to_nbrdf/h5_to_npy.py`
- 流程：`.binary -> .h5/.json -> .npy`

### 8.2 HyperBRDF

主链路：

- 训练：`HyperBRDF/main.py`
- 参数提取：`HyperBRDF/test.py`
- 解码：`HyperBRDF/pt_to_fullmerl.py`

模型管理页中的“运行记录”来自：

- `results_dir` 下递归扫描 `args.txt`
- 同级检查 `checkpoint.pt`
- 若存在 `train_loss.csv`，会估算 epoch 数

### 8.3 模型页当前能力

当前模型页支持：

- 固定材质选择
- Neural PyTorch 训练
- Neural Keras 训练
- `H5 -> NPY` 转换
- HyperBRDF 训练
- HyperBRDF 参数提取
- HyperBRDF `PT -> FullBin`
- 运行记录读取

当前模型页不支持：

- 动态注册新模型
- 动态删除模型

## 9. 分析链路

核心文件：

- `backend/services/analysis_service.py`
- `frontend/src/components/AnalysisWorkbench.tsx`
- `frontend/src/lib/fileNames.ts`

当前分析模块支持：

- 图片预览
- 图片删除，并可级联删除同名 `exr`
- PSNR / SSIM / Delta E 量化评估
- 网格拼图
- 对比拼图
- 图片滑块对比

匹配原则：

- 默认不是按完整文件名严格匹配
- 而是先归一化材质名，再比较

归一化会去掉：

- 新时间戳 `_YYYYMMDD_HHMMSS`
- 旧时间戳 `_DD_HHMMSS`
- `_fc1`
- `.binary`
- `.fullbin`

因此：

- 如果你修改输出文件命名规则
- 或修改 NPY / FullBin 文件命名方式
- 必须同步检查 `analysis_service.py` 和 `fileNames.ts`

## 10. 文件系统与路径 API

当前文件浏览有两类 API：

- 安全路径键：`/api/v1/fs/list`
- 任意工作区相对路径：`/api/v1/fs/list-path`

实现文件：

- `backend/services/file_service.py`
- `backend/core/paths.py`

关键约束：

- `list-path` 仍然只能访问项目根目录内的路径
- 会自动创建目录
- 不允许越过 `PROJECT_ROOT`

如果新增页面要浏览文件，优先复用这套路径约束，不要自行写新的裸路径访问逻辑。

## 11. 桌面封装链路

桌面相关文件：

- `desktop/launcher.py`
- `desktop/MatReflectNNDesktop.spec`
- `desktop/README.md`

关键事实：

- 桌面模式要求 `frontend/dist/index.html` 存在
- 启动器会自动探测项目根目录
- 会设置：
  - `MATREFLECT_PROJECT_ROOT`
  - `MATREFLECT_RUNTIME_ROOT`
  - `MATREFLECT_OUTPUTS_ROOT`

如果改桌面模式：

- 不只要看 `desktop/launcher.py`
- 还要同步检查：
  - `backend/core/config.py`
  - `backend/main.py`
  - `scripts/start_v2_desktop.ps1`
  - `scripts/build_v2_desktop.ps1`

## 12. 优先修改位置

大多数集成任务优先改这些位置：

- `frontend/src/components/`
- `frontend/src/features/`
- `frontend/src/lib/`
- `frontend/src/types/`
- `backend/api/v1/`
- `backend/services/`
- `backend/models/`
- `backend/core/`
- `desktop/`
- `scripts/start_v2_*.ps1`

除非任务明确要求，否则不要优先大改：

- `mitsuba/src/`
- `mitsuba/dist/`
- `Neural-BRDF/`
- `HyperBRDF/`

## 13. 编辑约束

- 优先保持 Windows 兼容。
- 路径处理优先 `pathlib.Path`。
- 尽量让路径仍然限制在 `PROJECT_ROOT` 内。
- 前端文案当前以中文为主。
- 设置页已经允许用户修改路径，不要再随意写死本地绝对路径。
- 若改输出命名、结果目录、脚本参数，必须沿链路检查上下游。

额外提醒：

- 旧文档里可能仍有 V1 / Streamlit 残留说法。
- 当前开发应以现有 V2 代码为准，而不是以旧文档为准。

## 14. 验证建议

优先最小闭环验证，不要默认跑重训练。

### 14.1 前后端改动

- 后端导入检查：`python -c "import backend.main"`
- 前端类型检查：`frontend\\node_modules\\.bin\\tsc.cmd --noEmit`

### 14.2 UI 联调

- 开发模式：`scripts/start_v2_dev.ps1`
- 生产模式：`scripts/start_v2_prod.ps1`

### 14.3 桌面模式

- `scripts/start_v2_desktop.ps1`

若桌面打不开，优先检查：

- `frontend/dist`
- `desktop/requirements.txt`
- `WebView2`
- `desktop/launcher.py`

### 14.4 渲染改动

检查：

- `scene/dj_xml/*.xml` 中目标材质节点是否仍可定位
- `backend/runtime/render_xml/` 是否生成临时 XML
- `data/outputs/*/{exr,png}` 是否产生新结果
- 新命名是否仍被前端和分析模块识别

### 14.5 训练改动

- Neural：单材质、小 epoch 或单个 `.h5` 转换
- HyperBRDF：单材质提取或小样本训练

### 14.6 分析改动

检查：

- 预览页是否能读到 `png`
- 量化评估是否还能匹配 GT / FullBin / NPY
- 拼图是否还能处理新旧时间戳

## 15. 给后续代理的工作方式建议

1. 先看 `git status`，不要覆盖用户本地实验修改。
2. 遇到“文档与代码不一致”时，优先信代码。
3. 先判断任务落在：
   - 前端 UI
   - 后端 API
   - 任务编排
   - 文件系统 / 路径
   - Mitsuba / 上游模型
   - 桌面封装
4. 只要涉及输出命名、目录结构、脚本参数、路径解析，就沿上下游全链路检查。
5. 不要把 `data/`、`backend/runtime/`、`HyperBRDF/results/`、`mitsuba/dist/` 当作可随意重建的缓存。
6. 非必要不要直接大改上游项目目录。
7. 若要接入新模型，当前标准方式是改代码，不是恢复动态注册表。

## 16. 常用入口

- 前端入口：`frontend/src/App.tsx`
- 工作区总入口：`frontend/src/components/WorkspaceCanvas.tsx`
- 渲染工作台：`frontend/src/components/RenderWorkbench.tsx`
- 分析工作台：`frontend/src/components/AnalysisWorkbench.tsx`
- 模型工作台：`frontend/src/components/ModelsWorkbench.tsx`
- 后端入口：`backend/main.py`
- Windows 安全启动入口：`backend/run_server.py`
- 渲染服务：`backend/services/render_service.py`
- 训练服务：`backend/services/train_service.py`
- 系统服务：`backend/services/system_service.py`
- 分析服务：`backend/services/analysis_service.py`
- 模型内建列表：`backend/services/model_registry.py`
- 路径解析：`backend/core/paths.py`
- 运行时设置：`backend/core/system_settings.py`
- 线程子进程封装：`backend/core/threaded_subprocess.py`
- 桌面启动器：`desktop/launcher.py`
