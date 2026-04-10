# V1 / V2 对照与切换结果

## 1. 当前结论

V1 已从仓库中移除，当前仓库只保留 V2。

当前入口：

- 开发：`scripts/start_v2_dev.ps1`
- 生产：`scripts/start_v2_prod.ps1`

## 2. 对照结论

| 能力 | V2 对应位置 | 状态 |
| --- | --- | --- |
| 渲染可视化 | [RenderWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/RenderWorkbench.tsx) | 已迁移 |
| 材质表达结果分析 | [AnalysisWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/AnalysisWorkbench.tsx) | 已迁移 |
| 网络模型管理 | [ModelsWorkbench.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/ModelsWorkbench.tsx) | 已迁移 |
| 设置 / 编译辅助 | [WorkspaceCanvas.tsx](/d:/AHEU/GP/MatReflect_NN/frontend/src/components/WorkspaceCanvas.tsx) | 已迁移 |

## 3. 已执行的 V1 清理

已删除：

- `app.py`
- `pages/`
- `pages/_modules/`
- `scripts/start_matreflect.ps1`
- `scripts/start_matreflect.cmd`
- 根依赖中的 `streamlit`

## 4. 迁移补齐结果

在删除前，已补齐以下原 V1 缺口：

- 自定义模型注册与删除
- 独立 `H5 -> NPY` 转换
- 分析模块自定义目录、输出目录和图片删除
- Mitsuba 编译辅助迁入 V2 设置页

## 5. 当前建议

后续工作都应以 V2 为唯一基线：

1. 不再新增任何 V1 兼容代码。
2. 所有文档、脚本、验证都以 V2 为准。
3. 后续若做回归测试，只验证 V2。
