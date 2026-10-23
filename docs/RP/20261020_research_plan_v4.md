# 研究计划 v4：以中期发表为基线

2026-10-20，会后修订。本版取代 v3；v3 已删除，原文在 git 历史里。

- 依据：10/20 会议，记录见 Notion 页面 "10/20 meeting summ & todo"。
- 2026-10-22 修订：主模型改为 Claude Haiku 5.5，effort xhigh，经 Batch API 提交（第 4 节）；第 1 步已完成；第 2 步默认 E1 10 次、每种方法 10 个循环（用户定），不使用任何 GPT-5.4 数据；第 5 节费用按 Haiku 重算。10/20 版的 DeepSeek 设计和费用见 git 历史。
- 状态：提案。第 1 步已完成，其余步骤都没有运行，费用均为估算。
- 证据汇编：`todo-temp/plan-v3/evidence_notes.md`。

## 1. 中期发表（9/7）的基线

| 项目 | 中期内容（`midterm_slides.pptx`） |
| --- | --- |
| 题目 | Optimizing Annotation Guideline Refinements for LLM-Based Annotation |
| 动机 | 监督模型要先有 593 篇 gold 才能学会标注惯例；LLM 可以通过指南学到这些惯例，"bypasses the need to produce large-scale gold data first" |
| 问题 | 主论文中，指南带来 +0.27（0.46 → 0.73），refinement 只多带来 +0.03（0.73 → 0.76） |
| 六个论点，分三条轴 | 提取（论点 2、3、6）：是否充分利用了开发数据？泛化（论点 1、4）：开发集上的提升能否推广到验证集？可靠（论点 5）：一次标注稳不稳定？ |
| 中期目标 | 把验证 F1 从约 0.79 提到 SOTA 0.87，同时保持低监督的优势（refinement 只用 10 篇，监督学习要 593 篇） |

## 2. 会后的定位：两种场景，两条 track

### 2.1 会上的意见

| 谁 | 意见 | 对计划的影响 |
| --- | --- | --- |
| 後藤教授、Kim 教授 | 不是所有标注都需要专家修正。需要修正的主要是构建 benchmark 的场景；越来越多的使用场景直接采用 LLM 的标注结果，不做修正 | 按这两种场景分成两条 track |
| Kim 教授 | 实际标注时专家不知道哪些对、哪些错，最终都要通读全文。删多标（FP）很便宜，补漏标（FN）必须读全文，和手工标注没有区别。如果有能调节精确率和召回率的参数，就往高召回一侧调 | Track 2 以 FN 为主指标，FP 为次要指标 |
| 後藤教授 | 只有一个案例分析，不够撑起一篇论文；要建立覆盖全部错误的分类体系。结论要说清楚：同样的减负，传统机器学习或微调也能做到，本方法的优势是只需要少量标注 | 错误分类体系是 Track 1 的第一步；写进答辩时的说法 |
| Ken | 现在的改动只有 top-4，原方法的其他步骤也能改，比如 discrepancy 的分类方式、principle 的生成方式。第 7 页的区间包含 0，还不显著。换新模型重跑，结论不变就可以。手上没有专家标注 | 列为 Track 1 的候选改动；在新模型上每种方法跑多个循环（10/22 起为 Haiku 5.5，默认每种 10 个）；两条 track 都以 gold 为参照 |

### 2.2 两条 track

| | Track 1 | Track 2 |
| --- | --- | --- |
| 场景 | LLM 标注直接使用，不经人工修正 | 构建 benchmark，需要专家修正 |
| 目标 | 提高直接标注的质量 | 减少专家的修正量 |
| 做法 | 先对全部错误做分类，再针对占比最高的错误类别改进方法 | 用多次运行之间的投票阈值调节召回率，用 FP 换取更少的 FN |
| 主指标 | 四子类型严格 F1，和主论文比（同一批 100 篇，0.73 / 0.76） | FN 数（召回率） |
| 次要指标与参照 | 单一类型 F1 对照监督 SOTA（NEEDLE 0.9228，划分不同，只作参照） | FP 数；FN 和 FP 的取舍曲线 |
| 判读 | 只在同一模型内部比较增益，区间不含 0 才说有增益 | FN 减少量的 bootstrap 区间不含 0 才说有效 |

**Track 2 的已有数据（GPT-5.4，valid100，只作说明）：**

| 设置 | FN | FP |
| --- | --- | --- |
| top-4 单次运行 | 162 | 148 |
| 8 次运行，至少 2 次标出才保留 | 109 | 217 |
| 8 次运行取并集（至少 1 次标出就保留） | 80 | 393 |

