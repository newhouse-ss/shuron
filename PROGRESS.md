# 研究进展

更新：2026-11-03。这里沿研究主线记录阶段成果、判断变化和下次 seminar 待办；逐次实验见 [LOG.md](LOG.md)，固定背景及评价口径见 [OVERVIEW.md](OVERVIEW.md)。

**2026-10-30，已保存理由的离线核查完成。** [正文第 8 节](todo-temp/error-analysis/reports/20261024_error_analysis_report_zh.md)与附录 J 增加 16 条预测的逐例探索，完整证据在 `todo-temp/error-analysis/outputs/20261030_rationale_audit/`。全部 30 次验证集运行的请求及预测来源已准确核对。理由与标签自洽仍可能与 gold 不同，边界取舍也常未被理由解释；分类前提不能确定的案例继续保留为未定。16 条是工作量上限，不代表全体比例或改写效果；未追加标注、修改指南或启动方法实验，也不据此关闭“全部错误分类”的待办。

## 总体主线与阶段目标

**在标注资源稀少、还不足以训练监督模型的阶段改进 guideline refinement：Track 1 让直接使用、不经人工修正的 LLM 标注质量更高；Track 2 在构建 benchmark 需要专家修正时，以 FP 换取更少的 FN，减少专家的修正量。**

这是本研究的总体方向，2026-10-20 会议后确定，取代 10-06 的“先逼近 SOTA、再替代或部分替代专家标注”；计划见 [RP v4](docs/RP/20261020_research_plan_v4.md)。此前的 hard-coding、规则冲突、Top-K 和开发数据规模分析，都是这条路线上的方法诊断。研究脉络来自 [中期 abstract](archive/2026-08-31_midterm-abstract/47256388_周恒宇_要旨.pdf)，第 1 至 2 页。

| 阶段 | 要解决的问题 | 当前位置 |
| --- | --- | --- |
| 复现与诊断 | 原指南及 refinement 能改善什么，提升被哪些环节限制？ | 已复现并开展诊断，发现开发收益、泛化收益与稳定性并不一致。 |
| 方法优化 | 如何从少量标注证据学习可复用规则，合理整合新旧指南，并减少修改副作用？ | 当前主要阶段，三条优化轴已有探索，规则作用域是本轮重点。 |
| Track 1：直接使用的标注质量 | 在 Haiku 上复现主要结果，对全部错误分类，再针对占比最高的错误类别改进方法 | 复现完成（10/23）：Haiku 上 top-4 比原指南 +0.0067 [−0.0145, +0.0279]，两种方法都没有证明比原指南好。错误分析第一版已在 10/30 汇报：Modifier 的收益和误标已对到条文，Specific、DiseaseClass 的损失还没查；下一步是把条文和结果模式对应起来。四子类型严格 F1 只和主论文比（0.73 / 0.76）；单一类型 F1 对照监督 SOTA（NEEDLE 0.9228）只作参照。 |
| Track 2：构建 benchmark 时的修正量 | 改进方法，让指南以更多 FP 换更少 FN，同时保持 F1；从标注者修正是否更容易的角度讨论 | 方法还没开始。10/23 seminar：与 Track 1 同样必要，不是补充分析；不用重复运行投票实现（那只利用 LLM 输出的随机性）。错误分析显示 FN 与真正漏标两种口径的结论不同，主指标待定。 |

两条 track 对应 10/20 会议提出的两种场景：并非所有标注都需要专家修正，需要的主要是构建 benchmark；越来越多的场景直接使用 LLM 标注。补漏标必须通读全文，和手工标注没有区别，所以 Track 2 以 FN 为主指标。没有现成的专家标注，两条 track 都以 gold 为参照；计时的专家实验列为未来工作。不主张 LLM 可以替代独立标注者。10/23 seminar 确认两条 track 都必要；计时实验不需要，"漏标贵、多标便宜"作为说明清楚的假设来论证。

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

同期开展 10/20/30 篇规模实验，validation F1 为 **0.7878/0.7745/0.8050**。各规模只有一条已报告 refinement 轨迹，尚不能隔离规模的作用。2026-10-08 勘误：三次运行的 n_examples 实际均为 5（resolved config 与 prompt 实测，见 [P4 报告](todo-temp/p0-p4/p4/20261007_p4_devsize_report.md)），此前"示例上限 5/10/15"为误记，规模对比不含示例数混杂。固定指南五次重复标注的 F1 标准差为 **0.01502/0.00978/0.00921**，提示需要把评价波动纳入方法优化。

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

**2026-10-06，P0 核查完成：** Round 4 开发 F1 从 0.8873 升至 0.9091，逐实体为 3 个修复、1 个新增回归；目标簇仅修复 1/3。norrin 与 FALDH 是较早存在的漏标，不能归为本轮新增回归。完整逐例变化和混淆矩阵见 [P0 报告](todo-temp/p0-p4/p0/20261006_round4_p0_report.md)。作用域的因果解释仍待 P1/P2。

**2026-10-07，P1/P2 三臂对照完成：** 原从句（dev F1 **0.8873**）、删除从句（P1，**0.8671**）、限定作用域改写（P2，**0.8511**，低于 R2 基线会被回退）三个原则版本下，norrin、FALDH、abnormal retinal vascular development 三个焦点漏标**均未恢复**，spasticity 均修复。结论：指南中与 gold 相反的排除示例是模型上游判断的**症状而非成因**——模型在这些 definitional/characterization 语境中本就不把这些短语读作疾病提及，限制条款的写法改变不了该判断；该从句的真实功能是压制 DiseaseClass 过度扩张的精度护栏（P1 删除后 S→D 类型错误 2→4）。详见 [P1 报告](todo-temp/p0-p4/p1/20261006_p1_truncated_clause_report.md)与 [P2 报告](todo-temp/p0-p4/p2/20261007_p2_scoped_clause_report.md)。下一步方向从"修改限制措辞"转向"更具体的语言模式原则 / 正例演示的代价权衡 / CONSTRAINT 通道承载"。

**2026-10-07，P3 Top-K 对比补全：** dev 终点 0.9155 的 top-4 指南实测 valid100 F1 **0.8023**（top-1 0.7878、原指南 0.7792），增益几乎全部来自 Modifier 召回（TP +26）；dev 上 0.9155 vs 0.9091 的差距在 dev10 噪声带内，valid 的 +0.0145 才是有效证据但仍是单点估计。吸收率 32% 反低于 top-1 的 41%，排除"更多硬编码"解释。两个 gold 相反排除示例在 top-4 终版指南中同样存在，且查证 top-4 第 1 轮分析调用已展示 FALDH/retinal-vascular 的 gold 标签仍照写排除——输入侧加证据也防不住，缺口定位在 refine_guidelines 调用看不到带标签的 discrepancy 证据。详见 [P3 报告](todo-temp/p0-p4/p3/20261007_p3_topk4_report.md)。

