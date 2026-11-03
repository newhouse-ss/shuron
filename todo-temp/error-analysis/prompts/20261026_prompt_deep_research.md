The goal is to complete and pass a master's thesis (修士論文) on LLM guideline refinement for biomedical NER.

Find out:
- what thesis the existing evidence can already support;
- what further work, feasible in the remaining time and budget, would make it defensible;
- which method-level changes, if any, the data and the literature support as the thesis's own contribution.

Start from the data, and mark every claim or direction that lacks data support. Do not restate earlier proposals unless the data support them.

## What the thesis has to meet (recorded requirements only)

From the 10/20 meeting (`PROGRESS.md`, 10/20 entry; `docs/RP/20261020_research_plan_v4.md` §2):
- 後藤教授:
  - one case analysis is not enough for a paper; an error taxonomy covering all errors is needed;
  - the conclusion must state the method's advantage over traditional ML or fine-tuning: it needs only a little annotation.
- 後藤教授 and Kim 教授: not all annotation needs expert correction; correction matters mainly when building benchmarks, and more and more uses take LLM annotation as is. Hence two tracks:
  - Track 1: annotation quality used without correction. Main measure: strict four-subtype F1 against the base paper on the same 100 validation documents (original 0.73, moderated 0.76).
  - Track 2: expert correction when building benchmarks. FN is the main measure because filling a missed mention costs as much as manual annotation; FP is the cost.
- Kim 教授: experts read the full text anyway, so tune toward recall.
- Ken:
  - the method's other steps, such as discrepancy classification and principle generation, can be changed;
  - the earlier top-4 gain interval included 0;
  - rerunning on a new model with the conclusion unchanged is acceptable;
  - no expert annotations are available.
- 10/23 seminar: Track 2 is as necessary as Track 1. Voting over repeated runs is rejected because it only exploits LLM randomness.
- The thesis does not claim that an LLM replaces independent annotators, or that the method beats the base paper in absolute score (plan v4 §2.3).
- Schedule (plan v4 §5; it may have slipped):
  - error taxonomy, Track 2 trade-off and choice of the Track 1 change: 11/03 to 11/09;
  - Track 1 experiments: 11/10 to 11/23;
  - buffer and the single test-set evaluation: 11/24 to 11/30;
  - writing: from December.
- The formal passing criteria and the submission deadline are not recorded in the repository. List them as open questions for the user; do not assume them.

## Research questions

1. Which thesis claims do the existing data already support, at what strength, and what is missing for each? Cover:
   - Track 1;
   - Track 2;
   - the error taxonomy;
   - the comparison with the base paper;
   - the reproduction on the new model.
2. Which method-level changes do the data and the literature support, which can be tested within the schedule and budget, and how much evidence would each add to the thesis?
3. For Track 2, what do the data say about trading FP for fewer FN without voting? Which method changes could do it?
4. Which published work positions the thesis? Cover:
   - guideline refinement for LLM annotation;
   - prompt or instruction optimization with candidate selection or acceptance steps;
   - LLM-assisted annotation and the cost of human correction;
   - learning curves comparing a little annotation with fine-tuning.

## The loop

Code: `src/llm_guideline_moderation/iterative.py` in `H:\Git\research\修論\llm-guideline-moderation-source`.

Each round of the loop does the following:
1. Claude Haiku 5.5 (effort xhigh, Batch API) annotates 10 development documents of NCBI Disease (74 gold mentions) with a guideline. The labels are SpecificDisease, DiseaseClass, Modifier and CompositeMention.
2. Discrepancies against gold are clustered by label pair.
3. The top-1 or top-4 clusters each get an analysis and a principle.
4. One rewrite merges the principles.
5. The development documents are re-annotated, and the round is kept if development F1 rises at all.

## Data available (all saved; offline only)

- `outputs/ncbi_disease/20261022_haiku-xhigh_{topk1,topk4}_loop01..10/`: 20 loops, 44 rounds.
  - `rounds/iteration_NN/snapshot.json` holds the guidelines, per-mention development predictions before and after, and the error clusters.
  - The same folder holds every prompt, the final guidelines, the validation predictions and `valid_metrics.json`.
