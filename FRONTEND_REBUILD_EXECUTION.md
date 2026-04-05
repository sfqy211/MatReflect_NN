# MatReflect_NN Frontend Rebuild Execution Plan

## 1. 决策结论

本项目应当**完全重构前端**。

原因不是“现在的 Streamlit 界面不好看”，而是：

1. 目标已经从“研究脚本网页化”升级为“现代化、主画布式、可持续扩展的实验工作台”。
2. 现有 Streamlit 架构高度依赖默认页面模型、`st.session_state` 和同步阻塞流程，不适合继续承载复杂交互。
3. 即使持续优化样式，也很难获得真正的 SPA 体验、精细组件状态控制、流畅的模块切换和更强的界面一致性。

因此，这次工作不再继续优化旧前端，而是转为：

- **前端完全重建**
- **后端做薄 API / 任务层适配**
- **核心算法、训练脚本、Mitsuba 调用链先不重写**

## 2. 重构原则

### 2.1 只重构前端形态，不重写算法内核

以下目录在第一阶段保持为“后端能力来源”，不做大规模逻辑重写：

- `Neural-BRDF/`
- `HyperBRDF/`
- `DecoupledHyperBRDF/`
- `scene/`
- `mitsuba/`

第一阶段只做：

- React 前端
- FastAPI 薄服务层
- 任务调度与日志推送
- 原有 Python 逻辑的 service 化包装

### 2.2 先做到可替换，再做到可删除

在 V2 前端没有完成关键功能对等前：

- 不删除 `app.py`
- 不删除 `pages/`
- 不删除 `pages/_modules/`

旧版 Streamlit 是迁移期兜底，不是立即丢弃的垃圾代码。

### 2.3 优先重建“最能体现价值”的模块

按优先级：

1. 渲染可视化
2. 材质表达结果分析
3. 网络模型管理

如果一开始就并行重建全部页面，失败概率高。

## 3. 目标范围

### 3.1 V2 首批必须覆盖

#### 模块 A：渲染可视化

对应现有：

- `pages/_modules/render_tool_page.py`
- `pages/_modules/render_tool_actions.py`

要覆盖的能力：

- 输入类型切换：`brdfs` / `fullbin` / `npy`
- 场景选择
- 文件列表加载
- 预设 20 材质选择
- 渲染参数设置
- 启动渲染 / 停止渲染
- EXR -> PNG 转换
- 实时日志
- 输出画廊

#### 模块 B：材质表达结果分析

对应现有：

- `pages/_modules/analysis_page.py`
- `pages/_modules/render_tool_actions.py` 中分析相关函数

要覆盖的能力：

- 图片预览
- 量化评估
- 网格拼图
- 对比拼图

#### 模块 C：网络模型管理

对应现有：

- `pages/_modules/training_page.py`
- `pages/_modules/training_neural_tab.py`
- `pages/_modules/training_hyper_tab.py`
- `pages/_modules/training_actions.py`

V2 首版先定义为：

- 模型列表与训练入口
- 训练参数编辑
- 训练启动与日志查看
- 已训练 checkpoint / run 选择
- 参数提取与重建转换

“增删模型”应理解为**管理训练结果、预设模型和运行记录**，不是先做完整模型仓库系统。

### 3.2 V2 首批不做

以下功能可以保留在旧版或后续阶段：

- 网页终端完全复刻
- Mitsuba 编译面板完整重做
- 复杂动画和 3D 交互
- 多用户权限系统
- 远程部署能力

## 4. 技术方案

## 4.1 前端

- React 18
- TypeScript
- Vite
- React Router
- Tailwind CSS
- shadcn/ui
- Zustand
- TanStack Query
- `react-resizable-panels`
- `react-compare-image` 或等价组件
- ECharts 或 Recharts

推荐视觉方向：

- 主画布工作台
- 左侧窄导航 + 中央内容区 + 右侧上下文面板
- 支持浅色/深色双主题
- 现代化、克制、研究工具感，而不是营销页风格

## 4.2 后端

- FastAPI
- Pydantic v2
- Uvicorn
- Python 3.9+

后端职责：

- 提供 REST API
- 提供 WebSocket 任务日志通道
- 管理本地长任务
- 把旧的 Python 工作流包装成 service

不负责：

- 重写训练逻辑
- 重写 Mitsuba 插件
- 替换现有模型脚本

## 4.3 任务执行模型

统一使用：

- `task_id`
- 内存态 + 落盘态的任务状态管理
- 后台子进程执行
- WebSocket 推流

任务状态至少包含：

- `pending`
- `running`
- `success`
- `failed`
- `cancelled`

每个任务至少记录：

- `task_id`
- `task_type`
- `created_at`
- `started_at`
- `finished_at`
- `status`
- `progress`
- `message`
- `log_path`
- `result_payload`

## 5. 目录结构

建议采用：

