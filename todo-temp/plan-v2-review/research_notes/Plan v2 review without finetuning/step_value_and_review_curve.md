# Plan v2 without S1: how much each remaining step can gain, whether the planned comparison can see it, what it costs, and how much review LLM annotation needs

Scope and conventions. All numbers come from saved artifacts or from `step_value_checks.py` (this folder), which ran offline on saved predictions, gold and loop records with no API call. "Strict F1" is the valid100 PubAnnotation score with exact span and exact subtype (four subtypes). "Single type" ignores the subtype (exact span only), which is how BioBERT and NEEDLE are scored. "Dev F1" is the loop's own set scoring on dev10 and is never compared numerically with valid100 scores. valid100 is the 100-document development split and has already been used for selection; the published BioBERT (0.8971) and NEEDLE (0.9228) numbers are single-type scores on the official test split, so any comparison with them is indicative only. Anything labeled "projection" is a what-if computed from saved data, not a measured result of the step.

## S4 (separate subtype decision): how much of the SpecificDisease/DiseaseClass loss could variant A recover?

### Takeaway
The original-guideline run already gives the gold subtype for 19 of top-4's 34 same-span S/D confusions, so fixing exactly those would add +0.024 strict F1 (about a third of the +0.073 all-label ceiling). But if variant A simply typed like the original guideline, it would also break 15 spans top-4 currently gets right, netting only +0.005 (not established). The dev30 pilot is cheap and its pass-to-pass noise is low, so the gate itself is informative: pilot first.

