# R3 指南删去点名排除后，能否修复 FALDH（结果）

2026-10-17。来源：10/16 meeting 教授反馈第 1 条，"Test whether guidelines of round3 can also fix the missing FALDH is the named exceptions are removed." 设计见 `20261016_r3_minus_faldh_design.md`（已于 10/20 删除，原文见提交 d86ea17），设置与事先约定的判读在运行前未改动。

## 结论

- **不能。** R3 指南删去点名 FALDH 的两处文字后，5 次都没有标注 FALDH（全为 O）。同一批次里 R3 原样的对照 3 次也全为 O，与 10/14 的结果一致。
- **按事先约定的判读**（有标注 ≤ 1/5）：只删点名排除，R3 修复不了 FALDH；10/14 里 R4 删去点名排除后能修复（3/3），靠的是 R4 新增的内容。这也触发了设计第 5 节的追加条件。
- **删除没有带来其他变化。** 8 次运行中，其余 13 个 gold 每次都标对，没有 FP。
- **R3 和 R4 在这一点上的文字差别**（推测阻挡来源，尚未检验）：
  - R3 第 12 行的一般性 exception rule 写的是 "a molecular/substance entity or its level/activity ... are **not** disease mentions"，没有例外。"deficient activity of fatty aldehyde dehydrogenase" 正好可以读成"一个分子的活性"。
  - R4 第 12 行新增了正向规则："deficit/absence/reduced-function + 具体分子"（含 "deficient activity"）**not automatically excluded**；第 14 行同一条 exception rule 前加了 "Outside the deficit/absence/reduced-function case described above"。
  - 所以 R3 里很可能还有第二道阻挡，就是第 12 行这条 exception rule。追加条件（删去其中 "a molecular/substance entity or its level/activity"）正是检验这一点。

## 1. 逐次结果

文档 10577908，14 个 gold；FALDH 的 gold 为 SpecificDisease [245,295)，原文 "deficient activity of fatty aldehyde dehydrogenase"。

| 次序 | 条件 | FALDH | TP/FP/FN | 输入 token | 输出 token | 完成时间 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 对照 1（R3 原样） | O | 13/0/1 | 4,431 | 29,220 | 07:13:24 |
| 2 | 主条件 1（R3 删去点名排除） | O | 13/0/1 | 4,357 | 19,554 | 07:46:20 |
| 3 | 对照 2 | O | 13/0/1 | 4,431 | 28,566 | 07:48:48 |
| 4 | 主条件 2 | O | 13/0/1 | 4,357 | 22,083 | 07:50:45 |
| 5 | 对照 3 | O | 13/0/1 | 4,431 | 38,543 | 07:54:01 |
| 6 | 主条件 3 | O | 13/0/1 | 4,357 | 23,556 | 07:55:56 |
| 7 | 主条件 4 | O | 13/0/1 | 4,357 | 42,485 | 07:59:20 |
| 8 | 主条件 5 | O | 13/0/1 | 4,357 | 31,338 | 08:02:07 |

唯一的 FN 每次都是 FALDH 本身。

## 2. 和 10/14 的对照放在一起

| 指南 | 点名排除 | FALDH 修复 | 运行日期 |
| --- | --- | --- | --- |
| R3 原样 | 有 | 0/3、0/3 | 10/14、10/17 |
| R3 删去点名排除 | 无 | **0/5** | 10/17 |
| R4 原样 | 有 | 0/3 | 10/14 |
| R4 删去点名排除 | 无 | 3/3 | 10/14 |

- R3 删除后 0/5 与 R4 删除后 3/3 的差别，Fisher 精确检验单侧 p = 1/56 ≈ 0.018。两组不在同一天运行（10/17 和 10/14），所以这只是辅助数字；不过两天的 R3 原样对照结果相同（都是 0/3）。
- 0/5 时，R3 删除后的修复概率单侧 95% 上限约为 45%。也就是说，不能排除 R3 删除后偶尔能修复，但修复率明显达不到 R4 删除后的水平。

## 3. 局限

- 没被标注的片段没有 rationale，所以看不到模型具体是按哪条规则不标 FALDH 的。"第二道阻挡是第 12 行"只是从文字差别得出的推测。
- 只有一篇文档、一个模型。
- 删除的是 R3 改写这一步写出的文字。它回答的是"这份指南能不能修复"，不回答"循环会不会自己写出不带排除的指南"。

