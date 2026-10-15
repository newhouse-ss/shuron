# P4: Development Size 10/20/30 Comparison: Does More Evidence Make Rules More General?

Date: analyzed 2026-10-07, finalized 2026-10-08
Status: complete (offline analysis; replicate trajectories designed but not executed, stopped by user decision on 2026-10-08)

Background in plain terms: the seminar asked whether giving the refinement loop more development documents (10, 20, or 30) makes the learned guideline less hard-coded and better on unseen data. Absorption rate means the share of dev gold mention strings that end up verbatim in the final guideline; a lower value means less answer-key copying. valid100 is the held-out 100-document validation set used to test generalization.

## Conclusions (TL;DR)

1. **Erratum (important)**: the `resolved_run_config.json` of the three size runs, confirmed by measuring the round-1 prompts, all show **n_examples = 5**. The "example cap 5/10/15" recorded in LOG/PROGRESS was wrong: **the confound "example count varies with size" does not exist at all**. The size effect is a pure document-count effect (LOG/PROGRESS corrected accordingly).
2. **The hard-coding end of the hypothesis is strongly supported**: absorption collapses monotonically with size, 41% to 9% to 3% (15/37, 6/68, 3/115). The wider the evidence base, the less the guideline copies gold verbatim.
3. **The generalization end is not supported by current evidence**: valid100 F1 is 0.7878 (dev10), 0.7745 (dev20, below the original guideline's 0.7792), 0.8050 (dev30), non-monotonic. Paired bootstrap shows **all between-arm 95% CIs cross 0** (dev30 minus dev10: +0.017 [-0.012, +0.047]). Only dev30 vs the original guideline is near significant (+0.026, one-sided 97.1%). valid100 lacks the power to detect effect sizes of 0.01 to 0.02.
4. **Same-kind gold control**: the dev30 guideline still wrote a flat exclusion for "deficiency of norrin" (L16/L185, gold=DiseaseClass) even though the norrin document (10484772) sits inside dev30. **More data did not remove the gold-contradicting exclusion failure mode**, consistent with the structural location in P3 section 3.4. The dev20 guideline is the cleanest (0 conflicts) yet worst on valid: a clean guideline does not equal good performance.
5. **Replicate trajectories not executed**: both replicate arms were designed and started twice (first killed when the application exited, second stopped by user decision), no data. All conclusions in this report rest on single-trajectory evidence; trajectory variance is unknown. This is the main reservation.
6. **P4 done means all five seminar todos are closed.**

## 1. Background and Hypothesis

Source: `archive/2026-10-02_seminar-conflict-casestudy/seminar_oct2.md`: "the tuning data is currently about 10 documents, 70 entities; verify whether more samples and same-kind controls reduce hard-coding". Original todo: "complete and report the 10/20/30 document experiments, add same-kind gold controls; compare hard-coding counts against test performance".

Hypothesis chain: more dev documents → more diverse error evidence → principles grounded on a wider evidence base → more general rules with less per-case hard-coding → better valid performance.

The three splits were programmatically verified as **nested** (dev10 ⊂ dev20 ⊂ dev30), so the document sets are not confounded; but the added documents change difficulty, and the three splits' initial F1 is non-monotonic (0.7972/0.7821/0.8092).

## 2. Summary Table (Existing Runs + valid100 Measurements)

| Size | dev F1 trajectory | Rounds / stop reason | Absorption | Guideline chars | valid100 F1 | valid P/R |
|---|---|---|---|---|---|---|
| Original guideline (anchor) | n/a | n/a | n/a | 7367 | 0.7792 | 0.8011/0.7585 |
| dev10 (20260802) | 0.7972→0.9091 | 4, threshold reached | 15/37 (41%) | →19940 | 0.7878 | 0.8121/0.7649 |
| dev20 (20260813) | 0.7821→0.8105 | 2, no improvement | 6/68 (9%) | →9827 | 0.7745 | 0.8145/0.7383 |
| dev30 (20260812) | 0.8092→0.8577 | 3, no improvement | 3/115 (3%) | →14211 | 0.8050 | **0.8345**/0.7775 |
| topk4-dev10 (reference) | 0.8028→0.9155 | 2, threshold reached | 12/37 (32%) | →19262 | 0.8023 | 0.8095/**0.7952** |

Additional observations:
- Dev-side gains shrink with size (+0.112/+0.028/+0.049): the larger the dev set, the more diverse the errors, and the harder the "accept only if F1 rises" rule is to satisfy. **Comparing sizes by final dev value is meaningless.**
- dev30's valid 0.8050 is the highest among all NCBI runs, and its gain is **precision-driven** (P 0.8345, the highest of all arms); topk4's gain is **recall-driven** (Modifier, see P3 section 4). The two mechanisms have different gain profiles.
- topk4 (10 documents) 0.8023 roughly equals dev30 (30 documents) 0.8050: the same valid level with one third of the data.
- Annotation noise reference (`size_noise`, fixed guideline repeated 5 times): F1 SD = 0.0150/0.0098/0.0092 for dev10/20/30.

## 3. Paired Bootstrap: Are the Valid Differences Credible?

Method: all five arms annotated the same valid100. Resample per-document TP/FP/FN from `per_document.json` 10,000 times with replacement and compare micro-F1 differences. Script `todo-temp/p4/bootstrap_valid.py`, results `todo-temp/p4/bootstrap_valid.json`.

| Comparison | Point estimate | 95% CI | P(diff>0) |
|---|---|---|---|
| dev10 − original | +0.0086 | [−0.0254, +0.0420] | 68.8% |
| dev20 − original | −0.0047 | [−0.0561, +0.0413] | 45.5% |
| dev30 − original | +0.0258 | [−0.0006, +0.0546] | **97.1%** |
| topk4 − original | +0.0231 | [−0.0197, +0.0685] | 85.6% |
| dev30 − dev10 | +0.0172 | [−0.0118, +0.0471] | 87.1% |
| dev30 − dev20 | +0.0305 | [−0.0081, +0.0772] | 92.9% |
| dev20 − dev10 | −0.0133 | [−0.0662, +0.0285] | 32.0% |
| topk4 − dev10 | +0.0145 | [−0.0209, +0.0498] | 78.5% |
| topk4 − dev30 | −0.0027 | [−0.0426, +0.0372] | 45.0% |

Reading: only dev30 vs the original guideline is near significant (97.1% one-sided). **All between-arm comparisons (including P3's topk4 vs dev10 = +0.0145) are indistinguishable from 0 at the 95% level.** This quantitatively confirms the "point estimate" reservation in the P3 report. For now we can only claim "refinement has a valid gain trend of about +0.02 to 0.03", not any ordering effect of size or k.

## 4. Same-Kind Gold Control: Conflict Audit of the Guidelines at Each Size

Script `todo-temp/p4/scan_gold_conflicts_multi.py` (a multi-run version of the P3 auditor: whitespace-insensitive label comparison, skips "(e.g., ...)" enumeration fragments), results `todo-temp/p4/gold_conflicts_multi.json`. **Every flagged line was triaged by hand.**

| Size | Scan overlaps | Human-confirmed conflicts | Notes |
|---|---|---|---|
| dev10 | 4 | **0** (at the flat exclusion example level) | All 4 are positive examples consistent with gold; the known FALDH/retinal-vascular conflicts exist as **conditional rule text** (recorded in P0 to P2), not as flat examples |
| dev20 | 0 | **0** | Shortest guideline (9,827 characters), most conservative, no example overlapping gold at all |
| dev30 | 6 | **1 (real, new)** | `deficiency of norrin` is written as an exclusion in two places (L16 conditional list + L185 flat "not annotated"), gold=DiseaseClass, and document 10484772 sits inside dev30; the other 4 flagged lines are inherited conditional rules (EBV/CMV organism rule, cancer/tumor broad-term rule), context-dependent rather than flat errors |

Conclusion: **scale did not solve the "writing exclusions that contradict gold" problem**: with a 30-document evidence base, refinement still wrote a flat exclusion for norrin. Together with P3 section 3.4 (top-4 received FALDH's gold label in round 1 and still wrote the exclusion): the failure point is not the amount of evidence, but the structural gap that the `refine_guidelines` call never sees labeled discrepancy evidence. A reverse piece of evidence: the dev20 guideline is the cleanest yet worst on valid, so "no conflicting examples" is neither necessary nor sufficient for good performance.

## 5. Replicate Trajectory Experiment: Designed, Not Executed

To fill the "one trajectory per size" gap, two replicate arms were designed (same split, same n_examples=5, same GPT-5.4 high as the original runs; only sampling noise differs):

- Arm A: dev20 replicate (`--dev-split reproduction/dev_splits/ncbi_disease_dev20.json`, run-name `..._dev20_run2`)
- Arm B: dev30 replicate (`--dev-split reproduction/dev_splits/ncbi_disease_dev30.json`, run-name `..._dev30_run2`)

Execution record: first launch on 2026-10-07 (task bash-hyqeddcy); the process died when the application exited (status.json records `OSError: [Errno 22]`, stdout pipe broken), round 1 did not finish, and the leftover directory was cleaned up. Restarted on 2026-10-08 (task bash-agp23t8q, logging to disk), then stopped by user decision with no data produced. All conclusions here rest on single trajectories. If reruns happen later, the commands above can be reused directly.

## 6. Overall Conclusions

1. **Direct answer to the seminar question**: more development data reduces hard-coding (absorption 41% → 9% → 3%, monotonic and mechanism-consistent), but less hard-coding does **not** convert into a discernible valid gain: dev20, absorbing 9%, is worst on valid; dev30, absorbing 3%, is best. Something else drives valid (gain profiles: dev30 precision-driven, topk4 recall-driven), not whether the guideline copies gold strings.
2. **Trend and limits of the size benefit**: dev30 is the only arm close to significantly beating the original guideline (+0.026, 97.1% one-sided), but arms are pairwise indistinguishable. Current evidence supports "refinement has a valid gain trend of about +0.02 to 0.03", not "bigger is better" or "top-4 beats top-1".
3. **Gold-contradicting exclusions are independent of scale**: dev30 still wrote the norrin flat exclusion. The fix points to the information structure of the refine call (P3 section 3.4: inject labeled evidence into the rewrite step, or check against gold after writing), not to more data.
4. **Limitations**: one trajectory per size (trajectory variance unknown); dev final values are not comparable across sizes (document sets are nested but difficulty differs, and the stopping rule is harsher on larger sets); valid100 lacks power for 0.01 to 0.02 effect sizes.
5. **Todo closure**: P4 done; the five 2026-10-02 seminar todos (P0 to P4) are now all closed.

## 7. Verification Record

- n_examples erratum evidence: all three runs' `inputs/resolved_run_config.json` show `"n_examples": 5`; each run's `rounds/iteration_01/snapshot.json` infer prompt was measured to contain 5 discrepancy examples and 5 TP FILE blocks, and the refine prompt 5 TP blocks (programmatically verified 2026-10-07)
- Split nesting: dev10 ⊂ dev20 ⊂ dev30 (verified programmatically on `sampled_sourceids`)
- Bootstrap: `todo-temp/p4/bootstrap_valid.py` → `bootstrap_valid.json` (10,000 resamples, seed 42)
- Gold audit: `todo-temp/p4/scan_gold_conflicts_multi.py` → `gold_conflicts_multi.json`; the dev30 L16/L185 norrin exclusions and the L83/L96 inherited conditional rules were all diagnosed by hand against the original text
- Replicates: two launch records in section 5 (bash-hyqeddcy died with the application exit; bash-agp23t8q stopped by user decision), neither produced data
- Valid scoring sources: `metrics.json` / `per_document.json` of `reproduction/results/ncbi-{g,m,s}-gpt54`, `ncbi-m-dev20`, `ncbi-m-dev30`, `ncbi-valid-topk4-gpt54`
