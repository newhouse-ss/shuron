# Clause-ablation test: design after an independent review (2026-11-03, not run)

The first draft of the clause-ablation test would not have removed the rule it meant to test, so it was withdrawn; this note keeps the corrected design and the decisions still open. Nothing here has been run, and no API was called.

## Question the test answers

The error analysis found that the Modifier rule for "history of"-type positions lines up with the new Modifier mislabels (report §4.2, §4.3), but no run has removed the rule and re-annotated. The test asks two separate questions:

- **Is the rule needed for the errors?** Remove it from a refined guideline and count the mislabels again.
- **Can the errors be removed without losing the gains?** The same guidelines label more gene-noun Modifiers correctly (report §4.1). If removing the rule also removes those gains, one rule causes both, which answers the professor's question of why one change hurts Specific and helps Modifier.

Terms used below:
- **Post-phrase position:** a gold mention right after a relational noun plus "of" or "with", such as "history of", "risk of", "patients with", as matched by the regex in `scripts/modifier_subset.py`. Validation has 71 such mentions whose gold label is not Modifier (report §4.2 table).
- **Gene-noun Modifier:** a gold Modifier right before a gene, protein or locus noun, as in "the DTD gene". Validation has 99; the original guideline labels 37.8 of them correctly per run (report §4.1).

## The first draft failed because the rule appears in six places

**In top-4 loop07 the rule is not confined to the second half of line 65, so deleting that half leaves it in force.** The first sentence of line 65 already reads "A disease name that premodifies, or is the complement of, a context or population noun (such as cases, population, history, risk, or incidence) is annotated Modifier." The same assignment is repeated at lines 66, 94, 112 and 235 of `outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop07/final/final_guidelines.txt`. top-4 loop06 states its version in at least five places. A deletion that left the general rule standing would most likely show no change, and that result could not be read.

A 10/17 test had a similar shape: deleting the two places in the R3 guideline that named FALDH fixed 0 of 5 FALDH annotations, and a general exception rule at R3 line 12 was the suspected second block, never tested (PROGRESS, 10/16 Todo). That ran on an earlier model and is cited only as a design lesson.

## Corrections the review required

**Each correction closes a way a skeptic could explain the result without the rule.**

- **Remove the rule, not a sentence.** For top-4 loop07, delete the complement-position assignment in all six spans (about 1% of the text) and keep the premodifier rule and the gene rule word for word. Freeze the diff and its hash, and check offline that no remaining sentence assigns Modifier after a context noun plus "of" or "with".
- **Compare with a fresh run of the unchanged guideline.** The guidelines and documents were chosen because the error showed up in one run, so a re-run would show fewer errors even with no edit. The unchanged guideline must run in the same batch, with the same documents and repeats. Choose documents by text and gold only.
- **Give every arm and repeat a new run name.** The runner reuses a saved reply when the run name, task, prompt and occurrence match (`reproduction/haiku_batch_loops.py:322-336`), so a re-run under the old name would silently return the 10/23 reply. Confirm zero reused replies before counting.
- **Count all non-Modifier gold labels at the post-phrase position.** Most of the family-history mentions are DiseaseClass or CompositeMention, not Specific, so a Specific-only count misses most of the errors.
- **Add the reverse direction.** Insert loop07's rule into the original guideline. The original states nothing similar, so this arm changes exactly one thing, and it tests whether the rule produces the errors on its own.
- **Fix the decision rules before sending.** "Back to the original level" has no threshold, since the original level is almost zero. "Gains unchanged" cannot be shown by a non-significant difference, so it needs a stated margin.

Annotating only some documents does not change what the model sees: each validation document is a separate call holding only the guideline and that document (`src/llm_guideline_moderation/pipeline.py:83-120`).

## Corrected design

**Four arms on fixed documents, five repeats each, all in one batch.**

| Arm | Guideline | Documents |
| --- | --- | --- |
| Unchanged | top-4 loop07 final, as is | post-phrase documents plus every document with gene-noun or people/risk premodifier gold Modifiers |
| Rule removed | top-4 loop07 with the six spans deleted | same |
| Original | original guideline | post-phrase documents |
| Original plus rule | original with loop07's lines 65 and 66 inserted | post-phrase documents |

- **Main count:** per run, how many of the 71 post-phrase non-Modifier gold mentions are labelled Modifier.
- **Gain checks:** correct gene-noun Modifiers, and correct premodifier Modifiers before people and risk nouns.
- **Reported but not decided on:** BRCA abstracts versus other documents; the nouns line 65 lists versus person nouns, which line 65 does not list.
- **Size:** the reviewer counted 35 post-phrase documents and 79 documents for the larger set, giving 1,140 calls. At the measured ¥0.63 to ¥1.09 per call (PROGRESS, 10/22 cost records), that is about ¥720 to ¥1,090, close to the ¥1,000 point where the administrator must be told. These document counts come from the reviewer's inline recount and must be regenerated by a saved script before approval.

Decision rules proposed by the reviewer; the thresholds are proposals, not derived, and must be set before any run:

- **Gate:** the unchanged guideline must reproduce the error (at least 10 post-phrase mislabels per run). Otherwise stop and report that the single run's 24 was mostly noise.
- **Rule needed:** the share of the excess removed, (unchanged minus removed) / (unchanged minus original), is at least 0.7, with a document-level bootstrap lower bound of at least 0.5.
- **Gains survive:** the lower bound of (removed minus unchanged) on gene-noun Modifiers is above −8 mentions. If the fresh unchanged run gains fewer than 10 over 37.8, this question has no answer.
- **Rule enough alone:** original plus rule recovers at least half of the excess, with a lower bound above zero.

## Whether to run it, and in what form

**Whether the rule is needed for the errors is already well supported; only the gains question could change the next step.** The 7 guidelines that wrote the rule made the error and the other 4 did not, and the saved reasons of all 24 loop07 errors cite the rule (`outputs/cited_sections_output.txt` B). If removing the rule also removes the gene-noun gains, narrowing the rule in the refinement prompt would cost those gains, which favours letting refinement check against dev gold instead.

The reviewer's preferred version runs the unchanged and rule-removed arms on about 40 unused training documents (about 400 calls). It leaves validation untouched and covers diseases other than breast and ovarian cancer, so it partly separates disease name from document topic. Those documents must be marked as used afterwards.

What any version cannot show: a gain for a method; that the loop can be stopped from writing the rule; a ranking of the upstream fixes; results for the other five guidelines, other models or other topics.

## Open decisions

- Validation documents or unused training documents.
- The four thresholds above.
- Whether to add top-1 loop05, whose rule is only a pointer to a section that does not contain it (lines 63 and 268), making it the cleanest single edit.
- Budget approval; nothing runs before it.

## Verification record (核查记录)

- Reviewer: one read-only statistics-focused agent, 2026-11-03; no files written, no API calls, no held-out gold read.
- Checked by hand after the review: loop07 lines 65, 66, 94 and 112 (quoted above); the reply-reuse key in `reproduction/haiku_batch_loops.py:322-336`.
- Counts taken from saved artifacts: 71 and 99 mentions, 37.8 per run (report §4.1, §4.2); 24 cited reasons (`outputs/cited_sections_output.txt` B).
- Counts not yet in a saved artifact: 35 and 79 documents, 1,140 calls, the training-pool counts. Regenerate them with a script in stage 0.
