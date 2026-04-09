# V2 快速开始

## 后端启动

```powershell
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

后端默认地址：

- API：`http://127.0.0.1:8000/api/v1`
- 文档：`http://127.0.0.1:8000/docs`

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

前端默认地址：

- 应用：`http://127.0.0.1:5173`

## 统一启动脚本

推荐直接使用以下入口：

```powershell
scripts\start_v2_dev.ps1
scripts\start_v2_prod.ps1
```

说明：

- `start_v2_dev.ps1`：分别启动后端与 Vite 开发服务器
- `start_v2_prod.ps1`：先构建 `frontend/dist`，再由 FastAPI 直接托管 V2 页面

## 可选环境变量

如果后端不是运行在默认地址，可创建 `frontend/.env.local`：

```bash
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## 训练环境

- `HyperBRDF` 使用 Conda 环境 `hyperbrdf`
- `Neural-BRDF` 可继续使用现有环境，或使用其独立训练环境

## 当前范围

- 新版 V2 工作台支持浅色 / 深色主题切换
- 核心模块入口已具备：
  - 渲染可视化
  - 材质结果分析
  - 网络模型管理
- 设置页已提供主题切换、系统信息查看与 Mitsuba 编译辅助入口
- 后端摘要与文件列表 API 已接通
- V2 是当前唯一推荐的日常入口
- V1 遗留代码可能仍存在于仓库中，但不属于正常启动路径
