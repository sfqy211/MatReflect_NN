# MatReflect_NN

`MatReflect_NN` 是一个运行在 Windows 本机上的材质研究工作台，当前只保留 V2 架构：

- 前端：React + Vite
- 后端：FastAPI + WebSocket
- 训练与推理：Conda 多环境调度

项目闭环包括：

1. 使用 Mitsuba 0.6 渲染 MERL / FullBin / NBRDF 材质。
2. 使用 Neural-BRDF 完成 `.binary -> .npy`。
3. 使用 HyperBRDF 完成 `.binary -> checkpoint.pt -> .pt -> .fullbin`。
4. 在工作台内完成渲染预览、量化评估、拼图分析、模型管理与系统设置。

## 当前入口

开发模式：

```powershell
scripts\start_v2_dev.ps1
```

生产模式：

```powershell
scripts\start_v2_prod.ps1
```

桌面模式：

```powershell
scripts\start_v2_desktop.ps1
scripts\build_v2_desktop.ps1
```

补充说明：

- 开发模式会分别启动后端和前端两个窗口。
- 桌面模式会复用现有 `frontend/dist`，并在本地窗口中嵌入当前 V2 前端。

## 环境准备

推荐使用 Conda，多环境如下。

### `matreflect`

用于：

- V2 backend
- 渲染调度
- 分析模块

```powershell
conda create -n matreflect -c conda-forge python=3.9 mamba -y
conda activate matreflect
mamba install -c conda-forge pyexr -y
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### `mitsuba-build`

用于 Mitsuba 0.6 的 SCons 编译：

```powershell
conda create -n mitsuba-build python=2.7 scons -y
```

### `nbrdf-train`

用于 Neural-BRDF 训练与 `h5 -> npy` 转换：

```powershell
conda create -n nbrdf-train python=3.8 -y
conda activate nbrdf-train
pip install numpy==1.19.5 tensorflow==2.4.1 keras==2.4.3 pandas matplotlib scikit-learn pillow scipy
```

### `hyperbrdf`

用于 HyperBRDF 训练、参数提取与解码：

```powershell
conda create -n hyperbrdf python=3.8 -y
conda activate hyperbrdf
pip install torch==1.8.1+cpu torchvision==0.9.1+cpu -f https://download.pytorch.org/whl/torch_stable.html
pip install matplotlib==3.3.4 numpy==1.21.6 pandas==1.2.2 scikit_learn==1.1.3 PyYAML==6.0 torchmeta==1.8.0
```

## 主要功能

### 网络模型管理

- 内置 Neural-BRDF / HyperBRDF 模型注册项
- 新模型需通过修改代码接入，不再提供 UI 动态注册
- 支持训练任务、参数提取、`pt -> fullbin`
- 支持独立 `H5 -> NPY` 转换
- 支持运行记录扫描

### 渲染可视化

- 支持 `.binary`、`.fullbin`、`.npy` 三类输入
- 支持 Mitsuba XML 场景切换
- 支持 EXR -> PNG 自动转换
- 前端当前提供“仅渲染 / 仅重建”两种工作模式
- 后端保留“重建后继续渲染”的串联能力，但前端当前未直接开放该按钮

### 材质表达结果分析

- 图片预览
- 图片删除与对应 EXR 清理
- PSNR / SSIM / Delta E 量化评估
- 网格拼图
- 对比拼图
- 自定义分析目录与输出目录

### 设置页

- 深浅主题切换
- 系统摘要
- Mitsuba 路径管理
- 依赖路径管理
- 虚拟环境管理
- Mitsuba 编译辅助入口
- 设置持久化与状态检查

## 目录结构

```text
MatReflect_NN/
├── frontend/                    # V2 React 前端
├── backend/                     # V2 FastAPI 后端
├── backend/runtime/             # 运行时任务、日志、临时 XML、系统设置
├── scripts/                     # 启动脚本、桌面封装脚本等
├── desktop/                     # 桌面封装说明
├── data/                        # 输入数据与输出结果
├── scene/                       # Mitsuba 场景资源
├── Neural-BRDF/                 # Neural-BRDF 上游代码
├── HyperBRDF/                   # HyperBRDF 上游代码
├── README.md
├── AGENTS.md
└── MODEL_PLUGIN_DEVELOPMENT_SPEC.md
```

## 相关文档

- [AGENTS.md](AGENTS.md)
- [MODEL_PLUGIN_DEVELOPMENT_SPEC.md](MODEL_PLUGIN_DEVELOPMENT_SPEC.md)
- [desktop/README.md](desktop/README.md)

## 常见问题

### 默认使用哪个入口？

只使用 V2：

- `scripts\start_v2_dev.ps1`
- `scripts\start_v2_prod.ps1`

### 为什么需要多个 Conda 环境？

因为 Mitsuba 编译、Neural-BRDF、HyperBRDF 的依赖栈差异很大，强行放在同一个环境里会导致版本冲突和不可复现问题。

### 如果 Mitsuba 没有被检测到怎么办？

先打开 V2 的设置页，检查系统摘要、路径状态、依赖路径和虚拟环境状态。默认检测位置为项目目录下的 `mitsuba/dist/mitsuba.exe`。

### 新模型是通过页面添加吗？

不是。

当前版本已经移除“自建模型动态注册”功能。新增模型的标准方式是开发者直接修改代码接入，详见 [MODEL_PLUGIN_DEVELOPMENT_SPEC.md](MODEL_PLUGIN_DEVELOPMENT_SPEC.md)。

### 为什么项目里仍然会看到绝对路径？

已安全改成相对路径的部分：

- `scripts/start_v2_dev.ps1`
- `scripts/start_v2_prod.ps1`
- `scripts/start_v2_desktop.ps1`
- `scripts/build_v2_desktop.ps1`
- 设置页中的路径输入占位示例

仍然可能保留绝对路径的部分：

- `backend/runtime/system_settings.json`
  - 这是用户本机保存的运行时设置，记录当前机器上的实际 Mitsuba、工作目录、依赖路径与 `vcvarsall` 路径。
- `backend/runtime/tasks/*.json` 与 `backend/runtime/logs/*`
  - 这是历史任务记录和日志，天然会写入当时运行机器上的绝对路径。
- `scripts/test_example_mitsuba_variants.ps1` 中的 Mitsuba 变体 `Exe`
  - 这是本地实验脚本，用来指向不同外部 Mitsuba 构建目录；这些路径本身就是机器相关的，无法统一改成项目内相对路径。
- Visual Studio 的 `vcvarsall.bat`
  - 这类路径通常位于系统安装目录，属于外部依赖路径，不属于项目工作区。

处理建议：

- 项目源码和正式启动脚本优先使用相对路径或动态推导路径。
- 运行时设置、历史任务日志、系统级依赖路径允许保留绝对路径。
- 如果迁移到新机器，优先在设置页重新保存一次系统设置，而不是手改历史任务文件。