### Cited Findings
- Top-4 has 34 same-span S/D confusions on valid100 (19 SpecificDisease predicted as DiseaseClass, 15 the other way) ([offline_direction_checks_output.txt §H](../../../../todo-temp/direction-scan/offline_direction_checks_output.txt)).
- On the same exact span, the original-guideline run gives the gold subtype in 19 of the 34, the same wrong subtype in 10, and has no prediction with that exact span in 5 ([step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- Strict F1 of top-4 is 0.8023. Fixing only those 19 gives 0.8265 (+0.0242); fixing all 34 S/D confusions gives 0.8457 (+0.0434) ([step_value_checks_output.txt §S4](step_value_checks_output.txt)). Fixing all 57 label mismatches of every kind gives 0.8750 (+0.0727), the "+0.073" in plan v2 ([error_breakdown_output.txt, top-4 block](../../../../todo-temp/meeting-20261020/error_breakdown_output.txt)).
- If those 19 fixes came with no breaks, the paired document bootstrap would give +0.0242, 95% interval [+0.0083, +0.0453], P(gain) 1.00; a subtype-only change on fixed spans is detectable at this size ([step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- Projection of "variant A types like the original run": copying the original run's S/D type onto every top-4 S/D prediction with the same span changes 37 entities, 19 fixes and 15 breaks, strict F1 0.8074 (+0.0051), 95% interval [−0.0213, +0.0328], P(gain) 0.62 ([step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- How many of the 7 other saved runs give the gold subtype on the same span, per confusion: none for 7 confusions, 1 run for 4, 2 for 6, 3 for 6, 4 for 8, 5 for 2, 6 for 1. The 7 that no run gets right include "Adrenal insufficiency", "fibrosis", "enzyme deficiency", "chromosomal fragmentation during meiosis", "DTDST chondrodysplasias", "fibre degeneration" and "Deficiency of terminal complement components" ([step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- Exploratory (run set not fixed in advance): replacing top-4's S/D type by the majority S/D type of all 8 runs on the same span changes 6 entities (4 fixes, 1 break), strict F1 0.8061, interval [−0.0013, +0.0096] ([step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- Gate B asks that S/D confusions fall by at least half on the dev30 pilot. In the 5 saved dev30 repeats of the original guideline, same-span S/D confusions are 16, 15, 14, 15, 16 (202 gold S plus D mentions); in 0 of the 20 ordered repeat pairs does the second repeat have half or fewer of the first ([step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- A gate-sized effect on valid100 (17 of the 34 fixed, no breaks) would give strict F1 0.8240 (+0.0217) (projection, [step_value_checks_output.txt §S4](step_value_checks_output.txt)).
- S/D confusion counts depend strongly on the guideline: 14 (dev30 guideline) to 58 (no-verified-example guideline); the same R4 guideline gives 33 and 41 in two passes ([20261019_direction_research_report.md §3.2](../../../../todo-temp/direction-scan/20261019_direction_research_report.md)).
- The no-verified-example run has the worst strict F1 of the 8 (0.7716) but the best single-type F1 (0.8692, against 0.8546 for top-4) ([step_value_checks_output.txt §0](step_value_checks_output.txt)).
- Cost: 230 calls, ¥12,739 to ¥20,324 (estimate; 30 pilot calls plus 200 for two valid100 passes) ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)). At ¥5,539 to ¥8,837 per 100 calls, the 30-call pilot alone is about ¥1,662 to ¥2,651 (computed from the same file).

### Inferences
- The original guideline's subtype choices are not a free win: they fix 19 and break 15 on top-4's spans. Variant A can only beat that if separating the decision from the rest of the guideline helps by itself; the proxy cannot test that. Variant B (contrastive criteria from development errors) carries most of the plausible upside.
- Seven confusions are typed wrong by every one of the 8 guidelines, so wording changes of the kind seen so far are unlikely to reach the full +0.043; a realistic ceiling for S4 is nearer the +0.024 of the 19 cases at least one guideline gets right, minus whatever breaks occur.
- Because spans stay fixed and pass noise on dev30 S/D counts is small (14 to 16), the dev30 pilot is a sharp, cheap test. If the pilot halves the count, the validation comparison is likely to be detectable too (a fix-only change of 17 to 19 entities has an interval excluding 0).
- The noTP result (best spans, worst subtypes) suggests a typing pass has more leverage on guidelines that find spans well; this is a lead, not a measured effect.

### Gaps
- The run-to-run randomness of a separate typing call is unknown; the dev30 repeat spread reflects full-annotation passes, not typing calls.
- Whether variant A behaves like the original-guideline run is an assumption; no typing pass has been run.
- Breaks on Modifier and CompositeMention (the other half of Gate B) were not projected, because a typing pass that only switches S and D cannot be simulated from saved runs for those types.

## S3 (gold-consistency check): how much validation text do the contradicting rules touch, and what F1 change is possible?

### Takeaway
None. The two gold-contradicting rules in the top-4 final name strings that occur in 0 of the 100 validation texts, so the largest direct F1 change is 0. Any F1 change S3's two validation passes show will be pass noise (two passes of one guideline differ by 0.009; one top-4 pass carries a 95% interval of about ±0.04). S3's value is guideline quality assurance on dev, which costs under ¥1,000; the ¥11,000 to ¥18,000 is almost all validation passes that cannot show an effect.

### Cited Findings
- The P3 scanner found exactly 2 exclusion examples in the top-4 final guideline that contradict dev10 gold: "abnormal retinal vascular development" (line 228, gold DiseaseClass) and "deficient activity of fatty aldehyde dehydrogenase" (line 252, gold SpecificDisease); a third overlap, line 12 "autosomal recessive disorder", was judged a consistent label rule ([a3_gold_conflicts.json](../../../../todo-temp/p3/a3_gold_conflicts.json); [P3 report](../../../../todo-temp/p3/20261007_p3_topk4_report_en.md)).
- In valid100, both flagged strings occur in 0 texts, 0 gold entities and 0 top-4 predictions; so do "fatty aldehyde dehydrogenase", "FALDH", "retinal vascular", "deficiency of norrin" (the dev30 guideline's contradiction) and "norrin" ([step_value_checks_output.txt §S3](step_value_checks_output.txt); norrin contradiction in the dev30 guideline from [P4 report §4](../../../../todo-temp/p4/20261007_p4_devsize_report.md)).
- The top-4 final has 8 quoted strings in exclusion lines; 3 occur in valid100 text: "Neisseria" (2 texts, 0 gold entities with that exact text), "autosomal recessive disorder" (2 texts, 2 gold entities, both predicted exactly by top-4), "phenotype." (2 texts, 0 gold) ([step_value_checks_output.txt §S3](step_value_checks_output.txt)).
- Largest direct strict F1 change on valid100 from the two flagged rules: 0.8023 to at most 0.8023 ([step_value_checks_output.txt §S3](step_value_checks_output.txt)).
- Plan v2 already expects "a small F1 change, because the contradicting strings do not occur in validation" ([plan v2 §5, S3](../../../../docs/RP/20261020_research_plan_v2.md)).
- Pass noise: the R4 guideline annotated twice scored 0.7878 and 0.7789 (difference +0.0089, interval [−0.0191, +0.0389]) ([offline_direction_checks_output.txt §A, §H](../../../../todo-temp/direction-scan/offline_direction_checks_output.txt)). One top-4 pass: 0.8023, 95% interval [0.7643, 0.8376] ([step_value_checks_output.txt §S6](step_value_checks_output.txt)).
- On dev, the mechanism is already tested: deleting the three FALDH lines of the R4 guideline restores FALDH 3 of 3 with no other regression; deleting the two FALDH lines of R3 does not (0 of 5) ([LOG.md, 10/14 and 10/17 rows](../../../../LOG.md)).
- Cost: 208 calls, ¥11,520 to ¥18,380 (5 rewrites, 3 dev checks, 200 validation calls) ([plan_v2_cost.py](../../../../todo-temp/direction-scan/plan_v2_cost.py); [plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)). The 8 non-validation calls cost about ¥443 to ¥707 (computed from the ¥5,539 to ¥8,837 per 100 calls in the same file).

### Inferences
- S3 cannot move valid100 F1 through the strings it targets. Its validation passes test only "no regression", and a regression smaller than about 0.03 cannot be distinguished from pass noise; the entity-level fix/break count the plan proposes is the more informative check.
- A cheaper S3 is a dev-only pilot: rewrite, rescan, dev check (about 8 calls). Validation passes are worth buying only if the rewrite changes lines beyond the flagged ones, or if a top-4 pass from S2b can be reused as the pair.

### Gaps
- Indirect effects of the rewrite (the model might change other lines while narrowing a rule) cannot be measured offline.
- The scanner covers quoted examples only; conditional rule text that contradicts gold (the R4 FALDH case is conditional) is outside its reach, so "0 contradictions left" would be a statement about examples only.

## S2a (four unscored loop finals): what difference between top-4 and top-1 could four loops each detect, and is a difference that large plausible?

### Takeaway
With the 8-run SD of 0.0123, four loops per arm detect (80% power, two-sided 5%) a difference of 0.024 by the plan's normal approximation, 0.029 by an exact t test, and 0.040 after Holm correction. The plausible difference from existing data is about +0.008 (unscored finals score like the average run) to +0.021 (all unscored top-4 finals score as well as the best top-4 loop). S2a will very likely end "not established"; its real value is measuring how much loops of one method spread, which decides whether any loop-level comparison is worth running.

### Cited Findings
- The 8 saved valid100 strict F1 values (original 0.7792, R4 0.7878, R4 rerun 0.7789, top-4 0.8023, dev20 0.7745, dev30 0.8050, noTP 0.7716, abstraction 0.7844) have mean 0.7855 and sample SD 0.0123; one same-guideline pair gives an SD estimate of 0.0063 ([step_value_checks_output.txt §0, §S2a/S5](step_value_checks_output.txt)).
- Smallest difference detectable 80% of the time (loop means, two-sided):

  | SD | Loops per arm | alpha 0.05, normal | alpha 0.05, exact t | alpha 0.0125 (Holm first step), exact t |
  | --- | --- | --- | --- | --- |
  | 0.0123 | 4 vs 4 | 0.0244 | 0.0293 | 0.0396 |
  | 0.0123 | 3 vs 4 | 0.0263 | 0.0330 | 0.0461 |
  | 0.0123 | 3 vs 3 | 0.0281 | 0.0378 | 0.0556 |
  | 0.0063 | 4 vs 4 | 0.0125 | 0.0150 | 0.0203 |
  | 0.0063 | 3 vs 4 | 0.0135 | 0.0169 | 0.0236 |

  ([step_value_checks_output.txt §S2a/S5](step_value_checks_output.txt)). Plan v2's "about 0.024; with 3 loops, about 0.028" matches the normal column only ([plan v2 §6.3](../../../../docs/RP/20261020_research_plan_v2.md)).
- Top-1 loops: R4 (two-pass mean 0.7833); runs 1 and 2 ended at the original guideline (final hash e6232d944d68, identical to the original), so their valid score is the original's 0.7792; run 3 is unscored (a1311085152b). These 3 known loop values have SD 0.0024 ([step_value_checks_output.txt §0, §S2a/S5](step_value_checks_output.txt)).
- Top-4 loops: only the 09/01 loop is scored (0.8023); runs 1 to 3 are unscored (5f5300a5811b, 5a2ddf57a5c7, cc7bb3416f86) ([step_value_checks_output.txt §0](step_value_checks_output.txt)). The scored top-4 loop is the one with the highest dev final of the four (dev F1, loop set scoring: 0.9155 against 0.8252, 0.8552, 0.8841) ([LOG.md](../../../../LOG.md)).
- Projections of the four-loop mean difference (top-4 minus top-1):

  | Scenario for the unscored finals | Top-4 mean | Top-1 mean | Difference |
  | --- | --- | --- | --- |
  | All at the 8-run mean (0.7855) | 0.7897 | 0.7818 | +0.0079 |
  | Top-4 ones at 0.8023, top-1 run 3 at 0.7855 | 0.8023 | 0.7818 | +0.0205 |
  | Top-4 ones at the 8-run maximum (0.8050), top-1 run 3 at the minimum (0.7716) | 0.8043 | 0.7783 | +0.0260 |
  | Reverse extreme | 0.7793 | 0.7867 | −0.0074 |

  ([step_value_checks_output.txt §S2a/S5](step_value_checks_output.txt)).
- For a difference of 0.0244 (normal) or 0.0292 (t), the three unscored top-4 finals would need a mean valid F1 of 0.8075 or 0.8139 if top-1 run 3 scores the 8-run mean, and 0.8029 or 0.8093 even if run 3 scores the 8-run minimum; no saved run exceeds 0.8050 ([step_value_checks_output.txt §S2a/S5](step_value_checks_output.txt)).
- Cost: 400 calls, ¥22,154 to ¥35,346 ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)).

### Inferences
- Under the SD of 0.0123, S2a can establish top-4 over top-1 only if the three unscored top-4 finals all score above every guideline seen so far. That is implausible, so the honest pre-stated outcome is "not established".
- The between-loop SD within one method is the unknown that matters. If it is near the same-guideline pass SD (0.0063), four loops per arm could detect about 0.015 to 0.020, and the optimistic +0.021 would be within reach. S2a measures exactly this, and it also adds four scored guidelines for the vote and for agreement signals. That is the reason to keep it, reframed as a spread estimate rather than a decisive test.
- Two top-1 loops ended at the original guideline, so the top-1 arm is partly a point mass at 0.7792; a t test on such an arm is a rough tool, and per-loop reporting (as the plan says) matters more than the p-value.

### Gaps
- No loop-level SD within a method exists yet; 0.0123 mixes methods and 0.0063 comes from one pair.
- A paired document bootstrap pooled over loops would ignore loop-to-loop variance and overstate certainty; the plan does not yet say which test S2a's primary comparison uses.

## S5 (reproducibility-gated acceptance): what upside is measurable, and are 3 loops enough to detect a validation gain?

### Takeaway
On dev, the problem S5 targets is common: 14 of 18 kept rounds across 13 dev10 loops gained less than the noise band (0.042), and a candidate identical in quality to the current guideline would pass "F1 rises" in 9 of 20 repeat pairs. On validation, no measurable upside exists: no undone-round guideline has a valid100 score, the whole noise-kept R4 loop is +0.009 over the original (not established), and 3 versus 4 loops detect only 0.026 to 0.046, as large as the entire spread of the 7 guidelines (0.033). Three loops are not enough; cut the validation arm.

### Cited Findings
- Round 4 of the R4 loop raised dev F1 (loop set scoring) from 0.8873 to 0.9091 and was kept; with the rerun values for Tay-Sachs disease and TSD it scores 0.8811 and would have been undone ([20261015_r4_nontarget_report.md](../../../../todo-temp/r4-nontarget/20261015_r4_nontarget_report.md)).
- One dev10 annotation has SD 0.01502 ([LOG.md, size-noise row](../../../../LOG.md)); the difference between two annotations then has SD 0.0212, and 1.96 times that is 0.0416 ([step_value_checks_output.txt §S5](step_value_checks_output.txt)).
- Across 13 completed dev10 loops (R4 loop, top-1 runs 1 to 3, top-4 09/01 and runs 1 to 3, noTP runs 2, 4, 5, abstraction runs 1 and 2), 18 rounds were kept and 11 rejected; 14 of the 18 kept rounds had a dev gain below 0.0416, including all four rounds of the R4 loop (+0.0397, +0.0223, +0.0281, +0.0218) ([step_value_checks_output.txt §S5](step_value_checks_output.txt)).
- In the 5 saved dev10 repeats of the original guideline (0.8028, 0.8085, 0.8252, 0.7832, 0.8028), the second of an ordered pair is strictly higher in 9 of 20 pairs ([step_value_checks_output.txt §S5](step_value_checks_output.txt); values from [offline_direction_checks_output.txt](../../../../todo-temp/direction-scan/offline_direction_checks_output.txt)).
- The initial dev F1 of the original guideline across the 13 loops has SD 0.0243, or 0.0148 without the lowest value 0.7391 (noTP run 4); some initial annotations may be cached, which is not checked ([step_value_checks_output.txt §S5](step_value_checks_output.txt)).
- Valid100: R4 minus original +0.0086, 95% interval [−0.0254, +0.0420] ([P4 report §3](../../../../todo-temp/p4/20261007_p4_devsize_report.md)). No saved valid100 run uses an R3 guideline ([step_value_checks.py RUNS](step_value_checks.py); [LOG.md](../../../../LOG.md)).
- Detectable differences for 3 S5 loops against 4 base loops: 0.0263 (normal), 0.0330 (exact t), 0.0461 (exact t at the Holm first-step alpha 0.0125) with SD 0.0123 ([step_value_checks_output.txt §S2a/S5](step_value_checks_output.txt)). The 8 single runs span 0.7716 to 0.8050 ([step_value_checks_output.txt §0](step_value_checks_output.txt)).
- Cost: 786 calls, ¥43,533 to ¥69,456 ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)).

### Inferences
- S5's dev-side question (do the two acceptance rules disagree, and how often?) has a large measured target: most kept rounds are inside noise. Its validation-side question cannot be answered at this budget, because any plausible gain is a fraction of the total refinement gain (+0.004 to +0.026 single-run), and the detectable difference is larger than that.
- The plan's own fallback ("report it as designed and argue from the round-4 evidence") is the better use of money. The 14-of-18 count is free supporting evidence.

### Gaps
- The entity-level reproducibility of fixes and regressions in past rounds cannot be replayed offline; the gate's actual keep/undo decisions are unknown without new calls.
- Whether the noise-kept rounds hurt validation is unmeasured; it would need valid100 scores of the guidelines before and after such rounds.

## Voting: how does F1 change with the number of runs voted, and which runs share a guideline?

### Takeaway
Voting gains rise quickly up to about 4 runs and then flatten: the mean over all subsets goes from 0.7855 (one run) to 0.8060 (3 runs), 0.8112 (4), 0.8139 (6) and 0.8158 (all 8). Of the votes tested with the bootstrap, the 8-run and the 7-distinct-guideline votes beat the original with intervals excluding 0, and none beats top-4. Two passes of the same guideline gain almost nothing (union +0.003 and +0.012 over the two passes, not established; intersection is worse). The 8 runs contain 7 distinct guidelines; R4 and its rerun share one.

### Cited Findings
- Guideline identity (SHA-256 of the guideline text, first 12 characters): original e6232d944d68; R4 10e93c9dab24; R4 rerun 10e93c9dab24 (same guideline by LOG naming; LOG marks input consistency with the first batch as unverified, and the 10/16 replay check confirms byte-identical R4 guideline text for the dev reruns, not for this valid batch); top-4 24d7089c8e7e; dev20 1dc6f006a1c8; dev30 520311412321; noTP 38f5289e4717; abstraction f4b25d391675 ([step_value_checks_output.txt §0](step_value_checks_output.txt); [LOG.md](../../../../LOG.md); [20261016_replay_identity_report.md](../../../../todo-temp/r4-nontarget/20261016_replay_identity_report.md)). The mapping from each valid prediction folder to its loop final is by folder name and LOG row; the prediction files do not record the guideline.
- Vote over all subsets of the 8 runs, keeping an entity proposed by at least half of the runs voted (mean [min, max] over subsets):

  | Runs voted | Subsets | Keep if at least | Strict F1 |
  | --- | --- | --- | --- |
  | 1 | 8 | 1 | 0.7855 [0.7716, 0.8050] |
  | 2 | 28 | 1 (union) | 0.7920 [0.7764, 0.8087] |
  | 3 | 56 | 2 | 0.8060 [0.7927, 0.8222] |
  | 4 | 70 | 2 | 0.8112 [0.7992, 0.8195] |
  | 5 | 56 | 3 | 0.8105 [0.8016, 0.8232] |
  | 6 | 28 | 3 | 0.8139 [0.8067, 0.8197] |
  | 7 | 8 | 4 | 0.8124 [0.8026, 0.8200] |
  | 8 | 1 | 4 | 0.8158 |

  For even counts, a strict majority does worse: 2 runs (both) 0.7779, 4 runs (3) 0.8004, 6 runs (4) 0.8068, 8 runs (5) 0.8088. Choosing the best threshold after the fact adds at most 0.004 to the means ([step_value_checks_output.txt §V](step_value_checks_output.txt)).
- Same guideline, two passes (R4 and its rerun): union 0.7906 (TP 638, FP 185, FN 153), intersection 0.7753 (TP 564, FP 100, FN 227), against single passes 0.7878 and 0.7789. Union minus R4 +0.0028 [−0.0114, +0.0173]; union minus rerun +0.0117 [−0.0047, +0.0302]; intersection minus R4 −0.0125 [−0.0315, +0.0043] ([step_value_checks_output.txt §V](step_value_checks_output.txt)).
- Vote of the 7 distinct guidelines (at least 4): 0.8145; minus top-4 +0.0122 [−0.0167, +0.0415]; minus original +0.0353 [+0.0053, +0.0677], P(gain) 0.989 ([step_value_checks_output.txt §V](step_value_checks_output.txt)). Vote of all 8 (at least 4): 0.8158; minus original +0.0366 [+0.0059, +0.0699] ([offline_direction_checks_output.txt §B, §H](../../../../todo-temp/direction-scan/offline_direction_checks_output.txt)).
- The run set was not fixed in advance, so the vote is exploratory ([20261019_direction_research_report.md §3.3](../../../../todo-temp/direction-scan/20261019_direction_research_report.md)).
- One 100-document pass costs ¥5,539 to ¥8,837 (estimate) ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)).

### Inferences
- The vote's gain comes from guideline diversity, not from repeating one guideline: two passes of one guideline barely move F1, while 3 or 4 different guidelines already give most of the 8-run gain.
- A deployable vote would need at least 3 passes per document (about ¥16,600 to ¥26,500 per 100 documents, projection from the per-pass cost) and several guidelines. The four S2a finals would make a pre-specified vote possible without new loops; that is a side benefit of S2a.
- No vote beats top-4 alone with an interval excluding 0, so voting is a robustness gain over the original, not a proven gain over the best guideline.

### Gaps
- Whether the valid batches called R4 and R4 rerun used byte-identical guideline text is not verified by any saved record.
- A vote over pre-specified guidelines (chosen before seeing validation) has not been run.

## Review-effort curve: how much agreement-ordered review reaches 0.875, 0.8971 and 0.9228?

### Takeaway
With the 7 other saved runs as the agreement signal, checking 16.5% of top-4's predicted entities reaches strict F1 0.875, 23.6% reaches 0.8971 and 36.9% reaches 0.9228; in random order the same targets need 45.7%, 59.6% and 76.2%. Single-type targets need 6.6%, 15.6% and 32.0%. With only a second pass of the same guideline (the S2b situation, measured on R4), strict targets need 38.1%, 55.3% and 74.4%, still better than random but much weaker. All targets are below the ceiling (0.9606 and 0.9565), so none needs missed-entity search, but the test-split targets compared with valid100 are indicative only.

### Cited Findings
- Method: predicted entities are ordered least-agreed first (agreement = number of other runs with the identical typed entity, random tie-break, mean over 20 seeds); gold acts as the expert and fixes or deletes each checked entity; the share reported is the first entity count at which the mean F1 reaches the target, measured entity by entity (no interpolation). The code reproduces the saved curve at 10%, 20% and 30% (0.8431, 0.8868, 0.9109 against 0.8432, 0.8868, 0.9109; the 0.0001 difference comes from rounding per seed) ([step_value_checks_output.txt §R](step_value_checks_output.txt); [offline_direction_checks_output.txt §C](../../../../todo-temp/direction-scan/offline_direction_checks_output.txt)).
- Agreement signal sources: for top-4 the 7 other runs are original, R4, R4 rerun, dev20, dev30, noTP and abstraction (6 other guidelines plus one same-guideline repeat of R4); for the S2b proxy, R4 uses only its own rerun ([step_value_checks_output.txt §0, §R](step_value_checks_output.txt)).
- Strict four subtypes, base top-4 (777 predicted, 148 wrong, start 0.8023, ceiling 0.9606, 60 gold entities with no overlapping prediction):

  | Target | Agreement order (seed range) | Random order | Wrong-first bound | At the agreement share: random / bound |
  | --- | --- | --- | --- | --- |
  | 0.875 (human agreement) | 128 (16.5%; 118 to 132) | 355 (45.7%) | 69 (8.9%) | 0.8277 / 0.9350 |
  | 0.8971 (BioBERT) | 183 (23.6%; 169 to 187) | 463 (59.6%) | 91 (11.7%) | 0.8395 / 0.9606 |
  | 0.9228 (NEEDLE) | 287 (36.9%; 274 to 290) | 592 (76.2%) | 116 (14.9%) | 0.8620 / 0.9606 |

  ([step_value_checks_output.txt §R](step_value_checks_output.txt)).
- Single type, base top-4, same agreement ordering (107 wrong, start 0.8546, ceiling 0.9606): 0.875 at 51 entities (6.6%; random 19.7%; bound 2.8%); 0.8971 at 121 (15.6%; random 39.1%; bound 5.8%); 0.9228 at 249 (32.0%; random 64.2%; bound 9.3%) ([step_value_checks_output.txt §R](step_value_checks_output.txt)).
- Strict, base R4 with its own second pass (745 predicted, 140 wrong, start 0.7878, ceiling 0.9565): 0.875 at 284 (38.1%; seeds 243 to 342; random 49.9%; bound 9.9%); 0.8971 at 412 (55.3%; random 63.8%; bound 12.2%); 0.9228 at 554 (74.4%; random 80.5%; bound 15.3%). With roles swapped (rerun as base): 43.9%, 60.2%, 80.3% (random 56.5%, 70.4%, 84.6%) ([step_value_checks_output.txt §R](step_value_checks_output.txt)).
- Single type, base R4 with its own second pass (93 wrong, start 0.8490): 0.875 at 74 (9.9%; random 23.1%); 0.8971 at 256 (34.4%; random 42.3%); 0.9228 at 465 (62.4%; random 67.8%) ([step_value_checks_output.txt §R](step_value_checks_output.txt)).
- Strict F1 at fixed shares, base top-4 with 7 runs (agreement / random / bound): 5% 0.8217 / 0.8095 / 0.8424; 10% 0.8431 / 0.8182 / 0.8854; 20% 0.8868 / 0.8343 / 0.9606; 30% 0.9109 / 0.8500 / 0.9606; 50% 0.9321 / 0.8822 / 0.9606. R4 with its rerun: 10% 0.8343 / 0.8055; 20% 0.8507 / 0.8243; 30% 0.8634 / 0.8418; 50% 0.8910 / 0.8750 ([step_value_checks_output.txt §R](step_value_checks_output.txt)).
- Top-4 with only one other run of a different guideline: 0.875 needs 15.6% (dev30) to 35.1% (R4 rerun) of entities; 0.8971 needs 31.0% to 52.1%; 0.9228 needs 57.1% to 72.6%; F1 at 20% ranges 0.8561 to 0.8870 ([step_value_checks_output.txt §R](step_value_checks_output.txt)).
- The base paper's moderated GPT-5 score, 0.76 (four subtypes, strict, valid100), is exceeded with no review by all 8 saved runs (lowest 0.7716) ([20261019_direction_research_report.md §2](../../../../todo-temp/direction-scan/20261019_direction_research_report.md); [step_value_checks_output.txt §0](step_value_checks_output.txt)).
- Reference points: BioBERT 0.8971 and human agreement about 0.875 (Leaman et al. 2013, as cited in the base paper) are recorded in [20261019_direction_research_report.md §2](../../../../todo-temp/direction-scan/20261019_direction_research_report.md); NEEDLE 0.9228 is taken from the assignment brief and was not checked here. All three are test-split or corpus-level figures, not valid100 results.

### Inferences
- The agreement signal is worth most when it comes from different guidelines. A same-guideline second pass saves about 88 checked entities out of 745 to reach 0.875 strict (284 instead of 372), while the 7-run signal saves 227 out of 777 (128 instead of 355).
- The "wrong-first" bound shows that a perfect router would need only 9% to 15% of entities for every target; the distance from that bound is the room an LLM reviewer (S7) or a better signal could take.
- For the S6 and S2b design, a second top-4 pass alone will give a curve like the R4 one (roughly 38% to reach 0.875 strict). Adding passes of a few other guidelines, which S2a produces anyway, would move it toward the 16.5% curve.

### Gaps
- Gold is a perfect and free expert; the curve counts checks, not hours, and real reviewers make errors.
- No second top-4 pass exists, so the same-guideline curve is measured on R4, not on the guideline the plan will freeze.
- The single-type curve reuses the typed agreement ordering (as asked); a span-only ordering might do better and was not computed.

## S2b, S6 and S7: what the saved data say about the remaining steps

### Takeaway
S2b's measured payoff is the review curve: a same-guideline second pass routes checks clearly better than random (+0.026 strict F1 at 20% checked on R4), and the top-4 half of S2b is the part the thesis needs. S6 adds no F1; it buys the only untouched estimate, with a 95% interval of about ±0.04 on one 100-document pass. S7's headroom is real but bounded: 31 wrong entities that every run agrees on are worth +0.034 if found.

### Cited Findings
- S2b proxy: on R4 with its rerun, agreement order gives 0.8507 at 20% checked against 0.8243 at random (+0.0264), and 0.8634 against 0.8418 at 30% ([step_value_checks_output.txt §R](step_value_checks_output.txt)). Entities that differ between the two passes are wrong 49% of the time (40 of 81), against 15% for agreed entities (100 of 664) ([offline_direction_checks_output.txt §C](../../../../todo-temp/direction-scan/offline_direction_checks_output.txt); [20261019_direction_research_report.md §3.3](../../../../todo-temp/direction-scan/20261019_direction_research_report.md)).
- S2b cost: 200 calls, ¥11,077 to ¥17,673 (estimate); each half (one guideline) is 100 calls, ¥5,539 to ¥8,837 ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)).
- S6 precision: one 100-document pass has a document-bootstrap 95% interval of [0.7643, 0.8376] for top-4, [0.7329, 0.8226] for the original and [0.7495, 0.8250] for R4 ([step_value_checks_output.txt §S6](step_value_checks_output.txt)). S6 cost: 300 calls, ¥16,616 to ¥26,510 (estimate) ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)). It needs agreement from the base-paper authors to use the test split ([plan v2 §5, S6](../../../../docs/RP/20261020_research_plan_v2.md)).
- S7 headroom: 31 of top-4's wrong entities appear in all 7 other runs (23 fixable, 8 to delete); correcting only these gives strict F1 0.8359 (+0.0336). At 20% checked, agreement order reaches 0.8868 against the wrong-first bound of 0.9606 ([step_value_checks_output.txt §R](step_value_checks_output.txt)). S7 is not priced ([plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt)).

