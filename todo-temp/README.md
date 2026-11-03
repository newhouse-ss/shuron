# todo-temp 索引

临时工作区：放还在用的分析脚本、它们的输出，以及已完成课题的结论报告。2026-10-20 和 2026-11-03 各整理过一次，整理前的全部内容分别保存在提交 d86ea17 和 3df8d00 中。

| 文件夹 | 内容 | 被谁引用 |
| --- | --- | --- |
| `p0-p4/` | 10/02 seminar 布置的五项核查：R4 逐例变化（p0）、截短 exception rule（p1）、限定作用域（p2）、top-4 与 gold 矛盾的规则扫描（p3）、开发集规模对比（p4）。汇总报告：`20261008_p0-p4_consolidated_report.md` | PROGRESS 10/08 段；LOG |
| `r4-attribution/` | R4 失败归因：总报告 `20261014_r4_failure_attribution_report.md`；`rule-chain/`（规则链追踪）；`isolation/`（隔离对照、R4 和 R3 删除点名排除的测试）；`nontarget/`（非目标变化、重跑一致性核查）；`check_model_version.py` | PROGRESS 10/14 至 10/17 段；LOG；10/16 的两份 deck |
| `plan-v3/` | plan v3（10/20 会议所用，已删除）和 `docs/RP/20261020_research_plan_v4.md` 所依据的离线分析和估算。`evidence_notes.md` 汇总了所有出处 | RP v4；PROGRESS 10/19、10/20 段；LOG；10/20 deck |
| `deepseek-stability/` | DeepSeek V4.1 Flash 稳定性测试（10/21 已运行）：设计、原始回复（`units/`）、统计和费用。DeepSeek 已不是主模型 | RP v4 第 1 步"稳定性测试"；PROGRESS 10/21 段；LOG |
| `haiku-trial/` | Claude Haiku 5.5 试跑（10/22）：effort 档位比较、原指南在 dev10 上重复运行的噪声、费用估算、batch 循环的离线检查；原始回复在 `units/` | PROGRESS 10/22 段；LOG |
| `seminar-20261023/` | 10/23 seminar 的粒度确认问题和 ① 至 ⑧ 的流程 todo（`TODO.md`）；Haiku 复现的设计（`reproduction_design.md`）和结果分析（`reproduction_analysis.py`，两种方法与原指南的差值出自这里） | PROGRESS 10/23 段；LOG；错误分析报告和附录；10/30 deck |
| `error-analysis/` | 10/23 Haiku 复现的错误分析（10/24 起）：中文报告与附录、脚本、输出、工作笔记和删条文检验的设计说明。文件夹内 `README.md` 是索引 | PROGRESS 10/24 至 10/30 段；LOG |
| `slides/` | 各次会议 deck 的生成脚本和共用的辅助函数、图片。deck 本身在 `修論/presentations/`（P0 至 P4 那份在 `docs/slides/`） | PROGRESS |

**10/20 整理时删掉的内容：**
- 运行过程的中间产物：dry_run 提示渲染、运行日志、排队探针、中途放弃的那次运行、中间成绩；
- P0 至 P4 的英文重复报告；
- plan v1、v2 的费用脚本；
- 被 `plan-v3/evidence_notes.md` 合并的 7 份叙述文档。

这些都可以从 d86ea17 找回。

**11/03 整理时删掉的内容（可从 3df8d00 找回）：**
- 错误分析报告两次修订前的备份（`error-analysis/notes/` 下两个 `*_review_before/`）；
- 10/26 外部审阅和 deep research 用的 prompt（`error-analysis/prompts/`）；
- `haiku-trial/` 和 `deepseek-stability/` 的 dry_run 提示渲染，可由各自的 dry-run 命令重新生成；
- 各处 `__pycache__/`。

运行日志和 `batch_state_*.json` 保留，因为脚本里的批次号、耗时和掉线次数以它们为出处。`error-analysis/outputs/20261030_rationale_audit/` 的 4 个大中间文件（约 100 MB）不入库，由 `rationale_audit_extract.py` 重建，sha256 记在同目录的 `reproducibility.json`。

**脚本约定：**
- 所有脚本都用 `Path(__file__)` 定位仓库根目录，在仓库根目录下运行，例如 `python todo-temp/plan-v3/error_breakdown.py`。
- `isolation/` 和 `nontarget/` 里的 `run_*.py`、`haiku-trial/run_haiku.py`、`deepseek-stability/run_stability.py` 会调用付费 API，运行前要先得到批准；其余脚本都是离线的。
