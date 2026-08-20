# reproduction/

Isolated reproduction work for *Refining and Reusing Annotation Guidelines for
LLM Annotation*. **Nothing in this folder modifies the upstream code.** It reads
`src/llm_guideline_moderation` through `lib/bootstrap.py` and reuses the
upstream evaluator so numbers stay consistent with the refinement loop's own
diagnostics.

## Status

| Gap in the released repo | Status |
| --- | --- |
| 1. Valid-set predictions are never scored locally | **done** - `eval_valid.py` |
| 2. Figure 3 confusion matrix has no producer | **done** - part of the same report |
| 3. Section 3.4.1 priority order differs from the paper | **done** - `lib/discrepancy.py` |
| 4. No prompt-only (S) / guideline (G) baseline switch | not started - needs provider decisions |
| 5. Reasoning vs non-reasoning knob not wired to spec/CLI | not started - needs API details |
| 6. Cost and time (Table 3) not recorded | not started |

## Local evaluation

No LLM calls, no API key, no cost.

```bash
python reproduction/eval_valid.py \
    --gold-dir data/datasets/ncbi_disease/valid \
    --pred-dir outputs/ncbi_valid_annotations \
    --entities data/schemas/ncbi_entities.schema.json \
    --label ncbi-gpt-r-g
```

Prints a Table 1-shaped summary and writes `results/<label>/` containing
`metrics.json`, `per_document.json`, `discrepancies.json`, `report.txt`.

`--entities` pins the confusion matrix axis to the full schema so labels the
model never predicted still appear as rows. `--require-complete` exits non-zero
if any document fails to align, for use in scripted sweeps. `--orient` switches
the confusion matrix layout between `pred-rows` (default) and `gold-rows`; see
the Figure 3 note below.

### Testing the plumbing without spending anything

`tools/make_mock_predictions.py` perturbs gold into a degraded prediction set,
so the whole annotate-then-evaluate path can be exercised offline:

```bash
python reproduction/tools/make_mock_predictions.py \
    --gold-dir data/datasets/ncbi_disease/valid \
    --out-dir reproduction/results/_mock_preds --seed 42
```

### Self-tests

```bash
python reproduction/tests/test_eval_valid.py     # 13 tests, offline
```

Includes end-to-end checks against the real shipped NCBI data: gold scored
against itself gives F1 = 1.0, empty predictions give all false negatives,
tampered text is reported rather than silently scored, and documents align by
`sourceid` rather than filename.

## Findings so far

### The shipped valid sets are the paper's evaluation sets

Gold entity counts against the `#Entity` column of Table 1:

| Dataset | Shipped | Paper | |
| --- | --- | --- | --- |
| NCBI Disease | 791 | 791 | exact |
| BC5CDR | 2,146 | 2,146 | exact |
| BioRED | 3,533 | 3,531 | **+2** |

Two of three match exactly, so absolute recall is directly comparable to the
paper. BioRED carries 2 extra gold entities (0.06%), too small to move a
two-decimal F1 but worth stating rather than glossing over.

### Two strict-match implementations, and they disagree on BC5CDR

The repo contains two: the upstream evaluator
(`evaluation.py:evaluate_pubannotation_pairs`, exclusive greedy matching, counts
each denotation) and the set-based one that actually drives the loop's stopping
rule (`iterative.py:_calculate_f1`, collapses duplicates). Both are reported
side by side, with a warning when they diverge.

They diverge whenever a document holds duplicate `(begin, end, obj)`
denotations. BC5CDR valid has 6 such duplicates across 4 documents
(`11337188`, `17702969`, `21418164`, `2322844`); NCBI and BioRED have none. On a
mock BC5CDR run this produced 1381 vs 1379 true positives.

**Report the `pubannotation` number.** BC5CDR's shipped total of 2,146 matches
the paper's `#Entity` only when duplicates are counted individually, so that is
the paper's counting convention.

### Section 3.4.1 priority order

The paper defines four mutually exclusive categories resolved in order: label
mismatch, boundary mismatch, false negative, false positive. Upstream
`_build_discrepancy_clusters` resolves the first two inside one document-order
greedy loop, so a gold entity overlapping both a differently-typed and a
same-typed prediction is classified by whichever it meets first.

`lib/discrepancy.py` applies the stated priority explicitly and pairs by largest
overlap first, making the result order-independent. Since the dominant
discrepancy group is the moderation target, this can change which pattern the
whole refinement loop aims at - a candidate explanation if refinement paths
diverge from the paper.

Entities that overlap a span already consumed by an earlier pairing fit none of
the four definitions literally. They are counted as `unpaired_overlap` and
reported rather than folded into FN/FP. It is 0 on all mock runs so far.

### Figure 3 orientation: read it as prediction rows, gold columns

Figure 3's header (`Gold↓Pred→`) and caption ("Rows correspond to the gold
labels and columns to the model predictions") say gold indexes rows. The numbers
say otherwise. Section 5.4 makes two label-specific claims about the NCBI run,
and both land correctly only under **prediction rows, gold columns**:

