# 研究进展

更新：2026-10-15。这里沿研究主线记录阶段成果、判断变化和下次 seminar 待办；逐次实验见 [LOG.md](LOG.md)，固定背景及评价口径见 [OVERVIEW.md](OVERVIEW.md)。

## 总体主线与阶段目标

**优化 guideline refinement，使 LLM 的数据标注质量首先逼近 SOTA，随后实现对人类专家标注的替代或部分替代，降低人工数据标注负担。**

这是本研究的总体方向。当前的 hard-coding、规则冲突、Top-K 和开发数据规模分析，分别针对这条路线上的方法瓶颈。长期目标由用户在 2026-10-06 明确，研究脉络来自 [中期 abstract](archive/2026-08-31_midterm-abstract/47256388_周恒宇_要旨.pdf)，第 1 至 2 页。

| 阶段 | 要解决的问题 | 当前位置 |
| --- | --- | --- |
| 复现与诊断 | 原指南及 refinement 能改善什么，提升被哪些环节限制？ | 已复现并开展诊断，发现开发收益、泛化收益与稳定性并不一致。 |
| 方法优化 | 如何从少量标注证据学习可复用规则，合理整合新旧指南，并减少修改副作用？ | 当前主要阶段，三条优化轴已有探索，规则作用域是本轮重点。 |
| 验证效果，逼近 SOTA | 改进能否稳定提升未参与修改的文档表现，并推广到同类案例及其他语料？ | 已有 validation 结果但增益有限且不一致。NCBI Disease 的比较目标是 BioBERT F1 **0.86**，尚未证明达到。 |
| 验证专家标注替代能力 | 哪些标注可交给 LLM，哪些仍须专家复核，质量和人工负担如何变化？ | 长期目标。专家对照及人工修正负担尚未实测，不能由接近 SOTA 分数直接推定。 |

研究同时允许完整替代与部分替代两种实际结果。达到可比的模型基准后，继续通过相同任务和规则下的专家对照、人工修正比例及时间成本，判断可自动化的范围。导师 9 月 12 日关于避免过早声称替代人工的反馈，是对现阶段证据和表达的要求，不取消这个长期目标。

## 从中期 abstract 延伸的三条优化轴

abstract 把六类方法问题归入三个方向。后续历史和新实验继续按这个结构解释，避免单个案例变成整个课题。

| 优化轴 | 中期诊断 | 延续至今的研究问题 |
| --- | --- | --- |
| **提取有效规则** | 示例未随错误类型调整，缺少 annotation rationale，每轮仅处理一个错误簇可能带来副作用。 | 哪些证据足以支持规则？Top-K 如何联合处理错误？新旧规则如何组合，避免修好一类却误伤另一类？ |
| **泛化到新文档** | verified examples 被写入指南，约 10 篇开发文档的错误覆盖不足。 | 如何保留正确行为而减少样例依赖？开发规模、同类对照和错误类型覆盖如何影响 validation 表现？ |
| **可靠评价** | 相同设置的标注存在波动，小样本变化可能影响接受修改与停止。 | 如何区分规则带来的真实收益/回归与随机变化，避免选中偶然高分？ |

当前 Round 3/4 冲突案例主要推进第一条轴，也关联第二条轴的样例依赖和第三条轴的回归判定。**当前优先切入点是规则作用域，后续是否推广为一般方法取决于验证结果。**

## 历史进展：从复现走向方法优化

### 1. 复现确立起点，暴露 refinement 的有限收益

7 月 27 日确定从既有 moderation 框架复现 NCBI Disease、BC5CDR、BioRED，并记录 F1、迭代次数、指南长度和重复波动。

中期 abstract 报告 NCBI 原指南到 refinement 的 validation 改善约为 **0.73 至 0.76**。后续本地 GPT-5.4 记录为 **0.7792 至 0.7878**，另一批 published-method 标注为 **0.7789**。这些来源及批次不同，不混成一组比较。共同需要回答的是：如何让 refinement 在新文档上的收益更大、更可靠，进一步逼近 **0.86** 的参考目标。

### 2. 8 月：检查开发提升是否来自可复用规则

dev10 原方法达到开发 F1 **0.9091**，但有 **15/37** 个符合条件的新实体字符串进入指南。去掉 verified-example 约束块后，已完成的三次运行文本吸收为零，但均未达到开发阈值 0.9；要求抽象和后验回归验证也做过有限尝试，含负结果与中断结果。