### Inferences
- The second pass of the original guideline in S2b serves only the noise estimate; the second top-4 pass serves noise, the review curve and the S3/S4 pairing. If S2b must shrink, keep the top-4 pass.
- S6's interval of about ±0.04 means the test-split result will place the method, not rank close variants; the test review curve inherits the same uncertainty.
- S7 must beat agreement routing at equal check counts; the 31 consistent errors are where it could, because agreement routing reaches them last.

### Gaps
- No test-split data exist locally, so S6's actual noise and the test mention count are unchecked.
- S7's cost and its own error rate (wrong changes to correct entities) are unknown until a model is chosen and a dev pilot runs.

## Cost, value per yen and recommendation, one row per step

### Takeaway
The two free analyses (review-effort curve and voting) carry the largest measured effects. Among paid steps, the S4 pilot is the best value (about ¥1,700 to ¥2,700 for a sharp gate on the largest error), S2b's top-4 pass and S6 are needed for the thesis claims, S2a is worth keeping only as a spread estimate, S3 should be shrunk to a dev-only check, and S5's validation arm should be cut because it cannot detect any plausible gain.

### Cited Findings
- Per-step summary (calls and yen from [plan_v2_cost_output.txt](../../../../todo-temp/direction-scan/plan_v2_cost_output.txt), estimates; upside and noise from [step_value_checks_output.txt](step_value_checks_output.txt) unless noted):

  | Step | Measured or projected upside on valid100 (strict) | Noise floor | Can the planned comparison see it? | Calls, JPY | Recommendation |
  | --- | --- | --- | --- | --- | --- |
  | S2a four unscored finals | Projection +0.008 to +0.021 (top-4 minus top-1 loop means) | 8-run SD 0.0123; same-guideline pair SD 0.0063 | No at SD 0.0123 (needs 0.024 normal, 0.029 t, 0.040 with Holm); possibly at SD 0.0063 | 400, ¥22,154 to ¥35,346 | Keep, reframed as a measurement of loop spread; pre-state "not established" as the likely result |
  | S2b second passes | Review routing: +0.026 at 20% checked over random (R4 proxy); union vote +0.003 / +0.012 (not established) | Pass difference 0.0089 | Likely for routing (disagreed entities are wrong 49% of the time against 15% for agreed ones; no formal test run); no for vote | 200, ¥11,077 to ¥17,673 | Keep; the top-4 pass (100 calls, ¥5,539 to ¥8,837) is the essential half |
  | S3 gold-consistency check | Direct footprint 0 (flagged strings in 0 of 100 texts) | One pass about ±0.04 (95% interval) | No F1 effect to see; only regressions above about 0.03 | 208, ¥11,520 to ¥18,380 | Pilot first: rewrite, rescan, dev check (about 8 calls, ¥443 to ¥707); validation passes only if the rewrite changes more than the flagged lines |
  | S4 typing pass | Ceiling +0.043 (34 S/D confusions); +0.024 for the 19 the original types right; variant A proxy +0.005 [−0.021, +0.033]; gate-sized +0.022 | dev30 S/D counts 14 to 16 per repeat, 0 of 20 pairs halve by chance | Yes, if fixes dominate breaks (19 fixes alone: [+0.008, +0.045]) | 230, ¥12,739 to ¥20,324 (pilot 30 calls, about ¥1,662 to ¥2,651) | Pilot first; expect most of the upside from variant B |
  | S5 gated acceptance | Dev: 14 of 18 kept rounds inside noise. Valid: unmeasured; whole R4 loop +0.0086 [−0.025, +0.042] | Loop SD 0.0123 | No (3 vs 4 loops: 0.026 normal, 0.033 t, 0.046 with Holm; all 7 guidelines span 0.033) | 786, ¥43,533 to ¥69,456 | Cut the run; report the design and the 14-of-18 round evidence |
  | S6 test split | No F1 gain; one untouched estimate | ±0.04 per pass (valid bootstrap) | Places the method; cannot rank close variants | 300, ¥16,616 to ¥26,510 | Keep, if the authors agree |
  | S7 LLM reviewer | Headroom +0.034 (31 consistent errors); bound 0.9606 against 0.8868 at 20% | Unknown | Unknown until a dev pilot | Not priced | Pilot first on dev, after S2b |
  | Review-effort curve | 0.875 / 0.8971 / 0.9228 strict at 16.5% / 23.6% / 36.9% checked (7-run signal); 38.1% / 55.3% / 74.4% (same-guideline pass) | Tie-break seed ranges in §R | Large margin over random order, which needs 45.7% / 59.6% / 76.2% (no formal test run) | 0 extra calls | Keep (core of RQ3) |
  | Voting over runs | 8 runs +0.0366 [+0.0059, +0.0699] over original; plateau from about 4 runs | Subset spread at 4 runs 0.7992 to 0.8195 | Yes against the original; no against top-4 | 0 extra calls on saved runs; ¥5,539 to ¥8,837 per extra pass in use | Keep as a free analysis; a deployable vote needs 3 or more passes of different guidelines |