```text
MatReflect_NN/
├── backend/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── system.py
│   │       ├── fs.py
│   │       ├── render.py
│   │       ├── train.py
│   │       └── analysis.py
│   ├── core/
│   │   ├── config.py
│   │   ├── paths.py
│   │   └── websocket.py
│   ├── models/
│   │   ├── common.py
│   │   ├── render.py
│   │   ├── train.py
│   │   └── analysis.py
│   ├── services/
│   │   ├── task_manager.py
│   │   ├── render_service.py
│   │   ├── train_service.py
│   │   ├── analysis_service.py
│   │   ├── file_service.py
│   │   └── adapters/
│   │       ├── render_actions_adapter.py
│   │       └── training_actions_adapter.py
│   ├── runtime/
│   │   ├── tasks/
│   │   └── logs/
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── render/
│   │   │   ├── analysis/
│   │   │   └── models/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── store/
│   │   ├── styles/
│   │   └── types/
│   └── package.json
│
├── pages/
├── data/
├── scene/
├── Neural-BRDF/
├── HyperBRDF/
├── DecoupledHyperBRDF/
└── mitsuba/
```

## 6. 分阶段执行

## Phase 0: 立项与冻结

### 目标

冻结 V1 功能范围，避免迁移过程中旧功能还在不断变。

### 要做

1. 标记 V1 为维护模式。
2. 记录现有功能清单。
3. 记录当前核心目录约定：
   - `data/inputs/*`
   - `data/outputs/*`
   - `scene/dj_xml/*`
   - `HyperBRDF/results/*`
   - `DecoupledHyperBRDF/results/*`
4. 确认 V2 首批只覆盖三大模块：
   - 渲染可视化
   - 结果分析
   - 网络模型管理

### 验收

- 有一份 V1 功能基线清单
- 不再继续投入 Streamlit UI 美化工作

## Phase 1: 后端骨架

### 目标

让 React 前端有稳定 API 可对接。

### 要做

1. 初始化 `backend/`
2. 提供 `/health`
3. 提供 `/api/v1/system/summary`
4. 提供 `/api/v1/fs/list`
5. 提供 WebSocket：`/ws/tasks/{task_id}`
6. 实现 `TaskManager` 最小版

### API 最小定义

#### GET `/api/v1/system/summary`

返回：

```json
{
  "project_root": "D:/AHEU/GP/MatReflect_NN",
  "mitsuba_exe": "...",
  "mtsutil_exe": "...",
  "mitsuba_exists": true,
  "available_modules": ["render", "analysis", "models"]
}
```

#### POST `/api/v1/fs/list`

请求：

```json
{
  "path_key": "render_outputs_binary_png",
  "page": 1,
  "page_size": 40,
  "suffix": [".png"]
}
```

### 验收

- Swagger 可用
- 能列出图片目录
- WebSocket 可建立连接

## Phase 2: 渲染模块迁移

### 目标

先完成最核心的渲染工作台。

### 要做

1. 从 `render_tool_actions.py` 抽出纯逻辑 service
2. 去掉对 `st.session_state`、`st.success/error`、placeholder 的直接依赖
3. 保留现有能力：
   - 场景 XML 选择
   - 材质枚举
   - preset 20
   - 渲染参数
   - EXR 转 PNG
   - 渲染日志
4. 提供接口：
   - `POST /api/v1/render/batch`
   - `POST /api/v1/render/stop`
   - `POST /api/v1/render/convert`
   - `GET /api/v1/render/scenes`
   - `GET /api/v1/render/files`

### React 页面交付

- 左侧：工作流面板
- 中间：结果画廊
- 右侧：任务状态 / 日志

### 验收

- 能从 V2 前端发起一次完整渲染
- 任务日志能实时显示
- 输出图像能自动出现在画廊

## Phase 3: 分析模块迁移

### 目标

迁移结果分析与对比能力。

### 要做

1. 把评估相关逻辑从 `render_tool_actions.py` 拆到 `analysis_service.py`
2. 提供接口：
   - `POST /api/v1/analysis/evaluate`
   - `POST /api/v1/analysis/grid`
   - `POST /api/v1/analysis/comparison`
   - `GET /api/v1/analysis/images`

### React 页面交付

- 图像预览
- 指标看板
- 图片对比滑块
- 多图拼图

### 验收

- 能完成 GT / Fullbin / NPY 三方量化评估
- 能生成拼图
- 能做图片滑动对比

## Phase 4: 网络模型管理迁移

### 目标

完成训练和模型资产管理的 V2 页面。

### 要做

1. 把 `training_actions.py` 抽为 service
2. 统一任务接口：
   - Neural-BRDF 训练
   - HyperBRDF 训练
   - DecoupledHyperBRDF 训练
   - teacher fitting
   - 参数提取
   - `.pt -> .fullbin`
3. 提供接口：
   - `POST /api/v1/train/neural/pytorch`
   - `POST /api/v1/train/neural/keras`
   - `POST /api/v1/train/hyper/run`
   - `POST /api/v1/train/hyper/extract`
   - `POST /api/v1/train/hyper/decode`
   - `GET /api/v1/train/runs`
   - `GET /api/v1/train/models`
4. 环境与资产约束：
   - `HyperBRDF` 使用 conda 环境 `hyperbrdf`
   - `DecoupledHyperBRDF` 使用 conda 环境 `decoupledhyperbrdf`
   - 两者 checkpoint 分开管理，不能默认混用

