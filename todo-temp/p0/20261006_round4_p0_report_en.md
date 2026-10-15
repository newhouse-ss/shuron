# P0: Round 4 Annotation Changes and Regression Audit

Date: 2026-10-06. Run under review: `20260802_gpt54-high_moderation`, NCBI Disease, Azure/OpenAI eastus2-gpt-5.4, reasoning_effort=high. This report reviews saved outputs offline: no new model calls were made, and the P1 ablation was not run here.

Background in plain terms: the pipeline refines an annotation guideline in rounds. Each round finds disagreements between gold labels and current predictions (called discrepancies), rewrites the guideline, and re-annotates the development documents. TP/FP/FN count correct spans, wrongly predicted spans, and missed gold spans under strict matching. This report checks what actually changed after Round 4.

## Conclusions

**Round 4 raised the overall score on this development batch, but it fixed only 1 of the 3 targeted misses, and it introduced 1 new regression.**

- Overall: TP **63 to 65**, FP **5 to 4**, FN **11 to 9**, F1 **0.8873 to 0.9091**. Entity level changes: **3 fixes and 1 new regression**, a net gain of 2 TP.
- This round targeted three missed SpecificDisease mentions. Only "deficiency of hepatic phenylalanine hydroxylase" recovered. FALDH and the specific span "deficiency in G6PD" are still missed. The other two fixes (Tay-Sachs disease and the TSD type error) are outside the targeted cluster.
- The new regression is "cutaneous vasculitis": SpecificDisease became DiseaseClass. The predicted spans and label sets of the other 7 documents are exactly identical to the state after Round 3.
- The norrin and FALDH misses predate Round 3. Round 4 added a norrin exclusion example and kept, with rewording, the FALDH exclusion example; both texts still contradict gold. These pre-existing misses must not be reported as new Round 4 regressions.
- The saved results confirm the changes above, but they cannot prove that any particular "do not apply" restriction caused them. The causal question is left to P1/P2.

## 1. What is compared, and how

**R0** is the annotation with the initial guideline. **After R1 to after R4** are the annotations after each accepted round. "Before Round 3" equals after R2; "before Round 4" equals after R3. Throughout this report, "new regression" means an entity that exactly matched gold in the previous state and no longer matches in this one, without presuming that any particular rule caused it.

The input is the same batch of **10 development documents sampled from the training set, 74 gold entities**, sample seed=42, n_examples=5. These are development results; they are not evidence about validation performance or expert-level ability.

Checks passed:

1. Document IDs agree across all states, and the saved gold spans and types agree with the local corpus gold.
2. Gold and predicted texts match the corresponding document spans; no duplicate annotations were found.
3. The after-R3 diagnostics are identical to the before-R4 diagnostics, and the guideline texts connect consistently; the final diagnostics equal after-R4.
4. Strict TP/FP/FN/F1 recomputed from per-entity annotations agree with the saved loop summary and the PubAnnotation evaluation.
5. Re-clustering with the current framework's error clustering function reproduces the saved summary.all_clusters.

Evidence: [input document list](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/inputs/sampled_train_documents.json), [run config](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/inputs/resolved_run_config.json), [Round 3 snapshot](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/snapshot.json), [Round 4 snapshot](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/snapshot.json).

## 2. Overall result: the score gain includes changes outside the targeted cluster

| State | TP | FP | FN | Predicted entities | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| After R2 (before R3) | 61 | 7 | 13 | 68 | 0.8971 | 0.8243 | 0.8592 |
| After R3 (before R4) | 63 | 5 | 11 | 68 | 0.9265 | 0.8514 | 0.8873 |
| After R4 | 65 | 4 | 9 | 69 | 0.9420 | 0.8784 | 0.9091 |

The F1 gain of Round 4 is **0.0218** (about 2.18 points). Of the 63 TP after R3, 62 stayed correct and 1 turned wrong; 3 new TP were added, giving the final 65.

Breakdown by gold category:

