# Round 4 规则链：目标漏标为什么没有被修复

日期：2026-10-14。

**核查对象**：`outputs/ncbi_disease/20260802_gpt54-high_moderation`（GPT-5.4 high，dev10，seed 42，n_examples 5）。另取 top-4 dev10 和 dev30 两个 run 做来源对照。

**做法**：全部依据保存的 snapshot 离线追踪，没有调用模型。对应计划为 [RP](../../docs/RP/20261014_r4_failure_attribution_plan.md) 的步骤 1。

## 结论

**1. 三个 R4 目标案例分属三种情况。**

| 案例 | 结果 | 初步归类 | 关键证据 |
| --- | --- | --- | --- |
| FALDH | 未修复 | **规则冲突，产生于改写指南这一站** | 新规则（第 12 至 13 行）放行；第 54 至 57、167、263 行三处点名"不标注"，其中第 167 行是 R4 新增 |
| G6PD | 未修复 | **修复条件不足（暂定）** | 指南中没有任何点名它的文字；新原则的适用条件和 exception rule 都能套到这个句子上，规则没有给出确定方向 |
| PAH | 已修复 | **撤销 R3 的副作用** | R3 的 exception rule 新增"分子/物质或其水平"排除（R3 第 12 行），PAH 在 R3 丢失；R4 加上"缺乏类情况除外"（R4 第 14 行），PAH 恢复 |

**2. 与 gold 相反的点名文字，来源都能追到"不许破坏的示例"区块（verified examples）。**

在三个 run 中，只有所在文档被放进该区块的案例，才被写成点名排除。文档在开发集中却从未被展示的案例，一次也没进过指南。新原则本身从未点名任何一个案例。

**3. 去掉点名排除，并不足以修复漏标。**

dev30 中 FALDH 是两轮的目标错误，它的文档从未被展示，指南也从未点名 FALDH，但它依然漏标。不过 dev30 指南里仍有一般性的 exception rule，所以不能据此认定 exception rule 与漏标无关。

**由此分出两层问题**：

- 冲突文字从哪里来：现有记录可以支持。
- 漏标为什么持续：要靠隔离对照回答。

## 1. 每一站实际看到什么

| 站 | 输入 | 是否看到目标案例的 gold |
| --- | --- | --- |
| ① 错误解释 | 目标错误的片段（带 gold 标签），加 5 篇对照文档（全文和部分正确标注） | 看到 |
| ② 写原则 | 错误解释的结果，加目标错误的片段（带 gold 标签） | 看到 |
| ③ 改写指南 | 当前指南、新原则，加"不许破坏的示例" | **看不到**。它没有收到任何错误例，也没有收到任何 gold |
| ④ 重新标注 | 新指南和文档 | 看不到（按设计） |

"不许破坏的示例"的构造见 `src/llm_guideline_moderation/iterative.py:383-409`，规则如下：

- 按样本顺序，取前 5 篇至少有 1 个正确标注的文档。
- 展示**全文**，每篇最多列出 5 条正确标注。
- 漏标和误标都不做标记。

在 dev10 top-1 run 的 4 轮里，这 5 篇固定是 10196379、10484772、10545613、10577908、10724160。所以 FALDH 的文档（10577908）和 norrin 的文档（10484772）每轮都被展示；G6PD 的文档（1303173）和 PAH 的文档（1671881）从未被展示。

由于每篇最多只列 5 条，"某个短语不在列表里"本身不能说明它被当成了负例。例如在 R4 的改写提示中，10577908 列出的 5 条不含 ichthyosis 和 spasticity，而这两个在 R3 后都预测正确。

## 2. 逐案例规则链

### 2.1 FALDH：deficient activity of fatty aldehyde dehydrogenase

**原文**：Sjogren-Larsson syndrome ( SLS ) is an autosomal recessive disorder characterized by ichthyosis , mental retardation , spasticity , and **deficient activity of fatty aldehyde dehydrogenase** ( FALDH ) .

**gold annotation**：SpecificDisease [245,295)。R0 至 R4 的预测一直是 O。

