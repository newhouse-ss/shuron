# Reproduction Report — GPT-5.4 on NCBI Disease

Reproducing *Refining and Reusing Annotation Guidelines for LLM Annotation*
(one of nine model × dataset configurations).

---

## 1. Scope

The original study runs moderation over **3 model families × 3 datasets = 9
configurations**. This report covers **one** of them: GPT-5.4 on NCBI Disease.

| Hypothesis | Status in this run |
| --- | --- |
| **H1** — adding guidelines improves LLM annotation | **Confirmed**, more strongly than the original |
| **H3** — moderation improves the guidelines | **Not disconfirmed** (direction matches, magnitude weaker) |
| **H2** — reasoning models outperform non-reasoning ones | **Explicitly out of scope**; requires a `low` vs `high` comparison, left for future work |

---

## 2. Differences that cannot be eliminated

| | Original | This run |
| --- | --- | --- |
| Model | `gpt-5-2025-08-07` | **GPT-5.4** |
| API surface | Standard OpenAI endpoint | **Azure OpenAI** |

**Absolute scores are therefore not comparable.** Only differences measured
*within* a single model — G−S and M−G — carry meaning across the two studies.
Every claim below is stated as a difference for that reason.

---

## 3. Changes required to run the released code

Five changes were made. **Four of them affect only whether a request reaches
the service; none changes what the model sees or returns.** The released
provider targets the standard OpenAI endpoint, so it was adapted for Azure:
URL and authentication form, two parameter names that every GPT-5.x deployment
rejects, asynchronous submission plus polling for long reasoning requests, and
retries for dropped connections and stalled jobs. These are transport-level and
do not influence any result; details are in the appendix.

### One change does affect results: the annotation alignment step

**What it does.** Before returning annotations, the pipeline re-locates each
mention string in the source text, because an LLM commonly reports the right
text with the wrong character offsets. The original implementation searched the
window `[start − 50, start + 50 + length]` and took the **leftmost** match.

**Why that is wrong.** The window opens 50 characters *before* the target, and
"leftmost" is biased toward earlier positions. Whenever the same string also
occurs earlier inside that window, the annotation is pulled back onto that
earlier occurrence, then discarded for colliding with the annotation that
legitimately sits there. Short abbreviations recur constantly in biomedical
abstracts, so this fires often: `CRF [871,874] → [851,854]`,
`DM [301,303] → [259,261]`.

**How large the effect is.** Feeding the gold annotations back through the
function — equivalent to a model that predicts perfectly — still lost or moved
roughly **4% of gold annotations in all three datasets**. The "survived but
moved" cases are the more damaging kind: at evaluation they count as one false
positive *and* one false negative, so a single error is charged twice.

**The fix.** Drop the window. Enumerate every occurrence in the document and
take the one nearest the supplied offset. A correct offset then wins at
distance 0, and a wrong one still snaps to the closest real occurrence. This
rule already existed in the same function as a fallback for when the window
search failed; it is now the only rule. No new logic was introduced — the
faulty branch that pre-empted it was removed.

**Result.** Recoverable gold annotations:

| Dataset | Offsets exact | Offsets perturbed (simulating LLM error) |
| --- | --- | --- |
| NCBI Disease | 96.3% → **100%** | 96.1% → **99.9%** |
| BC5CDR | 95.8% → **98.9%** | 95.6% → **98.7%** |
| BioRED | 96.2% → **100%** | 96.3% → **99.3%** |

BC5CDR does not reach 100% because 30 of its gold annotations are nested
(a composite mention and its parts annotated together); the pipeline's
overlap-rejection rule discards one of each pair. That rule was left unchanged.

---

## 4. Configuration

Published spec `experiments/ncbi_disease_valid_round1.spec.json`, unmodified.

| | |
| --- | --- |
| Refinement subset | 10 training documents, `seed = 42` (shared across models) |
| Evaluation set | 100 validation documents, 791 gold entities |
| Reasoning effort | `high`, held constant across all three conditions |
| Output token cap | 64,000 |
| Stopping rule | strict-match F1 ≥ 0.9, or no improvement |
| Evidence per prompt | 5 examples |