**2026-10-08，P4 规模对比完成（全部离线，无新运行）：** 三项结论：① 勘误——三次规模运行 n_examples 实际均为 5，"示例数 5/10/15 混杂"不存在；② 假设的硬编码端成立（吸收率 41%→9%→3% 单调塌缩），泛化端不成立——valid 0.7878/0.7745/0.8050 非单调，配对 bootstrap 显示所有臂间差 95% CI 跨 0（仅 dev30 vs 原指南 +0.026 达 97.1% 单侧），且吸收率低 ≠ valid 好（dev20 反例）；③ dev30 指南在拥有 norrin 文档的情况下仍写出其扁平排除——规模不解决 gold 相反排除，与 P3 §3.4 的结构定位一致。dev20/dev30 replicate 两臂已设计但按用户决定不执行，轨迹方差未知是主要保留。详见 [P4 报告](todo-temp/p0-p4/p4/20261007_p4_devsize_report.md)。**至此 2026-10-02 seminar 的五项 Todo（P0–P4）全部关闭。**

**2026-10-09，seminar 汇报 P0–P4，导师反馈确定下一阶段重点：** 会上报告了五项核查结果（R4 逐例变化、P1/P2 三臂对照、Top-4 valid100、规模对比）。导师的核心要求是**逐例解释"新规则为什么没有修复目标错误"**，而不是继续扩大实验规模：R4 针对 3 个 S→O 漏标只修复 1 个，需逐案例串起"原文/gold/R3 预测 → discrepancy 解释 → 新 principle → R3→R4 指南 diff → 最终预测"的规则链，并做隔离对照（新 principle 单独重标目标案例 vs R4 完整指南），以区分修复条件不足、规则冲突与整合失真；同时解释为什么针对漏标的规则主要改变了其他类型（2 个 M→S 修复、1 个 S→D 新增回归）。术语修正：safety clause 改称 **exception rule**；流程图须区分 gold annotation 与 TP，gold 来源直接指向原始 gold 数据。Top-4 收益（recall/Modifier 驱动、precision 未改善）需重复实验确认显著性；导师提醒 FP 增加可能反映"尽量标成实体"的标注偏置。两个下一步方向获认可：refinement 阶段注入目标错误案例的 gold（输入侧）、reviewer 写后冲突检查（输出侧）；pattern explanation 阶段可直接使用原始 gold annotation（含正确案例）。下次 seminar 拟邀请 Ken 与 Kim 教授，候选时间 10/15、10/16、10/19 上午、10/20，本周收集可用性。

**2026-10-14，新 P0 规则链与隔离对照完成（10/16 seminar 前）：** 计划见 [RP](docs/RP/20261014_r4_failure_attribution_plan.md)。

[规则链](todo-temp/r4-attribution/rule-chain/20261014_r4_rule_chain_report.md)显示 R4 的三个目标属于三种情况：

- **FALDH**：规则冲突。新规则放行，指南却有三处点名排除，其中一处是 R4 改写时新增的。
- **G6PD**：修复条件不足。
- **PAH**：这次"修复"其实是撤销 R3 exception rule 造成的回归。

与 gold 相反的点名排除，全部出自"不许破坏的示例"区块中被展示的文档。这个区块按样本顺序取前 5 篇有 TP 的文档，展示全文，不标记 FN；改写指南这一站看不到任何 gold。dev30 中 FALDH 的文档没有被展示，指南就从未点名它。

[隔离对照](todo-temp/r4-attribution/isolation/20261014_r4_isolation_report.md)（36 次，GPT-5.4 high）的结果：

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

10/16 seminar 的 slides 见 `../presentations/20261016_faldh_attribution_en.pptx`（slides 统一放在 `修論/presentations`），生成脚本为 `todo-temp/slides/build_faldh_slides.py`；非目标变化另成一份 `../presentations/20261016_r4_secondary_effects_en.pptx`，生成脚本为 `todo-temp/slides/build_secondary_effects_slides.py`。

**2026-10-16，seminar 反馈与当日离线核查：** 教授提出两项检验，原文见底部 Todo。

- 第二项的前提已离线核对：E1 能控制的输入和设置都与 08/02 原 run 相同；无法做到相同的只有模型版本（原 run 未记录）和模型自身的随机性。见[复现一致性核查](todo-temp/r4-attribution/nontarget/20261016_replay_identity_report.md)。
- 23 次重跑与原 run 相比，差别和重跑之间的差别处在同一水平。例外只有两处，而两处都是因为原 run 的结果特别才被挑出来的：R4 下的 Tay-Sachs/TSD，以及 R3 下的 PAH。R3 下 PAH 原 run 未标，重跑 3/3 是跨度正确的 DiseaseClass，两者都不算对。
- 对研究主线的含义：要说某一处"被规则改变"，必须先重复确认，单次标注不够。这与 10/15 关于"接受或回退一轮修改的决定可能被单次波动左右"的判断一致。
- 第一项已完成设计，未运行，设计稿已于 10/20 并入[结果报告](todo-temp/r4-attribution/isolation/20261017_r3_minus_faldh_report.md)（原文见提交 d86ea17）。10/17 已运行，见下。

**2026-10-17，R3 删去点名排除仍修不好 FALDH；FALDH 归因到此收尾：**

- R3 指南删去点名 FALDH 的两处后，5 次都没有标出 FALDH；同批 R3 原样对照 0/3，其余 13 个 gold 每次都对。10/14 里 R4 删去点名排除后是 3/3（Fisher 单侧 p ≈ 0.018，跨日比较，两天的 R3 对照一致）。见[结果](todo-temp/r4-attribution/isolation/20261017_r3_minus_faldh_report.md)。
- 对研究主线的含义：只去掉点名排除不够，R4 新 principle 写进指南的内容是修复 FALDH 的必要条件。连同 10/14 的"标签定义＋原则"3 次都当作疾病标注、③− 3/3 精确恢复，以及 PAH 在 R3 下 0/3、R4 下 3/3，可以说 R4 的 principle 对"缺乏/活性降低＋具体分子"这类漏标有用。FALDH 没修好，原因在改写这一站加入的点名排除（规则冲突），不在 principle 本身。
- 口径限制：只对 FALDH、PAH 两例成立，单一模型；G6PD 在 R4 下仍未修复；R4 这一轮的 dev F1 提升本身不能复现（10/15）。
- 决定不运行追加条件（删 R3 第 12 行的 "a molecular/substance entity or its level/activity"）。它只能区分 R4 里起作用的是收窄旧 exception rule（第 14 行），还是新增的正向规则（第 12 行）。两处都是按同一条 principle 写入的，所以不影响上面的结论。规则链显示 PAH 在 R3 的丢失与第 12 行同时发生，这与"第 12 行是 FALDH 的第二道阻挡"的推测一致，但这一点没有检验。

