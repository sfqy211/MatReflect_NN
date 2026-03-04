# MatReflect_NN

本目录包含基于 Streamlit 的一体化工具，将 Mitsuba 渲染、EXR 转换、编译、量化评估与图像工具拆分为多个小页面，便于独立操作与后续扩展。

## 启动方式

在命令行进入该目录后执行：

```bash
streamlit run app.py
```

## 页面结构

- 首页：展示全局配置与路径概览
- Mitsuba 渲染：批量渲染（BRDF / FullBin / NPY）
- EXR 转 PNG：批量转换渲染输出
- 编译：自动生成脚本并调用 SCons
- 量化评估：PSNR / SSIM / Delta E
- 网格拼图：将目录图片拼为大图
- 对比拼图：同名三列对比输出
- 日志：查看与清空操作日志

## 全局配置说明

左侧导航栏包含全局配置：

- 项目根目录：默认 `d:\AHEU\GP\MatReflect_NN`
- Mitsuba 目录：默认 `d:\mitsuba\dist`
- Mitsuba 可执行文件 / Mtsutil 可执行文件
- 场景 XML：默认指向 `Neural-BRDF\mitsuba\sample_scene.xml`

## 依赖环境

建议使用当前已验证的环境：

- Python 3.7+（当前环境已安装）
- streamlit
- opencv-python
- scikit-image
- pillow
- numpy

如需安装：

```bash
python -m pip install streamlit opencv-python scikit-image pillow numpy
```

## 目录约定

默认输入输出目录如下（可在页面中手动调整）：

- BRDF 输入：`data\inputs\brdfs`
- BRDF 输出：`data\outputs\brdfs`
- FullBin 输入：`data\inputs\fullbin`
- FullBin 输出：`data\outputs\fullbin`
- NPY 输入：`data\inputs\npy`
- NPY 输出：`data\outputs\npy`

## 后续开发建议

可按以下方向扩展：

- 训练模块接入（Neural-BRDF / HyperBRDF）
- 结果可视化与对比报表导出
- 一键渲染与材质预览模板