### 2.3 答辩时的说法

- **人工修正还有没有必要：** 构建 benchmark 需要经专家核对的数据，而且需要 benchmark 的标注对象远不止基因、疾病和关系，这是 Track 2 的场景。其他越来越多的使用场景直接采用 LLM 标注，这是 Track 1 的场景。
- **和微调相比的优势：** 只需要少量标注文档，不需要成百上千篇。文献中的学习曲线可以作支撑：同样约 10 篇的标注量，LLM 约 0.85，监督模型约 0.68（单一类型，划分不同）。

**不主张：**
- LLM 可以替代独立标注者；
- 方法在绝对分数上胜过主论文。

English (for slides):
- Two scenarios: LLM annotation used as is (Track 1) and benchmark building with expert correction (Track 2).
- Track 1: analyse every error, then improve the method where the errors concentrate; measured by strict F1 against the base paper.
- Track 2: trade false positives for fewer false negatives, because a missed mention costs as much as manual annotation; measured by FN, with FP as the cost.

## 3. 中期论点：当时、现在、在 v4 中

第 4 点（10 篇开发文档覆盖不了验证集的错误类型）不再探索。

| 论点 | 中期时的状态 | 中期之后的发现 | 在 v4 中 |
| --- | --- | --- | --- |
| 1. verified examples 被抄进指南 | 去掉示例就不再抄写，但循环到不了 0.9 | 同一个示例区块还写出了与 gold 矛盾的 named exclusion：R4 删掉后 FALDH 3/3 恢复 | Track 1 候选 |
| 2. verified examples 不随错误类型变化 | 未测 | 固定为按文件名排序的前 5 篇 | Track 1 候选 |
| 3. 没有利用标注理由 | 未测 | 仍未测；漏标没有理由可用 | Track 1 候选 |
| 5. 一次标注不稳定 | 开发集 10 篇时标准差 0.0150 | 13 个循环保留的 18 轮里，14 轮的提升在噪声带以内 | 稳定性测试；复现中测噪声带 |
| 6. 每轮只处理一个错误簇 | top-4 正在测试 | top-4 分数最高，但增益 +0.0231 [−0.0192, +0.0683] 未被证实 | 复现中做 top-4 对 top-1（10 对 10 个循环） |
| 新发现：子类型混淆 | 无 | SpecificDisease 和 DiseaseClass 互相判错，是严格 F1 上最大的损失 | 由分类体系确认后决定 |

## 4. 步骤

**模型（2026-10-22 定）：** 新实验全部使用 Claude Haiku 5.5（`claude-haiku-5-5`），effort xhigh，经 Message Batches API 提交；structured outputs 的 schema 取自 prompt 自身的字段，max_tokens 64000，不设 temperature。GPT-5.4 不再运行，现有结果只作为案例研究保留。GPT-5.4、DeepSeek、Haiku 的结果分表列出，不放在同一个比较里。

选择依据（dev10，同一 prompt 和评分，每种设置 20 次）：

| 设置 | dev10 F1 | 每次 FN | 每次调用 | 同一精度所需的钱（high = 1，FN / F1） |
| --- | --- | --- | --- | --- |
| DeepSeek V4.1 flash，开 thinking | 0.8062 | 16.8 | ¥1.27（标准 API，非高峰） | 2.99 / 2.62 |
| Haiku high | 0.7615 | 22.6 | ¥0.315（Batch） | 1.00 / 1.00 |
| Haiku xhigh | 0.7605 | 22.15 | ¥0.511（Batch） | 0.81 / 0.63 |
| Haiku max | 0.7745（只有 10 次完整） | 19.9（同左） | ¥1.431（Batch） | 2.35 / 2.09 |

- **为什么是 xhigh：** 达到同一显著性所需的钱约等于每次费用乘以方差，xhigh 最低。high 和 xhigh 的均值没有差别（p 0.88）。max 比 xhigh 好（没有截断的 8 篇文档上 F1 +0.024，p 0.007），但每次调用是 xhigh 的 2.8 倍，比 DeepSeek 还贵，且 5% 的回复超过 64000 token 被截断。
- **为什么是 Haiku：** 同一精度所需的钱约为 DeepSeek 的四分之一（FN 0.81 对 2.99，F1 0.63 对 2.62）；漏标更多（每次约 22 对 17），方法可减少的漏标更多。这只是假设：漏标多不等于指南能修好的漏标多，而且分析和改写也由 Haiku 来做。
- **风险：** Haiku xhigh 的 dev10 F1 比 DeepSeek 低 0.046（p < 0.0001），审稿人会问"为什么不直接用更强的模型"。max 不改指南，在 8 篇文档上每次就少漏标约 2 个（p < 0.0001），可作为"只提高 effort"的参照。是否在 DeepSeek 上跑同一方法作为较强模型的对照，待用户决定，费用另算。

