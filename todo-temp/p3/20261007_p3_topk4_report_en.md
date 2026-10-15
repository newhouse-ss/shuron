# P3: Is the Top-4 Parallel Rewrite's 0.9155 on Dev Real? Hard-Coding Measurement, Gold-Contradicting Example Audit, and valid100 Verification

Date: 2026-10-07
Status: complete (Phase A offline analysis + Phase B valid100 measurement)

Background in plain terms: the refinement loop normally analyzes only the single largest error cluster per round (top-1). The top-k variant feeds the top 4 conflict clusters into one round instead. This report asks three things about the most typical top-4 run: whether its dev gain is genuine or hard-coded, whether its final guideline still contains examples that contradict gold, and whether the gain survives on 100 unseen validation documents (valid100).

## Conclusions (TL;DR)

1. The core problem is not solved: the generated principle is abstract, and at the guideline refinement stage the model cannot see the gold data entities provided at the discrepancy analysis stage. So once such a gold entity shows up in the TP text at refinement stage, there is a risk it gets written up in the opposite direction. Enlarging the dev set does not solve this root problem.
2. **Phase B valid100 (core result)**: the top-4 final guideline scores strict-match F1 **0.8023** on 100 unseen documents, above the top-1 control's **0.7878** (+0.0145) and the original guideline's **0.7792** (+0.0231). The dev gap 0.9155 vs 0.9091 is not credible inside the dev10 noise band (about ±0.05). **The +0.0145 on valid100 is the valid evidence**, though still a point estimate without a significance test.
3. **A2 absorption rate**: the top-4 final guideline absorbed 32% of dev10 gold strings (12/37), **below** the top-1 control's 41% (15/37). The share of added lines quoting already-correct (TP) cases is 11%, also below top-1's 15%. Parallel rewriting (handling 4 conflict groups at once) **did not increase hard-coding**; the dev F1 of 0.9155 is not caused by more answer-key leakage.
4. **A3 gold-contradicting examples**: exactly **2** exclusion examples in the top-4 final guideline conflict with gold: the two "fatal" cases from the seminar case study (`abnormal retinal vascular development`, `deficient activity of fatty aldehyde dehydrogenase`), both added by refinement. (Why exactly these same two again? Worth analyzing.) Follow-up checking shows: **in the top-4 round-1 analysis calls, the gold labels of these two cases are explicitly visible, and the exclusion examples were still written**. Adding evidence on the input side cannot prevent contradictory rules; the gap is located in the `refine_guidelines` call not seeing labeled discrepancy evidence.
5. **Gain structure**: dev gains come mainly from SpecificDisease fixes (0.79 to 0.93) and a perfect Modifier score. Valid gains are realized almost entirely as **Modifier recall** (TP +26, R 0.7156 to 0.8349) and CompositeMention (TP +5). SpecificDisease is slightly worse than top-1 on valid (over-prediction, FP 58 to 83), and DiseaseClass improves in neither arm.
6. Reference point: top-4 with 10 dev documents reaches about the same valid F1 (0.8023) as top-1 with 30 documents (0.8050, `ncbi-m-dev30`). **Fully using the data under low-resource conditions?**

## 1. Design

P3 focuses only on the most typical top-4 run (the one ending at dev 0.9155), with the top-1 main run as control:

| Arm | Run | dev10 F1 | Rounds | valid100 F1 |
|---|---|---|---|---|
| top-1 control | `outputs/ncbi_disease/20260802_gpt54-high_moderation` | 0.7972→0.9091 | 4 | 0.7878 (existing anchor) |
| **top-4 subject** | `outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10` | 0.8028→0.9155 | 2 | **0.8023 (measured here)** |
| Original guideline anchor | Unmodified released guideline | n/a | n/a | 0.7792 |

Controlled variables: the same dev10 documents, the same original guideline, n_examples=5, Azure GPT-5.4 (reasoning high, max_output_tokens=64000), the same valid100 set and scoring script (`reproduction/eval_valid.py`, strict match). The only independent variable is k in top-k (number of conflict groups handled per rewrite: 1 vs 4).