**2026-10-19, preparation for the 10/20 meeting (Prof. Goto, Kon Woo Kim, Prof. Kim); offline only:**

- Validation error breakdown of the saved runs ([error breakdown](todo-temp/plan-v3/error_breakdown_output.txt)). With the top-4 guideline (strict F1 0.8023), the largest single loss is subtype confusion between SpecificDisease and DiseaseClass (21 each way; F1 0.8750 if all subtype errors were fixed by gold), then boundaries (0.8597), missed mentions (0.8429) and extra mentions (0.8260). Ignoring subtypes, the same predictions score 0.8546.
- Midterm point 4 has lower priority now: missed Modifier is 27 of 208 disagreements with top-4 (13%), against 40 with the base method.
- Simulated expert bound: checking each of the 777 predicted entities with gold reaches 0.9606. This frames the new annotation-reviewer direction (an LLM second pass, measured between the model alone and this bound).
- Target check: no source gives BioBERT 0.86 on NCBI Disease. Zhao and Goto 2025 (Table 4) report BioBERT-Large 0.897 with one Disease type on a different test split. The 0.86 in OVERVIEW is left unchanged until the user decides; the meeting deck uses 0.897 with its source.
- Deck (10/20 meeting, rebuilt on 10/20 from plan v3): `../presentations/20261020_progress_and_plan_en.pptx`, builder `todo-temp/slides/build_plan_v3_slides.py`. The 10/19 draft deck and its builder were deleted.

**2026-10-19 (later), direction research and plan v2; offline only:** [report](todo-temp/plan-v3/evidence_notes.md), plan v2, superseded on 10/20 by plan v3 and after the meeting by [plan v4](docs/RP/20261020_research_plan_v4.md); v1 and v2 were deleted.

- No refined guideline is yet proven better than the original on valid100: top-4 minus original +0.0231, 95% interval [−0.0192, +0.0683]. The same R4 guideline annotated twice gave 0.7878 and 0.7789. Four refined loop finals (top-1 run 3, top-4 runs 1 to 3) were never scored on validation; scoring them is the cheapest test of top-4 as a method.
- Subtype confusion (largest loss) is convention, not noisy gold: 20 of top-4's 34 same-span S/D confusions go against consistent training precedent. It is guideline-sensitive (14 to 58 across guidelines), and refinement created part of it (two cancer patterns, 3 to 16).
- Aggregation and routing are the strongest free levers: a vote over the 8 saved runs gives 0.8158 (+0.0366 [+0.0059, +0.0699] over original); checking the 20% / 30% least-agreed entities gives 0.887 / 0.911 with gold as the expert (random order 0.834 / 0.850).
- Ruled out offline: document-level label propagation (−0.039 / +0.001) and lexical precedent (+0.017 even with 563 documents).
- Plan v1 review: protocol kept, allocation changed. Track 1 targeted mechanisms with near-zero validation footprint and could only detect differences of about 0.028. Plan v2 starts with a fine-tuned yardstick on the same split (no source supports BioBERT 0.86 on NCBI Disease; no four-subtype supervised result found), scores existing guidelines, retrofits the gold-consistency check (arm 3 merged into it: gold as a check, not as writing material), pilots a subtype typing pass, and makes the review-effort curve the replacement result, with one final evaluation on the official test split if the authors agree. Core cost estimate ¥61,000 to ¥98,000 on GPT-5.4.
- The base paper is now public (arXiv 2605.20809, ACL 2026 main) and can be cited on slides.

**2026-10-20，会议（後藤教授、Ken、Kim 教授）与会后计划 v4：**

会议用 [deck](../presentations/20261020_progress_and_plan_en.pptx) 汇报了以中期发表为基线的 plan v3。会上的意见：

- 後藤教授、Kim 教授：不是所有标注都需要专家修正，需要修正的主要是构建 benchmark；越来越多的场景直接使用 LLM 标注，不做修正。
- Kim 教授：专家最终要通读全文；删多标便宜，补漏标与手工标注无异；有调节精确率和召回率的参数，就往高召回调。
- 後藤教授：一个案例分析不够写成论文，要建立覆盖全部错误的分类体系；结论要说明与传统 ML 或微调相比，本方法只需要少量标注。
- Ken：原方法的其他步骤（discrepancy 分类、principle 生成）也可以改；top-4 的区间包含 0；换新模型重跑，结论不变即可；手上没有专家标注。
- 测试集、标注费用、与 Ken 当前工作的边界，会上没有谈到，待邮件确认。

会后确定（[RP v4](docs/RP/20261020_research_plan_v4.md)）：
- 按场景分两条 track：Track 1 提高直接使用的标注质量；Track 2 以 FP 换 FN，减少专家修正量。
- 新实验全部在 DeepSeek V4.1 flash 上进行。顺序是：稳定性测试 → 复现 → 在 DeepSeek 输出上做错误分类体系和 Track 2 取舍曲线 → 按分类结果选定 Track 1 的改动。GPT-5.4 不再运行，也不再在它的输出上做新的分析。
- 计时的专家实验不做，列为未来工作。
- OVERVIEW 和 CLAUDE.md 中的“BioBERT 0.86”目标已删除。

会议的 Todo 写在 Notion 页面 “10/20 meeting summ & todo”，下方也有一份副本。

**2026-10-21，DeepSeek 稳定性测试（RP v4 第 1 步）完成：** 结果见 [报告](todo-temp/deepseek-stability/report_run_output.txt)，20 次的 SD 与重复次数规划见 [plan_next_step_output.txt](todo-temp/deepseek-stability/plan_next_step_output.txt)。

- **设置选定开 thinking。** 关 thinking 即使 temperature 0 也不稳定：dev10 F1 均值 0.2583，50 次调用中 6 次失控。开 thinking 高出 +0.5585，95% CI [0.377, 0.740]。
- **开 thinking 的标注噪声：** 原指南 20 次，dev10 F1 均值 0.8062，SD 0.0194（真实 SD 的 95% 范围 0.0147 至 0.0283，GPT-5.4 的 0.0150 在范围内）。
- **对循环的含义：** 同一指南跑两次，后一次更高的比例是 46.6%。循环按单次 dev10 分数决定是否接受一轮，对什么都没改的候选也接近五五开。复现照原方法保留这条规则；它是"可靠评价"一轴的 Track 1 候选，等第 3 步分类后再定。
- **稳定的错误，不是噪声：** Tay-Sachs disease、TSD 16/20 次标成 Modifier；FALDH、norrin、G6PD 20/20 漏标。留给第 3 步的分类体系。
- **标签名归一：** DeepSeek 有时照抄指南里的 "Specific Disease"，pipeline 现在把去掉空格后等于 schema 名的标签改回 schema 名。
- **费用：** 实际约 ¥303。开 thinking 的一次 dev10 标注调用非高峰约 ¥1.27、47 秒，低于 RP v4 按 GPT-5.4 输出长度的估算。循环内的其他调用（discrepancy、principle、改写）还没测过。

