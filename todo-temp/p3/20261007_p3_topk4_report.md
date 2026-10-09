# P3：Top-4 并行改写在 dev 上的 0.9155 是否真实？——硬编码测量、gold 相反示例审计与 valid100 验证

日期：2026-10-07
状态：完成（Phase A 离线分析 + Phase B valid100 实测）

---

## 结论（TL;DR）

1. 并没有解决核心问题：生成的Principle是抽象的，在guideline refinement阶段并不能看到在discrepancy analysis阶段提供的gold data entities，所以一旦这个gold data entities出现在guideline refinement阶段的TP的文本中，就有被误标为相反方向的风险。所以扩大dev集合并不能解决根本问题。
2. **B 阶段 valid100（核心结果）**：top-4 终版指南在 100 篇未见文档上 strict-match F1 **0.8023**，高于 top-1 对照的 **0.7878**（+0.0145）和原指南的 **0.7792**（+0.0231）。dev 上 0.9155 vs 0.9091 的差距在 dev10 噪声带（约 ±0.05）内不可信，**valid100 的 +0.0145 才是有效证据**——但仍是单点估计，未做显著性检验。
2. **A2 吸收率**：top-4 终版指南吸收了 dev10 gold 字符串的 32%（12/37），**低于** top-1 对照的 41%（15/37）；新增行中引用"已答对案例"（TP）的比例 11%，也低于 top-1 的 15%。并行改写（一次处理 4 个矛盾组）**没有加剧硬编码**，dev F1 的 0.9155 不是更多答案键泄漏造成的。
3. **A3 gold 相反示例**：top-4 终版指南中与 gold 冲突的排除示例**恰好 2 条**，即研讨会案例分析的两个"致命"案例（`abnormal retinal vascular development`、`deficient activity of fatty aldehyde dehydrogenase`），均为 refinement 新增（**牛魔的为什么又是这么两个相同的？值得分析一下**）。补充查证显示：**top-4 第 1 轮的分析调用里这两个案例的 gold 标签明确可见，排除示例仍被写入**——输入侧加证据防不住相反规则，缺口定位在 `refine_guidelines` 调用看不到带标签的 discrepancy 证据。
4. **收益结构**：dev 收益主要来自 SpecificDisease 修复（0.79→0.93）与 Modifier 满分；valid 收益几乎全部兑现为 **Modifier 召回**（TP +26，R 0.7156→0.8349）与 CompositeMention（TP +5）；SpecificDisease 在 valid 上反而略逊于 top-1（过预测，FP 58→83），DiseaseClass 两臂均无改善。
5. 参照系：top-4 用 10 篇开发文档达到的 valid F1（0.8023）≈ top-1 用 30 篇达到的水平（0.8050，`ncbi-m-dev30`）。**Fully use the data under low-resource condition?**

## 1. 实验设计

P3 只聚焦最典型的 top-4 运行（dev 终点 0.9155 那次），对照为 top-1 主运行：

| 臂 | 运行 | dev10 F1 | 轮数 | valid100 F1 |
|---|---|---|---|---|
| top-1 对照 | `outputs/ncbi_disease/20260802_gpt54-high_moderation` | 0.7972→0.9091 | 4 | 0.7878（已有锚点） |
| **top-4 受试** | `outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10` | 0.8028→0.9155 | 2 | **0.8023（本次实测）** |
| 原指南锚点 | 未修改的发行指南 | — | — | 0.7792 |

控制变量：同一批 dev10 文档、同一原指南、n_examples=5、Azure GPT-5.4（reasoning high、max_output_tokens=64000）、同一 valid100 集合与评分脚本（`reproduction/eval_valid.py`，strict match）。唯一自变量是 top-k 的 k（一次改写处理的矛盾组数：1 vs 4）。

模型选择说明：本机 `.env` 中 5_4 与 5_2 均已配置且探活成功（2026-10-07）。为保证与既有 top-1 valid100 锚点（0.7878，GPT-5.4 high）严格可比，**B 阶段仍用 GPT-5.4 high**；GPT-5.2 探活结果留档，需要时可一键复跑。

