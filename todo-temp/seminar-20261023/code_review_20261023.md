# Code review before the reproduction (2026-10-23)

Scope: everything the reproduction runs. That is the batch runner (`reproduction/haiku_batch_loops.py`), the loop (`src/llm_guideline_moderation/iterative.py`), top-4 (`reproduction/moderate_topk.py`), the Claude provider (`providers/claude.py`, `_shared.py`), annotation and span alignment (`pipeline.py`, `text_utils.py`) and the validation scorer (`reproduction/lib/scoring.py`). Offline only; no API calls.

## Conclusion

The parts that produce the numbers are sound. The loop follows the published rule; the scorer agrees with a separate minimal scorer to four decimals; no predicted mention is lost in span alignment; loops never share a reply. Two changes are required before the run (start at loop 02, a mode for the original-guideline runs). Two more are cheap insurance against the run getting stuck. Nothing found changes the pilot's results.

**Status (10/23, later):** the user approved all four changes below. They are in `reproduction/haiku_batch_loops.py` (`--first-loop`, `--e1`, batch splitting, `--max-attempts`). Each has an offline check in `reproduction/tests/test_haiku_batch_loops.py`, and all 12 checks pass.

## Required before the run

1. **No way to skip finished loops.** `--top1 10` runs loops 01 to 10. top-1 loop 01 ran on 10/22 before the hash seed was fixed, so its analysis prompts would be rebuilt differently, new calls would be paid, and its folder would be overwritten (`prepare_run_layout` does not clear or protect it). Fix: a start index (loops 02 to 10).
2. **No mode for the 10 original-guideline validation runs (E1).** Fix: reuse the loop's own validation step (same call, `instructions=""`, same output settings) with a separate run name per repeat, so the 10 runs never share a reply.

## Recommended (cheap insurance)

3. **Batches are not split by size.** The Batch API takes at most 100,000 requests or 256 MB per batch (Claude API reference, read 10/23). The pilot's largest request was 116,526 prompt characters. If all 9 new top-4 loops reach validation in the same step, that batch is about 105 MB with guidelines of the pilot's size, so it fits. Guidelines about 2.4 times longer would not, and a restart would form the same batch again and fail again. Fix: send pending requests in several batches above a size threshold.
4. **A call with three unusable replies blocks its loop for good.** On a resume the same three saved replies are replayed and fail again. In the pilot this happened only to the top-4 rewrite at the old 64,000 cap, which `--stop-at-cap` now handles. For annotation (structured output) only a refusal or a cut-off could cause it. Fix: an option that allows more tries on a resume, so no loop is lost.

## Known limits, no change needed

5. If a batch call still fails after the SDK's own 4 retries, every loop stops. A restart resumes from the saved replies and collects any batch already sent, so nothing is paid twice.
6. The spending cap is checked before each batch, so one batch can go past it. It is a stop, not an exact limit.
7. If `batches.create` reaches the server but its answer is lost, the batch is not recorded, and a restart sends it again (that batch is paid twice). Very rare.

## Checked and correct

- **Loop rule** (`iterative.py` lines 548 to 596): a round is kept only if development F1 is strictly higher. The loop stops at the first round that is not kept, at F1 0.9, or after 20 rounds.
- **Requests** (`providers/claude.py`):
  - `claude-haiku-5-5`, adaptive thinking, effort xhigh, max_tokens 128,000;
  - annotation constrained by a JSON schema;
  - a cut-off or a refusal raises instead of entering the run.
  - The price table in `run_haiku.py` matches the current reference ($0.10 / $0.50 per million tokens, $0.50 / $2.50 above 100K-token prompts, Batch at half price).
- **Offline tests pass:**
  - `reproduction/tests/test_haiku_batch_loops.py`: lockstep batches; separate replies per loop; retries; a rerun sends nothing; a crash is recovered; a cap of 0 sends nothing; `--stop-at-cap`.
  - `reproduction/tests/test_eval_valid.py`: 13 of 13 pass.
- **Scorer:** a separate minimal scorer reproduces the pilot exactly.
  - top-1 loop 01: 791 gold, TP 503, FP 146, FN 288, F1 0.6986;
  - top-4 loop 01: TP 554, FP 150, FN 237, F1 0.7411.
- **Span alignment** (`review_drop_check_output.txt`): replaying the pilot's 200 validation replies reproduces the saved predictions. 0 of 649 and 0 of 704 returned mentions were dropped.
- **Labels:** no predicted label outside the four subtypes in either pilot validation run.
- **Same conditions on both sets:** development and validation annotation use the same call and settings.
- **Thread capacity:** this machine starts 2,800 waiting threads in 0.3 s (18 loops × 100 validation documents plus 1,000 E1 requests).

## Not checked

- The model's side: whether Anthropic changes the deployed model during the run. Both methods run at the same time, so a change would hit both.
- The runner's cost accounting against the Anthropic console. The pilot's JPY 284.89 (USD 1.80) can be compared with the console's usage for 10/22.
- The code for the four changes above, which is not written yet.

## Verification record

- **Tests:** `python reproduction/tests/test_haiku_batch_loops.py` printed "all offline checks passed". The 13 functions of `test_eval_valid.py` were run directly, because pytest is not installed: 13 passed.
- **Span-alignment check:** `todo-temp/seminar-20261023/review_drop_check.py`, output `review_drop_check_output.txt`.
- **Batch limits:** the Claude API reference bundled with Claude Code, `python/claude-api/batches.md`.
- **Files reviewed:**
  - `reproduction/haiku_batch_loops.py` (1934cd39e62a)
  - `reproduction/moderate_topk.py` (03800d68dcaf)
  - `src/llm_guideline_moderation/iterative.py`, `pipeline.py` (uncommitted label fix), `text_utils.py`
  - `providers/claude.py`, `providers/_shared.py`