**2026-10-22，Claude Haiku 5.5 试验（dev10，Batch API）：** 起因是 DeepSeek 高峰时段价格翻倍。结果见 [报告](todo-temp/haiku-trial/report_output.txt)。

- **质量：** 同一 prompt、文档和评分下，Haiku 的 dev10 F1 比 DeepSeek 开 thinking 低约 0.045（high 0.7615、xhigh 0.7605，对 0.8062，p < 0.0001）。差距主要来自漏标（每次 FN 约 22，对 17），精确率相同（约 0.84）。漏标多对 Track 2 不利。
- **effort：** high 与 xhigh 没有显著差别（p 0.88），按事先规则选 high。xhigh 的分数更稳定（SD 0.0150 对 0.0240），但每次调用贵约六成。
- **费用与速度：** Batch 价每次调用 high ¥0.315，约为 DeepSeek 非高峰价（¥1.27）的四分之一；400 个请求 7 分钟完成，循环按步骤成批提交可行。
- **稳定的错误：** FALDH、norrin、G6PD 与 DeepSeek 一样 20/20 漏标；PAH Haiku 20/20 漏标；Tay-Sachs disease、TSD Haiku 多数标对，DeepSeek 多数标成 Modifier。
- **单位精度的费用：** 达到同一显著性所需的钱约等于每次费用 × 方差。以 high 为 1，xhigh 为 0.81（FN）/ 0.63（F1），DeepSeek 为 2.99 / 2.62（[计算](todo-temp/haiku-trial/effort_efficiency_with_max_output.txt)）。xhigh 噪声更小只在 F1 上勉强显著（p 0.046），FN 上不显著（p 0.14）。
- **effort max（同日补测，[报告](todo-temp/haiku-trial/report_with_max_output.txt)）：** max 确实更好。在没有截断的 8 篇文档上，F1 比 xhigh 高 0.024（p 0.007），每次少漏标约 2 个（p < 0.0001），按事先规则选 max。但每次调用 ¥1.431，是 xhigh 的 2.8 倍，比 DeepSeek 非高峰还贵，分数仍显著低于 DeepSeek；噪声不比 xhigh 小。5% 的回复超过 64000 token 被截断，用于循环需要提高上限。
- **max 与 Modifier：** max 把 Tay-Sachs disease、TSD 多数标成 Modifier（17/20、13/20），与 DeepSeek（17/20、17/20）相同，high、xhigh 则多数标对。思考越多越倾向 Modifier，可能是指南条文本身的读法问题。
- **决定（用户，10/22）：** 主模型用 Haiku 5.5，effort xhigh，经 Batch API 提交。理由：同一精度所需的钱最低（约为 DeepSeek 的四分之一），漏标多、可改进的空间大；max 比 DeepSeek 还贵且分数更低。RP v4 第 4、5 节已按此修订。
- **复现的次数（10/22 更正）：** 之前的 E1 和循环次数是用 GPT-5.4 的 valid100 数据算的，违反了用户"不用 GPT 数据做决定"的要求，已撤回（相关脚本开头注明撤回）。用户定默认次数：E1 10 次、每种方法 10 个循环。费用只按 Haiku 实测价格和代码里的循环结构算：每个循环 1 轮时 3,520 次调用、约 ¥1,799，3 轮约 ¥2,126，5 轮约 ¥2,453，20 轮（上限）约 ¥4,906；分析调用按最大尺寸计时最多 ¥11,647（[计算](todo-temp/haiku-trial/cost_default10_output.txt)）。轮数和分析调用的价格都没测过。
- **下一步：** 循环和 valid100 脚本接入 Claude provider，支持同一方法的循环同步推进、每一步一个批次，以及重试和续跑；然后通知管理员（超过 ¥1,000）并请用户批准复现。
- **待定：** 是否在 DeepSeek 上跑同一方法，作为较强模型的对照（费用另算）。
- **批处理试跑（10/22，top-1、top-4 各 1 个循环）：** 两个循环同步推进可行，6 个批次共约 36 分钟，¥90.36。top-1 第 1 轮的候选未被采用（dev10 0.7591 对 0.7681，差距在噪声内），终版即原指南，valid100 严格 F1 0.6986，这是 Haiku 上原指南的第一个 valid100 数。top-4 的改写要合并 4 条原则，思考超过 64000 token，3 次都截断，循环失败。实测价格：valid100 标注每次 ¥0.634，高于 dev10 的 ¥0.511；分析调用每次 ¥0.11 至 ¥0.36；top-1 改写 ¥1.5。
- **输出上限（用户 10/22 定）：** 提高到 128,000（Haiku 5.5 的上限），两种方法今后一致；top-1 的回复都不到 37,500 token，不受影响。
- **重启时发现原代码的不确定性：** `iterative.py` 第 393 行按集合顺序列出正确标注的例子，集合顺序随 Python 进程的字符串哈希而变，所以同一个循环换一个进程时分析 prompt 不同。runner 现在固定 PYTHONHASHSEED 为 0，原代码不改。
- **top-4 续跑结果（各只有 1 个循环，不能下结论）：** 6 轮全部被采用，dev10 F1 0.7313 → 0.9583；valid100 严格 F1 0.7411（FN 237，FP 150）。top-1 循环的候选未被采用，终版就是原指南，所以它的 0.6986（FN 288，FP 146）是原指南在 valid100 上的一次标注，和 E1 测的是同一件事。这次实际比较的是 top-4 终版指南和原指南，不是两种方法；top-1 还没有产生过改动后的指南。差距 +0.0425 里混着 top-4 的效果和两种在 Haiku 上都没测过的变动：同一指南重新标注一次的变动（E1 的 10 次重复来测），以及另跑一个 top-4 循环会写出不同指南的变动（10 个 top-4 循环来测）。各只有 1 次时三者分不开。dev10 与 valid100 相差 0.217，说明指南大多是对这 10 篇的调整。
- **top-4 的指南膨胀：** 每轮改写都整篇重写指南，长度从 7,367 字符涨到 113,338 字符（15 倍），改写输出接近 128,000 token 的上限（第 5 轮 99.4%）。以后的 top-4 循环很可能在某一轮改写超出上限；`--stop-at-cap`（改写 3 次都被截断时按被拒绝的一轮结束）已实现并测试，是否启用待用户决定。
- **实测费用：** 1 轮的 top-1 循环 ¥76；6 轮的 top-4 循环 ¥199，其中 valid100 标注每次 ¥1.093（长指南使输入变大）。第 5 节按每次 ¥0.511 算的费用低估了 top-4，复现的费用需要按实测重算。