分析内容：
- **A2** 硬编码/吸收率：`reproduction/measure_hardcoding.py`（含 top-4 行），输出 `reproduction/results/hardcoding.json`。
- **A3** gold 相反示例审计：`todo-temp/p3/scan_gold_conflicts.py`（离线），输出 `todo-temp/p3/a3_gold_conflicts.json`。
- **A4** 混淆矩阵：已有，`docs/discrepancy_matrices_seven_runs.svg` 第 5 行即 topk4_dev10。
- **B** valid100 标注：`reproduction/annotate_valid_resumable.py` → `outputs/20261007_ncbi_gpt54-high_valid-topk4/`（100/100，断点续跑），评分 `reproduction/results/ncbi-valid-topk4-gpt54/`。

## 2. A2：吸收率（硬编码测量）

口径（详见 `measure_hardcoding.py` 文档字符串）：absorption = dev10 的不同 gold 提及字符串中，有多少逐字进入了终版指南（且原指南中没有）；added-line TP-quoting = 新增行中逐字引用"基线已答对案例"的比例（precision 视角），对照列为引用矛盾案例的行数。

| 运行 | dev F1 | 指南字符 | absorbed | 新增行 | TP 引用 | 矛盾引用 |
|---|---|---|---|---|---|---|
| dev10 withTP（top-1） | 0.7972→0.9091 | 7367→19940 | 15/37 (41%) | 111 | 17 (15%) | 4 |
| **dev10 top-4** | 0.8028→0.9155 | 7367→19262 | **12/37 (32%)** | 97 | **11 (11%)** | 11 |
| dev10 noTP r2/r4/r5 | — | — | 0/37 | — | 0% | — |
| dev10 abstr r1/r2 | — | — | 0/37 | — | 0% | — |

要点：
- top-4 用 2 轮达到比 top-1（4 轮）更高的 dev F1，指南体量相当（19.3k vs 19.9k 字符），**吸收率反而更低**。并行化让每轮长得更快，但没有多抄答案键。
- 吸收是中性的：top-4 吸收的 12 条字符串中有 2 条（`abnormal retinal vascular development`、`deficient activity of fatty aldehyde dehydrogenase`）是以**排除示例**身份进入指南的——抄进来的是 gold 字符串，教的是与 gold 相反的行为（见 A3）。top-1 吸收的 15 条中包含 `deficiency of norrin`，top-4 未吸收该条（该案例两臂均漏标）。
- top-4 的矛盾引用行（11）远多于 top-1（4）：并行改写一轮处理 4 组矛盾，更多矛盾案例被写进指南，符合机制预期。

## 3. A3：终版指南与 gold 的冲突审计（dev10）

方法：提取终版指南中所有带引号字符串的 Annotate / Do-not-annotate 示例，在 dev10 gold 中按词边界精确匹配；排除示例若禁止标注 gold 实际标注的字符串，判为 `CONTRADICTS_GOLD`；仅限定标签的条款（"X 不算 Specific Disease" 且 gold 标 DiseaseClass）判为一致。数据：`todo-temp/p3/a3_gold_conflicts.json`。

### 3.1 与 gold 重叠的示例：3 条，真正冲突 2 条

| 行 | 示例引文 | 指南立场 | gold 标注 | 来源 | 初始模型 | 终版模型 | 判定 |
|---|---|---|---|---|---|---|---|
| L12 | "autosomal recessive disorder" | 不算 Specific Disease | DiseaseClass ×1 (10577908) | refinement 新增 | TP | TP | 一致（标签规则） |
| **L228** | "abnormal retinal vascular development" | **不标注**（仅机制/过程描述时） | **DiseaseClass** ×1 (10484772) | refinement 新增 | miss | miss | **冲突** |
| **L252** | "deficient activity of fatty aldehyde dehydrogenase" | **不自动标注**（仅生化/酶活读出时） | **SpecificDisease** ×1 (10577908) | refinement 新增 | miss | miss | **冲突** |

- 两条冲突示例就是研讨会案例分析（`archive/2026-10-02_seminar-conflict-casestudy/`）中的"致命"项，top-4 与 top-1 的终版指南都把它们写了进去；P1（删从句）与 P2（限定作用域）也都无法救回这两个漏标。
- 原指南继承的排除示例（如 L208 "Neisseria" 单独不标注）经词边界复核后与 gold 无冲突（gold 标的是完整短语 "Chronic neisserial infection"）。

### 3.2 收益结构：F1 从哪来

dev10 strict match，初始 → 终版：

