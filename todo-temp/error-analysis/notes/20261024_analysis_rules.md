# Error clustering and analysis rules

Not used. On 10/24 the user dropped this procedure (second coder, blind sheet, written predictions) as too heavy. The analysis that was run is `20261024_error_analysis_report.md`.

Draft, 2026-10-24, for independent review before any analysis starts. It replaces the method parts of `20261024_analysis_plan.md` (the first draft, reviewed on 10/24) with the user's decisions of 10/24. Offline only: no API calls. Nothing below has been run, and no individual validation error has been read. The only validation look so far: aggregate counts (subtype shifts, misses without any overlapping prediction) for 8 runs over all 100 documents, shown to the user on 10/24.

## Conclusion

| # | Question | Data |
| --- | --- | --- |
| Q1 | Which errors do the 30 validation runs make, and why? | Validation, all 100 documents, all 30 runs pooled |
| Q2a | Why were rewrites rejected (9 loops never changed the guideline) or kept? | Development, every round of all 20 loops |
| Q2b | Why do some final guidelines score low on validation? | Validation, comparisons chosen after Q1 |
| Q3 | Which one change to test next? | Q1 and Q2; tested later on 50 locked training documents |

Errors are clustered in two layers: the paper's error kinds (mechanical, every error), then a cause (manual, coded without knowing which run produced the error).

## 0. Decisions (user, 10/24)

- Analyze all 100 validation documents. Test the chosen change on 50 training documents never used before.
- Build the classes from all errors pooled. Groups (original guideline, top-1, top-4) are not fixed in advance; each error keeps its run as a tag.
- Analyze the rejected rewrites, including the 9 loops that ended with the original guideline.
- Test set size 50. Measured price: on random halves of validation, the 95% CI half-width of the top-4 minus original-guideline difference grows from 0.0213 to 0.0248 (`test_size_check_output.txt`).

## 1. Data

| Set | Content | Use |
| --- | --- | --- |
| Validation | 100 documents, 791 gold mentions; 30 runs: original guideline 10, top-1 final 10, top-4 final 10 | Q1, Q2b |
| Development | 10 training documents (dev10), 74 gold mentions. Each round's snapshot lists every error before and after the rewrite (640 clusters checked, none truncated). The rationales are in the batch queue replies | Q2a |
| Development reference | 20 runs of the original guideline on dev10 (`todo-temp/haiku-trial/units/H_xhigh__*`), plus each loop's round 1 "before" run | Noise for Q2a |
| Test | 50 documents drawn from the 543 training documents never used | Locked until the change experiment |
| Precedent pool | Training documents minus the 50 test documents (543) | Gold precedent lookup only (§2.3) |

Rules:

- **Test lock, before Step A.**
  - Pool: training files not in `reproduction/dev_splits/ncbi_disease_dev50.json`, which contains dev10, dev20 and dev30; 543 files.
  - Draw `random.Random(20261024).sample(sorted(pool), 50)`. The script reads file names only.
  - Save the list with the seed and pool size to `reproduction/test_splits/ncbi_disease_heldout50.json` and commit it.
  - Until the change experiment is approved: nobody opens its gold, computes statistics on it or annotates it.
- **Validation gold** is used for analysis and for choosing the change, never inside a loop. The 10/23 results stay as reported.
- **Sources.** No GPT-5.4 data. Every number comes from a script and its saved output in `todo-temp/error-analysis/`.

## 2. Clustering rules

### 2.1 Layer 1: error kind (mechanical, every error)

For each run and document, gold and predicted mentions are (start, end, subtype). A strict match (same span and subtype) is correct. Every other mention is classified by `reproduction/lib/discrepancy.py`, which implements the paper's Section 3.4.1 categories. It pairs by largest overlap, in this priority order:

1. **Subtype error:** overlaps a mention of another subtype. Split further into same span and different span.
2. **Boundary error:** overlaps a mention of the same subtype, with different offsets.
3. **Missed:** a gold mention that no prediction overlaps.
4. **Extra:** a prediction that overlaps no gold mention.
5. **Unpaired overlap:** overlaps something already paired, as in merged or split coordinations.

- **Cluster key.** kind × gold subtype × predicted subtype, the same keys the loop uses (for example "Gold: DiseaseClass vs LLM: O (Missed)"). The loop pairs in document order and this module by largest overlap, so a few items can land differently. On development, where both exist, the disagreement rate is reported.
- **Two counts.** Strict scoring counts a subtype or boundary error as one FP plus one FN. Reports give:
  - strict TP / FP / FN, which must reproduce `valid_metrics.json` for all 30 runs exactly, or the work stops;
  - error events, with each pair counted once. Per run, these must equal `discrepancy_counts` in `valid_metrics.json`.
