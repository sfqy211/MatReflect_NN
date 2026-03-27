# DecoupledHyperBRDF 改进设计文档

## 1. 目标

本文档将当前 `HyperBRDF` 单体网络，升级为一套更稳定、更可解释、对稀疏采样更友好的混合式 BRDF 重建方案：

`解析基底(analytic base) + 神经残差(neural residual) + 方向门控(confidence gate)`

该方案用于替代“单一网络直接拟合完整 BRDF”的训练范式，并兼容当前工程中的训练、推理、参数导出和 `.fullbin` 转换链路。

## 2. 背景与问题

当前实现的核心结构是：

- `SetEncoder` 对稀疏样本编码
- `HyperNetwork` 生成单个 `SingleBVPNet` 的参数
- `SingleBVPNet` 直接输出完整 BRDF

这一结构存在三个实际瓶颈：

1. 漫反射与镜面分量共享同一回归目标，动态范围和频率特性差异大，学习目标冲突。
2. 当前主损失是全局统一的重建损失，镜面高光面积小、频率高，容易被大面积低频区域淹没。
3. 在稀疏采样下，镜面信息本身就少，而当前 `SetEncoder` 采用简单均值池化，少量关键高光样本容易在编码阶段被平均掉。

论文《Hypernetworks for Generalizable BRDF Representation》已经明确指出，当前方法对 specular components 的估计较弱，并提出未来可以考虑 separate estimation pipeline。参考文献《Connecting Measured BRDFs to Analytic BRDFs by Data-Driven Diffuse-Specular Separation》进一步说明，更稳的方向不是纯粹把网络“硬拆三支”，而是先引入解析先验，再由神经网络补解析模型无法表达的残差。

## 3. 设计原则

本方案遵循以下原则：

1. 先让模型学习“容易、稳定、低维、可解释”的部分，再学习复杂残差。
2. 让高频高光成为残差学习目标，而不是让完整网络从零同时承担低频与高频建模。
3. 尽量复用当前工程的数据预处理、训练框架和导出链路，降低重构成本。
4. 在不破坏现有 `.pt -> .fullbin -> Mitsuba` 主链路的前提下，扩展保存格式与推理逻辑。

## 4. 总体方案

### 4.1 新架构概述

新模型命名为 `DecoupledHyperBRDF`，核心输出由三部分构成：

- `analytic base branch`
  预测低维解析材质参数，构造基础 BRDF。
- `residual branch`
  使用 hypernetwork 生成 hyponet 参数，仅学习解析基底无法覆盖的残差。
- `gate branch`
  逐方向输出融合权重，控制神经残差对最终 BRDF 的贡献。

最终预测形式为：

```text
pred_brdf(x) = analytic_brdf(x; theta)
             + sigmoid(g(x)) * residual_positive(x)
```

其中：

- `x` 为 BRDF 查询方向坐标
- `theta` 为解析 BRDF 参数
- `g(x)` 为门控分支输出
- `residual_positive(x)` 为残差分支输出，建议经过非负约束

### 4.2 为什么不采用“纯三分支独立神经网络”

原提案中“漫反射分支 + 镜面分支 + 门控分支”方向本身是合理的，但如果三个分支都完全神经化，会出现两个问题：

1. 分支语义不稳定
   模型没有显式监督时，“漫反射分支”未必真的学漫反射，只是学到某种更容易优化的低频子空间。
2. 计算成本偏高
   在当前工程里，真正的计算大头是 hypernetwork，而不是 hyponet 本体。三组独立超网络并不能算“很小的增量”。

因此本文档采用“解析基底 + 一个神经残差 + 一个轻量门控”的折中方案。它保留了解耦思想，但让各分支的职责更清晰，训练也更稳定。

## 5. 模型结构设计

### 5.1 编码器

编码器仍以当前 `SetEncoder` 为主体，但做两点升级：

1. 保留共享编码器，不为每个分支单独复制一套 encoder。
2. 将当前简单均值聚合升级为更稳的聚合策略。

建议优先采用：

```text
pooled = concat(mean(embeddings), max(embeddings))
```

原因：

- `mean` 保留整体材质基调
- `max` 更容易保留稀少但强烈的高光响应

若后续验证仍不足，再考虑 attention pooling。

### 5.2 解析基底分支

解析基底分支输入共享 latent，输出一组低维解析参数 `theta`。

推荐先实现两个版本中的一个：

#### MVP 版本

```text
Lambertian diffuse + single-lobe GGX specular
```

参数示例：

