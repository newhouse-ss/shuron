# 隔离对照：Round 4 目标案例在四种指南条件下的重标结果

日期：2026-10-14。对应 [RP](../../docs/RP/20261014_r4_failure_attribution_plan.md) 步骤 2，衔接 [规则链报告](../r4-rule-chain/20261014_r4_rule_chain_report.md)。

**实验概况**：

- 共 36 次单文档标注，全部成功。
- 运行时间：13:06:41 启动，第 1 次完成后应用户要求在 13:14:02 暂停，13:19:47 恢复，14:43:33 完成。
- 设置：与原 run `outputs/ncbi_disease/20260802_gpt54-high_moderation` 相同，即 Azure 部署 `5_4`、reasoning high、输出上限 64000、原标注模板、带 rationale 和 guideline section。四组只换指南文本。标注时不提供 gold。

## 结论

**1. FALDH：新原则本身能让模型把它当作疾病标注，放进完整的 R4 指南后失效。拦住它的不是原则自带的 exception rule。**

- 只给原则时（② 和 ②b），3 次都把它当成疾病标注：2 次标成 SpecificDisease（跨度多了 "( FALDH )"），1 次连同前面的症状列表标成一个 CompositeMention。
- 用 R4 完整指南时（③），3 次都是 O。
- 去掉 exception rule 后（②b），结果与 ② 完全相同。

所以障碍在完整指南的其他内容里。追加对照 ③− 已经确认就是三处点名排除：R4 指南只删去这三处、其余不变，FALDH 3 次全部精确标对，该文档 3 次都是 14/0/0（见第 7 节）。

**2. G6PD：四种条件下没有一次标成 SpecificDisease。exception rule 有一定压制作用，但去掉它也没有让模型得到 gold 的读法。**

- 去掉 exception rule 后（②b），模型 3 次都把相邻的 "enzyme deficiency" 标成 DiseaseClass。保留时（②）只有 1 次这样做。
- 跨度和标签都不对。这支持"修复条件不足"：原则描述的"缺乏 + 具体分子"结构，与模型对这句话的切分方式对不上。

**3. PAH：R3 指南下 3 次都错，R4 指南下 3 次都对。**

- R3 指南下 3 次都标成 DiseaseClass。保存的 R3 结果是 O，这次错误类型不同，但同样错。
- 这支持"R3 的 exception rule 造成回归、R4 的豁免把它撤销"的解释，而且 R4 对 PAH 的修复是稳定的。

**4. ③ 组复现了保存的 R4 结果。**

FALDH 为 O、G6PD 为 O、PAH 为 SpecificDisease，三个案例 3 次都一致。所以 R4 的修复失败不是一次偶然。

## 1. 结果总表

**评分口径**：

- **精确**：预测的跨度与标签都和 gold 一致。
- **方向**：预测与 gold 跨度重叠，并且标签和 gold 相同。

"方向"这一标准是**看过第 1 轮结果后才明确的**。RP 只写了"另记重叠跨度"，没有事先定义"有效"。原因是 ② 和 ②b 只有类别定义和一条原则，没有完整指南里"括号中的缩写单独标注"等跨度规则，即使判断方向正确，按精确匹配也会全算错。

| 案例（gold） | 条件 | 精确 | 方向 | 3 次的预测 |
| --- | --- | --- | --- | --- |
| FALDH（SpecificDisease） | ① R3 指南 | 0/3 | 0/3 | O、O、O |
| | ② 原则全文 | 0/3 | 2/3 | S [245,305)、CompositeMention [194,295)、S [245,305) |
| | ②b 去掉 exception rule | 0/3 | 2/3 | S [245,305)、S [245,305)、CompositeMention [194,295) |
| | ③ R4 指南 | 0/3 | 0/3 | O、O、O |
| G6PD（SpecificDisease） | ① R3 指南 | 0/3 | 0/3 | O、DiseaseClass [1552,1580)、O |
| | ② 原则全文 | 0/3 | 0/3 | O、DiseaseClass [1552,1569)、O |
| | ②b 去掉 exception rule | 0/3 | 0/3 | DiseaseClass [1552,1569)，3 次相同 |
| | ③ R4 指南 | 0/3 | 0/3 | O、O、O |
| PAH（SpecificDisease） | ① R3 指南 | 0/3 | 0/3 | DiseaseClass，3 次相同 |
| | ② 原则全文 | 1/3 | 3/3 | S [138,193)、S [138,193)、S（精确） |
| | ②b 去掉 exception rule | 1/3 | 3/3 | S [138,193)、S [138,193)、S（精确） |
| | ③ R4 指南 | 3/3 | 3/3 | S（精确），3 次相同 |

**跨度原文**：

| 跨度 | 原文 |
| --- | --- |
| [245,305) | "deficient activity of fatty aldehyde dehydrogenase ( FALDH )" |
| [194,295) | "ichthyosis , mental retardation , spasticity , and deficient activity of fatty aldehyde dehydrogenase" |
| [1552,1569) | "enzyme deficiency" |
| [1552,1580) | "enzyme deficiency in G6PD A-" |
| [138,193) | "deficiency of hepatic phenylalanine hydroxylase ( PAH )" |

