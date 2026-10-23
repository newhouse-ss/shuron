# Design: top-1 against top-4 on Haiku (the reproduction)

Run on 2026-10-23 as designed below; results in `reproduction_analysis_output.txt` (script `reproduction_analysis.py`). The text below is the design as fixed before the run.

Draft, 2026-10-23. Paid runs start only after the user approves this design, its budget and the decisions in §8, and after the steps in §7.

## Conclusion

- The experiment can be designed now and is close to runnable: the batch runner works, and the 10/22 pilot counts as loop 1 of each method (user, 10/22).
- It tests whether top-4 loops end with guidelines that score differently on validation from top-1 loops. It cannot be set up to guarantee a significant result. The outcome is reported either way; the 10/23 seminar accepted a well-discussed result without a stable gain (TODO.md, Q4).
- With 10 loops per method and p < 0.05, the test finds a gap of about 1.3 times the loop-to-loop SD four times out of five. That SD has never been measured on Haiku; these loops measure it.
- Before the first paid call: approval, money, the admin notice, the runner changes from the code review and a commit (§7).

## 1. What is compared

A loop starts from the original guideline, refines it on the 10 development documents round by round, and ends with a final guideline. That final guideline is annotated once on the 100 validation documents and scored, so one loop gives one validation F1. Ten loops per method show how much a method's result varies from loop to loop, and whether the two methods' averages differ by more than that.

The two methods, as implemented, differ in three ways, so a difference belongs to the method as a whole and not to the number of clusters alone:

| | top-1 | top-4 |
| --- | --- | --- |
| Code | published loop, `iterative.run_iterative_refinement` | `reproduction/moderate_topk.py`, k = 4 |
| Clusters refined per round | the largest one | the four largest |
| Rewrite | one principle | four principles merged in one rewrite |
| Rewrite prompt | published template | published template plus one instruction for principles that contradict each other |

## 2. Runs

| Arm | Count | New runs | What runs |
| --- | --- | --- | --- |
| E1 | 10 runs | 10 | The original guideline annotated on validation 10 times; no refinement |
| top-1 | 10 loops | 9 (loops 02 to 10) | Loop 01 is the 10/22 pilot |
| top-4 | 10 loops | 9 (loops 02 to 10) | Loop 01 is the 10/22 pilot |

- The count of 10 is the user's default (10/22), set before any Haiku noise data.
- All loops of both methods advance together, one batch per step, as in the pilot.
- A top-1 loop whose first candidate is rejected ends with the original guideline (pilot loop 01 did). Its validation run is then one more run of the original guideline. That is how the method behaves; such loops are kept, not replaced.

## 3. Fixed for every run

- Model: `claude-haiku-5-5`, effort xhigh, adaptive thinking, Batch API, max_tokens 128,000, structured output for annotation. The runner sets `PYTHONHASHSEED=0`.
- Development: `reproduction/dev_splits/ncbi_disease_dev10.json`. Starting guideline: `data/guidelines/ncbi_disease_guidelines.txt`. n_examples 5.
- Loop rule, as published: a round is kept only if development F1 improves. The loop stops at the first round that does not improve, at development F1 0.9, or after 20 rounds.
- A rewrite cut off at the output cap on all 3 tries: with `--stop-at-cap` the loop ends with its last accepted guideline (proposed for all loops; §8).
- Validation: `data/datasets/ncbi_disease/valid`, scored with strict PubAnnotation matching (`reproduction/lib/scoring.py`). Its gold never reaches the loop.
- Development F1 uses the loop's set scoring and validation F1 uses strict matching; the two are never mixed.

## 4. Measures

- **Primary:** validation strict F1 (exact span and subtype) of each final guideline: one number per loop or E1 run.
- **Secondary, reported without tests:**
  - missed (FN) and extra (FP) mentions on validation, the Track 2 measures;
  - precision and recall;
  - rounds kept;
  - development F1 at the start and the end;
  - final guideline length;
  - cost per loop.

## 5. Analysis, fixed before the run

Terms:

- **SD (standard deviation):** how far single results typically sit from their average.
- **Welch t-test:** checks whether two averages differ by more than their spread explains, without assuming both groups vary equally. Its p-value says how often a gap this large would appear if the two methods were really the same.
- **95% CI (confidence interval) of a difference:** the range of differences the data are consistent with.
- **Two-sided:** a gap in either direction counts. top-4 may also score lower on validation, since its guidelines fit the 10 development documents (pilot: development 0.958, validation 0.741).

Tests:

| | Question | Compared | Decision |
| --- | --- | --- | --- |
| P1 | Does top-1 differ from the original guideline? | 10 top-1 loops against 10 E1 runs | Welch, two-sided, p < 0.05 |
| P2 | Does top-4 differ from top-1? | 10 top-4 loops against 10 top-1 loops | Welch, two-sided, p < 0.05 |
| P3 | Does top-4 differ from the original guideline? | 10 top-4 loops against 10 E1 runs | Welch, two-sided, p < 0.05 |

- Every t-test uses 5% (user, 10/23). Each comparison alone has a 5% chance of a false "difference"; with three, the chance that at least one shows one is up to about 14%. The report says three tests were run.
- "Not significant" does not mean "equal", so a pattern such as P3 significant with P1 and P2 not is not a contradiction.
- Open: whether to add Holm's rule or a permutation test. Settle it before anyone looks at the validation difference: a rule chosen after seeing the result is no longer a test.
- For each test, report: the two means and SDs, the difference with its 95% CI, and p.

