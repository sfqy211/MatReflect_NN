# V1 / V2 对照与当前结论

## 1. 当前结论

截至本轮验证，V2 已完成对 V1 核心能力的替代，可以进入 V1 退役准备阶段。

当前建议定义为：

- V2：唯一推荐入口。
- V1：历史兼容层，下一阶段可删除。

## 2. 模块对照

| 能力 | V1 Streamlit | V2 Workspace | 当前状态 |
| --- | --- | --- | --- |
| 渲染可视化 | `pages/_modules/render_tool_page.py` | [RenderWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/RenderWorkbench.tsx) | 已迁移并完成闭环验证 |
| 材质表达结果分析 | `pages/_modules/analysis_page.py` | [AnalysisWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/AnalysisWorkbench.tsx) | 已迁移并补齐 V1 缺口 |
| 网络模型管理 | `pages/_modules/training_page.py` | [ModelsWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/ModelsWorkbench.tsx) | 已迁移并补齐 V1 缺口 |
| 设置 / 编译辅助 | V1 内嵌在旧页面逻辑中 | [WorkspaceCanvas.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/WorkspaceCanvas.tsx) | 已迁入 V2 设置页 |
| 网页终端 | `pages/4_Terminal.py` | 不再保留 | 已删除 |

## 3. 本轮完成的关键补齐

### 3.1 模型管理

- 修复自定义模型注册失败问题。
- 补齐独立 `H5 -> NPY` 转换入口。
- 修复训练/转换任务的 Conda 环境解析，避免错误退回当前 Python。

### 3.2 分析模块

- 补齐自定义预览目录。
- 补齐图片删除及对应 EXR 清理。
- 补齐自定义评估目录与标签。
- 补齐自定义拼图目录、列标签、输出目录。

### 3.3 环境兼容

- 修复 `Neural-BRDF` 在当前环境中的 Keras JSON 反序列化兼容问题。

## 4. 已验证结果

### 4.1 静态验证

- `frontend/npm run build` 通过。
- 相关 Python 文件 `py_compile` 通过。

### 4.2 API / 工作流验证

已完成以下实测：

1. 渲染
   - `binary -> png/exr` 成功。

2. HyperBRDF 解码
   - `pt -> fullbin` 成功。

3. 分析
   - 图片查询成功。
   - 量化评估成功。
   - 网格拼图成功。
   - 对比拼图成功。
   - 图片删除成功。

4. 模型管理
   - 自定义模型新增成功。
   - 自定义模型删除成功。
   - 独立 `H5 -> NPY` 转换成功。

## 5. 是否还需要保留 V1 作为功能兜底

从核心功能角度看，不再需要。

如果保留 V1，唯一价值只剩：

- 历史参考代码
- 回看旧 UI 行为

这不再属于“功能迁移未完成”，而属于“是否要保留历史代码”的工程决策。

## 6. 下一步建议

下一步不再是继续补迁移，而是直接执行 V1 退役：

1. 删除 `app.py` 与 `pages/`
2. 删除 `pages/_modules/`
3. 删除 `scripts/start_matreflect.*`
4. 清理 README 与快速开始文档中的 V1 描述
5. 最后再做一轮仅针对 V2 的回归检查