Model choice note: both 5_4 and 5_2 are configured in this machine's `.env` and passed liveness probes (2026-10-07). To stay strictly comparable with the existing top-1 valid100 anchor (0.7878, GPT-5.4 high), **Phase B still used GPT-5.4 high**. The GPT-5.2 probe result is on file; a rerun is one command away if needed.

Analyses:
- **A2** hard-coding/absorption: `reproduction/measure_hardcoding.py` (includes the top-4 row), output `reproduction/results/hardcoding.json`.
- **A3** gold-contradicting example audit: `todo-temp/p3/scan_gold_conflicts.py` (offline), output `todo-temp/p3/a3_gold_conflicts.json`.
- **A4** confusion matrix: already available; row 5 of `docs/discrepancy_matrices_seven_runs.svg` is topk4_dev10.
- **B** valid100 annotation: `reproduction/annotate_valid_resumable.py` → `outputs/20261007_ncbi_gpt54-high_valid-topk4/` (100/100, resumable), scored at `reproduction/results/ncbi-valid-topk4-gpt54/`.

## 2. A2: Absorption Rate (Hard-Coding Measurement)

Definitions (see the docstring of `measure_hardcoding.py`): absorption = how many distinct dev10 gold mention strings appear verbatim in the final guideline (and were absent from the original guideline). Added-line TP-quoting = the share of added lines that quote verbatim cases the baseline already got right (a precision view); the control column counts lines quoting conflict cases.

| Run | dev F1 | Guideline chars | Absorbed | Added lines | TP-quoting | Conflict-quoting |
|---|---|---|---|---|---|---|
| dev10 withTP (top-1) | 0.7972→0.9091 | 7367→19940 | 15/37 (41%) | 111 | 17 (15%) | 4 |
| **dev10 top-4** | 0.8028→0.9155 | 7367→19262 | **12/37 (32%)** | 97 | **11 (11%)** | 11 |
| dev10 noTP r2/r4/r5 | n/a | n/a | 0/37 | n/a | 0% | n/a |
| dev10 abstr r1/r2 | n/a | n/a | 0/37 | n/a | 0% | n/a |

Key points:
- top-4 reached a higher dev F1 in 2 rounds than top-1 in 4, with similar guideline size (19.3k vs 19.9k characters), and its absorption is **lower**. Parallelization makes each round grow faster, but it does not copy more answer keys.
- Absorption is neutral: 2 of the 12 strings top-4 absorbed (`abnormal retinal vascular development`, `deficient activity of fatty aldehyde dehydrogenase`) entered the guideline as **exclusion examples**: gold strings copied in, teaching behavior opposite to gold (see A3). Of the 15 strings top-1 absorbed, one is `deficiency of norrin`, which top-4 did not absorb (both arms miss that case).
- top-4 has far more conflict-quoting lines (11) than top-1 (4): one parallel rewrite handles 4 conflict groups, so more conflict cases get written into the guideline, as the mechanism predicts.

## 3. A3: Audit of Conflicts Between the Final Guideline and Gold (dev10)

Method: extract all quoted-string Annotate / Do-not-annotate examples from the final guideline and match them against dev10 gold with word-boundary exact matching. An exclusion example that forbids annotating a string gold actually annotates is judged `CONTRADICTS_GOLD`. Clauses that only restrict the label ("X does not count as Specific Disease" while gold labels DiseaseClass) are judged consistent. Data: `todo-temp/p3/a3_gold_conflicts.json`.

### 3.1 Examples overlapping gold: 3, of which 2 truly conflict

| Line | Quoted example | Guideline stance | Gold label | Origin | Initial model | Final model | Verdict |
|---|---|---|---|---|---|---|---|
| L12 | "autosomal recessive disorder" | Does not count as Specific Disease | DiseaseClass ×1 (10577908) | Added by refinement | TP | TP | Consistent (label rule) |
| **L228** | "abnormal retinal vascular development" | **Do not annotate** (when only a mechanism/process description) | **DiseaseClass** ×1 (10484772) | Added by refinement | miss | miss | **Conflict** |
| **L252** | "deficient activity of fatty aldehyde dehydrogenase" | **Do not auto-annotate** (when only a biochemical/enzyme-activity readout) | **SpecificDisease** ×1 (10577908) | Added by refinement | miss | miss | **Conflict** |

