# P1：截短 Round 3 原则后半段限制从句的对照实验

日期：2026-10-06。对照 run：[20260802_gpt54-high_moderation](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/) Round 3。实验脚本与产物：本目录（`todo-temp/p1/`）。本实验调用模型重新生成指南并重新标注 10 篇开发文档；原版 Round 3 结果直接取保存快照，未重跑。

## 结论

**假设未被证实：致命条目不是由原则后半句的 "do not apply" 从句单独造成的。**

- 截短从句后，原 guidelines 第 41–44 行的 FALDH 扁平排除示例（"Do not annotate … because it refers to enzyme activity"）确实**消失**；但模型在没有该从句的情况下**自行再生了等效限制**：条件性 FALDH 排除、对 "abnormal development / absence of a protein" 类短语的宽泛排除，甚至新增了对 "abnormal retinal vascular development" 的条件性排除示例（原版没有）。
- 三个焦点漏标（deficiency of norrin、deficient activity of fatty aldehyde dehydrogenase、abnormal retinal vascular development）在截短版中**无一恢复**。
- 截短版 dev F1 **0.8592 → 0.8671**，低于原原则的 **0.8873**；按循环接受规则（after > before）会被接受，但收益明显更小。
- 截短版还出现原版的压制对象松动的迹象：PAH deficiency 从漏标变成标错类型（DiseaseClass，FP+FN），cutaneous vasculitis 从正确翻成 DiseaseClass（丢 TP 且新增 FP）。该从句原本同时在压制类型扩张。

## 1. 实验设计（控制变量）

**唯一变量**：Round 3 保存的 `refine_guidelines` 提示中，moderation 原则从 521 字符截短为 281 字符——删去分号后的整句：

> **do not apply this rule** when the phrase refers only to a normal biological process, a molecular/substance entity or level, or an isolated descriptive finding that is **not** presented as a pathological condition of the patient/disorder.

截短前后原则全文见 [principle_original.txt](principle_original.txt) 与 [principle_truncated.txt](principle_truncated.txt)；截短版提示为 [prompt_truncated.txt](prompt_truncated.txt)（已断言除该句外与保存提示逐字符一致）。

**固定项**：guidelines_before（iteration_02 状态，与快照逐字符一致）、CONSTRAINT verified-examples 块原样保留、同一批 10 篇开发文档（seed 42）、同一模型配置（Azure eastus2-gpt-5.4，reasoning high）、同一循环评分器与分簇函数。

## 2. 指南文本对比

| 位置 | 原版 Round 3 结果 | 截短版 candidate |
| --- | --- | --- |
| 原则前半句（规则本体） | 第 11 行：definitional/characterization 语境中表异常病理状态的通用名词短语标 DiseaseClass | 保留（第 7、10 行改写并扩展） |
| 原则后半句（限制从句） | 第 12 行："Do not apply the previous bullet when … molecular/substance entity or its level/activity …"，并称此类短语 "not disease mentions" | 该句**不存在** |
| FALDH | 第 41–44 行："> Deficient activity of fatty aldehyde dehydrogenase - **Do not annotate**，because it refers to enzyme activity"（与 gold SpecificDisease 完全相反） | 扁平排除**消失**；但第 256–260 行新增**条件性**排除："not annotated when it is only a functional or mechanistic description" |
| abnormal retinal vascular development | 无排除示例 | 第 33–34 行**新增**条件性排除示例（"Do not annotate … when it is only a mechanistic or descriptive characterization"），与 gold DiseaseClass 相反 |
| 其他新增限制 | — | 第 11 行："abnormal development, reduced activity, altered expression, or absence of a protein are **not** annotated unless …"，字面上仍覆盖 "deficiency of norrin" |

截短版指南 18,654 字符，比原版结果（17,102）更长——模型用编号列表补写了更多细则。见 [guidelines_candidate_truncated.txt](guidelines_candidate_truncated.txt)。

## 3. 标注结果（同一批 10 篇开发文档，严格匹配口径）

| 状态 | TP | FP | FN | F1 |
| --- | --- | --- | --- | --- |
| R2 后（R3 前） | 61 | 7 | 13 | 0.8592 |
| R3 原原则（保存快照） | 63 | 5 | 11 | 0.8873 |
| R3 截短原则（本次） | 62 | 7 | 12 | **0.8671** |

焦点案例（gold → 各状态预测）：

| 实体 | Gold | R2 后 | R3 原版 | R3 截短 |
| --- | --- | --- | --- | --- |
| abnormal retinal vascular development | DiseaseClass | O | O | O |
| deficiency of norrin | DiseaseClass | O | O | O |
| spasticity | DiseaseClass | O | **TP** | **TP** |
| deficient activity of fatty aldehyde dehydrogenase | SpecificDisease | O | O | O |

截短版相对原版的全部实体级变化：

- **TP 增益**：无。
- **TP 损失**：cutaneous vasculitis [646,666)（SpecificDisease → DiseaseClass）。
- **新增 FP**：cutaneous vasculitis 标为 DiseaseClass；deficiency of hepatic phenylalanine hydroxylase 从漏标（O）变为标为 DiseaseClass（gold SpecificDisease，同时计 FP+FN）。

截短版错误分簇（总计 12，原版 R3 为 11）：S→D 类型错误 **4**（原版 2）、D→O 2、S→O 2、S→M 2、跨度 1、C→O 1。S→D 的上升与限制松动后 DiseaseClass 过度适用一致。

## 4. 对假设的判定与后续

1. **原则后半句不是致命条目的唯一成因。** 截短后 FALDH 扁平排除确实消失，但等效的条件性限制由模型自行再生，三个焦点漏标无一恢复；norrin 的排除示例原本就是 Round 4 才加入的（P0 已确认），本轮它始终漏标与限制文本无关。
2. **该从句并非纯害。** 截短版收益更小（+0.008 vs 原版 +0.028），且 S→D 类型错误翻倍——它原本部分压制了 DiseaseClass 的过度扩张。这与 slides 中"前半句扩召回、后半句是安全条款"的定位一致，但安全条款的写法把目标案例也扫了进去。
3. **对 P2 的启示**：问题在限制条款的**写法与作用域**（"molecular/substance entity or its level/activity" 字面上覆盖一切 "deficiency of X"），而不在"是否存在限制"。P2（限定作用域改写：让排除只约束机制/分子层面的非病理用法，并显式排除病理缺乏语境）仍是合理的下一步；同时应检查 CONSTRAINT 块是否在向模型暗示需要补偿性限制。
4. **局限**：本实验是单次重跑。标注存在随机波动（size-noise 实验 SD 0.009–0.015），0.8671 与 0.8873 的差距部分可能来自标注抽样；截短版指南文本本身也是单次生成样本。cutaneous vasculitis 的 S/D 跨轮反复（P0：D、S、D、S、D）提示其翻转也可能含噪声成分。

## 核查记录

- 复现命令：`python todo-temp/p1/run_p1.py`（需 .env 中 Azure 5_4 配置；本轮运行约 34 分钟）。
- 产物：[prompt_truncated.txt](prompt_truncated.txt)、[guidelines_candidate_truncated.txt](guidelines_candidate_truncated.txt)、[annotations_truncated.json](annotations_truncated.json)、[result.json](result.json)（全部计数与逐例数据）。
- 原版数据来自保存快照 iteration_03/snapshot.json（SHA-256 见 [P0 报告](../p0/20261006_round4_p0_report.md)）；截短点的断言、principle 在提示中唯一性的断言均由脚本强制执行。