- Value per ¥10,000 (projection, computed from the rows above): S4 at the gate-sized effect, +0.011 to +0.017 strict F1; S4 at the variant-A proxy, +0.0025 to +0.004; S2a, S3 and S5, no detectable F1 gain at any price in the plan. In the review curve, each extra 1% of top-4 entities checked between 0% and 20% adds on average 0.0042 strict F1 under agreement order against 0.0016 at random (averages between measured points, [step_value_checks_output.txt §R](step_value_checks_output.txt)).
- If only part of the budget is approved, plan v2's order is S2a, S3, S6, S2b, S4, S5 ([plan v2 §8](../../../../docs/RP/20261020_research_plan_v2.md)).

### Inferences
- Reordering by value per yen would put the S4 pilot (about ¥2,000) and the top-4 second pass (about ¥5,500 to ¥8,800) first, then S6, then S2a; S3's dev-only check costs almost nothing; S5's run and S3's validation passes would go last or be dropped.
- Dropping S5 and S3's validation passes saves about ¥54,600 to ¥87,100 (786 + 200 calls; computed from the cost file), more than the whole cost of S2a, S2b and the S4 pilot together.
- The thesis claim that is both large and well measured is workflow quality (review effort), not method quality (refined guideline F1); the steps that feed the review curve (S2b top-4 pass, S2a passes as extra agreement sources, S6) deserve priority.