| 标签 | 初始 (TP/FP/FN, F1) | 终版 (TP/FP/FN, F1) |
|---|---|---|
| SpecificDisease | 32/5/12, 0.7901 | 39/1/5, **0.9286** |
| DiseaseClass | 6/4/3, 0.6316 | 6/2/3, 0.7059 |
| Modifier | 18/2/1, 0.9231 | 19/0/0, **1.0000** |
| CompositeMention | 1/0/1, 0.6667 | 1/0/1, 0.6667 |
| 总计 | 57/11/17, 0.8028 | 65/3/9, **0.9155** |

收益几乎全部来自 SpecificDisease 的召回修复与误报压缩（FP 11→3）。

### 3.3 终版模型剩余错误

FN 9 条 + FP 3 条，其中 3 对是**同 span 标签不一致**（gold 与预测各算一端）：

| span | gold | 预测 | 文档 |
|---|---|---|---|
| exudative retinal detachment | DiseaseClass | SpecificDisease | 10484772 |
| PAH deficiencies | SpecificDisease | DiseaseClass | 1671881 |
| Chronic neisserial infection | SpecificDisease | DiseaseClass | 6859721 |

真正的纯漏标 6 条：`abnormal retinal vascular development`、`deficient activity of fatty aldehyde dehydrogenase`（均被排除示例显式禁止，见 3.1）、`intraretinal and subretinal lipid accumulation`（CompositeMention）、`deficiency of norrin`、`deficiency in G6PD`、`fever`。9 条 FN 中仅 2 条被指南文本覆盖（就是那两条排除示例），其余 7 条指南未曾讨论——**剩余错误主要不是指南写错，而是指南没覆盖到**。

### 3.4 补充查证：输入侧的 gold 证据防不住排除示例

针对"把更多 cluster 的 gold 数据给模型，它就会规避写相反规则"的假设，对既有快照做了事实核查（全部离线）：

- **top-1 第 3 轮**（写下排除示例的那轮）：FALDH 在 prompt 中出现 2 次，但都在 verified/TP 约束块的**原文**里；该块只列已答对的匹配标注，FALDH 因漏标而不带 gold 标签。第三轮输入确实缺这份证据——这支持"当时没给"的事实判断。
- **但 top-4 第 1 轮**（喂 4 个 cluster）：`infer_discrepancy_patterns_1` / `generate_moderation_principle_1` 中明确写着 `Gold: SpecificDisease, LLM: O, Entity Text: "deficient activity of fatty aldehyde dehydrogenase"`；`abnormal retinal vascular development` 同样带 `Gold: DiseaseClass` 出现在 `_3` 的两个分析调用里。**排除示例仍被写进第 1 轮的 guidelines_after 并留到终版**（第 2 轮同样展示了 gold 标签，同样保留）。
- 失败机制：生成的 4 条原则中两个实体名全部消失（`moderation_principle` 中 `fatty aldehyde` / `retinal vascular` 出现 0 次）——gold 证据在"cluster → 原则"抽象步被丢弃；而真正写规则的 `refine_guidelines` 调用只看到抽象原则 + TP 约束块，**从头到尾见不到带 gold 标签的 discrepancy 示例**。

结论：输入侧加 cluster（top-k 机制本身）不能防止 gold 相反规则；P1/P2 已证明输出侧改从句也救不回。缺口在 rewrite 调用的信息结构——要么把带标签的 gold 案例直接注入 `refine_guidelines`（输入侧修复），要么写完后对照 gold 校验新规则（输出侧修复，即 repo 已有的 postverify 探针方向）。

## 4. B 阶段：valid100 验证（GPT-5.4 high，100 篇）

命令：

```
python reproduction/annotate_valid_resumable.py \
  --input-dir data/datasets/ncbi_disease/valid \
  --guidelines outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/final/final_guidelines.txt \
  --output-dir outputs/20261007_ncbi_gpt54-high_valid-topk4
python reproduction/eval_valid.py --gold-dir data/datasets/ncbi_disease/valid \
  --pred-dir outputs/20261007_ncbi_gpt54-high_valid-topk4 \
  --label ncbi-valid-topk4-gpt54 --entities data/schemas/ncbi_entities.schema.json \
  --require-complete
```

总体结果（strict match，100 篇、791 个 gold 实体）：

