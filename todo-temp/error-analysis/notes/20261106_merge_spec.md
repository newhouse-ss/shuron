# Merge step: group located guideline text into items (2026-11-06)

## Purpose

Locating (notes/20261106_codex_locate_spec.md) found, for each of 2,918 changed predictions, the guideline text its rationale relies on. This step groups the distinct `basis` quotes of one guideline into items, so that a later script can count gains and losses per item. The rules below were agreed with the user on 2026-11-06. Work blind: no gold labels, no outcome differences, no earlier groupings.

## Inputs

- `todo-temp/error-analysis/outputs/bar_clause_pilot/codex_locate/merge_inputs/<prefix>_basis_entries.jsonl`, one line per distinct basis entry: `entry_id`, `line_start`, `line_end`, `quote`, `condition_words`, `n_predictions` (predictions that used exactly this entry), `cited_as_examples` (up to 3). Built by `scripts/bar_clause_pilot/prepare_merge_inputs.py`.
- The guideline: `.../codex_locate/inputs/guidelines/<prefix>_numbered.txt` (4-digit line number and a tab, not part of the text) and the plain copy `<prefix>.txt`.

## Rules

1. **An item is one statement of the guideline that says under what condition what to do**: a sentence, or one item of a list. Quotes of the same statement at different lengths belong to the same item.
2. **Lead-in plus list items.** If a quote spans a lead-in and several list items, and its `condition_words` name one list item, the entry belongs to that list item; otherwise it belongs to the lead-in statement. A list item that is an item gets `parent_item` = the lead-in item (create the lead-in item if needed).
3. **Branches inside one statement.** When a statement joins several conditions with "or", commas or a short list, and the entry's `condition_words` name one of them, set `branch` to a short name for that condition (a few words taken from the statement). Different wordings that name the same condition get the same branch name. If `condition_words` is empty, names the whole statement, or names a list item that is its own item under rule 2, `branch` is "".
4. **The same rule written at another place stays a separate item.** Do not merge items across places.
5. **What the item governs.** For each item set `action_type` by reading its text: `label` (assigns a label; put the label in `label`), `not_annotated` (says not to annotate), `span` (decides span boundaries), `other` (a definition without an action, precedence between rules, a pointer to another section).
6. Create items only for statements that some entry uses, plus lead-in parents needed by rule 2.

## Outputs (write with the Write tool; nothing else)

- `.../codex_locate/merge_outputs/<prefix>_items.json`: a JSON list of items `{"item_id": "<prefix>_001", "line_start": int, "line_end": int, "item_text": "...", "action_type": "label" | "not_annotated" | "span" | "other", "label": "", "parent_item": ""}`. `item_text` is the statement copied exactly from the guideline lines `line_start` to `line_end` (it may be a whole line).
- `.../codex_locate/merge_outputs/<prefix>_entry_map.json`: a JSON list `{"entry_id": ..., "item_id": ..., "branch": "..."}`, one per input entry.

Run `python -I todo-temp/error-analysis/scripts/bar_clause_pilot/validate_merge.py <prefix>` and fix what it reports by re-reading the guideline. It checks: every entry mapped exactly once; item ids unique; parents exist; `item_text` verbatim in its lines (after removing `*` and `_` and collapsing whitespace); each entry's lines overlap its item's lines or the item is the entry's lead-in; `action_type` values; `label` set only for `label` items.

## Hard rules

- Decide by reading; do not write code that groups entries (no clustering, string similarity or regex grouping). The only script you run is the validator.
- Open only this spec, your guideline's two files, your `merge_inputs` file and your own outputs. Do not open locate outputs, instances files, `bar_attribution*`, `error_rows.csv`, `prediction_index.jsonl`, other notes, reports, `LOG.md` or `PROGRESS.md`.
- No git, no API or network calls, never read `.env` or credential files, never open heldout50 data.
