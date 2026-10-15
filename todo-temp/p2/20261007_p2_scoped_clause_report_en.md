# P2: Controlled Experiment Rewriting the Round 3 Principle's Restrictive Clause with a Narrowed Scope

Date: 2026-10-07. Control run: [20260802_gpt54-high_moderation](../../outputs/ncbi_disease/20260802_gpt54-high_moderation/) Round 3. Experiment script and artifacts: this directory (`todo-temp/p2/`). This experiment called the model to regenerate the guideline and re-annotate the 10 development documents. The original Round 3 and P1 results are taken from saved data, not rerun.

Background in plain terms: P1 deleted the restrictive clause and the focal misses did not recover. P2 tests a softer version of the same idea: keep the restriction, but rewrite it so it only excludes non-pathological uses and explicitly keeps pathological deficiency states covered. If wording were the cause, this arm should recover the misses.

## Conclusions

**The scoped rewrite also failed to recover the focal misses. P2 dev F1 0.8511 is the lowest of the three arms, below the R2 baseline, and would be rolled back under the loop rule. Combined with P1, the three arms of evidence show: the proximate cause of the focal misses is not the wording of the restrictive clause, but the annotation model's upstream judgment of these contexts.**

- Focal case outcomes are **identical under all three principle versions**: spasticity fixed; deficiency of norrin, deficient activity of fatty aldehyde dehydrogenase (FALDH), and abnormal retinal vascular development all still missed.
- The text side worked as designed: the FALDH exclusion changed from flat (original) to conditional ("not annotated when it is only a biochemical characterization"), consistent with the P2 principle's scope wording. But annotation behavior did not follow the text.
- P2 lost 3 TP relative to the original (exudative retinal detachment type flip, G6PD deficient lost, cutaneous vasculitis type flip), total discrepancy 14 (original 11, P1 12).

## 1. Design (controlled variable)

**Only variable**: in the saved Round 3 `refine_guidelines` prompt, the second half of the moderation principle was changed from "delete" (P1) to "scoped rewrite". The first half is byte-identical (programmatic concatenation, asserted). The rewritten principle in full (861 characters, original 521):

> - **IF** a noun phrase in a definitional, characterization, or causal/etiologic context denotes an **abnormal clinical or pathological state**—even when its head is a generic state/process/symptom noun rather than a canonical disease label—**THEN** annotate it as **DiseaseClass**. **Scope the exclusion narrowly**: do **not** apply this rule to a phrase that merely names or measures a normal biological process, a molecular/substance entity, level, or activity as such, or that states an isolated descriptive finding—**and only when** that phrase is **not** presented as a pathological condition of the patient/disorder. A phrase that presents a deficient, reduced, absent, or otherwise abnormal state of such an entity **as** a pathological condition of the patient/disorder **remains covered** by this rule, even when its head names a molecule or a process.

(The em dashes above are part of the verbatim prompt text.) The rewrite targets two scope defects of the original clause: (1) the qualifier "not presented as a pathological condition" originally modified only the last alternative, and now constrains all alternatives; (2) pathological deficient/reduced/absent states are explicitly pulled back into coverage (without naming norrin/FALDH, to avoid writing the answer into the rule).

