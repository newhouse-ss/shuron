# P0：Round 4 标注变化与回归核查

日期：2026-10-06。核查 run：20260802_gpt54-high_moderation，NCBI Disease，Azure/OpenAI eastus2-gpt-5.4，reasoning_effort=high。本文根据保存输出离线核查，没有重新调用模型，也没有执行 P1 消融。

## 结论

**Round 4 在这批开发文档上的整体得分提高，但目标簇只修复了 1/3，且出现 1 个新增回归。**

- 整体：TP **63 至 65**，FP **5 至 4**，FN **11 至 9**，F1 **0.8873 至 0.9091**。逐实体变化为 **3 个修复、1 个新增回归**，净增 2 个 TP。
- 本轮目标是三个 SpecificDisease 漏标。只有“deficiency of hepatic phenylalanine hydroxylase”恢复；FALDH 和特定跨度“deficiency in G6PD”仍漏标。另两个修复是目标簇之外的 Tay-Sachs disease 和 TSD 类型错误。
- 新增回归是“cutaneous vasculitis”：SpecificDisease 变成 DiseaseClass。其余 7 篇文档的预测跨度和标签集合与 Round 3 后完全相同。
- norrin 和 FALDH 的漏标早于 Round 3。Round 4 新增 norrin 排除示例，保留并改写 FALDH 排除示例，文本仍与 gold 不一致；不能把这些既有漏标写成 Round 4 新增回归。
- 保存结果能够确认以上变化，尚不能证明某条“do not apply”限制造成了它们。因果问题留给 P1/P2。

## 1. 比较对象与核查口径

**R0** 为初始指南标注；**R1 至 R4 后**为各轮接受后的标注。Round 3 前对应 R2 后，Round 4 前对应 R3 后。全文的“新增回归”指上一状态精确匹配 gold、本轮变为不匹配的实体，不预设是某句规则造成。

输入为同一批 **10 篇训练集抽样开发文档、74 个 gold 实体**，sample seed=42，n_examples=5。这些是开发结果，不能当作 validation 或专家替代能力的证据。

核查已通过：

1. 所有状态的文档 ID 一致，保存的 gold 与本地语料 gold 的跨度及类型一致。
2. gold 和预测文本均与文档对应跨度一致，未发现重复标注。
3. R3 后 diagnostics 与 R4 前 diagnostics 完全一致，指南文本也衔接一致；最终 diagnostics 等于 R4 后。
4. 从逐实体标注重新计算的严格 TP/FP/FN/F1，与保存的循环 summary 和 PubAnnotation evaluation 相符。
5. 以当前原框架的错误分簇函数重新分簇，结果与保存的 summary.all_clusters 一致。

具体证据：[输入文档清单](../outputs/ncbi_disease/20260802_gpt54-high_moderation/inputs/sampled_train_documents.json)、[运行配置](../outputs/ncbi_disease/20260802_gpt54-high_moderation/inputs/resolved_run_config.json)、[Round 3 snapshot](../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/snapshot.json)、[Round 4 snapshot](../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/snapshot.json)。

## 2. 整体结果：得分提升包含目标簇外的变化

| 状态 | TP | FP | FN | 预测实体数 | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2 后（R3 前） | 61 | 7 | 13 | 68 | 0.8971 | 0.8243 | 0.8592 |
| R3 后（R4 前） | 63 | 5 | 11 | 68 | 0.9265 | 0.8514 | 0.8873 |
| R4 后 | 65 | 4 | 9 | 69 | 0.9420 | 0.8784 | 0.9091 |

R4 的 F1 增量为 **0.0218**（约 2.18 个百分点）。R3 的 63 个 TP 中，62 个保持正确，1 个变错；另外新增 3 个 TP，得到最终 65 个。

按 gold 类别分解：

| 类别 | Gold 数 | R3 后 TP/FP/FN | R4 后 TP/FP/FN | F1：R3 后至 R4 后 |
| --- | --- | --- | --- | --- |
| SpecificDisease | 44 | 36/1/8 | 38/1/6 | 0.8889 至 0.9157 |
| DiseaseClass | 9 | 7/2/2 | 7/3/2 | 0.7778 至 0.7368 |
| Modifier | 19 | 19/2/0 | 19/0/0 | 0.9500 至 1.0000 |
| CompositeMention | 2 | 1/0/1 | 1/0/1 | 0.6667 至 0.6667 |

