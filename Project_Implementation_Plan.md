# 基于神经网络的材质反射属性表达方法研究与实现 - 项目实施方案

## 1. 项目概述

本项目旨在利用深度学习技术对材质的双向反射分布函数（BRDF）进行压缩与表达，并结合物理渲染引擎（Mitsuba）实现高质量的真实感渲染。项目包含数据处理、网络构建、训练优化、渲染集成及系统开发等多个环节。

## 2. 技术栈选型 (Technology Stack)

基于提供的参考资料和现有环境，推荐以下技术栈：

### 2.1 开发语言与环境
*   **编程语言**: Python 3.8+ (核心算法与系统开发), C++ (Mitsuba 插件接口)
*   **深度学习框架**: PyTorch (配合 TorchMeta 用于 HyperBRDF)
*   **环境管理**: Anaconda / Miniconda
*   **操作系统**: Windows 10/11 (已具备 Visual Studio 编译环境支持)

### 2.2 核心算法与数据
*   **基准模型 (Baseline)**: Neural-BRDF (Sztrajman et al., 2021) - *已具备现成的 Mitsuba 插件支持*
*   **优化模型 (Advanced)**: HyperBRDF (Gokbudak et al., 2024) - *用于提升泛化能力和压缩效率*
*   **数据集**: MERL BRDF Database (已提供二进制及 H5 格式)

### 2.3 渲染引擎
*   **渲染器**: Mitsuba Renderer 0.5.0/0.6.0 (用户提供的 `d:\AHEU\GP\mitsuba\`)
    *   *优势*: 也就是传统的 Mitsuba 0.6 版本，工业界和学术界常用的科研渲染器。
    *   *现状*: `dist` 目录中已包含编译好的 `nbrdf_npy.dll` 插件，可直接支持 Neural-BRDF 的渲染，无需重新编译，极大降低了实施难度。

### 2.4 系统交互与可视化
*   **UI 框架**: Streamlit
    *   *理由*: 极简的 Python Web 框架，适合快速构建科研 Demo。可以轻松实现 "上传文件 -> 运行模型 -> 调用渲染器 -> 展示图片" 的全流程。
*   **图像处理**: OpenCV, NumPy, Matplotlib

---

## 3. 实施路径与计划 (Implementation Roadmap)

### 第一阶段：环境搭建与基线跑通 (Week 1-2)
*   **目标**: 成功运行现有的 Neural-BRDF 代码和 Mitsuba 渲染器。
*   **任务**:
    1.  配置 Python 3.6/3.8 环境，安装 PyTorch, NumPy, H5py 等依赖。
    2.  测试 `d:\AHEU\GP\mitsuba\dist\mitsuba.exe` 是否能正常运行。
    3.  验证 `nbrdf_npy.dll` 插件：使用 `Neural-BRDF` 提供的 `sample_scene.xml` 进行渲染测试。
    4.  跑通 `Neural-BRDF/binary_to_nbrdf/binary_to_nbrdf.py` 脚本，将 MERL 数据转换为网络权重。

### 第二阶段：网络模型构建与训练 (Week 3-6)
*   **目标**: 复现并改进 BRDF 神经网络模型。
*   **任务**:
    1.  **数据准备**: 使用 `binary_to_nbrdf.py` 或 `HyperBRDF` 的数据处理脚本，制作训练数据集。
    2.  **模型复现**:
        *   运行 `Neural-BRDF` 的 PyTorch 版本训练代码，获得材质的神经网络权重。
        *   (进阶) 运行 `HyperBRDF` 代码，训练 HyperNetwork 以从稀疏采样重建 BRDF。
    3.  **权重转换**: 编写/使用脚本将训练好的 PyTorch 模型转换为 Mitsuba 插件可读取的格式 (如 `.npy` 或 `.bin`)。

### 第三阶段：渲染集成与验证 (Week 7-9)
*   **目标**: 在渲染器中应用训练好的模型，并验证效果。
*   **任务**:
    1.  配置 Mitsuba XML 场景文件，引用训练生成的 `.npy` 权重文件。
    2.  **定性分析**: 渲染 Sphere 或 Material Ball 场景，对比 Ground Truth (原始 MERL 数据渲染结果) 和神经网络预测结果的视觉差异。
    3.  **定量分析**: 计算 PSNR (峰值信噪比) 和 SSIM (结构相似性) 指标，评估表达精度。

### 第四阶段：系统开发与可视化 (Week 10-12)
*   **目标**: 开发可视化的材质属性表达与渲染系统。
*   **功能模块**:
    *   **数据上传**: 支持上传 `.binary` (MERL) 格式文件。
    *   **模型推断**: 后台调用 PyTorch 模型生成神经网络权重。
    *   **渲染预览**: 后台调用 `mitsuba.exe` 渲染预览图 (Preview)。
    *   **结果展示**: 在网页端左右对比显示 "原始材质" vs "神经材质"。
*   **技术实现**: 使用 Streamlit 搭建前端，通过 Python `subprocess` 调用 Mitsuba 命令行工具。

### 第五阶段：论文撰写与答辩准备 (Week 13-14)
*   整理实验数据、渲染对比图、误差分析图表。
*   撰写毕业设计论文。

---

## 4. 关键文件与资源说明

*   **渲染器核心**: `d:\AHEU\GP\mitsuba\dist\mitsuba.exe`
*   **渲染插件**: `d:\AHEU\GP\mitsuba\dist\plugins\nbrdf_npy.dll` (关键文件，已存在)
*   **参考代码**:
    *   `d:\AHEU\GP\Neural-BRDF\`: 包含基线网络结构和 Mitsuba 插件源码。
    *   `d:\AHEU\GP\HyperBRDF\`: 包含更先进的 HyperNetwork 方法。
*   **参考文献**: `d:\AHEU\GP\参考文献\` 目录下的论文。

## 5. 已完成进度

*   **基线渲染已跑通**: 使用 `D:\mitsuba\dist\mitsuba.exe` 渲染 `Neural-BRDF/mitsuba/sample_scene.xml` 成功。
*   **渲染结果输出**: `d:\AHEU\GP\Neural-BRDF\mitsuba\sample_scene.exr`。
*   **NBRDF 权重文件**: `d:\AHEU\GP\Neural-BRDF\binary_to_nbrdf\output\blue-metallic-paint_*.npy`。

## 6. 系统开发现状 (Framework Status)

目前已完成系统基础框架搭建，使用 **Streamlit** 作为前端交互界面。

*   **入口文件**: `d:\AHEU\GP\app.py`
*   **功能模块**:
    *   **项目概览**: 展示项目简介与当前各阶段完成情况。
    *   **数据管理**: 支持上传 MERL 二进制材质文件。
    *   **模型训练**: (初步搭建) 训练参数配置界面。
    *   **渲染与分析**: (初步对接) 渲染结果预览界面。

## 7. 下一步建议 (Next Steps)

1.  **启动系统**: 运行 `streamlit run app.py` 查看界面。
2.  **功能填充**: 编写 Python 脚本，将现有的 `Neural-BRDF` 训练代码集成到 Streamlit 中。
3.  **渲染自动化**: 实现自动化生成 Mitsuba XML 场景文件，使其能够根据 UI 选择的材质动态渲染。
