# Implementation task: two-step annotation pilot (code and offline checks only, no paid run)

2026-11-13. Design (read first, it is the source of truth): `nodes/2026-11-16_seminar/two-step-pilot/notes/20261113_two_step_pilot_design.md`. Background: `20261113_thesis_claim_research.md` in the same folder.

## Purpose

The pilot asks whether, with the original guideline unchanged, splitting annotation into a find call and a typing call leaves fewer true misses (gold mentions that no prediction overlaps) than single-call annotation, and whether any reduction comes from the two-call structure rather than from an "include uncertain spans" instruction. This task writes the code and passes the offline checks. It does not run the pilot.

## Hard rules

1. **No paid calls.** Do not submit any batch and make no API or network calls. The paid run (about 1,600 calls, about JPY 1,010) needs the user's approval, and the administrator is notified first.
2. **Do not change existing behaviour.** New code goes in `nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/` (tests in `.../scripts/pilot/tests/`). Import from `src/llm_guideline_moderation/` and `reproduction/haiku_batch_loops.py`; do not edit them. If a change there is unavoidable, it must leave every existing prompt and output byte-identical, and `reproduction/tests/` must still pass.
3. **Fixed texts.** Copy the three instruction texts verbatim from the design's appendix. Do not reword or tune them.
4. **Data.** Never read `.env` or credential files. Use `reproduction/test_splits/ncbi_disease_heldout50.json` only to exclude its document IDs; never open those documents. Do not use valid100 except in offline check 3.
5. **Write only** under `nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/` and `nodes/2026-11-16_seminar/two-step-pilot/outputs/`. Only one AI tool works in this repo at a time; commit your files at the end.

## Fixed settings

- Guideline `data/guidelines/ncbi_disease_guidelines.txt` (keep the runner's SHA-256 prefix check); entity schema `data/schemas/ncbi_entities.schema.json`.
- Model and API exactly as `reproduction/haiku_batch_loops.py`: reuse its `make_template()`, `BatchQueue` and `QueueProvider` (claude-haiku-5-5, effort xhigh, adaptive thinking, structured outputs, max_tokens 128000, Message Batches, resume, at most 3 attempts). No spending cap.
- Every arm, run and step uses its own provider name, so identical prompts in different runs never share a reply.

## Documents

- Pool: `data/datasets/ncbi_disease/train/*.json` minus dev50 (`reproduction/dev_splits/ncbi_disease_dev50.json`), the heldout50 documents and heldout50's `excluded_biored`, exactly as `nodes/2026-11-06_seminar/error-analysis/scripts/ablation_stage0.py` lines 175-178. Assert 487 documents.
- Order: `random.Random(20261113).sample(sorted(pool_names), len(pool_names))`. Positions 1-100 are reserved for the main experiment and never annotated; positions 101-300 are the pilot documents.
- Before any call, write a manifest with both lists and the SHA-256 of the sorted pool name list.

## Arms (each pilot document, 2 runs per arm)

- **S:** the existing `annotate_with_guidelines` call exactly as the reproduction's validation step (`instructions=""`, `OutputConfiguration(include_rationale=True, include_guideline_section=True)`). Track 1 and Track 2 are its aligned annotations.
- **S+:** same template; `instructions` = the S+ text; output fields are S's fields plus `"excluded"` as a string, "yes" or "no" (the structured-output schema builder in `src/llm_guideline_moderation/providers/_shared.py` supports only integer and string). Track 2 = all aligned annotations; Track 1 = those with `excluded` = "no".
- **T, step 1:** same template; `instructions` = the step-1 text; output fields start, end, text, rationale, guideline_section (no entity). `Annotation` requires an entity, so parse in the new code; do not change the class. Align spans the same way as S.
- **T, step 2:** a new prompt with the same system instruction, entity schema, guideline and text blocks as `annotate_with_guidelines`; the step-2 text as the high-level instructions; a candidate block listing `id`, `start`, `end`, `text` for each aligned step-1 candidate (ids 1..k in order of start offset). Output `{"decisions": [{"id": integer, "entity": string, "rationale": string, "guideline_section": string}]}`, where `entity` is a schema label or "NONE". Spans are not changed. A document with no candidates gets no step-2 call.
- **T outputs:** Track 2 = all step-1 candidates, labelled with the step-2 type when one was given and "Candidate" otherwise (the label is only for the file format; true misses ignore labels). Track 1 = candidates given a schema label. A candidate with no decision is left out of Track 1 and counted. For a repeated id keep the first decision; ignore unknown ids.
- Save, per arm and run: raw replies, Track 1 and Track 2 predictions in PubAnnotation format (`annotations_to_pubannotation`), the step-2 undecided count, and usage. The paid run will write to `outputs/ncbi_disease/<run date>_haiku-xhigh_pilot_twostep/`.

## Scoring script (implement now, run only after the paid run)

- True misses per document: `classify_document` in `reproduction/lib/discrepancy.py`, kind `false_negative`, gold from the pilot documents' training files.
- Primary comparison (design section 5): per document, the mean over its 2 runs of Track 2 true misses in each arm; differences T minus S and T minus S+, summed over the 200 documents; two-sided 95% interval by resampling documents (10,000 resamples, fixed seed). Pass only if both intervals lie entirely below 0. Print which of the three outcomes in design section 5 applies.
- Report only, no thresholds: per arm, Track 2 predictions that overlap no gold; Track 1 strict F1 (mean of the 2 runs, `score_directory` in `reproduction/lib/scoring.py` on exactly the pilot documents); true misses by gold label; T's undecided candidates; per-call cost from usage.
- If more than 5% of calls are still unusable after retries, print "inconclusive" and list them.

## Offline checks (all must pass before the paid run; write the results to `nodes/2026-11-16_seminar/two-step-pilot/outputs/pilot_offline_checks_output.txt`)

1. For one pilot document, the S prompt equals what the reproduction's validation step builds for that text (same template, same guideline hash). Print a diff of the S+ and T step-1 prompts: only the last sentence of the instructions and the output field list may differ.
2. With a fake provider and hand-written replies, run all three arms on 2 pilot documents; Track 1, Track 2 and the undecided count match hand-computed expectations, including one missing and one repeated step-2 id.
3. The true-miss counter applied to `outputs/ncbi_disease/20261022_haiku-xhigh_e1_run01/valid_predictions` against `data/datasets/ncbi_disease/valid` gives 140.
4. The 200 pilot and 100 reserved documents are disjoint, all inside the 487 pool, none in dev50, heldout50 or the excluded BioRED IDs.
5. A dry run prints the number of calls (at most 1,600) and the cost at JPY 0.634 per call.
6. `reproduction/tests/` still pass.

## Return

- Files created and the purpose of each.
- The result line of each offline check.
- The exact command for the paid run, not executed.
- Anything in the design that could not be implemented as written, with the reason.