| Category | Gold count | After R3 TP/FP/FN | After R4 TP/FP/FN | F1: after R3 to after R4 |
| --- | --- | --- | --- | --- |
| SpecificDisease | 44 | 36/1/8 | 38/1/6 | 0.8889 to 0.9157 |
| DiseaseClass | 9 | 7/2/2 | 7/3/2 | 0.7778 to 0.7368 |
| Modifier | 19 | 19/2/0 | 19/0/0 | 0.9500 to 1.0000 |
| CompositeMention | 2 | 1/0/1 | 1/0/1 | 0.6667 to 0.6667 |

SpecificDisease gained 2 TP net. The two Modifier FP disappeared because Tay-Sachs disease and TSD were relabeled as the correct SpecificDisease. DiseaseClass gained one extra FP from cutaneous vasculitis. **The overall gain happened at the same time as one category got worse.**

## 3. What this round actually targeted, and the full history of the related cases

The cases below come from the infer_discrepancy_patterns prompts saved in each round; the actual inputs can be checked: [Round 3 prompt](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/infer_discrepancy_patterns.txt), [Round 4 prompt](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/infer_discrepancy_patterns.txt).

- **Round 3: Gold DiseaseClass / Pred O, 3 cases.** abnormal retinal vascular development, deficiency of norrin, spasticity.
- **Round 4: Gold SpecificDisease / Pred O, 3 cases.** deficient activity of fatty aldehyde dehydrogenase, deficiency in G6PD, deficiency of hepatic phenylalanine hydroxylase.

Abbreviations: S=SpecificDisease, D=DiseaseClass, M=Modifier, C=CompositeMention, O=no predicted entity on the gold span. Positions use zero-based half-open intervals [start,end) to distinguish different occurrences in the same document.

| Document and position | Entity | Gold | R0 | After R1 | After R2 | After R3 | After R4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10484772 [186,223) | abnormal retinal vascular development | D | O | O | O | O | O |
| 10484772 [949,969) | deficiency of norrin | D | O | O | O | O | O |
| 10577908 [228,238) | spasticity | D | D | O | O | D | D |
| 10577908 [245,295) | deficient activity of fatty aldehyde dehydrogenase | S | O | O | O | O | O |
| 1303173 [1559,1577) | deficiency in G6PD | S | O | O | O | O | O |
| 1671881 [138,185) | deficiency of hepatic phenylalanine hydroxylase | S | S | S | S | O | S |

From this we can conclude:

- **The one fixed case among the Round 3 targets is spasticity.** Its saved gold label in this run is DiseaseClass; it was correct after R3 and stayed correct after R4. It was correct initially, lost after R1, and only recovered at R3.
- abnormal retinal vascular development and deficiency of norrin have been missed from the initial state through R4.
- FALDH and the specific span deficiency in G6PD have also been missed throughout; they cannot be called new R3 regressions. Other entity occurrences in the G6PD document are annotated correctly, so this finding must not be generalized to "all G6PD mentions are missed".
- **PAH deficiency was a true positive newly lost at R3 and recovered by R4.** So this round's targeted fix mainly restored a regression from the previous round; the two older misses were not fixed.

If earlier discussions treated the gold label of spasticity as SpecificDisease, that should be corrected to the saved DiseaseClass recorded here. This report did not change gold.

## 4. All entity level changes in Round 4

Diffing the full prediction sets of the 10 documents found **4 gold entities whose results changed, spread over 3 documents**: one new annotation and three same-span type changes; no other predicted span or type changed.

| Document and position | Entity | Gold | After R3 | After R4 | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1671881 [138,185) | deficiency of hepatic phenylalanine hydroxylase | S | O | S | Fix |
| 6859721 [646,666) | cutaneous vasculitis | S | S | D | New regression |
| 8326491 [193,210) | Tay-Sachs disease | S | M | S | Fix |
| 8326491 [213,216) | TSD | S | M | S | Fix |

The three changed documents with strict counts:

| Document | After R3 TP/FP/FN | After R4 TP/FP/FN | Change |
| --- | --- | --- | --- |
| 1671881 | 4/1/2 | 5/1/1 | PAH deficiency recovered, TP+1, FN-1 |
| 6859721 | 11/1/1 | 10/2/2 | cutaneous vasculitis turned wrong, TP-1, FP+1, FN+1 |
| 8326491 | 4/2/2 | 6/0/0 | Tay-Sachs disease and TSD fixed, TP+2, FP-2, FN-2 |