SpecificDisease 净增加 2 个 TP；Modifier 的两个 FP 消失，因为 Tay-Sachs disease 和 TSD 改标为正确的 SpecificDisease。DiseaseClass 额外增加一个 FP，来自 cutaneous vasculitis。**总体提高与某个类别退化同时发生。**

## 3. 本轮实际目标与相关案例的完整历史

以下案例来自各轮保存的 infer_discrepancy_patterns 提示，实际输入可核查：[Round 3 提示](../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/infer_discrepancy_patterns.txt)、[Round 4 提示](../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/infer_discrepancy_patterns.txt)。

- **Round 3：Gold DiseaseClass / Pred O，3 例。** abnormal retinal vascular development、deficiency of norrin、spasticity。
- **Round 4：Gold SpecificDisease / Pred O，3 例。** deficient activity of fatty aldehyde dehydrogenase、deficiency in G6PD、deficiency of hepatic phenylalanine hydroxylase。

缩写：S=SpecificDisease，D=DiseaseClass，M=Modifier，C=CompositeMention，O=对应 gold 跨度未预测实体。位置使用零起始半开区间 [start,end)，用于区分同文档中的不同出现位置。

| 文档与位置 | 实体 | Gold | R0 | R1 后 | R2 后 | R3 后 | R4 后 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10484772 [186,223) | abnormal retinal vascular development | D | O | O | O | O | O |
| 10484772 [949,969) | deficiency of norrin | D | O | O | O | O | O |
| 10577908 [228,238) | spasticity | D | D | O | O | D | D |
| 10577908 [245,295) | deficient activity of fatty aldehyde dehydrogenase | S | O | O | O | O | O |
| 1303173 [1559,1577) | deficiency in G6PD | S | O | O | O | O | O |
| 1671881 [138,185) | deficiency of hepatic phenylalanine hydroxylase | S | S | S | S | O | S |

由此可以确定：

- **Round 3 目标中的 1 个修复是 spasticity。** 该 run 的保存 gold 为 DiseaseClass，R3 后正确，R4 后保持。它在初始状态正确，R1 后丢失，到 R3 才恢复。
- abnormal retinal vascular development 和 deficiency of norrin 从初始状态至 R4 一直漏标。
- FALDH 和特定跨度 deficiency in G6PD 也一直漏标，不能称为 R3 的新回归。G6PD 文档中的其他实体出现位置另有正确标注，不能把此结论扩展成“所有 G6PD mention 都漏标”。
- **PAH deficiency 是 R3 新丢失的原 TP，由 R4 恢复。** 因此，本轮目标修复主要是恢复上一轮回归，没有修复另外两例较早存在的漏标。

若此前讨论把 spasticity 的 gold 当作 SpecificDisease，应按这里的已保存 DiseaseClass 记录修正。本报告没有改动 gold。

## 4. Round 4 的全部实体级变化

对 10 篇文档的全部预测集合做差，发现 **4 个 gold 实体的结果发生变化，分布在 3 篇文档**。其中包含一次新增标注和三次同跨度类型改变；没有其他预测跨度或类型改变。

| 文档与位置 | 实体 | Gold | R3 后 | R4 后 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1671881 [138,185) | deficiency of hepatic phenylalanine hydroxylase | S | O | S | 修复 |
| 6859721 [646,666) | cutaneous vasculitis | S | S | D | 新增回归 |
| 8326491 [193,210) | Tay-Sachs disease | S | M | S | 修复 |
| 8326491 [213,216) | TSD | S | M | S | 修复 |

三篇改变的文档及严格计数：

| 文档 | R3 后 TP/FP/FN | R4 后 TP/FP/FN | 变化 |
| --- | --- | --- | --- |
| 1671881 | 4/1/2 | 5/1/1 | PAH deficiency 恢复，TP+1、FN-1 |
| 6859721 | 11/1/1 | 10/2/2 | cutaneous vasculitis 变错，TP-1、FP+1、FN+1 |
| 8326491 | 4/2/2 | 6/0/0 | Tay-Sachs disease 与 TSD 修复，TP+2、FP-2、FN-2 |

