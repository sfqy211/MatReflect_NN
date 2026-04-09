# V1 退役检查清单

## 1. 当前结论

当前已完成此前识别的 V1 -> V2 迁移缺口补齐，项目状态可更新为：

- V2：默认主入口，功能已覆盖渲染、分析、模型管理、设置页编译辅助。
- V1：仅作为待删除的历史兼容层保留。
- V1 全量删除：可以开始准备，不再需要继续补迁移功能。

## 2. 本轮补齐项

本轮已完成以下迁移缺口：

1. 自定义模型注册修复
   - 修复 [model_registry.py](/d:/AHEU/GP/MatReflect_NN/backend/services/model_registry.py) 将 `runtime.conda_env` 误判为项目路径的问题。
   - 已通过 `POST /api/v1/train/models` 与 `DELETE /api/v1/train/models/{model_key}` 实测闭环。

2. 分析页 V1 能力补齐
   - 新增自定义预览目录支持。
   - 新增图片删除与对应 EXR 清理接口。
   - 新增自定义评估目录与评估标签。
   - 新增网格拼图自定义源目录、输出目录。
   - 新增对比拼图自定义列目录、列标签、输出目录。
   - 相关入口：
     - [analysis.py](/d:/AHEU/GP/MatReflect_NN/backend/api/v1/analysis.py)
     - [analysis_service.py](/d:/AHEU/GP/MatReflect_NN/backend/services/analysis_service.py)
     - [AnalysisWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/AnalysisWorkbench.tsx)

3. 独立 `H5 -> NPY` 转换迁入 V2
   - 新增后端任务接口：`POST /api/v1/train/neural/keras/convert`
   - 新增模型管理页独立转换面板。
   - 修复当前环境下的两个真实兼容性问题：
     - V2 训练/转换任务未稳定找到 Conda，可能错误退回当前 Python。
     - `Neural-BRDF` 的 `h5_to_npy` 在当前环境下存在 Keras JSON 反序列化兼容问题。
   - 相关修改：
     - [conda.py](/d:/AHEU/GP/MatReflect_NN/backend/core/conda.py)
     - [train_service.py](/d:/AHEU/GP/MatReflect_NN/backend/services/train_service.py)
     - [render_service.py](/d:/AHEU/GP/MatReflect_NN/backend/services/render_service.py)
     - [common.py](/d:/AHEU/GP/MatReflect_NN/Neural-BRDF/binary_to_nbrdf/common.py)

## 3. 已完成验证

### 3.1 静态验证

- `backend` 相关 Python 文件 `py_compile` 通过。
- `frontend` 执行 `npm run build` 通过。

### 3.2 运行时验证

已在临时 FastAPI 服务上完成以下验证：

1. 渲染闭环
   - `binary -> render -> png/exr` 已通过。

2. HyperBRDF 解码闭环
   - `pt -> fullbin` 已通过。

3. 分析闭环
   - `GET /api/v1/analysis/images`
   - `POST /api/v1/analysis/evaluate`
   - `POST /api/v1/analysis/grid`
   - `POST /api/v1/analysis/comparison`
   - `POST /api/v1/analysis/delete-image`
   - 已生成并验证自定义输出文件。

4. 模型管理闭环
   - 自定义模型新增、删除已通过。
   - 独立 `H5 -> NPY` 转换已成功输出到 `backend/runtime/uat_npy`。

## 4. 可以删除 V1 的范围

在开始正式删除时，可按以下顺序执行：

1. 删除 V1 启动入口
   - [app.py](/d:/AHEU/GP/MatReflect_NN/app.py)
   - [pages/1_Mitsuba_Render_Tool.py](/d:/AHEU/GP/MatReflect_NN/pages/1_Mitsuba_Render_Tool.py)
   - [pages/2_Model_Training.py](/d:/AHEU/GP/MatReflect_NN/pages/2_Model_Training.py)
   - [pages/3_Data_Analysis.py](/d:/AHEU/GP/MatReflect_NN/pages/3_Data_Analysis.py)

2. 删除 V1 共享模块
   - [pages/_modules/render_tool_page.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/render_tool_page.py)
   - [pages/_modules/render_tool_actions.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/render_tool_actions.py)
   - [pages/_modules/analysis_page.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/analysis_page.py)
   - [pages/_modules/training_page.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/training_page.py)
   - [pages/_modules/training_neural_tab.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/training_neural_tab.py)
   - [pages/_modules/training_hyper_tab.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/training_hyper_tab.py)
   - [pages/_modules/training_actions.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/training_actions.py)
   - [pages/_modules/ui_shell.py](/d:/AHEU/GP/MatReflect_NN/pages/_modules/ui_shell.py)

3. 删除 V1 启动脚本
   - [scripts/start_matreflect.ps1](/d:/AHEU/GP/MatReflect_NN/scripts/start_matreflect.ps1)
   - [scripts/start_matreflect.cmd](/d:/AHEU/GP/MatReflect_NN/scripts/start_matreflect.cmd)

4. 清理文档中的 V1 入口说明
   - [README.md](/d:/AHEU/GP/MatReflect_NN/README.md)
   - [V2_QUICK_START.md](/d:/AHEU/GP/MatReflect_NN/V2_QUICK_START.md)
   - [V2_CUTOVER_GUIDE.md](/d:/AHEU/GP/MatReflect_NN/V2_CUTOVER_GUIDE.md)

## 5. 删除前建议

- 先单独提交本轮“迁移补齐”修改。
- 再新开一次提交执行 V1 文件删除，便于回滚。
- 删除 V1 时不要动 `data/`、`results/`、`mitsuba/`、`Neural-BRDF/`、`HyperBRDF/` 的实验资产与上游代码。

## 6. 最终状态

- 现在是否还存在阻止 V1 退役的迁移缺口：没有。
- 下一步建议：开始执行 V1 删除准备，并分批删除 V1 入口、模块和脚本。