- `kd_luma` 或 `kd_rgb`
- `ks_intensity`
- `roughness`
- `ior`
- `spec_tint_rgb` 或单独 `spec_color`

#### 进阶版本

```text
Lambertian diffuse + two-lobe GGX specular
```

参数示例：

- `kd_luma` 或 `kd_rgb`
- `ks1_intensity`, `roughness1`, `ior1`
- `ks2_intensity`, `roughness2`, `ior2`
- `spec_tint_rgb`

建议开发顺序是先单 lobe，再双 lobe。双 lobe 明显更适合 MERL 中多峰高光材料，但实现复杂度更高。

### 5.3 神经残差分支

残差分支沿用当前 hypernetwork + hyponet 的思想，但它的目标不再是完整 BRDF，而是：

```text
residual_target = gt_brdf - analytic_brdf
```

建议使用单独的 `ResidualBVPNet`，结构可初期复用 `SingleBVPNet`，后续按验证结果决定是否减小宽度。

为了减少不合法 BRDF 残差带来的伪影，建议残差输出采用如下形式之一：

1. `softplus(raw_residual)`
2. `relu(raw_residual)`
3. 小范围双边残差
   `scale * tanh(raw_residual)`

推荐先用第 1 种，因为连续且更稳定。

### 5.4 门控分支

门控分支不直接表示“镜面占比”，而表示“残差是否应该被启用，以及启用到什么程度”。

门控分支形式：

```text
gate(x) = GateNet(x; gate_params)
alpha(x) = sigmoid(gate(x))
```

最终融合：

```text
pred = analytic + alpha * residual
```

初始化策略：

- 将 gate 最后一层 bias 初始化为负值，例如 `-2`
- 让初始 `sigmoid(gate)` 接近 `0`
- 使训练初期模型主要依赖解析基底

该策略能避免训练初期残差分支对结果造成大幅扰动。

## 6. 输出字典与接口约定

新模型 `forward` 返回：

```python
{
    "model_in": coords,
    "model_out": final_brdf,
    "analytic_out": analytic_brdf,
    "residual_out": residual_brdf,
    "gate_out": gate_alpha,
    "latent_vec": embedding,
    "analytic_params": analytic_params,
    "residual_hypo_params": residual_hypo_params,
    "gate_hypo_params": gate_hypo_params,
}
```

说明：

- `model_out` 继续作为主监督输出，兼容现有训练框架
- `analytic_out`、`residual_out`、`gate_out` 用于损失分解与日志输出
- 导出时保存 `analytic_params + residual_hypo_params + gate_hypo_params`

## 7. 训练目标设计

### 7.1 主重建损失

沿用当前 cosine-weighted BRDF to RGB 的主损失思想，但作用在最终输出上：

```text
L_recon = MSE( rgb(pred_final), rgb(gt) )
```

### 7.2 解析基底监督损失

解析基底需要获得显式监督，否则它会退化成一个形状随意的低频支路。

推荐两种监督来源：

1. 离线 analytic fit teacher
   对训练集每个材料预先拟合 `Lambert + GGX` 或 `Lambert + 2GGX`
2. 在线弱监督
   仅要求 `analytic_out` 在 achromatic 空间逼近低频主体

推荐工程路径：

- 第一阶段先做离线 teacher，最稳
- 如果 teacher 代价过高，再降级到 achromatic weak supervision

损失形式：

```text
L_analytic = MSE( analytic_out, teacher_analytic )
```

若采用 achromatic teacher：

```text
L_analytic_achro = MSE( mean(analytic_out, channel), mean(teacher, channel) )
```

### 7.3 残差监督损失

令：

```text
target_residual = clamp_min(gt - analytic_out.detach(), 0)
```

训练初期建议先 `detach` 解析分支，避免两支互相争抢解释权。

损失：

```text
L_residual = MSE( residual_out, target_residual )
```

如果允许双边残差，则不做 `clamp_min`，但要加更强正则。

### 7.4 高光感知损失

这是本次改造的关键损失。推荐增加至少一种高光感知损失：

#### 方案 A：基于强度阈值的加权损失

```text
mask_spec = 1[ gt > tau ]
L_spec = mean( mask_spec * (pred - gt)^2 )
```

#### 方案 B：基于解析基底差值的高光掩码

```text
mask_spec = normalize( clamp(gt - analytic_teacher, 0) )
L_spec = mean( mask_spec * (pred - gt)^2 )
```

推荐先从方案 A 开始，简单可用。

### 7.5 门控正则

训练初期应抑制门控与残差过早放大：

