# 生物医学语料的预标注流程，以及 LLM 在其中的位置

2026-10-20。回答两个问题："先预标注、再由专家修改"是不是建这类语料的标准做法？我们的 LLM 替代的是谁？

## 结论

- **是标准做法。** NCBI Disease、BC5CDR、BioRED 三个语料都是这样建的：先由机器预标注，再由两到三位标注者各自独立修改，分歧由资深标注者裁决。
- **做预标注的不是人，而是自动工具。** NCBI 用的是自研的 CRF 识别器，BC5CDR 用的是 DNorm 和 tmChem，BioRED 用的是 PubTator。所以 LLM 替代的是预标注工具，不是哪一个人。它要减轻的是之后每位专家的修改工作；专家标准仍由原有的双人标注加裁决来保证。
- **35% 的口径：** 论文没有定义这个数。按论文给的计数推算，它最接近"预标注和最终标注之间的 F1"（34.3%）。论文引用它，是为了说明标注者没有被预标注带偏，而不是为了评价预标注的好坏。
- **预标注确实能减负，但不是必然的。**
  - Névéol 等人的研究：操作次数少 28.9%，时间少 38.7%。
  - Lingren 等人的研究：每个实体省时 13.85% 至 21.5%。
  - 2026 年一项 LLM 预标注的用户研究（AnnoHID）没有观察到时间减少。
  - 另外，预标注可能掩盖漏标。
- **LLM 现在还够不上替代两位独立标注者中的一位。** top-4 对照 gold 的严格 Jaccard 是 0.670；作为参照，BC5CDR 疾病标注者之间的一致度是 87.49%（不同语料，只能看方向）。

## 1. 三个语料的建库流程

| 语料 | 预标注来源 | 标注者 | 每篇几人 | 分歧处理 | 一致度 |
| --- | --- | --- | --- | --- | --- |
| NCBI Disease（Doğan and Lu 2012） | 自研 CRF 疾病识别器，在 AZDC 语料上训练；用十折交叉产生预标注，逐句标注 | 12 人，有生物医学信息学研究背景和语料标注经验 | 2 | 见下方四个阶段 | span 一致和 span 加类别一致，在 Phase II 之后都 "above 80%"，具体数值只在图 3 里 |
| BC5CDR（Li et al. 2016） | DNorm（疾病）和 tmChem（化学物）预先计算，在 PubTator 里显示 | 4 位 MeSH indexer，都有医学训练背景 | 2 | 由第三位资深标注者裁决 | 按 Jaccard 计：疾病 87.49%，化学物 96.05% |
| BioRED（Luo et al. 2022） | 已有语料的标注，加上 PubTator 的自动预标注 | 3 位，有生物医学信息学背景 | 3 | 三人达不成一致时，由一位分子生物学背景的资深标注者复审 | 实体 97.01% |

**NCBI 的四个阶段：**
1. **Phase I：** 两人各自审阅预标注，可以保留、删除、调整 span，也可以新增。
2. **Phase II：** 看过两人的分歧摘要后，各自修改自己的标注。
3. **开会达成一致。**
4. **第一作者通查全语料**，保证同一个短语在不同文档里的类别和 span 一致。

**共同模式：** 机器预标注 → 至少两人独立审阅和修改 → 裁决 → 一致性检查。

**还有一个和本研究直接相关的环节：试点。** BioRED 写道："A small set of PubMed articles were first used to develop our annotation guidelines and familiarize our annotators"，也就是先用少量文章制定指南、培训标注者。我们用 10 篇文档改进指南，正好对应这个试点阶段。

**工作量的一个参照：** BioRED 每批 20 篇，每位标注者标实体大约要 2 小时。

## 2. 35% 是怎么来的

Doğan and Lu 2012 §3.2 的原文：
- "There are a total of 3295 pre-annotated disease mentions: 1750 were found also in the final corpus while the remaining 1545 were either modified or deleted. Furthermore, the final corpus consists of additional 3605 new annotations. Overall, the agreement between pre-annotation and final annotation results is only 35%."
- 引用这个数的目的写在同一节："To demonstrate that human annotators were not biased towards the computer-generated pre-annotation"。

**按这些计数推算（`preannot_derived.py`）：**
- 1,750 + 1,545 + 3,605 = 6,900，正好等于最终语料的 mention 总数（Table 4：训练 5,148，开发 791，测试 961）。
- 预标注被原样保留的比例是 53.1%（1,750 / 3,295）；最终标注里来自原样预标注的比例是 25.4%（1,750 / 6,900）。把两者合成 F1，是 34.3%，和论文的 35% 最接近。
- 论文没有定义这个"agreement"，所以 34.3% 只是我的推测。
- 论文把预标注器描述为"疾病 mention 识别器"，没有提到子类型，所以这里比较的应该只有 span。

**和我们的 LLM 粗略对比：**

| | 精确度类指标 | 召回类指标 |
| --- | --- | --- |
| 2012 年 NCBI 的预标注（原样保留的比例） | 53.1% | 25.4% |
| top-4 指南（GPT-5.4，valid100），只比 span | 0.862 | 0.847 |
| top-4 指南，span 加子类型，严格匹配 | 0.810 | 0.795 |

