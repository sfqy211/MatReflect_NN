# V2 快速开始

## 1. 后端启动

```powershell
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

默认地址：

- API：`http://127.0.0.1:8000/api/v1`
- 文档：`http://127.0.0.1:8000/docs`

## 2. 前端启动

```powershell
cd frontend
npm install
npm run dev
```

默认地址：

- 应用：`http://127.0.0.1:5173`

## 3. 推荐的一键入口

开发模式：

```powershell
scripts\start_v2_dev.ps1
```

生产模式：

```powershell
scripts\start_v2_prod.ps1
```

说明：

- `start_v2_dev.ps1`：分别启动后端和 Vite 开发服务器。
- `start_v2_prod.ps1`：先构建 `frontend/dist`，再由 FastAPI 直接托管前端页面。

## 4. 前端环境变量

如果后端不是默认地址，可创建 `frontend/.env.local`：

```bash
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## 5. 训练环境

- `Neural-BRDF`：`nbrdf-train`
- `HyperBRDF`：`hyperbrdf`

V2 会通过 `conda run -n ...` 调用这些环境。

## 6. 当前范围

V2 当前已覆盖：

- 渲染可视化
- 材质表达结果分析
- 网络模型管理
- 设置页系统摘要与 Mitsuba 编译辅助

仓库中已不再保留 V1 / Streamlit 启动路径。