因此，问题从“提高开发分数”延伸为“如何学习能迁移的规则，同时保护正确案例”。文本吸收不等于正确答案记忆，现有结果也没有证明保护正确案例必须依靠记忆。

同期开展 10/20/30 篇规模实验，validation F1 为 **0.7878/0.7745/0.8050**。各规模只有一条已报告 refinement 轨迹，尚不能隔离规模的作用。2026-10-08 勘误：三次运行的 n_examples 实际均为 5（resolved config 与 prompt 实测，见 [P4 报告](todo-temp/p4/20261007_p4_devsize_report.md)），此前"示例上限 5/10/15"为误记，规模对比不含示例数混杂。固定指南五次重复标注的 F1 标准差为 **0.01502/0.00978/0.00921**，提示需要把评价波动纳入方法优化。

8 月 20 日将中期摘要的当前结果重点放在 hard-coding，是当时的写作安排；整个研究仍沿三条优化轴展开。详见 [seminar 历史](archive/seminar_note.txt)和 [8 月实验报告](reproduction/REPORT_progress_20260814.md)，旧报告状态及过强因果结论以当前记录为准。

### 3. 9 月：扩展错误处理，检查规则质量与跨语料表现

Top-4 一次达到开发 F1 **0.9155**，后续重复没有同样达到阈值，尚未形成稳定优于 Top-1 的结论。其价值在于检验联合处理多个错误是否能提升整体收益，同时暴露规则组合的副作用。2026-10-07 补测：该次指南 valid100 F1 **0.8023**（top-1 0.7878、原指南 0.7792），增益集中于 Modifier 召回；单点估计（P3）。

BC5CDR、BioRED 的复现已完成，validation 原指南/修改后分别为 **0.8634/0.8579**、**0.7836/0.8077**。结果不支持所有语料都稳定受益；这些运行用 GPT-5.2，主要 NCBI 诊断用 GPT-5.4，跨语料差异还混有模型差异。

9 月 12 日导师建议指南优化包含修改和删除原规则，不只追加 gold 示例。9 月 24 日进一步分析新增规则的抽象/硬编码部分、讨论专家标注参考，并要求给出解决新旧指南冲突的案例。专家参考服务于长期替代目标，目前仍无同任务实测分数。

### 4. 10 月：用真实冲突检验一项具体优化假设

2026-10-02 seminar（2026-10-06 补录）的 [会议摘要](archive/2026-10-02_seminar-conflict-casestudy/seminar_oct2.md)和 [案例 slides](archive/2026-10-02_seminar-conflict-casestudy/conflict_handle_casestudy.pptx)展示新旧指南合并后的严重冲突：修好一类错误可能误伤其他类别，指南甚至把 gold 实体写为“不标注”。

具体而言，指南把“deficiency of norrin”和“deficient activity of fatty aldehyde dehydrogenase”写作排除示例，但开发 gold 分别标为 DiseaseClass 和 SpecificDisease；“spasticity”的适用范围也需核查。会议摘要报告 Round 3 的三个目标案例只修复一个，Round 4 调整范围后的整体变化仍待核查。约 10 篇、70 个实体的小样本还需要规模及同类对照。

**当时的假设：** “do not apply” 限制的作用域过宽，可能让本应标注的病理状态被排除。（2026-10-07 经 P1/P2 三臂对照检验：**未证实**，见下方结果。）

**对研究主线的推进：** 从观察有限提升、样例依赖和不稳定，进一步定位到规则组合及作用域这一潜在机制。已发现案例，尚未验证解决方法；由此形成文档底部的五项 Todo。

材料：[Round 3 snapshot](outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/snapshot.json)、[Round 4 snapshot](outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/snapshot.json)。需分别记录原规则、实际提示证据、新增文本、模型输出和 gold；gold 不一致或错误簇排名本身不能证明冲突原因或实际选中的提示案例。

**2026-10-06，P0 核查完成：** Round 4 开发 F1 从 0.8873 升至 0.9091，逐实体为 3 个修复、1 个新增回归；目标簇仅修复 1/3。norrin 与 FALDH 是较早存在的漏标，不能归为本轮新增回归。完整逐例变化和混淆矩阵见 [P0 报告](todo-temp/p0/20261006_round4_p0_report.md)。作用域的因果解释仍待 P1/P2。

