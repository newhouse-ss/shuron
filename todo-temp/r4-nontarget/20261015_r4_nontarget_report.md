# R4 非目标变化：Tay-Sachs 的"改对"不能复现

2026-10-15。对象：`outputs/ncbi_disease/20260802_gpt54-high_moderation`（GPT-5.4 high，dev10，seed 42）的 Round 4。

## 结论

- **Tay-Sachs disease、TSD 的 M→S 不是 R4 指南造成的。** 用同一份 R4 指南重标 5 次，两处都是 Modifier（0/5 为 S）；R3 指南下同样 0/5。原 run 中 R4 那一次标成 S，是无法复现的单次翻转。
- **cutaneous vasculitis 的 S→D 也在波动范围内。** 原指南不变、重复 5 次时，该处为 D、S、S、D、D（离线证据，见第 3 节）。
- **因此 R4 的两类非目标变化都不能归因于新 principle。** 10/09 seminar 待办里"为什么针对漏标的规则修复了 2 个 M→S 并新增 1 个 S→D"这一问题，前提不成立：这两处变化都在标注波动之内。
- **R4 被接受依赖这次翻转（反事实算术，非新实验）。** 其他预测不变，只把这两处换成重跑中一致出现的 Modifier，R4 的 dev F1 为 0.8811，低于 R3 的 0.8873，按循环规则 R4 会被回退。
- **E2（机制探针）未执行。** 事先约定的执行条件是"R4 指南下至少 3/5 为 S"，实际 0/5。

## 1. 问题与假设

R4 的目标是 3 个 S→O 漏标。目标以外，8326491 中 "a Tay-Sachs disease ( TSD ) causing mutation" 的两处由 M 改为 S（gold 为 S），6859721 中 "other causes of cutaneous vasculitis" 由 S 改为 D（gold 为 S）。

离线分析（同日）提出的假设：R4 第 12 行首次把 "causation ... context" 与 Specific Disease 连在一起，模型可能把它推广到字面范围之外。支持它的是变化的选择性：同篇 6 处中只有致病语境的 2 处变了。

事先约定的判读（运行前定下）：以全称 [193,210) 为主指标；R3 下 S 不超过 1/5、R4 下 S 至少 3/5 才算 R4 造成；满足后才做 E2（删去第 12 行的 causation 措辞）。

## 2. 实验 E1

- **固定项**：模型、提示模板、输出配置与原 run 相同，标注时不给 gold。两份指南的 SHA-256 与 10/14 隔离对照相同（R3 43f14079…、R4 10e93c9d…）。
- **变量**：只换指南文本，R3 后指南或 R4 后指南。
- **规模**：8326491 × 2 种指南 × 5 次，共 10 次调用，按"R3、R4 交替"的顺序执行。
- **评分**：6 个 gold 跨度逐一记录标签，并保存模型给出的 rationale 和引用条款。

**结果**：

| 指南 | Tay-Sachs disease [193,210) | TSD [213,216) | 其余 4 处（gold M） | 整篇 TP/FP/FN |
| --- | --- | --- | --- | --- |
| R3，5 次 | M ×5 | M ×5 | 全对 | 4/2/2，5 次相同 |
| R4，5 次 | M ×5 | M ×5 | 全对 | 4/2/2，5 次相同 |
| 原 run 保存的 R4 结果 | S | S | 全对 | 6/0/0 |

10 次的 rationale 都引用 Rule 3（Modifier），理由一致：疾病名修饰 "mutation"，即"致病突变"。

**合并既有证据**：这一处在原指南下的 6 次标注（原 run 的 R0，加上 08-20 的固定指南重复 5 次）、R1 至 R3 的 3 次，以及本次 10 次重跑，共 19 次都是 M。唯一的 S 是原 run 的 R4 那一次。只有 5 次时，R4 指南下 S 概率的单侧 95% 上限约为 45%，所以不能排除"低概率地会改对"，但"R4 导致改对"没有得到支持。

## 3. cutaneous vasculitis（离线，未新跑）