| 顺序 | 步骤 | 做什么 | 调用 | 完成标准 |
| --- | --- | --- | --- | --- |
| 1 | 稳定性测试与选模型 | 已完成（10/16 至 10/22）：DeepSeek 开、关 thinking；开 thinking 补到 20 次；Haiku high、xhigh、max 各 20 次 | 已完成 | 见 LOG 10/16 至 10/22 各行 |
| 2 | 主要结果复现 | E1：valid100 用原指南标注 10 次；E2：top-1 循环 10 个；E3：top-4 循环 10 个；每个终版在 valid100 上标注 1 次。同一方法的循环同步推进，每一步一个批次。主要问题两个，各以 Welch 检验 p < 0.025 判定：P1 top-1 循环是否胜过 E1；P2 top-4 是否胜过 top-1 | 3,520 至 9,600，视轮数 | 全部跑完；噪声、增益、top-4 对 top-1 都有区间 |
| 3 | 错误分类体系 | 用复现的全部输出，分两层归类。第一层：漏标、多标、边界、子类型，再按实体类型细分。第二层（原因）：指南导致（与 gold 矛盾的规则、过宽的排除）、指南没覆盖、标注惯例或 gold 歧义、模型不稳定、开发集没覆盖。先用规则自动归类，再随机抽 50 个人工核对 | 0 | 每个错误都有归类；报告人工核对的一致率；各类别有计数和占比 |
| 4 | Track 2 取舍曲线 | 用同一批输出，投票阈值 k 从 1 调到 N，画 FN 和 FP 的曲线 | 0 | 每个 k 都有 FN、FP 和区间；FN 减少量相对单次运行有 bootstrap 区间 |
| 5 | Track 1 改动 | 按第 3 步的结果，针对占比最高的错误类别选定改动，一次只改一处，与第 2 步同一方法的循环对照；循环数按第 2 步测得的循环间离散度定 | 每个循环 123 至 490 次，视方法和轮数 | 主看目标错误类别是否减少；严格 F1 的区间不含 0 才主张有增益 |
| 6 | 测试集评价 | 流程冻结后只跑一次 | 300 | 需要作者同意；只跑一次，看到结果后不再修改 |

**第 2 步的次数：** 默认 E1 10 次、每种方法 10 个循环（用户 10/22 定）。不使用任何 GPT-5.4 数据。

**Track 1 的候选改动**（只列候选，等第 3 步结果出来再选）：
- 删除与 gold 矛盾的 named exclusion（中期论点 1，约 12 次调用）；
- 按错误簇挑选 verified examples（论点 2）；
- 把标注理由传给 Pattern Explanation（论点 3）；
- 单独判定子类型（新发现，约 320 次调用）；
- 重新设计 discrepancy 的分类方式（Ken 的建议）；
- 改 principle 的格式（Ken 的建议）。

## 5. 日程与费用

| 周 | 内容 |
| --- | --- |
| 10/20 至 10/26 | 稳定性测试与选模型（已完成）；循环和 valid100 脚本接入 Claude provider，支持同步推进的批次提交、重试和续跑 |
| 10/27 至 11/02 | 主要结果复现 |
| 11/03 至 11/09 | 错误分类体系；Track 2 取舍曲线；选定 Track 1 的改动 |
| 11/10 至 11/23 | Track 1 改动的实验 |
| 11/24 至 11/30 | 缓冲；测试集评价（获得同意时） |
| 12 月起 | 写作 |

| 第 2 步（E1 ×10，每种方法 10 个循环），每个循环的轮数 | 调用 | 估算 | 最多 |
| --- | --- | --- | --- |
| 1 轮 | 3,520 | ¥1,799 | ¥2,136 |
| 2 轮 | 3,840 | ¥1,962 | ¥2,636 |
| 3 轮 | 4,160 | ¥2,126 | ¥3,137 |
| 5 轮 | 4,800 | ¥2,453 | ¥4,138 |
| 10 轮 | 6,400 | ¥3,270 | ¥6,641 |
| 20 轮（停止规则的上限） | 9,600 | ¥4,906 | ¥11,647 |