Tay-Sachs disease 与 TSD 来自同一上下文，不能解释为两个独立的实验重复。这里的 cutaneous vasculitis 特指 [646,666) 这次出现，另一处 [192,212) 在 R3 和 R4 均正确。受影响跨度在 R0 至 R4 的标签序列为 **D、S、D、S、D**，跨轮反复变化；这强化了继续检查稳定性的必要性，但不能区分规则改动与随机标注各自的作用。

## 5. 错误混淆矩阵

这里使用该 run 保存的错误分簇口径，**行是 Gold，列是模型预测**。矩阵只计错误，不包括 TP：

- 非 O 的对角线表示同类型但跨度不匹配，**不是正确标注**。
- O 列表示分簇中的漏标；O 行表示额外预测。
- O/O=0 不代表 true negative 数量。NER 中未枚举全部非实体字符。
- 类型错误及跨度错误各计一次 discrepancy，但严格评价同时记一个 FP 和一个 FN。因此，矩阵总数不等于 FP+FN。

### Round 3 前，R2 后

| Gold \\ Pred | SpecificDisease | DiseaseClass | Modifier | CompositeMention | O |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 1 | 3 | 2 | 0 | 2 |
| DiseaseClass | 1 | 0 | 0 | 0 | 3 |
| Modifier | 0 | 0 | 0 | 0 | 0 |
| CompositeMention | 0 | 0 | 0 | 0 | 1 |
| O | 0 | 0 | 0 | 0 | 0 |

总 discrepancy **13**：6 个类型错误、1 个跨度错误、6 个漏标。

### Round 3 后，Round 4 前

| Gold \\ Pred | SpecificDisease | DiseaseClass | Modifier | CompositeMention | O |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 1 | 2 | 2 | 0 | 3 |
| DiseaseClass | 0 | 0 | 0 | 0 | 2 |
| Modifier | 0 | 0 | 0 | 0 | 0 |
| CompositeMention | 0 | 0 | 0 | 0 | 1 |
| O | 0 | 0 | 0 | 0 | 0 |

总 discrepancy **11**：4 个类型错误、1 个跨度错误、6 个漏标。Round 3 的整体收益也不局限于其目标簇：除 spasticity 恢复外，exudative retinal detachment 的原有类型错误被修正，cutaneous vasculitis 恢复正确类型，同时 PAH deficiency 丢失。

### Round 4 后

| Gold \\ Pred | SpecificDisease | DiseaseClass | Modifier | CompositeMention | O |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 1 | 3 | 0 | 0 | 2 |
| DiseaseClass | 0 | 0 | 0 | 0 | 2 |
| Modifier | 0 | 0 | 0 | 0 | 0 |
| CompositeMention | 0 | 0 | 0 | 0 | 1 |
| O | 0 | 0 | 0 | 0 | 0 |

总 discrepancy **9**：3 个类型错误、1 个跨度错误、5 个漏标。相对 R4 前：

| 错误分组 | 前 | 后 | 逐例对应 |
| --- | --- | --- | --- |
| Gold S / Pred O | 3 | 2 | 恢复 PAH deficiency |
| Gold S / Pred M | 2 | 0 | 修复 Tay-Sachs disease、TSD |
| Gold S / Pred D | 2 | 3 | 新增 cutaneous vasculitis 回归 |
| Gold D / Pred O | 2 | 2 | abnormal development、norrin 未变 |
| Gold S / Pred S（跨度错误） | 1 | 1 | unilateral retinal telangiectasis 未变 |
| Gold C / Pred O | 1 | 1 | 脂质积累的 CompositeMention 未变 |

## 6. 规则变化与标注变化的对应边界

比较 snapshot.guidelines_before 与 guidelines_after，可以确认 R4 主要做了以下修改：

