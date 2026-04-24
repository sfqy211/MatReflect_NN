# 项目概述

## 定位

`MatReflect_NN` 是一个基于 V2 架构的 Windows 本地材质研究集成工作台。

核心组成：

- 前端：`React + Vite`（4 个工作模块）
- 后端：`FastAPI + WebSocket`（API 前缀 `/api/v1`）
- 桌面封装：`pywebview + PyInstaller`
- 任务调度：多 Conda 环境 + 本地 Mitsuba / 上游模型代码

## 主链路

1. MERL `.binary` / NBRDF `.npy` / FullBin `.fullbin` → Mitsuba 渲染
2. Neural-BRDF `.binary → .h5/.json → .npy` 训练与转换
3. HyperBRDF 训练、参数提取、`pt → fullbin` 解码
4. 渲染结果的预览、量化评估（PSNR/SSIM/Delta E）、网格拼图、对比拼图
5. Mitsuba 编译辅助、虚拟环境管理、桌面模式

## 运行时环境

| Conda 环境 | 用途 |
|---|---|
| `matreflect` | 后端、分析、桌面封装 |
| `mitsuba-build` | Mitsuba 编译 |
| `nbrdf-train` | Neural-BRDF 训练 / 转换 |
| `hyperbrdf` | HyperBRDF 训练 / 提取 / 解码 |

## 启动方式

| 脚本 | 说明 |
|---|---|
| `scripts/start_v2_dev.ps1` | 开发模式（分两个窗口启动前后端） |
| `scripts/start_v2_prod.ps1` | 生产模式 |
| `scripts/start_v2_desktop.ps1` | 桌面模式 |
| `scripts/build_v2_desktop.ps1` | 桌面打包 |

开发模式后端通过 `python -m backend.run_server` 启动（设置 `ProactorEventLoopPolicy`），前端通过 Vite 开发服务器。