- `outputs/ncbi_disease/20261022_haiku-xhigh_e1_run01..10/`: 10 validation runs of the original guideline.
- `outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/`: raw replies with a per-annotation `rationale` and `guideline_section`. Each loop's `calls.json` maps calls to reply ids.
- Gold:
  - `data/datasets/ncbi_disease/train` (593 documents). Exclude the 50 listed in `reproduction/test_splits/ncbi_disease_heldout50.json`, and never open their gold.
  - `data/datasets/ncbi_disease/valid` (100 documents, 791 mentions).
- `todo-temp/error-analysis/` (index: `README.md`):
  - reports in `reports/`;
  - scripts in `scripts/`;
  - results in `outputs/`, including `error_rows.csv` (every error of the 30 validation runs), `rule_links.json`, `rule_chain.json`, `topk4_stability.json`, `keep_criteria.json`, `history_tally_output.txt`, `test_power_output.txt`, and `example_caps_output.txt` (measured cost per call).
  - Read the reports' limits sections. The hand-coded contradiction check in the report's §3.5 and appendix C is not robust.
- Project records: `OVERVIEW.md`, `PROGRESS.md`, `LOG.md`, `docs/RP/20261020_research_plan_v4.md`, and the midterm materials listed in `OVERVIEW.md`.

## Findings so far (verify before relying on them)

- Haiku's errors with the original guideline repeat across runs: 71% of a run's errors appear in at least 15 of 19 runs. Two groups of missed mentions make up 46% of all errors (10/24 report).
- 19 original-guideline validation runs score F1 0.692 to 0.724. The 11 changed guidelines score 0.659 to 0.748, one run each. The pre-registered tests P1 to P3 were not significant.
- Among top-4 loops:
  - Loops above the original range broke 27 validation mentions on average and loops below it broke 61; they fixed 52 and 36.
  - The extra breaks line up with rules that contradict the development gold of phrases they quote.
  - The keep decision on net development F1 let those rules in. Thresholds on that F1 do not separate harmful from helpful rounds (report §2, §3.5; appendix D.6).
- Track 2: true misses (a gold mention no prediction overlaps) number 135.6 per original run. Some changed guidelines have fewer without lower F1, in single runs. No correction time was measured.
- Development F1 of one run varies with SD about 0.015.

## Tasks

1. Data mining for each research question.
   - For Q2: use features available inside the loop when a rule is written (development predictions, prompts, annotator rationales and cited sections, rule wording, source cluster). Measure how well each would have flagged the rule edits that later hurt on validation, and how often it would wrongly flag helpful ones. Use validation only as the outcome being explained, and say so.
2. Feasibility checks the data allow offline. Examples:
   - Do `guideline_section` citations identify the rule behind a changed label?
   - How many training-gold instances exist per construction?
   - How large are run-to-run flips per mention?
   - What statistical power does a run budget give?
3. Literature with exact references (authors, year, venue, and the section or table used). Do not cite anything you have not read.
4. Synthesis: 2 or 3 candidate thesis storylines. For each, give:
   - the central claim;
   - which recorded requirement each part meets;
   - the evidence already in hand;
   - the missing experiments, with cost from measured per-call costs and time against the schedule;
   - the risks and what happens if the key experiment fails.
   Rank them by how likely they are to be finished and defended in time.

## Constraints

- No API calls and no paid runs. Every number must trace to a saved file. Separate what was observed from what is inferred.
- Development gold may feed refinement. Validation gold is for evaluation and analysis only. Test gold is never read.
- Ideas derived from validation analysis are evaluated once, at the end, on the 50 held-out test documents.
- Do not use GPT-5.4 outputs for any decision; they are kept only as a case study.
- Do not propose voting or ensembling over repeated LLM runs.
- Every paid run needs the user's approval, and spending over JPY 1,000 must be reported to the administrator. Include this in any cost plan.
- Never read `.env` or credential files.

## Output

A report with these parts:
1. Conclusion first.
2. Claims against evidence, as a table.
3. Features tested, with flag rate and false-flag rate.
4. A literature table.
5. The ranked storylines.
6. Open questions for the user.
7. Limits.
8. A verification record: scripts, commands, artifacts, and SHA-256 hashes of the outputs.