1. The iteration-0 dominant pattern is "Predicted: DiseaseClass, Gold: No
   Entity", frequency 7 - Figure 3a's `D` row, `O` column.
2. "Five label mismatch cases ... incorrectly labeled as SpecificDisease instead
   of the gold label Modifier" - Figure 3a's `S` row, `M` column holds 5, and it
   falls to 0 in Figure 3b ("entirely resolved in Iteration 1"). The transposed
   cell `M`/`S` holds 0 in Figure 3a, so gold-rows cannot produce this claim.

Two independent quantitative checks beat one caption sentence, so `pred-rows` is
the default. `test_reproduces_the_section_5_4_modifier_claim` locks claim 2 in.

**Residual inconsistency, still open.** Figure 2 is the moderation example for
that same dominant pattern, and it is written entirely as a false negative
story: DiseaseClass mentions are "suppressed" and "dropped", the inserted rule
says to *annotate* each conjunct, and the caption states the goal is "to reduce
DiseaseClass false negatives". Under `pred-rows` the dominant pattern is 7 false
*positives*, and DiseaseClass false negatives sit at `O` row / `D` column = 1,
far too small to be dominant. So Figure 2 and Section 5.4 disagree about the
direction regardless of how the matrix is oriented.

This cannot be settled from the paper. An actual NCBI run will show whether the
dominant cluster comes out as FN or FP; until then keep both layouts available.
Orientation is presentation only - `Discrepancy` always stores `gold_label` and
`pred_label` explicitly, and `--orient gold-rows` produces the exact transpose,
never different counts.

### Azure deployment probe results

`python reproduction/probe_azure.py` against the four configured deployments,
api-version `2025-04-01-preview`. All four are live.

| Deployment | token param | reasoning param | effort effect (reasoning_tokens low→high) | JSON mode |
| --- | --- | --- | --- | --- |
| `southcentralus-gpt-4o` | `max_completion_tokens` or `max_tokens` | **rejected (400)** | n/a - non-reasoning | OK |
| `eastus2-gpt-5.1` | **`max_completion_tokens` only** | `reasoning_effort` (flat) | 25 → 63 | OK |
| `eastus2-gpt-5.2` | **`max_completion_tokens` only** | `reasoning_effort` (flat) | 16 → 19 | OK |
| `eastus2-gpt-5.4` | **`max_completion_tokens` only** | `reasoning_effort` (flat) | 24 → 49 | OK |

Two findings that would break the upstream provider on these deployments:

* **`max_tokens` is rejected by every GPT-5.x deployment** - `400 Unsupported
  parameter: 'max_tokens' is not supported with this model. Use
  'max_completion_tokens' instead.` Upstream `providers/openai.py:35` sends
  exactly `max_tokens`.
* **Nested `reasoning: {"effort": ...}` is rejected** - `400 Unknown parameter:
  'reasoning'.` The accepted spelling is the flat `reasoning_effort: "high"`.
  Upstream `providers/openai.py:41-42` sends exactly the nested form. It never
  fires in practice only because `_build_provider()` never sets the field, so
  the bug is latent rather than active - enabling reasoning effort through
  upstream as written would 400 on every call.

`lib/azure_provider.py` defaults to `max_completion_tokens` + flat, which the
probe confirms is the working combination.

Effort genuinely changes compute on all three reasoning models, so H2 can be run
as a within-model low/high comparison. Note `5.2`'s spread is narrow (16 → 19 on
a trivial probe prompt); re-check it on a real annotation prompt before relying
on it. `4o` rejects both spellings, which makes it a clean non-reasoning arm -
though 4o vs 5.x is a cross-generation comparison, confounded by general
capability, unlike the paper's within-model design.

## Still needs answers before the LLM runs

- **GPT-5.4**: name of the reasoning-effort parameter, and whether a low enough
  setting exists to serve as the non-reasoning arm of H2.
- **DeepSeek V4**: still two model names (chat / reasoner), or one model with a
  toggle?
- **Kimi K3**: OpenAI-compatible `/chat/completions`? base URL? thinking toggle?

Only H2 (Table 2) depends on these. H1 and H3 do not.

Related: upstream `providers/openai.py:41-42` sends
`payload["reasoning"] = {"effort": ...}`, a Responses API field, to
`/chat/completions`. If the endpoint ignores unknown fields, the paper's `low`
and `high` GPT arms sent identical requests. Verify before trusting Table 2's
GPT row.

## Layout

```
reproduction/
  eval_valid.py                  CLI - strict-match scoring of a prediction directory
  lib/bootstrap.py               puts src/ on sys.path, read-only
  lib/discrepancy.py             Section 3.4.1 categories + Figure 3 matrix
  lib/scoring.py                 gold/pred alignment + both strict implementations
  lib/report.py                  console rendering
  tools/make_mock_predictions.py offline plumbing test aid
  tests/test_eval_valid.py       11 offline self-tests
  results/                       run outputs (gitignored)
```