**Fixed items**: guidelines_before (iteration_02 state), the CONSTRAINT verified-examples block, the same 10 development documents (seed 42), the same model configuration (Azure eastus2-gpt-5.4, reasoning high), the same loop scorer and clustering function. Exclusion examples were not hand-edited at all; they are fully model-generated (kept separate from P1's "delete" arm, so the two kinds of change can be distinguished).

**Three-arm comparison**: original (clause as saved, from the saved snapshot), P1 (clause deleted, from [p1/result.json](../p1/result.json)), P2 (this run).

## 2. Guideline text comparison

| Location | Original Round 3 | P1 truncated | P2 scoped rewrite |
| --- | --- | --- | --- |
| FALDH exclusion | Flat "Do not annotate" (lines 41 to 44) | Conditional ("only a functional or mechanistic description") | Conditional ("used as a biochemical characterization rather than as a standalone pathological condition mention", lines 44 to 47, 246) |
| abnormal retinal vascular development | No exclusion example | **New** conditional exclusion | No exclusion example |
| norrin | None (added only at R4) | None | None |
| Guideline length | 17,102 characters | 18,654 characters | 19,057 characters |

P2's text is closest to the design intent: exclusions are conditional, and unlike P1 it did not regenerate extra exclusion examples. See [guidelines_candidate_scoped.txt](guidelines_candidate_scoped.txt).

## 3. Annotation results (same 10 development documents, strict matching)

| State | TP | FP | FN | F1 |
| --- | --- | --- | --- | --- |
| After R2 (before R3) | 61 | 7 | 13 | 0.8592 |
| R3 original principle | 63 | 5 | 11 | **0.8873** |
| R3 P1 truncated | 62 | 7 | 12 | 0.8671 |
| R3 P2 scoped rewrite | 60 | 7 | 14 | **0.8511** |

Focal cases (gold to prediction in each state):

| Entity | Gold | After R2 | Original | P1 | P2 |
| --- | --- | --- | --- | --- | --- |
| abnormal retinal vascular development | DiseaseClass | O | O | O | O |
| deficiency of norrin | DiseaseClass | O | O | O | O |
| spasticity | DiseaseClass | O | **TP** | **TP** | **TP** |
| deficient activity of fatty aldehyde dehydrogenase | SpecificDisease | O | O | O | O |

All entity level changes of P2 relative to the original (gains are zero):

- **TP losses, 3**: exudative retinal detachment (DiseaseClass to SpecificDisease, a new reverse type error), G6PD deficient (Modifier lost), cutaneous vasculitis (SpecificDisease to DiseaseClass, the same flip as P1).
- **New FP, 2**: exudative retinal detachment labeled SpecificDisease, cutaneous vasculitis labeled DiseaseClass.

P2 error clusters (14 total): S to O 3, S to D 3, D to O 2, S to M 2, span 1, D to S 1, C to O 1, M to O 1.

## 4. Combined verdict across the three arms (P0-P1-P2 series conclusion)

1. **The exclusion examples are not the proximate cause of the misses.** Under all three restriction texts (original / deleted / scoped rewrite), the three focal misses came out exactly the same. P2 does not even contain an exclusion example for abnormal retinal vascular development, and it is still missed. The guideline's exclusion examples that contradict gold are a **symptom** of the model's upstream judgment, not the cause: in these definitional/characterization contexts the model does not read the phrases as disease mentions in the first place, and rule wording cannot change that judgment.
2. **The restrictive clause's real function is a precision guardrail.** Deleting it (P1) doubled S to D type errors (2 to 4). Keeping but rewriting it (P2) brought no improvement this round and introduced new losses. Of the original 0.8873 gain, the spasticity fix comes from the first half of the principle, and the rest of the gain partly comes from the second half suppressing DiseaseClass over-expansion.
3. **Read "P2 worse than P1" with caution.** Of P2's three TP losses, the cutaneous vasculitis flip matches P1 (possibly driven by a shared tendency of this guideline family), but the losses of exudative retinal detachment and G6PD deficient are single samples; the gap between 0.8511 and 0.8592/0.8671 is partly within annotation noise (SD 0.009 to 0.015). The safe statement: P2 recovered no focal case and showed no overall gain.
4. **Implication for the main research line.** To get "deficiency of X / pathological deficiency state" cases annotated, the rule-wording road is basically closed by three arms of evidence. Options: a) write more specific language patterns into the principle (for example, "annotate as DiseaseClass when deficiency/absence of [molecule] appears in a results in / characterized by frame") and test in a new round; b) positive example demonstrations (effective, but that is the hard-coding path, in tension with the goal of avoiding example dependence; the trade-off must be made explicit); c) accept that such cases need the CONSTRAINT/rationale channel rather than rule text. Before choosing, return to the boundary that "guideline improvement should include modifying and deleting original rules, not only appending gold examples".
5. **Limitations**: each arm is a single rerun; guideline candidates are single generation samples; annotation noise was not measured per arm.

## Verification record

- Reproduce with: `python todo-temp/p2/run_p2.py` (requires the Azure 5_4 configuration in .env; the candidate guideline and per-document annotations are checkpointed, so an interrupted rerun does not spend API calls twice).
- Artifacts: [prompt_scoped.txt](prompt_scoped.txt), [principle_original.txt](principle_original.txt), [principle_scoped.txt](principle_scoped.txt), [guidelines_candidate_scoped.txt](guidelines_candidate_scoped.txt), [annotations_scoped.json](annotations_scoped.json), [result.json](result.json).
- Original data come from the saved snapshot iteration_03/snapshot.json (SHA-256 in the [P0 report](../p0/20261006_round4_p0_report.md)); P1 data come from [p1/result.json](../p1/result.json).
