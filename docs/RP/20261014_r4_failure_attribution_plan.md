# 研究计划：10/16 seminar 前定位 Round 4 修复失败的环节

日期：2026-10-14（周三）。seminar：2026-10-16（周五）上午。可用时间：10/14 至 16:30，10/15 全天。

## 目标

回答导师在 10/09 seminar 提出的问题：**Round 4 针对 3 个 S→O 漏标生成了新规则，为什么只修复了 1 个？**

交付"案例、具体条款、预测变化"三者对应的证据，不扩大实验规模。来源：[PROGRESS.md](../../PROGRESS.md) 中的 2026-10-09 seminar Todo（新 P0），以及 Notion 页面"10/9 meeting summ & todo"。

## 对象

**run**：`outputs/ncbi_disease/20260802_gpt54-high_moderation`。设置为 GPT-5.4 high（Azure），dev10，sample seed 42，n_examples 5。

**流水线四站**（每轮依次执行）：

1. 错误解释：`infer_discrepancy_patterns`。
2. 写原则：`generate_moderation_principle`。
3. 改写指南：`refine_guidelines`。这一站同时收到"不许破坏的示例"（verified examples）。
4. 重新标注。

**案例**：

| 案例 | 文档与位置 | gold | 角色 |
| --- | --- | --- | --- |
| deficient activity of fatty aldehyde dehydrogenase（FALDH） | 10577908 [245,295) | SpecificDisease | R4 目标，未修复；R4 指南明确写"不标注" |
| deficiency in G6PD | 1303173 [1559,1577) | SpecificDisease | R4 目标，未修复；指南中没有提到 |
| deficiency of hepatic phenylalanine hydroxylase（PAH） | 1671881 [138,185) | SpecificDisease | R4 目标，已修复；R3 刚造成回归，R4 将其恢复 |
| deficiency of norrin | 10484772 [949,969) | DiseaseClass | R3 目标，未修复；R4 指南明确写"不标注" |
| abnormal retinal vascular development | 10484772 [186,223) | DiseaseClass | R3 目标，未修复 |

前三个是主要对象。后两个是导师要求同时追踪的"gold 相反排除"案例，只做来源追踪。FALDH 同时属于两组，不重复计数。

## 步骤 1：规则链（10/14，离线，不调用模型）

**状态：已完成（2026-10-14）。** 见 [规则链报告](../../todo-temp/r4-rule-chain/20261014_r4_rule_chain_report.md)。

- FALDH：规则冲突，产生于改写指南这一站。
- G6PD：修复条件不足（暂定）。
- PAH：撤销 R3 的副作用。
- 与 gold 相反的点名文字，都出自"不许破坏的示例"区块中被展示的文档。

以下为原计划。

对每个案例逐站整理以下内容：

1. 原文、gold annotation、R3 后的预测。
2. 错误解释怎样描述它。
3. 新原则的条件和 exception rule 是否覆盖它。
4. 改写指南这一站实际收到了什么：案例文本、gold、所在文档是否出现在 verified examples 中，以及以什么形式出现。
5. R3 到 R4 的相关指南 diff。
6. R4 后的预测。

**归类**：

- 修复条件不足：原则没有覆盖这个案例。
- 规则冲突：新规则允许标注，但其他条款或例外仍然禁止。
- 整合失真：原则可用，但写入完整指南时被改写、弱化或覆盖。

读记录无法区分的部分，留给步骤 2。

**产出**：`todo-temp/r4-rule-chain/` 下的报告、追踪脚本和中间数据。报告要分开写三类内容：已观察到的现象、有记录支持的解释、尚未验证的假设。

## 步骤 2：隔离对照（27 次调用的报备已于 10/14 发送；条件 ②b 新增的 9 次需补充报备；批准后执行）

**状态：已完成（2026-10-14，36/36）。** 见[隔离对照报告](../../todo-temp/r4-isolation/20261014_r4_isolation_report.md)。

- FALDH：只给原则时能被标出，用 R4 完整指南时不能，去掉 exception rule 无变化。
- G6PD：四组都没有标对。
- PAH：R3 指南下错，R4 指南下对。

追加对照 ③−（删去 FALDH 的三处点名排除，3 次调用）已于 15:06 至 15:15 完成：FALDH 3/3 精确恢复，整篇 14/0/0。

以下为原计划。

**固定项**：

- 与原 run 相同的模型部署与 reasoning_effort。
- 相同的标注提示模板和输出配置。
- 相同的文档。
- 标注时不给模型看 gold，gold 只用于事后评分。

**条件**（四选一，一次只换指南文本）：

| 条件 | 指南文本 | 回答的问题 |
| --- | --- | --- |
| ① | R3 后指南（`iteration_04/snapshot.json` 的 `guidelines_before`） | 原来的错误能否复现 |
| ② | 标签定义加 R4 新原则全文，不放入完整指南 | 新原则本身能否处理目标案例 |
| ②b | 标签定义加 R4 新原则，但删去其 exception rule | exception rule 有没有拦住 FALDH 和 G6PD |
| ③ | R4 后指南（`iteration_04/guidelines_after.txt`） | 整合后是否保留了修复能力 |