**2026-10-23，scope 确认 seminar：** [deck](../presentations/20261023_scope_confirmation_en.pptx)（生成脚本 `todo-temp/slides/build_scope_confirmation_slides.py`，生成后用户另有手改）。逐题问答与注意点见 [TODO](todo-temp/seminar-20261023/TODO.md) 第 ① 节。依据是会议录音的自动转写（没有说话人标注，有缺段）；第二语料一题的答案由用户补充。

- **两条 track 都必要（Q1）：** 教授不同意把 Track 2 作为补充分析，并说审稿意见也是这个方向。Track 2 不能靠重复运行投票，那只利用 LLM 输出的随机性；要在方法上改，让指南以更多 FP 换更少 FN，同时保持 F1，并从标注者修正是否更容易的角度讨论。计时的专家实验不需要。
- **错误分析先行（Q2、Q3）：** 只做一个改动是否足够、分析做多深，等错误分类出来后再谈。教授把错误分析与分类列为第一件事。
- **完成标准（Q4）：** 即使没有稳定的 F1 提升，讨论清楚改动的价值和局限即可。
- **模型与语料（Q5、Q6）：** 便宜的模型可以；较强模型的对照未定（实验室 API 只有 GPT-5.2、5.4）。实验必须在 NCBI Disease 上做，有时间再扩展到其他数据集。
- **费用（Q7）：** 未定。先问 DBCLS 能否提供 Claude API key；在此之前自己垫付。报销需要表格、收据和显示美元汇率的银行流水。
- **其他：** 投票那页解释了约 40 分钟，以后展示重复运行要先给"运行 × gold"矩阵并说明次数的依据；教授问到 top-2、top-3（都没跑过）；top-4 试跑的 +0.04 需要重复循环和 t 检验才能下结论；会后要写一份含统计检验的研究计划。
- **对研究主线的含义：** Track 2 从"在已有输出上分析 FN/FP 取舍"变成需要自己方法的研究目标，RP v4 中 Track 2 的投票阈值和取舍曲线要改写。复现（E1 与 top-1、top-4 各 10 个循环）不受影响。

**2026-10-23，复现完成（Haiku：原指南 10 次，top-1、top-4 各 10 个循环）：** [设计](todo-temp/seminar-20261023/reproduction_design.md)，[结果](todo-temp/seminar-20261023/reproduction_analysis_output.txt)。三个检验在运行前固定：Welch 双侧，各 5%。

| 比较 | 均值差 | 95% CI | p |
| --- | --- | --- | --- |
| top-1 − 原指南 | −0.0031 | [−0.0148, +0.0085] | 0.58 |
| top-4 − top-1 | +0.0098 | [−0.0120, +0.0316] | 0.35 |
| top-4 − 原指南 | +0.0067 | [−0.0145, +0.0279] | 0.50 |

- **三个都不显著。** 在 Haiku 上，两种 refinement 都没有证明比原指南好；区间排除了大幅提升：top-1 最多 +0.009，top-4 最多 +0.028。
- **top-1 基本不改指南：** 10 个循环中 8 个第 1 轮候选未采用，终版即原指南，所以 top-1 组几乎就是原指南的重复标注。
- **top-4 改了指南，但结果分散（描述，未检验）：** SD 0.029，约为原指南重复标注（0.010）的三倍。3 个循环高于所有原指南运行（0.7481、0.7441、0.7411），3 个低于所有原指南运行（0.6589、0.6855、0.6906）。
- **dev 提升不预示 validation（描述，未检验）：** 例如 top-4 loop06 dev10 0.774 → 0.849，validation 0.6855，低于所有原指南运行；loop09 dev10 0.768 → 0.897，validation 0.7181。
- **试跑的 +0.0425 来自这个分布的一次抽样：** top-4 loop01 是 10 个 top-4 循环中第 3 高；top-1 loop01（终版即原指南）0.6986 低于原指南均值 0.7048。
- **一次 validation 标注的波动：** 原指南 10 次，SD 0.0105。
- **Track 2 相关（未检验）：** FN 均值：原指南 281.9，top-1 282.0，top-4 271.8（SD 31.2）。
- **费用与运行：** ¥2,517（$15.92），低于估算的 ¥2,960 至 3,110；18 个批次约 2 小时；没有不可用回复。
- **对研究主线的含义：** 按 10/23 的完成标准（Q4），不显著的结果本身可以写，但要配合分析。下一步是教授列为第一件事的错误分析，现在有 30 次 validation 输出可用；"哪些改写在 validation 上有用、哪些有害"和"dev10 上的接受规则为何选不出能泛化的改写"是直接的问题。按设计，不因不显著而追加循环。

**2026-10-24 至 10-30，错误分析（离线，未调用 API）：修改后的指南各不相同，F1 的高低跟着少数几条新规则走；这些规则出自改写看不到的 gold 和只看总分的保留判定。** [报告](todo-temp/error-analysis/reports/20261024_error_analysis_report_zh.md)，[附录](todo-temp/error-analysis/reports/20261024_error_analysis_appendix_zh.md)，英文版尚未同步。材料是 10/23 复现的 30 次验证集运行和 44 轮改写记录。下文的"原指南范围"指 19 次原指南运行（10 次重复标注，加上停在原指南的 9 个循环各一次）的最小值到最大值。