- **Misses at three levels, for Track 2:** strict FN; FN ignoring the subtype (no prediction at the exact span); pure misses (no overlapping prediction at all).

### 2.2 Error items across runs

- **Items.** One error item is a gold-side error keyed by document, gold span and subtype, kind, and predicted span and subtype. An extra is keyed by document, predicted span and subtype.
- **Weighting.** Every table sums occurrences over runs, so an error made in 25 runs weighs 25 and one made once weighs 1. No threshold drops any error.
- **Stability**, as a description only: for each class, the share of its occurrences coming from items made in at least 8, in 3 to 7, or in at most 2 of the 10 original-guideline runs.

### 2.3 Layer 2: cause (manual, blind to the run)

**Unit and view.** Each distinct item is coded once; its weight is its occurrence count. A script writes a shuffled coding sheet with random item IDs. For each item it shows:
- the text around the mention;
- the gold annotation and the prediction;
- for a predicted mention, the model's rationale and cited section;
- the full text of the guideline that run used, under a random code;
- the precedent lookup.

It hides the run, method, loop, score, and every other run's result. The mapping file is not opened until coding ends. Limit: the original guideline is recognizable, so the coder is blind to the run and its score, not to whether the guideline was changed.

**Rule support.** A rule supports an annotation if its words or one of its listed examples cover this mention when read literally. Each item gets exactly one cause, decided in this order:

| Order | Cause | Test |
| --- | --- | --- |
| 1 | Gold doubtful | Mechanical precedent: the same string (exact, case-insensitive) occurs at least 3 times in the precedent pool, and more than half of those are annotated the way the prediction is (same subtype and span; for a missed item, not annotated; for an extra item, annotated). The coder only confirms the string means the same in context |
| 2 | Rule leads to the error | A rule in the run's guideline supports the prediction (for a missed item: excludes the mention), and no rule supports the gold |
| 3 | Model ignores the rule | A rule supports the gold, and no rule supports the prediction |
| 4 | Guideline contradictory | Rules support both |
| 5 | Guideline silent | No rule decides the case |
| 6 | Unclear | The coder cannot tell whether a rule applies. Reported, not hidden |

For causes 2 to 4, the coder records the rule. Comparing the run's guideline with the original then marks it as original, added, deleted or rewritten.

**Surface tags**, automatic and not exclusive. They describe items but are not causes:
- abbreviation;
- coordination;
- modifier position (the mention stands directly before a noun such as "patients", "gene" or "mutation");
- gene or protein name containing a disease word;
- plural or generic term;
- nested mention.

The exact patterns live in the script.

**Scale.** If there are more than 600 distinct items, items are coded in descending weight until 80% of all occurrences are covered. A random 50 of the rest are also coded, to show whether their cause mix differs. The uncoded share is reported.

**Agreement.**
- The user codes at least 50 items on the same blinded sheet without seeing Claude's codes. They are stratified by kind in proportion, with at least 5 per kind.
- Report Cohen's kappa (agreement corrected for chance: 1 is perfect agreement, 0 is chance level) with a 95% bootstrap CI (2,000 resamples), and the confusion between the two coders.
- If kappa is below 0.6, the usual line for acceptable agreement, the definitions are revised once and all items recoded. Both rounds are reported.

## 3. Analysis rules

### 3.1 Q1: error profile (validation)

- One table of class (layer 1 × layer 2) with:
  - occurrences over the 30 runs and the mean per run;
  - the share of all strict FP and FN;
  - F1 if that class alone were fixed. This is computed per run, then averaged, and is not additive across classes.
- The same counts per run go to a separate output file.

### 3.2 Q2a: rejected and kept rewrites (development)

- **Scope:** all 44 rounds (26 kept, 18 rejected). For each round, compare the before run with the candidate run:
  - per gold mention: lost (found before, missed by the candidate) and gained;
  - per extra mention: added and removed;
  - all by layer-1 class.
