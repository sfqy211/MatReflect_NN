# AGENTS.md

`MatReflect_NN` — Windows 本地材质研究集成工作台。React + Vite 前端，FastAPI + WebSocket 后端。

## 常用命令

### 启动开发模式（前后端分窗口）
```powershell
scripts\start_v2_dev.ps1
```
后端 `localhost:8000`（Conda env `matreflect`），前端 `localhost:5173`（Vite dev server）。

### 启动生产模式
```powershell
scripts\start_v2_prod.ps1
```
先 `npm run build` 构建前端，再单窗口启动后端，后端 mount `frontend/dist/` 提供静态站。

### 后端导入检查
```powershell
conda run -n matreflect python -c "import backend.main"
```

### 前端类型检查
```powershell
frontend\node_modules\.bin\tsc.cmd --noEmit
```

### 后端手动启动（调试用）
```powershell
conda run -n matreflect python -m backend.run_server --reload --host 127.0.0.1 --port 8000
```
入口是 `backend/run_server.py`，它设置 `WindowsProactorEventLoopPolicy` 和 `PYTHONPATH` 后再启动 uvicorn。

### 前端手动启动
```powershell
cd frontend && npm run dev -- --host=127.0.0.1 --port=5173
```

项目无自动化测试套件（`backend/tests/` 为空，无 pytest 配置）。

## 架构概览

### 三层架构

```
┌───────────────────────────────────────────────────────┐
│  Frontend (React + Vite)                              │
│  App.tsx → ModuleRail + WorkspaceCanvas + StatusBar   │
│  4 模块: models / render / analysis / settings        │
│  状态: features/*/use*.ts hooks + @tanstack/react-query│
└──────────┬──────────────────────────┬─────────────────┘
           │ REST /api/v1/*           │ WebSocket
           │                          │ /ws/tasks/{id}
           │                          │ /ws/system/metrics
┌──────────▼──────────────────────────▼─────────────────┐
│  Backend (FastAPI)                                    │
│  Routes → Services → Core                             │
│  跨切: task_manager + model_registry + websocket_hub  │
└──────────┬────────────────────────────────────────────┘
           │ threaded_subprocess (在对应 Conda 环境中)
┌──────────▼────────────────────────────────────────────┐
│  External Tools (上游代码，只读对待)                    │
│  mitsuba/dist/ | Neural-BRDF/ | HyperBRDF/            │
└───────────────────────────────────────────────────────┘
```

### 后端分层

- **API 路由层** (`backend/api/v1/`): `render.py`, `analysis.py`, `train.py`, `system.py`, `fs.py`, `models.py`, `terminal.py` — 薄路由，参数校验后委托 Service
- **Service 层** (`backend/services/`): 业务逻辑核心
  - `render_service` — 渲染/重建调度，XML 改写，EXR→PNG
  - `train_service` — 训练/提取/解码调度，按 adapter 分派
  - `analysis_service` — 评估(PSNR/SSIM/Delta E)、网格拼图、对比拼图
  - `model_import_service` — 自定义模型导入、虚拟环境创建、动态注册
  - `terminal_service` — PTY 终端会话管理
  - `system_service` — 系统设置读写、Mitsuba 编译
  - `file_service` — 文件浏览与预览（路径安全校验）
  - `task_manager` — 任务持久化到 `runtime/tasks/*.json`，重启后 pending/running 标记 failed
  - `model_registry` — 模型注册服务（从 `backend/config/model_registry.json` 加载）
- **Core 层** (`backend/core/`):
  - `config.py` — 环境变量→路径常量（PROJECT_ROOT, RUNTIME_ROOT, OUTPUTS_ROOT 等）
  - `paths.py` — Mitsuba 路径探测 + SAFE_PATHS 安全校验
  - `system_settings.py` — 设置持久化（`runtime/system_settings.json`），合并用户值与默认值
  - `threaded_subprocess.py` — 子进程线程封装，`run_process_streaming()` 是唯一合规的子进程调用方式
  - `websocket.py` — WebSocketHub，按 task_id 管理连接和广播
  - `conda.py` — Conda 环境探测
  - `runtime_logging.py` — 运行日志

### 关键数据流

1. 前端操作 → REST API → Service 创建 `TaskRecord`（task_manager）
2. Service 通过 `run_process_streaming()` 在对应 Conda 环境中启动子进程
3. 子进程输出通过 `on_output` 回调 → `websocket_hub` → 前端 WebSocket 实时更新
4. 任务状态持久化到 `runtime/tasks/*.json`
5. 渲染图片通过 `/media/outputs` 静态文件端点直接 HTTP 访问

### 渲染链路要点

三种渲染模式：`brdfs`（GT/参考值 → merl 插件）、`npy`（Neural-BRDF 输出 → nbrdf_npy 插件）、`fullbin`（HyperBRDF 输出 → fullmerl 插件）。UI 标签按模型来源命名，内部 key 不变。渲染时动态改写 XML：替换 bsdf 节点、转绝对路径、`ldrfilm→hdrfilm`、更新 integrator。临时 XML 写入 `backend/runtime/render_xml/`。FullBin 模式下小文件自动回退 merl 插件。输出命名 `材质名_YYYYMMDD_HHMMSS`。

### 训练链路要点

3 个内建模型 + 用户自定义模型通过 `model_registry.json` 注册。每个模型定义 `adapter`、`runtime`（conda_env + 脚本路径）、`supports_*` 能力标记、`parameters`（可配置参数列表）、`supports_reconstruction`。`train_service` 按 adapter 字段分派到具体训练/提取/解码/重建逻辑。自定义模型通过 `model_import_service` 导入，命令行接口（subprocess），自动创建虚拟环境。训练与重建分离：训练在 ModelsWorkbench 的训练 Tab，重建在重建 Tab。

