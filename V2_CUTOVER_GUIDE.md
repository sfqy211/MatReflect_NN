# V2 切换指南

## 1. 默认入口

当前仓库已经完成切换，默认入口只有 V2：

```powershell
scripts\start_v2_dev.ps1
scripts\start_v2_prod.ps1
```

V1 / Streamlit 已从仓库中清理，不再作为兼容入口保留。

## 2. 开发模式

```powershell
scripts\start_v2_dev.ps1
```

该脚本会启动：

- FastAPI 后端：`http://127.0.0.1:8000`
- Vite 前端：`http://127.0.0.1:5173`

## 3. 生产模式

```powershell
scripts\start_v2_prod.ps1
```

该脚本会执行：

1. 构建 `frontend/dist`
2. 启动 FastAPI
3. 由后端托管 V2 前端

默认地址：

- 应用：`http://127.0.0.1:8000`
- 文档：`http://127.0.0.1:8000/docs`

## 4. 环境说明

- 后端默认环境：`matreflect`
- Neural-BRDF 环境：`nbrdf-train`
- HyperBRDF 环境：`hyperbrdf`
- Mitsuba 编译环境：`mitsuba-build`

## 5. 切换后的使用约定

- 日常开发与使用统一走 V2。
- 渲染、分析、模型管理、设置页编译辅助都在 V2 中完成。
- 如果需要核对迁移结论，请直接看：
  - [V1_V2_COMPARISON.md](/d:/AHEU/GP/MatReflect_NN/V1_V2_COMPARISON.md)
  - [V1_DECOMMISSION_CHECKLIST.md](/d:/AHEU/GP/MatReflect_NN/V1_DECOMMISSION_CHECKLIST.md)
