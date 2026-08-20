# Ablation Report — Removing Verified Examples from Guideline Refinement

NCBI Disease · GPT-5.4 (Azure) · `reasoning_effort=high` · seed 42

---

## 1. What prompted the ablation

Section 3.4.4 describes verified examples (true positives) as "in-prompt
checks": the model is told not to introduce changes that would flip cases it
already handles correctly. In the released implementation that block occupies
**46% of the refinement prompt** (8,170 of 17,605 characters in round 1) and
carries 18 true positives together with the **complete text of five development
documents** — `iterative.py:385` emits `f"TEXT: {document.text}"`, and each of
the five abstracts appears character-for-character (1,617, 1,140, 1,288, 1,768
and 1,114 characters, all matching their source files exactly).

The model does not treat that block as a constraint. It treats it as material.
Seven newly written guideline entries were sampled from round 1 and traced back
to their source; **all seven are true positives from the block, and none appears
among the discrepancy examples the round was moderating** — the two sets are
disjoint. That round targeted `Gold: SpecificDisease vs LLM: DiseaseClass`,
whose examples are `PAH deficiencies`, `vasculitis`, `arthritis`,
`cutaneous vasculitis` and `Chronic neisserial infection`; the entries written
into the guideline are `ovarian cancer`, `fragile X syndrome`,
`Wiskott-Aldrich syndrome`, `retinal telangiectasis`, `Coats telangiectasis`,
`autosomal recessive disorder` and `mental retardation`. Over four rounds the
guideline grew from 7,367 to 19,940 characters and **15 of 43 development-set
entity strings (34.9%) were written in verbatim**.

Two qualifications. The seven are a sample, not an exhaustive enumeration of
everything the round added. And the comparison is against the discrepancy
examples the model actually saw: the cluster held 6 cases and `n_examples = 5`
sent five of them, so the sixth was never in the prompt.

## 2. Hypothesis

Removing the block stops the guideline absorbing development-set content, and
regression protection is not lost because the loop already gates on
`improved = F1_after > F1_before` — a net check backed by real re-annotation
rather than a sentence in a prompt.

**Single variable.** Only the CONSTRAINT block and the CONSTRAINT CHECK
instruction referring to it were removed (template 1,676 → 1,221 characters).
No instruction was added. True positives remain in `infer_discrepancy_patterns`,
which Section 3.4.2 requires for contrastive analysis. Upstream source is
untouched; the template dict is overridden at runtime by
`reproduction/ablation_no_tp.py`.

## 3. Results

| Run | Rounds | Stop | F1 trajectory | Final guideline | Hardcoded dev entities |
| --- | --- | --- | --- | --- | --- |
| **withTP** (published) | 4 | threshold | 0.7972 → 0.8369 → 0.8592 → 0.8873 → **0.9091** | 19,940 | **15/43 (34.9%)** |
| noTP run1 | 2 | interrupted | 0.7943 → 0.8310 → 0.8592 | 11,980 | **0/43** |
| noTP run2 | 2 | no improvement | 0.7972 → 0.8369 → 0.8369 | 10,002 | **0/43** |
| noTP run3 | 1 | interrupted | 0.7972 → 0.8611 | 10,398 | **0/43** |
| noTP run4 | 2 | no improvement | 0.7391 → 0.7887 → 0.7887 | 9,809 | **0/43** |
| noTP run5 | 3 | no improvement | 0.8085 → 0.8169 → 0.8227 → 0.8227 | 11,442 | **0/43** |

Larger development sets, `n_examples` scaled proportionally (dev30 with 15,
dev50 with 25), reverted on **round 1** in both cases.

### 3.1 The hypothesis holds on hardcoding

**Five independent ablation runs, 0/43 in every one.** The strings the published
run wrote into its guideline — `Coats disease`, `Sjogren-Larsson syndrome`,
`Wiskott-Aldrich syndrome`, `retinal telangiectasis`, `autosomal recessive
disorder`, `ichthyosis`, `spasticity` and six more — never appear. Guideline
inflation drops from 2.71× to 1.33–1.63×, and what growth remains contains no
development-set content.

The effect is an order of magnitude and is not sensitive to run-to-run variance.

### 3.2 But the loop no longer sustains itself

**With the block, the run climbs for four rounds and reaches the 0.9 threshold.
Without it, all five runs revert within one to three rounds and none exceeds
0.8611.**

This is the central finding, and it reframes the block's role. It was written as
a regression guard, and that is exactly what it does — the mechanism is
memorisation, but the function is real. Removing it removes the hardcoding and
the ability to keep improving at the same time, because they are the same thing:
the guideline climbs on the development set by restating answers already in its
own prompt.

**The published method's 0.9091 is therefore not a generalisation result.** It
is what a regression guard implemented as in-prompt text produces when the
evaluation set and the memorised set are identical.

### 3.3 Development-set size does not explain the early reversion

The dominant cluster's share of total discrepancies is comparable across sizes —
17% at dev30 and 20% at dev50, against 19–33% at dev10 — and so is the
theoretical gain from resolving it completely (+0.046 and +0.056 against
+0.042 to +0.101). Both large-set runs are n=1, and at dev10 round-1 gains
ranged from +0.0084 to +0.0496, so a single reversion at a larger size is within
the observed spread. **Size is not identified as the cause by this data.**

### 3.4 Successful rounds realise about half their potential（*）

| Run | Round 1 achieved | Theoretical maximum | Realised |
| --- | --- | --- | --- |
| withTP | +0.0397 | +0.0839 | 47% |
| noTP run2 | +0.0397 | +0.0699 | 57% |
| noTP run4 | +0.0496 | +0.1014 | 49% |
| noTP run5 | +0.0084 | +0.0567 | 15% |

Even rounds that improve break roughly as much as they fix elsewhere. This
matches the held-out finding that M gained 48 true positives over G and lost 43
for a net of +5. Single-cluster targeting combined with whole-document guideline
rewriting produces broad collateral change, which is what limits the number of
productive rounds — independent of the verified-examples block.

## 4. Conclusion

The verified-examples block causes the hardcoding **and** carries the regression
protection that keeps refinement going. Removing it cleanly eliminates the first
and destroys the second. The published configuration reaches the threshold only
by memorising the set it is scored on; the ablated configuration is honest and
stalls below 0.87.

**Neither configuration demonstrates guideline refinement that generalises.**
What is needed is a regression guard that does not place answers in the prompt —
the block's function without its mechanism.

## 5. Method notes

Two diagnostic gaps were found and fixed while running this; neither changes
loop behaviour.

- **Reverted rounds discarded the candidate.** `guidelines_after`,
  `summary_after` and `diagnostics_after` are all reset to the "before" values
  when a round reverts, so the refined guideline, its score and its annotations
  left no trace. `guidelines_candidate`, `summary_candidate` and
  `diagnostics_candidate` now record them. The progress line also printed
  `summary_after`, which on a reverted round is `summary_before` — reporting
  "F1 x → x" regardless of what the candidate scored.
- Refinement does make substantial edits when it reverts. The dev30 candidate
  added 45 lines against 2 removed, with abstract rules, negative constraints
  and counter-examples. A reverted round is not an empty one.

**Artefacts.** `outputs/20260802_ncbi_gpt54-high_moderation` (published
configuration) and `outputs/2026080{5,6}_ncbi_gpt54-high_moderation-noTP_run{1..5}`
(ablation). Splits in `reproduction/dev_splits/`.
