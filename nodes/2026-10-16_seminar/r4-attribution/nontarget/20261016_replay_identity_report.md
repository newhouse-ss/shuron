# E1 重跑的输入和设置是否与原 run 相同；"不能复现"是否是波动

2026-10-16。来源：10/16 meeting 教授反馈第 2 条，"Test whether the 'M→S fixes can't be reproduced' are real noise or not. I need to make the input and settings all the same." 本文全部离线完成，没有调用 API。

## 结论

- **E1 能控制的输入和设置，都与 08/02 原 run 相同。** 指南文本逐字节相同，文档、提示模板、输出配置、模型部署、推理强度、输出上限和请求路径也一致（第 1 节）。
- **有两样东西无法做到相同。**
  - 一是 Azure 部署背后的模型版本。08/02 没有记录，现在无法查到当时的版本。
  - 二是模型自身的随机性。调用里没有设置 temperature 或 seed，同样的输入本来就会得到不同输出。所谓"波动"，指的就是这一部分。
- **现有数据支持"原 run 的 S 是一次偶然结果"，没有发现模型整体变了的迹象。**
  - 23 次重跑与原 run 保存的预测相比，大多数预测完全相同。不一致的数量，与重跑之间互相比较时的不一致处在同一水平（第 2 节）。
  - 重跑全部和原 run 不一致的格子只有两个，而这两个都是因为原 run 的结果"特别"才被挑出来研究的案例。只按一次结果挑案例，重跑时回到常态是预料之中的。
- **还不能完全排除的一种可能**：08/02 的模型版本在这一处给出 S 的概率更高。旧版本已经无法重放，所以只能用更多重复缩小范围，或者请管理员确认部署是否升级过（第 3 节）。

## 1. 逐项核对

| 项目 | 原 run（08/02） | E1（10/15） | 是否相同 | 依据 |
| --- | --- | --- | --- | --- |
| 指南文本 | `iteration_04` 的 `guidelines_after` | 同一字段 | 逐字节相同，SHA-256 10e93c9d… | `check_replay_identity.py` 第 3 项 |
| 文档 | `data/datasets/ncbi_disease/train/8326491.json` | 同一文件 | 原 run 未保存全文；保存的 12 个跨度在 E1 文档同一位置上文字全部一致 | 同上第 2 项 |
| 提示组装 | `annotate_with_guidelines`，模板在 `prompts.py` | 同一函数 | 标注提示原 run 未保存。同一文件里另外三个模板能逐字还原原 run 4 轮保存的提示，没有一处不符 | 同上第 1 项 |
| E1 实际提示 | | dry run 21,992 字符 | 逐字包含 R4 指南和文档全文 | 同上第 4 项 |
| instructions | 启动脚本未传入，取默认空串 | 空串 | 相同 | `scripts/run_iterative_refinement.py` 第 237 至 250 行 |
| 输出配置 | rationale + guideline section | 相同 | 相同 | 同上第 244 至 247 行；`run_nontarget.py` 第 122 行 |
| 模型部署 | `eastus2-gpt-5.4`（key `5_4`） | key `5_4` | 部署相同 | `inputs/resolved_run_config.json` |
| 推理强度、输出上限 | high，64000 | high，64000 | 相同 | 同上；`run_nontarget.py` 第 151 行 |
| 请求路径 | Responses API 后台模式 | 同一代码路径 | 相同 | `reproduction/REPORT_ncbi_gpt54.md` 第 36 至 42、497 行 |
| 每篇文档单独调用 | 是 | 是 | 相同 | `iterative.py` 第 345 至 364 行 |
| temperature、seed | 未设置 | 未设置 | 相同，但正因如此输出会随机变化 | `providers/openai.py` 第 224 至 234 行 |
| 模型版本 | 未记录 | 未记录 | **无法确认** | 两边保存的记录里都没有 `model` 字段 |
| 代码版本 | 早于 08/20 的首次提交 | 08/20 提交，之后 src 未改 | **无法逐字确认** | 08/02 的输出缺少 08/20 代码会写的 `guidelines_candidate.txt` 和 `dev_split`，说明当时的代码更旧 |

## 2. 重跑结果与原 run 的对照

比较对象是 10/14 隔离对照和 10/15 E1 里，用 R3 或 R4 原样指南重跑的全部单元，共 23 次，涉及 4 篇文档。每次重跑按（起点，终点，标签）和原 run 保存的预测比较，同时比较重跑之间的差别。