| 站 | 记录 | 是否覆盖或保留修复 |
| --- | --- | --- |
| ① 错误解释 | 作为 Example 1。解释指出这类短语"看起来像机制性异常而不是疾病名"，并建议在 "characterized by" 等定义句中标为 SpecificDisease | 覆盖 |
| ② 写原则 | 条件：缺乏类名词加具体分子，并处在定义、因果、特征描述语境，就标为 SpecificDisease。exception rule：仅指孤立的生化发现、机制描述或实验室异常时不适用 | 条件覆盖。exception rule 的措辞与 R3 指南排除 FALDH 的理由（"refers to enzyme activity"）几乎相同 |
| ③ 改写指南 | 输入里有两处 R3 写下的 FALDH 排除（R3 第 41、241 行）。FALDH 所在文档以全文出现在"不许破坏的示例"中，未标注。没有任何 gold 信息 | **失败点**。新规则写入第 12 至 13 行；两处旧排除保留并改写（第 54 至 57、263 行）；另外**新增**第 167 行，把 FALDH 作为 exception rule 的例子 |
| ④ 重新标注 | O | 未修复 |

**FALDH 排除的来历**：它是 R3 写进来的，而 R3 的目标并不是 FALDH。R3 针对的是 D→O 漏标，其中 spasticity 与 FALDH 同在一句。R3 的新原则带有"分子/物质或其水平不适用"的 exception rule，改写这一站随即把同句中未标注的 FALDH 写成了"不标注"示例（R3 第 41、241 行）。

**归类**：规则冲突，产生于改写指南这一站。是否是 FALDH 漏标的唯一障碍，要看隔离对照（第 5 节）。

### 2.2 G6PD：deficiency in G6PD

**原文**：We infer that the coexistence of the two mutations is responsible for enzyme **deficiency in G6PD** A- because they act synergistically in causing instability of the enzyme .

**gold annotation**：SpecificDisease [1559,1577)。gold 跨度不含 "enzyme" 和 "A-"。R0 至 R4 一直是 O，而且附近没有任何重叠预测。同一文档中另外三处 G6PD 提及，在 R4 后都标对了：Modifier "G6PD deficient"，SpecificDisease "glucose 6-phosphate dehydrogenase ( G6PD ) deficiency"，SpecificDisease "G6PD deficiency"。

| 站 | 记录 | 是否覆盖或保留修复 |
| --- | --- | --- |
| ① 错误解释 | 作为 Example 2，建议包含 "responsible for" 语境 | 覆盖 |
| ② 写原则 | 条件中有 "responsibility for a clinical condition"。但这句话本身是在解释突变如何导致酶不稳定，exception rule 中的"机制描述、孤立生化发现"同样能套上 | 两边都能套，方向不确定 |
| ③ 改写指南 | 文档从未被展示，指南中没有任何 G6PD 文字 | 没有点名冲突 |
| ④ 重新标注 | O | 未修复 |

**归类（暂定）**：修复条件不足。新原则对这个句子没有给出确定方向，它也不是被点名条款禁止的。

**风险**：即使模型开始标注，也可能标成 "enzyme deficiency in G6PD A-"，按精确匹配仍算错。隔离对照需要单独记录重叠跨度。

### 2.3 PAH：deficiency of hepatic phenylalanine hydroxylase

**原文**：Phenylketonuria is an autosomal recessive disease caused by a **deficiency of hepatic phenylalanine hydroxylase** ( PAH ) .

**gold annotation**：SpecificDisease [138,185)。预测序列为 R0 S、R1 S、R2 S、R3 O、R4 S。

| 轮 | 记录 |
| --- | --- |
| R3（丢失） | R3 原则的 exception rule 写入 R3 第 12 行："Do not apply ... a molecular/substance entity or its level/activity ... Such phrases are not disease mentions." 酶缺乏可以被读成"分子的水平/活性"。R3 的目标是 D→O 漏标，PAH 是附带损伤 |
| R4（恢复） | 新原则作为 Example 3 覆盖了它（"caused by"）。R4 第 14 行在原排除前加上 "Outside the deficit/absence/reduced-function case described above"，第 101 行要求保留分子补语。文档从未被展示，指南中从未点名 PAH |

**归类**：R4 唯一的"修复"，实质是撤销 R3 exception rule 的副作用，靠的是一般规则，而不是点名示例。

**FALDH 与 PAH 的对照**：两者都是"缺乏/活性降低 + 酶"，都在定义句里，都被同一条新原则覆盖。差别在于：

- FALDH 的文档被展示，指南中有三处点名排除；PAH 没有。
- PAH 在 R0 至 R2 本来就能标对，FALDH 从未标对过。

因此这个对照提示了点名排除的作用，但混有"模型原本倾向"的差别，不能当作因果证据。

### 2.4 norrin 与 abnormal retinal vascular development（来源追踪）

这两个都是 10484772 中的 DiseaseClass 漏标，都是 R3 的目标，R0 至 R4 一直是 O。该文档 4 轮都在"不许破坏的示例"中。