```text
L_gate = mean(gate_out)
```

或者：

```text
L_gate = mean(gate_out^2)
```

其目标不是让门控永远小，而是让训练前期先靠解析基底站稳。

### 7.6 现有正则保留

保留当前两项正则：

- latent loss
- hypo weight loss

但需扩展为只对残差/门控 hyponet 参数统计，避免把解析参数头也混进同一范式。

### 7.7 总损失

推荐总损失：

```text
L_total =
    w_recon    * L_recon
  + w_analytic * L_analytic
  + w_residual * L_residual
  + w_spec     * L_spec
  + w_gate     * L_gate
  + w_latent   * L_latent
  + w_fw       * L_hypo_weight
```

## 8. 训练阶段设计

### 8.1 阶段 A：稳定初始化

目标：

- 优先学习可解释、低频、稳定的解析基底
- 限制残差和门控的自由度

策略：

1. 复用 baseline checkpoint 的 encoder 权重
2. 若残差分支复用现有 hyponet 结构，允许用 baseline 权重初始化其一部分
3. gate bias 初始化为负值，例如 `-2`
4. `w_gate` 设大，`w_spec` 设小
5. 优先优化 `L_recon + L_analytic`

该阶段结束标准：

- 基础重建稳定
- `analytic_out` 已能给出合理基底
- `gate_out` 整体偏小但非零

### 8.2 阶段 B：联合微调

目标：

- 释放残差能力，增强高光细节拟合
- 逐步减小“解析基底独占解释权”的限制

策略：

1. 逐步增大 `w_spec`
2. 逐步减小 `w_gate`
3. 逐步提高残差分支学习率占比，或解除部分冻结
4. 根据验证集高光指标判断是否需要打开双 lobe base

### 8.3 阶段 C：可选精修

如果后期要追求视觉质量，可加入：

- 更强的 spec-only 验证集 early stop
- 更细的 material-type curriculum
- 更高分辨率或更密 query 的最终精调

该阶段不是 MVP 必需项。

## 9. 数据与采样改造

### 9.1 当前问题

当前 `data_processing.py` 中 `context_coords/context_amps` 是纯随机采样。对于镜面主导材质，重要样本可能在 4000 个点中占比极低。

### 9.2 建议改造

采用混合采样：

```text
context = random_samples + highlight_samples + near-specular samples
```

推荐比例：

- `50%` 随机采样
- `25%` 高值 BRDF 采样
- `25%` 接近镜面方向的几何采样

说明：

- 高值采样有助于稳定恢复高光峰值
- 几何接近镜面方向的采样有助于学习高光峰形
- 保留随机采样以维持整体分布泛化

### 9.3 解析 teacher 数据缓存

如果采用离线 analytic teacher，建议新增缓存目录，例如：

```text
data/analytic_teacher/
```

每个材质保存：

- `analytic_params`
- `analytic_eval_full`
- 可选 `spec_mask`

以避免训练时重复拟合。

## 10. 文件级实施设计

### 10.1 `models.py`

新增或修改内容：

1. 新增 `AnalyticBRDFHead`
   从 shared latent 输出解析参数。
2. 新增 `ResidualHyperBRDF` 或复用 `SingleBVPNet`
   用于预测残差。
3. 新增 `GateBVPNet`
   输出逐方向 gate logits。
4. 新增 `DecoupledHyperBRDF`
   整合共享 encoder、解析头、残差 hypernet、门控 hypernet。
5. 新增 `eval_analytic_brdf(coords, analytic_params)`
   给定坐标和参数，计算解析基底。

建议保留旧 `HyperBRDF` 类，方便回归测试和对照实验。

### 10.2 `main.py`

新增或修改内容：

1. 模型实例化切换
   增加 `--model_type {baseline, decoupled}`。
2. 新增损失函数
   `analytic_loss`
   `residual_loss`
   `spec_loss`
   `gate_reg_loss`
3. 新增训练阶段控制参数
   `--stage_a_epochs`
   `--gate_bias_init`
   `--spec_loss_weight`
   `--analytic_loss_weight`
4. 新增日志项
   `analytic_loss`
   `residual_loss`
   `spec_loss`
   `gate_mean`
5. 允许加载 baseline checkpoint 并部分映射到新模型

### 10.3 `data_processing.py`

新增或修改内容：

1. 实现混合 context 采样逻辑
2. 可选返回 `spec_mask` 或 `teacher_analytic`
3. 保持默认行为向后兼容

建议通过新参数开关控制：