**2026-10-07，P1/P2 三臂对照完成：** 原从句（dev F1 **0.8873**）、删除从句（P1，**0.8671**）、限定作用域改写（P2，**0.8511**，低于 R2 基线会被回退）三个原则版本下，norrin、FALDH、abnormal retinal vascular development 三个焦点漏标**均未恢复**，spasticity 均修复。结论：指南中与 gold 相反的排除示例是模型上游判断的**症状而非成因**——模型在这些 definitional/characterization 语境中本就不把这些短语读作疾病提及，限制条款的写法改变不了该判断；该从句的真实功能是压制 DiseaseClass 过度扩张的精度护栏（P1 删除后 S→D 类型错误 2→4）。详见 [P1 报告](todo-temp/p1/20261006_p1_truncated_clause_report.md)与 [P2 报告](todo-temp/p2/20261007_p2_scoped_clause_report.md)。下一步方向从"修改限制措辞"转向"更具体的语言模式原则 / 正例演示的代价权衡 / CONSTRAINT 通道承载"。

**2026-10-07，P3 Top-K 对比补全：** dev 终点 0.9155 的 top-4 指南实测 valid100 F1 **0.8023**（top-1 0.7878、原指南 0.7792），增益几乎全部来自 Modifier 召回（TP +26）；dev 上 0.9155 vs 0.9091 的差距在 dev10 噪声带内，valid 的 +0.0145 才是有效证据但仍是单点估计。吸收率 32% 反低于 top-1 的 41%，排除"更多硬编码"解释。两个 gold 相反排除示例在 top-4 终版指南中同样存在，且查证 top-4 第 1 轮分析调用已展示 FALDH/retinal-vascular 的 gold 标签仍照写排除——输入侧加证据也防不住，缺口定位在 refine_guidelines 调用看不到带标签的 discrepancy 证据。详见 [P3 报告](todo-temp/p3/20261007_p3_topk4_report.md)。

**2026-10-08，P4 规模对比完成（全部离线，无新运行）：** 三项结论：① 勘误——三次规模运行 n_examples 实际均为 5，"示例数 5/10/15 混杂"不存在；② 假设的硬编码端成立（吸收率 41%→9%→3% 单调塌缩），泛化端不成立——valid 0.7878/0.7745/0.8050 非单调，配对 bootstrap 显示所有臂间差 95% CI 跨 0（仅 dev30 vs 原指南 +0.026 达 97.1% 单侧），且吸收率低 ≠ valid 好（dev20 反例）；③ dev30 指南在拥有 norrin 文档的情况下仍写出其扁平排除——规模不解决 gold 相反排除，与 P3 §3.4 的结构定位一致。dev20/dev30 replicate 两臂已设计但按用户决定不执行，轨迹方差未知是主要保留。详见 [P4 报告](todo-temp/p4/20261007_p4_devsize_report.md)。**至此 2026-10-02 seminar 的五项 Todo（P0–P4）全部关闭。**

**2026-10-09，seminar 汇报 P0–P4，导师反馈确定下一阶段重点：** 会上报告了五项核查结果（R4 逐例变化、P1/P2 三臂对照、Top-4 valid100、规模对比）。导师的核心要求是**逐例解释"新规则为什么没有修复目标错误"**，而不是继续扩大实验规模：R4 针对 3 个 S→O 漏标只修复 1 个，需逐案例串起"原文/gold/R3 预测 → discrepancy 解释 → 新 principle → R3→R4 指南 diff → 最终预测"的规则链，并做隔离对照（新 principle 单独重标目标案例 vs R4 完整指南），以区分修复条件不足、规则冲突与整合失真；同时解释为什么针对漏标的规则主要改变了其他类型（2 个 M→S 修复、1 个 S→D 新增回归）。术语修正：safety clause 改称 **exception rule**；流程图须区分 gold annotation 与 TP，gold 来源直接指向原始 gold 数据。Top-4 收益（recall/Modifier 驱动、precision 未改善）需重复实验确认显著性；导师提醒 FP 增加可能反映"尽量标成实体"的标注偏置。两个下一步方向获认可：refinement 阶段注入目标错误案例的 gold（输入侧）、reviewer 写后冲突检查（输出侧）；pattern explanation 阶段可直接使用原始 gold annotation（含正确案例）。下次 seminar 拟邀请 Ken 与 Kim 教授，候选时间 10/15、10/16、10/19 上午、10/20，本周收集可用性。

