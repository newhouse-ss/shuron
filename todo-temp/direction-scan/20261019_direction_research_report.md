# Research directions toward the target, and a review of the 10/20 research plan

Written 2026-10-19 for the 2026-10-20 meeting (Prof. Goto, Kon Woo Kim, Prof. Kim). Scope: (1) which directions can move NCBI Disease annotation quality toward the fine-tuned reference and toward partial replacement of expert annotation, ranked by expected return per cost, using only saved data, offline analysis and published work; (2) whether `docs/RP/20261020_research_plan_to_draft.md` (plan v1) is feasible and well aimed. The revised plan is `docs/RP/20261020_research_plan_v2.md`. No API calls were made for this report.

## Conclusions

1. **No refined guideline is yet proven better than the original on validation.** Top-4 has the best single-run score (strict F1 0.8023 against 0.7792), but the paired bootstrap gives +0.0231 with a 95% interval of [−0.0192, +0.0683] (probability of a real gain 0.85). The same R4 guideline annotated twice scored 0.7878 and 0.7789, so one rerun moves F1 by 0.009, the same size as the R4 gain itself. Top-4's number also comes from the best of four top-4 loops; the other three were never scored on validation. The top-4 direction is promising, not established.
2. **The target number needs a source and a matching yardstick.** No source gives BioBERT 0.86 on NCBI Disease. Published fine-tuned scores use one Disease type on the test split: BioBERT 0.8971 (Lee et al. 2020), PubMedBERT 0.9090 (Chen et al. 2025). Scored the same way (exact span, one type), our best predictions reach 0.8546 on the validation split. I found no published supervised result with the four NCBI subtypes, so the fair target has to be measured: a fine-tuned model trained on the same 593 training documents, scored with our strict scorer. Without this, "approach SOTA" has no fixed meaning.
3. **The largest validation loss, subtype confusion, comes from the model and the guideline rather than from noisy gold.** Of 34 same-span SpecificDisease/DiseaseClass confusions under top-4, 20 involve strings whose training gold agrees with the validation gold; one agrees with the prediction, and 13 never occur in training. The count also depends strongly on the guideline: from 14 (dev30 guideline) to 58 (no-verified-example guideline). Part of it is created by refinement: two cancer patterns ("hereditary breast cancer" predicted as DiseaseClass; bare "cancer", "tumour", "lipomas" predicted as SpecificDisease) rise from 3 errors under the original guideline to 16 under top-4, concentrated in a few documents.
4. **The strongest free evidence points to aggregation and targeted human review.**
   - A majority vote over the 8 saved validation runs (keep an entity proposed by at least 4) scores 0.8158. This is the only comparison with the original guideline whose interval excludes 0: +0.0366, [+0.0059, +0.0699].
   - If an expert checks the predicted entities on which runs agree least, F1 rises to 0.887 after checking 20% of them and 0.911 after 30% (checking in random order: 0.834 and 0.850).
   - With only one extra run as the agreement signal, the same checks give 0.869 and 0.881.
   - I found no published curve of this kind for biomedical NER, so it can be a contribution.
5. **Two cheap ideas were tested offline and dropped.** Document-level label propagation does not help: copying a string's label to its other occurrences adds almost nothing (mean +0.001), and forcing one type per string in a document hurts (mean −0.039), because NCBI types the same string differently in different roles (disease versus Modifier). Lexical precedent is weak: relabeling S/D predictions by training gold gains +0.000 with a 10-document pool and only +0.017 with all 563 unused training documents.
6. **Plan v1 has a sound protocol but spends its budget in the wrong place.** Its Track 1 arms target the FALDH mechanism, whose validation footprint is close to zero by the plan's own analysis. Track 1 would also cost ¥170,000 to ¥310,000 on GPT-5.4, and with 3 loops per arm it can only detect differences of about 0.028 or more, larger than any effect seen so far. Track 2 (reviewer) has the right goal, but an LLM reviewer has to beat the free agreement-routing baseline above. The revised plan does three things before any new loop:
   - fix the yardstick;
   - score the guidelines that already exist;
   - test the mechanism fixes by retrofitting them onto existing guidelines.

   It moves subtype errors and the review-effort curve to the center.

## 1. Goal, and what "approaching SOTA" can mean

