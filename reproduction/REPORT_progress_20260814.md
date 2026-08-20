# Progress Report: Hard-Coding and the Development-Set Learning Curve

**Period** 2026-08-02 to 2026-08-14 · **Dataset** NCBI Disease · **Model** GPT-5.4 (Azure), `reasoning_effort=high` · **Seed** 42

## I. Introduction

This work reproduces *Refining and Reusing Annotation Guidelines for LLM Annotation* and probes two weaknesses in its method.

> **Aim 1.** Revise the prompt to avoid hard-coding, e.g. do not list the discrepancy directly in the guideline, this helps the LLM to cheat.
>
> **Aim 2.** After finishing the hard-coding issue, expand the size of the development dataset to see how the F1 score changes, to test the paper's assumption: *"Future research should examine the learning curve by incrementally increasing the volume of development data."*

Aim 2 presupposes Aim 1: a learning curve measured on a method that memorises its development set measures memorisation, not learning. The two were explored in parallel anyway, because Aim 1 proved structural rather than a wording problem, and because the Aim 2 curve turned out to carry information about Aim 1. **Aim 2 used the published methodology unchanged.** Its absolute F1 inherits the hard-coding caveat; its trend does not, since the confound is measured at every point.

## II. Progress Made Since the Last Report

### A. Aim 1: eliminating hard-coding

#### A.1 The mechanism

Hard-coding does not come from the discrepancy examples. It comes from the **CONSTRAINT block of verified examples** in `refine_guidelines`, Section 3.4.4's "in-prompt check", which lists true positives so the rewrite will not break cases that already pass. That block is **46% of the refinement prompt** (8,170 of 17,605 characters in round 1) and carries 18 true positives plus the **full text of five development documents**. The model reads it as material, not as a constraint: seven new guideline entries were traced to source, all seven came from that block, and none appears among the discrepancy examples the round was moderating.

#### A.2 How the hard-coding metric is computed

Two kinds of quoted mention mean opposite things:

| Quoted mention | Reached the prompt via | Meaning |
| --- | --- | --- |
| **Discrepancy** | §3.4.2 discrepancy examples | The method working. §3.4.4 is supposed to address these. |
| **True positive** | §3.4.4 CONSTRAINT block | Answer key, scored on the documents it was copied from. |

The question is therefore not how much text was copied but how much of it is the answer key. [`measure_hardcoding.py`](reproduction/measure_hardcoding.py) reports:

**Metric A, absorption (recall-style).** Of the distinct gold mention strings in the development split, how many appear verbatim in the final guideline?

```
absorption = |{s ∈ gold(dev) : s ∉ G_initial ∧ s ⊂ G_final}| / |{s ∈ gold(dev) : s ∉ G_initial}|
```


#### A.3 Experiment 1: remove the block

Only the CONSTRAINT block and the instruction referring to it were removed (1,676 to 1,221 characters). Nothing was added.

| Run | Rounds | Stop | Dev F1 | Guideline | Absorption |
| --- | --- | --- | --- | --- | --- |
| **withTP** (published) | 4 | threshold | 0.7972 to **0.9091** | 7,367 to 19,940 | **15/37 = 41%** |
| noTP run 2 | 2 | no improvement | 0.7972 to 0.8369 | 7,367 to 10,002 | **0/37** |
| noTP run 4 | 2 | no improvement | 0.7391 to 0.7887 | 7,367 to 9,809 | **0/37** |
| noTP run 5 | 3 | no improvement | 0.8085 to 0.8227 | 7,367 to 11,442 | **0/37** |

Two further ablation runs were interrupted before writing a final artefact; the earlier report scored those by hand and also found zero. **Every ablation run is zero, none reaches the threshold, and all stall within 1 to 3 rounds.**

> **This is the central finding of Aim 1.** The block was written as a regression guard and that is genuinely what it does. The mechanism is memorisation but the function is real, so it cannot be deleted: removing the hard-coding and removing the ability to keep improving are the same operation. The guideline climbs on the development set by restating answers already in its own prompt. **The published 0.9091 is not a generalisation result.**

#### A.4 Experiment 2: keep the block, forbid verbatim copying

Deletion fails, so the next attempt keeps the true positives in the prompt and adds one instruction: write the rule, do not transcribe the mention.