What the test can detect: the gap it finds four times out of five, in units of the loop-to-loop SD (`design_numbers_output.txt`):

| Loops per method | p < 0.025 | p < 0.05 |
| --- | --- | --- |
| 5 | 2.33 | 2.03 |
| 10 | 1.48 | 1.32 |
| 15 | 1.18 | 1.06 |
| 20 | 1.00 | 0.90 |

How to read it: if the loop-to-loop SD were 0.02 F1 (an illustration, not a measured value), 10 loops per method at p < 0.05 would detect a gap of about 0.026.

Rules:

- Nobody looks at the validation difference between the methods before all loops finish. Development F1, failures and cost are watched only to keep the loops running.
- No extra loops because a result is not significant. No loop is dropped or replaced because of its score.
- A loop that fails (a call refused or unparseable after 3 tries, or a batch error) is resumed by rerunning the runner. A resume replays saved replies, so nothing is paid twice.
- A loop ended by the output cap counts, with its last accepted guideline.

What each outcome would mean:

- **P2 significant, top-4 higher:** top-4's gain is larger than loop-to-loop variation, on this model and these documents.
- **P2 not significant:** no evidence of a difference. The CI shows how large a difference is still possible. Reported as is.
- **P2 significant, top-4 lower:** top-4's guidelines fit the development documents at the cost of validation.

## 6. Cost and time

Batch prices, estimated from the pilot (`design_numbers_output.txt`, from `phase1_budget_output.txt`). These are not upper bounds: a loop can run up to 20 rounds.

| JPY | Like the pilot | Four rounds each |
| --- | --- | --- |
| 9 top-1 loops | 684 | 991 |
| 9 top-4 loops | 1,793 | 1,335 |
| E1, 10 runs | 634 | 634 |
| Total | 3,110 | 2,960 |

- "Like the pilot" assumes every top-1 loop stops after 1 round and every top-4 loop after 6, as the pilot loops did.
- `--cap-usd` counts every saved reply in the batch queue, including the pilot's JPY 284.89. Covering the pilot plus the higher estimate needs USD 21.48. Proposed cap: USD 25 (about JPY 3,950). It is a stop, not a target: once reached, no batch is sent and the user decides.
- Time: the pilot's first run took 6 batches in about 36 minutes for two loops (PROGRESS.md, 10/22). Batch time with 18 or more loops per batch has not been measured.

## 7. Before the first paid call

1. The user approves this design, the budget and the decisions in §8. Every paid run needs approval.
2. Money: the API balance is about USD 0.35. The professor said to ask first whether DBCLS can provide a Claude API key. Until then the user pays and claims later (form, receipt, and a bank statement with the USD conversion rate).
3. Admin notice: spending since 10/21 is JPY 1,040, over the JPY 1,000 line (v4 §5).
4. Runner changes from the code review (`code_review_20261023.md`), each tested offline with a fake client before any paid call:
   - Required: start at loop 02 and leave loop 01 alone; an E1 mode that reuses the loop's validation step, with a separate run name per repeat.
   - Recommended: split a batch above a size threshold (the Batch API takes at most 256 MB); allow more tries on a resume, so a call with three unusable replies cannot block its loop for good.
5. Commit the uncommitted work, so every run records the code it ran with.
6. The design goes to the professor together with the results (user, 10/23).

## 8. Decisions (user, 10/23)

| Decision | Choice | Why |
| --- | --- | --- |
| `--stop-at-cap` for all loops | Yes | Without it, a top-4 loop whose rewrite exceeds the cap fails and leaves a gap in the data. top-1 replies stayed under 37,500 tokens (PROGRESS.md, 10/22), so it changes nothing there |
| Include E1 | Yes | Needed for P1 and to measure how much one annotation run varies on validation |
| Spending cap | USD 25 | §6 |
| Significance level | 5% for every t-test | User's choice; Holm or a permutation test still open (§5) |
| Professor | The design goes with the results | No wait before the run |

## Not in this design

- top-2 and top-3 (asked about at the seminar; each would add 10 more loops);
- a stronger-model control;
- a second corpus;
- the Track 2 method;
- the error taxonomy (offline; it can start now on existing outputs).

## Verification record

- Budget and detectable gaps: `todo-temp/seminar-20261023/design_numbers.py` (6662a46356a6), output `design_numbers_output.txt` (05783c98638b). It reads `todo-temp/haiku-trial/phase1_budget_output.txt` (ee60fe4e0191).
  - The simulated critical values match t tables: 2.097 against 2.101 at 0.05 with 18 degrees of freedom.
- Runner behaviour (lockstep batches, resume, `--stop-at-cap`, `--cap-usd`, hash seed): `reproduction/haiku_batch_loops.py` (1934cd39e62a), its docstring and `run_loop`.
- The hash-seed effect on analysis prompts: `todo-temp/haiku-trial/replay_check_output.txt` (f81d112abb4d).
- How top-4 differs from top-1: `reproduction/moderate_topk.py` (03800d68dcaf), docstring and `main`.
- Pilot loops: `status.json` of `outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop01` (1 round, rejected, validation 0.6986) and `_topk4_loop01` (6 rounds, threshold reached, validation 0.7411).
- No API calls were made for this design.
