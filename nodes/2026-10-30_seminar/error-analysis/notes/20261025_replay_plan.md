# Replay test of the per-document cap: plan (draft)

2026-10-25. Draft for your decision; nothing runs until you approve it. Items marked **[decide]** are proposals. Background: `20261024_error_analysis_report.md` §5 and Appendix D.

## 1. Question

When the analysis and rewrite prompts list **every** correct mention of the five documents they already show, do the rewrites write fewer rules against the gold for constructions whose labels the five-item cap used to hide?

## 2. What changes, and what stays fixed

- **Changed (one variable):** the per-document cap on correct mentions in `_build_true_positive_examples`, which feeds both the analysis and the rewrite prompts.
- **Fixed:** five documents shown; five error examples per cluster; prompt templates; claude-haiku-5-5, effort xhigh, Batch API, max_tokens 128000; PYTHONHASHSEED 0; the 10 development documents and their scoring.
- **Check before sending:** each new prompt differs from the recorded one only inside the list. Any other difference stops the run.

## 3. Design

- **Starting states:** the 44 recorded rounds of the 20 Haiku loops (the same guideline, baseline annotation and error clusters). Each is replayed once: analysis, principles and rewrite regenerated, and the candidate annotated once on the 10 development documents.
- **Control:** the recorded round. It counts as a control only under the fixed settings above. Top-1 loop 01 round 1 ran with another hash seed, so it is left out of the main analysis **[decide: or rerun its control]**.
- **Unit of analysis:** the loop (20 clusters). Rounds of one loop share a guideline history and are not independent.
- **Exposed rounds:** the change only matters where the uncapped list contains the target mention, which happens when Haiku had it right before the rewrite. That's 29 of 44 rounds for the family-history mention, and 53 of 88 mention × round cases for the two symptoms (`rule_chain_output.txt` B).

## 4. Measures

- **Primary [decide]:** in exposed rounds, whether the candidate states a rule against the gold for the target construction: Modifier after "a family history of", or O for bare symptoms in a list. The rule texts are coded as in Figure 7, blind to arm where possible. The comparison is the paired difference, treatment minus control, summarized per loop.
- **Negative control:** the gene-word rule, whose labels were already listed in 105 of 112 cases. It should not change.
- **Secondary:**
  - development F1 change and keep decisions;
  - development true misses;
  - the copy rate of development gold strings (`reproduction/measure_hardcoding.py` definition);
  - the copy rate of the newly listed strings in particular.

## 5. Criteria

- **Success [decide]:** the against-gold rule rate in exposed rounds is at least halved against control, and the loop-level paired comparison points the same way in most loops (sign test across loops, two-sided 5%, reported with its count).
- **Guards [decide]:**
  - development F1 of the candidates is not lower than control by more than 0.021, one SD of the difference between two runs;
  - the copy rate is not higher than control by more than 5 percentage points.
  - A guard breach is reported as a cost, not hidden by the primary result.
- **The result is read as:** evidence about one local mechanism in one round. It says nothing about the multi-round loop, validation F1, or either track's goal.

## 6. Pilot, budget, stopping

- **Pilot [decide]:** 4 recorded states, 2 top-1 and 2 top-4, at least one of them exposed for the family-history mention. It checks the prompt diff, reply parsing and cost per state; outcomes are not inspected. About JPY 45 (estimate, from JPY 471 for all 44 in `example_caps_output.txt`).
- **Full replay:** the remaining 40 states, about JPY 430 (estimate), only after the pilot passes and you approve.
- **Budget cap [decide]:** JPY 600 in total, enforced by the runner's spending cap. That is below the JPY 1,000 reporting line.
- **Stop if:** a prompt differs beyond the list; the cap is reached; the pilot shows a pipeline failure.
- **No interim looks** at the primary measure.

## 7. Data rules and next step

- Development gold only. No validation data in the replay, and the 50 held-out test documents' gold is not read.
- **If it succeeds:** fix one method version and evaluate it once on the 50 held-out documents. Track 1: strict F1. Track 2: true misses, extra mentions and each kind of edit, against an F1 margin fixed in advance **[decide]**. True misses stand in for search effort; no correction time is measured, so no result claims that expert time is saved.
- **Implementation needed:** a replay mode in the runner that loads a recorded round's state, and n_examples split into three parameters. This could go to Codex with this page as the spec.