gold 跨度分别为 FALDH [245,295)、G6PD [1559,1577) "deficiency in G6PD"、PAH [138,185)。

## 2. 按 RP 的读法逐条对照

| RP 中的观察 | 实际情况 | 结论 |
| --- | --- | --- |
| ② 有效、③ 无效 | FALDH 符合（按方向计，2/3 对 0/3；若把 CompositeMention 也算作"当作疾病"，是 3/3 对 0/3） | 原则可用，整合后失效 |
| ② 无效、②b 有效 | 三个案例都不符合 | 没有案例被 exception rule 单独拦住 |
| ② 与 ②b 都无效 | G6PD 符合（按方向都是 0/3）。但 ②b 让模型标注相邻短语的次数从 1/3 升到 3/3 | 问题主要不在 exception rule。原则的适用条件没有对上这句话 |
| ② 与 ②b 都有效、③ 无效 | FALDH 符合 | 拦住 FALDH 的是完整指南中的其他条款 |
| PAH：① 为 O 或错、③ 为 S | 符合（① 3 次都标成 DiseaseClass，③ 3 次都精确正确） | 支持 R3 造成回归、R4 撤销 |

**与规则链报告中假设的对应**：

- **FALDH 的"规则冲突，产生于改写指南这一站"**：得到支持。原则本身能改变判断，完整指南却阻止了它。
- **H2**（"FALDH 持续漏标是标注这一站的上游判断，与点名排除无关"）：被削弱。不给完整指南时，模型确实会把 FALDH 当作疾病。
- **H3**（"G6PD 被 exception rule 的措辞拦住"）：部分支持。去掉 exception rule 后，模型更常在这句话里标注，但标的是 "enzyme deficiency" 和 DiseaseClass，不是 gold 的读法。
- **H1**（"改写这一站为什么会写出点名排除"）：这次实验不检验它。

## 3. 非目标实体的变化

与保存的 R3 后预测相比：

- **② 和 ②b，FALDH 那篇**：每次都丢了 2 至 3 个 DiseaseClass（ichthyosis、mental retardation、spasticity）。极简指南里没有"定义语境中的病理状态标为 DiseaseClass"等细则，这是预期中的副作用。
- **② 和 ②b，PAH 那篇**：有 1 至 2 次波动较大（TP/FP/FN 低至 2/4/4），另有几次多标对了 [694,710) 的 SpecificDisease。
- **③，G6PD 那篇**：3 次中有 1 次丢了 Modifier "G6PD deficient"。

因此 ② 和 ②b 只能用来回答"原则能否改变目标案例的判断"，不能当作可用的完整指南。

## 4. 局限

- 每格只有 3 次重复，只覆盖 3 篇开发文档和一个模型，结论只能写到"在这些重复中观察到"。它不代表 validation 表现。
- ③ 与 ② 的差别包含完整指南的全部内容，不只是三处点名排除。这一点已由第 7 节的追加对照 ③− 定位到点名排除。
- "方向"口径是事后明确的。精确匹配的结果已同时列出。
- 暂停时作废的那次调用（13:09 至 13:14）没有保存用量，实际消耗比下面的合计略多。

## 5. 追加对照 ③− 的设计（用户确认后于 15:06 至 15:15 执行，结果见第 7 节）

**条件 ③−**：R4 指南删去点名 FALDH 的三处文字，其余不变，只标 FALDH 那篇，重复 3 次，共 3 次调用。三处文字是：

- 第 54 至 57 行的示例。
- 第 167 行的排除。
- 第 263 行的说明。

读法：

- 若 FALDH 恢复：障碍就是点名排除。这样整条链就闭合了，点名排除来自"不许破坏的示例"区块（规则链报告第 3 节），可以直接支撑导师认可的两个方向：给改写这一站提供 gold，以及写后冲突检查。
- 若仍不恢复：障碍在完整指南的一般性条款中，例如第 13 行的 exception rule 与第 14 行的排除。

## 6. 用量（实测，来自每次调用保存的 usage）

| 项目 | 合计 | 每次平均 |
| --- | --- | --- |
| 调用次数 | 36 | |
| 输入 token | 97,113 | 约 2,698 |
| 输出 token | 959,532 | 约 26,654 |

输出全部是推理 token。不含暂停时作废的那 1 次。

追加对照 ③− 另用 3 次：输入 14,502 token，输出 105,580 token（每次约 3.5 万）。事先按 ③ 组推算的输出是 7 万多 token，实际比推算多约 40%。

## 7. 追加对照 ③− 结果

**条件**：R4 指南删去第 54 至 58 行（FALDH 的"不标注"示例块及其后空行）、第 167 行、第 263 行，其余逐字不变。删后剩 19,216 字符，不再含 "fatty aldehyde" 或 "FALDH"。

**范围**：只标 FALDH 所在的 10577908，重复 3 次。其他设置与前 36 次相同。

