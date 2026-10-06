# 研究概览

更新：2026-10-06。本文件保留研究背景、方法和评价口径。当前进展及下次 seminar 待办见 [PROGRESS.md](PROGRESS.md)，逐次实验结果见 [LOG.md](LOG.md)。

## 研究目标

这是一个以生物医学命名实体识别（NER）为起点的 NLP 硕士研究。基于 *Refining and Reusing Annotation Guidelines for LLM Annotation*，总体路线是优化 guideline refinement，首先使 LLM 标注效果逼近 SOTA，随后实现对人类专家数据标注的替代或部分替代，减少人工标注负担。

[中期 abstract](archive/2026-08-31_midterm-abstract/47256388_周恒宇_要旨.pdf)将方法优化归为三个方向：从开发证据提取有效规则、泛化到新文档、可靠评价。hard-coding、Top-K、数据规模和规则冲突是其中的具体问题；其结果需回到整体标注质量和后续人工负担上判断。

研究建立在已有 moderation 框架上，覆盖 NCBI Disease、BC5CDR 和 BioRED。NCBI Disease 是主要诊断场景。BioBERT 在 NCBI Disease 上的 F1 **0.86** 是用户指定的 SOTA 比较目标；它与专家标注水平是不同的参考，正式比较时需要附上相同数据划分及评分口径。

## 基线方法

从训练集抽取少量开发文档，按原指南标注，与 gold 比较并归类错误；针对选中的错误簇推断模式、生成原则，再修改指南并重新标注。开发 F1 达到 0.9 或不再改善时停止，最终指南用于独立文档评价。

基线通常使用 10 篇开发文档、5 个提示示例。作者说明 10 篇是随机抽样下的经验及资源选择，并非最优规模。用于保护已有正确案例的 verified-example 输入包含完整文档和既有模型标注，不只是实体片段。

## 研究与评价口径

- **开发 F1** 用于指导修改及停止；**validation F1** 用于观察开发样本之外的表现，二者分别报告。
- 当前复现采用精确跨度及实体类型匹配：validation 报告 PubAnnotation 口径，开发循环及停止规则使用集合评分。两者对重复标注的处理不同，不混用结果。
- **指南一致性、模型遵循指南、与 gold 一致** 是不同问题。与 gold 冲突不能直接等同于指南内部自相矛盾。
- **文本吸收率** 统计至少四字符的开发实体字符串是否新增于指南，排除原指南已有字符串；它也会计入“不标注”示例，不能解释为正确答案记忆率。人工 hard-coding 审核另看删除示例后是否仍有可执行的条件和标注方向。
- 重复标注存在随机波动；同时改变样本规模、示例数量或模型的比较不能归因于单一因素。用于反复调优的 validation 反馈也需与最终独立评价区分。

## 已确定的研究边界

用户在 2026-10-06 明确了“先逼近 SOTA，再替代或部分替代专家标注”的长期路线。导师在 9 月 12 日提醒，当前性能不足以直接声称已能替代人工，需要更充分的证据；这限定现阶段结论，不取消长期目标。接近模型基准后仍需评估同任务专家质量、人工修正量和时间成本，确定可替代范围。指南改进应包含修改、删除原规则，而不只是追加 gold 示例。

共享的未发表稿件及通信按作者的保密要求在研究范围内使用。

## 按需查阅的材料

| 材料 | 用途 |
| --- | --- |
| [主论文](archive/references/backbone-research.pdf) | 基线方法和实验设计 |
| [同作者相关工作](archive/references/sub-backbone-research1.pdf)、[相近研究](archive/references/sub-backbone-research2.pdf) | 证据驱动的指南构建、规则组合和其他标注工作流 |
| [导师通信](archive/correspondence/email_with_professor.pdf)、[作者通信](archive/correspondence/email_with_auther_of_backbone-research.pdf) | 已记录的研究建议和方法澄清 |
| [中期摘要](archive/2026-08-31_midterm-abstract/47256388_周恒宇_要旨.pdf)、[中期 slides](archive/2026-09-07_midterm-defense/midterm_slides.pptx) | 中期成果，状态可能早于后续实验 |
| [冲突案例 slides](archive/2026-10-02_seminar-conflict-casestudy/conflict_handle_casestudy.pptx) | October 2 seminar 对应的 Round 3/4 案例 |
| [人工 hard-coding 分析](archive/2026-09-24_seminar-expert-benchmark/hardcoding_analysis.docx)、[专家标注参考提案](archive/2026-09-24_seminar-expert-benchmark/Expert_Annotation_Benchmark_English.pptx) | 诊断方法和待探索参考 |
| [seminar 历史](archive/seminar_note.txt)、[每次会议留档](archive/) | 研究反馈的原始记录 |

代码入口及数据结构见 [README.md](README.md)。实验变体和评分工具在 reproduction/，保存的配置、逐轮提示和指南在 outputs/，评分结果在 reproduction/results/，发表与报告留档在 archive/。新 session 先读本文件和 PROGRESS，再按当前问题读取相应实验材料，避免每次加载全部历史。