- **No-change reference.** Lost and gained counts between pairs of original-guideline development runs. The 20 trial runs are pooled with the 20 loops' round 1 "before" runs only if their per-document annotation prompts are identical (`prompt_sha256`); otherwise only the 20 loop runs are used. A round's lost or gained count above the reference's 95th percentile is "beyond noise".
- **Rule links.**
  - Diff each candidate guideline against its before guideline (added, deleted, rewritten rules).
  - Link a gained or added mention to a changed rule through the candidate's cited section, resolved within that candidate's text.
  - Link a lost mention through its string appearing in a changed rule; otherwise mark "no link found".
  - These links show association only.
- **Hard-coding.** The share of added rule text that copies development mention strings literally.
- **Two questions, both descriptive:**
  1. What separates rejected from kept rewrites?
  2. Would an acceptance rule that also rejects a development FN rise beyond noise have changed any decision? This is replayed on the recorded counts.

### 3.3 Q2b: why some final guidelines score low (validation)

- **Exploratory.** The comparisons are chosen after Q1, from what Q1 shows, and the report says so.
- **Class counts.** For each of the 11 changed loops: each class's count against the range of the 10 original-guideline runs.
- **Loop-specific errors** are items the loop gets wrong that the original guideline gets right in at least 9 of 10 runs. **Loop-specific fixes** are the reverse.
  - No-change reference: the same counts for each original-guideline run against the other 9 (right in at least 8 of 9).
  - Report the loop's count minus the reference mean, with the reference range.
- **Rule links.** Each loop-specific error or fix is linked to a rule:
  - the diff of the final guideline against the original;
  - the cited section, resolved within that loop's guideline, since rewrites renumber sections;
  - the round that introduced the rule, from the snapshots.

  These links show association only. Testing cause (inserting one rule into the original guideline and re-annotating) is a separate paid proposal.

### 3.4 Q3: choosing the change

Criteria, fixed before candidates are listed:

1. It targets a class with a large share in Q1, or a failure pattern from Q2.
2. It needs development data only at run time (no validation or test gold).
3. It changes one thing.
4. It is expected to cut missed mentions while keeping F1 (the professor, 10/23; confirmed by the user, 10/24).
5. It fits an approved budget.

Decision: the user, then the professor. The change experiment gets its own design, with pre-registered tests on the 50 locked test documents.

### 3.5 Not done

- Significance tests on the 30 validation runs (all of this is description).
- API calls.
- Changes to the method, the guideline or the runner.
- Opening the test gold.

## 4. Outputs and checks

| Order | Output | Check |
| --- | --- | --- |
| 0 | Test list (§1) | 50 names, all in the pool, committed before Step A |
| 1 | Ledger: one row per run × document × item, validation and development | Reproduces strict TP / FP / FN of all 30 runs and every round's development counts; layer-1 counts equal `discrepancy_counts` |
| 2 | Coding sheet and mapping (§2.3) | Sheet shows no run information |
| 3 | Q1 table | Every occurrence in exactly one class |
| 4 | Q2a and Q2b reports | Every item beyond the reference linked to a rule or marked "no link found" |
| 5 | Candidate list (Q3) | Each criterion answered with evidence |

Each report ends with a verification record.

## 5. Open points for review

- Cause order and the precedent test (at least 3 occurrences, more than half).
- The scale rule (600 items, 80% of occurrences).
- The no-change references for Q2a and Q2b.
- Whether blinding means anything when the guideline text is visible.
- Whether 50 test documents are enough for the change experiment.

## Verification record

- **Test size:** `todo-temp/error-analysis/scripts/test_size_check.py` and its output `test_size_check_output.txt`.
  - Per-document counts reproduce `valid_metrics.json` for all 30 runs.
  - SD of F1 across runs, 100 documents against random halves: original 0.0105 against 0.0151; top-1 0.0139 against 0.0180; top-4 0.0288 against 0.0327.
- **Unused training documents:** 593 in `data/datasets/ncbi_disease/train/`. 50 are in `ncbi_disease_dev50.json`, which contains every other dev split. None of the other 543 is named in `outputs/*/inputs/`, `todo-temp/`, `archive/` or `docs/`.
- **Error kinds:** `reproduction/lib/discrepancy.py` (module docstring). The loop's clusters: `src/llm_guideline_moderation/iterative.py`, lines 150 to 275.
- **Development snapshots:** `rounds/iteration_NN/snapshot.json` of all 20 loops. 640 clusters, each with as many examples as its count. 44 rounds, 18 rejected.
- **Trial runs:** `todo-temp/haiku-trial/units/` holds 200 `H_xhigh` files (10 documents × 20 runs).
