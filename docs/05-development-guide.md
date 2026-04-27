# 开发指南

## 运行前提

- 平台：Windows + PowerShell
- Conda：Miniconda / Anaconda
- 关键 Conda 环境：`matreflect`、`mitsuba-build`、`nbrdf-train`、`hyperbrdf`

## 验证方法

### 后端导入检查

```powershell
python -c "import backend.main"
```

### 前端类型检查

```powershell
frontend\node_modules\.bin\tsc.cmd --noEmit
```

### 渲染改动验证

- `scene/assets/*/scene.xml` 中目标材质节点是否仍可定位（`id="Material"` 或兼容类型的 bsdf）
- `backend/runtime/render_xml/` 是否生成临时 XML
- `data/outputs/*/{exr,png}` 是否产生新结果
- 新命名是否仍被前端和分析模块识别

### 训练改动验证

- Neural：单材质、小 epoch 或单个 `.h5` 转换
- HyperBRDF：单材质提取或小样本训练

### 分析改动验证

- 预览页是否能读到 PNG
- 量化评估是否还能匹配 GT / FullBin / NPY
- 拼图是否还能处理新旧时间戳格式

## 编辑约束

- 路径优先 `pathlib.Path`
- 路径限制在 `PROJECT_ROOT` 内
- 前端文案以中文为主
- 设置页允许用户修改路径，避免写死绝对路径
- 涉及输出命名 / 脚本参数时，必须沿链路检查上下游

## 优先修改区域

大多数集成任务优先改这些位置：

- `frontend/src/components/`、`frontend/src/features/`、`frontend/src/lib/`、`frontend/src/types/`
- `backend/api/v1/`、`backend/services/`、`backend/models/`、`backend/core/`
- `scripts/start_v2_*.ps1`

不要优先大改：

- `mitsuba/src/`、`mitsuba/dist/`
- `Neural-BRDF/`
- `HyperBRDF/`

## 架构原则

- 子进程统一使用 `backend/core/threaded_subprocess.py` 中的 `run_process_streaming` / `terminate_process`（不要直接用 `asyncio.create_subprocess_*`，因为 Windows + Uvicorn reload + asyncio 子进程存在兼容问题）
- 任务持久化到 `backend/runtime/tasks/*.json`，服务重启后 pending/running 任务自动标记为 failed
- WebSocket 通过 `backend/core/websocket.py` 的 hub 统一管理
- 文件浏览复用 `backend/services/file_service.py` 的 `resolve_workspace_path`，确保不越过 `PROJECT_ROOT`
- 前端子视图切换通过 `AnalysisSubView` 和 `ModelsSubView` 类型控制
