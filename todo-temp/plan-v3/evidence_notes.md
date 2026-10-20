# plan v3 的证据汇编

2026-10-20 整合。`docs/RP/20261020_research_plan_v3.md` 和 10/20 会议 deck 引用的数字，出处都在本文件或本文件夹的脚本输出里。

本文件取代以下 7 份文档，原文保存在提交 d86ea17 中：
- 10/19 方向核查报告（`direction-scan/20261019_direction_research_report.md`）；
- plan v2 review 报告及其 3 份笔记（审计、文献、步骤价值与复核曲线）；
- `thesis-framing/20261020_thesis_goal_and_nodes_v2.md`；
- `thesis-framing/20261020_preannotation_workflow.md`。

## 0. 本文件夹的脚本和输出

所有脚本都只读已保存的文件，不调用 API。

| 脚本 | 输出 | 内容 |
| --- | --- | --- |
| `offline_direction_checks.py` | `offline_direction_checks_output.txt`、`.json` | 8 个已保存 valid100 运行上的噪声、投票、复核曲线、gold 子类型一致性、文档内传播、词典基线、配对 bootstrap |
| `error_breakdown.py` | `error_breakdown_output.txt`、`.json` | 各指南的错误类型、单一类型 F1、"修好一类错误后的 F1" |
| `step_value_checks.py` | `step_value_checks_output.txt`、`.json` | 子类型判定的上限和代理结果、删除矛盾示例对 valid100 的影响、可检测差异、保留轮次与噪声、投票子集、复核曲线、单次分数的区间 |
| `audit_helper.py` | `audit_helper_output.txt` | 8 次运行的标准差与可检测差异、癌症类 S/D 混淆、按 1% 步长的复核曲线（含单一类型口径）、dev30 上子类型判定关口的基线 |
| `node_cost.py`（调用 `plan_cost.py`） | `node_cost_output.txt` | DeepSeek 各步骤的调用数、费用和串行耗时（估算） |
| `expert_study_size.py` | `expert_study_size_output.txt` | 专家标注研究需要的篇数（重抽样），以及工时和费用（估算） |
| `preannot_derived.py` | `preannot_derived_output.txt` | NCBI 2012 预标注的推算值；LLM 的 P、R、Jaccard |

重跑说明：
- 2026-10-20 整理时重跑了全部脚本，输出与原记录一致，只有换行符不同。
- `audit_helper.py` 第 5 节比较的是 plan v2 的中英文版本，两份文件已删除，所以重跑时会跳过这一节。

## 1. 已保存运行上的结果

数据：valid100（NCBI Disease 开发集 100 篇，791 个 gold），GPT-5.4 high。评分按项目约定：valid100 用严格 PubAnnotation 匹配。

### 1.1 噪声与区间

| 项目 | 数字 | 出处 |
| --- | --- | --- |
| 同一 R4 指南标注两次 | 0.7878 对 0.7789，相差 0.0089；两次输出完全相同的实体占并集的 0.807 | `offline_direction_checks_output.txt` A 节 |
| 单次分数的 95% 区间（文档 bootstrap，10,000 次） | 原指南 0.7792 [0.7329, 0.8226]；top-4 0.8023 [0.7643, 0.8376]；R4 0.7878 [0.7495, 0.8250] | `step_value_checks_output.txt` S6 节 |
| 配对差异（bootstrap，10,000 次，seed 42） | top-4 减原指南 +0.0231 [−0.0192, +0.0683]；top-4 减 R4 +0.0145 [−0.0215, +0.0507]；R4 减重跑 +0.0089 [−0.0191, +0.0389] | `offline_direction_checks_output.txt` H 节 |
| 8 次运行的严格 F1 | 0.7716 至 0.8050，均值 0.7855，标准差 0.0123 | `audit_helper_output.txt` 第 2 节 |
| 可检测差异（双侧，检验力 0.8） | 3 对 4 个循环：α = 0.05 时 0.026 至 0.033；α = 0.0125 时 0.031 至 0.046 | `step_value_checks_output.txt` S2a/S5 节 |
| 开发集上保留的轮次 | 13 个 dev10 循环共保留 18 轮，其中 14 轮的提升小于噪声带 0.0416（1.96 × 两次标注之差的标准差 0.0212） | `step_value_checks_output.txt` S5 节 |

