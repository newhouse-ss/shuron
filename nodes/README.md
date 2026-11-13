# 按会议节点整理的研究材料

每个文件夹对应一次 seminar 或会议，里面放为这次会议做的分析、脚本、输出和汇报材料；跨好几个节点持续使用的放 `shared/`。原始运行结果不在这里，仍按 run ID 放在 `outputs/`、`logs/`、`reproduction/`，逐次实验见 [LOG.md](../LOG.md)，每个节点的结论见 [PROGRESS.md](../PROGRESS.md) 同日期的段落。

## 归属规则

- **节点：** 一次 seminar 或会议，文件夹名是"日期_事件"。
- **两次会议之间产生的材料，放进它所准备的下一次会议。** 例如 11/07 至 11/13 的分析放在 `2026-11-13_seminar/`。
- **脚本互相调用的主题文件夹整体放在开始的节点。** 例如 `r4-attribution/` 里 10/17 才完成的 R3 检验也留在 10/16 节点，下表注明。
- **error analysis 跨了三个节点，按日期拆开。** 被两个以上后续节点读取的基础表和报告本体放在 `shared/error-analysis/`。

## 节点一览

| 节点 | 内容 |
| --- | --- |
| [2026-08-31_midterm-abstract](2026-08-31_midterm-abstract/) | 中期摘要：`47256388_周恒宇_要旨.pdf`（提交版）；`47256388_HengyuZhou_要旨_revised_fixed.docx/.pdf`（2026-09-02 修订定稿） |
| [2026-09-07_midterm-defense](2026-09-07_midterm-defense/) | 中期答辩（9/7 至 9/8）：`midterm_slides.pptx`；`presentation-revised.pptx`（按修改日期推断为答辩修订版） |
| [2026-09-15_seminar-future-plan](2026-09-15_seminar-future-plan/) | `9_15 future plan.docx` |
| [2026-09-24_seminar-expert-benchmark](2026-09-24_seminar-expert-benchmark/) | `Expert_Annotation_Benchmark_English.pptx`（专家标注基准构想）；`hardcoding_analysis.docx`（新增规则的抽象与硬编码逐条分析） |
| [2026-10-02_seminar-conflict-casestudy](2026-10-02_seminar-conflict-casestudy/) | `conflict_handle_casestudy.pptx`（Round 3/4 冲突案例）；`seminar_oct2.md`（会议摘要，10/06 补录） |
| [2026-10-09_seminar](2026-10-09_seminar/) | `p0-p4/`：10/02 布置的五项核查（R4 逐例变化、截短 exception rule、限定作用域、top-4 与 gold 矛盾的规则扫描、开发集规模对比），汇总报告 `p0-p4/20261008_p0-p4_consolidated_report.md`；`slides/20261008_p0-p4_findings_en.pptx` |
| [2026-10-16_seminar](2026-10-16_seminar/) | `20261014_r4_failure_attribution_plan.md`；`r4-attribution/`：R4 失败归因（总报告、规则链、隔离对照、非目标变化），含 10/16 会上布置、10/17 完成的 R3 删点名排除检验（`isolation/20261017_r3_minus_faldh_report.md`）；`slides/` 下两份 10/16 deck |
| [2026-10-20_meeting](2026-10-20_meeting/) | `20261020_research_plan_v4.md`（当前研究计划）；`plan-v3/`：计划 v3 和 v4 所依据的离线分析与估算，出处汇总在 `evidence_notes.md` |
| [2026-10-23_seminar](2026-10-23_seminar/) | `deepseek-stability/`：DeepSeek 稳定性测试（10/16 设计，10/21 运行）；`haiku-trial/`：Haiku 试跑（10/22）；`seminar-20261023/`：粒度确认、流程 todo、Haiku 复现的设计和结果分析 |
| [2026-10-30_seminar](2026-10-30_seminar/) | `error-analysis/`（10/24 至 10/30）：错误模式、规则与 gold 的对照、逐轮记录、Modifier 子集与 pilot 编码、理由引用的条文；`notes/` 是当时的分析计划和规则 |
| [2026-11-06_seminar](2026-11-06_seminar/) | `error-analysis/`（10/31 至 11/06）：柱子归因（`bar_attribution`、`bar_patterns`、`dc_loss_clauses`）、删条文检验的准备（`clause_ablation_stage0`、`rerun_cost`）、柱子聚类抽样（`bar_cluster_sample`）、理由定位到条文（`bar_clause_pilot`，其中 `codex_locate/` 是 Codex 的定位记录） |
| [2026-11-13_seminar](2026-11-13_seminar/) | `error-analysis/`（11/07 至 11/13）：按实体类型看整体（`overall_view/`）、类型文本相似度试点（`type_text/`）、top-4 loop08 与其他改后指南的 Modifier 条文对照（`pair_*`、`anchor_loop08_*`） |
| [2026-11-16_seminar](2026-11-16_seminar/) | `two-step-pilot/`（11/13 起）：论文主张的调研（`notes/20261113_thesis_claim_research.md`）、两步标注检验的设计与结果（`notes/20261113_two_step_pilot_design.md`）、代码与评分（`scripts/pilot/`，评分输出 `outputs/20261114_scores/`）、原指南真正漏标能否被找到与检验篇数的离线推算（`scripts/`、`outputs/`） |
| [shared](shared/) | `error-analysis/`：错误分析报告和附录（中英文）及其图；错误总表（`error_table.py` 写出 `error_rows.csv`）；已保存理由的索引（`20261030_rationale_audit/`）；柱子数据（`loop_label_tables`）。`slides/`：各次 deck 的生成脚本，共用排版函数在 `build_faldh_slides.py`；deck 本身在 `修論/presentations/`，10/09、10/16 的三份在对应节点的 `slides/` |

