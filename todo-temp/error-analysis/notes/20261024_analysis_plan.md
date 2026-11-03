# Data analysis plan: what the reproduction outputs show, and which change to make

Superseded by `20261024_analysis_rules.md` after the user's decisions of 10/24. Kept as the first draft, which the first review read.

Draft, 2026-10-24, for independent review. Offline only: no API calls. It covers the professor's first action from the 10/23 seminar (error analysis and classification) and feeds step ⑥ (one change, second approval).

## Conclusion

Three questions, answered in order from the saved outputs of the 10/23 reproduction:

| # | Question | Why it matters |
| --- | --- | --- |
| Q1 | What errors does Haiku make with the original guideline, and what causes them? | The complete error classification the professor asked for (Q2, Q3 of 10/23) |
| Q2 | What does refinement change on validation? Why do some top-4 rewrites help while others hurt, and why does the development check not see it? | The reproduction found no significant gain, but top-4 spread its results: 3 loops above every original-guideline run, 3 below |
| Q3 | Which one change should be made next, and does it also cut missed mentions without adding extra ones? | Track 1 (better F1) and Track 2 (fewer missed mentions at a controlled price) |

Everything is descriptive. No new significance tests are run on these 30 validation runs; the change chosen in Q3 gets its own pre-registered experiment with new loops.

## 1. Data (all saved, committed in 0108501)

| Source | Content | Location |
| --- | --- | --- |
| E1 | Original guideline, 10 runs × 100 validation documents | `outputs/ncbi_disease/20261022_haiku-xhigh_e1_run01..10/` |
| top-1, top-4 | Final guideline of 10 loops each, annotated once on validation | `..._topk1_loop01..10/`, `..._topk4_loop01..10/` |
| Reasons and cited rules | Each predicted mention's rationale and the guideline section it cites (not kept in `valid_predictions`, only in the raw replies) | `..._batchqueue/replies/` (matched to run and document by prompt hash, as in `todo-temp/seminar-20261023/review_drop_check.py`) |
| Loop internals | Per round: error clusters, pattern analysis, principles, rewrite prompt, guideline before / candidate / after, development diagnostics per document | `.../rounds/iteration_NN/` |
| Development noise | Original guideline, 20 runs on the 10 development documents (Haiku xhigh trial) | `todo-temp/haiku-trial/units/` |
| Gold | Validation: 100 documents, 791 mentions. Development: 10 documents, 74 mentions | `data/datasets/ncbi_disease/` |

Of the 20 loops, 11 changed the guideline: top-1 loops 05 and 07, and every top-4 loop except 03. The other 9 ended with the original guideline.

## 2. Rules for this analysis

- **Validation gold is used for analysis and for choosing the change, never inside a loop.** Choosing the change from validation errors makes these 100 documents a set we chose with. So the change's test needs new loops, and any claim beyond that needs documents not used here (the official test split, still to be decided). Reports state this.
- **Noise reference.** Every loop's validation result is one annotation run. The 10 E1 runs measure how much one run varies: F1 SD 0.0105, missed mentions (FN) SD 8.4, extra mentions (FP) SD 7.5 (`reproduction_analysis_output.txt`). On the development documents, one run varies with F1 SD 0.0150 and FN SD 1.27 (`todo-temp/haiku-trial/fn_noise_output.txt`). A per-loop difference inside the range of the 10 E1 runs is not interpreted as a guideline effect.
- **Mention-level stability.** A gold mention counts as reliably found if E1 finds it in at least 8 of 10 runs, reliably missed if in at most 2, and unstable otherwise. The same thresholds apply to extra mentions. (Thresholds open for review.)
- **No GPT-5.4 data.** Every number comes from a saved script and its output in `todo-temp/error-analysis/`.

## 3. Steps

### Step A. Mention ledger (foundation for B and C)

- One row per (document, span, subtype) that appears in the gold or in any of the 30 validation runs.
- Per run, its outcome: correct, missed, extra, boundary mismatch (overlapping span), subtype mismatch (same span, other subtype). For predicted mentions, add the cited guideline section and the rationale.
- Check: the ledger reproduces every run's TP, FP and FN exactly as in `reproduction_analysis_output.txt`.

### Step B. Error classification for the original guideline (Q1)