**条件 ② 和 ②b 的文本**（2026-10-14 确定）：

- **标签定义**：原样截取原始指南 `inputs/initial_guidelines.txt` 中四个类别的定义句，不含示例：
  - 第 6 至 8 行：Specific Disease 和 Disease Class。
  - 第 20 行：Composite Mention。
  - 第 28 行：Modifier。

  保存的 `entity_schema.json` 只有四个标签名，没有定义，所以不能用它。
- **② 的原则**：`iteration_04/snapshot.json` 中 `moderation_principle` 的全文。
- **②b 的原则**：同一原文，在 "annotate the whole phrase as **SpecificDisease**" 处结束，删去其后的 "; **DO NOT** apply this rule when the same wording refers only to an isolated biochemical finding, mechanistic description, or laboratory abnormality rather than the disorder itself."。其余文字一字不改。
- ② 与 ②b 只差这一个从句，是单变量对照。

**文档与规模**：10577908、1303173、1671881 三篇。每个组合重复 3 次：4 种条件 × 3 篇 × 3 次，共 36 次单文档调用。

**输入量**：用不联网的替身 provider 渲染了 12 个真实提示（2026-10-14），36 次调用合计 437,955 个字符。按每 token 3 至 4 个字符换算，输入约 11 万至 15 万 token。

- 每次调用的提示长度：①、③ 约 1.9 万至 2.3 万字符；②、②b 约 0.3 万至 0.4 万字符。
- 输出和推理 token 无法事先测，未计入。
- 先前给 27 次调用估的 20 万至 30 万 token，是按每次约 8 千 token 的粗估，偏高。

**评分**：

- 主指标：目标跨度的精确匹配（标签和跨度都与 gold 一致）。
- 另外单独记录与 gold 重叠的预测跨度和标签。例如 G6PD 的 gold 跨度不含 "enzyme" 和 "A-"，模型标成更长的跨度时，不应被记成 O。
- 同时记录三篇文档中其他 gold 实体的变化，检查是否带来回归。

**结果读法**：

| 观察 | 解释 |
| --- | --- |
| ② 有效、③ 无效 | 原则可用，整合后失效。优先查规则冲突与整合，再移除疑似冲突条款来验证 |
| ② 无效、②b 有效 | exception rule 拦住了目标案例 |
| ② 与 ②b 都无效 | 问题不在 exception rule。查错误解释、原则的适用条件，以及模型是否正确执行 |
| ② 与 ②b 都有效、③ 无效 | 拦住目标案例的是完整指南中的其他条款，例如 FALDH 的三处点名排除 |
| 同一条件下 3 次结果不一致 | 报告为不稳定，不当作规则效果 |

PAH 的预期：① 为 O、③ 为 S。若如此，支持"R3 的 exception rule 造成回归，R4 的豁免将其撤销"。

**可选扩展**：用 8326491、6859721 两篇文档在 ① 和 ③ 下各重复 3 次（另加 12 次调用），检查 R4 的非目标变化是否稳定。非目标变化指 Tay-Sachs/TSD 被修复、cutaneous vasculitis 新增回归。这部分需要另行报备，优先级低于 ②b。

## 步骤 3：seminar 之后，低成本模型试跑对比

与这次汇报无关，10/16 之前不做。

- **对比对象**：Claude Haiku 5.5 与 DeepSeek V4.1 Flash。
- **做法**：各用原指南标注 valid100，用 `reproduction/eval_valid.py --require-complete` 评分，与 GPT-5.4 原指南的 0.7792 对照。
- **判定**：差距小于约 0.02 视为打平，选便宜的模型。
- **前置工作**：
  - 为 Haiku 新写一个 provider，使用官方 `anthropic` SDK。
  - 调大 DeepSeek provider 的输出上限（当前默认 8192），因为改写指南这一步要输出整份指南。
  - 由用户本人把密钥写入 `.env`。
- **注意**：换模型后，现有的基准数字和噪声带都要用新模型重测，不与 GPT-5.4 的结果混比。

## 时间线

| 时间 | 事项 |
| --- | --- |
| 10/14 至 16:30 | 步骤 1：规则链 |
| 10/14 获批后，或 10/15 上午 | 步骤 2：隔离对照 |
| 10/15 下午 | 汇报材料：逐例对照表、关键 diff、三类表述的区分 |
| 10/16 上午 | seminar |

## 边界

- 用于改规则的 gold 只能来自 dev，独立评估集的答案不进入 refinement。
- dev10 的 F1 标准差约 0.015。单个案例只有 3 次重复，结论只能写到"在这些重复中观察到"。
- 术语：限制从句统一称 exception rule；错误案例对应的正确答案称 gold annotation，TP 只指此前已预测正确的案例。
- 步骤 2 必须使用原 run 的模型。换模型会同时改变两个因素，结果无法解释 R4。