**2026-10-14，新 P0 规则链与隔离对照完成（10/16 seminar 前）：** 计划见 [RP](docs/RP/20261014_r4_failure_attribution_plan.md)。

[规则链](todo-temp/r4-rule-chain/20261014_r4_rule_chain_report.md)显示 R4 的三个目标属于三种情况：

- **FALDH**：规则冲突。新规则放行，指南却有三处点名排除，其中一处是 R4 改写时新增的。
- **G6PD**：修复条件不足。
- **PAH**：这次"修复"其实是撤销 R3 exception rule 造成的回归。

与 gold 相反的点名排除，全部出自"不许破坏的示例"区块中被展示的文档。这个区块按样本顺序取前 5 篇有 TP 的文档，展示全文，不标记 FN；改写指南这一站看不到任何 gold。dev30 中 FALDH 的文档没有被展示，指南就从未点名它。

[隔离对照](todo-temp/r4-isolation/20261014_r4_isolation_report.md)（36 次，GPT-5.4 high）的结果：

- **FALDH**：在"标签定义＋原则"条件下，3 次都被当作疾病标注（2 次 SpecificDisease，跨度含缩写；1 次 CompositeMention）。用 R4 完整指南为 0/3。去掉原则的 exception rule，结果不变。
- **G6PD**：四组都没有标对。去掉 exception rule 后，模型只是改为把 "enzyme deficiency" 标成 DiseaseClass。
- **PAH**：R3 指南下 0/3，R4 指南下 3/3。

据此修正 2026-10-07 "排除示例是症状而非成因"的表述：不给完整指南时，模型会标出 FALDH，障碍在完整指南之内。

追加对照 ③− 随后确认了障碍所在：R4 指南只删去点名 FALDH 的三处文字，FALDH 3/3 精确恢复，整篇 14/0/0，没有其他回归。

至此形成完整的证据链：

1. 改写指南这一站看不到 gold，却能看到示例文档全文。
2. 它把未标注的 FALDH 写成了"不标注"。
3. 这些文字阻止了新规则对 FALDH 的修复。

这直接支持 10/09 seminar 认可的两个方向：给 refinement 提供 gold（方案 A），以及写后冲突检查（方案 B）。norrin 的点名排除没有做删除实验；改写那一站为什么这样写，仍是假设。

保留意见：每格只有 3 次重复，只覆盖 3 篇开发文档；"方向正确"的口径是看过第 1 轮结果后才明确的。

**2026-10-15，R4 非目标变化不能归因于新 principle：**

- Tay-Sachs disease、TSD 的 M→S：用同一份 R4 指南重跑 5 次全是 M，R3 指南下也是 5 次 M。原 run 的 S 是不能复现的单次翻转。
- cutaneous vasculitis 的 S→D：原指南不变时 5 次中 2 次为 S，属于波动。

这对第三条优化轴（可靠评价）是直接证据。其他预测不变、只把这两处换成重跑中的 M，R4 的 dev F1 为 0.8811，低于 R3 的 0.8873，按循环规则 R4 本应被回退。R4 能复现的修复只有 PAH 一处。也就是说，接受或回退一轮修改的决定，可能被单次标注波动左右。

同日完成的规则链补充：

- Guideline Refinement 收到的 verified examples 是按文件名排序后的前 5 篇文档。FALDH 的文档排第 4，所以每轮都会出现，与内容无关。
- 提示声明这些文档"currently handled CORRECTLY"，又要求"prioritize specific sub-cases to avoid regression"。这与 FALDH 被写成点名排除的过程一致，但属于推断。
- 论文 §3.4.4 说这一步还会收到 discrepancy context，现有实现没有传入。

10/16 seminar 的 slides 见 `../presentations/20261016_faldh_attribution_en.pptx`（slides 统一放在 `修論/presentations`），生成脚本为 `todo-temp/r4-isolation/build_faldh_slides.py`；非目标变化另成一份 `../presentations/20261016_r4_secondary_effects_en.pptx`，生成脚本为 `todo-temp/r4-nontarget/build_secondary_effects_slides.py`。

## 后续记录方式

实验后，LOG 新增一行，PROGRESS 记录它对三条优化轴、阶段目标和当前决策的影响，并更新文档底部的 Todo。负结果和中断同样保留。

