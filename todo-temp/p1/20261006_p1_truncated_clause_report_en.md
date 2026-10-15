# P1: Controlled Experiment Truncating the Trailing Restrictive Clause of the Round 3 Principle

Date: 2026-10-06. Control run: [20260802_gpt54-high_moderation](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/) Round 3. Experiment script and artifacts: this directory (`todo-temp/p1/`). This experiment called the model to regenerate the guideline and re-annotate the 10 development documents. The original Round 3 result is taken from the saved snapshot, not rerun.

Background in plain terms: in Round 3 the model wrote a moderation principle whose second half is a restrictive "do not apply this rule" clause. The suspicion was that this clause caused the two fatal guideline items that contradict gold. This experiment deletes exactly that clause and nothing else, then checks whether the focal misses recover and whether false positives increase.

## Conclusions

**Hypothesis not confirmed: the fatal items were not caused by the "do not apply" clause in the second half of the principle alone.**

- After truncation, the flat FALDH exclusion example at lines 41 to 44 of the original guidelines ("Do not annotate ... because it refers to enzyme activity") did **disappear**. But without the clause, the model **regenerated equivalent restrictions on its own**: a conditional FALDH exclusion, a broad exclusion of phrases like "abnormal development / absence of a protein", and even a new conditional exclusion example for "abnormal retinal vascular development" (absent in the original).
- None of the three focal misses (deficiency of norrin, deficient activity of fatty aldehyde dehydrogenase, abnormal retinal vascular development) recovered in the truncated version.
- Truncated dev F1 **0.8592 to 0.8671**, below the original principle's **0.8873**. Under the loop's acceptance rule (after > before) it would still be accepted, but the gain is clearly smaller.
- The truncated version also shows signs that what the clause suppressed has loosened: PAH deficiency went from missed to wrongly typed (DiseaseClass, FP+FN), and cutaneous vasculitis flipped from correct to DiseaseClass (losing a TP and adding an FP). The clause was also holding back DiseaseClass over-expansion.

## 1. Design (controlled variable)

**Only variable**: in the saved Round 3 `refine_guidelines` prompt, the moderation principle was truncated from 521 to 281 characters by deleting the whole sentence after the semicolon:

> **do not apply this rule** when the phrase refers only to a normal biological process, a molecular/substance entity or level, or an isolated descriptive finding that is **not** presented as a pathological condition of the patient/disorder.

The full principle before and after truncation: [principle_original.txt](principle_original.txt) and [principle_truncated.txt](principle_truncated.txt). The truncated prompt: [prompt_truncated.txt](prompt_truncated.txt) (asserted to be character-identical to the saved prompt except for that sentence).

**Fixed items**: guidelines_before (iteration_02 state, character-identical to the snapshot), the CONSTRAINT verified-examples block kept as is, the same 10 development documents (seed 42), the same model configuration (Azure eastus2-gpt-5.4, reasoning high), the same loop scorer and clustering function.

## 2. Guideline text comparison

| Location | Original Round 3 result | Truncated candidate |
| --- | --- | --- |
| First half of the principle (rule body) | Line 11: in definitional/characterization contexts, generic noun phrases denoting abnormal pathological states are labeled DiseaseClass | Kept (rewritten and expanded at lines 7 and 10) |
| Second half of the principle (restrictive clause) | Line 12: "Do not apply the previous bullet when ... molecular/substance entity or its level/activity ...", calling such phrases "not disease mentions" | This sentence **does not exist** |
| FALDH | Lines 41 to 44: "> Deficient activity of fatty aldehyde dehydrogenase - **Do not annotate**, because it refers to enzyme activity" (exactly opposite to gold SpecificDisease) | Flat exclusion **gone**; but lines 256 to 260 add a **conditional** exclusion: "not annotated when it is only a functional or mechanistic description" |
| abnormal retinal vascular development | No exclusion example | Lines 33 to 34 **add** a conditional exclusion example ("Do not annotate ... when it is only a mechanistic or descriptive characterization"), opposite to gold DiseaseClass |
| Other new restrictions | n/a | Line 11: "abnormal development, reduced activity, altered expression, or absence of a protein are **not** annotated unless ...", which literally still covers "deficiency of norrin" |