| 指南 | 文档 | 次数 | 每次与原 run 不同的预测数 | 重跑两两之间不同的预测数 |
| --- | --- | --- | --- | --- |
| R3 | 10577908（FALDH） | 3 | 0, 0, 0 | 0, 0, 0 |
| R3 | 1303173（G6PD） | 3 | 0, 1, 0 | 1, 0, 1 |
| R3 | 1671881（PAH） | 3 | 1, 1, 1 | 0, 0, 0 |
| R3 | 8326491（Tay-Sachs） | 5 | 全部 0 | 全部 0 |
| R4 | 10577908 | 3 | 0, 0, 0 | 0, 0, 0 |
| R4 | 1303173 | 3 | 1, 0, 0 | 1, 1, 0 |
| R4 | 1671881 | 3 | 0, 0, 0 | 0, 0, 0 |
| R4 | 8326491 | 5 | 全部 4 | 全部 0 |

怎么读这张表：

- **8 格里有 6 格**，重跑与原 run 的差别不超过重跑之间的差别。1303173 那 1 处差别在重跑之间也会出现，属于同一种波动。
- **两格是重跑全部一致、却都与原 run 不同**：
  - R4 / 8326491：Tay-Sachs disease、TSD 两处，原 run 是 SpecificDisease，5 次重跑都是 Modifier（一处标签变化记作 2 个差别，所以是 4）。
  - R3 / 1671881：原 run 在 "deficiency of hepatic phenylalanine hydroxylase" 处没有标注，3 次重跑都以正确跨度标为 DiseaseClass。gold 是 SpecificDisease，所以两种结果都不算对，"R3 下 PAH 0/3" 的结论不变。不过，"R3 把 PAH 改成漏标"这件事本身，也像是一次偶然结果。
- **这两格有一个共同点**：它们都是因为原 run 那一次的结果"特别"才被挑出来的。前者是 R4 的非目标变化，后者是 R3 新增的漏标。如果原 run 的每个预测都是一次随机抽样，那么事后专挑结果特别的案例去重跑，看到它回到常态，是正常现象。
- **没有被挑选过的预测**，比如这 4 篇文档里其余的所有预测，重跑与原 run 基本相同。如果模型版本在 08/02 之后有了大的变化，这些预测也应该大量不同，但实际没有。

## 3. 还缺什么，以及怎么补

1. **请管理员确认部署是否升级过。** Azure 部署有模型版本和自动升级设置。管理员可以查 `eastus2-gpt-5.4` 在 08/02 到 10/15 之间有没有换过版本。这一项不花调用。
2. **以后每次调用都保存响应里的 `model` 字段。** 现在的代码只保存了文本和用量。这是一处小改动，可以交给 Codex。
   - 10/16 补充：R3 排除实验的第一次尝试记录了这个字段，Azure 返回的是部署名 `eastus2-gpt-5.4`，不是模型版本（`nodes/2026-10-16_seminar/r4-attribution/isolation/attempt1_20261016_queued/`）。所以这一项查不出版本，版本只能靠第 1 项问管理员。
3. **如果需要更强的证据，加重复次数。** 用 R4 指南再标 8326491 15 次，与 E1 合计 20 次。
   - 如果出现 S，就直接证明同样的输入下 S 会随机出现。
   - 如果仍然一次 S 都没有，那么今天这个模型给出 S 的概率，单侧 95% 上限从约 45% 降到约 14%。
   - 用量按 E1 里 R4 组的实测平均推算：每次约输入 4,821、输出 15,211 token，15 次约输入 7.2 万、输出 22.8 万 token。这是估计。
4. **最直接的整轮对照（规模较大，先不建议）**：用 R4 指南把 10 篇开发文档全部重标，逐篇和原 run 比较。它同时能检验 R4 的 dev F1 提升能否复现。不过目前只有 4 篇文档有实测用量，没法可靠估算总用量。

## 核查记录

**脚本与输出**（都在 `nodes/2026-10-16_seminar/r4-attribution/nontarget/`，离线运行，没有调用 API）：

| 文件 | SHA-256 前 12 位 |
| --- | --- |
| `check_replay_identity.py` | 07978e6c82b5 |
| `check_replay_identity_output.txt` | 41f877201104 |
| `replay_vs_saved.py` | 91e09a832c2a |
| `replay_vs_saved_output.txt` | d9d5b83be509 |

**命令**：

```
python nodes/2026-10-16_seminar/r4-attribution/nontarget/check_replay_identity.py
python nodes/2026-10-16_seminar/r4-attribution/nontarget/replay_vs_saved.py
```

**数据来源**：

- 原 run 的预测：`outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/snapshot.json` 的 `diagnostics_before`（R3）和 `diagnostics_after`（R4）。
- 重跑：`nodes/2026-10-16_seminar/r4-attribution/isolation/units/` 中 c1_R3 和 c3_R4 的单元，以及 `nodes/2026-10-16_seminar/r4-attribution/nontarget/units/` 的 10 个单元。
- 代码历史：`git log` 显示 `src/llm_guideline_moderation/` 只有 2488342（08/20）一次提交；`scripts/run_iterative_refinement.py` 在 d899b86（10/06）改过 1 行。
- 原 run 的最终记录 `final/iterative_refinement_run.json` 里，没有 rationale、原始响应、用量或模型字段。