The goal stated at the midterm: close the gap between validation F1 (about 0.79) and SOTA without giving up the 10-document supervision advantage (10 documents for refinement against 593 for fine-tuning), then measure how much expert annotation the method can replace (midterm deck slide 10; OVERVIEW). At the 9/15 review, Prof. Goto said F1 around 0.8 is not enough to replace manual annotation and asked for either a much better refinement or a reframing as LLM support for manual annotation. Prof. Kasahara asked how to balance cost and performance (`archive/2026-09-15_seminar-future-plan/9_15 future plan.docx`).

Two meanings of "approach SOTA" follow, and the plan needs both:

- **Method quality.** The guideline alone, with 10 documents, moves strict F1 toward the fine-tuned model scored on the same split and metric.
- **Workflow quality.** LLM annotation plus a measured amount of human checking reaches that level. This is the partial-replacement answer the 9/15 review asked for.

## 2. Where we stand, with uncertainty

Strict F1 requires exact span and exact subtype (PubAnnotation scorer). "One type" collapses the four subtypes, which is how BioBERT and PubMedBERT are scored. The paired bootstrap resamples the 100 documents 10,000 times and recomputes both F1 scores each time. A 95% interval that contains 0 means the difference is not established.

| Guideline (GPT-5.4 high, valid100) | Strict F1 | One type | Difference from original, 95% interval, P(gain) |
| --- | --- | --- | --- |
| Original | 0.7792 | 0.8351 | |
| R4, top-1 dev10 (two passes) | 0.7878, 0.7789 | 0.8490 (first pass) | +0.0086, [−0.0254, +0.0420], 0.69 (P4 report) |
| Top-4 dev10 | 0.8023 | 0.8546 | +0.0231, [−0.0192, +0.0683], 0.85 |
| Top-1 dev30 | 0.8050 | 0.8455 | +0.0258, [−0.0006, +0.0546], 0.97 (P4 report) |
| Vote of 8 saved runs, at least 4 | 0.8158 | not computed | +0.0366, [+0.0059, +0.0699], 0.99 |

Readings:

- Same guideline, two passes: R4 minus its rerun is +0.0089, [−0.0191, +0.0389]. The passes share 664 identical entities, 62 of 100 documents get identical output, and about one entity in five differs.
- The 8 single runs have a standard deviation of 0.0123. They mix methods, so this overstates the spread of one method, but it is the only planning value available. With 3 loops per arm, two arms must differ by about 0.028 to be detected 80% of the time; with 4 loops, by about 0.024.
- Top-4's three sibling loops ended at development F1 0.8252, 0.8552 and 0.8841 and have refined final guidelines on disk (hashes 5f5300a5811b, 5a2ddf57a5c7, cc7bb3416f86) that were never scored on validation. Top-1 run 3 also has an unscored refined final (a1311085152b); top-1 runs 1 and 2 ended at the original guideline. Scoring these four guidelines (about ¥22,000 to ¥35,000, estimate) gives a loop-level comparison of top-1 and top-4, four loops each, without a new loop.

**Position against published numbers** (different splits, so only orientation):

| Source | Setting | NCBI Disease F1 | Checked |
| --- | --- | --- | --- |
| Lee et al. 2020, Bioinformatics (BioBERT v1.1) | Fine-tuned, one type, test split | 0.8971 | Publisher page, via the literature search |
| Chen et al. 2025, Nature Communications 16:3280 | Fine-tuned PubMedBERT | 0.9090 | PMC full text, read 10/19 |
| Same | GPT-4 zero / one / five-shot | 0.5827 / 0.5988 / 0.6389 | Same |
| Zhao and Goto 2025, arXiv 2503.03261, Table 4 | GPT-4o, two-step inference plus guideline retrieval; SOTA baseline | 0.810; 0.897 | PDF read 10/19 |
| Kim et al. 2026, ACL (base paper, Table 1) | GPT-5, original / refined guideline, valid100, four subtypes, strict | 0.73 / 0.76 | PDF read 10/19 |
| Base paper, appendix | Human inter-annotator agreement, "approximately 87.5% for disease mention annotation" (Leaman et al. 2013) | 0.875 | PDF read 10/19 |
| This project | GPT-5.4 high, top-4 guideline, valid100 | strict 0.8023, one type 0.8546 | Saved artifacts |

Possible origin of the 0.86: Zhao and Goto's Table 4 gives the SOTA baseline for BC5CDR-Disease as 0.866 and for NCBI Disease as 0.897. This is an inference; the user decides the number.

