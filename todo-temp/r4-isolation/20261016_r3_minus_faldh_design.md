# 实验设计：删去点名排除后，R3 指南能否修复 FALDH（未运行）

2026-10-16。来源：10/16 meeting 教授反馈第 1 条，"Test whether guidelines of round3 can also fix the missing FALDH is the named exceptions are removed."

## 1. 要回答的问题

10/14 的删除检验显示：R4 指南删去三处点名 FALDH 的文字后，FALDH 3/3 以正确跨度标为 SpecificDisease（`units_c3minus/`）。但 R4 同时新增了一条针对"缺乏/活性降低 + 具体分子"的 principle，所以还不知道起作用的是"删掉排除"本身，还是"删掉排除 + R4 新 principle"。

本实验用 R3 指南做同样的删除。R3 没有 R4 的那条 principle，只有 R3 自己的 DiseaseClass principle，以及第 12 行的一般性 exception rule（"a molecular/substance entity or its level/activity"）。

## 2. 条件（一次只改一个变量）

| 条件 | 指南文本 | 次数 | 说明 |
| --- | --- | --- | --- |
| R3 原样 | `iteration_04/snapshot.json` 的 `guidelines_before`，SHA-256 43f14079… | 3 | 对照。10/14 同条件 3 次全为 O，这次在同一批次里重跑，防止日期不同带来的差异 |
| R3 去掉点名排除 | 同上，删去第 41 至 45 行和第 241 行，其余逐字节不变 | 5 | 主条件 |

删去的原文：

- 第 41 行：`> Deficient activity of fatty aldehyde dehydrogenase`
- 第 42、45 行：空行
- 第 43 行：`- **Do not annotate**`
- 第 44 行：`because it refers to enzyme activity rather than a disease/pathological-state mention.`
- 第 241 行：`- In “deficient activity of fatty aldehyde dehydrogenase,” the phrase is **not** annotated because it refers to enzyme activity rather than a disease/pathological-state mention.`

保留不动：第 12 行的一般性 exception rule、第 172 行 Example 4 的 "functional activity" 说明。脚本要断言：删除前每行内容与上表一致；删除后全文不含 "fatty aldehyde" 和 "FALDH"；行数正好少 6 行。

## 3. 固定项

与 E1 和 10/14 隔离对照完全相同（逐项核对见 `todo-temp/r4-nontarget/20261016_replay_identity_report.md`）：

- 文档 10577908（gold 14 个，FALDH 为 SpecificDisease [245,295)）。
- Azure 部署 `5_4`，reasoning high，max_output_tokens 64000，走 Responses API 后台模式。
- `annotate_with_guidelines` 模板，instructions 为空，输出配置含 rationale 和 guideline section。
- 标注时不给 gold，gold 只用于事后评分。
- 执行顺序按重复次数交替：对照 1、主条件 1、对照 2、主条件 2 …，主条件第 4、5 次排在最后。

## 4. 评分与事先约定的判读

每次运行对 FALDH 记一个状态：

- **修复**：跨度 [245,295) 且标签为 SpecificDisease。
- **类型错**：跨度正确，标签不是 SpecificDisease。
- **边界错**：有重叠的预测，但跨度不同。
- **未标**：没有重叠的预测。

另记整篇 TP/FP/FN，看删除是否影响其余 13 个实体。

| 主条件结果 | 判读 |
| --- | --- |
| 修复 ≥ 4/5 | R3 指南删掉点名排除就能修复 FALDH，R4 的新 principle 对 FALDH 不是必需的。也就是说，R3 已经具备修复条件，阻挡它的只有点名排除 |
| 类型错 ≥ 3/5 | R3 能找到 FALDH，但给不出 SpecificDisease。R4 的新 principle 提供的是类型 |
| 有标注的次数 ≤ 1/5 | 即使删掉点名排除，R3 也修复不了。需要 R4 新增的内容。触发第 5 节的追加条件 |
| 其他 | 结果不稳定，只报告分布，不下结论 |

对照组如果不是全为 O，说明今天的模型行为和 10/14 不同，先报告这一点，再解读主条件。

## 5. 追加条件（只在主条件有标注 ≤ 1/5 时运行）

在主条件的基础上，再删去第 12 行里的 "a molecular/substance entity or its level/activity"，5 次。它检验的是：R3 剩下的一般性 exception rule 是不是第二道阻挡。

## 6. 规模与用量

- 主实验 8 次调用，追加条件 5 次。
- 参考用量：10/14 用 R3 指南标注这篇文档的 3 次，每次输入 4,431 token，输出 29,550 至 33,993 token。按此推算，主实验约输入 3.5 万、输出 25.5 万 token，追加条件约输入 2.2 万、输出 16 万 token。这是按已测用量推算的估计，不是测量结果。

## 7. 局限

- 只有一篇文档、一个模型。
- 5 次重复只能分辨大的差别。比如 0/5 时，修复概率的单侧 95% 上限约为 45%。
- 删除的是 R3 改写这一步写出的文字。它回答的是"这份指南能不能修复"，不回答"循环会不会自己写出不带排除的指南"。

## 核查记录

- 删除位置：用 `iteration_04/snapshot.json` 的 `guidelines_before` 按换行切分后逐行读出，第 41 至 46 行、第 240 至 242 行内容与上文一致；全文共 244 行，"fatty aldehyde" 出现 2 次，"FALDH" 出现 0 次。
- 参考用量：`todo-temp/r4-isolation/units/c1_R3__10577908__r{1,2,3}.json` 的 `usage`。
- 10/14 先例：`todo-temp/r4-isolation/units_c3minus/` 3 个单元，FALDH 均为 SpecificDisease [245,295)。
- 本文件只是设计，没有调用 API。
