# Error analysis of the 10/23 Haiku reproduction

All work in this folder is offline, with no API calls. The test documents' gold is never read.

## Folders

| Folder | Contents |
| --- | --- |
| `reports/` | The reports, each in English and Chinese (`_zh`). Figures used by the 10/24 report are in `reports/figures/`. |
| `scripts/` | Analysis scripts. Each one reads raw outputs or earlier results and writes to `outputs/`. |
| `outputs/` | Script outputs (`*_output.txt`, `*.json`, `*.csv`). Every number in the reports traces to a file here. |
| `notes/` | Working documents: the 10/24 analysis plan and rules, the coding tutorial, the draft replay plan of 10/25, the post-hoc analysis spec of 10/28 (`20261028_posthoc_analysis_spec.md`, paused; its numeric case filters withdrawn), and the classification draft with a 30-case pilot coding (`20261028_classification_pilot.md`; sampler `scripts/pilot_cases.py`, outputs `pilot_cases_output.txt`, `pilot_cases.json`, hand coding `pilot_coding.csv`; v2 recoding and new-case check: `scripts/pilot_recheck.py`, `pilot_recheck_text.txt`, `pilot_recheck_pred.txt`, `pilot_recheck_textcodes.csv`, `pilot_recheck_codes.csv`, `pilot_recoding_v2.csv`, `pilot_clause_eval_v2.csv`; v2.1 corrections 10/29), and the 10/29 analysis `20261029_modifier_context_analysis.md` (scripts `error_overview.py`, `modifier_subset.py`; outputs `error_overview_output.txt`, `error_overview.json`, `modifier_subset_output.txt`, `modifier_subset.json`, hand coding `modifier_b2_clause_coding_v1.csv` and `_v2.csv` via `scripts/modifier_b2_coding.py`; v2 of 10/29 adds `scripts/outside_subset.py` → `outside_subset_output.txt`, `outside_subset.json`, and `scripts/loop10_broken_coding.py` → `loop10_broken_coding.csv`). |

## Reports

| Report | What it answers |
| --- | --- |
| `reports/20261024_error_analysis_report.md` + `_appendix.md` | What errors Haiku makes, why 9 loops kept the original guideline, which rules lined up with gains and losses, and (added 10/26) why some top-4 loops improved and others fell (§3.5). Candidate improvements, untested, are in appendix D.5 to D.7. |

## Scripts, in the order to run them

Run from this folder with `PYTHONHASHSEED=0`, for example `python scripts/rule_links.py`. Each script's docstring states its inputs and method.

| Script | Main inputs | Writes to `outputs/` |
| --- | --- | --- |
| `error_table.py` | the 30 validation runs | `error_table_output.txt`, `error_rows.csv`, `error_items.csv` |
| `error_patterns.py` (uses `patterns_lib.py`) | `error_rows.csv` | `error_patterns_output.txt`, `error_patterns.json`, `error_items_patterns.csv` |
| `gold_precedent.py` | training gold, `error_items_patterns.csv` | `gold_precedent_output.txt`, `gold_precedent.json` |
| `rounds_table.py` | round snapshots | `rounds_table_output.txt`, `rounds.json` |
| `rule_links.py` | `error_rows.csv`, `rounds.json`, final guidelines | `rule_links_output.txt`, `rule_links.json` |
| `rule_chain.py` | `rule_links.json`, `error_patterns.json`, prompts | `rule_chain_output.txt`, `rule_chain.json` |
| `tp_exposure.py` | `rounds.json`, prompts | `tp_exposure_output.txt` |
| `example_caps.py` | round snapshots, saved batch usage | `example_caps_output.txt` |
| `test_power.py` | `error_patterns.json` | `test_power_output.txt` |
| `test_size_check.py` | validation runs | prints; saved as `test_size_check_output.txt` (`python scripts/test_size_check.py > outputs/test_size_check_output.txt`) |
| `history_tally.py` | round snapshots, analysis prompts | `history_tally_output.txt` |
| `topk4_stability.py` | `rule_links.json`, `rounds.json`, `history_tally_output.txt`, `error_table_output.txt`, final guidelines | `topk4_stability_output.txt`, `topk4_stability.json` |
| `keep_criteria.py` | round snapshots, `topk4_stability.json`, `history_tally_output.txt` | `keep_criteria_output.txt`, `keep_criteria.json` |
| `cited_sections.py` (10/29, after the review; run after `modifier_subset.py`) | saved annotation replies, `modifier_subset.json`, `modifier_b2_clause_coding_v5.csv`, `loop10_broken_coding.csv`, `rule_links.json`, final guidelines | `cited_sections_output.txt`, `cited_sections.csv` |
| `rationale_audit_extract.py` | saved validation calls, replies, guidelines, predictions and `error_rows.csv`; offline exact replay | `20261030_rationale_audit/`: provenance index, frozen sample, text-only documents and guidelines |
| `rationale_audit_summarize.py` | frozen sample, separately saved gold/status and `semantic_coding.json` | `20261030_rationale_audit/semantic_summary.json`, `cases_reviewed.md`; verifies evidence quotes and line numbers |
| `make_figures.py` | the JSON files above | `reports/figures/fig1` to `fig7` |
| `draw_test_split.py` | training documents | `reproduction/test_splits/ncbi_disease_heldout50.json`. Already drawn; do not re-run. |

On 10/26, after the files were moved here, every script except `draw_test_split.py` was re-run and reproduced its outputs byte for byte. The one exception is `tp_exposure_output.txt`, which lists six tied example strings in a different order; all its counts are identical, and the saved file is kept.