The base paper is now public: arXiv 2605.20809, Kim, Kim and Aizawa, "Accepted to the ACL 2026 Main Conference" (arXiv page read 10/19). It can be cited on slides. Ken's radiology draft (`../papers/multi-annotator setting.pdf`, the same text as `archive/references/sub-backbone-research1.pdf`) is still unpublished and stays off the slides.

## 3. Offline evidence gathered today

Script `offline_direction_checks.py`, output `offline_direction_checks_output.txt` and `.json`. All eight saved validation runs reproduce their `metrics.json` F1 exactly (assertions in the script). The validation set has now been used for direction selection, which is one more reason to keep the official test split for the final claim (section 6.2 of plan v2).

### 3.1 Errors left by the best guideline (from the 10/19 error breakdown)

Top-4 on valid100: 777 predicted entities, 148 of them wrong; 162 gold entities not matched exactly, 60 of which have no overlapping prediction at all. If one kind of error were replaced by gold: subtype 0.8750 (57 errors), boundary 0.8597 (45), missed 0.8429 (55), extra 0.8260 (45). Checking every predicted entity gives 0.9606. Missed entities stay missed because the checker only sees what the model proposed.

### 3.2 Subtype confusion is learnable convention, and refinement both fixes and creates it

- Training gold rarely gives one string both S and D: 36 strings among 578 that occur at least twice. Most mixed strings mix SpecificDisease and Modifier (for example "DMD", "PKU"), which is the corpus's role convention, not inconsistency.
- Top-4's 34 same-span S/D confusions, by training precedent:
  - 20: training gold agrees with the validation gold;
  - 1: training gold agrees with the prediction ("myotonia");
  - 13: the string never occurs in training.
- Same-span S/D confusions per guideline (S→D plus D→S):

  | Guideline | S/D confusions |
  | --- | --- |
  | Original | 26 |
  | R4 | 33 |
  | R4 rerun | 41 |
  | Top-4 | 34 |
  | dev20 | 42 |
  | dev30 | 14 |
  | No verified examples | 58 |
  | Abstraction | 38 |

  The same R4 guideline gives 33 and 41 in two passes, so differences of about 10 are within noise. The range across guidelines (14 to 58) is wider than that, so the guideline text drives this error more than anything else we have measured.
- Cancer patterns: under the original guideline there are 0 "hereditary/sporadic … cancer" S→D errors and 3 bare "cancer/tumour/lipoma" D→S errors. Under top-4 there are 8 and 8. The top-4 guideline contains a line written during refinement: "modifiers that still leave the phrase class-level (for example, inheritance pattern alone in 'autosomal recessive disorder') do not make it a Specific Disease" (line 12). That line fits "hereditary breast cancer" being typed as a class. Two documents hold 11 of the wrong cancer-pattern predictions, so this is a strong lead, not proof.
- Lexical precedent is weak. Relabeling top-4's S/D predictions to the other S/D type when at least 75% of training occurrences say so:

  | Precedent pool | Strict F1 |
  | --- | --- |
  | 10 documents | 0.8028 |
  | 30 documents | 0.8054 |
  | 100 documents | 0.8097 |
  | 300 documents | 0.8148 |
  | 563 documents | 0.8189 |

  Means over 5 random pools; base 0.8023. String memory explains a small part. The rest needs rules about how a phrase is built, which is guideline territory.

### 3.3 Aggregating runs, and routing human checks by agreement

- **Vote.** Keeping an entity when at least k of the 8 saved runs propose it exactly:

  | k | Strict F1 |
  | --- | --- |
  | 2 | 0.8071 |
  | 3 | 0.8147 |
  | 4 | 0.8158 |
  | 5 | 0.8088 |
  | 6 | 0.7986 |

  For comparison, the best single run is 0.8050 and the mean single run 0.7855. The vote gains mostly on precision (top-4: 148 false positives; vote at 4: 125, with similar true positives). The 8 runs use different guidelines, so this is an ensemble of guideline variants, and the run set was not fixed in advance. Treat it as a signal.