---

## 5. The moderation process

F1 on the development subset rose at every iteration and crossed the threshold
after four rounds. The original study reports three iterations for this
configuration.

```
G0 → G1 → G2 → G3 → G4
0.7972 → 0.8369 → 0.8592 → 0.8873 → 0.9091     stop: threshold reached
```

Precision and recall rose together throughout. The targeted discrepancy cluster
shifted from coarse to fine errors:

| Round | Dominant cluster (the moderation target) | n |
| --- | --- | --- |
| 1 | SpecificDisease predicted as DiseaseClass (label) | 6 |
| 2 | SpecificDisease with wrong boundaries | 3 |
| 3 | DiseaseClass missed entirely | 3 |
| 4 | SpecificDisease missed entirely | 3 |

### 5.1 Discrepancy distribution across iterations

Rows are model predictions, columns are gold labels. The diagonal holds span
boundary mismatches, the `O` column holds predictions with no gold counterpart,
the `O` row holds gold entities with no prediction. C = CompositeMention,
D = DiseaseClass, M = Modifier, S = SpecificDisease, O = no entity.

Note that cells off the `O` row and column each count as one false negative *and*
one false positive — a mislabelled entity is both a gold entity that was missed
and a prediction that was wrong. The matrix total is therefore the number of
discrepancy cases, not a decomposition of either error type. For G₄:
FN = 3 label + 1 boundary + 5 missed = 9, and FP = 3 label + 1 boundary + 0
spurious = 4, matching the recorded counts.

**(a) G₀ — original guideline · F1 = 0.7972**

| pred＼gold | C | D | M | S | O | total |
| --- | --- | --- | --- | --- | --- | --- |
| **C** | 0 | 0 | 0 | 0 | 0 | 0 |
| **D** | 0 | 0 | 0 | **6** | 0 | 6 |
| **M** | 0 | 0 | 0 | 2 | 0 | 2 |
| **S** | 0 | 1 | 0 | 2 | 1 | 4 |
| **O** | 1 | 2 | 0 | 3 | 0 | 6 |
| **total** | 1 | 3 | 0 | 13 | 1 | **18** |

**(b) G₁ · F1 = 0.8369**

| pred＼gold | C | D | M | S | O | total |
| --- | --- | --- | --- | --- | --- | --- |
| **C** | 0 | 0 | 0 | 0 | 0 | 0 |
| **D** | 0 | 0 | 0 | **2** | 0 | 2 |
| **M** | 0 | 0 | 0 | 2 | 0 | 2 |
| **S** | 0 | 1 | 0 | 3 | 0 | 4 |
| **O** | 1 | 3 | 0 | 3 | 0 | 7 |
| **total** | 1 | 4 | 0 | 10 | 0 | **15** |

**(c) G₂ · F1 = 0.8592**

| pred＼gold | C | D | M | S | O | total |
| --- | --- | --- | --- | --- | --- | --- |
| **C** | 0 | 0 | 0 | 0 | 0 | 0 |
| **D** | 0 | 0 | 0 | 3 | 0 | 3 |
| **M** | 0 | 0 | 0 | 2 | 0 | 2 |
| **S** | 0 | 1 | 0 | 1 | 0 | 2 |
| **O** | 1 | 3 | 0 | 2 | 0 | 6 |
| **total** | 1 | 4 | 0 | 8 | 0 | **13** |

**(d) G₃ · F1 = 0.8873**

| pred＼gold | C | D | M | S | O | total |
| --- | --- | --- | --- | --- | --- | --- |
| **C** | 0 | 0 | 0 | 0 | 0 | 0 |
| **D** | 0 | 0 | 0 | 2 | 0 | 2 |
| **M** | 0 | 0 | 0 | 2 | 0 | 2 |
| **S** | 0 | 0 | 0 | 1 | 0 | 1 |
| **O** | 1 | 2 | 0 | 3 | 0 | 6 |
| **total** | 1 | 2 | 0 | 8 | 0 | **11** |

