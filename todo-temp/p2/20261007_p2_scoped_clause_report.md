# P2：限定作用域改写 Round 3 原则限制从句的对照实验

日期：2026-10-07。对照 run：[20260802_gpt54-high_moderation](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/) Round 3。实验脚本与产物：本目录（`todo-temp/p2/`）。本实验调用模型重新生成指南并重新标注 10 篇开发文档；原版 Round 3 与 P1 结果直接取保存数据，未重跑。

## 结论

**限定作用域改写同样未能恢复焦点漏标；P2 dev F1 0.8511 为三臂最低，低于 R2 基线，按循环规则会被回退。结合 P1，三臂证据表明：焦点漏标的近因不是限制条款的写法，而是标注模型对这些语境的上游判断。**

- 焦点案例结果在三个原则版本下**完全一致**：spasticity 修复，deficiency of norrin、deficient activity of fatty aldehyde dehydrogenase（FALDH）、abnormal retinal vascular development 全部仍漏标。
- 文本侧改写按预期生效：FALDH 排除从扁平（原版）变为条件式（"仅作生化特征描述时不标注"），与 P2 原则的作用域措辞一致；但标注行为没有跟随文本。
- P2 相对原版新增 3 个 TP 损失（exudative retinal detachment 类型翻转、G6PD deficient 丢失、cutaneous vasculitis 类型翻转），总 discrepancy 14（原版 11、P1 12）。

## 1. 实验设计（控制变量）

**唯一变量**：Round 3 保存的 `refine_guidelines` 提示中，moderation 原则后半句从"删除"（P1）改为"限定作用域改写"。前半句逐字节不变（程序化拼接并断言）。改写后原则全文（861 字符，原版 521 字符）：

> - **IF** a noun phrase in a definitional, characterization, or causal/etiologic context denotes an **abnormal clinical or pathological state**—even when its head is a generic state/process/symptom noun rather than a canonical disease label—**THEN** annotate it as **DiseaseClass**. **Scope the exclusion narrowly**: do **not** apply this rule to a phrase that merely names or measures a normal biological process, a molecular/substance entity, level, or activity as such, or that states an isolated descriptive finding—**and only when** that phrase is **not** presented as a pathological condition of the patient/disorder. A phrase that presents a deficient, reduced, absent, or otherwise abnormal state of such an entity **as** a pathological condition of the patient/disorder **remains covered** by this rule, even when its head names a molecule or a process.

改写针对原从句的两个作用域缺陷：① "not presented as a pathological condition" 限定词原本只修饰最后一个备选项，现约束所有备选项；② 显式回捞病理性的 deficient/reduced/absent 状态（不点名 norrin/FALDH，避免把答案写进规则）。

**固定项**：guidelines_before（iteration_02 状态）、CONSTRAINT verified-examples 块、同一批 10 篇开发文档（seed 42）、同一模型配置（Azure eastus2-gpt-5.4，reasoning high）、同一循环评分器与分簇函数。排除示例不做任何人工修改，完全由模型生成（与 P1 的"删除"臂分开，以区分两类改动）。

**三臂对照**：原版（从句原样，取保存快照）、P1（从句删除，取 [p1/result.json](../p1/result.json)）、P2（本次）。

## 2. 指南文本对比

| 位置 | 原版 Round 3 | P1 截短 | P2 限定改写 |
| --- | --- | --- | --- |
| FALDH 排除 | 扁平 "Do not annotate"（41–44 行） | 条件式（"only a functional or mechanistic description"） | 条件式（"used as a biochemical characterization rather than as a standalone pathological condition mention"，第 44–47、246 行） |
| abnormal retinal vascular development | 无排除示例 | **新增**条件式排除 | 无排除示例 |
| norrin | 无（R4 才加入） | 无 | 无 |
| 指南长度 | 17,102 字符 | 18,654 字符 | 19,057 字符 |

P2 的文本结果最接近设计意图：排除被限定为条件式，且没有 P1 那样再生额外的排除示例。见 [guidelines_candidate_scoped.txt](guidelines_candidate_scoped.txt)。

## 3. 标注结果（同一批 10 篇开发文档，严格匹配口径）