- **平均收益没有确认，单份指南的差别是真的。** 11 份修改后指南中 7 份 F1 落在原指南范围外（3 份高于、4 份低于），纯波动只会有约 1 份。
- **F1 跟着 Specific 的损失走，不跟着 Modifier 的收益走。** 几乎每份指南都多标对了 Modifier。按排名比，11 份指南的 F1 与 Specific 标对数的相关是 0.84，与 Modifier 只有 0.44。
- **Modifier 的新增误标对应各指南新写的条文。** 增量几乎全落在 history of、risk of、patients with 这类短语后的疾病名上，只出现在写了"这类位置标 Modifier"的指南里，模型自述的标注依据也是这些条文。没有删掉条文后重标的对照，对应不能说成因果。
- **家族史规则是从一篇开发文档推广出来的，问题不在照抄字符串。** 这篇文档里的 ovarian cancer 多数修饰别的名词（gold 标 Modifier），只有 "a family history of ovarian cancer" 指疾病本身（gold 标 Specific）。改写那一步只看得到 verified examples（5 篇开发文档，每篇最多 5 个标对的提及），列出的总是前一种；它新写家族史规则时几乎都写成 Modifier，那时从没见过家族史位置的 gold。11 份指南都抄进了这篇文档的短语，但只有把家族史写成 Modifier 的 7 份在验证集上出现这类误标。
- **保留判定只看开发集总 F1，与 gold 相反的规则也能留下。** 事后核对 5 个开发集短语：top-4 的 9 份指南给它们写的 32 处规定中，15 处与开发集 gold 相反，都写在被保留的轮次。写入那一轮，开发集上通常已有对应提及由对变错，只是被总分的上升盖过了。
- **F1 最低的 top-4 loop10 删掉了原指南"cancer、tumor 要标"的规定**，它新漏掉的提及一半多是它自己的条文要求不标的。Specific 标成 DiseaseClass 等其余损失还没查原因。
- **Track 2 的结论取决于指标。** 只统计没有任何预测重叠的漏标（"真正漏标"，可看作必须通读全文才能补上的那部分）时，6 份指南低于原指南范围；按 FN 只有 4 份。
- **候选改动（都未检验）：** 改写后按开发集 gold 核对新规则；把全部标错例子交给分析和改写（主论文第 3.4.4 节写改写也会收到，现有实现没有传入）；取消 verified examples 每篇 5 个的上限；只收紧 history of 这类短语后的 Modifier 规则。
- **对研究主线的含义：** Track 1 的改动对象从"选哪类错误来修"具体到流程的两个环节：改写这一步能看到哪些 gold，保留判定看什么。这与 10/14 FALDH 证据链里的缺口相同：改写看不到 gold，就把开发文档里没列出的情形写错。验证集 100 篇的逐例错误已用于挑选改动，它不再是独立评价集，选出的改动要在新循环和没用过的文档上评价。

**2026-10-30 seminar：汇报错误分析；教授要求先把逐循环、逐轮的对照摆清楚，再把指南条文和结果模式对应起来。** [deck](../presentations/20261030_error_analysis_en.pptx)，生成脚本 `todo-temp/slides/build_error_analysis_slides.py`。依据是会议录音的自动转写，没有说话人标注，大段听不清，下面只记能确认的意见。

- **计数没讲清楚。** 教授反复追问 19 次原指南运行和 11 个以修改后指南结束的循环是怎么来的，建议列一张逐循环的表：每一轮的 F1、指南改没改，让每份修改后指南都能和原指南对上。以后的汇报先给这张表，再给汇总。
- **基线不配对。** 教授质疑拿一份修改后指南的一次标注去比 19 次原指南运行的均值和范围："用均值，看不出提升是不是确实发生在这一轮"，倾向逐例对照原指南的标注。讨论后接受原指南在各循环相同、任一次原指南运行都可作对照，转而要求看中间轮次：每一轮指南怎么改，标注怎么变。中间轮次只在开发集上标注过，在验证集上逐轮比较需要新标注；是否要追加，转写里听不清。
- **不要只看 F1。** 按子类型的变化方向有一部分来自原指南的起点：原指南 Modifier 标得差，改进空间大；Specific 标得好，空间小。教授也认为保留判定只看 F1 不稳，需要更稳健的判据。按子类型的分析要对 FP、FN 也做一遍，现在只有 TP。
- **把条文和结果模式对起来，这是主要的新要求。** 教授注意到多份指南属于同一种模式：Modifier 变好，Specific 没变好。要求把每份指南的结果对应到具体条文，看哪类条文带来哪种模式；如果能解释同一条文为什么对 Specific 有害、对 Modifier 和 DiseaseClass 有利，论证就站得住。用户提出的检验是删掉候选条文后重新标注。教授还问到每轮选中的错误簇（Modifier 还是 Specific）与结果的关系，这一点还没分析。
- **家族史规则：教授接受原因分析，提议在改写的 prompt 里要求"不写与 gold 相反的条文"。** 这需要把开发集全部标对的提及交给改写，不再只给 verified examples；教授确认这是改写指南、不是评价，用开发集 gold 可以。它和报告里"取消 5 个上限""核对新规则与开发集 gold"两个候选是同一方向。
- **范围：** 下一步查 Specific、DiseaseClass 的损失；教授问到 Composite 的边界错能否靠上下文区分，还没做。是否在 GPT 等模型上重复（教授问到）：现在只用 Haiku 探索，有发现后再在其他模型上检验。
- **对研究主线的含义：** 错误分析从"给全部错误计数"推进到"条文对应结果模式"，这是 Track 1 选改动的依据；要说条文造成了结果，需要删条文重标这样的对照，要先估费用。教授的提议把 10/09 认可的"给 refinement 提供 gold"具体成改写 prompt 里的一条约束，加上完整的开发集 gold。
- **下次 seminar：** 下周 16:00，日期转写听不清，待确认。

## 后续记录方式

实验后，LOG 新增一行，PROGRESS 记录它对三条优化轴、阶段目标和当前决策的影响，并更新文档底部的 Todo。负结果和中断同样保留。

seminar 后，将会议要点及其对研究主线的推进融入对应日期的历史进展，随后更新底部 Todo。每次保留未完成项，也检查短期任务是否仍服务于方法优化和长期标注目标。OVERVIEW 只在研究目标、方法或评价定义变化时更新。

## 下次 seminar 前的 Todo

### 2026-10-30 seminar Todo（当前进行中）

- [x] 逐循环对照表：每个循环每一轮的开发集 F1、是否保留，终版指南的验证集 F1，与原指南并列（教授）。只用已保存的输出。10/31 完成：报告第 1 节、附录 K。
- [ ] 中间轮次：每一轮指南改了哪些条文，开发集标注随之怎样变（教授）。验证集上逐轮比较需要新标注，先估费用，用户批准后再做。11/03 开发集一侧做了与两类 DiseaseClass 损失有关的三个循环（top-1 loop05、top-4 loop06、loop05），见报告第 6.3 节、附录 N；验证集一侧未做。
- [x] 按子类型的变化补上 FP、FN，并列出原指南各子类型的起点，把改进空间和条文的作用分开（教授）。10/31 完成：报告第 3 节。FN 按 gold 标签等于标对数的反面，不另列。
- [x] 条文对应结果模式：把 11 份指南按子类型变化归成几种模式，找出各模式对应的条文，解释同一条文为什么对 Specific 有害、对 Modifier 和 DiseaseClass 有利（教授）；顺带看每轮选中的错误簇与结果的关系。11/04 完成（11/03 第二版经独立审阅撤回）：报告第 3 节，33 根柱子只有 16 根超出单次运行的波动，超出的对得上 history of 规则、部位词规定、列举症状和单独 cancer 不标等少数条文写法（盲编码、重算前写定规则，附录 P）；"三根都正"和"Specific 负、其余正"两组单次运行分不开；第 5.1 节（top-4 loop06 的"病理状态名词标 DiseaseClass"一条标对 10 个 DiseaseClass、标错 5 个 Specific）、第 6.3 节（11 份指南都处理过同一个开发集错误簇，写出的规则方向相反）。删条文后重标的检验需要新标注，设计见上面的研究思路。
- [] Specific 标成 DiseaseClass、DiseaseClass 漏标两类损失，照 Modifier 的做法查。11/03 完成：Specific 标成 DiseaseClass 只出在规定"部位词不足以算具体疾病"的 top-1 loop05、top-4 loop06，理由 60 个中 59 个引用这一节；top-4 loop05 新漏的 20 个 DiseaseClass 只有 6 个是它的条文明确要求不标的（报告第 5 节，附录 L、M）。
- [ ] Composite 的边界错能否靠上下文区分（教授问到）。需要可以解释10/30的slides中的分数分布模式。
- [ ] 是否批准每份修改后指南在验证集上再标 2 次（2,200 次调用，约 ¥1,874，超过 ¥1,000 须通知管理员），用来判断柱状图的正负号分组（报告第 9 节）。
- [ ] Track 1 候选：改写 prompt 要求不写与开发集 gold 相反的条文，同时把开发集全部标对的提及交给改写（教授提议）。和报告里的四个候选一起排序，一次只改一处；都未检验。
- [ ] Track 2 主指标用 FN 还是真正漏标，待定（报告第 7 节）。
- [ ] 同步英文版报告（教授读的是中文版）。
- [ ] 确认下次 seminar 的日期（下周 16:00）。