Is the model capable of that? The pipeline contains a natural control. Step §3.4.3 writes a **principle** and step §3.4.4 writes the **guideline**, in the same round, with the same true positives available: the pattern explanation feeding §3.4.3 quotes them as "Contrastive Evidence", and 11 of the 37 development mention strings appear in the principle prompt. §3.4.3 is told to state a general rule. §3.4.4 is not. Across the four rounds of the published run the principles contain **0** development mention strings while the guidelines accumulate **10, 12, 13, 15**.

**This is suggestive, not conclusive, and the reason is size.** The four principles total 2,430 characters against 12,573 characters of new guideline text. At the guideline's rate of 1.19 strings per 1,000 characters, 2.9 would be expected in the principles, so observing 0 carries p ≈ 0.06. Consistent with the constraint working, equally consistent with a short output having less room. This data does not separate them.

#### A.5 Experiment 3: post-hoc verification

The CONSTRAINT block does two things at once: it tells the model not to break the passing cases, and it says what they are. A.3 showed that deleting it loses both. **Post-hoc verification separates them in time: withhold the true positives while the guideline is written, then check them afterwards by actually running the draft.** The guard stops being a promise in a prompt and becomes a measurement on the output, so there is nothing to copy at the moment of writing.

```
ROUND n
─────────────────────────────────────────────────────────────────────
   annotate dev set with G_prev
         │
         ├──► protected = true positives ....... CHECKER ONLY
         │                                       never enters a prompt
         └──► discrepancies
                   │
                   ▼
              §3.4.1 analysis -> §3.4.2 patterns -> §3.4.3 principle
                   │                               (published, unchanged)
                   ▼
      ┌──►  WRITE draft G_new ................... WRITER sees no TPs
      │            │
      │            ▼
      │       annotate dev set with G_new
      │            │
      │            ▼
      │       lost = protected - TPs(G_new)
      │            │
      │            ├── lost = 0, or budget spent ──► keep best draft
      │            │                                        │
      │            └── lost != 0 ──┐                        │
      │                            │                        │
      └── RETRY: names only the ───┘                        │
          cases that broke                                  │
                                                            ▼
                                    OUTER: re-annotate independently
                                           improved = F1_new > F1_prev
```

**The retry path leaks, and this was measured.** To repair a regression the model must be told which case broke, and that description is itself an answer. Within one round of condition **A**, where the only difference between the two attempts is whether the regression list was received:

| Attempt | Feedback | Regressions | **Dev strings leaked into the guideline** |
| --- | --- | --- | --- |
| 1 | none | 4 | **0 / 37** |
| 2 | names the mention and its correct label | 0 | **6 / 37** |

Condition **B** tested the obvious fix, giving only the character span and entity type so the mention text is never shown. Over five attempts it leaked **0 every time** and never repaired anything: regressions ran 4, 5, 5, 6, 4 and no draft reached the pre-refinement baseline.

> **Post-hoc verification does not escape the dilemma of A.3, it reproduces it one level down.** The copyable unit and the diagnosable unit are the same object: withhold the mention text and the model loses the ability to fix what it broke. What the design does buy is that the leak becomes *conditional*, since the first draft is always clean and only a failed check exposes anything, and *bounded*, at the cases that actually broke rather than all 18 true positives and five full documents every round. Measured, that is 6/37 against the published 15/37.
>
> **The conditionality has not materialised.** Every observed round went to retry, so in practice the leak fires every round. And if the regression count is mostly sampling noise, the retry fires on a regression that never happened, paying the full leak for nothing. Condition **C** adds A.4's abstraction constraint to the retry path; it has not run to completion.

| Run | Round | Attempts (regressions) | Dev F1, internal | Dev F1, outer re-annotation |
| --- | --- | --- | --- | --- |
| **A** | 1 | 4, 0 | 0.8286 | 0.8169 to **0.8143**, `improved=False` |
| **C** | 1 | 2, 0 | 0.8531 | 0.7857 to **0.8451**, `improved=True` |
| **C** | 2 | 2, 1, 2 | 0.8671 | crashed before completing |

**A validity problem was found and is being measured.** The regression count is `protected − TPs(trial)`, where both sides are independent annotation samples of the same documents, so it mixes real breakage with sampling noise, and the noise term has never been quantified. Three signs it may dominate:

