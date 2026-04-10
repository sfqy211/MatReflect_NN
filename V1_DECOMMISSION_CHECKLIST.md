# V1 退役检查清单

## 1. 当前状态

V1 退役已经执行完成，仓库内已不再保留 Streamlit 入口与相关页面代码。

## 2. 已完成事项

- [x] 删除 `app.py`
- [x] 删除 `pages/`
- [x] 删除 `pages/_modules/`
- [x] 删除 `scripts/start_matreflect.ps1`
- [x] 删除 `scripts/start_matreflect.cmd`
- [x] 从 `requirements.txt` 移除 `streamlit`
- [x] 更新 `README.md`
- [x] 更新 `V2_QUICK_START.md`
- [x] 更新 `V2_CUTOVER_GUIDE.md`
- [x] 更新 `AGENTS.md`

## 3. 删除前已确认的迁移结果

删除前已确认以下能力都在 V2 中可用：

- 渲染闭环
- 分析闭环
- 自定义模型注册 / 删除
- 独立 `H5 -> NPY` 转换
- HyperBRDF 提取与解码
- Mitsuba 编译辅助

## 4. 现在的唯一入口

- 开发：`scripts/start_v2_dev.ps1`
- 生产：`scripts/start_v2_prod.ps1`

## 5. 后续原则

1. 后续新功能只落在 V2。
2. 不再恢复 V1 兼容入口。
3. 回归测试只针对 V2。