### 分析链路要点

材质名匹配通过 `normalize_material_name` 归一化（去时间戳、去 `_fc1`、去扩展名），不是严格文件名匹配。修改命名规则时必须同步检查：`analysis_service.py` 的 `normalize_material_name`、`frontend/src/lib/fileNames.ts`。

### 前端结构

- `App.tsx` — 根组件，4 模块切换（ModuleKey: models/render/analysis/settings），默认激活 models
- `components/` — 工作台组件（ModelsWorkbench, RenderWorkbench, AnalysisWorkbench, SettingsWorkbench）
- `components/TerminalPanel.tsx` — xterm.js 终端面板（@xterm/xterm + WebSocket PTY）
- `components/ModelImportWizard.tsx` — 自定义模型导入向导
- `components/ModelParameterForm.tsx` — 动态模型参数表单（根据 model.parameters 配置渲染）
- `components/CommandsDocPanel.tsx` — 命令文档浮窗
- `components/ConfirmDialog.tsx` — 删除确认对话框
- `components/AnalysisCompareView.tsx` — 三栏并排对比视图
- `components/AnalysisResultTable.tsx` — 评估结果表格
- `features/*/use*.ts` — 各模块状态管理 hooks
- `lib/fileNames.ts` — 文件名解析工具
- `types/api.ts` — API 类型定义（含 ModelParameter, ReconstructRequest, ModelImportRequest 等）

### Conda 环境

| 环境 | 用途 |
|---|---|
| `matreflect` | 后端运行、分析 |
| `mitsuba-build` | Mitsuba 编译（Python 2.7 + SCons） |
| `nbrdf-train` | Neural-BRDF 训练/转换 |
| `hyperbrdf` | HyperBRDF 训练/提取/解码 |

### 新增 API 端点

- `POST /models/import` — 导入自定义模型
- `DELETE /models/{model_key}` — 删除自定义模型（仅 built_in=false）
- `GET /models/{model_key}/config` — 获取模型配置
- `PUT /models/{model_key}/config` — 更新模型配置
- `GET /models/{model_key}/env-status` — 查询虚拟环境状态
- `POST /models/{model_key}/setup-env` — 创建虚拟环境
- `POST /train/reconstruct` — 启动重建任务
- `WS /ws/pty/{session_id}` — PTY 终端通信

### 路径与环境变量

`config.py` 定义核心路径，均支持环境变量覆盖：
- `MATREFLECT_PROJECT_ROOT` → PROJECT_ROOT
- `MATREFLECT_RUNTIME_ROOT` → RUNTIME_ROOT（默认 `backend/runtime/`）
- `MATREFLECT_OUTPUTS_ROOT` → OUTPUTS_ROOT（默认 `data/outputs/`）

### WebSocket 端点

- `/ws/system/metrics` — 系统指标实时推送（CPU/GPU，由 `metrics_service` 驱动）
- `/ws/tasks/{task_id}` — 单任务状态实时推送（由 `websocket_hub` + `task_manager` 驱动）
- `/ws/pty/{session_id}` — PTY 终端全双工通信（由 `terminal_service` 驱动）

## 关键约束

1. **子进程**：统一用 `threaded_subprocess.py` 的 `run_process_streaming`，不要直接用 `asyncio.create_subprocess_*`（Windows + Uvicorn reload 兼容问题）
2. **路径**：优先 `pathlib.Path`，限制在 `PROJECT_ROOT` 内；设置页允许用户修改路径，避免写死绝对路径
3. **任务**：持久化到 `backend/runtime/tasks/*.json`，重启后 pending/running 自动标记 failed
4. **文档与代码不一致时**：信代码
5. **不可随意清理**：`data/`、`scene/assets/`、`references/`、`backend/runtime/`、`models/`、`mitsuba/dist/`
6. **不优先大改**：`mitsuba/src/`、`models/Neural-BRDF/`、`models/HyperBRDF/`
7. **命名变更**：同步检查渲染输出、前端 `fileNames.ts`、分析 `normalize_material_name`
8. **优先改**：`frontend/src/`、`backend/api/`、`backend/services/`、`backend/models/`、`backend/core/`、`scripts/`
9. **前端文案**：以中文为主
10. **术语规范**：UI 标签按模型来源命名（GT/参考值、Neural-BRDF 输出、HyperBRDF 输出），不使用文件后缀名（binary/NPY/FullBin）作为标签
11. **自定义模型**：通过 `model_import_service` 导入，命令行接口（subprocess 调用），自动创建虚拟环境
12. **训练与重建分离**：训练在 ModelsWorkbench 中，重建也迁移到 ModelsWorkbench 的重建 Tab，RenderWorkbench 仅保留纯渲染
13. **删除操作**：所有删除（图片/模型/运行记录）必须有前端确认对话框

## 文档索引

- [docs/00-overview.md](docs/00-overview.md) — 项目定位、主链路、Conda 环境、启动方式
- [docs/01-directory-structure.md](docs/01-directory-structure.md) — 目录结构、文件索引
- [docs/02-render-pipeline.md](docs/02-render-pipeline.md) — 渲染链路（模式、场景、XML 改写、输出命名）
- [docs/03-train-pipeline.md](docs/03-train-pipeline.md) — 训练链路（内建模型、脚本、API）
- [docs/04-analysis-pipeline.md](docs/04-analysis-pipeline.md) — 分析链路（评估、拼图、材质名匹配）
- [docs/05-development-guide.md](docs/05-development-guide.md) — 开发验证、编辑约束、架构原则