### Gaps
- All yen figures are estimates from per-call token assumptions; actual usage was never recorded for refinement or typing calls.
- S7 has no price, so its value per yen cannot be computed.

### Verification record (核查记录)
- Command (2026-10-19, offline, no API call, no credential read): `python -I step_value_checks.py`, run from `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/`. Runtime about 10 seconds.
- Script: `step_value_checks.py`, SHA-256 first 12 characters `6ede298c8ec8`. Outputs: `step_value_checks_output.txt` (`776f502e4921`), `step_value_checks.json` (`7865d667db75`).
- Checks inside the script: all 8 runs' TP, FP and FN equal their `reproduction/results/<label>/metrics.json` strict counts (assertions); the review curve reproduces `offline_direction_checks_output.txt` section C at 10%, 20% and 30% for both the 7-run and the R4 curves (assertions, tolerance 0.0001); guideline hashes for the four unscored finals match plan v2 (a1311085152b, 5f5300a5811b, 5a2ddf57a5c7, cc7bb3416f86).
- Reused code: `ents`, `prf`, `score`, `classify_preds`, the curve ordering and `boot` are copied from `todo-temp/direction-scan/offline_direction_checks.py` (not imported, because importing it reruns it and rewrites its outputs); the exclusion and quote patterns are copied from `todo-temp/p3/scan_gold_conflicts.py`. Power values use an exact two-sample t power integral written in the script (no scipy available).
- Validation gold was used only for scoring and diagnosis. No repository file outside this folder was modified; `git status` matches the session start apart from this folder.