- The two conflicting examples are exactly the "fatal" items from the seminar case study (`archive/2026-10-02_seminar-conflict-casestudy/`). Both the top-4 and top-1 final guidelines wrote them in. P1 (delete the clause) and P2 (scoped rewrite) also failed to rescue these two misses.
- Exclusion examples inherited from the original guideline (such as L208 "Neisseria" alone not annotated) were rechecked with word boundaries and show no conflict with gold (gold annotates the full phrase "Chronic neisserial infection").

### 3.2 Gain structure: where the F1 comes from

dev10 strict match, initial to final:

| Label | Initial (TP/FP/FN, F1) | Final (TP/FP/FN, F1) |
|---|---|---|
| SpecificDisease | 32/5/12, 0.7901 | 39/1/5, **0.9286** |
| DiseaseClass | 6/4/3, 0.6316 | 6/2/3, 0.7059 |
| Modifier | 18/2/1, 0.9231 | 19/0/0, **1.0000** |
| CompositeMention | 1/0/1, 0.6667 | 1/0/1, 0.6667 |
| Total | 57/11/17, 0.8028 | 65/3/9, **0.9155** |

The gain comes almost entirely from SpecificDisease recall fixes and false-positive compression (FP 11 to 3).

### 3.3 Remaining errors of the final model

9 FN + 3 FP, of which 3 pairs are **same-span label disagreements** (gold and prediction each count one side):

| Span | Gold | Prediction | Document |
|---|---|---|---|
| exudative retinal detachment | DiseaseClass | SpecificDisease | 10484772 |
| PAH deficiencies | SpecificDisease | DiseaseClass | 1671881 |
| Chronic neisserial infection | SpecificDisease | DiseaseClass | 6859721 |

The 6 true pure misses: `abnormal retinal vascular development`, `deficient activity of fatty aldehyde dehydrogenase` (both explicitly forbidden by exclusion examples, see 3.1), `intraretinal and subretinal lipid accumulation` (CompositeMention), `deficiency of norrin`, `deficiency in G6PD`, `fever`. Only 2 of the 9 FN are covered by guideline text (those two exclusion examples); the other 7 are never discussed by the guideline. **The remaining errors are mainly not wrongly written guidelines, but guideline silence.**

### 3.4 Follow-up check: gold evidence on the input side does not prevent exclusion examples

For the hypothesis "if the model sees more clusters' gold data, it will avoid writing contradictory rules", we fact-checked the existing snapshots (all offline):

- **top-1 Round 3** (the round that wrote the exclusion example): FALDH appears twice in the prompt, but only inside the **original text** of the verified/TP constraint block. That block lists only already-correct matched annotations, so FALDH, being missed, carries no gold label. The Round 3 input indeed lacked this evidence: this supports the factual claim "it was not given at the time".
- **But top-4 Round 1** (fed 4 clusters): `infer_discrepancy_patterns_1` / `generate_moderation_principle_1` explicitly contain `Gold: SpecificDisease, LLM: O, Entity Text: "deficient activity of fatty aldehyde dehydrogenase"`; `abnormal retinal vascular development` likewise appears with `Gold: DiseaseClass` in the two analysis calls of `_3`. **The exclusion examples were still written into Round 1's guidelines_after and survived to the final version** (Round 2 again showed the gold labels and kept them).
- Failure mechanism: the entity names of both cases disappear entirely from the 4 generated principles (`fatty aldehyde` / `retinal vascular` occur 0 times in `moderation_principle`): the gold evidence is dropped at the "cluster to principle" abstraction step. The `refine_guidelines` call that actually writes the rules sees only the abstract principle plus the TP constraint block, and **never sees discrepancy examples with gold labels from start to finish**.

