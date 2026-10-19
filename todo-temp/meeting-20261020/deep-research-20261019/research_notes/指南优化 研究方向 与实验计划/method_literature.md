# 方法文献与来源核查

来源：research_literature 只读文献检索及一轮重点来源复核，2026-10-19。下列研究支持候选机制，不提供本项目未来增益的数值预测。

## 直接相关

1. Kon Woo Kim, Jin-Dong Kim, Akiko Aizawa. **Refining and Reusing Annotation Guidelines for LLM Annotation**, ACL 2026. https://aclanthology.org/2026.acl-long.1760/ 。公开元数据核实作者和发表状态。本地 PDF 是匿名投稿稿，不能假设逐字等同终稿。§3、§4.2、Table1：10 篇原训练集文档做 refinement，100 篇原开发集文档评价，原 test 保留；改写器收到 discrepancy context 与 verified TP。本地稿 GPT-5 NCBI 三个条件的 F1 分别 .46（prompt-only）、.73（original guideline）、.76（refined）。**不是 P=.46、R=.73、F1=.76**。文献代理补充曾误标 P/R/F1，父代理已依据直接提取纠正并要求复核。典型收益有限，存在新 FP。当前实现信息传递与论文描述的差别必须向作者确认，修复实现不自动构成新方法。

2. Siun Kim, Hyung-Jin Yoon. **DiZiNER: Disagreement-guided Instruction Refinement via Simulating Pilot Annotation for Zero-shot Named Entity Recognition**, ACL 2026. https://aclanthology.org/2026.acl-long.795/ 。8 个异构标注模型、18 个 NER 数据集，含 AnatEM、BC2GM、BC4CHEMD、BC5CDR、GENIA，没有 NCBI Disease。它用模型间分歧而非本项目的 dev-gold discrepancy 驱动指令修改。§5 与附录 Table16 把共识结果替换为 gold，平均变化约 +0.3 F1 且数据集间正负并存；作者提出固定目标拟合及多样性解释。**不能据此说 gold 普遍有害，或反对独立的 gold-conflict checker**。低监督定义、模型数量与本项目不同，六周内不宜整体复刻。14/18 的比较属于原论文自己的基线与数据设置，不能当本项目收益预测。

## 规则、示例、核查

3. Huang et al. **GuideNER: Annotation Guidelines Are Better than Examples for In-Context Named Entity Recognition**, AAAI 2025. https://ojs.aaai.org/index.php/AAAI/article/view/34591 。四个数据集含 GENIA；从训练示例归纳规则并在来源案例上验证。text-davinci-003 的 GENIA F1 64.76，去规则验证 62.80（Table2，待最终来源复核回执）；模型、数据及规则生成任务均与当前改写任务不同。可支持规则验证这一机制的试验动机，不能支持声称本项目验证器预计提升 1.96 点。

4. Ge et al. **Improving few-shot named entity recognition for large language models using structured dynamic prompting with retrieval augmented generation**, npj Artificial Intelligence 2026. https://www.nature.com/articles/s44387-025-00062-2 。5 个生物医学数据集，GPT-4/LLaMA3，结构化提示与推理时检索标注示例。摘要报 5-shot/10-shot 平均提升 8.8%/6.3%，headline 未清楚说明相对百分比还是百分点，因此报告无需照搬数值。它验证 inference-time retrieval，不直接验证 rewrite-stage protected-example selection。检索若访问整个 train gold，将破坏只用 10 篇监督的约束；本项目只能先在同样十篇中选。

5. Wang et al. **GPT-NER: Named Entity Recognition via Large Language Models**, arXiv 2023. https://arxiv.org/abs/2304.10428 。将 NER 转成标记跨度生成，增加候选实体 self-verification 以减少误报。GENIA Table3：无验证 64.06、zero-shot 验证 64.29、few-shot 验证 64.42。本研究有 biomedical GENIA，早期笔记称“仅通用 NER”不准确。它支持有限验证试验，不支持大增益或针对漏标的修复；当前项目的允许补漏 reviewer 比候选验证权限更大。

6. Hu et al. **Improving Large Language Models for Clinical Named Entity Recognition via Prompt Engineering**, JAMIA 2024. https://pmc.ncbi.nlm.nih.gov/articles/PMC11339492/ 。GPT-3.5/GPT-4；163 MTSamples 合成出院小结、91 VAERS 报告；结合指南、错误分析和示例。GPT-4 relaxed F1 .861/.736，exact F1 .593/.542。宽松与严格指标差距表明匹配口径不能忽视。不同临床语料、模型、方法，不能外推为 NCBI 四子类型预计增益。

7. Nagar et al. **LLMs are not Zero-Shot Reasoners for Biomedical Information Extraction**, arXiv 2024. https://arxiv.org/abs/2408.12249 。BioMistral-7B/Llama2；比较标准提示、CoT、自一致性、检索与受约束输出。在该设置中标准提示总体优于若干复杂方法，说明多一步 reasoning 或投票不自动获益。结论限旧开放模型及该零样本设置，不证明当代模型 detailed-guideline review 无效。

## 自动提示优化，作为方法背景而非优先实现

8. Pryzant et al. **Automatic Prompt Optimization with Gradient Descent and Beam Search**, EMNLP 2023，ProTeGi. https://aclanthology.org/2023.emnlp-main.494/ 。用文字错误反馈、候选改写、beam/bandit 选择提示。任务级最大改善不能外推 NER。与当前错误反馈驱动修改相近，新颖性不能只叫“自动迭代优化”。

9. Opsahl-Ong et al. **Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs**, 2024，MIPRO. https://arxiv.org/abs/2406.11695 。联合优化多阶段指令及示例，非本任务，可能增加搜索和选择偏差。只有 10 篇 dev 时不宜优先引入完整优化器。

10. Agrawal et al. **GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning**, 2025 preprint / 2026 conference version. https://arxiv.org/abs/2507.19457 。自然语言反思与 Pareto 候选演化，跨六任务评价，非 NCBI 四子类型。此处仅作方法谱系；若论述最终会议归属，需以公开版本元数据为准，不必用该归属支撑研究决策。

## 与当前资源约束对齐后的建议

- 写后显式冲突审查：本地机制证据最直接，GuideNER 提供验证规则的间接先例。先在已知正反案例上测是否真能检出冲突及误报，再付费修复和重标。检测率提高与 held-out F1 提高是两个不同结论。
- 按错误模式选择正反对照示例：检索与结构化 prompt 文献提供动机，但当前更改的是改写器保护示例，不是标注器 few-shot 输入。先保持相同五篇/相同 token 预算的对照，限已标十篇。
- 默认不把实体级 gold 发给改写器：教师可用 dev gold 做分析，writer 只接抽象原则；或者 checker 看到 gold，writer 只收抽象冲突。必须先说明哪种反馈仍符合用户的监督约束。
- 分离跨度识别和类型判定：本地错误分布支持优先诊断；先用既有预测做 subtype-only 试验，避免大规模多模型 CoT。
- reviewer 是后处理工作流，需要同预算模型对照及 fixes/breaks，而非 guideline refinement 方法本身；不能用 gold 模拟分数推出人工节省。
- 自动 prompt 搜索、八模型 disagreement、外部知识 RAG、全面改换模型，不列六周主线。

## 证据强度边界

本地案例是直接机制证据，公开其他语料实验是可迁移性的间接动机，任何未来 valid/test 改善仍是待检验假设。数据集、匹配指标、模型、监督量、评价 split 不同的 headline 分数不可并列解释成预期效果。
