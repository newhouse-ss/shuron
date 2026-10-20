# Correct six numbers and shrink plan v2

Without S1, plan v2 still holds, but it needs six number fixes, a different yardstick and a much smaller core.

**Numbers.** Almost every number in plan v2 traces exactly to its artifact, and the English and Chinese versions agree line by line. Six need fixing:
- the detectable loop differences ignore the plan's own Holm correction (0.024 becomes 0.040, and a 4-against-4 loop comparison can never pass that threshold);
- the "+0.073 if subtype were fixed" ceiling covers all 57 subtype errors, while fixing only the SpecificDisease/DiseaseClass errors is worth 0.043;
- the "3 to 16 cancer patterns" count has no saved query, and pass-to-pass noise is just as large;
- "PubMedBERT 0.9090" is actually BINDER;
- S4 needs 260 calls, not 230;
- the round 4 values are dev F1, not valid100.

**Yardstick.** Without a trained model, the yardstick becomes a sourced reference frame:
- the base paper's moderated GPT-5 scores 0.76 strict F1 on the same 100 documents; every saved GPT-5.4 run already beats it, so it is a floor, not a target;
- published single-type scores, such as prompted GPT-4 (0.6389) and NEEDLE (0.9228), give orientation only;
- human agreement of 87.5% can be quoted only with its ambiguity, because its source does not say what it measures.

**Remaining steps**, judged with saved data:
- S3 becomes an offline delete-only scan (0 calls). Deleting the FALDH lines restored FALDH in 3 of 3 passes when the round 4 principle was present, and in 0 of 5 without it. Its direct valid100 effect is 0.
- The S4 pilot is the one sharp gate (60 calls).
- S6 runs with the authors' consent.
- S2a and S2b run only as needed.
- S5 is cut. By the user's decision, S7 is dropped and the review-effort curve is paused.
- Voting is a free result on saved runs.

The revised core is an estimated 366 calls, ¥20,271 to ¥32,342, against plan v2's ¥61,367 to ¥97,909. The thesis can claim a like-for-like placement against the base paper's setting, a diagnosis of the loop, and a correctness fix with no regression. It cannot claim that refinement beats the original guideline or the base paper's method, that 10 documents are "worth N annotated documents", or that it reaches human level.

**Terms used below.**
- **Strict F1**: the valid100 score with exact span and exact subtype (four subtypes), the base paper's metric.
- **Single-type F1**: ignores the subtype (exact span only). Published fine-tuned models are scored this way.
- **Dev F1**: the loop's own set scoring on development documents. It is never compared numerically with valid100 scores.
- **Valid100**: the 100-document official development split. It has already been used to choose guidelines, so its results are selection results.
- **Intervals**: 95% intervals from a **paired document bootstrap**, which resamples the 100 documents 10,000 times and recomputes both scores each time.
- **Holm correction**: a rule that tightens the significance threshold when several comparisons are tested together.

Every yen figure is an estimate from per-call token assumptions, not a measured bill.

## Six plan v2 numbers need fixing; the rest trace exactly

The audit checked every key number in plan v2 against the file it cites. More than twenty match exactly, including:
- the headline scores (0.8023 top-4, 0.8050 dev30, 0.7792 original);
- top-4 minus original, +0.0231 [−0.0192, +0.0683];
- the 8-run vote;
- the per-step costs and the SD of 0.0123.

The English and Chinese files are line-aligned (357 lines each) and differ in no number ([plan_v2_audit.md §1, §5](../research_notes/Plan%20v2%20review%20without%20finetuning/plan_v2_audit.md)). Each fix below has to go into both versions.