- **Review curve.** An expert (gold standing in) checks top-4's predicted entities, least-agreed first, where agreement is the number of other runs with the identical entity. Checking fixes the span and type, or deletes the entity.

  | Share checked | Agreement order | Random order | Wrong entities first (bound) |
  | --- | --- | --- | --- |
  | 10% (78) | 0.8432 | 0.8182 | 0.8854 |
  | 20% (155) | 0.8868 | 0.8343 | 0.9606 |
  | 30% (233) | 0.9109 | 0.8500 | 0.9606 |
  | 50% (388) | 0.9321 | 0.8823 | 0.9606 |

  - The agreement signal is cheap to get. Using 1, 2, 3 or 7 other runs, checking 30% gives 0.8805, 0.8977, 0.9066, 0.9104 (means over random run subsets).
  - With two passes of the same guideline (R4), checking 30% gives 0.8634. Same-guideline passes disagree less than different guidelines, so the signal is weaker but real: the entities that differ between the two passes are wrong 49% of the time (40 of 81), against 15% for agreed entities (100 of 664).
- **Consistent errors exist.** 481 of top-4's 777 entities appear in all 7 other runs; 31 of them are wrong. Agreement cannot find these; this is where a reviewer that reads the document could add value (FALDH and Tay-Sachs disease are examples from the case study).
- **Missed entities.** The other 7 runs propose 59 spans that overlap no top-4 prediction; 21 are exactly gold and 9 more overlap gold. Checking those 59 candidates recovers about a third of top-4's 60 gold entities with no overlapping prediction.
- **Limits.** Gold as the expert is perfect and costs nothing per check; real checking takes time and makes errors. The curves give the share of entities a person must look at, not the hours.

### 3.4 Dropped after testing

- **Document-level propagation.** Gold annotates 97.9% (train) and 99.5% (valid) of repeated occurrences of an annotated string, and the model already does too. Adding missing occurrences changes the 8 runs by +0.001 on average (+0.009 for dev30, near zero elsewhere) and changes nothing on the dev30 documents. Forcing one type per string in a document costs 0.039 on validation and 0.048 on dev, because the same string is SpecificDisease in one sentence and Modifier in the next.
- **Dictionary baselines.**

  | Dictionary | Strict F1 | One type |
  | --- | --- | --- |
  | Built from dev10 gold | 0.0858 | 0.1883 |
  | Built from 563 training documents | 0.4504 | 0.5929 |

  The guideline approach is far beyond lookup.
- **Abbreviations.** Only 18 of 208 top-4 discrepancies are abbreviation-like strings (11 of them misses). Boundary errors are symmetric (23 too long, 22 too short), and the extra words are scattered ("classical" 4, "idiopathic" 2, "late onset" 2). Neither is a single fixable convention.

## 4. What the literature says

The three searches covered public sources only. Rows marked "to check" come from search summaries and must be checked against the paper before they reach a slide.

| Direction | Evidence | Status |
| --- | --- | --- |
| Demonstrations chosen by similarity | Monajatipoor et al. 2024 (arXiv 2404.07376): strategic selection of in-context examples gives "~15-20% increase in F1" on biomedical few-shot NER (abstract). Their NCBI GPT-4 table numbers (62.6 random vs 79.3 retrieved) were reported by the search agent | Abstract read; table to check |
| Guidelines rather than examples | GuideNER (Huang et al., AAAI 2025), cited by the base paper: guidelines beat examples for in-context NER | Cited by the base paper |
| Disagreement among several LLMs to refine instructions | DiZiNER (arXiv 2604.15866, ACL 2026): zero-shot SOTA on 14 of 18 benchmarks, +8.0 F1 over prior zero-shot bests; pairwise model agreement correlates with F1 | Read 10/19 (PDF) |
| Gated, append-only rule patches | Ken's radiology draft: patches eligible only when supported by at least 2 documents or 2 models, appended rather than regenerating the guideline; composition peaks at about 10 of 21 patches, then falls because rules conflict | Read 10/19; unpublished, off slides |
| Self-verification / reviewer pass | Gero et al. 2023 (arXiv 2306.00024): large gains on hard clinical extraction, small on easy ones; an omission-finding step raises recall and lowers precision. GPT-NER self-verification targets false positives | Summary-level; to check |
| Repeated sampling of one model | Small NER gains reported; heterogeneous models give more diversity (SaM, ACL 2025, summary) | Summary-level |
| Human-LLM work allocation | CoAnnotating (Li et al., EMNLP 2023): uncertainty-based allocation up to 21% better than random, classification only | Abstract-level |
| LLM pre-annotation then expert correction | Goel et al. 2023 (ML4H): medication extraction, human time per document 26.67 to 11.32 minutes (58% less) at similar quality | Summary-level; to check |
| Run-to-run variance | Atil et al. 2024 (arXiv 2408.04667): accuracy varies by up to 15% between runs at temperature 0 on reasoning tasks | Summary-level |
| What the base paper asks for next | Learning curve with more development data and "more robust or noise-tolerant termination conditions" (§6.2); "consistency checks or automated detection of overly broad rules" (Limitations) | Read 10/19 |
| Supervised results with the four NCBI subtypes | None found | Gap |
| Curve of human checks needed versus F1, biomedical NER | None found | Gap |

