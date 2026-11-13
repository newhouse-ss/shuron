# Locating task: the guideline text behind each prediction (2026-11-06, locating only)

## Purpose

This is preliminary error analysis on valid100. Each bar on slide 5 is split into per-instance differences against the 19 original-guideline runs. This task only finds, for every changed prediction, the guideline text the model relied on. Merging located text into items and aggregating gains and losses are separate later steps; their rules are decided only after locating is complete for all guidelines and checked, without looking at outcomes. Do not merge, aggregate, judge whether annotations are correct, or draw conclusions.

This replaces script-based parsing of citations, which resolved 72 of 342 inferred references to the wrong line in top-4 loop04, 05 and 06 (mostly by stopping at a rule heading when the citation named an exception or sub-item under it).

## Executors

- Codex (gpt-6.1-sol, effort ultra): top4_loop07 rows 1 to 279 and top4_loop01 rows 1 to 20, in `outputs/<prefix>_locate.jsonl`. Before this revision Codex also merged top4_loop07 into items (`top4_loop07_items.csv`, `_quote_to_item.csv`, `_merge_decisions.json`, `_distinct_basis.json`, `_phase2_checks.json`); those files are a trial, out of order, and are not used.
- Claude API, `claude-haiku-5-5`, effort max, Message Batches: top4_loop01 rows 21 to 272, in `outputs/top4_loop01_locate_haiku.jsonl` (`scripts/bar_clause_pilot/haiku_locate.py`, $2.12). Seven of its records quoted non-contiguous text; they were moved to `top4_loop01_locate_haiku_rejected.jsonl` and located again by a Claude Opus 5.5 subagent (in `top4_loop01_locate.jsonl`).
- Codex, effort high: top4_loop02, top4_loop04, top4_loop05, and top4_loop06 rows 1 to 280; the Codex usage limit ended the run there.
- Claude Opus 5.5 subagents, effort high: top4_loop06 rows 281 to 305, top4_loop08, top4_loop09, top4_loop10, top1_loop05, top1_loop07, and the seven top4_loop01 records above. They wrote batches to `outputs/agent_batches/` and appended them only through `scripts/bar_clause_pilot/append_locate_batch.py`, which rejects a batch unless every quote is verbatim; `check_locate.py` checks a finished guideline. Two of them also used a read-only display script of their own in the session scratchpad (printing rows only).
- Result (2026-11-06): all 2,918 predictions located, none `cannot_locate`; all 11 guidelines pass `check_locate.py` (`outputs/locate_final_check_output.txt`).
- The original-guideline lookup was started without the user's approval and stopped after 25 of 496 records (`outputs/original_lookup_locate.jsonl`); whether it is needed depends on a later decision.

## Hard rules

1. **Locate by reading, never by code.** Every locating decision comes from reading the prediction's citation, rationale and context against the guideline. Do not map citations or rationales to lines with regex, keyword, string-similarity or embedding matching. Code may only read inputs, write outputs, track progress and check that quotes occur verbatim.
2. **Stay blind.** Use only this spec and files under `nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate/inputs/`. Do not open other files in `bar_clause_pilot/`, `bar_attribution*`, `error_rows.csv`, `prediction_index.jsonl`, notes, reports, `LOG.md` or `PROGRESS.md`; they contain gold labels, outcome differences or earlier mappings.
3. **Write only** under `codex_locate/outputs/` and the executor's own script folder. Do not modify any existing file.
4. Never read `.env` or credential files. Never open heldout50 data.
5. A Codex executor makes no API or network calls of its own. Only one AI tool works in this repo at a time; commit at the end of a session if the sandbox allows it.

## Inputs (`codex_locate/inputs/`, built by `scripts/bar_clause_pilot/prepare_locate_inputs.py`; hashes in `manifest.json`)

- `<prefix>_predictions.jsonl`, one line per prediction to locate. Prefixes: `top4_loop01, 02, 04, 05, 06, 07, 08, 09, 10`, `top1_loop05`, `top1_loop07`; 2,918 lines in total. Fields: `pred_id`, `guideline`, `doc`, `pred_start`, `pred_end`, `pred_text`, `pred_label`, `context` (about 250 characters each side, prediction marked `[[...]]`), `guideline_section` (the model's own free-text citation), `rationale` (the model's own explanation).
- `original_lookup_predictions.jsonl`, 496 lines: original-guideline predictions at positions where some changed guideline has no prediction. Same fields with `lookup_id` instead of `pred_id`, plus `n_original_runs_with_this_citation`.
- `guidelines/<prefix>.txt` and `guidelines/original.txt`: the guideline the predictions were made with, line endings normalised to LF. Line numbers in all outputs are 1-based lines of these files. `guidelines/<name>_numbered.txt` shows the same lines with a 4-digit number and a tab; the number is not part of the text.

## Locating rules (per prediction)

Order: `top4_loop07`, `top4_loop01, 02, 04, 05, 06, 08, 09, 10`, `top1_loop05`, `top1_loop07`, then the original lookup. Read the whole guideline before starting it. Write one JSON line per prediction:

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
- The gold label is unknown. Do not try to infer it, and do not judge whether the annotation is right.

## Checks (after each guideline)

- every input `pred_id` appears exactly once;
- every quote occurs in lines `line_start` to `line_end` of the guideline file after removing `*` and `_` and collapsing whitespace on both sides;
- `condition_words` is a substring of its quote (same normalisation); `role` and `status` take only the values above.

Fix failures by re-reading the guideline, not by editing a quote until it passes.

## Stopping and reporting

Stop and flag with evidence, without changing the design, if: a context does not contain the predicted text; a guideline file looks wrong; more than about 10% of a guideline's predictions are `cannot_locate`. Record per guideline: predictions located and `cannot_locate`, quotes by role, check results, output hashes (Codex in `outputs/session_log.md`; API runs in the run's own output summary).
