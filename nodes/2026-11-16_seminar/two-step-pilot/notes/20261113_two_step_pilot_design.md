# 两步标注试跑设计：指南不变，把"找全"和"定类型"拆开，真正漏标会不会减少

状态：设计，未运行，未写代码。2026-11-13。来源：`20261113_thesis_claim_research.md` 第 4 节方案 A。

**用词：** 真正漏标指没有任何预测与之重叠的 gold 提及（类型、边界不论）。Track 2 输出指交给专家修正的全部预测；Track 1 输出指直接使用的标注。

## 1. 要回答的问题

原指南一字不改，只把标注拆成"先找全、再定类型"两次调用，真正漏标是否比现在的单次标注少；如果少，是拆开这个结构的作用，还是"宁可多标"这句说明本身的作用。

## 2. 三个组，相邻两组只差一处

| 组 | 做法 | Track 2 输出 | Track 1 输出 |
| --- | --- | --- | --- |
| S：单次标注（现状） | 复现用的标注调用，原样不改 | 全部标注 | 同左 |
| S+：单次标注加"宁可多标"说明 | 同一个调用，instructions 加附录第一段；指南认为不该标的也输出，排除标记填 yes 并引用条文 | 全部标注 | 排除标记为 no 的标注 |
| T：两步标注 | 第一次调用用和 S+ 相同的范围说明找候选，不定类型（附录第二段）；第二次调用给每个候选定类型或判 NONE 并引用条文，不改边界，不新增候选（附录第三段） | 第一步的全部候选 | 第二步定了类型的候选 |

- S 到 S+ 只改说明，S+ 到 T 只改结构（一次调用变两次，找的范围相同）。
- 例：原指南第 75、76 行规定 "abnormalities" 这类泛称不标，gold 却把 "eye abnormalities" 标为 DiseaseClass，30 次运行都没找到。S 不输出它，是真正漏标；S+ 输出并标 `excluded`，它进入专家的审核清单；T 第一步把它列为候选，第二步判 NONE 并引用第 75、76 行，同样进入审核清单。
- 主要比较 T 与 S+：只有 T 也赢过 S+，才能说作用来自结构。

## 3. 固定不变的

- **指南：** `data/guidelines/ncbi_disease_guidelines.txt`（原指南，沿用运行器的哈希前缀检查）。
- **模型：** claude-haiku-5-5，effort xhigh，adaptive thinking，structured outputs，max_tokens 128000，Batch API；与 `reproduction/haiku_batch_loops.py` 相同，复用它的 BatchQueue（断点续跑，最多重试 3 次）。
- **实体 schema：** `data/schemas/ncbi_entities.schema.json`。
- **评分：** 真正漏标用 `reproduction/lib/discrepancy.py` 的 `classify_document`（`false_negative`），与错误分析报告同一口径；Track 1 的严格 F1 用 `reproduction/lib/scoring.py` 的 `score_directory`。
- **规模：** 每组每篇跑 2 次：第 2 次让波动小 20% 至 29%，第 3 次只再小 8% 至 14%。200 篇（你 11/13 定）：按原指南 19 次运行的波动推算，真实减少 20% 时有九成以上把握判出来；各篇数能判出多大的减少见 `outputs/pilot_size_options_output.txt`。

## 4. 文档

- **池：** 训练集 593 篇去掉 dev50、heldout50（留作最终评价的 50 篇）和 6 个 BioRED PMID，共 487 篇；定义与 `nodes/2026-11-06_seminar/error-analysis/scripts/ablation_stage0.py` 第 175 至 178 行相同。
- **抽样：** `random.Random(20261113).sample(sorted(pool), len(pool))` 打乱。前 100 篇留作方案 A 正式实验的评价集，这次不用；第 101 至 300 篇作试跑文档。运行前把两份清单和池的 SHA-256 写进输出目录。
- **验证集 100 篇不用：** 它的逐例错误已用来挑方向，不再是独立的评价集（错误分析报告第 10 节）。

## 5. 判定（运行前写定）

主指标是 Track 2 输出的真正漏标数，按文档配对比较：同一篇文档在两组里各取 2 次的平均，相减后在全部试跑文档上合计。

- **通过：** T 对 S、T 对 S+ 的合计差，按文档重抽样得到的 95% 区间都不含 0，而且 T 更少（RP v4 的口径）。两个比较都要通过，误判通过的机会不超过 2.5%。拆开结构本身有作用，进入正式实验设计。
- **只赢 S、不赢 S+：** 没有证明两步结构比同样说明下的单次调用更好。方案 A 作为架构改动没有得到支持，停；说明层面的结果交你和教授判断。
- **不赢 S：** 停方案 A。
- **只报告、不设门槛：** Track 2 输出中不与任何 gold 重叠的预测数（专家要删的）；Track 1 的严格 F1（2 次的均值）；按 gold 类型分的真正漏标；每次调用的实际费用。
- **结论作废：** 重试后仍不能用的调用（截断、拒答、JSON 解析失败）超过 5% 时，补跑这些调用再判定。

## 6. 费用与时间

