# V2 切换指南

## 默认入口

V2 已经是当前仓库的默认界面入口。仓库中仍可能保留部分 V1 / Streamlit 遗留代码，用于迁移核对与历史能力兜底，但它已不再是推荐的日常使用入口。

## 开发模式

推荐使用统一启动脚本：

```powershell
scripts\start_v2_dev.ps1
```

该脚本会启动：

- FastAPI 后端：`http://127.0.0.1:8000`
- Vite 前端：`http://127.0.0.1:5173`

## 生产模式

推荐使用生产脚本：

```powershell
scripts\start_v2_prod.ps1
```

该脚本会执行：

1. 构建 `frontend/dist`
2. 启动 FastAPI
3. 由后端直接托管构建后的 V2 前端

默认地址：

- 应用：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/docs`

## 环境说明

- 后端默认环境：`matreflect`
- `HyperBRDF` 训练环境：`hyperbrdf`

## 遗留说明

仓库中仍可能保留部分 Streamlit 代码，用于迁移核对和功能对等验证。日常使用请统一使用 V2 启动脚本，不再按旧文档将 V1 视为常规入口。