| 修改 | 保存文本位置 | 实际结果 |
| --- | --- | --- |
| Rule 1 新增“缺失/缺乏/功能降低表达 + 特定分子实体”可作为 SpecificDisease 的条件，另排除单纯生化测量/机制描述 | R4 指南第 12 至 13 行 | 三个目标中仅 PAH deficiency 恢复 |
| 原分子/过程排除限制前增加 “Outside the deficit/absence/reduced-function case described above” | 第 14 行 | 限制文本被缩小，但另两例目标漏标仍存在 |
| Rule 5 要求保留识别病理缺乏状态所必需的分子补语 | 第 101 行 | PAH deficiency 的完整 gold 跨度得到恢复 |
| 增加 C7 deficiency 正例，并新增 deficiency of norrin 排除示例 | 第 43 至 52 行 | norrin 仍为 O；其排除文本与 gold D 不一致 |
| 保留并改写 R3 已新增的 FALDH 排除示例，其他条目继续补充相同排除逻辑 | 第 54 至 57、167 至 168、263 至 264 行 | FALDH 仍为 O；排除文本与 gold S 不一致 |

原始指南：[R3 后](../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/guidelines_after.txt)、[R4 后](../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/guidelines_after.txt)。

需要准确区分：

1. **FALDH 排除示例在 R3 新增，norrin 排除示例在 R4 新增。** 两个对应跨度在新增文本之前就已漏标，不能据此认定新增示例首次造成了漏标。
2. R4 同时修改了 Rule 1、Rule 5 和多个示例，观察到的 PAH 恢复不能唯一归因于缩小“do not apply”作用域。
3. R4 diff 没有直接针对 Tay-Sachs disease、TSD 或 cutaneous vasculitis 的新增专门条款；这些标签变化发生在整份指南改写后的重新标注中，无法由当前记录指定哪一句造成。
4. “gold 与排除示例不一致”是这里能直接证明的事实。是否属于指南内部逻辑矛盾、例句丢失上下文、或原则条件被错误判断，需要分别分析；本报告没有将这些原因合并为已确定结论。

## 7. Round 4 仍未解决的全部错误

共 9 个 discrepancy：

| 文档 | Gold 实体 | Gold | R4 预测 | 状态相对 R3 后 |
| --- | --- | --- | --- | --- |
| 1671881 | PAH deficiencies | S | D | 原有类型错误 |
| 6859721 | Chronic neisserial infection | S | D | 原有类型错误 |
| 6859721 | cutaneous vasculitis | S | D | 新增回归 |
| 10484772 | abnormal retinal vascular development | D | O | 原有漏标 |
| 10484772 | deficiency of norrin | D | O | 原有漏标 |
| 10577908 | deficient activity of fatty aldehyde dehydrogenase | S | O | 原有漏标 |
| 1303173 | deficiency in G6PD | S | O | 原有漏标 |
| 10484772 | unilateral retinal telangiectasis [30,63) | S | retinal telangiectasis，S [41,63) | 原有跨度错误 |
| 10484772 | intraretinal and subretinal lipid accumulation | C | O | 原有漏标 |

“deficiency of hepatic phenylalanine hydroxylase”与“PAH deficiencies”是同文档中不同的 gold 实体。前者恢复，并不意味着后者的类型错误也已解决。

## 8. P0 完成情况与 P1 的输入

P0 已完成：核查 R4 前后标注、追踪相关案例历史、列出所有修复和新增回归，并整理混淆矩阵及整体/类别指标。

下一步消融可以以这里的 **R4 后指南和固定文档**为明确起点，保留确切修改文本，分别观察：

- 目标：FALDH 和 deficiency in G6PD 是否恢复；PAH deficiency 是否保持正确。
- 相关未解决案例：norrin、abnormal retinal vascular development。
- 回归控制：cutaneous vasculitis，以及当前正确的 spasticity、Tay-Sachs disease、TSD。
- 全体文档：TP 增减、FP/FN 与错误矩阵，而不只看目标案例或最终 F1。

是否修改显式负例，应与作用域消融分开记录。这里只有 P1 的输入依据，没有运行消融或承诺其效果。

## 核查记录

使用当前 [循环评分及分簇实现](../src/llm_guideline_moderation/iterative.py)重建保存结果；离线分析脚本与中间数据保存在 todo-temp/round4_p0/，本报告已包含关键计数和全部变化。

输入 snapshot SHA-256：

- Round 3：70fd43ec8e11a135dac97ce377a5bbbb0704b19c7ff1020ec5a5dae0ab3a7f67
- Round 4：e6be9f17042a10725f0b5629ab6206d49672bbf2f905fe78f39db6ebf8c4e17f

核查所用的开发 gold 未修改。模型/规则因果关系、独立重复稳定性及 validation 效果均不在本次离线 P0 的已验证范围内。