| 状态 | TP | FP | FN | F1 |
| --- | --- | --- | --- | --- |
| R2 后（R3 前） | 61 | 7 | 13 | 0.8592 |
| R3 原原则 | 63 | 5 | 11 | **0.8873** |
| R3 P1 截短 | 62 | 7 | 12 | 0.8671 |
| R3 P2 限定改写 | 60 | 7 | 14 | **0.8511** |

焦点案例（gold → 各状态预测）：

| 实体 | Gold | R2 后 | 原版 | P1 | P2 |
| --- | --- | --- | --- | --- | --- |
| abnormal retinal vascular development | DiseaseClass | O | O | O | O |
| deficiency of norrin | DiseaseClass | O | O | O | O |
| spasticity | DiseaseClass | O | **TP** | **TP** | **TP** |
| deficient activity of fatty aldehyde dehydrogenase | SpecificDisease | O | O | O | O |

P2 相对原版的全部实体级变化（增益为零）：

- **TP 损失 3 个**：exudative retinal detachment（DiseaseClass→SpecificDisease，新增反向类型错误）、G6PD deficient（Modifier 丢失）、cutaneous vasculitis（SpecificDisease→DiseaseClass，与 P1 相同的翻转）。
- **新增 FP 2 个**：exudative retinal detachment 标为 SpecificDisease、cutaneous vasculitis 标为 DiseaseClass。

P2 错误分簇（总计 14）：S→O 3、S→D 3、D→O 2、S→M 2、跨度 1、D→S 1、C→O 1、M→O 1。

## 4. 三臂合并判定（P0–P1–P2 系列结论）

1. **排除示例不是漏标的近因。** 三种限制文本（原有 / 删除 / 限定改写）下三个焦点漏标结果完全相同；P2 连 abnormal retinal vascular development 的排除示例都不存在，它仍然漏标。指南里与 gold 相反的排除示例是模型上游判断的**症状**，不是成因——模型在这些 definitional/characterization 语境中本就不把这些短语读作疾病提及，规则文本的写法改变不了这个判断。
2. **限制从句的真实功能是精度护栏。** 删除它（P1）S→D 类型错误翻倍（2→4）；保留但改写（P2）本轮也未能改善且引入新的损失。原版 0.8873 的收益中，spasticity 的修复来自原则前半句，其余收益部分来自后半句对 DiseaseClass 过度扩张的压制。
3. **P2 比 P1 更差的读法需要谨慎。** P2 的三个 TP 损失中，cutaneous vasculitis 的翻转与 P1 一致（可能由该指南家族的共同倾向驱动），但 exudative retinal detachment 和 G6PD deficient 的损失是单次抽样；0.8511 与 0.8592/0.8671 的差距部分在标注噪声（SD 0.009–0.015）范围内。稳妥的说法是：P2 没有带来任何焦点案例恢复，整体也未见收益。
4. **对研究主线的启示。** 若要让这类"deficiency of X / 病理缺乏状态"案例被标注，规则措辞这条路在三臂证据下已基本被封死，可选方向：a) 在原则中写入更具体的语言模式（如 "deficiency/absence of [分子] 处于 results in / characterized by 框架时按 DiseaseClass 标注"）并用新的一轮检验；b) 正例演示（有效但即 hard-coding 路径，与避免样例依赖的目标冲突，需明确权衡）；c) 承认此类案例需要 CONSTRAINT/rationale 通道而非规则文本来承载。选择前应回到"指南改进应包含修改、删除原规则，而不只是追加 gold 示例"的边界上来。
5. **局限**：各臂均为单次重跑；指南候选文本是单次生成样本；标注噪声未按臂重复测量。

## 核查记录

- 复现命令：`python todo-temp/p2/run_p2.py`（需 .env 中 Azure 5_4 配置；候选指南与逐文档标注均已断点保存，中断后续跑不重复消耗 API 调用）。
- 产物：[prompt_scoped.txt](prompt_scoped.txt)、[principle_original.txt](principle_original.txt)、[principle_scoped.txt](principle_scoped.txt)、[guidelines_candidate_scoped.txt](guidelines_candidate_scoped.txt)、[annotations_scoped.json](annotations_scoped.json)、[result.json](result.json)。
- 原版数据来自保存快照 iteration_03/snapshot.json（SHA-256 见 [P0 报告](../p0/20261006_round4_p0_report.md)）；P1 数据来自 [p1/result.json](../p1/result.json)。
