# Overall view by entity type: grouped bars, similarity matrices, one guideline pair (2026-11-08)

Preliminary error analysis, exploration stage. Offline only: no API calls, no new annotation. Agreed with the user on
2026-11-08. The task produces descriptive tables and figures; it does not interpret them, rank causes, or add tests.

## Background (read only what you need)

- 11 refined guidelines, each annotated once on valid100: top-4 loop01, 02, 04, 05, 06, 07, 08, 09, 10; top-1 loop05, 07.
- Baseline: the 19 original-guideline runs (defined in `nodes/shared/error-analysis/scripts/loop_label_tables.py`).
- A bar = strict TP count of one refined guideline on one gold label minus the 19-run baseline mean. Labels used here:
  Modifier, SpecificDisease, DiseaseClass (CompositeMention is not part of this task).
- Existing artifacts (read, never modify):
  - `nodes/2026-11-06_seminar/error-analysis/outputs/bar_attribution.json` key `bars`: the 33 bars.
  - `nodes/shared/error-analysis/outputs/loop_label_tables.json` keys `by_label` (per guideline and label: `tp`, `tp_out`
    = outside the 19-run min..max, `fp`, `fp_out`, all as differences from the baseline mean), `start`, `loops`
    (`valid_f1` = overall strict F1).
  - Per-mention differences: `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/<prefix>_instances.csv`, columns
    `category, doc, start, end, text, gold_label, ..., n_orig_of_19, d`. Prefixes `top4_loop01` ... `top1_loop07`; for
    top-4 loop07 use `top4_loop07_instances.csv` (if it and `loop07_instances.csv` disagree on gold rows, stop and
    report). Gold rows are those with a non-empty `gold_label`; a gold mention absent from a file has d = 0.
  - Guideline texts: `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate/inputs/guidelines/top4_loop08.txt`,
    `top4_loop04.txt` and their `_numbered.txt` versions (line numbers are 1-based lines of the plain files).
  - Rule aggregates: `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate/aggregate/top4_loop08_items.csv`,
    `top4_loop04_items.csv` (rows with `level == item`; an instance relying on several items is counted under each,
    so rows overlap and must not be summed).

## Outputs (new files only)

Script `nodes/2026-11-13_seminar/error-analysis/scripts/overall_view.py` (stdlib plus matplotlib; run with `python -I`), writing to
`nodes/2026-11-13_seminar/error-analysis/outputs/overall_view/`:

1. `type_f1.csv`: one row per refined guideline and label: guideline, label, gold_n, tp, fp, fn, f1, overall_f1.
   Per-label strict F1 = 2TP / (2TP + FP + FN), with TP = gold mentions of this label strictly matched, FN = gold_n - TP,
   FP = predictions with this predicted label that are not strictly correct (the same "wrong prediction by predicted
   label" counting as section D of `loop_label_tables.py`; reuse its code paths, do not write a new matcher).
2. `grouped_bars.png`: three panels (Modifier, SpecificDisease, DiseaseClass), each 11 bars = the bar values from
   `bar_attribution.json`, sorted by that label's F1 (descending; ties by overall F1). Mark bars with `tp_out == true`
   with a star. Under each bar print the guideline name and that label's F1 (3 decimals). Zero line drawn.
3. `similarity_<label>.csv` (three files) and `similarity_matrices.png` (three heatmaps with the value in each cell,
   2 decimals): 11 x 11 cosine similarity. Vector of a guideline = d of every gold mention of that label (key
   doc, start, end, gold_label), gold rows only, TP side only, missing mentions = 0. Rows and columns sorted as in 2.
4. `overall_view_output.txt`: for each label, the 11 guidelines in the order of 2 with: label F1, bar (TP change),
   `tp_out`, FP change and `fp_out` from `loop_label_tables.json`, cosine with the guideline of highest label F1.
   Then the checks below with their results.
5. `pair_loop08_loop04_modifier.md`: Modifier clauses of top-4 loop08 and top-4 loop04 side by side.
   - A Modifier clause = one sentence or one list item (the unit of `notes/20261106_merge_spec.md`) that assigns,
     excludes or conditions the Modifier label, including worked examples that name Modifier.
   - Read both guidelines in full first. Align clauses by content, not by line. Each row: loop08 line(s) and verbatim
     text, loop04 line(s) and verbatim text, status (`same content`, `worded differently`, `only in loop08`,
     `only in loop04`).
   - For rows not `same content`: one sentence on what differs, and a direction judged from the text alone: under this
     wording, loop08 labels `more`, `fewer` or `unclear` mentions as Modifier than loop04, with the kind of mention
     affected (e.g. a disease name after "history of"). Do not open predictions, instances or items.csv while judging
     direction.
   - After all directions are written, attach to each row the existing `items.csv` row(s) whose `lines` cover the
     quoted line(s): item_id, lines, n, gold_gain, gold_loss, new_fp_n, copied as they are. No new counting, no sums.
   - End with the two Modifier bars (+50.74 and +26.74) and nothing else; no verdict.

## Checks (all must pass; print each in the output txt)

- The stored `d` column has 4 decimals (first run, 2026-11-08: every sum missed the bar by 0.00004 to 0.00013 for this
  reason). Use the exact value d = y - n_orig_of_19 / 19, with y = 1 for category `gold_now_right` and y = 0 for the
  other gold categories. Check that it rounds to the stored `d` at 4 decimals for every gold row, then use it everywhere
  (sums and cosine vectors).
- Per guideline and label, the sum of exact d over gold rows equals the bar in `bar_attribution.json` (|diff| < 1e-6).
- Per guideline and label, `tp` in `type_f1.csv` equals `start[label].tp_mean + by_label[guideline][label].tp`
  (|diff| < 1e-6), and fp equals the 19-run mean FP of that label plus `by_label[...].fp`.
- `overall_f1` equals `loops[...].valid_f1` for that guideline.
- Each similarity matrix is symmetric with ones on the diagonal.
- Every quoted clause in the pair file occurs verbatim at the stated line(s) of the plain guideline file (check by code).

If a check fails, stop, write what failed in the output txt, and do not produce the figures.

## Limits

- Do not modify any existing file, PROGRESS.md, LOG.md, reports or slides. Do not commit. Exception: the first run's
  own files (`scripts/overall_view.py`, everything in `outputs/overall_view/`) are replaced by this run; keep the clause
  directions it already wrote only if they were written before items.csv, predictions or instances were opened.
- No interpretation, conclusions, significance tests, extra pairs, FP-side matrices or noise baselines.
- Finish with a short final message: files written, check results, anything you could not do.