- **调用：** 每篇每跑一次，S 和 S+ 各调用 1 次（一次标完整篇），T 调用 2 次（先找、再定类型）。200 篇 × 2 次：S 400 次，S+ 400 次，T 800 次，共 1,600 次。
- **费用（估算）：** 原指南在验证集上每次调用实测 ¥0.634（`nodes/2026-10-23_seminar/haiku-trial/batch_pilot_costs_output.txt` 第 5 行），1,600 次约 ¥1,010。不设花费上限（你 11/13 的决定）；超过 ¥1,000，运行前按 RP v4 第 5 节通知管理员。
- **时间（推算）：** 实现和离线检查 1 至 2 天（交给 Codex）；运行约 1 天（T 的第二步要等第一步）；分析半天。

## 7. 交给 Codex 的实现要求

- **模板：** S 沿用现有 `annotate_with_guidelines` 模板和 `OutputConfiguration(include_rationale=True, include_guideline_section=True)`，一个字不改。S+ 只在 `instructions` 填附录第一段，输出字段加一个排除标记。T 第一步也用现有模板，`instructions` 填附录第二段，输出字段与 S+ 相同，只去掉类型和排除标记；第二步新增一个模板，正文用附录第三段。
- **T 的输出 schema：** 第一步 `{"annotations": [{"start", "end", "text", "rationale", "guideline_section"}]}`；第二步 `{"decisions": [{"id", "entity", "rationale", "guideline_section"}]}`，`entity` 取 schema 中的标签或 `"NONE"`；边界一律用第一步的。
- **第二步漏判时怎么处理（只影响 Track 1 的报告，不影响通过与否）：** 模型漏判的候选，在 Track 1 里当作不标，并记下个数。交给专家的清单只由第一步的候选决定。
- **输出：** `outputs/ncbi_disease/<运行日期>_haiku-xhigh_pilot_twostep/` 下按组、按次分目录，保存原始回复、Track 1 与 Track 2 的 PubAnnotation 预测、`metrics.json`、文档清单。分析脚本和输出放下次 seminar 的节点文件夹（日期待定）。
- **提交批次前的离线检查，全部通过才运行：**
  1. dry run：S 的 prompt 与复现 E1 的 prompt 只有正文不同（同模板、同指南哈希）。
  2. 用假 provider 跑通三组，Track 1、Track 2 输出与手算一致；漏判按上条处理。
  3. 计数口径：用同一段计数代码重算 `20261022_haiku-xhigh_e1_run01` 在验证集上的真正漏标，等于 140。
  4. 试跑文档与留作评价的 100 篇不相交，都在 487 篇池内。
  5. dry run 打印预计费用。

## 8. 不做的

- 不改指南，不跑改进循环（那是正式实验）。
- 不在验证集上运行，不和 top-4 指南比较。

## 附录：三段新说明的草稿（请审）

**S+ 的 instructions：**

> Annotate every span that could be a disease mention under the guidelines below, in any role. If the guidelines say a span should not be annotated, still return it and cite the section that excludes it. When a span is a disease mention only under some reading, include it. Give each span the type it would otherwise have, and set "excluded" to "yes" for spans the guidelines say should not be annotated and "no" otherwise.

**T 第一步（找全）：**

> Annotate every span that could be a disease mention under the guidelines below, in any role. If the guidelines say a span should not be annotated, still return it and cite the section that excludes it. When a span is a disease mention only under some reading, include it. Do not give a type in this step.

（前三句与 S+ 逐字相同；只有最后一句不同：S+ 要给类型和排除标记，这里不给类型。）

**T 第二步（定类型）：**

> You are given the text, the guidelines and a numbered list of candidate spans. Decide each candidate exactly once: give its type from the entity schema, or NONE if the guidelines say it should not be annotated, and cite the guideline section. Keep each candidate's span as given and do not add spans.

## 核查记录

- 文档池：`ablation_stage0.py` 第 175 至 178 行；`reproduction/test_splits/ncbi_disease_heldout50.json`（size 50，seed 20261024，pool_size 537，排除 6 个 BioRED PMID）。
- 单价：`batch_pilot_costs_output.txt` 第 5 行，top-1 loop01（停在原指南）的验证集标注 100 次，¥63.38，平均 ¥0.634。
- 计数口径：`nodes/shared/error-analysis/scripts/error_table.py` 用 `reproduction/lib/discrepancy.py` 的 `classify_document`；e1_run01 的真正漏标 140 见 `outputs/true_miss_recoverability_output.txt` 第 3 行。
- 规模：`nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot_variance.py`（ba3a0d31c90b）输出 `outputs/pilot_variance_output.txt`（ffb2f87a4a17），给出同一篇文档重复标注的波动 0.355 和效果在文档间的不均 1.045（去掉文档 8733131 为 0.500）；`nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot_size_options.py`（b5af51cf532d）输出 `outputs/pilot_size_options_output.txt`（e99053527000），给出各篇数能判出的减少和跑 2、3 次的差别。两个脚本在仓库根目录直接运行。
- 运行器设置：`reproduction/haiku_batch_loops.py` 第 94 至 113 行（训练集目录、指南、schema、输出配置、重试次数）。
- 本文件只是设计，没有调用 API。