### 1.2 错误构成（top-4，valid100）

| 错误类型 | 数量 | 用 gold 修好后的严格 F1 |
| --- | --- | --- |
| 子类型错 | 57（SpecificDisease 与 DiseaseClass 互判各 21） | 0.8750 |
| 边界不同 | 45（预测偏长 23，偏短 22） | 0.8597 |
| 漏标 | 55（Modifier 27，DiseaseClass 25） | 0.8429 |
| 多标 | 45 | 0.8260 |

- 修正总数：原指南 229（漏标 73，多标 34，边界 44，子类型 67，其他 11）；top-4 208（55、45、45、57、6）。
- 单一类型 F1：原指南 0.8351，R4 0.849，top-4 0.8546，dev30 0.8455；8 次运行中最高 0.8692（noTP）。
- top-4 的预测全部用 gold 检查一遍，严格 F1 的上限是 0.9606。有 60 个 gold 实体附近没有任何预测。
- 出处：`error_breakdown_output.txt`；`offline_direction_checks_output.txt` 的 C 节和 G 节；`step_value_checks_output.txt` 的 0 节。

### 1.3 子类型（S/D）混淆

- top-4 上，同一 span 的 S/D 混淆有 34 个：
  - 原指南在同一 span 上判对了 19 个，同样判错 10 个，另有 5 个没有这个 span；
  - 只修这 19 个，严格 F1 +0.0242；34 个全修 +0.0434；
  - 有 7 个被另外 7 次运行全部判错。
- 变体 A 的代理结果（把原指南的 S/D 判定照搬到 top-4 的 span 上）：修好 19 个，弄坏 15 个，+0.0051 [−0.0213, +0.0328]。
- 关口的基线：dev30 上原指南 5 次重复的 S/D 混淆分别为 16、15、14、15、16；20 对有序重复里，没有一对是后一次减到一半或更少（0/20）。
- 按训练集 gold 的先例看：20 个混淆里训练先例与 valid gold 一致；13 个的字符串在训练集里没出现过；只有 1 个的训练先例与预测一致。
- 出处：`step_value_checks_output.txt` S4 节；`audit_helper_output.txt` 第 7 节；`offline_direction_checks_output.txt` D 节。

### 1.4 投票、复核曲线、被排除的方向

- **投票（8 次运行，同一实体至少 k 次出现才保留）：**
  - k ≥ 4 时 0.8158，比原指南高 +0.0366 [+0.0059, +0.0699]，是唯一区间不含 0 的提升；但比 top-4 只高 +0.0135 [−0.0137, +0.0387]。
  - 8 次运行的预测合起来包含 711 个 gold，另有 80 个 gold 没有任何一次运行标出。
  - 运行集合不是事先定好的，所以这个结果属于探索性的（`step_value_checks_output.txt` V 节）。
- **复核曲线（用 gold 代替专家，按各次运行的一致度从低到高检查）：**
  - 以另外 7 次运行作信号：检查 16.5% 的实体严格 F1 就到 0.875，随机顺序要 45.7%；
  - 只以同一指南的第二次标注作信号：要检查 38.1%，随机 49.9%；
  - 单一类型口径下达到 0.897 和 0.9228，分别要检查 16% 和 32%（随机顺序 39% 和 65%）；
  - 出处：`step_value_checks_output.txt` R 节；`audit_helper_output.txt` 第 4 节。
- **离线排除的方向：**
  - 文档内统一类型：平均 −0.039；文档内补标：+0.001（E 节）。
  - 训练集 gold 词典：严格 F1 0.4504；用训练先例改 S/D：即使先例池有 563 篇，也只到 0.8189（F 节）。