### React 页面交付

- 模型类型切换
- 参数表单
- 运行记录列表
- 实时日志
- 训练结果卡片

### 验收

- 能启动至少 3 类训练任务
- 能查看 run 列表和 checkpoint
- 能完成一次 `.binary -> checkpoint/.pt/.fullbin` 的闭环

## Phase 5: 收尾与切换

### 目标

完成 V2 主切换。

### 要做

1. 编写统一启动脚本
2. 提供开发模式与生产模式启动方式
3. 补齐前端错误边界、空状态、任务失败提示
4. 做 V1/V2 对照测试
5. 只有在功能对等后，才允许删除旧前端

### 删除旧前端的前置条件

必须全部满足：

1. 渲染模块对等
2. 分析模块对等
3. 模型管理模块对等
4. 关键路径测试通过
5. 至少一轮真实实验流程在 V2 上成功完成

## 7. 前端页面结构建议

## 7.1 全局布局

```text
┌─────────────────────────────────────────────────────┐
│ Top Bar: 项目 / 主题切换 / 系统状态 / 当前任务       │
├──────────────┬───────────────────────────┬──────────┤
│ Left Nav     │ Main Canvas               │ Side Rail│
│ 模块切换     │ 主工作区                   │ 上下文    │
│ Render       │ 表单 / 图表 / 画廊 / 对比   │ 日志/帮助 │
│ Analysis     │                           │          │
│ Models       │                           │          │
└──────────────┴───────────────────────────┴──────────┘
```

## 7.2 渲染页

左：

- 输入类型
- 场景
- 材质选择
- 参数表单
- 启动按钮

中：

- 当前结果画廊
- 过滤和搜索

右：

- 当前任务状态
- 实时日志
- 最近输出

## 7.3 分析页

上：

- 目录选择
- 比较对象选择

中：

- 指标卡片
- 图像对比组件

下：

- 网格拼图
- 对比拼图

## 7.4 模型管理页

左：

- 模型类型
- 参数编辑

中：

- 运行列表
- 当前训练状态
- Loss 曲线

右：

- checkpoint 信息
- 导出动作

## 8. 关键 API 合约

## 8.1 渲染任务

### POST `/api/v1/render/batch`

请求：

```json
{
  "render_mode": "brdfs",
  "scene_path": "scene/dj_xml/scene_test_merl_accelerated.xml",
  "input_dir": "data/inputs/binary",
  "output_dir": "data/outputs/binary",
  "selected_files": ["alum-bronze.binary"],
  "integrator_type": "bdpt",
  "sample_count": 256,
  "auto_convert": true,
  "skip_existing": false,
  "custom_cmd": null
}
```

返回：

```json
{
  "task_id": "render_xxx",
  "status": "pending"
}
```

## 8.2 训练任务

统一返回：

```json
{
  "task_id": "train_xxx",
  "status": "pending"
}
```

## 8.3 WebSocket 消息

```json
{
  "task_id": "render_xxx",
  "event": "log",
  "status": "running",
  "progress": 42,
  "message": "Rendering: [+++++     ]"
}
```

结束时：

```json
{
  "task_id": "render_xxx",
  "event": "done",
  "status": "success",
  "progress": 100,
  "message": "Render completed"
}
```

## 9. 风险与规避

### 风险 1：前端先做太大，后端接口不稳定

规避：

- 先锁 API
- 前后端用 mock 数据联调

### 风险 2：旧逻辑抽不出来

规避：

- 不直接“迁移 Streamlit 页面”
- 先把纯逻辑抽成 service
- UI 相关调用全部留在 adapter 层

### 风险 3：训练 / 渲染长任务不稳定

规避：

- 任务状态落盘
- 标准化日志文件
- 所有任务必须可重连查看状态

### 风险 4：范围失控

规避：

- 首版只做三大模块
- 不复刻终端
- 不先做复杂动画

## 10. 推荐实施顺序

严格按这个顺序：

1. `backend/` 骨架
2. 渲染 API
3. React 基础布局
4. 渲染页
5. 分析页
6. 模型管理页
7. 启动脚本
8. 对照验证
9. 决定是否移除 Streamlit

不要倒过来先做训练页，也不要同时开三条主线。

## 11. 里程碑与验收口径

### Milestone A

后端跑起来，React 壳子跑起来，能显示系统状态和空页面。

### Milestone B

V2 渲染页可以独立完成一次真实渲染闭环。

### Milestone C

V2 分析页可完成真实评估与对比。

### Milestone D

V2 模型管理页可完成训练与提取闭环。

### Milestone E

V1/V2 功能对照通过，准备切换。

## 12. 下一步建议

如果现在就开始执行，不要再讨论是否重构前端，直接进入以下动作：

1. 创建 `backend/` 与 `frontend/`
2. 先实现 Phase 1
3. 同时用 mock 数据起一个渲染页 React 原型
4. 以“渲染模块可用”为第一个真正里程碑

这会比继续在 Streamlit 上微调更有效，也更符合你的目标。