- 原 run 逐轮标签：R0 为 D，R1 为 S，R2 为 D，R3 为 S，R4 为 D。
- 原指南不变、重复 5 次（`reproduction/results/size_noise/repeat_01` 至 `05`）：D、S、S、D、D。
- 这批重复的参数没有保存。按提交 2488342 中脚本的默认值推定为原指南（内容与 run 的初始指南只差换行符）、Azure 5_4、high。
- 结构上的原因（读文本得出，未检验）：这一处同时满足 R4 指南第 9 行"etiologic context → Specific Disease"和第 10 至 11 行"generic / non-referential etiologic description → Disease Class"，指南没有规定优先顺序。

## 4. 对 R4 接受决定的含义（反事实算术）

| 版本 | TP | FP | FN | dev F1 |
| --- | --- | --- | --- | --- |
| R3 后（保存） | 63 | 5 | 11 | 0.8873 |
| R4 后（保存） | 65 | 4 | 9 | 0.9091 |
| R4 后，Tay-Sachs/TSD 取重跑中的 M | 63 | 6 | 11 | 0.8811 |

第三行只改动这两处，其他预测保持原样。cutaneous vasculitis 同样在波动，若它在 R4 保持 S，结果又会不同，所以这里只说明"R4 的接受依赖不可复现的翻转"，不给出 R4 的"真实"分数。这与 dev10 的标注噪声（F1 标准差约 0.015）一致：R4 的 +0.0218 中，能复现的修复只有 PAH 一处（隔离对照中 R3 指南 0/3、R4 指南 3/3）。

## 5. 术语（对照原论文核对，建议采用）

- **secondary effect**：本轮目标错误组以外的案例发生的变化，包括改对和改错。出处是 base paper 第 447 至 448 行、第 458 至 477 行。
- **correct change / false change**：单个案例层面的变化方向，见 Figure 4。
- **regression**：本轮之前正确、之后错误的案例，属于案例层面。同作者的另一篇论文把 regression 用在指标层面（F1 下降超过阈值），讲 F1 下降时写 per-label F1 regression。
- **新增的一条轴：能否归因**。原论文没有区分。本次两处变化都属于"观察到但不能归因于规则"的变化，不应称为规则的 secondary effect。

是否写入 OVERVIEW 的术语条，待用户确认。

## 6. 运行记录与保留

- 首次启动在 20:49。第 1 次调用 2 分钟完成，第 2 次在服务端停滞超过 30 分钟，21:24 按用户要求中断。已完成的 1 个单元和日志按要求删除；被中断的那次调用已提交到 Azure，服务端是否计费未知。
- 21:26 重新启动。第 1 次调用用时 42 分钟，之后每次约 2 分钟，22:45 完成，10/10 成功。
- 本次运行未事先报备，按用户安排于 10/16 向管理员补报。

## 核查记录

**命令**：

```
python todo-temp/r4-nontarget/run_nontarget.py run --conditions c1_R3 c3_R4 c3_nocause --dry-run
python todo-temp/r4-nontarget/run_nontarget.py run --conditions c1_R3 c3_R4   # 21:26:58 至 22:45:38
python todo-temp/r4-nontarget/run_nontarget.py score
```

**产物**：

- `run_nontarget.py`，SHA-256 31c92d8c…4388
- `manifest.json`，SHA-256 deec4302…321b。其中 snapshot SHA-256 与 10/14 相同（e6be9f17…）。
- `scores.json`，SHA-256 c87e3909…f441
- `units/`，10 个单元，全部 ok。
- `conditions/`、`dry_run/`：c3_nocause（E2 条件）已生成，未运行。

**用量**：输入 45,470 token，输出 162,220 token（R3 组 21,365 / 86,166，R4 组 24,105 / 76,054）。

**反事实算术**：数据取自 `rounds/iteration_04/snapshot.json` 的 `summary_before` 和 `summary_after`，F1 = 2TP / (2TP + FP + FN)。

**本次没有修改 `outputs/` 下的任何文件。**
