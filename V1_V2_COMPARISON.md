# V1 / V2 对照与切换记录

## 当前结论

V2 现在作为默认工作台入口，V1 Streamlit 保留为兼容兜底，不删除。

原因：

- V2 已覆盖本轮重构目标内的 3 个核心模块：渲染、分析、网络模型管理
- V2 已具备开发 / 生产两种启动方式
- V2 已补齐基础错误边界、空状态和任务失败提示
- 旧版网页终端和部分历史操作路径仍可作为回退方案保留

## 模块对照

| 能力 | V1 Streamlit | V2 Workspace | 当前状态 |
| --- | --- | --- | --- |
| 渲染可视化 | 已有 | 已迁移 | V2 可作为主入口 |
| 材质表达结果分析 | 已有 | 已迁移 | V2 可作为主入口 |
| 网络模型管理 | 已有 | 已迁移 | V2 可作为主入口 |
| 设置 / 系统信息 | 侧边栏混合承载 | 已迁移到设置页 | V2 可作为主入口 |
| 网页终端 | 已有 | 未迁移 | V1 保留 |
| Mitsuba 编译面板 | 已有 | 未迁移 | V1 保留 |

## Phase 5 验收记录

### 1. 统一启动脚本

- 开发模式：`scripts/start_v2_dev.ps1`
- 开发模式批处理入口：`scripts/start_v2_dev.cmd`
- 生产模式：`scripts/start_v2_prod.ps1`
- 生产模式批处理入口：`scripts/start_v2_prod.cmd`

### 2. 开发 / 生产启动方式

- 开发模式：后端 `uvicorn --reload` + 前端 `vite`
- 生产模式：先构建 `frontend/dist`，再由 FastAPI 直接托管静态页面

### 3. 前端韧性补齐

- 全局错误边界：`frontend/src/components/ErrorBoundary.tsx`
- 统一反馈卡片：`frontend/src/components/FeedbackPanel.tsx`
- 渲染 / 分析 / 模型页已接入空状态与错误提示
- 任务失败 / 取消状态已展示任务消息

### 4. 构建与检查

- `frontend`: `npm run build` 通过
- `backend` 与训练相关 Python 文件：`py_compile` 通过

## 切换策略

1. 默认使用 V2：
   - 开发时运行 `scripts/start_v2_dev.ps1`
   - 生产时运行 `scripts/start_v2_prod.ps1`
2. V1 保留：
   - `app.py` 和 `pages/` 暂不删除
   - 如需旧版网页终端或历史编译入口，继续使用 V1
3. 删除 V1 前仍需满足：
   - 旧终端相关能力完成迁移，或明确废弃
   - 至少一轮完整真实实验流程在 V2 下复验通过
