# Codex task: locate the guideline text behind each prediction (2026-11-06)

## Purpose

This is preliminary error analysis on valid100. Each bar on slide 5 is split into per-instance differences against the 19 original-guideline runs; the next step is to find, for every changed prediction, the guideline text the model relied on, so that gains and losses can be summed per guideline item. The result is a list of candidate items; whether an item actually caused a change is tested later by control experiments. You only locate text and aggregate. Do not judge whether annotations are correct and do not draw conclusions.

This replaces script-based parsing of citations, which resolved 72 of 342 inferred references to the wrong line in top-4 loop04, 05 and 06 (mostly by stopping at a rule heading when the citation named an exception or sub-item under it).

## Hard rules

1. **Locate by reading, never by code.** Every locating decision comes from reading the prediction's citation, rationale and context against the guideline. Do not map citations or rationales to lines with regex, keyword, string-similarity or embedding matching, and do not write such a script even as a first pass. Code may only read inputs, write outputs, track progress, check that quotes occur verbatim, and aggregate in Phase 3.
2. **No API or network calls** of any kind (no DeepSeek, OpenAI, Azure, Anthropic).
3. **Stay blind until Phase 3.** During Phases 1 and 2, open only this spec and files under `todo-temp/error-analysis/outputs/bar_clause_pilot/codex_locate/inputs/`. Do not open, until Phase 3: any other file in `bar_clause_pilot/` (instances, section groups, citation audits, verdicts, loop07 files, summaries, `count_workload_output.txt`), `bar_attribution*`, `error_rows.csv`, `prediction_index.jsonl`, notes, reports, `LOG.md`, `PROGRESS.md`. They contain gold labels, outcome differences or earlier mappings.
4. **Write only** under `todo-temp/error-analysis/outputs/bar_clause_pilot/codex_locate/outputs/` and `todo-temp/error-analysis/scripts/codex_locate/`. Do not modify any existing file.
5. Never read `.env` or credential files. Never open heldout50 data (`reproduction/test_splits/ncbi_disease_heldout50.json` or its documents' gold).
6. Only one AI tool works in this repo at a time. Commit at the end of every session with a clear message and leave the tree clean.

## Inputs (`codex_locate/inputs/`, built by `scripts/bar_clause_pilot/prepare_locate_inputs.py`; hashes in `manifest.json`)

- `<prefix>_predictions.jsonl`, one line per prediction to locate. Prefixes: `top4_loop01, 02, 04, 05, 06, 07, 08, 09, 10`, `top1_loop05`, `top1_loop07`; 2,918 lines in total. Fields: `pred_id`, `guideline`, `doc`, `pred_start`, `pred_end`, `pred_text`, `pred_label`, `context` (about 250 characters each side, prediction marked `[[...]]`), `guideline_section` (the model's own free-text citation), `rationale` (the model's own explanation).
- `original_lookup_predictions.jsonl`, 496 lines: original-guideline predictions at positions where some changed guideline has no prediction. Same fields with `lookup_id` instead of `pred_id`, plus `n_original_runs_with_this_citation`.
- `guidelines/<prefix>.txt` and `guidelines/original.txt`: the guideline the predictions were made with, line endings normalised to LF. Line numbers in all outputs are 1-based lines of these files. `guidelines/<name>_numbered.txt` shows the same lines with a 4-digit number and a tab; the number is not part of the text.

## Phase 1: locate (per guideline, per prediction)

Order: `top4_loop07` first, then `top4_loop01, 02, 04, 05, 06, 08, 09, 10`, `top1_loop05`, `top1_loop07`. Read the whole guideline before starting it. Work in batches of 20 predictions in file order; after each batch append to `outputs/<prefix>_locate.jsonl` and update `outputs/progress.json`. On resume, skip `pred_id`s already in the output.

For each prediction write one JSON line:

```json
{"pred_id": "...", "status": "located",
 "quotes": [{"quote": "...", "line_start": 65, "line_end": 65, "condition_words": "is the complement of",
             "role": "basis", "cited_as": "Section 3 - Context and population frames"}],
 "note": ""}
```

- **quote**: the shortest contiguous span of the guideline, copied exactly, that states both the condition and the action (label, not annotated, span rule) the rationale relies on. It may cover consecutive lines; keep the text as in the file. If the rationale relies on a whole sentence or bullet, quote all of it.
- **condition_words**: when the quoted rule lists several conditions (joined by "or", commas or a list) and the rationale invokes one of them, copy the words that name that condition; they must be a substring of the quote. Example: rationale "The disease name is the complement of the context noun risk in 'risk of breast cancer'" with the line-65 sentence of top4_loop07 gives `"is the complement of"`. If the rationale does not say which condition, leave it empty.
- **role**:
  - `basis`: according to the rationale, the label or span follows from this text. Exceptions, precedence rules and examples the rationale relies on are `basis` too.
  - `ruled_out`: the rationale cites this text to say it does not apply here (for example "What NOT 8 not applicable", or a rule cited only to explain why it is not used).
  - `context`: cited or alluded to but not decisive, such as a definition named in passing.
- **cited_as**: the fragment of `guideline_section` that points to this text, or empty if the text was found only through the rationale. Split `guideline_section` at semicolons; every fragment must appear in some quote's `cited_as` or be explained in `note` (for example: the cited section does not exist in this guideline).
- Several quotes when the rationale relies on several places. If the citation names an item that does not exist but the rationale clearly relies on another existing text, quote that text and say so in `note`.
- **status** `cannot_locate`: neither the citation nor the rationale leads to supporting text in this guideline; `quotes` empty and `note` says why.
- **note**: at most 20 words; required for `cannot_locate` and anything unusual.
- You do not know the gold label. Do not try to infer it, and do not judge whether the annotation is right.

After each guideline, run a checker you write as `scripts/codex_locate/check_quotes.py`:
- every input `pred_id` appears exactly once;
- every quote occurs in lines `line_start` to `line_end` of the guideline file after removing `*` and `_` and collapsing whitespace on both sides;
- `condition_words` is a substring of its quote (same normalisation); `role` and `status` take only the values above.

Fix failures by re-reading the guideline, not by editing a quote until it passes.

## Phase 2: merge quotes into items (per guideline, still blind)

From the Phase 1 output, collect the distinct `basis` entries `(line_start, line_end, quote, condition_words)`. Write `outputs/<prefix>_items.csv` and `outputs/<prefix>_quote_to_item.csv`. Apply this rule as written; do not adjust it:

- Two entries are the same item when they state the same condition and the same action at the same place in the guideline (overlapping text or the same sentence or bullet), for example the same sentence quoted at different lengths.
- In a sentence with several conditions, entries with different `condition_words` are different branch items; entries with empty `condition_words` go to the parent item (the whole sentence or rule). Link branches to the parent with `parent_item`.
- The same rule written again elsewhere in the guideline stays a separate item. When the condition and action are clearly the same, list the other item ids in `restates`. Do not merge them.

`<prefix>_items.csv` columns: `item_id` (prefix plus a running number), `line_start`, `line_end`, `item_text` (verbatim full sentence or bullet), `condition_words`, `action` (short: label X / not annotated / span rule / other), `parent_item`, `restates`. `<prefix>_quote_to_item.csv` columns: `line_start`, `line_end`, `quote`, `condition_words`, `item_id`. Every distinct basis entry maps to exactly one item.

## Phase 3: aggregate (only after Phases 1 and 2 are complete for all 11 guidelines)

Now you may open `bar_clause_pilot/<prefix>_instances.csv`, `outputs/bar_attribution.json` and `bar_clause_pilot/count_workload_output.txt`. Write `scripts/codex_locate/aggregate.py`.

- An instance row in `<prefix>_instances.csv` has the per-instance difference `d` (this run labels the gold right, or makes the no-gold prediction: 1, else 0; minus the share of the 19 original runs that do the same) and a `category`: `gold_now_right` and `gold_now_wrong_with_prediction` (gold side), `nogold_new_prediction` (new false positive side), `gold_now_unlabelled` and `nogold_dropped_prediction` (no prediction in this run).
- Join instances that have a prediction to Phase 1 by `pred_id` = `<prefix>|doc|target_pred_start|target_pred_end|target_pred_label`, then through `basis` quotes to items.
- Per item: number of gold instances, sum of positive `d` and sum of negative `d` over gold instances (keep them separate), number and summed `d` of `nogold_new_prediction` instances, number of distinct documents, number of distinct strings (casefolded), members (`doc:start-end text d`). An instance whose prediction has basis in several items is listed under each, and once in `<prefix>_joint_groups.csv` keyed by its sorted item set.
- Separate buckets: located but no `basis` quote (only `ruled_out`, `context` or `cannot_locate`); and no prediction (summed `d` per category).
- A per-guideline totals table in which every instance is counted exactly once (by its item set or bucket).
- Checks, printed as pass/fail: per guideline, summed `d` over gold instances per label (SpecificDisease, DiseaseClass, Modifier) equals `bars` in `bar_attribution.json` within 0.05; instance counts with and without a prediction equal section A of `count_workload_output.txt`; every `pred_id` joins; every instance counted once in the totals table.
- Outputs: `outputs/<prefix>_item_summary.csv`, `outputs/<prefix>_joint_groups.csv`, `outputs/aggregate_output.txt` (per guideline: totals, the ten items with the largest summed absolute gold `d`, check results; sha256 of inputs and outputs).

## Part B: original-guideline lookup (after Phase 3; lower priority)

Apply the Phase 1 rules to `original_lookup_predictions.jsonl` against `guidelines/original.txt`, output `outputs/original_lookup_locate.jsonl` keyed by `lookup_id`, and run the same checker. No merging or aggregation for Part B.

## Sessions, stopping and reporting

- Each session: read this spec and `outputs/progress.json`, continue where it stopped. End of session: run the checker on finished guidelines, append to `outputs/session_log.md` (date; guidelines and batches done; check results; problems), commit as `Codex locate: <what was done>`.
- Stop and flag with evidence, without changing the design, if: a context does not contain the predicted text; a guideline file looks wrong; more than about 10% of a guideline's predictions are `cannot_locate`; the merge rule cannot be applied to some entries.
- Final entry in `session_log.md`: per guideline, predictions located and `cannot_locate`, quotes by role, items, Phase 3 check results, output hashes.
