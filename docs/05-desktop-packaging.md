# 桌面封装

## 核心文件

- 启动器：`desktop/launcher.py`
- 打包配置：`desktop/MatReflectNNDesktop.spec`
- 启动脚本：`scripts/start_v2_desktop.ps1`
- 打包脚本：`scripts/build_v2_desktop.ps1`

## 桌面模式行为

1. 探测项目根目录（检查 `backend/main.py` + `frontend/` + `scene/`）
2. 验证 `frontend/dist/index.html` 存在
3. 设置环境变量：
   - `MATREFLECT_PROJECT_ROOT`
   - `MATREFLECT_RUNTIME_ROOT`
   - `MATREFLECT_OUTPUTS_ROOT`
4. 在本地线程内启动 FastAPI（`DesktopServer`，禁用 signal handlers）
5. 等待后端就绪（轮询 `/api/v1/health`，最多 60s）
6. 用 `pywebview` 打开窗口

**桌面模式依赖当前工作区**，不会把 `data/`、`scene/`、`mitsuba/`、Conda 环境打包成独立资源。

## 打包要求

- `frontend/dist` 必须存在
- `desktop/requirements.txt` 已安装
- 系统需安装 WebView2

## 修改桌面模式时需同步检查

- `desktop/launcher.py`
- `backend/core/config.py`
- `backend/main.py`
- `scripts/start_v2_desktop.ps1`
- `scripts/build_v2_desktop.ps1`