**(e) G₄ — final guideline · F1 = 0.9091**

| pred＼gold | C | D | M | S | O | total |
| --- | --- | --- | --- | --- | --- | --- |
| **C** | 0 | 0 | 0 | 0 | 0 | 0 |
| **D** | 0 | 0 | 0 | 3 | 0 | 3 |
| **M** | 0 | 0 | 0 | 0 | 0 | 0 |
| **S** | 0 | 0 | 0 | 1 | 0 | 1 |
| **O** | 1 | 2 | 0 | 2 | 0 | 5 |
| **total** | 1 | 2 | 0 | 6 | 0 | **9** |

**Summary across iterations**

| | G₀ | G₁ | G₂ | G₃ | G₄ |
| --- | --- | --- | --- | --- | --- |
| Label mismatch | 9 | 5 | 6 | 4 | **3** |
| Boundary mismatch | 2 | 3 | 1 | 1 | **1** |
| False negative | 6 | 7 | 6 | 6 | **5** |
| False positive | 1 | 0 | 0 | 0 | **0** |
| **Total discrepancies** | **18** | 15 | 13 | 11 | **9** |
| **True positives** | **57** | 59 | 61 | 63 | **65** |

**Reading the matrices.** The round-1 target `D→S` falls from **6 to 2**, the
same phenomenon and magnitude the original reports (7 → 1).

Both studies show the same overall shape: **the discrepancy total falls
monotonically while individual cells rebound.** The original's totals run
28 → 21 → 17 → 15 across its four matrices; here they run 18 → 15 → 13 → 11 → 9,
with true positives rising monotonically from 57 to 65. This matches the
original's Section 5.4 observation that moderation "does not monotonically
reduce *all* discrepancies, but instead rebalances precision–recall trade-offs" —
the claim is about individual cells, not the aggregate.

The two runs differ in **how severe those trade-offs are**. The original's
largest single-cell rebound is a sixfold jump (1 → 6) at its first iteration.
The rebounds here are mild by comparison: boundary errors rise from 2 to 3 at G₁
while label errors are being fixed, DiseaseClass false negatives rise from 2 to 3
before falling back, and the round-4 target `O→S` drops from 3 to 2 at the cost
of `D→S` rising from 2 to 3 — the only increase in the final matrix. Whether the
milder side effects reflect the newer model or simply the smaller absolute counts
(18 initial discrepancies here against 28 in the original) cannot be determined
from a single run.

Two blind spots are visible in the matrices:

- **`O→C` never moves.** CompositeMention false negatives sit at 1 through all
  five states. That cell was never frequent enough to become the dominant
  cluster, so the "moderate only the largest cluster" strategy never reached it.
- **The M column is empty throughout.** The 10 sampled development documents
  contain no gold Modifier entities, so moderation had no opportunity to learn
  that category — and Modifier is precisely the category that collapses on the
  validation set (Section 8.1). This is a concrete instance of the selection
  bias the original discusses in its Section 6.2.

### 5.2 Guideline growth

| | G₀ | G₁ | G₂ | G₃ | G₄ |
| --- | --- | --- | --- | --- | --- |
| Characters | 7,367 | 11,489 | 14,757 | 17,102 | **19,940** |

The guideline grew **2.7×**, roughly 3,000 characters per round. The cause is
that refinement hard-codes development-set content into the guideline: **15 of
43 development-set entity strings (34.9%) appear verbatim**, embedded in whole
sentences copied from the source documents. This also makes the development-set
F1 optimistic — part of 0.9091 measures whether the model can restate examples
already present in its own prompt. Section 8.2 quantifies the effect.

---

## 6. Main results

Validation set, 100 documents, 791 gold entities, strict match (exact boundary
and exact type).

| Condition | P | R | **F1** | TP | FP | FN | Predictions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **S** — prompt only | 0.34 | 0.46 | **0.39** | 360 | 694 | 431 | 1,054 |
| **G** — original guideline | 0.80 | 0.76 | **0.78** | 600 | 149 | 191 | 749 |
| **M** — refined guideline | 0.81 | 0.76 | **0.79** | 605 | 140 | 186 | 745 |