| 指南 | P | R | F1 | TP/FP/FN |
|---|---|---|---|---|
| 原指南 | 0.8011 | 0.7585 | 0.7792 | 600/149/191 |
| top-1 终版 | 0.8121 | 0.7649 | 0.7878 | 605/140/186 |
| **top-4 终版** | 0.8095 | **0.7952** | **0.8023** | 629/148/162 |

逐标签 F1：

| 标签 | 原指南 | top-1 | top-4 | top-4 vs top-1 |
|---|---|---|---|---|
| SpecificDisease | 0.8400 | **0.8512** | 0.8244 | **-0.027**（FP 58→83，过预测） |
| DiseaseClass | **0.6581** | 0.6500 | 0.6372 | -0.013（召回 0.61→0.57） |
| Modifier | 0.7642 | 0.7647 | **0.8505** | **+0.086**（TP +26，召回 +0.12） |
| CompositeMention | 0.6098 | 0.6667 | **0.7792** | +0.113（TP +5） |

valid 矛盾类别（soft match）：label_mismatch 57、boundary 45、FN 55、FP 45；主导组为 SpecificDisease↔SpecificDisease 边界问题（n=32）。

## 5. 综合结论

1. **dev 收益方向在未见数据上成立。** top-4 的 0.9155 不是硬编码假象（吸收率 32% < top-1 的 41%），valid100 复现了排序：top-4 0.8023 > top-1 0.7878 > 原指南 0.7792。两臂 dev-valid 落差相近（-0.113 vs -0.121），top-4 没有更大的泛化衰减。效率视角：top-4 用 10 篇开发文档 ≈ top-1 用 30 篇的 valid 水平（0.8023 vs 0.8050）。
2. **收益与代价都有具体落点。** 收益集中在 Modifier 召回（+26 TP，与 dev 上 Modifier→1.0 方向一致）和 CompositeMention；代价是 SpecificDisease 过预测（FP 58→83）和 DiseaseClass 召回下滑——dev 上 SpecificDisease 的改善没有完整迁移。
3. **规则组合的副作用仍然存在但代价可控。** 两个 gold 相反排除示例照常出现在 top-4 终版指南里，但在 valid100 上没有可辨代价（这两个具体字符串在 valid 中占比极小）；它们是"指南局部写错"的确证而非整体收益的障碍。结合 3.4 与 P1/P2：输入侧（更多 cluster 的 gold 证据）与输出侧（删改从句）都修不掉它们，缺口在 rewrite 调用见不到带标签证据。
4. **需要补做的验证**：（a）单点估计，可对 `per_document.json` 做配对 bootstrap 估计 +0.0145 的置信区间；（b）top-4 其余重复运行（dev 0.8252/0.8552/0.8841 三次）的 valid 评分，检验该收益的稳定性；（c）结构修复臂：把带 gold 标签的漏标案例注入 `refine_guidelines`，检验能否在不牺牲精度护栏的前提下消除相反排除示例。

## 6. 核查记录

- `reproduction/measure_hardcoding.py --show-strings`（2026-10-07 重跑，含 top-4 行）→ `reproduction/results/hardcoding.json`
- `python todo-temp/p3/scan_gold_conflicts.py` → `todo-temp/p3/a3_gold_conflicts.json`（示例审计 3 条重叠 / 2 条冲突；FN 9、FP 3 逐条列出；逐标签 F1 复算与快照一致）
- 3.4 节快照核查：top-1 `rounds/iteration_03/snapshot.json`（FALDH 仅在 TP 块原文，infer 提示中无 gold 标签）；top-4 `rounds/iteration_01|02/snapshot.json`（FALDH/retinal-vascular 带 gold 标签出现于分析调用，排除示例仍在 `guidelines_after`）
- API 探活：`OpenAIProvider.from_azure_env("5_4"/"5_2", reasoning_effort="high")` 各一次 `complete` 调用，均约 6 秒返回 OK（2026-10-07）
- B 阶段：后台任务 `bash-fvgaexuv`，100/100 篇完成（约 5.9 小时，断点续跑无中断）；评分输出 `reproduction/results/ncbi-valid-topk4-gpt54/{metrics.json,per_document.json,discrepancies.json,report.txt}`，`--require-complete` 通过
- 焦点案例判定与 P0/P1/P2 报告交叉一致（norrin/FALDH/retinal vascular 漏标、spasticity 修复）