- **删除矛盾示例对 valid100 的直接影响：** 被点名的字符串在 valid100 里出现 0 次，所以严格 F1 不变，0.8023 仍是 0.8023（`step_value_checks_output.txt` S3 节）。

## 2. SOTA 与参照点（已核实）

| 说法 | 结论 | 说明 |
| --- | --- | --- |
| NCBI：NEEDLE F1 92.28（P 91.76，R 92.81） | 对 | 只有一个 Disease 类型；用 gold 训练集加词典弱标签训练，最后再用 gold 微调（Jiang et al. 2021，Table 5 和 Table 9） |
| NCBI：BioBERT 89.71 | 对 | 测试集，实体级完全匹配（Lee et al. 2020，Table 6） |
| BioRED：T5-3B Multi+CVAE 94.36，Disease 92.84 | 对 | 测试集，单次运行；其他 9 个语料的开发集也用作训练数据（Oi and Miwa，ACL 2025 short） |
| BC5CDR：Bio-RFX 91.96 | 数字对，但不是 NER 的 SOTA | 用的是为关系抽取准备的句子级版本，全部只有 11,241 个实体；主论文随机抽的 100 篇 BC5CDR 开发文档就有 2,146 个实体（EMNLP 2024） |
| 主论文 moderated GPT-5：NCBI 0.76，BioRED 0.82，BC5CDR 0.86 | 对 | Table 1。NCBI 和 BioRED 用完整开发集 100 篇；BC5CDR 从 500 篇开发集里抽 100 篇；测试集刻意不用 |
| "NCBI 上 BioBERT 0.86" | 没有出处 | 0.86 是主论文在 BC5CDR 上的分数；Zhao and Goto (2025) 的 BC5CDR-Disease 是 0.866 |

**其他参照：**
- **四子类型的监督结果：** 没有找到。NCBI 语料作者本人在 BANNER 实验中就把四个类别合成了一个（Doğan and Lu 2012，§2.6）。
- **小样本监督学习（单一类型，按句子计）：**
  - PubMedBERT，100 句：0.680（Gutiérrez 2022）；
  - BERT-MRC，50 句：0.758（Su 2024）；
  - BioBERT，626 句和 1,171 句：0.8108 和 0.8582（RDANER，测试集，5 次平均）；
  - BLURB 训练集共 5,424 句、593 篇。
- **专家一致度：**
  - NCBI 两两一致度，在 span 和"span 加类别"两个层面，Phase II 之后都 "above 80%"，具体数值只在 Doğan 2012 的图 3 里；
  - DNorm 引用的 87.5% 没有说明口径；
  - BC5CDR 疾病标注者之间 87.49%（Jaccard）；BioRED 实体 97.01%；
  - 众包（15 人多数投票，单一类型）：0.872（Good et al. 2015）。
- **主论文的显著性：** 原指南 0.7264 → moderated 0.7588，+0.0323，bootstrap p = 0.0762（Table 6）。

## 3. 预标注流程（文献）

| 语料 | 预标注 | 标注者 | 分歧处理 |
| --- | --- | --- | --- |
| NCBI Disease（Doğan and Lu 2012） | 自研 CRF 识别器，在 AZDC 上训练，十折交叉 | 12 人，每篇 2 人；Phase I 可以保留、删除、改 span 或新增 | Phase II 各自修改，然后开会达成一致，最后由第一作者通查 |
| BC5CDR（Li et al. 2016） | DNorm、tmChem，在 PubTator 中显示 | 4 位有医学背景的 MeSH indexer，每篇 2 人 | 资深标注者裁决 |
| BioRED（Luo et al. 2022） | 已有标注加上 PubTator | 每篇 3 人 | 资深标注者复审；项目开始时先用少量文章制定指南 |