**Per entity type (F1)**

| Type | S | G | M | G−S | M−G |
| --- | --- | --- | --- | --- | --- |
| SpecificDisease | 0.64 | 0.84 | 0.85 | +0.20 | +0.01 |
| **Modifier** | **0.00** | 0.76 | 0.76 | **+0.76** | 0.00 |
| DiseaseClass | 0.36 | 0.66 | 0.65 | +0.30 | −0.01 |
| CompositeMention | 0.35 | 0.61 | 0.67 | +0.26 | +0.06 |

**Hypotheses**

| | This run | Original | Verdict |
| --- | --- | --- | --- |
| **H1** = G − S | **+0.39** | +0.27 | Confirmed, stronger than the original |
| **H3** = M − G | **+0.01** | +0.03 | Direction matches; not disconfirmed |

H3 is deliberately **not** claimed as confirmed: this is a single run with no
significance testing, and Section 6.1 shows the +0.01 is a small residue of a
much larger reshuffling.

### 6.1 The M−G gain is a residue of large-scale churn

Comparing true positives document by document, M did not simply add five
correct annotations to G's output. **It gained 48 and lost 43.**

| | Count |
| --- | --- |
| True positives M gained over G | 48 |
| True positives M lost relative to G | 43 |
| **Net** | **+5** |

Ninety-one annotations changed to yield a net gain of five — the net effect is
5.5% of the behavioural change. Refinement produced a broad reshuffle, not a
targeted correction.

**Where the losses went.** Each lost true positive was traced to what M
predicted at that span instead:

| Count | Gold label → M's prediction | Examples |
| --- | --- | --- |
| 8 | SpecificDisease → DiseaseClass | `cataract`, `myotonia`, `male-infertility` |
| 8 | Modifier → boundary shifted | `familial breast cancer`, `familial aniridia` |
| 7 | Modifier → nothing predicted | `tumor`, `Tumor`, `C6-deficient` |
| 5 | SpecificDisease → boundary shifted | `sporadic breast cancers` |
| 5 | DiseaseClass → SpecificDisease | `tumour`, `myopathy`, `cancer` |
| 10 | other reassignments | |