Conclusion: adding clusters on the input side (the top-k mechanism itself) cannot prevent gold-contradicting rules; P1/P2 showed that editing the clause on the output side cannot rescue them either. The gap is the information structure of the rewrite call: either inject labeled gold cases directly into `refine_guidelines` (input-side fix), or check new rules against gold after writing (output-side fix, the direction of the repo's existing postverify probe).

## 4. Phase B: valid100 Verification (GPT-5.4 high, 100 documents)

Commands:

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

Overall results (strict match, 100 documents, 791 gold entities):

| Guideline | P | R | F1 | TP/FP/FN |
|---|---|---|---|---|
| Original guideline | 0.8011 | 0.7585 | 0.7792 | 600/149/191 |
| top-1 final | 0.8121 | 0.7649 | 0.7878 | 605/140/186 |
| **top-4 final** | 0.8095 | **0.7952** | **0.8023** | 629/148/162 |

Per-label F1:

| Label | Original | top-1 | top-4 | top-4 vs top-1 |
|---|---|---|---|---|
| SpecificDisease | 0.8400 | **0.8512** | 0.8244 | **-0.027** (FP 58→83, over-prediction) |
| DiseaseClass | **0.6581** | 0.6500 | 0.6372 | -0.013 (recall 0.61→0.57) |
| Modifier | 0.7642 | 0.7647 | **0.8505** | **+0.086** (TP +26, recall +0.12) |
| CompositeMention | 0.6098 | 0.6667 | **0.7792** | +0.113 (TP +5) |

Valid disagreement categories (soft match): label_mismatch 57, boundary 45, FN 55, FP 45; the dominant group is SpecificDisease↔SpecificDisease boundary issues (n=32).

## 5. Overall Conclusions

1. **The dev gain direction holds on unseen data.** top-4's 0.9155 is not a hard-coding artifact (absorption 32% < top-1's 41%), and valid100 reproduces the ordering: top-4 0.8023 > top-1 0.7878 > original 0.7792. The two arms have similar dev-to-valid drops (-0.113 vs -0.121): top-4 shows no larger generalization decay. Efficiency view: top-4 with 10 dev documents matches top-1 with 30 documents on valid (0.8023 vs 0.8050).
2. **Gains and costs both have concrete locations.** Gains concentrate in Modifier recall (+26 TP, consistent with Modifier going to 1.0 on dev) and CompositeMention. Costs are SpecificDisease over-prediction (FP 58 to 83) and DiseaseClass recall decline: the SpecificDisease improvement on dev did not fully transfer.
3. **Side effects of rule composition persist, but at a controllable cost.** The two gold-contradicting exclusion examples appear in the top-4 final guideline as usual, yet show no discernible cost on valid100 (these two specific strings are extremely rare in valid). They are firm evidence of "locally wrong guideline text", not a barrier to the overall gain. Together with 3.4 and P1/P2: neither the input side (gold evidence from more clusters) nor the output side (deleting or rewriting the clause) can fix them; the gap is that the rewrite call never sees labeled evidence.
4. **Verification still needed**: (a) point estimates; a paired bootstrap on `per_document.json` can give a confidence interval for +0.0145; (b) valid scoring of the other top-4 replicate runs (dev 0.8252/0.8552/0.8841) to test the stability of this gain; (c) a structural-fix arm: inject gold-labeled missed cases into `refine_guidelines` and test whether contradictory exclusion examples disappear without sacrificing the precision guardrail.

## 6. Verification Record

- `reproduction/measure_hardcoding.py --show-strings` (rerun 2026-10-07, includes the top-4 row) → `reproduction/results/hardcoding.json`
- `python todo-temp/p3/scan_gold_conflicts.py` → `todo-temp/p3/a3_gold_conflicts.json` (example audit: 3 overlaps / 2 conflicts; 9 FN and 3 FP listed one by one; per-label F1 recomputation matches the snapshot)
- Section 3.4 snapshot check: top-1 `rounds/iteration_03/snapshot.json` (FALDH only in the TP block's original text, no gold label in the infer prompt); top-4 `rounds/iteration_01|02/snapshot.json` (FALDH/retinal-vascular appear with gold labels in the analysis calls, exclusion examples still in `guidelines_after`)
- API probes: `OpenAIProvider.from_azure_env("5_4"/"5_2", reasoning_effort="high")`, one `complete` call each, both returned OK in about 6 seconds (2026-10-07)
- Phase B: background task `bash-fvgaexuv`, 100/100 documents complete (about 5.9 hours, resumable with no interruption); scoring output `reproduction/results/ncbi-valid-topk4-gpt54/{metrics.json,per_document.json,discrepancies.json,report.txt}`, `--require-complete` passed
- Focal case judgments are cross-consistent with the P0/P1/P2 reports (norrin/FALDH/retinal vascular missed, spasticity fixed)