| # | Plan v2 says (where) | Saved data or sources say | Fix |
| --- | --- | --- | --- |
| 1 | Smallest detectable loop difference 0.024 (4 loops) and 0.028 (3 loops) (§6.3) | That is a normal approximation at an unadjusted 5% level. Exact t test: 0.029 (4 vs 4). At Holm's first step (0.0125, needed because v2 makes four comparisons): 0.040 (4 vs 4) and 0.046 (3 vs 4). With 4 loops per arm, the smallest p a permutation test can give is 2/70 (about 0.029), so it can never pass 0.0125 | Take loop comparisons out of the Holm family and report them per loop, or state that they cannot reach significance |
| 2 | Subtype "+0.073 if fixed" (§2, S4) | This covers all 57 subtype mismatches. SpecificDisease/DiseaseClass (S/D) errors alone: +0.043 if all 34 were fixed; +0.024 for the 19 that the original guideline already types correctly | State the scope of each ceiling |
| 3 | Cancer patterns rose from 3 to 16 (§2, S4) | No query was saved. The counts reproduce only if "stage III cancers" and "sporadic renal cell carcinomas" count (bare words only: 2 and 15). The same R4 guideline gives 7 and 16 in two passes | Save the query. Drop "refinement created it", since pass-to-pass noise is just as large |
| 4 | "PubMedBERT 0.9090 (Chen et al. 2025)" (§1.2) | Chen et al. attribute 0.9090 to BINDER, a PubMedBERT-based bi-encoder. Plain fine-tuned PubMedBERT was reported at 0.8782 | Relabel |
| 5 | S4: 230 calls, ¥12,739 to ¥20,324 (§5, §8) | The design (two variants × 30 pilot calls, plus 200) needs 260 calls, ¥14,400 to ¥22,975. Typing calls on the test split are not budgeted | Fix the count. Budget test typing if S4 is adopted |
| 6 | Round 4 "0.9091, 0.8811" in the §2 table | These are dev F1 values (loop set scoring), placed without a label among valid100 strict values | Label them as dev F1 |

