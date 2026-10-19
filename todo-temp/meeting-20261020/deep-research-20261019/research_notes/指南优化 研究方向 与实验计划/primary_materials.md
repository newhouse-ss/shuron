# 中期原件与基础论文直接核查

来源：core_code_mapper 第二轮只读提取，2026-10-19。通过 bundled Python 的 pypdf 和 python-pptx 在内存读取，未修改输入。

## 基础论文

- `archive/references/backbone-research.pdf` 第 1 页标题为 **Refining and Reusing Annotation Guidelines for LLM Annotation**，作者栏为 Anonymous ACL submission。本地稿不能独立验证最终作者、会议及正式发表状态。公开版本由文献代理另查。
- 第 3 页 §3.2：精确边界及实体类型同时匹配。第 3 至 4 页：达到停止阈值或不再改善则停止，不改善时丢弃最新修改。
- 第 4 至 5 页 §3.4：按 gold/predicted label pair 聚类，选择最多的组；解释案例包含 mention、60 字符语境窗、类型及错误分类。论文称每轮自动采样 verified TP，并称改写阶段收到 current guideline、principle、discrepancy context 与 verified examples。这与当前实现的固定前五篇、没有带 gold discrepancy 的路径存在需要作者确认的差异。
- 第 5 至 6 页 §4.2：从原训练集随机取 10 篇供 refinement；从原开发集取 100 篇评价。NCBI 与 BioRED 原开发集均 100 篇；BC5CDR 从 500 篇中取 100。原测试集未用于该论文这项评价。
- 第 7 页 Table 1：NCBI GPT-5 为 prompt-only .46、原指南 .73、改写后 .76，3 轮，评价 gold 实体 791。不能与本项目 GPT-5.4 复现批次拼接。
- 第 10 页 appendix：.9 停止阈值是参考标注者一致性的启发式，不是达到或超过人工质量的声明。
- 全文没有 593，也没有微调 BioBERT 实验。

## 中期摘要

两份摘要均为 2 页，路径在 `archive/2026-08-31_midterm-abstract/`。第 1 页 Table 1 的六项问题为：

1. 用来防回归的 verified-example 文档被写进指南，38/52 新增行可追溯至这五篇文档。
2. 错误类型变了，verified examples 没变；Round 3 最大组是 boundary mismatch，示例未体现相关边界证据。
3. 标注模型输出 rationale 和 guideline section，后续没有保留、使用。
4. validation 中 Modifier→O 占错误 21%，dev 中为零。
5. 相同指南重复标注不一致，20 次 dev10 F1 范围 .739 至 .859。
6. 每轮处理单一组，三轮目标 12 条错误，总错误仅少 7 条。

两版第 2 页结果：保留 verified examples 时 dev .797→.909、valid .779→.789，Copied Share 38/52=73%；移除示例后 dev .797→.837、valid .779→.771、0/32；提供示例但禁止复制后 dev .823→.833、valid .779→.784、0/25。后两种干预未达 .9 停止阈值，不能仅凭 absorption 降低就说方法更好。

摘要另报 DeepSeek-V4 十次并行：temperature0 SD .0261，temperature1 SD .0147；不能外推到另一版本。副标题的研究轴仍是规则有效性、泛化、可靠评价，不能把整个课题缩成一个 FALDH 案例。

## 中期 slides

- `archive/2026-09-07_midterm-defense/presentation-revised.pptx` 为 9 页；第 2 页出现 593 文档对比。
- `archive/2026-09-07_midterm-defense/midterm_slides.pptx` 为 10 页；第 3 页引 Kim et al. ACL 2026，第 7 页 top4/top1 分别 2/4 轮、错误 18→9 / 18→11；第 10 页目标为 validation 约 .79 逼近 SOTA .87，保留 10 docs vs 593 docs 优势。
- .87 是 slides 中的目标，但缺精确指标与 benchmark 来源；不是已验证的可比阈值。
- 593 可由公开 NCBI 原始划分独立核查；文档数不等于监督 token、实体数、挑选成本、人工时间或相同条件下达到同质量的样本需求。
