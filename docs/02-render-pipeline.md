# 渲染链路

## 核心文件

- 后端：`backend/api/v1/render.py` + `backend/services/render_service.py`
- 前端：`frontend/src/components/RenderWorkbench.tsx` + `frontend/src/features/render/useRenderWorkbench.ts`

## 渲染模式

三种渲染模式对应不同输入类型：

| 模式 | 输入 | bsdf 插件 |
|---|---|---|
| `brdfs` | `.binary` | `merl` / `merl_accelerated` |
| `npy` | `*_fc1.npy` | `nbrdf_npy` / `SIREN_*` |
| `fullbin` | `.fullbin` | `fullmerl`（小文件自动回退 `merl`） |

## 工作模式

前端当前开放两种操作：

- **仅渲染** — `POST /api/v1/render/batch`
- **仅重建** — `POST /api/v1/render/reconstruct`

`render_after_reconstruct` 路径后端仍保留，但前端未开放。

## 默认场景选择（`render_service.py:get_default_scene_path`）

| 渲染模式 | 优先场景 |
|---|---|
| `fullbin` | `scene/dj_xml/hyperbrdf_ref.xml` |
| `npy` | `scene/dj_xml/scene_universal.xml` |
| `brdfs` | `scene/dj_xml/scene_universal.xml` |

依次回退到 `scene/dj_xml/*` → `scene/old_xml/*`。

## 运行时 XML 改写

渲染前后端会动态处理场景 XML：

1. 相对资源路径 → 绝对路径
2. `ldrfilm` → `hdrfilm`
3. 更新 `integrator` 类型和 `sampleCount`
4. 定位 `id="Material"` 的 bsdf 节点（或兼容类型）
5. 按渲染模式重写材质节点

关键函数：`find_target_bsdf`、`update_bsdf_for_mode`、`update_integrator_and_sampler`

临时 XML 写入 `backend/runtime/render_xml/`。

## FullBin / Binary 特殊逻辑

`fullbin` 模式下，若文件尺寸匹配标准 MERL `.binary`（`12 + 90*90*180*3*8` 字节），会自动改用 `merl` 插件渲染。即 `data/inputs/fullbin/` 中混入的 `.binary` 文件仍按 MERL 路径渲染。

## 输出命名

格式：`材质名_YYYYMMDD_HHMMSS`

涉及位置：
- 后端生成：`render_service.py`
- 前端解析：`frontend/src/lib/fileNames.ts`
- 分析匹配：`analysis_service.py`

仍兼容旧格式 `材质名_DD_HHMMSS`。

## EXR → PNG 转换

- `POST /api/v1/render/convert` — 批量转换
- 使用 `mtsutil.exe tonemap`
- 渲染批次中 `auto_convert=true` 时每张渲染完自动转换

## 进度解析

从 Mitsuba 输出中通过正则可解析渲染进度条 `Rendering: [...]` 来估算百分比。
