# todo-temp 索引

临时工作区：放还在用的分析脚本、它们的输出，以及已完成课题的结论报告。2026-10-20 整理过一次，整理前的全部内容保存在提交 d86ea17 中。

| 文件夹 | 内容 | 被谁引用 |
| --- | --- | --- |
| `p0-p4/` | 10/02 seminar 布置的五项核查：R4 逐例变化（p0）、截短 exception rule（p1）、限定作用域（p2）、top-4 与 gold 矛盾的规则扫描（p3）、开发集规模对比（p4）。汇总报告：`20261008_p0-p4_consolidated_report.md` | PROGRESS 10/08 段；LOG |
| `r4-attribution/` | R4 失败归因：总报告 `20261014_r4_failure_attribution_report.md`；`rule-chain/`（规则链追踪）；`isolation/`（隔离对照、R4 和 R3 删除点名排除的测试）；`nontarget/`（非目标变化、重跑一致性核查）；`check_model_version.py` | PROGRESS 10/14 至 10/17 段；LOG；10/16 的两份 deck |
| `plan-v3/` | plan v3（10/20 会议所用，已删除）和 `docs/RP/20261020_research_plan_v4.md` 所依据的离线分析和估算。`evidence_notes.md` 汇总了所有出处 | RP v4；PROGRESS 10/19、10/20 段；LOG；10/20 deck |
| `deepseek-stability/` | 下一步要做的 DeepSeek 稳定性测试设计和费用估算（未运行） | RP v4 第 1 步"稳定性测试" |
| `seminar-20261023/` | 10/23 seminar 的粒度确认问题和 ① 至 ⑧ 的流程 todo（`TODO.md`） | — |
| `slides/` | 各次会议 deck 的生成脚本和共用的辅助函数、图片。deck 本身在 `修論/presentations/`（P0 至 P4 那份在 `docs/slides/`） | PROGRESS |

**整理时删掉的内容：**
- 运行过程的中间产物：dry_run 提示渲染、运行日志、排队探针、中途放弃的那次运行、中间成绩；
- P0 至 P4 的英文重复报告；
- plan v1、v2 的费用脚本；
- 被 `plan-v3/evidence_notes.md` 合并的 7 份叙述文档。

这些都可以从 d86ea17 找回。

**脚本约定：**
- 所有脚本都用 `Path(__file__)` 定位仓库根目录，在仓库根目录下运行，例如 `python todo-temp/plan-v3/error_breakdown.py`。
- `isolation/` 和 `nontarget/` 里的 `run_*.py` 会调用付费 API，运行前要先得到批准；其余脚本都是离线的。