1. **Non-monotone feedback.** C round 2 went 2, 1, 2: attempt 3 received a shorter regression list than attempt 2 and produced more regressions.
2. **A ratchet in the stopping rule.** The loop stops as soon as an attempt scores 0, so a lucky draw is never re-tested while an unlucky one gets more draws. Both observed zeros landed on attempt 2 and stopped immediately.
3. **Internal beats outer in both rounds** (−0.0143, −0.0080), the signature of picking the best of several noisy drafts. A is the sharp case: 0 regressions and +0.0117 internally, then −0.0026 under independent re-annotation.

A noise-floor measurement is running: annotate dev10 three times with the **unchanged** guideline and count how many true positives move. Every difference is noise by construction, so it gives the floor the loop should stop at.

### B. Aim 2: development-set size and the learning curve

Sizes **10 / 20 / 30**, nested (dev10 ⊂ dev20 ⊂ dev30) so a larger set is strictly more information, never a different sample. `n_examples` scaled with the set (5 / 10 / 15), since the paper's 5 is stated relative to 10 documents. Each refined guideline was applied to the same held-out 100-document validation set used for the S/G/M comparison.

| Dev size | Rounds | Stop | Dev F1 | Dev gain | **Valid F1** | **vs. G** | Absorption |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 4 | threshold | 0.7972 to **0.9091** | **+0.1119** | 0.7878 | +0.0085 | **41%** |
| 20 | 2 | no improvement | 0.7821 to 0.8105 | +0.0284 | 0.7745 | **−0.0047** | 9% |
| 30 | 3 | no improvement | 0.8092 to 0.8577 | +0.0485 | **0.8050** | **+0.0258** | **3%** |

Validation baselines: S (no guideline) 0.3902, G (shipped guideline) 0.7792.

**Development gain and held-out gain dissociate.** dev10 posts the largest development gain in the study and transfers 8% of it; dev30 posts less than half that gain and transfers 53%. This is the expected signature if the dev10 gain is largely memorisation, and Metric A confirms it independently: **absorption falls monotonically, 41% to 9% to 3%.** The CONSTRAINT block is capped at `n_examples` documents, so copyable material grows far more slowly than the gold-mention denominator (37, 68, 115) and copying stops being an efficient way to raise development F1. **Enlarging the development set is itself a partial mitigation for Aim 1**, not by design but measurably.

**Transfer is governed by error-type coverage, not volume.** Each split's baseline discrepancy profile against the validation set's:

| Error class | **valid** | dev10 | dev20 | dev30 |
| --- | --- | --- | --- | --- |
| `Gold:Modifier vs LLM:O` | **17%** | **0%** | 19% | 14% |
| `Gold:O vs LLM:Modifier` | **11%** | 0% | 6% | 4% |
| `Gold:SpecificDisease vs LLM:DiseaseClass` | 10% | **30%** | 19% | 17% |
| **any class involving Modifier** | **41%** | **10%** | 30% | 22% |
| total discrepancies at baseline | 229 | 20 | 53 | 78 |

Modifier accounts for 41% of validation errors and 10% of dev10's, and the largest single validation error class occurs **zero times** in dev10. Four rounds of refinement could not address it, which caps how much of dev10's +0.1119 could ever have transferred, independent of memorisation.

dev20's negative result is best read as n=1 variance on a 2-round run that reverted early, but that is not yet demonstrated and is the main gap. With three points, one regressing, the curve is **directionally supportive but not established**. What is established is a mechanism the paper does not discuss: the development set supplies an error-type distribution, not just volume, and transfer depends on how well it matches the target.

## III. Current Status

| Question | Status | Evidence |
| --- | --- | --- |
| Does the published method hard-code? | **Settled, yes** | 41% absorption at dev10; 7/7 traced entries from the CONSTRAINT block |
| Can the block be removed? | **Settled, no** | 5/5 ablation runs at zero, all stall in 1 to 3 rounds, ceiling 0.8611 vs 0.9091 |
| Does an abstraction constraint help? | Premise verified, effect not isolated | §3.4.3 abstracts at 0 to 1 strings/round; C not run to completion |
| Does post-hoc verification work? | **Open, metric validity in question** | Non-monotone 2,1,2; internal minus outer −0.0143, −0.0080 |
| Does dev size raise held-out F1? | Directionally yes, n=1 per point | valid +0.0085, −0.0047, +0.0258 |
| Does dev size reduce hard-coding? | **Settled, yes, monotone** | absorption 41%, 9%, 3% |