seminar 后，将会议要点及其对研究主线的推进融入对应日期的历史进展，随后更新底部 Todo。每次保留未完成项，也检查短期任务是否仍服务于方法优化和长期标注目标。OVERVIEW 只在研究目标、方法或评价定义变化时更新。

## 下次 seminar 前的 Todo

已关闭的一组来自 [October 2 会议摘要](archive/2026-10-02_seminar-conflict-casestudy/seminar_oct2.md)（保留原优先顺序，均已完成）；当前进行中的一组来自 2026-10-09 seminar，列在本节末尾。注意两组的 P0–P4 编号含义不同，引用时不要混淆。

- [x] **P0：核查 Round 4 标注变化与回归。** 已复算整体及类别指标，整理混淆矩阵和逐例历史，区分已有错误、目标修复与新增回归。见 [P0 报告](todo-temp/p0/20261006_round4_p0_report.md)。
- [x] **P1：检验限制条款。** 已完成单变量对照（2026-10-06）：截短 R3 原则的 "do not apply" 从句后，原 41–44 行扁平排除消失，但模型自行再生等效条件限制，norrin/FALDH/abnormal development 无一恢复；dev F1 0.8671 低于原原则的 0.8873，S→D 类型错误翻倍。假设未证实，问题指向限制条款的写法与作用域而非其存在本身。见 [P1 报告](todo-temp/p1/20261006_p1_truncated_clause_report.md)。
- [x] **P2：改写作用域。** 已完成（2026-10-07）：限定改写使 FALDH 排除从扁平变为条件式，且未再生额外排除示例，但焦点漏标仍无一恢复；dev F1 0.8511 低于 R2 基线，按循环规则会被回退。结合 P1 的三臂证据：漏标近因是标注模型的上游判断，不是限制文本。见 [P2 报告](todo-temp/p2/20261007_p2_scoped_clause_report.md)。
- [x] **P3：整理并补充 Top-K 对比。** 已完成（2026-10-07）：0.9155 那次 top-4 指南 valid100 实测 F1 **0.8023**（top-1 0.7878、原指南 0.7792），增益集中于 Modifier 召回；吸收率 32% 低于 top-1 的 41%，硬编码解释被排除；两个 gold 相反排除示例仍在，且查明输入侧给 gold 证据也防不住。见 [P3 报告](todo-temp/p3/20261007_p3_topk4_report.md)。
- [x] **P4：汇报 10/20/30 篇规模对比。** 已完成（2026-10-08，全部离线）：吸收率随规模单调塌缩（41%→9%→3%）但 valid 非单调且臂间差均在噪声内（bootstrap）；dev30 仍写出 norrin 的 gold 相反排除——规模解决硬编码、不解决冲突示例；n_examples 误记勘误（实际均为 5）。replicate 两臂已设计未执行。见 [P4 报告](todo-temp/p4/20261007_p4_devsize_report.md)。

**本轮交付：** 逐例变化表、Round 4 混淆矩阵，以及原规则、删除限制、限定作用域三个版本的对比（P0–P4 已完成，seminar 五项 Todo 全部关闭）。**与整体目标的连接：** 三臂对照显示规则措辞路径对焦点漏标无效，P3/P4 进一步显示加证据（top-k、加数据）也防不住 gold 相反排除；共同缺口定位在 refine_guidelines 调用看不到带标签的 discrepancy 证据。若提出新的承载方式（gold 证据注入 rewrite 步、写后对照校验、CONSTRAINT 通道），需先在小样本验证可复用收益，再扩大评价，检查整体 validation 收益与稳定性，推动向 SOTA 目标前进。改善一个开发案例不直接视为达到阶段目标。

### 2026-10-09 seminar Todo（当前进行中；与上方已关闭的 10-02 五项不是同一组编号）

下次汇报的重点是解释"新规则为什么没有修复目标错误"，不是继续扩大实验规模。

**新 P0（下次 seminar 必做）：逐例定位失败环节。**

