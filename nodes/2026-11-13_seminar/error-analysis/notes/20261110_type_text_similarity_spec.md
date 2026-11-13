# Per-type text similarity of guideline clauses (2026-11-10)

Preliminary error analysis, exploration stage. Agreed with the user on 2026-11-10. Offline: no API calls, no subagents;
Codex does the reading itself. The task produces descriptive tables and figures; it does not interpret them.

## Purpose

The annotation similarity matrices (`nodes/2026-11-13_seminar/error-analysis/outputs/overall_view/similarity_<label>.csv`) show whether
two refined guidelines changed the same gold mentions. This task adds the matching text similarity: per entity type, how
similar the guideline clauses that affect that type are. Whole-guideline similarity is not used, because it mixes the
changes of all types.

## Inputs

- 12 guideline texts in `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate/inputs/guidelines/`: `<name>.txt`
  (plain; line numbers are 1-based lines of this file) and `<name>_numbered.txt`. Names: `original`, `top4_loop01`,
  `top4_loop02`, `top4_loop04`, `top4_loop05`, `top4_loop06`, `top4_loop07`, `top4_loop08`, `top4_loop09`, `top4_loop10`,
  `top1_loop05`, `top1_loop07`.
- Original type definitions: lines 5 to 37 of `original.txt` (section 1: Specific Disease and Disease Class; section 2:
  Composite Mention; section 3: Modifier).
- For ordering and the side-by-side table only: `nodes/2026-11-13_seminar/error-analysis/outputs/overall_view/type_f1.csv` and
  `similarity_<label>.csv`.
- For the check in step 3 only: `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/<prefix>_instances.csv` and
  `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate/outputs/<prefix>_locate.jsonl` plus
  `<prefix>_locate_haiku.jsonl` where present. Join them as `nodes/2026-11-06_seminar/error-analysis/scripts/bar_clause_pilot/aggregate_items.py`
  does (pred_id = `<prefix>|doc|target_pred_start|target_pred_end|target_pred_label`; quotes with role `basis` only).

## Step 1: judge which types each unit affects (reading only)

Do this before opening any file listed for step 3, any file in `outputs/overall_view/`, any `items.csv`, or the pair
file. Judge from the guideline text and the original definitions alone.

- Unit: one sentence or one list item (the unit of `nodes/2026-11-06_seminar/error-analysis/notes/20261106_merge_spec.md`). Headings,
  separators and example passages are units too. Every non-empty line is split into units; a unit does not cross a
  list-item boundary.
- For each unit, ask: following this unit, does it change, or can it change, which mentions get which of the four labels
  (Modifier, SpecificDisease, DiseaseClass, CompositeMention)? Implicit effects count: a unit does not need to name a
  type. Give exactly one judgement:
  - `types`: it affects one or more particular types more than the others. List all of them (e.g., a rule that sends a
    disease name before a noun to Modifier instead of SpecificDisease lists both).
  - `general`: it affects all types in the same way (e.g., what counts as a disease mention at all, span rules that hold
    for every type, duplicate mentions).
  - `none`: it does not affect labels (headings, formatting, output instructions, purely descriptive text).
- One short reason for every `types` and `general` unit.
- Output: `nodes/2026-11-13_seminar/error-analysis/outputs/type_text/units_<name>.csv`, columns `name, unit_id, line_start, line_end,
  text, judgement, types, reason`. `text` is verbatim; `types` is semicolon-separated and empty unless judgement is
  `types`.

## Step 2: text similarity

Script `todo-temp/error-analysis/scripts/type_text_similarity.py` (stdlib plus matplotlib; run with `python -I`), writing to
`nodes/2026-11-13_seminar/error-analysis/outputs/type_text/`.

- For each of Modifier, SpecificDisease, DiseaseClass: the text of a guideline = its units whose `types` include that
  type, joined in file order. `general` and `none` units are left out. CompositeMention gets no matrix.
- TF-IDF cosine over the 12 texts of that type. Tokens: lowercase `[a-z0-9]+`; remove a fixed English stop-word list
  written out in the script (the NLTK english list). tf = raw count; idf = ln((1 + 12) / (1 + df)) + 1; L2-normalise each
  vector; cosine. sklearn is not installed: implement the formula.
- Rows and columns in the order of the annotation matrices (that type's F1 descending, ties as in
  `scripts/overall_view.py`), with `original` last.
- Outputs:
  1. `text_similarity_<label>.csv` (12 x 12, three files).
  2. `text_similarity_matrices.png`: three heatmaps, value in each cell (2 decimals), same layout as
     `outputs/overall_view/similarity_matrices.png`.
  3. `type_text_output.txt`: per type, (a) per guideline the number of units listing that type, the number of `general`
     and `none` units, and the word count of that type's text; (b) the row of the guideline with the highest label F1:
     for every other refined guideline, label F1, annotation cosine (from `similarity_<label>.csv`), text cosine, and
     that guideline's text cosine with `original`. Then the step 3 results and the checks.

## Step 3: check for missed judgements (after all step 1 files are written)

- For each refined guideline and each type T of the three: take every instance in `<prefix>_instances.csv` with a
  prediction (`target_pred_label` non-empty) whose `gold_label` or `target_pred_label` is T, and its quotes with role
  `basis`. Locate each quote by exact search within its stated lines of the plain file and map it to the units whose
  character span overlaps it.
- A miss: a basis quote cited by a T instance whose overlapping units all lack T in `types`.
- Report per guideline and type: the number of distinct quotes cited by T instances, the number of misses, and for each
  miss the quote's lines, the unit text and its judgement (`general`, `none`, or the other types it lists).
- Do not change any judgement after this step.

## Checks (print each in the output txt; if one fails, stop and do not produce the figures)

- Every unit text occurs verbatim at its stated lines of the plain file.
- Coverage: the units of each file, in order and with whitespace removed, reproduce the file's text with whitespace
  removed.
- Every unit has one valid judgement; `types` is non-empty exactly when the judgement is `types`.
- Each matrix is symmetric with ones on the diagonal. If a type text is empty, report it and leave its row empty.
- Every basis quote used in step 3 is found within its stated lines; list any that are not.

## Limits

- Do not modify any existing file, PROGRESS.md, LOG.md, reports or slides. Do not commit.
- No interpretation, conclusions, significance tests, embeddings or other similarity measures.
- If the Codex quota runs out: stop, keep the finished `units_<name>.csv` files, and report which are missing.
- Finish with a short final message: files written, check results, miss counts, anything you could not do.