### 研究思路（10/30 梳理）

主线：方法的平均收益没有确认，但修改后指南之间的差别是真的，能追到少数几条条文；坏条文出自流程的两个缺口：改写那一步看不到 gold，保留一轮只看开发集总 F1。研究从"哪些条文造成差别"走到"让流程不写、不留坏条文"。

- **论文故事线：** 复现（已完成）→ 诊断：损失对到具体条文（Modifier 部分已对上）→ 机制：已有证据，没有对照实验 → 方法：Track 1、Track 2 各一个候选，都未检验 → 评价：新循环、没用过的文档（待定）。
- **Track 1 首选：** 改写拿到开发集全部标对的提及，prompt 要求不写与开发集 gold 相反的条文（教授提议）。要同时报告照抄开发集字符串的比例，因为清单上的字符串约一半被抄进了指南。
- **Track 2 候选：** 标注输出加一个"不确定，送审"的出口，在方法上以 FP 换 FN，不是投票。依据是 top-4 loop10 的条文要求症状送审，输出里没有这一项，结果全变成漏标。
- **删条文重标的检验：** 初稿经独立审阅后撤回并修正，见 [设计说明](todo-temp/error-analysis/notes/20261103_clause_ablation_design_review.md)；未运行，先定文档、判定阈值和预算。11/03 离线准备完成（报告第 9 节、附录 O）：7 份指南的规则位置已列出，top-4 loop07 删 5 行的文本、diff、哈希已固定并确认删干净；验证集方案 79 篇、1,140 次、约 ¥906，没用过的训练文档 487 篇（214 篇有短语后提及，history of 之后只有 10 个），两组 40 篇约 ¥298。
- **待拍板：** 新方法在哪些文档上评价（验证集的逐例错误已用来挑选改动，不再独立）；Track 2 主指标（倾向真正漏标为主、FN 为辅）；预算。

### 2026-10-23 seminar Todo（当前进行中）

- [x] 错误分析与分类先行（教授）：先在已有的 Haiku 输出上建立分类方案，复现后再计数。（10/30 汇报第一版，见[错误分析报告](todo-temp/error-analysis/reports/20261024_error_analysis_report_zh.md)；细化见上方 10/30 Todo）
- [ ] Track 2 改为方法上的目标：以 FP 换 FN、同时保持 F1；修订 RP v4 中 Track 2 的部分。
- [ ] 写一份含统计检验的研究计划（会后要求）。
- [ ] 问 DBCLS 能否提供 Claude API key；准备报销材料：表格、收据、显示美元汇率的银行流水。
- [ ] top-2、top-3 是否要做：待定（教授问到）。

### 2026-10-20 meeting Todo（当前进行中；取代下方 10-09、10-16 两组里未完成的项）

- [ ] 在 DeepSeek 复现的输出上，建立覆盖全部错误的分类体系（後藤教授）。（10/22 起主模型为 Haiku；10/30 汇报了 Haiku 输出上的第一版，细化见 10/30 Todo）
- [ ] Track 1：按分类体系的结果改进方法，一次只改一处（Ken、後藤教授）。
- [ ] Track 2：以 FN 为主指标，测试投票阈值等调高召回率的方法（Kim 教授）。（10/23 改：不用投票，在方法上以 FP 换 FN，见上）
- [ ] 准备答辩时的说法：人工修正主要用于构建 benchmark；与微调相比，本方法只需要少量标注（後藤教授、Kim 教授）。
- [ ] DeepSeek 上每种方法 5 个循环，给出统计显著性（Ken）。（10/22 改为 Haiku、每种方法 10 个循环）
- [ ] 新实验全部使用 DeepSeek V4.1 flash，GPT-5.4 只作案例研究（Ken：换新模型重跑，结论不变即可）。（10/22 改为 Haiku 5.5 xhigh）
- [ ] 没有专家标注：两条 track 都以 gold 为参照（Ken）。
- [ ] 邮件确认：测试集能否最后用一次、标注费用、与 Ken 当前工作的边界。

已关闭的一组来自 [October 2 会议摘要](archive/2026-10-02_seminar-conflict-casestudy/seminar_oct2.md)（保留原优先顺序，均已完成）；当前进行中的一组来自 2026-10-09 seminar，列在本节末尾。注意两组的 P0–P4 编号含义不同，引用时不要混淆。

