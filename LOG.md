# 实验日志

一行一个实际运行或已定义的重复实验，只记设置、结果和状态。解释、决策及下次 seminar 待办见 [PROGRESS.md](PROGRESS.md)。这是已整理实验的索引，不是 outputs 下所有目录的清单。

日期取 run ID 或批次标识，不代表实际完成日期；缺失时不推测。NCBI refinement 默认 GPT-5.4 high，dev10；另行注明 dev20/30。validation F1 使用 metrics.json 的 PubAnnotation 口径，dev F1 保留循环记录的集合评分口径；吸收指新增实体字符串出现数，不是正确答案记忆数。

2026-10-06 对 outputs/ 与 logs/ 做过规范化重命名：去掉与父目录重复的数据集段（如 `20260802_ncbi_gpt54-high_moderation` → `20260802_gpt54-high_moderation`），`k1` 统一为 `topk1`，`_rN` 统一为 `_runN`。reproduction/ 下旧报告和 logs/ncbi_disease/ 短标签日志中仍出现的旧名为重命名前记录。

| 日期 | 实验 / 证据 | 设置 | 关键结果 | 状态 |
| --- | --- | --- | --- | --- |
| 2026-09-22 | [BioRED moderation](outputs/biored/20260922_gpt52-high_moderation/status.json) | GPT-5.2 high，dev10 | dev F1 0.8287 至 0.8602，2 轮 | 完成，无进一步改善 |
| 2026-09-22 | [BC5CDR moderation](outputs/bc5cdr/20260922_gpt52-high_moderation/status.json) | GPT-5.2 high，dev10 | dev F1 0.8675 至 0.8988，4 轮 | 完成，无进一步改善 |
| 2026-09-02 | [NCBI topk4-run3](outputs/ncbi_disease/20260902_gpt54-high_topk4_run3/status.json) | Top-4 | dev F1 0.8194 至 0.8841，4 轮 | 完成，无进一步改善 |
| 2026-09-02 | [NCBI topk4-run2](outputs/ncbi_disease/20260902_gpt54-high_topk4_run2/status.json) | Top-4 | dev F1 0.8028 至 0.8552，2 轮 | 完成，无进一步改善 |
| 2026-09-02 | [NCBI topk4-run1](outputs/ncbi_disease/20260902_gpt54-high_topk4_run1/status.json) | Top-4 | dev F1 0.7972 至 0.8252，3 轮 | 完成，无进一步改善 |
| 2026-09-02 | [NCBI topk1-run3](outputs/ncbi_disease/20260902_gpt54-high_topk1_run3/status.json) | Top-1 | dev F1 0.8028 至 0.8511，2 轮 | 完成，无进一步改善 |
| 2026-09-02 | [NCBI topk1-run2](outputs/ncbi_disease/20260902_gpt54-high_topk1_run2/status.json) | Top-1 | dev F1 0.8028 至 0.8028，1 轮 | 完成，无改善 |
| 2026-09-02 | [NCBI topk1-run1](outputs/ncbi_disease/20260902_gpt54-high_topk1_run1/status.json) | Top-1 | dev F1 0.8451 至 0.8451，1 轮 | 完成，无改善 |
| 2026-09-01 | [NCBI topk4-dev10](outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/status.json) | Top-4 | dev F1 0.8028 至 0.9155，2 轮；吸收 12/37 | 完成，达到阈值 |
| 2026-08-24 | [NCBI published 标注批次](reproduction/results/ncbi-valid-published-0824/metrics.json) | published-method，valid100 | F1 0.7789 | 已评分，与早期批次输入一致性未核实 |
| 2026-08-24 | [NCBI noTP 标注批次](reproduction/results/ncbi-valid-noTP-0824/metrics.json) | noTP，valid100 | F1 0.7716 | 已评分 |
| 2026-08-24 | [NCBI abstraction 标注批次](reproduction/results/ncbi-valid-abstraction-0824/metrics.json) | 要求抽象，valid100 | F1 0.7844 | 已评分 |
| 2026-08-14 | [NCBI verified + abstraction](outputs/ncbi_disease/20260814_gpt54-high_verified_dev10_abstraction/status.json) | 后验回归验证，加抽象约束 | 未得到完整运行最终分数 | 失败，provider server error |
| 2026-08-14 | [NCBI verified 无抽象](outputs/ncbi_disease/20260814_gpt54-high_verified_dev10_noabstraction/status.json) | 后验回归验证 | dev F1 0.8169 至 0.8169，1 轮 | 完成，无改善 |
| 2026-08-14 | [NCBI abstraction-run2](outputs/ncbi_disease/20260814_gpt54-high_moderation-abstraction_run2/status.json) | 保留示例，要求抽象 | dev F1 0.8252 至 0.8252；吸收 0/37 | 完成，最终指南未改变 |
| 2026-08-14 | [NCBI abstraction-run1](outputs/ncbi_disease/20260814_gpt54-high_moderation-abstraction_run1/status.json) | 保留示例，要求抽象 | dev F1 0.8227 至 0.8333，2 轮；吸收 0/37 | 完成，无进一步改善 |
| 2026-08-13 | [NCBI withTP-dev20](outputs/ncbi_disease/20260813_gpt54-high_moderation-withTP_dev20/status.json) | dev20，示例上限 10 | dev F1 0.7821 至 0.8105，2 轮；吸收 6/68 | 完成，无进一步改善 |
| 2026-08-12 | [NCBI withTP-dev30](outputs/ncbi_disease/20260812_gpt54-high_moderation-withTP_dev30/status.json) | dev30，示例上限 15 | dev F1 0.8092 至 0.8577，3 轮；吸收 3/115 | 完成，无进一步改善 |
| 2026-08-06 | [NCBI noTP-run5](outputs/ncbi_disease/20260806_gpt54-high_moderation-noTP_run5/status.json) | 删除 verified-example 约束块 | dev F1 0.8085 至 0.8227，3 轮；吸收 0/37 | 完成，无进一步改善 |
| 2026-08-06 | [NCBI noTP-run4](outputs/ncbi_disease/20260806_gpt54-high_moderation-noTP_run4/status.json) | 删除 verified-example 约束块 | dev F1 0.7391 至 0.7887，2 轮；吸收 0/37 | 完成，无进一步改善 |
| 2026-08-06 | [NCBI noTP-run3](outputs/ncbi_disease/20260806_gpt54-high_moderation-noTP_run3-partial-1round/status.json) | 删除 verified-example 约束块 | 报告中的部分轨迹 0.7972 至 0.8611 | 中断，SSL 轮询失败 |
| 2026-08-06 | [NCBI noTP-run2](outputs/ncbi_disease/20260806_gpt54-high_moderation-noTP_run2/status.json) | 删除 verified-example 约束块 | dev F1 0.7972 至 0.8369，2 轮；吸收 0/37 | 完成，无进一步改善 |
| 2026-08-05 | [NCBI noTP-run1](outputs/ncbi_disease/20260805_gpt54-high_moderation-noTP_run1-partial/status.json) | 删除 verified-example 约束块 | 报告中的部分轨迹 0.7943 至 0.8592 | 中断，SSL 轮询失败 |
| 2026-08-02 | [NCBI published-dev10](outputs/ncbi_disease/20260802_gpt54-high_moderation/status.json) | withTP，示例上限 5 | dev F1 0.7972 至 0.9091，4 轮；吸收 15/37 | 完成，达到阈值 |
| 2026-09-22 | [BioRED valid-G](reproduction/results/biored-valid-G/metrics.json) | 原指南，valid100 | F1 0.7836 | 已评分 |
| 2026-09-22 | [BioRED valid-M](reproduction/results/biored-valid-M/metrics.json) | 修改后指南，valid100 | F1 0.8077 | 已评分 |
| 2026-09-22 | [BC5CDR valid-G](reproduction/results/bc5cdr-valid-G/metrics.json) | 原指南，valid100 | F1 0.8634 | 已评分 |
| 2026-09-22 | [BC5CDR valid-M](reproduction/results/bc5cdr-valid-M/metrics.json) | 修改后指南，valid100 | F1 0.8579 | 已评分 |
| 2026-08-02 | [NCBI valid-S](reproduction/results/ncbi-s-gpt54/metrics.json) | 简单提示，valid100 | F1 0.3902 | 已评分 |
| 2026-08-02 | [NCBI valid-G](reproduction/results/ncbi-g-gpt54/metrics.json) | 原指南，valid100 | F1 0.7792 | 已评分 |
| 2026-08-02 | [NCBI valid-M 早期批次](reproduction/results/ncbi-m-gpt54/metrics.json) | 修改后指南，valid100 | F1 0.7878 | 已评分 |
| 2026-08-13 | [NCBI dev20-M valid](reproduction/results/ncbi-m-dev20/metrics.json) | dev20 所得指南，valid100 | F1 0.7745 | 已评分 |
| 2026-08-13 | [NCBI dev30-M valid](reproduction/results/ncbi-m-dev30/metrics.json) | dev30 所得指南，valid100 | F1 0.8050 | 已评分 |
| 未记录 | [size-noise 重复标注](reproduction/results/size_noise/summary.json) | 固定指南，5 次标注，dev10/20/30 | F1 SD 0.01502/0.00978/0.00921 | 已有结果，未等同于保护 TP 损失分析 |
| 未记录 | [postverify probe A](reproduction/results/postverify_probe.json) | 修复反馈包含 mention | 两次尝试回归数 4、0；F1 0.8511、0.8811 | 局部 probe 完成 |
| 未记录 | [postverify probe B](reproduction/results/postverify_probe_condB.json) | 反馈仅含 span/type | 回归数 4/5/5/6/4；最佳 F1 0.7862 | 局部 probe 完成 |

吸收数据见 [hardcoding.json](reproduction/results/hardcoding.json)，中断运行的部分轨迹见 [ablation report](reproduction/REPORT_ablation_verified_examples.md)。新实验完成后新增一行；seminar、方案和未执行 Todo 不写成实验行。