**Running:** noise-floor measurement. **Halted:** condition C, killed by a transient Azure `server_error` at 9.4 h, after round 1 and round 2's drafts.

## IV. Next Steps and Timeline

| # | Step | Depends on | Est. |
| --- | --- | --- | --- |
| 1 | **Finish the noise floor**, read per-pair `lost` against the observed 4, 2, 2, 1. | running | < 1 h |
| 2 | **Decide the verification design.** Floor 0 to 1: signal is real, restart C. Floor ≥ 2: the selection rule is choosing on noise, replace with a single draft plus feedback deferred to the next round, or *k* repeated annotations averaged. | 1 | 1 d |
| 3 | **Add API-level retry** for Responses `status='failed'`, so a transient fault cannot kill a 9-hour run. | | < 1 h |
| 4 | **Second seed at dev20**, to settle whether −0.0047 is variance or a real dip. | 2 | 2 d |
| 5 | **Extend the curve to dev50** under whichever design survives step 2. | 2 | 3 d |
| 6 | **Report Aim 1's conclusion** with the surviving intervention measured on held-out data, not development F1. | 2, 4 | |
| 7 | Replicate on BC5CDR and BioRED. | 6 | later |

Step 2 gates everything downstream. Steps 4 and 5 should not run under the published methodology again, since they would only re-measure a confound already quantified in II.B.

## V. Challenges and Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| **The two aims may not be separable.** A.3 shows hard-coding and loop progress are one mechanism; if no intervention preserves both, Aim 1's answer is a negative result about the method. | High, reframes the contribution | The negative result is publishable and fully evidenced; the II.B mechanism stands independently. |
| **The verification metric may be measuring noise.** | High, invalidates A.5 | Being measured now; decision rule fixed in advance, floor ≥ 2 means redesign. |
| **Verbatim-only hard-coding metric.** A model told to abstract may paraphrase and score as success. | Medium, false positive for A.4 | Read alongside guideline growth and added-line shape; a paraphrase check is a possible extension. |
| **n=1 per curve point.** | Medium, dev20's dip unattributable | Step 4. Round-1 spread at dev10 was +0.0084 to +0.0496, so differences under ~0.04 are not interpretable. |
| **Cost and Azure instability.** Verification costs `max_attempts × \|dev\|` annotations per round; C took 9.4 h for two rounds at 8.4 min/call, then died to a transient fault. | Medium, limits replication | Reduce `max_attempts` from 3 to 2, run conditions sequentially, add step 3's retry. Per-iteration checkpoints already let a restart resume. |

## VI. Conclusion

**Aim 1 is diagnostically complete and not yet solved.** The hard-coding is fully localised to the CONSTRAINT block of verified examples, 46% of the refinement prompt, and quantified at 41% absorption for the published dev10 configuration. The decisive result is that this block cannot simply be removed: five ablation runs eliminate hard-coding entirely and every one of them stalls below the threshold the published run reaches. Memorisation is not a side effect of the regression guard, it is the regression guard, so the published 0.9091 should not be read as generalisation. Two replacements are in flight: an abstraction constraint whose premise is verified, and post-hoc verification whose own measurement validity is now under test.

**Aim 2 produced a usable curve and one result stronger than expected.** Development gains and held-out gains dissociate: dev10 gains +0.1119 on its own set and transfers +0.0085, while dev30 gains less than half as much and transfers +0.0258. Absorption falls monotonically with size, 41% to 9% to 3%, which both explains the dissociation and shows that enlarging the development set is itself a partial mitigation for Aim 1. Transfer is driven by error-type coverage rather than volume: Modifier accounts for 41% of validation errors and 10% of dev10's, and the largest validation error class never occurs in dev10.

Both lines converge: **the development set's composition, not its size or the refinement loop's own F1, determines whether a refined guideline generalises.** The immediate decision point is the noise-floor measurement, which determines whether the current verification design survives.