**Sources for the table.** Rows 1 to 3, 5 and 6: [audit_helper_output.txt §2, §3, §6](../research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt), [step_value_checks_output.txt §S2a/S5, §S4](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt) and [error_breakdown_output.txt](../../meeting-20261020/error_breakdown_output.txt). Row 4: [Chen et al. 2025](https://arxiv.org/pdf/2305.16326) cite BINDER for 0.9090, and [NEEDLE, Table 5](https://arxiv.org/pdf/2106.08977) quotes PubMedBERT at 87.82.

**Three smaller fixes** ([plan_v2_audit.md §1](../research_notes/Plan%20v2%20review%20without%20finetuning/plan_v2_audit.md)):
- The loop-final hashes match only as SHA-256 of the text with surrounding whitespace removed. State that convention.
- The v1 range of ¥170,000 to ¥310,000 mixes Global and Data Zone prices. On v2's Global-only basis it is ¥174,133 to ¥277,822.
- Two bootstrap scripts give slightly different intervals for top-4 minus original ([−0.0192, +0.0683] and [−0.0197, +0.0685]). Choose one.

## Without S1, the base paper's 0.76 is a floor, not a target

S1 was meant to give a supervised four-subtype score on the same split. No published equivalent exists: every supervised NCBI benchmark collapses the four subtypes into one Disease type, starting with the corpus authors' own BANNER experiments ([Doğan and Lu 2012, §2.6](https://aclanthology.org/W12-2411.pdf); [NEEDLE](https://arxiv.org/pdf/2106.08977)). The replacement is a table of reference points, each with its difference from the thesis setting stated next to it.

| Reference point | F1 | How it differs from the thesis valid100 strict score | Source |
| --- | --- | --- | --- |
| Base paper, GPT-5, original guideline (G) | 0.73 strict | Same 100 documents and same strict span-and-subtype scoring; different model | [Kim, Kim, Aizawa, ACL 2026, Table 1](https://aclanthology.org/2026.acl-long.1760.pdf) |
| Base paper, GPT-5, moderated (M) | 0.76 strict (P 0.82, R 0.71) | Same as above. The paper's own M over G gain (+0.0323) has bootstrap p 0.0762, not significant | [same, Tables 1 and 6](https://arxiv.org/html/2605.20809v1) |
| Thesis, GPT-5.4 high, 8 saved runs | 0.7716 to 0.8050 strict; 0.8351 to 0.8692 single type | (thesis) | [step_value_checks_output.txt §0](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt) |
| Other four-subtype LLM studies | GPT-4o 0.36 to 0.58 strict; GPT-4 up to 0.6436 | Evaluation set size or matching rule not stated | [Kim et al. 2025, arXiv preprint](https://arxiv.org/pdf/2510.12835v1); [Ge et al. 2025](https://arxiv.org/html/2508.06504v1) |
| Prompted LLMs, single type | GPT-4 five-shot 0.6389; GPT-5 five-shot 0.691; GPT-4o with guideline retrieval 0.810 | Test split, one type, exact string match | [Chen et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11972378/); [Hou et al. 2025](https://arxiv.org/pdf/2509.04462); [Zhao and Goto 2025](https://arxiv.org/html/2503.03261v2) |
| Supervised encoders, small training sets | PubMedBERT 0.680 at 100 sentences (test); 0.772 / 0.812 at 500 / 1,000 sentences (dev); BioBERT 0.8108 / 0.8582 at 626 / 1,171 sentences (test) | One type. Training data are random sentences, not whole documents. RDANER does not state its matching rule | [Gutiérrez et al. 2022](https://arxiv.org/pdf/2203.08410v2); [Gutiérrez et al. 2023](https://arxiv.org/pdf/2306.17649); [RDANER](https://arxiv.org/pdf/2101.00388) |
| Supervised, full training split | BANNER 0.819 (dev) / 0.818 (test); BioBERT 0.8971; NEEDLE 0.9228 | One type. NEEDLE also uses weak dictionary labels over PubMed text, with span-level scoring on Crichton et al. data; the paper implies the test split but never states it | [Doğan and Lu 2012](https://aclanthology.org/W12-2411.pdf); [Lee et al. 2020](https://academic.oup.com/bioinformatics/article/36/4/1234/5566506); [NEEDLE](https://arxiv.org/pdf/2106.08977) |
| Humans | 87.5% (what it measures is not stated); span and span-plus-subtype agreement both "above 80% after phase II"; 15-worker crowd 0.872 (spans only, training documents) | Agreement between annotator pairs before consensus, not a model scored against consensus gold | [Leaman et al. 2013](https://academic.oup.com/bioinformatics/article/29/22/2909/316280); [Doğan and Lu 2012](https://aclanthology.org/W12-2411.pdf); [Good et al. 2015](https://arxiv.org/pdf/1408.1928) |

**The same-split comparison is fair only when matched G against G and M against M.** Valid100 is the base paper's evaluation set: the paper used the full 100-document NCBI development split, with 791 mentions in four subtypes and strict span-and-type matching ([ACL 2026, §4.2 and Appendix](https://arxiv.org/html/2605.20809v1)). The local copy has the same 100 documents and 791 mentions, and none of them overlaps the training split ([audit_helper_output.txt §1](../research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)).
- **G against G.** The thesis's **0.7792 is the original-guideline score**, so it belongs next to the base paper's 0.73. The gap, about +0.05 (the base value is rounded), comes with the change of model and run conditions, not with any refinement. It is larger than the base paper's own G-to-M step (+0.03) and larger than any refinement gain the thesis has established.
- **M against M.** The base paper's **0.76 is the moderated score**, so its thesis counterpart is R4 (0.7878 and 0.7789 in two passes).

GPT-5.4 high already clears 0.76 with every saved guideline. So 0.76 works as a reproduction check and a floor, and a thesis result above it does not show that the method is better.

**Single-type numbers place the thesis between prompted LLMs and full supervision.** The thesis's single-type F1 of 0.8351 to 0.8692 sits:
- above the prompted LLMs in the table (top 0.810);
- above BANNER trained on all 593 documents (0.819 on the same development split);
- below full supervision (0.8971 to 0.9228).

One exception: a preprint reports 0.883 for GPT-4 with 16 retrieved examples, but does not state its matching rule or retrieval pool ([Monajatipoor et al. 2024](https://arxiv.org/html/2404.07376v1)).

The thesis's 10 gold documents equal about 85 to 95 sentences. (This is derived from the published counts: 5,424 sentences in 593 training abstracts, and 6,651 sentences in 793 abstracts.) Published encoders reach a similar single-type level with about 1,000 to 1,200 training sentences, roughly one fifth of the training split. That comparison is an inference with four caveats ([literature_reference_points.md Q1](../research_notes/Plan%20v2%20review%20without%20finetuning/literature_reference_points.md)):
- the published curves sample sentences, not whole documents;
- most score the test split;
- the thesis model also reads the expert guideline;
- one source does not state its matching rule.

**Human agreement needs its ambiguity stated.** The 87.5% figure does not say whether it counts spans only or spans plus subtype. It also compares annotator pairs before consensus, which is a different target from model against consensus gold. Quote it as a band with that caveat, never as a target line.

**S1 has to come out of plan v2 in about twenty places.** It appears in the goal, Q1, §1.1, §1.2, RQ1, the timeline, S6, §6.2, the budget, both success rows, three risk rows, meeting question 2 and the change log. Each has a replacement that needs no training ([plan_v2_audit.md §2](../research_notes/Plan%20v2%20review%20without%20finetuning/plan_v2_audit.md)). Two rewrites matter most:
- **RQ1** becomes: "How far is 10-document LLM annotation from the base paper's moderated GPT-5 (strict) and from published fine-tuned scores (single type), how does the gap split by error kind, and how does it change with development-set size?" The last part needs no new runs. The existing P4 curve gives valid100 strict 0.7878 (dev10), 0.7745 (dev20) and 0.8050 (dev30), one trajectory each ([P4 report](../../p4/20261007_p4_devsize_report.md)). This is also what the base paper's future-work line asks for: "examine the learning curve by incrementally increasing the volume of development data" ([ACL 2026, §6.2](https://aclanthology.org/2026.acl-long.1760.pdf)). The paper means more moderation documents, not supervised training size.
- **Meeting question 2** becomes: "Is our strict F1 against your 0.76 on the same 100 documents, plus single-type F1 against published fine-tuned scores, an acceptable yardstick without training a model?"

## Saved data show which remaining steps can move a number

Each remaining step was tested offline against saved predictions with two questions: what is the largest F1 change it could cause, and could the planned comparison detect a change that size? The list below orders the steps by value per yen. Calls and yen use plan v2's per-call constants (¥55.39 to ¥88.37 per call; [plan_v2_cost.py](../../direction-scan/plan_v2_cost.py)). The tier totals were recomputed for this report.

| # | Step | Calls | JPY (estimate) | When / condition | What saved data say |
| --- | --- | --- | --- | --- | --- |
| 1 | Reference-frame table (replaces S1) | 0 | 0 | Week 1 | No supervised four-subtype score exists to measure against |
| 2 | S3, delete-only: one offline scan of the final guideline against dev gold; contradicting examples are deleted | 0 | 0 | Week 1 | Top-4 final: 2 contradicting examples. Their strings occur in 0 of 100 valid100 texts, so the direct valid100 change is 0 |
| 2a | Optional dev check of the deletion: 3 passes on each of the 2 flagged documents | 6 | 332 to 530 | Week 1 | R4 with the FALDH lines deleted: 3 of 3 fixed, no other change |
| 3 | S4 pilot: typing pass, variants A and B, on a saved dev30 pass | 60 | 3,323 to 5,302 | Day 1 | 34 S/D confusions; ceiling +0.043. Saved dev30 repeats show 14 to 16 confusions, and 0 of 20 repeat pairs halve by chance, so the gate is sharp |
| 4 | Vote over saved runs | 0 | 0 | Any time | 8 runs +0.0366 [+0.0059, +0.0699] over the original (exploratory) |
| 5 | S6 test split: frozen guideline ×2, original ×1, scored strict and single type | 300 | 16,616 to 26,510 | Week 5, with the authors' consent | The only untouched estimate. One 100-document pass carries a 95% interval of about ±0.04 |
| | **Core total** | **366** | **20,271 to 32,342** | | Plan v2 core: 1,108 calls, 61,367 to 97,909. Without S6: 66 calls, 3,655 to 5,832 |
| 6 | S2b, top-4 half: second top-4 pass | 100 | 5,539 to 8,837 | Only if Gate B passes (S4 validation pairs with it) | Same-guideline noise is already measured: R4 twice, 0.0089 apart |
| 7 | S4 validation on two top-4 passes | 200 | 11,077 to 17,673 | Only if Gate B passes | A gate-sized effect (17 fixes, no breaks) projects to +0.0217 |
| 8 | S4 typing calls on the test split | 200 | 11,077 to 17,673 | Only if S4 enters the frozen pipeline | Missing from plan v2's budget |
| 9 | S2a: score the four unscored loop finals | 400 | 22,154 to 35,346 | Only if a loop-spread estimate is wanted | Projected top-4 minus top-1 is +0.008 to +0.021, against a detectable difference of 0.024 to 0.040 |
| | **All, if every condition fires** | **1,266** | **70,118 to 111,871** | | Plan v2 all: 2,124 calls, 117,639 to 187,689 |
| | Dropped: S1; S3 rewrite and validation passes (208 calls, 11,520 to 18,380); S5 run (786 calls, 43,533 to 69,456); second pass of the original guideline (100 calls, 5,539 to 8,837); S7 (never priced); review-effort curve as a planned step | | | | |

**Evidence for the table:** [step_value_checks_output.txt §S4, §S3, §S2a/S5, §S6, §V](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt); [offline_direction_checks_output.txt §A, §H](../../direction-scan/offline_direction_checks_output.txt); [plan_v2_cost_output.txt](../../direction-scan/plan_v2_cost_output.txt); [LOG.md, 10/14 and 10/17 rows](../../../LOG.md).

### Delete-only S3

**How it works.** After the loop produces its final guideline, the P3 scanner checks it once against the dev gold of the discrepancy examples. Any example that says "not annotated" (or gives another label) for a string that dev gold annotates is simply wrong, so it is deleted. There is no rewrite call, no second LLM pass and no validation pass.

**What the scan finds on top-4.** It flags 2 examples in the top-4 final:
- line 228, "abnormal retinal vascular development" (gold DiseaseClass, document 10484772);
- line 252, "deficient activity of fatty aldehyde dehydrogenase" (gold SpecificDisease, document 10577908).

Both entities were missed before the loop and still missed after it ([a3_gold_conflicts.json](../../p3/a3_gold_conflicts.json)).

**Deletion works when the round 4 principle is present, and is not enough on its own.** On the FALDH document:
- **R4 guideline with the three FALDH passages deleted** (lines 54 to 58, 167, 263): FALDH was labeled exactly right in 3 of 3 passes (R4 unchanged: 0 of 3). The whole document scored 14 TP, 0 FP, 0 FN in every pass (R4 unchanged: 13/0/1), with no other change.
- **R3 guideline with its two FALDH passages deleted** (lines 41 to 45, 241): FALDH was fixed in 0 of 5 passes (same-batch R3 control: 0 of 3), and the document scored 13/0/1 every time.

The 3-of-3 against 0-of-5 difference gives a one-sided Fisher p of 1/56, about 0.018. That number is only auxiliary, because the two arms ran on different days ([R4 isolation report](../../r4-isolation/20261014_r4_isolation_report.md); [R3 deletion report](../../r4-isolation/20261017_r3_minus_faldh_report.md)).

**What it changes on valid100.** The flagged strings occur in 0 of 100 valid100 texts, and so do "FALDH", "retinal vascular" and "norrin". The direct valid100 strict F1 change is therefore 0 (0.8023 stays 0.8023) ([step_value_checks_output.txt §S3](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt)). The claim is guideline correctness with no regression, not an F1 gain.

**Why delete-only is better than plan v2's rewrite.** Deletion calls no model, so it cannot quietly change other lines, which was a risk of the rewrite version. It also never shows gold to a writing step, which settles the user's inline objection on v1 arm 3. It uses dev gold only, which the project rules allow.

**Cost.** The scan costs 0 calls. The optional dev check is 6 calls, ¥332 to ¥530 by the plan's per-call estimate. For reference, the 10/14 three-pass check on the FALDH document logged 14,502 input and 105,580 output tokens, about ¥256 at the same prices (computed from the logged tokens).

**Two caveats.**
- **Delete only the sentence or bullet that names the contradicted string, and keep the general rule text around it.** In R4, line 167 embeds the string inside a general exclusion ("isolated molecular-function or laboratory-abnormality phrases such as …"), and line 263 attaches a general reason to it. The tested deletion removed those lines whole, so the narrower "delete the example, keep the rule" version has not been run. In top-4, both flagged items are single bullets under worked examples, so deletion there is clean. For example, line 227 ("retinal telangiectasis" = Specific Disease) stays.
- **Applying the scan only at the end leaves intermediate rounds carrying the wrong rule.** The FALDH exclusion already sat in the R3 guideline (two passages) and was still in R4 (three passages), so later rounds were written with it in place.

The scanner also checks only quoted examples. A rule that contradicts gold without quoting a string is outside its reach.

### The other steps

**S4 targets the largest error, but variant A alone is unlikely to pay.** As a proxy for variant A, the original run's S/D subtype can be copied onto top-4's matching spans. That fixes 19 entities but breaks 15, for +0.0051 [−0.0213, +0.0328]. Seven of the 34 confusions are typed wrong by all eight saved guidelines, so the realistic ceiling sits near +0.024, not +0.043. Most of the plausible gain therefore rests on variant B, which adds contrastive criteria ([step_value_checks_output.txt §S4](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt)). Three fixes keep S4 within the project rules:
- **B's example criterion comes from validation errors.** Plan v2's example (site-specific cancers against bare "cancer") was found in valid100 errors. Dev10 and dev30 gold contain no "hereditary/sporadic … cancer" SpecificDisease mentions at all, so either drop that criterion or state its origin.
- **On top-4 passes, the typing pass must keep top-4's own subtype definitions**, so that only one thing changes.
- **Gate B ("confusions fall by at least half") means about 8 or fewer**, since the saved dev30 passes have 14 to 16 ([audit_helper_output.txt §7](../research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)).

**S2a cannot decide its own question.** For top-4 to beat top-1 at the plan's threshold, the three unscored top-4 finals would need a mean valid100 score of 0.8075 or more (if top-1 run 3 lands at the 8-run mean). No saved run has exceeded 0.8050, so the honest pre-stated outcome is "not established". What S2a does buy is the first estimate of how much loops of one method spread ([step_value_checks_output.txt §S2a/S5](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt)).

**S5's problem is real on dev but invisible on valid100 at this budget.**
- **On dev.** In dev F1 (loop set scoring), 14 of the 18 rounds kept across 13 dev10 loops gained less than the 0.0416 noise band. When the same guideline is annotated twice on dev10, the second pass scores higher in 9 of 20 pairs.
- **On valid100.** In valid100 strict F1, 3 loops against 4 can detect only 0.026 to 0.046. That is about as large as the whole spread of the eight saved runs (0.7716 to 0.8050), while the entire R4 loop gained only +0.0086 [−0.0254, +0.0420] over the original.

Cutting the run saves ¥43,533 to ¥69,456, and the 14-of-18 count already makes S5's argument at no cost ([step_value_checks_output.txt §S5](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt)).

**Voting is a free result, with a clear limit.** The mean strict F1 over all subsets of saved runs rises from 0.7855 (one run) to 0.8060 (three) and 0.8112 (four), then flattens at 0.8158 (all eight).
- The gain comes from different guidelines. Two passes of one guideline add at most +0.0117, not established.
- No vote beats top-4 alone: the 7-distinct-guideline vote is +0.0122 [−0.0167, +0.0415] over top-4.
- The run set was not fixed in advance, so the result is exploratory ([step_value_checks_output.txt §V](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt)).

**The review-effort curve is computed and paused.** The user has paused review, so S7 is dropped and the review-effort curve is not a planned step. The curve was already computed offline at no cost. Gold stood in for the expert, and predicted entities were checked least-agreed first. With the 7 other saved runs as the agreement signal, strict F1 reaches 0.875 after checking 16.5% of top-4's entities; random order needs 45.7%. With a same-guideline second pass as the signal (measured on R4), it needs 38.1%, against 49.9% at random ([step_value_checks_output.txt §R](../research_notes/Plan%20v2%20review%20without%20finetuning/step_value_checks_output.txt)). If the curve returns later, plan v2's "0.887 at 20% checked" should be replaced by the same-guideline value, 0.851.

## The thesis can claim placement and diagnosis, not supervised equivalence

| Claim | Verdict | Evidence |
| --- | --- | --- |
| GPT-5.4 with any saved guideline beats the base paper's moderated GPT-5 on the same 100 documents | Can claim, as a model-level observation | 0.7716 to 0.8050 against 0.76; G against G about +0.05 |
| Single-type score lies between prompted LLMs and full supervision | Can claim as orientation, with split and unit caveats | 0.8351 to 0.8692, against prompted 0.6389 to 0.810 and supervised 0.8971 to 0.9228 |
| Delete-only S3 removes a wrong rule without regression | Can claim on the tested document, as correctness rather than F1 | R4 deletion 3 of 3 and 14/0/0; valid100 footprint 0 |
| Voting over different guidelines beats the original guideline | Can claim, labeled exploratory | +0.0366 [+0.0059, +0.0699]; not over top-4 |
| A refined guideline beats the original | Not established | top-4 +0.0231 [−0.0192, +0.0683]; dev30 +0.0258 [−0.0006, +0.0546] |
| Top-4 beats top-1 as a method | Very likely "not established" even after S2a | Needs unscored finals above every saved run |
| "10 documents of refinement are worth N annotated documents" | Cannot claim | No document-level supervised curve exists. String-memory baselines (dictionary 0.4504, precedent 0.8028 to 0.8189) measure something else |
| The refinement method beats the base paper's | Cannot claim | The model change confounds every comparison with 0.73 and 0.76 |
| LLM annotation reaches human agreement | Cannot claim | 87.5% does not state its level. Best strict 0.8050 is below it. Single type 0.8351 to 0.8692 is near the crowd's 0.872, but the crowd was scored on training documents |

**Sources:** [offline_direction_checks_output.txt §B, §F, §H](../../direction-scan/offline_direction_checks_output.txt); [P4 report](../../p4/20261007_p4_devsize_report.md); [plan_v2_audit.md §2, §3](../research_notes/Plan%20v2%20review%20without%20finetuning/plan_v2_audit.md); [literature_reference_points.md Q3](../research_notes/Plan%20v2%20review%20without%20finetuning/literature_reference_points.md).

## Conclusion

**The fine-tuned yardstick was never really available.** Dropping S1 costs the thesis one claim, supervised equivalence ("worth N documents"), and that claim had no published support in four subtypes anyway. Patching it with dictionary or precedent baselines would mislead. What remains is honest:
- **G against G and M against M with the base paper.** This shows that the model, not the refinement, explains the gap above 0.76.
- **Single-type placement against published scores.** This places the thesis between prompted LLMs and full supervision.

**Half the old core budget was buying comparisons that could not see an effect.** The revised core of about ¥20,000 to ¥32,000 spends money only where saved data say an outcome is detectable or needed. Delete-only S3 turns a 208-call step into an offline scan, at the price of one untested variant (narrow deletion that keeps the general rule text). The S4 pilot remains the sharpest test in the plan: it costs a few thousand yen, it targets the largest error kind, and noise alone did not halve the confusions in any of 20 saved repeat pairs.

**The meeting should settle three things:**
- the one-time use of the test split;
- whether the authors accept the reference-frame yardstick in place of S1;
- whether input-side gold, which the 10/09 seminar endorsed and plan v2 dropped without flagging, stays out of scope.

## 核查记录

**Inputs read for this report (2026-10-19)**
- The three notes in `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/`: `plan_v2_audit.md`, `step_value_and_review_curve.md`, `literature_reference_points.md`.
- Their outputs: `audit_helper_output.txt` and `step_value_checks_output.txt`.
- `docs/RP/20261020_research_plan_v2.md`.
- `todo-temp/direction-scan/plan_v2_cost_output.txt` and `plan_v2_cost.py`.
- For the delete-only S3 revision: `LOG.md` (10/14 and 10/17 rows), `todo-temp/r4-isolation/20261014_r4_isolation_report.md` (§7 table), `todo-temp/r4-isolation/20261017_r3_minus_faldh_report.md`, and `todo-temp/p3/a3_gold_conflicts.json`.
- Lines 54 to 58, 167 and 263 of the R4 final guideline, and lines 224 to 254 of the top-4 final guideline.

**Commands recorded in the notes (offline, no API calls, no credential files read)**

```
python -I "todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/audit_helper.py"
python -I step_value_checks.py        # run from the notes folder; about 10 seconds
sha256sum todo-temp/direction-scan/offline_direction_checks_output.txt todo-temp/direction-scan/plan_v2_cost_output.txt todo-temp/meeting-20261020/error_breakdown_output.txt
sha256sum of outputs/ncbi_disease/20260902_*/final/final_guidelines.txt and data/guidelines/ncbi_disease_guidelines.txt; SHA-256 of whitespace-stripped text via python -I
pdftotext -layout on a local copy of the base paper, streamed to stdout and searched (no file saved)
grep for CJK characters in docs/RP/20261020_research_plan_to_draft.md; grep "inheritance pattern alone" over outputs/ncbi_disease/*/final/final_guidelines.txt; grep "NEEDLE|92.28" over *.md, *.txt, *.py
```

**Commands run for this report (offline, no API calls)**

```
sha256sum <the artifacts in the table below>      # rechecks every hash the notes give; all match
grep FALDH LOG.md; grep "167|263|14/0/0" todo-temp/r4-isolation/20261014_r4_isolation_report.md
sed -n '54,58p;167p;263p' outputs/ncbi_disease/20260802_gpt54-high_moderation/final/final_guidelines.txt
sed -n '224,254p' outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/final/final_guidelines.txt
python -I -c "<print contradictions and document IDs from todo-temp/p3/a3_gold_conflicts.json>"
python -I -   # cost arithmetic: calls x (4,834 x $2.50 + output x $15.00) / 1e6 x 158.086954 JPY/USD,
              # output 22,551 (mean) or 36,459 (max) tokens, the constants in plan_v2_cost.py;
              # gives 6 / 66 / 366 / 500 / 766 / 1,266 calls; logged 10/14 tokens
              # (14,502 in, 105,580 out) at the same prices give about JPY 256
```

**Artifacts (SHA-256, first 12 characters)**

| File | SHA-256 |
| --- | --- |
| `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/audit_helper.py` | a89273a57240 |
| `.../audit_helper_output.txt` | 218644059fb1 |
| `.../step_value_checks.py` | 6ede298c8ec8 |
| `.../step_value_checks_output.txt` | 776f502e4921 |
| `.../step_value_checks.json` | 7865d667db75 |
| `todo-temp/direction-scan/offline_direction_checks_output.txt` | 4680e457c66e |
| `todo-temp/direction-scan/plan_v2_cost_output.txt` | a102ea385e65 |
| `todo-temp/direction-scan/plan_v2_cost.py` | 993fdd007426 (hashed for this report) |
| `todo-temp/meeting-20261020/error_breakdown_output.txt` | 41ca602af29f |
| `todo-temp/p3/scan_gold_conflicts.py` | 4af1a4eee479 (hashed for this report) |
| `todo-temp/p3/a3_gold_conflicts.json` | 53b6578b3730 (hashed for this report) |
| `todo-temp/r4-isolation/20261014_r4_isolation_report.md` | 85a5ff8084ec (hashed for this report) |
| `todo-temp/r4-isolation/20261017_r3_minus_faldh_report.md` | db2437ecf7a9 (hashed for this report) |
| `outputs/ncbi_disease/20260802_gpt54-high_moderation/final/final_guidelines.txt` (R4) | raw file 873c40fb43c1; whitespace-stripped 10e93c9dab24 (notes) |
| `outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/final/final_guidelines.txt` (top-4) | raw file d1e9f9a9bdcf; whitespace-stripped 24d7089c8e7e (notes) |
| `docs/RP/20261020_research_plan_v2.md` | 2abb43dcd110 (hashed for this report) |
| `docs/RP/20261020_research_plan_v2_zh.md` | fe977a24b778 (hashed for this report) |

**Checks inside the note scripts**
- All 8 runs reproduce their saved strict TP, FP and FN in `reproduction/results/<label>/metrics.json` (assertions).
- The review curve reproduces `offline_direction_checks_output.txt` section C at 10%, 20% and 30%, within 0.0001.
- The four unscored final hashes match plan v2.
- Validation gold was used only for scoring and diagnosis.

**Published sources.** Downloaded PDFs, with SHA-256 (first 16 characters) from the literature note; these are scratchpad copies, not in the repository:

| Source | SHA-256 |
| --- | --- |
| Base paper, ACL 2026 PDF | 0f0b205eea63f7bf |
| NEEDLE | 3a730b8efdd0057a |
| Gutiérrez et al. 2022 | 43644dcc04e27f3d |
| Gutiérrez et al. 2023 | 3beef9a8a4be526c |
| RDANER | 628759ac2e22963f |
| Chen et al. 2025 | 0c63c0d83a0bfbf6 |
| Hou et al. 2025 | f637600c2129fead |
| Kim et al. 2025 | 54d085ff82836206 |
| Doğan and Lu 2012 | b632de5542e29729 |
| Good et al. 2015 | ef9a79dc20569210 |

Ge et al., Zhao and Goto, Monajatipoor et al., Lee et al. (BioBERT) and Leaman et al. (DNorm) were read as HTML pages, with no hash. The arXiv HTML pages went through a fetch summarizer, so their table cells carry a small transcription risk.

**Not verified or not done**
- BINDER's 0.909 was not read in its primary paper; it is cited through Chen et al.
- NEEDLE does not state the test split in so many words.
- What DNorm's 87.5% measures is unknown.
- Figure-only values (Doğan and Lu 2012 Figure 3, Hou et al. Figure 1) were not read.
- The narrow delete-only variant (keep the general rule text, delete only the named example) has not been run.
- No API calls were made, and no repository file was modified apart from writing this report.