这个对比只能看方向，原因有三：
- 文档范围不同：一个是全部 793 篇，一个是 valid100；
- 定义不同：一个是"原样保留"，一个是"完全一致"；
- 年代不同。

方向上，LLM 是一个强得多的预标注器。

## 3. 预标注效果的已有研究

| 研究 | 场景 | 预标注方式 | 结果 |
| --- | --- | --- | --- |
| Névéol, Islamaj Doğan, Lu 2010，J Biomed Inform 44(2):310–318 | 7 人标注 10,000 条 PubMed 查询，16 个类别；一半有预标注，一半从零开始 | 自动工具 | 操作次数 244 对 343（−28.9%）；时间 106 对 173 分钟（−38.7%）；标注者一致度 85.18 对 77.00；类别分布没有显著差别（p = 0.6233），但有预标注时 Abbreviation 类的标注明显变少，作者认为是预标注掩盖了漏标 |
| Lingren et al. 2014，JAMIA 21(3):406–413 | 临床试验公告，疾病和症状，2 位标注者 | 词典 | 每个实体省时 13.85% 至 21.5%（p < 0.01）；没有发现偏差，只有罕见的症状类例外 |
| AnnoHID（ACL 2026 demo） | 印尼语医疗社交媒体，NER 和概念规范化，21 人的用户研究 | LLM | LLM 辅助没有减少标注时间；NER 的 κ 是 0.76。只读了论文页面的摘要信息，没有读全文 |

**三点启示：**
1. **按"操作次数"衡量负担已有先例。** Névéol 等人就是这样算的，和我们计划里的"修正次数"是同一种指标。
2. **省时不是必然的。** 传统的预标注能省 14% 至 39% 的时间，但 LLM 预标注的那项用户研究没有观察到省时。所以如果能做一次计时，比任何模拟都更有说服力。
3. **偏差主要表现为漏标被掩盖。** 用 gold 模拟专家测不出这种偏差，只能写进局限，或者靠真人实验来测。

## 4. LLM 在流程中能替代什么

| 角色 | 现在由谁做 | LLM 能否替代 | 依据 |
| --- | --- | --- | --- |
| 预标注 | 自动工具 | 能，而且是升级 | 第 2 节的对比；本研究的主张放在这里 |
| 两位独立标注者之一 | 人 | 目前不能 | top-4 对照 gold 的 Jaccard：严格匹配 0.670，只比 span 0.746。人和人之间：BC5CDR 疾病 87.49%（Jaccard），NCBI 两两一致度 Phase II 后 >80%。我们比的是 LLM 对一致后的 gold，他们比的是人对人，所以只能看方向 |
| 裁决和一致性检查 | 资深标注者、第一作者 | 不在本研究范围 | |
| 试点阶段制定指南 | 项目组用少量文章制定指南、培训标注者 | refinement 可以辅助 | BioRED 的描述；我们的 10 篇正好对应这个阶段 |

## 5. 对研究定位和计划的影响

**一句话定位：** 在新语料的试点阶段，用少量专家标注来改进指南，让 LLM 成为更好的预标注器；在专家标准不变的前提下，减少每位专家需要做的修改。

**计划里要改的地方：**
- **人工负担的主指标：** 每位标注者在 Phase I 要做的操作，包括修改、删除、新增；原样保留的不计。对照两个基线：
  - 从零标注：全部都要新增；
  - 旧式预标注：用 NCBI 2012 年的水平，只能粗略对比。
- **局限：** 写明预标注可能掩盖漏标（Névéol 研究里 Abbreviation 的例子），gold 模拟测不出来。
- **计时：** 建议在会上问：能不能用 5 到 10 篇文档，请一位标注者分别在"从零标注"和"修改 LLM 预标注"两种条件下各做一次，记录时间。
- **不主张：** LLM 可以替代独立标注者。

## 核查记录

- **原文核对（PDF 下载到 scratchpad，用 `pdftotext` 提取文字）：**
  - Doğan and Lu 2012（aclanthology.org/W12-2411.pdf），SHA-256 b632de5542e297295f6448f0c6598a3d72a6771a8023e84f8fc629e0301a61d9。读了 §2.3、§2.5、§3.1、§3.2 和参考文献。
  - Luo et al. 2022 BioRED（arxiv.org/pdf/2204.04263），SHA-256 e350d577fa8deb3718be7c7e700f5e31b07bd4e00e7bc5c0fb3f91fa5a143ae7。读了 §3.2、§3.3 和 Table 4。
- **通过网页抓取工具读取（经过摘要模型转述，个别数字有转写风险）：**
  - BC5CDR：Li et al. 2016，Database，PMC4860626；
  - Névéol et al. 2010：PMC3063330；
  - Lingren et al. 2014：PMC3994857；
  - AnnoHID：aclanthology.org/2026.acl-demo.67，只读了页面摘要。
- **NCBI 的 mention 总数：** 5,148、791、961 取自 `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/literature_reference_points.md` 的 Q3，原文是 Doğan and Lu 2012 的 Table 4。
- **推算的数字：** `todo-temp/thesis-framing/preannot_derived.py`（1382655c1666），输出 `preannot_derived_output.txt`（4662ebbe0472）。
- **我们的 TP、FP、FN：** 取自 `todo-temp/meeting-20261020/error_breakdown_output.txt`（41ca602af29f）。
- **没有调用标注 API。**