| 条件 | FALDH 精确 | 3 次的预测 | 整篇 TP/FP/FN | 相对 R3 后的其他变化 |
| --- | --- | --- | --- | --- |
| ③ R4 指南 | 0/3 | O、O、O | 13/0/1，3 次相同 | 无 |
| ③− 删去三处点名排除 | **3/3** | SpecificDisease [245,295)，3 次相同 | **14/0/0**，3 次相同 | 无 |

**结论**：在 R4 指南中，拦住 FALDH 的就是这三处点名排除。删去后，R4 新规则（第 12 至 14 行，未改动）在完整指南里也能把 FALDH 精确修好，而且同一文档中没有出现其他回归。

**与规则链报告合起来，证据链是**：

1. 改写指南这一站看不到 gold，但能看到"不许破坏的示例"中的文档全文。
2. 它把其中未标注的 FALDH 写成了"不标注"（R3 写下两处，R4 保留并新增一处）。
3. 这三处文字阻止了 R4 新规则对 FALDH 的修复（本节）。

第 1、2 步出自保存记录的观察，第 3 步是这次的单变量实验结果。改写那一站**为什么**会这样写（H1），仍然是假设。

**局限**：只有 1 个案例、1 篇文档、3 次重复。这个结论说明的是"FALDH 在 R4 中为什么没修好"，不能直接推广为"所有点名排除都有害"。norrin 的点名排除没有做对应的删除实验。

## 核查记录

**命令**：

```
python todo-temp/r4-isolation/run_isolation.py run --dry-run
python todo-temp/r4-isolation/run_isolation.py run      # 13:06:41 PID 20088；13:14:02 暂停；13:19:47 恢复 PID 13856
python todo-temp/r4-isolation/run_isolation.py score
```

**产物**：

- `todo-temp/r4-isolation/run_isolation.py`，SHA-256 e8abe64219a9a3f0fcc464395a1e98fafbad44fc4a8d977c73d4d6e767099d27
- `todo-temp/r4-isolation/scores.json`，SHA-256 77327942f8175813da9a16b7bd88716ebe247313e184246ba3f507cf362711eb
- `units/`：36 个单元，每个含标注、原始回复和 usage。
- `scores_interim_rep1.json`：第 1 轮的中间评分。
- `manifest.json`、`conditions/`：四组指南文本。
- `dry_run/`：渲染出的提示。
- `run.log`、`run_resume.log`：运行日志，`run.err`、`run_resume.err` 均为空。

**输入**：iteration_04 snapshot，SHA-256 e6be9f17042a10725f0b5629ab6206d49672bbf2f905fe78f39db6ebf8c4e17f，与 P0 报告一致。

**四组指南文本的 SHA-256**：

| 条件 | 字符数 | SHA-256 |
| --- | --- | --- |
| c1_R3 | 17,102 | 43f140798fc501fddafabf9e41faebc6fe66e8747e8ffcbae32c0b7b8070daab |
| c2_principle | 1,229 | 0de540cc6d3cec29b8bc3cc9a9fa34a047272295f4f1fd051486a295041b02db |
| c2b_no_exception | 1,048 | 40657c3701ac5a0c884b9db981e4902941a359860b10b5f784c26ec2e455285a |
| c3_R4 | 19,940 | 10e93c9dab248eec9efe9ba7ada1e2b8ecca3c17dbbce31fb429410de6868f1a |

**运行前检查**：

- dry-run 渲染的 36 个提示合计 437,955 字符，与计划一致。
- 用保存的 R3、R4 预测伪造结果文件测试评分，PAH 所在文档的 TP/FP/FN 为 4/1/2 和 5/1/1，与 P0 报告一致。

**追加对照 ③−**：

```
python todo-temp/r4-isolation/run_c3_minus.py run --dry-run
python todo-temp/r4-isolation/run_c3_minus.py run      # 15:06:16 PID 20692，15:15:07 完成
python todo-temp/r4-isolation/run_isolation.py score --units-dir todo-temp/r4-isolation/units_c3minus --out todo-temp/r4-isolation/scores_c3minus.json
```

- `run_c3_minus.py`，SHA-256 bf58efca50c24628f360ab76207df9f39bcd37d06ebdaf63c1d1bc8d714d5e9d
- `scores_c3minus.json`，SHA-256 6575c8c10977115a8bba2a5cc23f5d60476cb9d73f10e79ac2157e6fa051c74c
- `conditions/c3_minus_faldh.txt`，SHA-256 93e16e8716fc627cbcfe1a3fd0c46fb20c7d8ae2d6b8265f4a008045818e5251。派生自 c3_R4，后者 SHA-256 为 10e93c9d…，与上表一致。
- `manifest_c3minus.json`：记录删除的行号。
- `units_c3minus/`：3 个单元。
- `run_c3minus.log`：运行日志，`run_c3minus.err` 为空。
- 与 c3_R4 的 diff 只包含计划删除的 7 行。

**未修改**：`outputs/` 下的任何文件。
