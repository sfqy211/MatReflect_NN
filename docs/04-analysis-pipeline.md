# 分析链路

## 核心文件

- 后端：`backend/services/analysis_service.py`
- 前端：`frontend/src/components/AnalysisWorkbench.tsx` + `frontend/src/features/analysis/useAnalysisWorkbench.ts`
- 文件名工具：`frontend/src/lib/fileNames.ts`

## 功能

| 子视图 | 说明 |
|---|---|
| 量化评估 | PSNR / SSIM / Delta E 三组对比（GT vs M1, GT vs M2, M1 vs M2） |
| 图像对比滑块 | 两张图片的左右对比 |
| 网格拼图 | 将多张图片排列成网格 |
| 对比拼图 | 多列材质并排对比（支持列标签头） |

## 图片管理

- 支持 PNG 预览（通过 `/media/outputs` 挂载）
- 支持删除，并可级联删除同名 EXR

## 材质名匹配

**不是按完整文件名严格匹配**，而是先归一化再比较。

归一化规则（`normalize_material_name`）：
- 去掉新时间戳 `_YYYYMMDD_HHMMSS`
- 去掉旧时间戳 `_DD_HHMMSS`
- 去掉 `_fc1` 后缀
- 去掉 `.binary` / `.fullbin` 扩展名

## 数据集

分析模块使用 5 组图片集：

| 图像集 | 标签 |
|---|---|
| `brdfs` | GT / BRDF |
| `fullbin` | FullBin |
| `npy` | NPY |
| `grids` | Grids |
| `comparisons` | Comparisons |

所有目录通过系统设置中配置的路径解析，支持通过 `directory` 参数覆盖为自定义路径。

## 注意事项

修改输出文件命名规则或 NPY / FullBin 文件命名方式时，必须同步检查 `analysis_service.py` 的 `normalize_material_name` 函数和 `frontend/src/lib/fileNames.ts`。
