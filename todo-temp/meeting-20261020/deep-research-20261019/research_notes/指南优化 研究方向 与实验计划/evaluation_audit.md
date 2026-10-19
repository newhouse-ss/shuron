# 独立评价审查与父代理整合要求

来源：research_eval_engineer 已回传的重点核查与父代理对交付范围的要求。2026-10-19。完整回执补在同目录另一文件。

## 原计划必须修改的评价问题

1. .012 来源于 sqrt(2)*.015/sqrt(3)，只是两组三次均值差的约一个标准误。在独立高斯近似下也不是 95% 显著性阈值；多轮筛选还增加偶然接受。不能把它写成已校准的噪声门槛。
2. 固定指南重复标注、从头生成独立指南的轨迹、有限评价文档是三层不确定性。文档配对 bootstrap 只覆盖第三层条件不确定性，不覆盖全部方法波动。
3. 现有 valid100 已用于误差分析、挑选研究方向，后续可作 development/validation evidence，不能再说 untouched test。是否有未参与分析的原始 test 或另批数据，必须先审计再冻结。
4. Top-4 未证实稳定优于 Top-1。优先考虑评价已有多条 Top-4 和 Top-1 的终版指南，优先补“评分”，不直接补“生成轨迹”。旧模型部署可能漂移，正式比较需同一批次、同配置评价指南，不能只拼历史分数。
5. noise-robust acceptance 是待验证方案，不能先验作为所有 arm 的更优新基线。将重复评价作为共有测量过程，并保持接受策略固定；若专门研究接受策略，就单独对照。
6. 用户批注不能直接给 gold。默认保留开发 gold 用于已有教师端错误分析和离线评分，writer 仅收到抽象规则/冲突类型，不直接接收实体级 gold。checker 看 gold 的权限需明确，不能忽略用户边界；另列待会后确认选项。
7. 类型混淆双向对称不是 gold 歧义的充分证据。先做盲审、看 guideline 定义及上下文，未审前以基准 gold 为评价准则。
8. 用整个训练集 gold 挑 10 篇，将消耗超过 10 篇监督信息；不能仍宣称只用 10 篇人工标注。
9. 基础模型 SD 和一次原指南 valid 差距不够作为模型替换桥接。至少在新模型内有 matched baseline，再用小规模 old/new guideline 交叉检查迁移；否则结论只归属于新模型。
10. copied share 非增和零 scanner 报警不宜作为方法成功硬门槛。文本吸收本身不是记忆证据，scanner 漏检也不等于零真实冲突。主要终点应是独立质量，辅助终点包括检出的冲突、目标修复、回归及 token/调用成本。
11. .8811 是把两个不复现预测替换、其余冻结的反事实分数，不是完整 dev 重标的均值。版本不可考，证据足以证明决策敏感，尚不能完全区分随机性与模型漂移。

## Oracle 与 reviewer

- .9606 =731TP/0FP/60FN，是既定 matcher 下的 gold-edit 场景。未配对重叠中仍有 gold；若允许拆分、合并、扩边或新增，能达到的值变动，因此不是所有 prediction-only review 的理论上界。
- 当前 reviewer 可 add，而 oracle 不可 add，权限不等。将 gold-edit 与 reviewer 的差距解释为剩余人力没有依据。
- 若实际标注减负是研究终点，至少测选择复核率、漏掉错误率、人工检出漏标所需的整句/整篇阅读，真实专家时间需真实测量。实体变化数不是人工时间。
- reviewer 对照需标注本身、同模型相同额外预算的二次处理，必要时 reviewer 模型独立直接标注。否则更好 reviewer 基础模型或额外 token 都可能解释提升。
- 先在开发集测 fixes/breaks，若不净改善停止，不必保证论文一定有 reviewer 正结果。不要在 validation 看结果后改权限再测，并当单次确认。

## BioBERT 直接来源

https://pmc.ncbi.nlm.nih.gov/articles/PMC7703786/ ，BioBERT 原论文 §4.1、§4.2、Table6：NCBI F1 89.71 对应 BioBERT v1.1 (+PubMed)，§4.2 模型为 BERT_BASE；§4.1 对 NCBI 训练集去重，Disease 单类型、entity exact match。不能把它与 Zhao 表4 BioBERT-Large v1.2 的 .897 当同一实验。

截至本轮没有确认相同任务定义、split、监督约束下 2026 当前 SOTA。推荐称“历史微调参照”，正式阶段在同一数据和 scorer 上复评。项目四子类型 F1 .8023 不可直接与单 Disease 类型 .8971 相减解释差距；collapse .8546 也只解决类型，未解决 split/预处理/模型监督差异。

## Pro 订阅

Anthropic 官方：Pro 不含 Claude Console API，API 单独计费；可在现有 Claude/受支持 Claude Code 里做少量手动可行性试验，Pro 与 Claude Code 共享限额。不要假设订阅鉴权可转入通用 Python API。若受支持 Claude Code 工作流能保存固定输入、原始结构化输出、模型/会话状态，也不能一概声称正式实验只能 API；但本轮未验证批量复现能力。

- https://support.claude.com/en/articles/8325606-what-is-the-pro-plan
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan
- https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-is-claude-api-usage-billed-separately-from-my-paid-claude-plan

## 决策边界

用户要广泛背景探索、当前现状评估和可供明天讨论的优化 proposal；不是要求现在启动任何付费试验。本轮保留原稿、历史 outputs 和既有未提交工作，只在本次新目录内生成报告和修订计划。不更新 LOG 为“已做实验”，不修改实际部署或模型配置。

以预期信息收益及成本排优先级，不伪造 ROI 倍数或预计 F1 增益。时间为 10/21 至 12/1 六周。原计划人民币/日元价格表未经本轮全项复核，只可标为历史估计，不作为授权。本轮使用 calls/tokens 的预估公式，任何后续付费执行需要明确预算。
