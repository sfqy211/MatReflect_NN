# AGENTS.md

`MatReflect_NN` — Windows 本地材质研究集成工作台。React + Vite 前端，FastAPI + WebSocket 后端。

## 文档索引

- [docs/00-overview.md](docs/00-overview.md) — 项目定位、主链路、Conda 环境、启动方式
- [docs/01-directory-structure.md](docs/01-directory-structure.md) — 目录结构、文件索引、gitignore 说明
- [docs/02-render-pipeline.md](docs/02-render-pipeline.md) — 渲染链路（模式、场景、XML 改写、输出命名）
- [docs/03-train-pipeline.md](docs/03-train-pipeline.md) — 训练链路（内建模型、脚本、API）
- [docs/04-analysis-pipeline.md](docs/04-analysis-pipeline.md) — 分析链路（评估、拼图、材质名匹配）
- [docs/05-development-guide.md](docs/05-development-guide.md) — 开发验证、编辑约束、架构原则

## 核心文件速查

| 区域 | 文件 |
|---|---|
| 前端入口 | `frontend/src/App.tsx` |
| 后端入口 | `backend/main.py` |
| 安全启动 | `backend/run_server.py` |
| 渲染服务 | `backend/services/render_service.py` |
| 训练服务 | `backend/services/train_service.py` |
| 分析服务 | `backend/services/analysis_service.py` |
| 系统服务 | `backend/services/system_service.py` |
| 模型注册 | `backend/services/model_registry.py` |
| 任务管理 | `backend/services/task_manager.py` |
| 路径解析 | `backend/core/paths.py` |
| 子进程封装 | `backend/core/threaded_subprocess.py` |
| 系统设置 | `backend/core/system_settings.py` |

## 关键约束

1. **子进程**：统一用 `threaded_subprocess.py` 的 `run_process_streaming`，不要直接用 asyncio 子进程
2. **路径**：优先 `pathlib.Path`，限制在 `PROJECT_ROOT` 内
3. **任务**：持久化到 `backend/runtime/tasks/*.json`，重启后 pending/running 自动标记 failed
4. **文档与代码不一致时**：信代码
5. **不可随意清理**：`data/`、`backend/runtime/`、`HyperBRDF/results/`、`mitsuba/dist/`
6. **不优先大改**：`mitsuba/src/`、`Neural-BRDF/`、`HyperBRDF/`
7. **命名变更**：同步检查渲染输出、前端 `fileNames.ts`、分析 `normalize_material_name`