- [x] （2026-10-14 完成：与 3 个 gold 相反案例只在 FALDH 重合，未修复案例共 4 个，加上已修复的 PAH；见[规则链报告](todo-temp/r4-rule-chain/20261014_r4_rule_chain_report.md)）追踪 R4 后仍存在的 2 个 S→O 漏标（FALDH、deficiency in G6PD）；此前 3 个 gold 相反排除案例先按 case ID 核对重合（FALDH 重叠），保留完整句子与上下文。已有基础：P0 报告的逐例历史与 R4 diff 对照、P3 §3.4 的 gold 可见性核查，新增工作是归因与隔离实验，避免重复劳动。
- [x] （2026-10-15 完成：两类变化都不能归因于 R4 新 principle。Tay-Sachs/TSD 用 R4 指南重跑 5 次全是 M，原 run 的 S 不能复现；cutaneous vasculitis 在原指南不变时 5 次中 2 次为 S，属于波动。见[非目标变化报告](todo-temp/r4-nontarget/20261015_r4_nontarget_report.md)）解释 R4 非目标变化：为什么针对漏标生成的规则主要修复了 2 个 M→S（Tay-Sachs/TSD）并新增 1 个 S→D 回归。
- [x] （2026-10-14 完成：FALDH 为规则冲突，G6PD 为修复条件不足，PAH 为撤销 R3 副作用）逐案例串规则链：原文/gold/R3 预测 → discrepancy explanation → 新 principle → R3→R4 guideline diff → 最终预测；归类为修复条件不足（principle 太抽象）、规则冲突（新规则允许但例外仍禁止）或整合失真（principle 可用但写入时被改写弱化）。交付物是"案例—具体条款—预测变化"证据，不只是总体分数。
- [x] （2026-10-14 完成，另加 ②b"去掉 exception rule"；见[隔离对照报告](todo-temp/r4-isolation/20261014_r4_isolation_report.md)；追加 ③− 已完成：删去三处点名排除后 FALDH 3/3 恢复）隔离对照（会上提出）：同模型同生成设置，用 ①R3 指南 ②标签定义＋新 principle（不进完整指南） ③R4 完整指南 三种条件重标 3 个原 S→O 案例；重标阶段不给 annotator gold，gold 仅用于事后评分。结果读法：principle 单独有效而整合无效 → 优先查规则冲突与整合；单独也无效 → 查 discrepancy explanation 与 principle 内容；相同条件下结果不稳 → 先少量重复，避免把随机变化当成规则效果。
- [ ] 汇报材料：逐例对照表（原始错误、新 principle、最终相关条款、重标结果、判断依据）＋关键 guideline diff（只标真正影响目标案例的修改）＋明确区分已观察现象、实验支持的解释、尚未验证的假设。

**新 P1（完成定位后有时间再测）：流程改进，一次只改一个输入位置。**

- [ ] 方案 A（输入侧）：refinement 阶段提供目标错误案例对应的 gold；区分两种用途——错误案例的 gold（修复用）与此前的 TP gold（防回归）；pattern explanation 阶段可直接使用原始 gold annotation（含正确案例，帮助理解类别边界，会上已确认），不必另造集合。
- [ ] 方案 B（输出侧）：reviewer 冲突检查，至少输出受影响案例、冲突条款、冲突来源（允许条件/排除条件/类别定义）；先验证能否可靠发现问题，再考虑"反馈 → 再 refinement"自动循环；reviewer 自述"已修复"不算数，必须重新标注验证目标错误与回归。
- 边界：以上均为待测方向而非已确认方案；用于改规则的 gold 只能来自 dev，不能把独立评估集答案引入 refinement。

**新 P2：补充验证与表达修正。**

- [ ] Top-4 按原计划补 2 次重复实验确认收益稳定；同时报告 precision/recall/F1 与类别变化，检查收益是否主要来自 Modifier、FP 是否增加、是否只是"倾向标成实体"的标注偏置而非类别边界改善。
- [ ] 术语与图表：safety clause → exception rule；区分 gold annotation 与 TP；流程图标明各阶段实际收到的文本/预测/gold/抽象解释，gold 箭头直接来自原始 gold 数据；模糊词 "recovered" 改为明确表述（如"目标漏标恢复数：0/3"）。
- [ ] 引入 gold 后继续关注 hard-coding，不靠把答案写进指南换 dev 提分；暂缓继续扩大 dev set（当前更缺错误机制证据）。

**新 P3：会议协调。**

- [ ] 收集 Ken、Kim 教授可用时间（候选：10/15 周四、10/16 周五、10/19 周一上午 10–13 时、10/20 周二），确定下次 seminar 安排。