- **norrin**：R1 至 R3 都没有被写进指南。R4 新增第 49 至 52 行的点名排除（"This results in a deficiency of norrin ... Do not annotate"）。
- **retinal vascular development**：R1 把含有它的 Coats 句子写成正例示例（R1 第 26 行），但只标注了句中的 "retinal telangiectasis"。R3 又新增第 147 行，把 "retinal vascular development" 列为"机制过程，不标注"。

**案例重合核对**：R4 后仍漏标的 2 个 S→O（FALDH、G6PD），与此前 3 个"gold 相反排除"案例（norrin、FALDH、retinal vascular development）只在 FALDH 处重合。所以需要解释的未修复案例共 4 个，加上已修复的 PAH，共 5 个。

## 3. 跨 run 来源检验

用同一追踪脚本检查 top-4 dev10 和 dev30 两个 run。

| run | 轮 | 案例 | 文档被展示 | 指南新增点名文字 | 预测 |
| --- | --- | --- | --- | --- | --- |
| dev10 top-1 | R3 | FALDH | 是 | 是（第 41、241 行） | O→O |
| dev10 top-1 | R4 | FALDH | 是 | 是（新增第 167 行） | O→O |
| dev10 top-1 | R1 至 R3 | norrin | 是 | 否 | O |
| dev10 top-1 | R4 | norrin | 是 | 是（第 49 行） | O→O |
| dev10 top-1 | R1 至 R4 | G6PD、PAH | 否 | 否 | 见 2.2、2.3 |
| top-4 dev10 | 第 1 轮 | FALDH | 是 | 是（第 224、225 行） | O→O |
| top-4 dev10 | 第 1 轮 | retinal vascular development | 是 | 是（第 27、32、199、201 行） | O→O |
| top-4 dev10 | 第 1 轮 | G6PD | 是（列出 3 条标注） | 否 | O→O |
| top-4 dev10 | 第 1、2 轮 | norrin | 是 | 否 | O |
| dev30 | 第 2、3 轮 | FALDH（目标错误） | **否** | **否** | O→O |
| dev30 | 第 2 轮 | norrin | 是 | 是（第 16、185 行） | O→O |
| dev30 | 第 1 至 3 轮 | G6PD | 否 | 否 | O |

**读法**：在这些观察中，文档被展示是写入点名文字的必要条件，但不是充分条件。这是 3 个 run、5 个案例的观察性结果，不是对照实验。

这与已有证据一致：删除 verified-example 区块的 noTP 运行，已完成的三次（run2、run4、run5）吸收数均为 0/37（见 [LOG.md](../../LOG.md)）。

dev30 中 FALDH 始终未被点名，却仍然漏标。不过 dev30 指南第 16 行有一条一般性 exception rule（"Do not apply this rule when the phrase refers only to the biological entity, ... protein level/status, or causal mechanism ..."），所以这个观察只能说明"点名排除不是必要条件"，不能说明 exception rule 无关。

## 4. 区分三类表述

**已观察到的现象**：

- 第 1 节和第 2 节中各站的输入与输出。
- FALDH、norrin、retinal vascular development 的点名文字，只出现在文档被展示的 run 和轮次中。
- R4 改写这一站在 FALDH 上新增了第三处排除。
- PAH 的丢失与恢复，分别与 R3 第 12 行、R4 第 14 行的改动同时发生。

**有记录支持的解释**：

- 改写指南这一站只能从当前指南、新原则和"不许破坏的示例"三处取得具体字符串。新原则从未点名这些案例；FALDH 排除最初出现时（R3），当前指南里也没有它。所以 R3 的 FALDH 排除文字，来源只能是"不许破坏的示例"。
- 这一站看不到任何 gold，所以无法得知这些短语在开发 gold 中是实体。

**尚未验证的假设**：

- **H1**：改写这一站把示例文档中未列出的短语当作 exception rule 的例子，是因为提示要求"不得使这些示例失效"，而它看不到这些短语的 gold。提示内容与此一致，但没有证据证明这就是模型的理由。
- **H2**：FALDH 持续漏标的主因，是标注这一站对这类定义句的上游判断，与点名排除无关。dev30 只提供部分支持，因为一般性 exception rule 仍在。
- **H3**：G6PD 不被标注，是因为句子贴合 exception rule 的"机制描述/生化发现"措辞。

## 5. 对隔离对照的影响

按 RP 步骤 2 的三种条件，预期的读法：