The last two gaps match the two cheapest new experiments in the revised plan.

## 5. Directions ranked by return per cost

"Cost" uses the per-call mean and maximum of the earlier estimate (GPT-5.4 high, ¥5,539 to ¥8,837 per 100-document pass; `plan_v2_cost_output.txt`). These are estimates, not measurements.

| # | Direction | Our evidence | Literature | What it answers | Cost (estimate) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Fine-tuned yardstick on the same split and metric, plus a learning curve (10 to 593 documents) | Target number unsourced; one-type gap 0.855 vs 0.897 is cross-split | No four-subtype result; no NCBI learning curve found | What the target is; how many annotated documents the method is worth | No API cost; a GPU for training | **Do first** |
| 2 | Score the guidelines that already exist (4 unscored loop finals; second passes of original and top-4) | Top-4 gain not established (P 0.85); same-guideline rerun differs by 0.009 | Repeated runs recommended (Atil et al.) | Is top-4 a method effect; validation noise; agreement signal for 3 | ¥33,000 to ¥53,000 | **Do first** |
| 3 | Review-effort curve: repeated passes plus agreement routing (partial replacement) | 0.887 / 0.911 at 20% / 30% checked; one extra pass already gives most of it | Gap in biomedical NER; Goel, CoAnnotating as precedents | The replacement goal, with a cost axis | Free on the outputs of 2 and 6 | **Core result** |
| 4 | Subtype-focused refinement (a typing pass with contrastive S/D definitions, or scope-limited subtype rules) | Largest loss (+0.073 if fixed); 14 to 58 confusions across guidelines; refinement creates some | Definition prompting (PromptNER) helps type decisions; evidence abstract-level | Can the guideline close the biggest gap | Pilot on dev30 saved predictions, then 2 passes: ¥13,000 to ¥20,000 | **Pilot, then decide** |
| 5 | Gold-consistency check after the rewrite (merges plan v1 arms 3 and 4) | FALDH chain; top-4 final still holds 2 rules against dev gold; scanner exists | Base paper Limitations ask for it | Removes rules that contradict development gold; answers "delete rules" (9/15) | Retrofit on top-4 final: ¥12,000 to ¥18,000 | **Do, small** |
| 6 | Reproducibility-gated acceptance (keep a round only if its fixes reproduce and its regressions do not) | Round 4 kept by noise; dev10 SD 0.015 | Base paper §6.2 asks for it; Ken's gates are related | Midterm point 5 as a method | 3 loops: ¥44,000 to ¥69,000 | **If budget allows** |
| 7 | LLM reviewer (Claude) reading whole documents | 31 consistent errors that agreement cannot see | Self-verification trades recall for precision | Whether a reviewer beats free agreement routing | Model to choose; pilot on dev | **After 3** |
| 8 | Vote over passes or guideline variants | 0.8158, the only interval that excludes 0 | Small for one model, larger for heterogeneous | A method gain at k times the annotation cost | Free once 2 and 6 exist | **Report with 3** |
| 9 | Verified examples chosen by error type | Mechanism only; contradicting strings absent from validation | | Midterm point 2 | Needs loops | Later, or fold into 5 |
| 10 | Demonstration retrieval from more gold | Lexical precedent +0.017 at 563 documents | 15 to 20% in few-shot settings without guidelines | Breaks the 10-document budget | Loops plus passes | Only inside the learning-curve framing |
| 11 | Document-level propagation | −0.039 / +0.001 | | | | **Dropped** |
| 12 | Coverage-balanced development set for Modifier | Missed Modifier fell from 40 to 27 with top-4 | | | | Low priority |

## 6. Review of plan v1 (`docs/RP/20261020_research_plan_to_draft.md`)

### 6.1 What is good and should stay

