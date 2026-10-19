# 评价审查最终补充

来源：research_eval_engineer 最终回执，2026-10-19。以下为拟议方案，不是已执行结果。

## 更窄的主假设

保护证据的正确性保证应只覆盖已经确认正确的预测跨度，不能把包含漏标的整篇文档称为“处理正确”，也不能因文本没有列在预测里就把它当负例。

最干净对照：相同五篇文档、相同此前预测、相同 principle、相同设置，只修改这条正确性承诺。不要同时动态换示例、换模型、加 reviewer 或 raw gold。若该机制不重复出现或没有质量净收益，则止于机制诊断，不扩全循环。与教师抽象反馈、输出冲突检查等方向互斥分阶段选择，不能在主对照一次改完。

## 资源公式参考

- 现有重复轨迹：原指南＋同期三条 Top-1＋三条 Top-4，7×100=700 次标注；再加最初两条成功轨迹为最多900次。**这不是最少必须执行的预算**，可以去重、先审计、分批决策。当前无预算授权，不启动。
- 固定快照机制完整试验：2 种说明×3 次 rewrite×(1 次 rewrite＋dev10×3 次重标)=186 次，重试另计。这是扩展上限方案，起步可缩小已固定机制案例，但不得把缩小试验的结果称为全局收益。
- 原方法与单一改动各3轨迹、最多3轮、每版 dev10 标注2次，每轮3次分析/生成调用，并加终版 valid100：总1134次；dev每版3次时1374次。数量依赖实际停止轮数及分析调用定义，不是通用固定价格。
- 未使用 test100，两臂各3终版：600次。若已验证输出可重复使用，不能把复用预测算独立标注。
- reviewer dev10：两条件（独立重新标注、读取旧预测复核）×3次×10篇=60次，若无净改善停止。
- token cap64000 不等于费用上限，须另设总token/费用/时间/重试上限与完整率记录。不是所有阶段自动顺次执行，阶段无支持信号就停。

## 评价

- 主终点 strict micro-F1，辅助 P/R、忽略子类型的跨度 F1、各类型计数、fixes/breaks、失败及调用成本。
- 独立轨迹均值差至少 .01、至少2/3为正可作为**会议拟议的实用晋级规则**，不是显著性或功效保证。样本3条仍很弱，所有轨迹与区间照报。
- 文档配对 bootstrap 必须同步抽两臂相同文档，重算 TP/FP/FN 的 micro-F1；不能以文档 F1 平均替代，也不能把条件性区间当全过程方差。
- 若能证明有未用于选方向的原 test，冻结后一次终检；否则诚实写探索性 validation，另定未来确认。
- 复核负担以文档/句子覆盖率、残留错误做模拟，选择信号不得看 gold；20/40/60% 文档 gold 完整替换只是模拟。实际人类速度和纠错质量须真实测量。

## 一手来源

1. NCBI 官方资源：https://www.ncbi.nlm.nih.gov/CBBresearch/Dogan/DISEASE/ 。原语料论文：https://pmc.ncbi.nlm.nih.gov/articles/PMC3951655/ 。793 篇 PubMed 摘要，原始 split 为593/100/100；四类 Specific Disease、Disease Class、Composite Mention、Modifier。BioBERT 预处理去重可能改变训练计数，需核具体版本。10 vs593 是直接 refinement 监督文档数对原训练集规模，不是达到同质量所必需的标注量比较。
2. BioBERT：https://pmc.ncbi.nlm.nih.gov/articles/PMC7703786/ ，§4.1、§4.2、Table6。原论文89.71为 Base v1.1 (+PubMed)，单 Disease、exact entity、原 test，非本项目四类 valid100。
3. Zhao 与 Goto：https://arxiv.org/html/2503.03261v2 ，Table4 的 .897是另一实验表中的引用；不得与 BioBERT原论文不同模型版本拼成一条说明。
4. Huang et al. **Large Language Models Cannot Self-Correct Reasoning Yet**，ICLR2024：https://openreview.net/forum?id=IkmD3fKBPQ 。研究无外部反馈的推理自纠错，不能泛化成所有 NER review 失效；仅支持设置无偏对照及报告新破坏。
5. Geifman 与 El-Yaniv. **Selective Classification for Deep Neural Networks**，2017：https://arxiv.org/abs/1705.08500 。风险与覆盖率须同时报告；用于本项目文档复核时是方法借鉴而非直接效果证据。
6. Lingren et al., JAMIA2014，预标注对人工速度/偏差影响的研究：https://academic.oup.com/jamia/article-pdf/21/3/406/9517677/21-3-406.pdf 。直接测人的速度和质量，与替换 gold 标签的模拟不同。报告不需照搬未复核效应数值。
7. Pro说明与官方Claude Code路径详见 evaluation_audit.md 所列官方链接。

## 会上要定

主贡献是证据作用域、抽象反馈还是独立审查；原方法是否真将整篇文档标为正确；是否先补已有重复轨迹；禁止 raw gold 的具体模型边界；原 test 是否确实保留；没有真人专家时如何限定长期替代目标的阶段性证据。不要把“诊断足够写论文”当成保证毕业或不必追求性能目标。