Tay-Sachs disease and TSD come from the same context, so they cannot be read as two independent replicates. Here "cutaneous vasculitis" means the occurrence at [646,666); the other occurrence at [192,212) is correct in both R3 and R4. The label sequence of this span across R0 to R4 is **D, S, D, S, D**, flipping repeatedly across rounds. This strengthens the need to keep checking stability, but it cannot separate the effect of rule edits from annotation randomness.

## 5. Error confusion matrices

These use the run's saved error clustering. **Rows are gold, columns are model predictions.** The matrices count errors only, not TP:

- A non-O diagonal cell means the same type but a mismatched span, **not a correct annotation**.
- The O column holds the misses; the O row holds extra predictions.
- O/O=0 is not a true negative count: NER does not enumerate every non-entity character.
- A type error and a span error each count as one discrepancy, but strict scoring also records one FP and one FN. So the matrix total does not equal FP+FN.

### Before Round 3 (after R2)

| Gold \ Pred | SpecificDisease | DiseaseClass | Modifier | CompositeMention | O |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 1 | 3 | 2 | 0 | 2 |
| DiseaseClass | 1 | 0 | 0 | 0 | 3 |
| Modifier | 0 | 0 | 0 | 0 | 0 |
| CompositeMention | 0 | 0 | 0 | 0 | 1 |
| O | 0 | 0 | 0 | 0 | 0 |

Total discrepancies **13**: 6 type errors, 1 span error, 6 misses.

### After Round 3 (before Round 4)

| Gold \ Pred | SpecificDisease | DiseaseClass | Modifier | CompositeMention | O |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 1 | 2 | 2 | 0 | 3 |
| DiseaseClass | 0 | 0 | 0 | 0 | 2 |
| Modifier | 0 | 0 | 0 | 0 | 0 |
| CompositeMention | 0 | 0 | 0 | 0 | 1 |
| O | 0 | 0 | 0 | 0 | 0 |

Total discrepancies **11**: 4 type errors, 1 span error, 6 misses. Round 3's overall gain was also not limited to its targeted cluster: besides spasticity recovering, the pre-existing type error of exudative retinal detachment was corrected and cutaneous vasculitis returned to the correct type, while PAH deficiency was lost.

### After Round 4

| Gold \ Pred | SpecificDisease | DiseaseClass | Modifier | CompositeMention | O |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 1 | 3 | 0 | 0 | 2 |
| DiseaseClass | 0 | 0 | 0 | 0 | 2 |
| Modifier | 0 | 0 | 0 | 0 | 0 |
| CompositeMention | 0 | 0 | 0 | 0 | 1 |
| O | 0 | 0 | 0 | 0 | 0 |

Total discrepancies **9**: 3 type errors, 1 span error, 5 misses. Relative to before R4:

| Error group | Before | After | Case mapping |
| --- | --- | --- | --- |
| Gold S / Pred O | 3 | 2 | PAH deficiency recovered |
| Gold S / Pred M | 2 | 0 | Tay-Sachs disease and TSD fixed |
| Gold S / Pred D | 2 | 3 | new cutaneous vasculitis regression |
| Gold D / Pred O | 2 | 2 | abnormal development and norrin unchanged |
| Gold S / Pred S (span error) | 1 | 1 | unilateral retinal telangiectasis unchanged |
| Gold C / Pred O | 1 | 1 | lipid accumulation CompositeMention unchanged |

## 6. What the rule edits can and cannot explain

Comparing snapshot.guidelines_before and guidelines_after confirms that R4 mainly made these edits:

| Edit | Location in saved text | Observed result |
| --- | --- | --- |
| Rule 1 added "deficiency/absence/reduced-function expression + specific molecular entity" as a SpecificDisease condition, while excluding pure biochemical measurements or mechanism descriptions | R4 guideline lines 12 to 13 | Of the three targets, only PAH deficiency recovered |
| The original molecular/process exclusion now starts with "Outside the deficit/absence/reduced-function case described above" | Line 14 | The restriction text was narrowed, but the other two targeted misses remain |
| Rule 5 requires keeping the molecular complement needed to identify a pathological deficiency state | Line 101 | The full gold span of PAH deficiency was restored |
| Added a C7 deficiency positive example and a new deficiency of norrin exclusion example | Lines 43 to 52 | norrin is still O; its exclusion text contradicts gold D |
| Kept and rewrote the FALDH exclusion example added at R3; other entries continue the same exclusion logic | Lines 54 to 57, 167 to 168, 263 to 264 | FALDH is still O; the exclusion text contradicts gold S |