## 4. 运行过程

- **10/16 第一次尝试失败**：20:37 起提交的 12 个后台任务全部停在 queued，从未开始执行，被脚本取消；连续 3 个单元失败后停止。用量记录为空。21:28 的一次极小测试请求同样停在 queued。记录归档在 `attempt1_20261016_queued/` 和 `probe_queue_20261016T213201.json`。
- **10/17 06:23 极小测试请求正常**：9.5 秒开始执行，22.6 秒完成，输入 13、输出 29 token（`probe_queue_20261017T062345.json`）。随后重跑主实验。
- **10/17 重跑**：第 1 次调用用了约 50 分钟，第 2 次约 33 分钟，之后每次 2 至 3.5 分钟，8 次全部成功。
- 响应里的 `model` 字段返回的是部署名 `eastus2-gpt-5.4`，不是模型版本。

## 5. 用量与费用

- 8 次合计：输入 35,078，输出 235,345 token（实测）。
- 按 East US 2 的两种部署价格换算：Global Standard 约 $3.62（约 572 日元），Data Zone Standard 约 $3.98（约 629 日元）。汇率 158.087（10/16）。部署类型未知，所以给两个数。
- 10/16 失败的 13 个任务没有用量记录；10/17 的测试请求为 42 token。

## 6. 下一步：追加条件（10/17 决定不运行）

10/17 决定不运行。它只能区分 R4 里起作用的是第 12 行的正向规则还是第 14 行收窄后的 exception rule，两处都出自同一条 R4 principle，不改变"修复靠 R4 新增内容"的结论。条件文本保留，以后需要时可直接运行。以下是原计划。

按设计第 5 节：在主条件的基础上，再删去第 12 行的 "a molecular/substance entity or its level/activity, "，其余不变，标 5 次。条件文本已经生成并通过断言（`conditions/c4b_minus_level.txt`，SHA-256 前 12 位 90d95e72e161）。

- 判读可以沿用主实验的标准：修复 ≥ 4/5 说明第 12 行这条 exception rule 就是第二道阻挡；有标注 ≤ 1/5 说明还需要 R4 那条正向规则本身。
- 用量按今天主条件的实测推算：5 次约 338 至 372 日元，按今天的最大值推算最多约 512 至 564 日元。加上本批的 572 至 629 日元，合计约 910 至 1,190 日元，可能超过 1000 日元，所以运行前要先给管理员说一声。
- 运行命令需要显式提高预算：`python nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py run --conditions c4b_minus_level --budget-jpy 0`。

## 核查记录

**命令**：

```
python -u nodes/2026-10-16_seminar/r4-attribution/isolation/probe_queue.py                          # 10/16 21:28（失败）与 10/17 06:23（正常）
python -u nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py run --budget-jpy 0       # 10/17 06:23:51 至 08:02:07，退出码 0
python nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py score
```

**文件**（SHA-256 前 12 位）：

| 文件 | 哈希 |
| --- | --- |
| `run_r3_minus.py` | 6f773476cbe4 |
| `manifest_r3minus.json` | 9f53aca3906d |
| `scores_r3minus.json` | 35d5efbb19da |
| `run_r3minus.log` | 39584a6ec3f5 |
| `probe_queue.py` | 0bcfaed979c4 |
| `probe_queue_20261016T213201.json` | c7d2bab6be6d |
| `probe_queue_20261017T062345.json` | a9181e7f1ab1 |

**指南文本**（按发送文本计算）：R3 原样 43f140798fc5；R3 删去点名排除 c04305a9a8ee。运行前 dry run 确认今天的 R3 对照提示与 10/14 保存的提示逐字相同（19,827 字符）。

**单元**：`units_r3minus/` 下 8 个文件，状态全部为 ok。

**R4 的文字**：`iteration_04/snapshot.json` 的 `guidelines_after` 第 12、14 行。

**统计**：Fisher 单侧 p = 1/C(8,3) = 0.0179；0/5 的单侧 95% 上限 = 1 − 0.05^(1/5) = 0.451。