- `--sampling_mode random`
- `--sampling_mode hybrid`

### 10.4 `test.py`

当前逻辑仅导出一组 `hypo_params`。新方案下应导出结构化参数字典：

```python
{
    "model_type": "decoupled",
    "analytic_params": ...,
    "residual_hypo_params": ...,
    "gate_hypo_params": ...,
}
```

同时保留 baseline 兼容格式：

```python
{
    "model_type": "baseline",
    "hypo_params": ...
}
```

### 10.5 `pt_to_fullmerl.py`

推理逻辑从“单网络前向”改为：

1. 加载 `.pt` 参数字典
2. 若是 `baseline`
   走原有单 hyponet 推理
3. 若是 `decoupled`
   - 计算 `analytic_brdf`
   - 计算 `residual_brdf`
   - 计算 `gate`
   - 融合得到最终 BRDF
4. 做反归一化并导出 `.fullbin`

### 10.6 新增工具脚本

建议新增：

```text
fit_analytic_teacher.py
```

职责：

- 为 MERL 材质生成 analytic teacher
- 缓存参数与 full-grid 评估结果

这是后续训练稳定性的关键辅助脚本。

## 11. 推理与导出兼容设计

### 11.1 `.pt` 保存格式

建议统一采用显式字段，而不是依赖“字典形状猜测”：

```python
{
    "format_version": 2,
    "model_type": "decoupled",
    "dataset": "MERL",
    "analytic_params": ...,
    "residual_hypo_params": ...,
    "gate_hypo_params": ...,
}
```

### 11.2 导出流程

链路保持不变：

```text
checkpoint.pt
-> test.py 生成材质参数 .pt
-> pt_to_fullmerl.py 生成 .fullbin
-> Mitsuba 评估
```

变化点只在于：

- `test.py` 输出参数字典，而不是单个 hyponet 参数
- `pt_to_fullmerl.py` 改为识别 `model_type`

## 12. 评估指标

除沿用现有整体重建误差外，建议新增以下验证指标：

1. 全局 `img_loss`
2. 高光区域 `spec_loss`
3. achromatic base 误差
4. 稀疏采样稳定性曲线
   比较 `N = 40, 160, 400, 2000, 4000`
5. 导出后 `.fullbin` 的 Mitsuba 渲染误差

推荐重点关注两类现象：

- 高光是否更清晰
- 稀疏样本下结果是否更稳定

## 13. 风险与应对

### 风险 1：解析基底过强，残差学不到东西

应对：

- 阶段 B 逐步降低 `w_analytic`
- 逐步释放 gate
- 检查 `gate_mean` 和 `residual_norm`

### 风险 2：残差分支学习噪声，出现伪高光

应对：

- 残差输出非负约束
- 增加残差平滑或权重正则
- 提高 gate 约束

### 风险 3：analytic teacher 质量不稳定

应对：

- MVP 先用单 lobe GGX
- teacher 仅作为弱监督，不作为硬标签
- 对失败材质允许退化为 achromatic weak teacher

### 风险 4：导出链路复杂度上升

应对：

- 明确 `model_type` 和 `format_version`
- 保留 baseline 分支
- 先完成 `.pt` 与 `.fullbin` 的双格式兼容

## 14. 实施顺序

推荐按以下顺序落地：

### 阶段 1：MVP

1. 新增 `DecoupledHyperBRDF`
2. 实现 `analytic base(single GGX) + residual + gate`
3. 新增主损失、高光损失、门控正则
4. 改造 `test.py` 和 `pt_to_fullmerl.py` 支持新格式

### 阶段 2：稳定性增强

1. 改造 `SetEncoder` 聚合策略
2. 改造 `data_processing.py` 的混合采样
3. 加入 analytic teacher 缓存

### 阶段 3：性能增强

1. 升级到 two-lobe GGX base
2. 增加更细的 residual/gate 约束
3. 做系统性的稀疏采样和渲染评估

## 15. 最终结论

相较于“纯三分支独立超网络”的方案，本文档推荐的实现路线是：

```text
共享编码器
+ 解析基底分支
+ 神经残差分支
+ 轻量门控分支
```

这是一个更适合当前代码库的折中方案，原因是：

1. 更符合 measured BRDF 的物理结构
2. 更容易利用解析先验稳定训练
3. 更适合稀疏样本条件下的高光恢复
4. 对现有训练和导出链路改动更可控

后续代码实现应以本设计文档为准，优先完成 MVP，再逐步加入 teacher、混合采样和双 lobe 基底。
