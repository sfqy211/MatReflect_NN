# 目录结构

## 核心工作区

| 目录 | 说明 |
|---|---|
| `frontend/` | V2 React 前端 |
| `backend/` | V2 FastAPI 后端 |
| `scripts/` | 启动脚本 |
| `scene/` | Mitsuba 场景资源（`scene/assets/` 下每个场景一个子目录，主 XML 为 `scene.xml`） |
| `references/` | 只读参考区（上游文档、论文笔记等） |

## 上游模型代码（只读对待）

- `Neural-BRDF/`
- `HyperBRDF/`
- `mitsuba/`

## 数据目录

```
data/
  inputs/
    binary/     MERL .binary
    npy/        Neural-BRDF .npy 权重
    fullbin/    FullBin .fullbin
  outputs/
    binary/{exr,png}/
    npy/{exr,png}/
    fullbin/{exr,png}/
    grids/      网格拼图
    comparisons/ 对比拼图
```

## 运行时目录

- `backend/runtime/logs/`
- `backend/runtime/tasks/`
- `backend/runtime/render_xml/`
- `backend/runtime/system_settings.json`

## .gitignore 关键忽略项

以下目录不纳入版本控制，但不可随意删除（包含本地依赖、用户资产、运行输出）：

- `data/`、`mitsuba/`、`HyperBRDF/`、`Neural-BRDF/`
- `backend/runtime/`
- `frontend/node_modules/`、`frontend/dist/`

## 后端模块文件

### API 路由 (`backend/api/v1/`)

| 文件 | 路由 |
|---|---|
| `render.py` | `/api/v1/render/*` |
| `analysis.py` | `/api/v1/analysis/*` |
| `train.py` | `/api/v1/train/*` |
| `system.py` | `/api/v1/system/*` |
| `fs.py` | `/api/v1/fs/*` |

### 服务层 (`backend/services/`)

| 文件 | 职责 |
|---|---|
| `render_service.py` | 渲染 / 重建调度 |
| `train_service.py` | 训练 / 提取 / 解码调度 |
| `analysis_service.py` | 评估、网格、对比拼图 |
| `system_service.py` | 系统设置、Mitsuba 编译 |
| `file_service.py` | 文件浏览与预览 |
| `task_manager.py` | 任务持久化与 WebSocket 推送 |
| `model_registry.py` | 内建模型定义 |

### 核心模块 (`backend/core/`)

| 文件 | 职责 |
|---|---|
| `config.py` | 环境变量 → 路径常量 |
| `paths.py` | 路径解析 + mitsuba 自动探测 |
| `system_settings.py` | 系统设置读写 |
| `threaded_subprocess.py` | 子进程线程封装 |
| `conda.py` | Conda 环境探测 |

## 前端模块 (`frontend/src/`)

| 路径 | 说明 |
|---|---|
| `App.tsx` | 前端根组件 |
| `components/WorkspaceCanvas.tsx` | 工作区容器 |
| `components/ModuleRail.tsx` | 左侧导航栏 |
| `components/RenderWorkbench.tsx` | 渲染工作台 |
| `components/AnalysisWorkbench.tsx` | 分析工作台 |
| `components/ModelsWorkbench.tsx` | 模型工作台 |
| `components/SettingsWorkbench.tsx` | 设置页 |
| `features/*/use*.ts` | 各模块状态管理 hooks |
| `lib/fileNames.ts` | 文件名解析工具 |
| `types/api.ts` | API 类型定义 |