## 不在这里的

- `outputs/`、`logs/`、`data/`、`reproduction/`：原始运行、数据集和复现代码。
- `docs/`：跨阶段的参考图和 PubAnnotation 用法。
- `archive/`：参考论文、通信留档、seminar 原始记录总表。

## 脚本约定

- 在仓库根目录运行，例如 `python nodes/2026-10-23_seminar/haiku-trial/vote_curve.py`。脚本用 `Path(__file__)` 定位仓库根目录；error analysis 的脚本以 `PYTHONHASHSEED=0` 运行，`overall_view.py` 需要带 matplotlib 的 Python（`H:/Anaconda/python.exe`）。
- 会调用付费 API 的脚本，运行前先得到批准：`p0-p4/p1/run_p1.py`、`p0-p4/p2/run_p2.py`、`r4-attribution/check_model_version.py`、`r4-attribution/isolation/run_*.py`、`r4-attribution/nontarget/run_nontarget.py`、`deepseek-stability/run_stability.py`、`haiku-trial/run_haiku.py`、`2026-11-06_seminar/error-analysis/scripts/bar_clause_pilot/haiku_locate.py`。其余脚本都是离线的。
- 已保存理由索引的 4 个大中间文件（约 100 MB）不入库，由 `shared/error-analysis/scripts/rationale_audit_extract.py` 重建，sha256 记在同目录的 `reproducibility.json`。

## 2026-11-13 整理记录

**来源。** 原 `todo-temp/` 各主题文件夹、`docs/RP/`、`docs/slides/` 和 `archive/` 下的日期文件夹。整理前的状态是提交 0ba2036；更早两次整理（10/20、11/03）删掉的内容在提交 d86ea17 和 3df8d00。完整的旧路径与新路径对照在 [path_map_20261113.tsv](path_map_20261113.tsv)，11/13 以前写的笔记和输出里出现的 `todo-temp/...` 路径按它查。

**改动范围。** 只挪了文件，改了脚本和文档里的路径；文档里能对上的路径都已改成新路径。保存的输出和会话记录（json、csv、txt）没有改，里面的旧路径保持原样。

**核对。** 挪动后重跑了全部离线脚本：error analysis 44 个，其余节点 44 个。输出与整理前提交的文件比较，除换行符外逐字节一致。只有 5 个文件不同，都保留了原版本：

- `shared/error-analysis/outputs/20261030_rationale_audit/diagnostics.json`：记录的是脚本自身的 sha256，改路径后脚本变了。
- `2026-10-30_seminar/error-analysis/outputs/tp_exposure_output.txt`：6 个并列字符串的排列顺序，10/26 已记录。
- `2026-11-13_seminar/error-analysis/outputs/overall_view/overall_view_output.txt`：末尾有一段人工追加的执行说明，脚本本身不生成。
- `2026-10-09_seminar/p0-p4/p0/analysis.json` 和 `2026-10-20_meeting/plan-v3/audit_helper_output.txt`：前者记录的是 10/06 改名前的运行路径，后者对照的 plan v3 中英文件早已删除。整理前的版本跑出来也同样不一致。

另有 7 个早期脚本（如 `haiku-trial/batch_pilot_costs.py`）的屏幕输出与保存的文件不同。在临时检出的整理前版本上运行，结果与整理后完全一样；差别来自保存之后 `outputs/` 又增加了运行，与这次整理无关。

**没有运行的脚本：** 上面列出的付费 API 脚本；生成 deck 的脚本（会覆盖 `修論/presentations/` 里的 deck）；`codex_locate/` 的会话脚本（会改写会话记录）；需要参数的 `r4-attribution/rule-chain/trace_cases.py`。