- **NCBI 的"35%"：** 3,295 个预标注里，1,750 个原样保留，1,545 个被修改，另新增 3,605 个，三者相加正好是全部 6,900 个 mention。按这些计数推算，"F1 形式"的一致度是 0.343，与论文报告的 35% 相近；论文本身没有定义这个数。论文引用它，是为了说明标注者没有被预标注带偏。
- **预标注效果的研究：**
  - Névéol 2010：操作 244 对 343（−28.9%），时间 106 对 173 分钟（−38.7%），一致度 85.18 对 77.00；有预标注时 Abbreviation 类的标注变少，作者认为是漏标被掩盖了。
  - Lingren 2014：每个实体省时 13.85% 至 21.5%，没有发现偏差。
  - AnnoHID（ACL 2026 demo）：LLM 预标注没有减少标注时间。
- **LLM 作为预标注器（top-4，valid100）：** 只比 span 时 P 0.862、R 0.847；严格匹配时 Jaccard 0.670（`preannot_derived_output.txt`）。

## 4. 导师和审查委员的意见（原话）

| 日期 | 来源 | 原话 |
| --- | --- | --- |
| 9/12 | 导师邮件（`archive/correspondence/email_with_professor.pdf` 第 7 页） | "F1 = 0.8 (SOTA) may not be good enough for replacing manual annotation ... You can also consider that the LLM annotation will be still have some supports for manual annotation and not saying it will fully replace manual annotations." "It should be not just adding some sentences form the gold examples, but also modifying or deleting the original texts." |
| 9/15 | 审查委员（`archive/2026-09-15_seminar-future-plan/9_15 future plan.docx`） | "current scores not sufficient for product-level use. Asked how to balance cost and performance." "asked what the research goal is, and raised the concern that the dev10 selection may be biased" |
| 9/15 | 同一文档的批注（推测是会上记下的意见） | "goal --> reduce the burden of human annotators." "anyways to estimate the headroom?" "Consider what kind of parts human should remain" |

## 5. 估算（都不是测量值）

- **单次调用的费用：**
  - GPT-5.4 high：¥55.39 至 ¥88.37；
  - DeepSeek V4.1 flash：开 thinking ¥2.204 至 ¥3.523，关 thinking ¥0.069。
  - 出处：`plan_cost.py`、`node_cost_output.txt`。
- **plan v3 的调用量和费用：** 必做步骤 3,876 次调用，关 thinking 约 ¥377，开 thinking ¥8,430 至 ¥13,475；加上条件步骤 4,376 次，关 ¥412，开 ¥9,532 至 ¥15,236（`node_cost_output.txt`）。
- **专家标注研究：**
  - 试点（1 人 40 篇）：4.9 至 12.6 小时，¥7,396 至 ¥63,159；
  - 正式实验（2 人各 100 篇，交叉设计）：12.7 至 39.2 小时，¥18,979 至 ¥195,794；
  - 时薪是占位数；
  - 标注 100 篇时，配对差异的 95% 区间半宽约 ±0.045（`expert_study_size_output.txt`）。

## 核查记录

- **原文：** 被取代的 7 份文档，原文都在提交 d86ea17 中。本文件里的数字都从当时的输出文件逐条摘抄，没有重新计算。
- **文献核对：**
  - NEEDLE、BioBERT、主论文、学习曲线、专家一致度：沿用 10/19 文献笔记，原文保存在 d86ea17 中。
  - CVAE、Bio-RFX、主论文 Table 1：10/20 下载 PDF 后核对，SHA-256 分别为 19f98f26…、bedac8fa…、0f0b205e…。
  - 预标注的三篇语料论文和三项效果研究：10/20 核对。其中 BC5CDR、Névéol、Lingren、AnnoHID 是通过网页抓取读取的。
- **重跑：** 2026-10-20 整理后重跑了本文件夹的全部脚本，输出与 d86ea17 中的记录一致，差异只有换行符；`audit_helper.py` 第 5 节如上所述被跳过。