- One controlled change per arm, a fixed protocol, and a pre-stated rule that a difference inside the noise band is "unproven".
- Repeat-based acceptance as a baseline, built on direct evidence (round 4).
- An honest expectation (six weeks will probably not reach the reference number) and a thesis that holds without reaching it.
- Costs written down before any run, and a fallback if the budget is refused.
- Track 2's aim: a measured answer to the replacement question, framed between the model alone and a simulated expert.

### 6.2 Problems

1. **Effort is not where the errors are.**
   - The plan's own section 2.1 puts the largest losses in subtype (0.875 if fixed) and boundary errors.
   - Arms 2 to 4 all target the FALDH mechanism, and section 2.2 says the strings involved never occur in the validation texts.
   - The mechanism could still matter on validation through over-broad rules (section 3.2 above), but the plan does not measure that. It measures total F1, contradiction counts and copied share.
2. **Track 1 cannot detect the effects it hopes for.**
   - With 3 loops per arm and between-run SD about 0.012, two arms must differ by about 0.028 to be detected 80% of the time.
   - The largest single-guideline gain seen so far is +0.026 (dev30), and none of the guideline differences is established.
   - The likely result is "unproven" for every arm, after spending most of the budget.
3. **Cost and comparability.**
   - ¥170,000 to ¥310,000 on GPT-5.4, or a move to DeepSeek, which breaks comparability with every existing GPT-5.4 number. The base paper's DeepSeek scored 0.55 / 0.56 on NCBI against GPT-5's 0.73 / 0.76.
   - Wall-clock time is also tight: one validation pass took about 5.9 hours (P3 report), and plan v1 needs 16 validation passes and 15 loops (12 of them with triple annotation) in four weeks.
4. **Existing evidence is not used first.** Four refined loop finals that were never validated already answer "is top-4 a method effect". The plan schedules more top-K loops as out of scope instead.
5. **No comparable yardstick and no untouched test.** The target is a cross-split, one-type number, and every evaluation stays on valid100, which has now been used to choose directions. The base paper kept the official test split unused "for future benchmarking"; one final use of it, agreed with the authors, would give a clean claim.
6. **Repeat-based acceptance decides on mean F1 only.** With 3 repeats and a 0.012 threshold, most rounds (typical gain 0.01 to 0.02) will be rejected, and the loop may stop at round 1. The repeats contain more information than the mean: whether the targeted fixes reproduce, and whether the regressions do. Gating on reproducible entity changes uses the same calls and is closer to how the case study found round 4's problem.
7. **Track 2 has no free baseline.** Agreement between passes already reaches 0.887 after checking 20% of entities. A Claude reviewer counts as useful only if it beats that, or finds the consistent errors that agreement misses.
8. **Arm 3 and the inline comment "this amounts to telling the model the answer".** Two concerns are mixed together:
   - Leakage: no. Development gold is the loop's training signal; Discrepancy Analysis and Pattern Explanation already see it, and the base paper (§3.4.4) says Guideline Refinement receives "the discrepancy context", which the implementation omits. Validation and test gold never enter.
   - Hard-coding: yes, a real risk. A rewrite that sees gold strings can copy them into rules, which is midterm point 1.

   The comment's instinct is right about the second concern. The remedy is to use gold as a check after writing, not as writing material. The rewrite stays as it is; a deterministic check compares every annotate / do-not-annotate example with development gold. When one contradicts gold, the rewrite is asked once to remove or narrow that rule, with an instruction not to add the string as an example, and copied share is measured afterwards. So arms 3 and 4 merge into one arm (direction 5).
9. **Inline question: can the Pro subscription run the reviewer?** It is possible for prompt development, by running Claude Code non-interactively (`claude -p`) on the development documents, within the plan's usage limits. For thesis numbers it is weaker:
   - Claude Code adds its own system prompt and tools.
   - Sampling settings cannot be set.
   - Per-call usage is not recorded the way the API records it.
   - Pro rate limits make a 100-document pass slow.
   - Whether scripted batch use fits the subscription terms should be checked; I could not confirm it.

   Suggested split: pilot with the subscription; run the validation and test passes through the API with a fixed model ID and logged usage, or report the Claude Code setting as a limitation. Either way, the reviewer must run in a fresh process that sees only the guideline, the document and the predictions. This session has read validation gold and error lists.

### 6.3 Verdict

Feasible only with budget approval, and not the best use of six weeks. The protocol ideas survive; the allocation changes. Plan v2:

1. Measures the yardstick and the existing guidelines first (cheap, decisive).
2. Tests the mechanism fixes by retrofitting them onto existing guidelines instead of running new loop families.
3. Puts the subtype errors and the review-effort curve at the center, because that is where the remaining F1 and the replacement question are.