- [x] **P0：核查 Round 4 标注变化与回归。** 已复算整体及类别指标，整理混淆矩阵和逐例历史，区分已有错误、目标修复与新增回归。见 [P0 报告](todo-temp/p0-p4/p0/20261006_round4_p0_report.md)。
- [x] **P1：检验限制条款。** 已完成单变量对照（2026-10-06）：截短 R3 原则的 "do not apply" 从句后，原 41–44 行扁平排除消失，但模型自行再生等效条件限制，norrin/FALDH/abnormal development 无一恢复；dev F1 0.8671 低于原原则的 0.8873，S→D 类型错误翻倍。假设未证实，问题指向限制条款的写法与作用域而非其存在本身。见 [P1 报告](todo-temp/p0-p4/p1/20261006_p1_truncated_clause_report.md)。
- [x] **P2：改写作用域。** 已完成（2026-10-07）：限定改写使 FALDH 排除从扁平变为条件式，且未再生额外排除示例，但焦点漏标仍无一恢复；dev F1 0.8511 低于 R2 基线，按循环规则会被回退。结合 P1 的三臂证据：漏标近因是标注模型的上游判断，不是限制文本。见 [P2 报告](todo-temp/p0-p4/p2/20261007_p2_scoped_clause_report.md)。
- [x] **P3：整理并补充 Top-K 对比。** 已完成（2026-10-07）：0.9155 那次 top-4 指南 valid100 实测 F1 **0.8023**（top-1 0.7878、原指南 0.7792），增益集中于 Modifier 召回；吸收率 32% 低于 top-1 的 41%，硬编码解释被排除；两个 gold 相反排除示例仍在，且查明输入侧给 gold 证据也防不住。见 [P3 报告](todo-temp/p0-p4/p3/20261007_p3_topk4_report.md)。
- [x] **P4：汇报 10/20/30 篇规模对比。** 已完成（2026-10-08，全部离线）：吸收率随规模单调塌缩（41%→9%→3%）但 valid 非单调且臂间差均在噪声内（bootstrap）；dev30 仍写出 norrin 的 gold 相反排除——规模解决硬编码、不解决冲突示例；n_examples 误记勘误（实际均为 5）。replicate 两臂已设计未执行。见 [P4 报告](todo-temp/p0-p4/p4/20261007_p4_devsize_report.md)。

**本轮交付：** 逐例变化表、Round 4 混淆矩阵，以及原规则、删除限制、限定作用域三个版本的对比（P0–P4 已完成，seminar 五项 Todo 全部关闭）。**与整体目标的连接：** 三臂对照显示规则措辞路径对焦点漏标无效，P3/P4 进一步显示加证据（top-k、加数据）也防不住 gold 相反排除；共同缺口定位在 refine_guidelines 调用看不到带标签的 discrepancy 证据。若提出新的承载方式（gold 证据注入 rewrite 步、写后对照校验、CONSTRAINT 通道），需先在小样本验证可复用收益，再扩大评价，检查整体 validation 收益与稳定性，推动向 SOTA 目标前进。改善一个开发案例不直接视为达到阶段目标。

### 2026-10-09 seminar Todo（当前进行中；与上方已关闭的 10-02 五项不是同一组编号）

下次汇报的重点是解释"新规则为什么没有修复目标错误"，不是继续扩大实验规模。

**新 P0（下次 seminar 必做）：逐例定位失败环节。**

- [x] （2026-10-14 完成：与 3 个 gold 相反案例只在 FALDH 重合，未修复案例共 4 个，加上已修复的 PAH；见[规则链报告](todo-temp/r4-attribution/rule-chain/20261014_r4_rule_chain_report.md)）追踪 R4 后仍存在的 2 个 S→O 漏标（FALDH、deficiency in G6PD）；此前 3 个 gold 相反排除案例先按 case ID 核对重合（FALDH 重叠），保留完整句子与上下文。已有基础：P0 报告的逐例历史与 R4 diff 对照、P3 §3.4 的 gold 可见性核查，新增工作是归因与隔离实验，避免重复劳动。
- [x] （2026-10-15 完成：两类变化都不能归因于 R4 新 principle。Tay-Sachs/TSD 用 R4 指南重跑 5 次全是 M，原 run 的 S 不能复现；cutaneous vasculitis 在原指南不变时 5 次中 2 次为 S，属于波动。见[非目标变化报告](todo-temp/r4-attribution/nontarget/20261015_r4_nontarget_report.md)）解释 R4 非目标变化：为什么针对漏标生成的规则主要修复了 2 个 M→S（Tay-Sachs/TSD）并新增 1 个 S→D 回归。
- [x] （2026-10-14 完成：FALDH 为规则冲突，G6PD 为修复条件不足，PAH 为撤销 R3 副作用）逐案例串规则链：原文/gold/R3 预测 → discrepancy explanation → 新 principle → R3→R4 guideline diff → 最终预测；归类为修复条件不足（principle 太抽象）、规则冲突（新规则允许但例外仍禁止）或整合失真（principle 可用但写入时被改写弱化）。交付物是"案例—具体条款—预测变化"证据，不只是总体分数。
- [x] （2026-10-14 完成，另加 ②b"去掉 exception rule"；见[隔离对照报告](todo-temp/r4-attribution/isolation/20261014_r4_isolation_report.md)；追加 ③− 已完成：删去三处点名排除后 FALDH 3/3 恢复）隔离对照（会上提出）：同模型同生成设置，用 ①R3 指南 ②标签定义＋新 principle（不进完整指南） ③R4 完整指南 三种条件重标 3 个原 S→O 案例；重标阶段不给 annotator gold，gold 仅用于事后评分。结果读法：principle 单独有效而整合无效 → 优先查规则冲突与整合；单独也无效 → 查 discrepancy explanation 与 principle 内容；相同条件下结果不稳 → 先少量重复，避免把随机变化当成规则效果。
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

### 2026-10-16 seminar Todo（当前进行中）

教授反馈原文：

> Test whether guidelines of round3 can also fix the missing FALDH is the named exceptions are removed.
>
> Test whether the 'M→S fixes can't be reproduced' are real noise or not. I need to make the input and settings all the same.

- [x] R3 指南删去点名 FALDH 的两处（第 41 至 45 行、第 241 行）后重标 10577908，看 FALDH 能否修复。10/17 结果：**不能**，删除后 0/5，同批 R3 原样对照 0/3，其余 13 个 gold 每次都对。10/14 里 R4 删去点名排除后是 3/3，所以 FALDH 的修复靠的是 R4 新增的内容，不只是去掉点名排除。R3 第 12 行的一般性 exception rule（"a molecular/substance entity or its level/activity"）没有 R4 那样的 deficiency 例外，推测是第二道阻挡，未检验。见[结果](todo-temp/r4-attribution/isolation/20261017_r3_minus_faldh_report.md)。
- [x] （2026-10-17 决定不运行：现有证据已足以说明 R4 新增内容是修复 FALDH 的必要条件，这一条只能细分是第 12 行还是第 14 行起作用，不改变结论）追加条件：在上一条的基础上再删去 R3 第 12 行的 "a molecular/substance entity or its level/activity"，5 次，检验它是否就是第二道阻挡。条件文本已备好（`conditions/c4b_minus_level.txt`），以后需要时可直接运行。
- [ ] 检验 Tay-Sachs/TSD 的 M→S 不能复现是否真是波动，要求输入和设置完全相同。10/16 离线核查：能控制的都相同，模型版本无法确认。可补的三项都还没做：请管理员确认部署是否升级过；以后保存每次调用的 `model` 字段；用 R4 指南再标 8326491 15 次。10/17 补充：`model` 字段实测返回的是部署名 `eastus2-gpt-5.4`，查不出版本，版本只能问管理员。见[核查](todo-temp/r4-attribution/nontarget/20261016_replay_identity_report.md)。