The truncated guideline is 18,654 characters, longer than the original result (17,102): the model wrote more detail using numbered lists. See [guidelines_candidate_truncated.txt](guidelines_candidate_truncated.txt).

## 3. Annotation results (same 10 development documents, strict matching)

| State | TP | FP | FN | F1 |
| --- | --- | --- | --- | --- |
| After R2 (before R3) | 61 | 7 | 13 | 0.8592 |
| R3 original principle (saved snapshot) | 63 | 5 | 11 | 0.8873 |
| R3 truncated principle (this run) | 62 | 7 | 12 | **0.8671** |

Focal cases (gold to prediction in each state):

| Entity | Gold | After R2 | R3 original | R3 truncated |
| --- | --- | --- | --- | --- |
| abnormal retinal vascular development | DiseaseClass | O | O | O |
| deficiency of norrin | DiseaseClass | O | O | O |
| spasticity | DiseaseClass | O | **TP** | **TP** |
| deficient activity of fatty aldehyde dehydrogenase | SpecificDisease | O | O | O |

All entity level changes of the truncated version relative to the original:

- **TP gains**: none.
- **TP losses**: cutaneous vasculitis [646,666) (SpecificDisease to DiseaseClass).
- **New FP**: cutaneous vasculitis labeled DiseaseClass; deficiency of hepatic phenylalanine hydroxylase went from missed (O) to labeled DiseaseClass (gold SpecificDisease, counting both FP and FN).

Error clusters of the truncated version (12 total, vs 11 in original R3): S to D type errors **4** (vs 2 in the original), D to O 2, S to O 2, S to M 2, span 1, C to O 1. The rise of S to D matches DiseaseClass over-application after the restriction loosened.

## 4. Verdict on the hypothesis and what follows

1. **The second half of the principle is not the sole cause of the fatal items.** After truncation the flat FALDH exclusion did disappear, but equivalent conditional restrictions were regenerated by the model on its own, and none of the three focal misses recovered. The norrin exclusion example was only added in Round 4 anyway, so norrin being missed throughout this round has nothing to do with the restriction text.
2. **The clause is not purely harmful.** The truncated version's gain is smaller (+0.008 vs the original's +0.028), and S to D type errors doubled: the clause was partly suppressing DiseaseClass over-expansion. This matches the framing in the slides ("the first half expands recall, the second half is a safety clause"), but the safety clause was written in a way that swept the target cases in too.
3. **Implication for P2**: the problem lies in the **wording and scope** of the restrictive clause ("molecular/substance entity or its level/activity" literally covers every "deficiency of X"), not in whether a restriction exists. P2 (scoped rewrite: let the exclusion constrain only mechanistic/molecular non-pathological uses, and explicitly exempt pathological deficiency contexts) is still a reasonable next step. At the same time, check whether the CONSTRAINT block is hinting to the model that compensating restrictions are needed.
4. **Limitations**: this experiment is a single rerun. Annotation has random fluctuation (size-noise experiment SD 0.009 to 0.015), so part of the 0.8671 vs 0.8873 gap may come from annotation sampling; the truncated guideline text is itself a single generation sample. The S/D flip-flopping of cutaneous vasculitis across rounds (P0: D, S, D, S, D) suggests its flip may also contain a noise component.

## Verification record

- Reproduce with: `python todo-temp/p1/run_p1.py` (requires the Azure 5_4 configuration in .env; this run took about 34 minutes).
- Artifacts: [prompt_truncated.txt](prompt_truncated.txt), [guidelines_candidate_truncated.txt](guidelines_candidate_truncated.txt), [annotations_truncated.json](annotations_truncated.json), [result.json](result.json) (all counts and per-case data).
- Original data come from the saved snapshot iteration_03/snapshot.json (SHA-256 in the [P0 report](../p0/20261006_round4_p0_report.md)). The assertion on the truncation point and the assertion that the principle occurs exactly once in the prompt are enforced by the script.