1. **Kinds, complete and mechanical:** missed, extra, boundary, subtype (4 × 4 confusion), each by subtype. For each kind: its count and how much F1 would rise if that kind alone were fixed (computed against gold).
2. **Stability:** each error as reliable (at least 8 of 10 E1 runs), unstable (3 to 7) or rare (at most 2). Reliable errors are what a guideline change can address. Unstable ones are run-to-run variation.
3. **Causes, for reliable errors:**
   - first an automatic tag from the cited guideline section, string patterns (abbreviation, coordination, modifier inclusion) and precedent in the training split's gold;
   - then a manual check: all reliable errors if there are at most about 150, otherwise a sample of 50 stratified by kind, with the rest reported by automatic tag;
   - cause classes: the cited rule says otherwise; the guideline is silent; boundary convention; subtype convention; gold inconsistent with similar training gold; other or unclear.
4. **Agreement check:** Claude assigns causes; the user checks a random 30. The agreement rate is reported, so the classification is not one coder's opinion only.

Output: a table of kind × cause with counts, shares of all errors, and F1 that could be recovered. Every error falls in exactly one class, and "other or unclear" is reported, not hidden.

### Step C. What refinement changed (Q2)

1. **Per changed loop, mention gains and losses against E1:**
   - gained: a gold mention found by the loop but reliably missed by E1;
   - lost: a gold mention missed by the loop but reliably found by E1;
   - added and removed extra mentions, defined the same way.
   Changes for unstable mentions are reported separately, as possible noise.
2. **Link each gain and loss to a rule.** Diff the final guideline against the original. Use the cited section in each rationale to find the rule behind a gained or lost mention, and the round snapshots to find the round and principle that introduced it. Rule types: added inclusion rule, added exclusion rule (including named examples), rewritten definition, deleted rule.
3. **Three signatures seen in the top-4 results:**
   - over-inclusion: FP well above E1 (top-4 loops 06 and 07; top-1 loop 05);
   - over-exclusion: FN well above E1 (top-4 loop 10);
   - balanced recall gain: FN about 42 below E1 with FP unchanged (top-4 loops 01, 04, 08).
   Question: which rule types produce each signature? These groups were defined from validation counts, so the result is an explanation, not a test.
4. **Is it visible on the development side?** For each accepted round:
   - the change in development FN and FP, set against the development noise above;
   - compared with the same loop's validation FN and FP change;
   - the share of added rule text that copies development mentions literally (hard-coding, as measured in August).
   This asks whether a development-only check could have rejected the bad rewrites. With 11 changed loops it is descriptive.

### Step D. Choose the one change (Q3)

- **Candidate list** from B and C, plus the six earlier candidates (10/23 deck, slide 14). Each candidate is described by:
  - the error class it targets and how much F1 that class holds;
  - its mechanism;
  - whether it works with development data only;
  - its expected effect on FN and FP;
  - its cost;
  - the evidence behind it.
- **Selection criteria, fixed before the candidates are listed:**
  1. it targets a reliable error class or a bad-rewrite signature;
  2. it needs no validation gold;
  3. it changes one thing;
  4. it is expected to lower FN without raising FP;
  5. it is affordable.
- **Decision:** the user, then the professor (second approval). The change experiment gets its own design document with pre-registered tests and new loops.

## 4. Deliverables

| Order | Deliverable | Check |
| --- | --- | --- |
| 1 | Ledger script and output | Reproduces all 30 runs' TP / FP / FN |
| 2 | Error classification report (B) | Every error classified; agreement on the user's 30 checks |
| 3 | Refinement report (C) | Every gain and loss outside noise linked to a rule, or marked "no rule found" |
| 4 | Candidate list (D) | Each criterion answered with evidence |

Scripts and outputs go to `todo-temp/error-analysis/`. Each report ends with a verification record.

## 5. Not in this plan

- New API calls. If isolating one rule's effect needs a re-annotation, it is proposed separately with its cost.
- New significance tests on the 30 runs.
- Changes to the method, the guideline or the runner.

## 6. Open points for the review

- Stability thresholds (at least 8, at most 2 of 10).
- Manual cause coding: sample size and the agreement check.
- Whether the development noise reference (20 runs of the original guideline) is valid for judging rounds with other guidelines.
- Whether anything in Step C over-reads groups chosen by validation scores.