The two largest label flips run in **opposite directions between SpecificDisease
and DiseaseClass** — precisely the distinction the round-1 principle addressed
("a noun phrase headed by a generic pathology term, used referentially, is
SpecificDisease; used generically or taxonomically, DiseaseClass"). That rule
cut the targeted cluster from 6 to 2 on the development subset, but on held-out
data it is applied too aggressively in both directions. The five DiseaseClass
losses are exactly the generic pathology nouns the rule names — `tumour`,
`cancer`, `myopathy`.

**Modifier is damaged by rules that never concerned it.** The category gained 11
and lost 17, a net −6, with seven instances dropped entirely. Yet moderation
never targeted Modifier: the 10 development documents contain 19 Modifier
entities and the model labelled all of them correctly, so the category never
produced a discrepancy cluster and was never the subject of any round. The
refined rules about SpecificDisease and DiseaseClass spilled over into a
category that was never observed to be failing.

The prompt does carry a regression guard — `verified_examples` instructs the
model not to break cases already handled correctly — but it is populated from
development-set true positives only, so it cannot protect distributions that the
10 documents do not represent.

---

## 7. Attributing the differences

- **S is lower than the original (0.39 vs 0.46).** Driven almost entirely by the
  total failure of the Modifier category (Section 8.1). Excluding Modifier, S
  recovers roughly 63% of the remaining 573 gold entities, comparable to the
  original.
- **G and M are higher (0.78/0.79 vs 0.73/0.76).** Newer model.
- **H3 is weaker (+0.01 vs +0.03).** Section 6.1 identifies the mechanism: the
  round-1 principle generalises too aggressively on held-out data, flipping
  labels in both directions between SpecificDisease and DiseaseClass, and its
  side effects reach a category (Modifier) that moderation never targeted. A
  second contributing factor is that G already starts at 0.78 here versus 0.73
  in the original, leaving less headroom.

---

## 8. Findings not reported in the original

### 8.1 The label name conflicts with its annotation-scheme meaning

Under the prompt-only condition the model produced **311 `Modifier`
annotations and matched none of them** (218 in gold, 0 true positives).

```
Model predicts:  inherited · breast · ovarian · hereditary ·
                 genetic modifier · rare HRAS1 alleles
Gold contains:   VHL · DM · tumor · HD · breast cancer ·
                 myotonic dystrophy · ataxia-telangiectasia
```

The model reads "Modifier" in its ordinary English sense — an adjective or
qualifier. In NCBI Disease, `Modifier` denotes **a disease mention functioning
as a modifier**; every gold instance is a disease name. The two readings pick
out disjoint sets of objects, which is why boundary mismatches number only 8
while label mismatches reach 327.

The confusion matrix for this condition makes the disjointness explicit:

| gold Modifier (218) | went to |
| --- | --- |
| 113 | predicted as SpecificDisease |
| 69 | missed entirely |
| 23 | predicted as DiseaseClass |
| 12 | predicted as CompositeMention |
| 1 | labelled Modifier but with wrong boundaries |

Meanwhile 136 predicted Modifiers overlap no gold entity at all — adjectives
invented outright.

**This is not a capability failure; the label name actively misleads.** The
category's G−S of **+0.76** is the largest of the four. It shows that a guideline
carries specification information that cannot be inferred from the label name —
the strongest mechanistic evidence for H1 in this study, and a sharper argument
than the aggregate F1 difference.

A related effect: S over-annotates by 33% (1,054 predictions against 791 gold);
adding the guideline brings this to 749 immediately.

### 8.2 Development-set leakage, and the guideline inflation that causes it

```
Development set (10 docs, sentences copied into the guideline)
    0.7972 → 0.9091     +0.11
Validation set (100 held-out docs)
    0.78   → 0.79       +0.01
```

**An eleven-fold difference.** What leakage explains, and what it does not, must
be separated. Section 6.1 traced the 48 true positives M gained on the
validation set: only **2 of them** are development-set gold strings. The
validation gain is therefore *not* memorisation. Leakage instead corrupts the
**development-set score and the stopping rule that reads it** — the run halts
when F1 on the same 10 documents whose sentences sit in the prompt crosses 0.9,
and that F1 is 2 annotations above the threshold out of 74 gold entities.

The causal chain can be located precisely:

1. The original's Section 3.4.3 requires principles to use abstract phrasing
   rather than instantiations tied to specific tokens — and **the released
   implementation honours this**. The generated principles are uniformly
   abstract ("generic pathology term", "used referentially"), containing no
   specific entity names.
2. **Section 3.4.4 imposes no equivalent constraint.** The guideline-integration
   prompt contains no anti-instantiation instruction.
3. **That step is instead handed the full text of the development documents.**
   `verified_examples` passes complete document bodies together with an
   instruction not to break those cases, so the model lifts sentences straight
   out of the documents in front of it as worked examples.

Guideline inflation (Section 5.2) and leakage are the two ends of this single
mechanism, not separate phenomena.

Two improvements follow, addressing the two distinct problems:

- **For leakage** — restrict `verified_examples` to the matched annotations and
  a minimal context window rather than full document bodies, and add an
  abstraction constraint to the guideline-integration step mirroring the one
  already applied to principle generation.
- **For the stopping rule** — evaluate it on a second, disjoint sample. Drawing
  another 10 documents from the same pool costs no additional annotation effort
  and never enters any prompt. Rule induction still sees only 10 documents, so
  the minimal-supervision claim is preserved, while the halting decision is no
  longer made on data the guideline has memorised. A testable prediction: with a
  disjoint stopping set the loop should run *more* iterations, and validation
  M−G should exceed +0.01.

---

## 9. Observations on the method and its implementation

- **Boundary-error evidence is incomplete.** For `Span Boundary Error` clusters,
  the prompt sent to pattern explanation contains only the gold span text; the
  model's own predicted span is recorded but never rendered. Both labels in such
  a cluster are identical by definition, so the prompt carries no information
  distinguishing the boundary error the model is asked to explain.
- **Section 3.4.3 states the current guideline is provided; the implementation
  does not provide it.** The principle-generation template has no corresponding
  placeholder, although its body instructs the model to check consistency
  against the current guidelines.
- **Section 3.4.4 lists four inputs; three are passed.** The discrepancy context
  is absent, reaching the step only indirectly through the principle text.
- **The prompt-only baseline does not match Figure 5a.** Passing an empty
  guideline file still leaves five references to a guideline in the prompt, two
  of which are mutually contradictory: the model is told to follow the
  guidelines exactly and to cite the relevant guideline section, in a prompt
  that also states no guidelines were provided. This depresses S and therefore
  **inflates the measured H1 gain**.
- **Section 3.4.1's priority ordering sits uneasily with its grouping
  description.** The stated priority implies per-entity classification, while
  "grouped by predicted and gold label pairs" implies per-pair classification;
  the two disagree when one gold entity overlaps several predictions.
- **Discrepancy pairing is greedy in document order rather than by overlap
  size.** The order of gold annotations changes which entity is reported as
  missed. NCBI Disease and BioRED have no overlapping gold and never trigger it;
  BC5CDR has 64 overlapping pairs and does.

---

## 10. Limitations and next steps

**Limitations.** Single run, no repetitions and no significance testing. One of
nine configurations. The H3 effect of +0.01 is at a magnitude indistinguishable
from noise. The S baseline is depressed by the prompt defect described in
Section 9, so the H1 figure is an upper bound.

**Next steps**, in increasing cost:

1. **Test H2** — `low` versus `high` on the same model and dataset. `low` has
   been verified stable on the synchronous endpoint and costs substantially less.
2. **Complete the GPT row** — BC5CDR and BioRED.
3. **A leakage control experiment** — rerun moderation with the Section 8.2 fix
   and check whether validation-set M−G widens. This tests the leakage
   hypothesis directly.
4. **Additional model families** — Gemini, DeepSeek.

---

## Appendix — transport-level changes

None of these alter the prompt sent or the output received.

| Change | Reason |
| --- | --- |
| Azure endpoint support: deployment in the URL, `api-key` header, api-version query parameter | The released provider targets `api.openai.com` and cannot reach an Azure deployment |
| `max_completion_tokens` replaces `max_tokens` | Every GPT-5.x deployment rejects `max_tokens` with `400 Unsupported parameter` |
| `reasoning_effort: "high"` replaces nested `reasoning: {"effort": …}` | The nested form belongs to the Responses API and is rejected on chat/completions with `400 Unknown parameter` |
| Asynchronous submission plus polling for `high` and `xhigh` | The synchronous endpoint withholds response headers until the first content token, and reasoning emits none. Measured: `low` 35s and `medium` 61s succeed; `high` dropped at 130s (and succeeded on retry at 89s); `xhigh` dropped at 180.1s, 180.2s and 181.4s across three api-versions and both streaming modes. Under the queued API, `xhigh` ran 279s with no disconnect. |
| Retry on connection failure; resubmit jobs stalled in `queued` | A dropped TLS connection during a status poll ended one 30-minute run; jobs observed sitting at `queued` for hours without ever starting ended two more |

**Cost.** Refinement: 62 API calls over 113.5 minutes (about 110 s per call at
`high`). Validation annotation: 100 documents per condition, three conditions.

**Artefacts.** Output directories are named `<date>_<dataset>_<model>-<effort>_<what>`:

| | |
| --- | --- |
| Refinement | `outputs/20260802_ncbi_gpt54-high_moderation/` |
| Validation annotations | `outputs/20260802_ncbi_gpt54-high_valid-{S,G,M}/` |
| Scores and diagnostics | `reproduction/results/ncbi-{s,g,m}-gpt54/` |