Core cost estimate: ¥61,000 to ¥98,000; with all conditional steps, ¥118,000 to ¥188,000 (GPT-5.4, estimates).

## 7. Questions only Ken and Prof. Kim can answer

1. May we use the official NCBI Disease test split once, at the end, for the final claim? The base paper kept it unused for future benchmarking.
2. Is a fine-tuned model trained on the same 593 documents with the four subtypes, scored with the same strict scorer, the right yardstick? Have they seen four-subtype supervised numbers?
3. In their runs, was SpecificDisease/DiseaseClass confusion the largest validation loss? Did refined guidelines also turn "hereditary … cancer" into a class?
4. Their gated, append-only moderation overlaps with directions 5 and 6. Which parts should this thesis leave to them?
5. Would "F1 against the share of entities a person checks", with gold as the expert, count as evidence on the replacement goal? Would a small timed check by a real annotator be feasible?
6. Was "the first five documents by file name" an intended design for verified examples?

## 核查记录 (verification record)

**Commands (2026-10-19, no API calls)**

```
python -I todo-temp/direction-scan/offline_direction_checks.py   # sections A to H, C2
python -I todo-temp/direction-scan/plan_v2_cost.py                # cost estimates for plan v2
```

**Artifacts**

| File | SHA-256 (first 12) |
| --- | --- |
| `todo-temp/direction-scan/offline_direction_checks.py` | 5093d08fec9c |
| `todo-temp/direction-scan/offline_direction_checks_output.txt` | 4680e457c66e (identical on rerun; seeds fixed) |
| `todo-temp/direction-scan/offline_direction_checks.json` | 67a41aef6678 |
| `todo-temp/direction-scan/plan_v2_cost.py` | 993fdd007426 |
| `todo-temp/direction-scan/plan_v2_cost_output.txt` | a102ea385e65 |

**Sources for each statement**

| Statement | Source |
| --- | --- |
| Strict F1 of 8 runs, assertions against `metrics.json` | `offline_direction_checks.py` load section; `reproduction/results/*/metrics.json` |
| R4 rerun used the R4 guideline | `logs/ncbi_disease/valid-published-rerun.log` line 1 ("guideline 19940 chars", R4 has 19,940) |
| Bootstrap intervals for top-4, R4 rerun, vote | `offline_direction_checks_output.txt`, section H |
| Bootstrap for R4 and dev30 against original | `todo-temp/p4/20261007_p4_devsize_report.md`, section 3 |
| One-type F1, error kinds, 0.9606 bound | `todo-temp/meeting-20261020/error_breakdown_output.txt` |
| Unscored loop finals and hashes | `outputs/ncbi_disease/20260902_*/final/final_guidelines.txt`, hashed 10/19 |
| S/D confusion counts, precedent, cancer patterns | output sections D, F, H; cancer-pattern counts from an ad hoc query over the same files (regex in this report's section 3.2) |
| Review curves, missed candidates | output sections C, C2 |
| Propagation, dictionary, abbreviations, boundaries | output sections E, F, G |
| SD 0.0123 and detectable difference 0.028 / 0.024 | computed from the 8 strict F1 values; 2.80 × √(2·SD²/n) |
| Top-4 line 12 text | `outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/final/final_guidelines.txt` |
| One validation pass about 5.9 hours | `todo-temp/p3/20261007_p3_topk4_report.md`, verification section |
| Base paper on arXiv, ACL 2026 main | https://arxiv.org/abs/2605.20809 (read 10/19) |
| Base paper IAA, §6.2, Limitations, §3.4.4, DeepSeek 0.55 / 0.56 | `archive/references/backbone-research.pdf` (pdftotext) |
| Chen et al. 2025 numbers | https://pmc.ncbi.nlm.nih.gov/articles/PMC11972378/ (read 10/19) |
| Zhao and Goto 2025 Table 4 | `../papers/Zhao.pdf` (pdftotext) |
| Monajatipoor et al. abstract | https://arxiv.org/abs/2404.07376 (read 10/19) |
| DiZiNER abstract | `../papers/DiZiNER-...pdf` (pdftotext) |
| Ken's draft details | `../papers/multi-annotator setting.pdf` (pdftotext); unpublished |
| Other literature rows | literature search summaries of 10/19; marked "to check" where not read in full |