Original guidelines: [after R3](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_03/guidelines_after.txt), [after R4](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/guidelines_after.txt).

Distinctions that must be kept:

1. **The FALDH exclusion example was added at R3; the norrin exclusion example was added at R4.** Both spans were already missed before those texts were added, so the new examples cannot be named as the first cause of the misses.
2. R4 edited Rule 1, Rule 5, and several examples at once, so the observed PAH recovery cannot be attributed uniquely to narrowing the "do not apply" scope.
3. The R4 diff contains no new clause aimed at Tay-Sachs disease, TSD, or cutaneous vasculitis. Those label changes happened during re-annotation after the whole guideline was rewritten, and the current records cannot name the sentence that caused them.
4. "Gold contradicts the exclusion examples" is the fact directly provable here. Whether the underlying cause is an internal logic conflict in the guideline, an example that lost its context, or a misjudged principle condition needs separate analysis. This report does not merge these causes into a settled conclusion.

## 7. All errors still open after Round 4

9 discrepancies in total:

| Document | Gold entity | Gold | R4 prediction | State relative to after R3 |
| --- | --- | --- | --- | --- |
| 1671881 | PAH deficiencies | S | D | pre-existing type error |
| 6859721 | Chronic neisserial infection | S | D | pre-existing type error |
| 6859721 | cutaneous vasculitis | S | D | new regression |
| 10484772 | abnormal retinal vascular development | D | O | pre-existing miss |
| 10484772 | deficiency of norrin | D | O | pre-existing miss |
| 10577908 | deficient activity of fatty aldehyde dehydrogenase | S | O | pre-existing miss |
| 1303173 | deficiency in G6PD | S | O | pre-existing miss |
| 10484772 | unilateral retinal telangiectasis [30,63) | S | retinal telangiectasis, S [41,63) | pre-existing span error |
| 10484772 | intraretinal and subretinal lipid accumulation | C | O | pre-existing miss |

"deficiency of hepatic phenylalanine hydroxylase" and "PAH deficiencies" are different gold entities in the same document. The recovery of the former does not mean the type error of the latter is also fixed.

## 8. P0 status and inputs for P1

P0 is complete: annotations before and after R4 were audited, the history of the related cases was traced, all fixes and the new regression were listed, and the confusion matrices plus overall and per-category metrics were assembled.

The next ablation can start from a clear baseline, the **after-R4 guideline and the fixed documents**, keeping the exact edited text, and observe separately:

- Targets: whether FALDH and deficiency in G6PD recover; whether PAH deficiency stays correct.
- Related open cases: norrin, abnormal retinal vascular development.
- Regression controls: cutaneous vasculitis, plus the currently correct spasticity, Tay-Sachs disease, and TSD.
- All documents: TP gains and losses, FP/FN, and the error matrix, not only the target cases or the final F1.

Whether to edit explicit negative examples should be recorded separately from the scope ablation. This section only provides the input basis for P1; it does not run the ablation or promise its effect.

## Verification record

The saved results were rebuilt with the current [loop scoring and clustering implementation](../../src/llm_guideline_moderation/iterative.py). Offline analysis scripts and intermediate data are kept in todo-temp/p0/. This report already contains the key counts and all changes.

Input snapshot SHA-256:

- Round 3: 70fd43ec8e11a135dac97ce377a5bbbb0704b19c7ff1020ec5a5dae0ab3a7f67
- Round 4: e6be9f17042a10725f0b5629ab6206d49672bbf2f905fe78f39db6ebf8c4e17f

The development gold used for this audit was not modified. Model/rule causality, stability across independent replicates, and validation performance are all outside the verified scope of this offline P0.