| 案例 | ② 原则单独 | ③ R4 完整指南 | 支持的解释 |
| --- | --- | --- | --- |
| FALDH | 标出 | 未标出 | 规则冲突，整合时产生（与 H1 一致） |
| FALDH | 未标出 | 未标出 | 原则本身不足以改变判断（与 H2 一致） |
| G6PD | 标出 | 未标出 | 整合问题 |
| G6PD | 未标出 | 未标出 | 修复条件不足（与 H3 一致） |
| PAH | | ① 为 O、③ 为 S | 支持 R3 exception rule 造成回归 |

**建议**：

1. **增加条件 ②b**：标签定义加 R4 原则，但去掉其 "DO NOT apply" 从句。这能直接回答导师的保留问题"不能认定 exception rule 与问题无关"。**已采纳（2026-10-14），写入 RP 步骤 2**，新增的 9 次调用需补充报备。
2. **条件 ② 的"标签定义"**：取原始指南（`inputs/initial_guidelines.txt`）第 6 至 8、20、28 行四个类别的定义句，不含示例。**已写入 RP 步骤 2**。保存的 `entity_schema.json` 只有标签名，不能使用。
3. **评分**：除精确匹配外，单独记录与 gold 重叠的预测跨度和标签，避免 G6PD 这类跨度差异被记成 O。

## 6. 非目标变化（简述）

Tay-Sachs disease、TSD（8326491）和 cutaneous vasculitis（6859721）的文档从未进入"不许破坏的示例"，指南里也没有点名它们的条款。cutaneous vasculitis 在 R0 至 R4 的标签序列为 D、S、D、S、D（见 P0 报告），稳定性未知。

现有记录无法把这些变化归因到具体条款，需要 RP 中的可选扩展（同一指南重复标注）判断它们是否只是波动。

## 核查记录

**命令**：

```
python todo-temp/r4-rule-chain/trace_cases.py --run-dir outputs/ncbi_disease/20260802_gpt54-high_moderation --out todo-temp/r4-rule-chain/trace.json
python todo-temp/r4-rule-chain/trace_cases.py --run-dir outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10 --out todo-temp/r4-rule-chain/trace_20260901_gpt54-high_topk4_dev10.json
python todo-temp/r4-rule-chain/trace_cases.py --run-dir outputs/ncbi_disease/20260812_gpt54-high_moderation-withTP_dev30 --out todo-temp/r4-rule-chain/trace_20260812_gpt54-high_moderation-withTP_dev30.json
diff outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_02/guidelines_after.txt .../iteration_03/guidelines_after.txt
diff .../iteration_03/guidelines_after.txt .../iteration_04/guidelines_after.txt
```

**产物**：

- `todo-temp/r4-rule-chain/trace_cases.py`，SHA-256 f38a6276c2bf95ac784e2cbbdc26580216a4a6f8cdf6155218c46ff63525711d
- `trace.json`
- `trace_20260901_gpt54-high_topk4_dev10.json`
- `trace_20260812_gpt54-high_moderation-withTP_dev30.json`

**输入 snapshot SHA-256**：

- dev10 top-1：
  - iteration_01：ca8be7444e34704f513db8379b1b88f0f8be585fd259647194dc736645d7767c
  - iteration_02：764b5446d29d56bded193ecca68578f8831359832bc55c4dad844fcc5f8a3e86
  - iteration_03：70fd43ec8e11a135dac97ce377a5bbbb0704b19c7ff1020ec5a5dae0ab3a7f67（与 P0 报告一致）
  - iteration_04：e6be9f17042a10725f0b5629ab6206d49672bbf2f905fe78f39db6ebf8c4e17f（与 P0 报告一致）
- top-4 dev10：
  - iteration_01：b8229b66edd3014d40f409e5b708ba6efc629e3c673a07571b0315fbf1f50fe4
  - iteration_02：76ae12bcfc7b3bfdf7017d9eea9ebb7d8f3624fe084501fd754a2cb285c27fc6
- dev30：
  - iteration_01：e6c1cbf5e26c64672f69caf8847c6407d9d3d35a8b38e984412214f2d04da08a
  - iteration_02：eb7325cd32194c0a464aa19ae2766185677fa2a62fd7d8f405894fd88a46800a
  - iteration_03：3e6876b8342cabc5fe202fda4a8d28c6e27dcce0f219dc0fb2b6687a27262957

**另需说明**：

- 追踪脚本第一次运行时，正则的 DOTALL 使示例区块只解析出第一篇文档；修正后重跑，本文数字全部来自修正后的输出。
- [P4 扫描](../p4/gold_conflicts_multi.json) 对 dev10 终版指南报告的冲突为空，与第 2.1、2.4 节确认的 FALDH、norrin 点名排除不符，该扫描器存在漏检，本文未采用它的计数。
- 没有调用模型，没有修改 `outputs/` 下的任何文件。