其中 E1 为 1,000 次调用、¥511。测试集评价 300 次调用、¥153。分类体系和取舍曲线不调用 API。

- 只有标注调用的价格是实测的：Haiku xhigh 在 dev10 上的均值 ¥0.511（Batch 价），valid100 的文档按同价计。
- 轮数没测过，所以按轮数列出。循环在第一次不提高 dev10 F1 时停止，最多 20 轮。
- 分析调用（discrepancy、principle、改写）也没测过："估算"按标注调用计价，"最多"按 100,000 token 的 prompt 加 64,000 token 输出计价（每次 ¥3.32）。
- 同步批次每一步都能看到已花的钱，可以设花费上限。
- Batch 价要求同一方法的循环同步推进；每轮 4 个先后相连的批次，另加开头的 dev10 标注和最后的 valid100 标注各 1 个。用标准 API 价格翻倍。
- 每一次运行都要先得到批准；超过 ¥1,000 的部分要通知管理员，第 2 步运行前需通知。

## 6. 不做的事

| 不做 | 理由 |
| --- | --- |
| 在 GPT-5.4 上做新的实验或分析 | 之后不再使用 GPT-5.4；分类体系和取舍曲线都在 Haiku xhigh 的输出上做 |
| 计时的专家标注实验 | 没有现成的专家标注；补漏标和手工标注没有区别，负担直接用 FN 和 FP 的数量衡量。列为未来工作，写进局限 |
| 微调模型基准 | 不做训练；和微调的比较引用文献中的学习曲线 |
| 用 LLM 替代独立标注者 | 不在主张范围内 |
| 论点 4：按错误覆盖挑选开发文档 | 不再探索 |
| 改写时输入 gold | 担心把答案写进指南（硬编码） |

## 7. 待邮件确认

- 官方测试集能否在最后用一次；
- 标注费用；
- 和 Ken 当前工作的边界。

## 核查记录

- **会议内容：** `C:\Users\zhouh\Music\meetily-recordings\Meeting 20_10_26_13_59_17_2026-10-20_04-59\transcripts.json`，358 段，约 67 分钟，没有说话人标注。
  - 发言人按内容归属，经用户确认。
  - "没有专家标注""换新模型重跑即可"也由用户确认。
- **中期内容：** `archive/2026-09-07_midterm-defense/midterm_slides.pptx`，第 2、4、8、9、10 页。
- **其他数字：** 出处见 `todo-temp/plan-v3/evidence_notes.md`。
  - Track 2 的 FN 和 FP：`offline_direction_checks_output.txt` 的 inputs 一节和 B 节；
  - 子类型和噪声：`step_value_checks_output.txt` 的 S4 节和 S5 节；
  - 学习曲线：evidence_notes 第 2 节。
- **费用（10/20 版，DeepSeek）：** `todo-temp/plan-v3/node_cost.py`（4f9eec7cc127），输出 `node_cost_output.txt`（714163730ca7）的 "== plan v4" 一节。
- **选模型（10/22）：** 都在 `todo-temp/haiku-trial/`。
  - F1、费用、截断：`report_with_max_output.txt`（4b1f7003f6f8）；
  - FN 与噪声：`fn_noise_with_max_output.txt`（74ce14ab0bcc）；
  - 同一精度所需的钱：`effort_efficiency_with_max_output.txt`（932778912103）；
  - max 在没有截断的 8 篇文档上的比较：`max_check_output.txt`（ebfa87a6409f）；
  - DeepSeek 的 20 次：`todo-temp/deepseek-stability/units/`。
- **第 2 步的费用（10/22，默认次数 10）：** `todo-temp/haiku-trial/cost_default10.py`（8bd6b0475d8d），输出 `cost_default10_output.txt`（67fc125645a5），只用 Haiku 实测价格和代码里的循环结构。停止规则见 `src/llm_guideline_moderation/iterative.py`（`SAFE_MAX_ITERATIONS = 20`，F1 0.9，第一次不提高即停）；top-4 每轮的调用见 `reproduction/moderate_topk.py`。
- **已撤回：** `plan_counts_haiku.py`、`plan_adaptive_haiku.py`、`plan_cost_haiku.py`、`stand_in_ranges.py`、`why_counts.py` 用了 GPT-5.4 的数据，文件开头已注明撤回，不用于任何决定。
- **本文件只是计划，没有调用 API。**
