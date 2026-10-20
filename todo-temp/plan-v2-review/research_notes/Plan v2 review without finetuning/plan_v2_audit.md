# Plan v2 audit: number tracing, and what changes once S1 (fine-tuning) is dropped

All paths are relative to the repository root `H:\Git\research\修論\llm-guideline-moderation-source`. Short names used below: **v2** = `docs/RP/20261020_research_plan_v2.md`; **v2zh** = `docs/RP/20261020_research_plan_v2_zh.md`; **v1** = `docs/RP/20261020_research_plan_to_draft.md`; **report** = `todo-temp/direction-scan/20261019_direction_research_report.md`; **offline** = `todo-temp/direction-scan/offline_direction_checks_output.txt`; **cost** = `todo-temp/direction-scan/plan_v2_cost_output.txt`; **breakdown** = `todo-temp/meeting-20261020/error_breakdown_output.txt`; **P4** = `todo-temp/p4/20261007_p4_devsize_report.md`; **P3** = `todo-temp/p3/20261007_p3_topk4_report_en.md`; **helper** = `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/audit_helper_output.txt` (new offline computation made for this audit, script `audit_helper.py` in the same folder); **base paper** = `archive/references/backbone-research.pdf` (public as arXiv 2605.20809; the local copy is headed "Anonymous ACL submission"; line numbers below are the paper's own margin numbers). "L" means line. Scoring words: "strict" is valid100 PubAnnotation exact span and subtype; "one-type" is exact span with the four subtypes collapsed; "dev F1" is the loop's set scoring on development documents.

## 1. Does each key number in plan v2 trace to the artifact it cites?

### Takeaway
Almost every number matches its artifact exactly. The exceptions are small but real: the S4 call count does not match the S4 design (230 budgeted, 260 described), the "cancer patterns 3 to 16" had no saved artifact (I reproduced it, but only under one of two reasonable definitions, and the same R4 guideline gives 7 and 16 in two passes), the loop-final hashes only match a whitespace-stripped convention that v2 does not state, the v1 cost range uses a different price basis than v2's, and the stated 0.024 / 0.028 detectable differences ignore the Holm correction that v2 itself prescribes.

### Cited Findings

**Summary and section 2 evidence table**

| Item (v2 location) | v2 value | Artifact and line | Artifact value | Status |
| --- | --- | --- | --- | --- |
| Top-4 strict F1 ([v2 L9](docs/RP/20261020_research_plan_v2.md)) | 0.8023 | [offline L6](todo-temp/direction-scan/offline_direction_checks_output.txt); [breakdown L54](todo-temp/meeting-20261020/error_breakdown_output.txt) | 0.8023 | match |
| Top-1 dev30 strict F1 (v2 L9) | 0.8050 | offline L8; breakdown L80 | 0.8050 / 0.805 | match |
| Original guideline (v2 L9) | 0.7792 | offline L3; breakdown L2 | 0.7792 | match |
| Top-4 minus original (v2 L10, L43) | +0.023 [−0.019, +0.068]; +0.0231 [−0.0192, +0.0683] | offline L88 | +0.0231 [−0.0192, +0.0683], P 0.846 | match with offline. **Minor mismatch with the second cited source**: [P4 L50](todo-temp/p4/20261007_p4_devsize_report.md) gives [−0.0197, +0.0685], P 85.6% (different bootstrap script, `todo-temp/p4/bootstrap_valid.py`) |
| dev30 minus original (v2 L43) | +0.0258 [−0.0006, +0.0546] | P4 L49 | +0.0258 [−0.0006, +0.0546], 97.1% | match |
| Same guideline twice (v2 L11, L44) | 0.009; 0.7878 and 0.7789 | offline L4, L5, L14 | 0.7878, 0.7789, abs diff 0.0089 | match |
| Four unscored loop finals (v2 L45, L94) | top-1 run 3; top-4 runs 1 to 3; hashes a1311085152b, 5f5300a5811b, 5a2ddf57a5c7, cc7bb3416f86 | `outputs/ncbi_disease/20260902_*/final/final_guidelines.txt`; no matching valid run in `outputs/ncbi_disease/` or `reproduction/results/` (directory listings, 10/19) | hashes match only as SHA-256 of the text with surrounding whitespace stripped; the raw-file SHA-256 prefixes are e43b2281a438, b4be926b13a7, be10332da0e9, e796b5e8b1d0 | match under an unstated convention ([v2 L352](docs/RP/20261020_research_plan_v2.md) and [report L277](todo-temp/direction-scan/20261019_direction_research_report.md) only say "hashed 10/19") |
| Top-1 runs 1 and 2 ended at the original guideline (v2 L95) | | same files | both finals are 7,367 characters with stripped hash e6232d944d68, the original's hash | match |
| Original guideline hash ([v2 L194](docs/RP/20261020_research_plan_v2.md)) | e6232d944d68 | `data/guidelines/ncbi_disease_guidelines.txt` | raw SHA-256 e6232d944d68 (file has no trailing newline) | match |
| Round 4 kept by noise (v2 L46, L145) | 0.9091, 0.8811 | [`todo-temp/r4-nontarget/20261015_r4_nontarget_report.md` L10, L51 to L53](todo-temp/r4-nontarget/20261015_r4_nontarget_report.md) | 0.8873 (R3), 0.9091 (R4 saved), 0.8811 (R4 with rerun values) | match. These are dev F1 (loop scoring) but the v2 L46 row does not say so, while every other row in the table is valid100 strict |
| Subtype "if fixed" (v2 L47, L129) | +0.073 | breakdown L64 | label mismatch fixed 0.8750 (+0.0727), 57 errors | match. It covers all 57 subtype errors, not only S/D; breakdown L69 and L71 give +0.0344 (gold SpecificDisease only) and +0.0319 (gold DiseaseClass only) |
| Same-span S/D confusions (v2 L47) | 34; 20 against training precedent | offline L53, L94 (topk4 19 + 15) | 34; 20 / 1 / 13 | match. Note breakdown L59 counts 42 S/D label mismatches (21 each way, any overlap), the figure v1 used ([v1 L38](docs/RP/20261020_research_plan_to_draft.md)); the two counts measure different things |
| S/D confusions across guidelines (v2 L48, L130) | 14 to 58 | offline L94 | dev30 8+6 = 14; noTP 39+19 = 58 | match |
| Cancer patterns (v2 L48) | 3 to 16 | report L95 and [report L278](todo-temp/direction-scan/20261019_direction_research_report.md) ("ad hoc query ... regex in this report's section 3.2"); no regex or output is saved | not found in any saved artifact. Reproduced by [helper section 3](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt): original 0 S→D + 3 D→S = 3; top-4 8 + 8 = 16, **only if** "stage III cancers" and "sporadic renal cell carcinomas" count; with bare words only, 2 and 15 | not found; now reproducible under a stated definition |
| Vote of 8 runs (v2 L14, L49) | 0.8158; +0.0366 [+0.0059, +0.0699] | offline L21, L93 | 0.8158; +0.0366 [+0.0059, +0.0699], P 0.990 | match |
| Review curve (v2 L15, L50) | 20% / 30%: 0.887 / 0.911; random 0.834 / 0.850 | offline L34, L35 | 0.8868 / 0.9109; random 0.8343 / 0.8500 | match |
| One extra run (v2 L50) | 0.869 / 0.881 | offline L98 (C2, m=1) | 0.8686 / 0.8805 | match (0.8805 shown as 0.881). The "one extra run" is a random run with a *different* guideline; a second pass of the *same* guideline gives 0.8507 / 0.8634 (offline L43, L44) |
| Label propagation (v2 L51, L283) | −0.039 / +0.001 | offline L71 | harmonize −0.0390; add only +0.0010 | match |
| Lexical precedent (v2 L51, L284) | +0.017 with 563 docs | offline L85 | 0.8189 vs base 0.8023 (+0.0166) | match |
| Stable wrong entities (v2 L180) | 31 | offline L30, L31 | 481 entities in all 7 other runs, 31 wrong | match |
| Missed Modifier (v2 L282) | 40 to 27 | breakdown L35 (R4), L61 (top-4) | 40, 27 | match |
| One-type F1 (v2 L36) | 0.8546 | breakdown L56 | 0.8546 | match |
| Contradicting examples in top-4 (v2 L111) | 2 | [P3 L13](todo-temp/p3/20261007_p3_topk4_report_en.md) | exactly 2 | match |

**Section 6.3 statistics**

- SD 0.0123 of the 8 strict F1 values: the 8 values are offline L3 to L10; recomputed SD (ddof 1) is 0.0123, mean 0.7855 ([helper section 2](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)). Match.
- Detectable 0.024 (4 loops) and 0.028 (3 loops) with 2.80 × √(2·SD²/n) ([v2 L220](docs/RP/20261020_research_plan_v2.md), L352): recomputed 0.0245 and 0.0282 at two-sided alpha 0.05 (helper section 2). Match as arithmetic.
- But v2 L212 to L216 makes the four primary comparisons Holm-corrected. At Holm's first step (alpha 0.05 / 4 = 0.0125) the same formula gives 0.0291 (4 loops) and 0.0337 (3 loops) (helper section 2). The stated detectable differences therefore do not match v2's own testing rule.
- The SD comes from 8 single passes of 8 different guidelines, not from loops of one method; the report says this "overstates the spread of one method, but it is the only planning value available" ([report L47](todo-temp/direction-scan/20261019_direction_research_report.md)).

**Section 8 budget and other cost figures**

| Item | v2 | Artifact | Status |
| --- | --- | --- | --- |
| Per call: input 4,834, output 22,551 / 36,459, Global prices (v2 L238) | | `todo-temp/direction-scan/plan_v2_cost.py` L4 to L6, L12 to L14; recomputed ¥55.39 / ¥88.37 per call (helper section 6) | match |
| S2a 400 calls ¥22,154 to ¥35,346; S2b 200 ¥11,077 to ¥17,673; S3 208 ¥11,520 to ¥18,380; S6 300 ¥16,616 to ¥26,510; S5 786 ¥43,533 to ¥69,456 (v2 L243 to L248) | | [cost L2 to L7](todo-temp/direction-scan/plan_v2_cost_output.txt) | match |
| S4 230 calls ¥12,739 to ¥20,324 (v2 L140, L247) | | cost L6 ("pilot on dev30 (1 repeat, 30 docs) then valid100 on 2 saved passes") | **mismatch with the S4 design**: v2 L135 to L138 describe two variants, "30 calls per variant", plus 200 validation calls = 260 calls, ¥14,400 to ¥22,975 (helper section 6). Conditional and "all" totals are 30 calls (about ¥1,660 to ¥2,650) short |
| Core 1,108 calls ¥61,367 to ¥97,909; all 2,124 ¥117,639 to ¥187,689 (v2 L250, L251; summary L20) | | cost L9 to L11 | match (given the S4 count above) |
| S2 "600 calls, ¥33,000 to ¥53,000" (v2 L104) | | 22,154 + 11,077 = 33,231; 35,346 + 17,673 = 53,019 (cost L2, L3) | match |
| v1 "¥170,000 to ¥310,000" (v2 L20, L312) | | [`todo-temp/meeting-20261020/plan_cost_output.txt`](todo-temp/meeting-20261020/plan_cost_output.txt): Global mean ¥174,133 to **Data Zone** max ¥305,605 | number matches v1 ([v1 L15](docs/RP/20261020_research_plan_to_draft.md)), but the **price basis differs**: v2's ranges are Global only. On a Global-only basis v1 arms 1 to 4 are ¥174,133 to ¥277,822 (same file) |
| S6 300 calls (v2 L162 to L166) | | cost L5 | match for annotation only. If S4 enters the frozen pipeline (v2 L162), its typing calls on the test split are not budgeted |
| 5.9 hours per validation pass (v2 L234) | | P3 L151 ("100/100 documents complete (about 5.9 hours ...)") | match |

**Literature numbers in v2 section 1.2 and 11 that I could check locally**

- Base paper DeepSeek 0.55 / 0.56 on NCBI ([v2 L279](docs/RP/20261020_research_plan_v2.md)): base paper Table 1, NCBI (791), DeepSeek G 0.55, M 0.56. Match.
- Human agreement "about 0.875" (v2 L175): base paper Appendix A, margin L708 to L710: "The NCBI Disease corpus reports an inter-annotator agreement of approximately 87.5% for disease mention annotation (Leaman et al., 2013)". Match.
- BioBERT 0.8971, PubMedBERT 0.9090, Zhao and Goto 0.897 / 0.866 (v2 L35): sources are outside the repository (report L54 to L57, L62 point to a publisher page, PMC and `../papers/Zhao.pdf`). Not checked here.

### Inferences
- The table in v2 section 2 can be presented as traced, with three fixes: label the 0.9091 / 0.8811 row as dev F1; state that the review numbers come from 7 runs of *different* guidelines; and either save the cancer-pattern query or quote the definition used.
- The cancer-pattern finding is weaker than v2 L48 and L131 suggest. Under the same definition, the R4 guideline gives 7 in one pass and 16 in its rerun, noTP gives 17 and abstraction 15 (helper section 3), and the "inheritance pattern alone" line appears only in the top-4 guideline (`outputs/ncbi_disease/20260901_gpt54-high_topk4_dev10/final/final_guidelines.txt` L12; absent from every other final, grep 10/19). So "refinement created it" and "line 12 explains it" are not separable from pass-to-pass noise with the data in hand.
- Fixing the S4 count adds about ¥1,700 to ¥2,700 to the conditional tier; it does not change the core total.

### Gaps
- The P4 and offline bootstrap scripts give slightly different intervals for the same comparison; which one the thesis will use is not decided anywhere.
- The base paper's 0.73 / 0.76 are two-decimal values with no interval, so any difference from them below about 0.005 cannot be stated.

## 2. Which parts of plan v2 depend on S1, and what can replace each without training?

### Takeaway
S1 is woven into the goal statement, RQ1, both success tables, the timeline, S6, the review-curve target, four risk rows, a meeting question, a change-log row and the deck. Each has a no-training replacement: the base paper's moderated GPT-5 (strict 0.76, same 100 documents and metric) as the same-split reference, published fine-tuned scores (up to NEEDLE 0.9228) compared in one-type F1, and human agreement 0.875 as the review-curve target. The existing valid100 data already give the review-curve crossing points for these targets. One planned claim cannot be replaced: "10 documents of refinement are worth N fully annotated documents" needs a supervised learning curve, which no repository file or cited source provides.

### Cited Findings

**Where v2 depends on S1, with a replacement for each**

| v2 location | Dependence on S1 | Replacement needing no training | Supporting data |
| --- | --- | --- | --- |
| Summary L7 (goal "close to a fine-tuned model") and L17 (Q1 "What is the fair target? A fine-tuned model on the same split and scorer, plus a learning curve") | Target defined as an S1 output | Q1 becomes "Where does the method stand against sourced reference points?" Strict four-subtype: base paper GPT-5 moderated 0.76 (P 0.82, R 0.71) on the same 100 documents. One-type: published fine-tuned scores (BioBERT 0.8971, PubMedBERT 0.9090, NEEDLE 0.9228). Human agreement 0.875 | Base paper Table 1 (NCBI (791), GPT-5, M: 0.82 / 0.71 / 0.76, TP 565); base paper Appendix A margin L708 to L710; [report L54 to L59](todo-temp/direction-scan/20261019_direction_research_report.md); NEEDLE 92.28 is from the user's message and appears in no repository file (grep for "NEEDLE" and "92.28", 10/19) |
| Summary L21 ("a fair yardstick") | S1 is the yardstick | "A sourced reference frame: published numbers with their split, type scheme and training data stated" | as above |
| §1.1 L29 (method quality "against a fine-tuned model scored on the same split and metric") | S1 | Strict F1 against the base paper's 0.76 (same split and metric); one-type F1 against published fine-tuned scores (different split unless S6 runs) | Thesis one-type: original 0.8351, R4 0.8490, R4 rerun 0.8467, top-4 0.8546, dev30 0.8455 (breakdown L4, L30, L56, L82; helper section 1) |
| §1.2 L37 ("Step S1 measures one, and the deck should present the target as 'to be measured on the same split'") | S1 | "No four-subtype supervised result exists ([report L165](todo-temp/direction-scan/20261019_direction_research_report.md)); the gap is reported in one-type F1 against published scores and in strict F1 against the base paper" | report L165 ("Supervised results with the four NCBI subtypes: None found") |
| §3 RQ1 L57 (steps S1, S2; "base paper §6.2 asks for a learning curve") | S1 | RQ1: "How far is 10-document LLM annotation from the base paper's moderated GPT-5 (strict) and from published fine-tuned scores (one-type), how does the gap split by error kind, and how does it change with development-set size?" Steps: S2, plus one-type scoring in S6 | Error kinds: breakdown L58 to L76. Development-size curve already exists: valid100 0.7878 (dev10), 0.7745 (dev20), 0.8050 (dev30), one trajectory each ([P4 L12, L30 to L32, L14](todo-temp/p4/20261007_p4_devsize_report.md)). The base paper's request is "examine the learning curve by incrementally increasing the volume of development data" (base paper §6.2, margin L518 to L520), i.e. development data for moderation, not supervised training size |
| §4 L64 (week 1 "S1 fine-tuned yardstick + learning curve") and L75 (core steps "S1, S2, S3, S6") | S1 scheduled and in core | Delete; core becomes S2, S3, S6 plus the review analysis. Use week 1 for the S2 passes, the test-split download and conversion, and a reference-frame table | v2 L227 already lists the test-split work in week 1 |
| §5 S1 L79 to L90 | Whole step | Replace with "Reference frame (no calls)": a table of reference points with settings | Same sources as row 1 |
| §5 S6 L164 ("The S1 models") | S1 output | Score the same S6 passes also in one-type F1 for comparison with published test-split scores | v2 L210 already plans one-type F1 "for comparison with the literature" |
| Review-effort curve L175 ("the share needed to reach the S1 fine-tuned score and the human agreement level") | S1 score is one of two targets | Targets: human agreement 0.875 (strict); published one-type levels 0.897, 0.909, 0.9228 (one-type curve); the 0.9606 bound | On valid100 ([helper section 4](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)): strict 0.875 is first reached at 17% of entities checked with 7 other runs as the signal (random order 46%, wrong-first 9%), and at 39% with one same-guideline rerun (random 50%). One-type, top-4 with 7 other runs: 0.897 at 16%, 0.909 at 22%, 0.9228 at 32%. One-type, R4 with its rerun: 0.875 at 10%, 0.897 at 35%, 0.909 at 47%, 0.9228 at 63%. The helper reproduces the saved 10/20/30% values exactly (offline L33 to L35, L42 to L44) |
| §6.2 L206 (training split "Fine-tuning only (S1)") | S1 | "Not used by any new step; already used offline for precedent and dictionary reference points" | offline L50, L75 to L85 (training gold used in sections D and F) |
| §7 L227 (week 1 "S1 implementation and training") and L231 (week 5 "S1 models on test") | S1 | Week 1: drop S1. Week 5: one-type scoring of the S6 passes | |
| §8 L242 (S1 row, 0 calls) | Budget row | Delete; totals do not change (S1 had 0 calls, cost L1) | cost L1, L9 |
| §9 L259 (RQ1 success: "A fine-tuned four-subtype score on the same split with an interval, and the document count at which it matches the LLM"; reported: "Learning curve") | S1 | Success: thesis strict F1 with a paired interval against the base paper's 0.76, and one-type F1 against published scores, with the gap split by error kind. Reported in any case: the development-size curve (P4) and error breakdown | P4 L27 to L33; breakdown L58 to L76 |
| §9 L261 (RQ3 success: "reach the S1 score and the human-agreement level") | S1 | "The share of entities to check to reach 0.875 (strict) and the published one-type levels" | helper section 4 |
| §10 L267 (budget fallback "S1 (free), S2a, S3") | S1 as the free fallback | "S2a, S3; reference frame and review curve on existing passes (free)" | The review curve already exists for 8 saved runs (offline section C) |
| §10 L269 (GPU not available) | S1 only | Delete | |
| §10 L273 (fine-tuned model far above the LLM, claim becomes "worth N annotated documents") | S1 | "Published fine-tuned scores far above the LLM: the claim becomes the review-effort curve plus the strict comparison with the base paper's setting" | helper section 4 |
| §12 Q2 L293 | Asks whether S1 is the right yardstick | "Is comparing our strict F1 with your 0.76 on the same 100 documents, and our one-type F1 with published fine-tuned scores, an acceptable yardstick without training a model? Have you seen four-subtype supervised numbers?" | |
| §13 L307 ("(absent) / S1 fine-tuned yardstick and learning curve / The target number had no source") | S1 | "(absent) / sourced reference frame: base paper 0.76, published one-type scores, human agreement 0.875 / The target number had no source; training is out of scope" | |
| Deck outline L318 (slide 3 target check), L324 to L326 (RQs, steps, success) | Implicitly S1 | Slide 3 shows the reference table; slides 9 to 11 drop S1 | |

**Related places outside v2 that also name the fine-tuned yardstick**

- [report L8](todo-temp/direction-scan/20261019_direction_research_report.md) ("the fair target has to be measured: a fine-tuned model ..."), L16 to L19 (conclusion 6, "fix the yardstick"), L176 (direction 1, "Do first"), L243 (question 2).
- [`PROGRESS.md` L153](PROGRESS.md) ("Plan v2 starts with a fine-tuned yardstick on the same split").
- `OVERVIEW.md` L11 still states BioBERT 0.86 as the user-set target and says a formal comparison needs the same split and scoring ([OVERVIEW L11](OVERVIEW.md)).

### Inferences
- The strongest same-split, same-metric reference without training is the base paper's GPT-5 row, but the thesis already exceeds it with GPT-5.4 (original 0.7792 against the base paper's 0.73 original and 0.76 moderated), so it works as a floor and a reproduction check, not as a target.
- Published one-type scores are the only "SOTA" numbers available. They differ from the thesis's one-type F1 in split (test versus valid100) and in evaluation unit (sentence or token level in the literature, as the report notes at L57 for Zhao and Goto and L34 for collapsing subtypes). Running S6 would remove the split difference but not the format difference. They should be shown as orientation, with settings next to each number. NEEDLE's 0.9228 also uses weak labels in addition to gold (user's message), which is one more setting to state.
- The review curve is where the replacement targets are most useful: with gold standing in for the expert, the existing data already say how many checks reach 0.875 or 0.897. The planned design (two passes of the same guideline, v2 L170, L162) behaves like the R4-with-rerun curve (0.875 strict at 39%), not like the 7-run curve (17%) that v2 L15, L50 and L309 quote.
- Dropping S1 removes the only step that needed a GPU and Codex implementation time in week 1, so the S2 passes (the slowest item, about 5.9 hours per pass when run in sequence, P3 L151) can start earlier.
- "Worth N annotated documents" cannot be replaced. The nearest existing evidence, string-memory baselines (dictionary from 563 training documents: strict 0.4504, offline L75; precedent relabeling from 10 to 563 documents: 0.8028 to 0.8189, offline L81 to L85), measures naive reuse of gold strings, not a trained model. Using it as a substitute would mislead.

### Gaps
- No repository file gives a learning curve for fine-tuned models on NCBI Disease; whether such a curve exists in published work was not checked (out of scope: local files only).
- Whether the 87.5% agreement is a strict four-subtype figure or a span-level figure is not stated in the base paper passage; Leaman et al. 2013 is not in the repository. This decides whether 0.875 belongs on the strict or the one-type curve.
- The NEEDLE figure and its setting come only from the user's message.

## 3. Is valid100 the base paper's NCBI evaluation set, and is 0.7792 comparable to the base paper's 0.76?

### Takeaway
Valid100 is, with strong evidence, the base paper's NCBI evaluation set: the authors' own released data, the full 100-document NCBI development split, with the same 791 gold mentions. But 0.7792 is the thesis's *original guideline* score and should be set against the base paper's original-guideline 0.73; the base paper's 0.76 is the *moderated* score, whose thesis counterpart is R4 (0.7878 and 0.7789). Data and metric match; the model does not (GPT-5.4 high against GPT-5), so these are reference points, not a method comparison.

### Cited Findings
- The base paper sampled "a minimal set of 10 documents from the original training split" for moderation and "a larger set of 100 documents from the original development split as our evaluation dataset. For NCBI Disease and BioRED, we used their respective development splits in full, as both contain exactly 100 documents" (base paper §4 setup, margin L347 to L356). It "intentionally withheld the original test sets ... for future benchmarking" (margin L359 to L363).
- This repository is the base paper's artifact release, with "train and valid PubAnnotation datasets for BC5CDR, BioRED, and NCBI Disease" and the evaluation project `ncbi-valid` ([`README.md` L3 to L10, L60 to L66](README.md)).
- The shipped NCBI valid gold has 791 entities, equal to the `#Entity` of Table 1 ([`reproduction/README.md` L65 to L71](reproduction/README.md)); base paper Table 1 heads the NCBI block "NCBI (791)".
- The local valid set has 100 documents, 791 gold mentions, `sourcedb` PubMed, and no `sourceid` overlap with the 593 training documents ([offline L2](todo-temp/direction-scan/offline_direction_checks_output.txt); [helper section 1](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)).
- Base paper Table 1, NCBI, GPT-5: guideline (G) P 0.78, R 0.68, F1 0.73, TP 540; moderation (M) P 0.82, R 0.71, F1 0.76, TP 565, 3 iterations. The user's figures (P 82, R 71, F1 76) match the M row.
- Thesis, GPT-5.4 high, valid100 strict: original guideline P 0.8011, R 0.7585, F1 0.7792, TP 600; R4 (base method, dev10, 4 rounds) P 0.8121, R 0.7649, F1 0.7878, TP 605; R4 rerun F1 0.7789, TP 597 ([breakdown L2, L28](todo-temp/meeting-20261020/error_breakdown_output.txt); helper section 1; [P4 L30](todo-temp/p4/20261007_p4_devsize_report.md) for 4 rounds).
- Same metric: in the moderation step the base paper computes F1 "based on a strict matching criterion, which requires exact match of both the entity" span and type (margin L210 to L213), and it describes its held-out evaluation as "strict span-and-type performance on held-out data" (margin L568 to L569). The thesis scorer reuses the upstream evaluator `evaluate_pubannotation_pairs`, and the README says to report the `pubannotation` number because it is the paper's counting convention ([`reproduction/README.md` L79 to L94](reproduction/README.md)). NCBI has no duplicate denotations, so the two strict implementations agree on NCBI (same file, L87 to L90).
- Development sample: the thesis dev10 is a seed-42 random sample of 10 training documents (`reproduction/dev_splits/ncbi_disease_dev10.json`; 08/02 run config `sample_size 10`, `seed 42`); the released spec also samples 10 training documents at random with seed 42 and `"model": "gpt-5"` (`experiments/ncbi_disease_valid_round1.spec.json`). The paper text says only "randomly sampled".
- The project already decided not to pool these numbers: "中期 abstract 报告 ... 0.73 至 0.76。后续本地 GPT-5.4 记录为 0.7792 至 0.7878 ... 这些来源及批次不同，不混成一组比较" ([`PROGRESS.md` L38](PROGRESS.md)).
- The model field returned by the deployment is the deployment name `eastus2-gpt-5.4`, so the exact model version of past runs cannot be recovered ([`PROGRESS.md` L212](PROGRESS.md)).

### Inferences
- Like for like: thesis G 0.7792 against base paper G 0.73 (about +0.05, the base value being rounded); thesis M (R4) 0.7878 / 0.7789 against base paper M 0.76. The model change alone is associated with a larger gain than the base paper's own G to M step (+0.03) and larger than any refinement gain the thesis has established.
- So "the base paper's 0.76" is a fair same-data, same-metric reference, but a thesis result above it does not show the refinement method is better; it shows GPT-5.4 high is stronger on this set.
- The thesis dev10 may be the same 10 documents the released code would draw (same seed and sample size), but nothing shows the paper's runs used that draw.

### Gaps
- No document-ID list from the official NCBI corpus is in the repository, so identity with the official development file is shown through the authors' release and the 791 count, not through an ID-by-ID match.
- The local PDF is the submission version; whether the arXiv or ACL camera-ready Table 1 differs was not checked.
- The base paper's GPT-5 reasoning setting for Table 1 is not stated in the passages read (Table 2 shows "Reason" 0.73 for GPT on NCBI, which equals the G value in Table 1).

## 4. Are the user's inline annotations in plan v1 addressed in plan v2?

### Takeaway
v1 holds two inline annotations, and v2 answers both. The answer to the first is partial: S3 still sends the development gold label of each flagged string to the rewrite step, and v2 drops the input-side gold direction that the 10/09 seminar had endorsed without flagging that change for the meeting.

### Cited Findings
- Only two annotations exist in v1. A search for CJK characters finds them at [v1 L134](docs/RP/20261020_research_plan_to_draft.md) and v1 L169; the other matches are the heading 核查记录 (L240) and a path containing 修論 (L255).
- Annotation 1, on arm 3 (gold given to Guideline Refinement): "（肯定不可能直接给，相当于直接告诉模型答案了）" (v1 L134). v2 response: S3 "uses gold only as a check, never as writing material, which answers the concern in v1's inline comment on arm 3" ([v2 L109](docs/RP/20261020_research_plan_v2.md)); arm 3 is "Merged into S3: gold as a check, not as material" (v2 L281, L306). The report separates leakage (no) from hard-coding (a real risk) ([report L216 to L220](todo-temp/direction-scan/20261019_direction_research_report.md)).
- But S3 step 2 sends the rewrite call the conflict text "this example says do not annotate X; development gold annotates X as SpecificDisease", with the instruction "do not add the string as an example" (v2 L112), and then measures copied share (v2 L113, L118).
- The 10/09 seminar endorsed two directions: gold injected at the refinement stage (input side) and a written-rule conflict check (output side) ([`PROGRESS.md` L78](PROGRESS.md); still open as 方案 A and 方案 B at L188, L189).
- Annotation 2, on the Track 2 prerequisites: "（不能用当前的Pro订阅来做吗？ ）" (v1 L169). v2 response: a pilot "can run through Claude Code non-interactively on the subscription"; validation numbers should come from the API with a fixed model ID, or the Claude Code setting must be reported as a limitation; terms of use to be checked; the reviewer runs in a fresh process (v2 L185). The report gives the reasons (system prompt and tools added by Claude Code, no sampling control, no per-call usage, rate limits) ([report L221 to L228](todo-temp/direction-scan/20261019_direction_research_report.md)).

### Inferences
- Annotation 1 is addressed in spirit: gold is used after writing, not as writing material. In practice S3 does show the rewrite step one gold label per flagged string. That is a narrow, development-only use, but the user's objection was exactly about showing gold to the rewrite step, so the plan should say this openly and let the user decide.
- Putting input-side gold (方案 A) out of scope reverses a seminar-endorsed direction. This is a decision for the meeting (the user, Prof. Goto), not something v2 should settle silently.
- Annotation 2 is fully addressed.

### Gaps
- v1 is untracked in git (git status at session start lists it as `??`), so whether v1 is "kept unchanged" (v2 L3) cannot be checked against history.

## 5. Do the English and Chinese versions of plan v2 differ in any number?

### Takeaway
No. The two files are line-aligned (357 lines each), and every line carries the same numbers. Six lines differ in digit tokens, all because of wording.

### Cited Findings
- [Helper section 5](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt) compares the numbers on each line of [v2](docs/RP/20261020_research_plan_v2.md) and [v2zh](docs/RP/20261020_research_plan_v2_zh.md). Differences:
  - L3: v2zh adds "英文版为同目录下的 `20261020_research_plan_v2.md`，两者内容一致" (a file name, not a result).
  - L65: v2 "2nd pass" against v2zh "第二次标注".
  - L72: v2zh "12 月初" against v2 "early December".
  - L259, L305, L345: v2zh repeats "F1" once more in the sentence.
- Wording checked by eye on the lines with key claims: v2 L35 "which may be where 0.86 came from" against v2zh L35 "0.86 可能来自后者" (the latter = BC5CDR 0.866). The meaning agrees with the report ([report L62](todo-temp/direction-scan/20261019_direction_research_report.md)).

### Inferences
- Any correction from this audit (S4 count, Holm-adjusted detectable differences, cancer-pattern definition, removal of S1) has to be made in both files to keep them aligned.

### Gaps
- Only numbers were compared mechanically; sentence-level meaning was compared only on selected lines.

## 6. Do any plan v2 steps break the project rules in CLAUDE.md?

### Takeaway
No step breaks a rule in its letter: validation gold never enters refinement text, and dev and valid scoring are kept apart. Four places come close and should be fixed or stated. (1) S4(B)'s contrastive criteria are motivated by validation-found cancer patterns that dev gold does not contain. (2) S4 applied to top-4 changes two things at once. (3) S5 compares new loops against old loops across an unknown model-version gap. (4) The loop-level comparisons cannot reach significance under the Holm rule v2 prescribes.

### Cited Findings
- Rule text: "Dev gold may feed refinement; independent validation gold never does"; "One controlled variable per experiment arm"; "dev F1 uses the loop's set scoring; valid100 uses strict PubAnnotation matching. Never mix the two" ([`CLAUDE.md`](CLAUDE.md), Working Rules).
- v2 assigns valid100 gold to "Nothing" and calls valid100 results "selection results"; the test split is used once ([v2 L198 to L206](docs/RP/20261020_research_plan_v2.md)). The loop's set scoring is used "only inside the loop" (v2 L210).
- **Validation-informed criteria (S4 B).** The cancer patterns were found in valid100 errors ([report L95](todo-temp/direction-scan/20261019_direction_research_report.md); offline L95). The S4(B) example criterion, "site-specific cancers against bare 'cancer' or 'tumour'", is that same pattern, while v2 says the criteria "come from dev10 or dev30 gold, never from validation errors" (v2 L137). Dev10 and dev30 gold contain 0 "hereditary/sporadic ... cancer" SpecificDisease mentions; dev30 has 7 bare cancer/tumour/lipoma DiseaseClass mentions and dev10 has 1 ([helper section 7](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)).
- **Pilot in-sample for S4(B).** The S4 pilot runs on the same dev30 documents whose gold writes the (B) criteria (v2 L137, L138). The size_noise dev30 set is identical to `reproduction/dev_splits/ncbi_disease_dev30.json` (helper section 7).
- **Gate B baseline.** The 5 saved original-guideline passes on dev30 have 14, 15, 16, 15 and 16 same-span S/D confusions (helper section 7), so "fall by at least half" (v2 L139) means 8 or fewer.
- **Two changes at once (S4 on top-4).** Variant (A) uses "the original guideline's subtype definitions only" (v2 L136), but in validation it is applied to top-4 passes (v2 L139), whose guideline rewrote the definition area (top-4 final L12; 19,262 characters against the original's 7,367, P4 L29, L33). Against the top-4 baseline, (A) changes both the separate call and the definitions.
- **Unknown model version (S5).** S5 compares its new loops with S2's existing loops (v2 L152). Past runs date from 08/02 to 09/02 (`LOG.md` L21 to L27, L42), and the deployment returns only its name, so the model version cannot be confirmed ([`PROGRESS.md` L212](PROGRESS.md)). v2's own fixed items include "One change per comparison" (§6.1, v2 L196).
- **Statistics.** The "paired document bootstrap for every comparison" (v2 L211) resamples documents for one pass against one pass. It does not capture loop-to-loop variation, which comparisons 1 and 4 (v2 L213, L216) are about. With Holm, the detectable differences rise to about 0.029 (4 loops) and 0.034 (3 loops) ([helper section 2](todo-temp/plan-v2-review/research_notes/Plan%20v2%20review%20without%20finetuning/audit_helper_output.txt)).
- **Mixed scales in one table.** v2's §2 table puts dev F1 0.9091 / 0.8811 (loop scoring, [nontarget L51 to L53](todo-temp/r4-nontarget/20261015_r4_nontarget_report.md)) next to valid100 strict numbers without a label (v2 L46). On NCBI the two scorers give the same numbers (offline L11; `reproduction/README.md` L87 to L90), so no value is wrong; only the label is missing.
- **Reviewer prompt contamination (S7).** The session that wrote the plan has read validation gold and error lists; v2 requires a fresh process (v2 L185; [report L228](todo-temp/direction-scan/20261019_direction_research_report.md)).

### Inferences
- S4(B) should either limit itself to criteria that dev gold actually supports, or state that the topic was chosen from validation errors. If it does neither, a gain on valid100 or test from (B) carries an indirect validation-to-refinement path, which the rule is meant to exclude.
- S4 needs a variant (A') that keeps top-4's own subtype definitions when it is applied to top-4 passes, so that only "separate call" changes.
- For a 4-against-4 loop comparison, an exact permutation test over loop scores has a smallest two-sided p of 2/70 (about 0.029; C(8,4) = 70 arrangements). That is above Holm's first threshold of 0.0125, so comparison 1 cannot be declared established however large the difference. v2 should either take the loop comparisons out of the Holm family and report them descriptively (as v2 L219 partly does), or say plainly that they cannot reach significance.
- S5 should run a few same-guideline control passes in the same weeks (for example, the R4 guideline on dev10) so that drift in the deployment can be told apart from the acceptance rule.

### Gaps
- v2 does not name the test for the loop-level comparisons, so the permutation bound above is an inference about the likely test, not a check of a stated one.
- Whether the 08/02 R4 loop and the 09/02 top-1 loops ran the same code version (S2a pools them as "four loops per method", v2 L95) was not checked.

### Verification record (核查记录)

**Commands (2026-10-19, offline, no API calls, no `.env` or credential file read)**

```
python -I "todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/audit_helper.py"
sha256sum todo-temp/direction-scan/offline_direction_checks_output.txt todo-temp/direction-scan/plan_v2_cost_output.txt todo-temp/meeting-20261020/error_breakdown_output.txt
sha256sum / md5sum / sha1sum of outputs/ncbi_disease/20260902_*/final/final_guidelines.txt and data/guidelines/ncbi_disease_guidelines.txt; SHA-256 of whitespace-stripped text via python -I
pdftotext -layout archive/references/backbone-research.pdf -    (streamed to stdout and searched; no file saved)
grep for CJK characters in docs/RP/20261020_research_plan_to_draft.md; grep "inheritance pattern alone" over outputs/ncbi_disease/*/final/final_guidelines.txt; grep "NEEDLE|92.28" over *.md, *.txt, *.py
```

**Artifacts**

| File | SHA-256 (first 12) |
| --- | --- |
| `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/audit_helper.py` | a89273a57240 |
| `todo-temp/plan-v2-review/research_notes/Plan v2 review without finetuning/audit_helper_output.txt` | 218644059fb1 |
| `todo-temp/direction-scan/offline_direction_checks_output.txt` | 4680e457c66e (same as report L263) |
| `todo-temp/direction-scan/plan_v2_cost_output.txt` | a102ea385e65 (same as report L266) |
| `todo-temp/meeting-20261020/error_breakdown_output.txt` | 41ca602af29f (same as v1 L254) |

**Checks in the helper.** The 8 runs reproduce their saved strict F1 (assertions). The helper's review curve matches the saved values at 0/10/20/30/50/100% (offline L32 to L37, L41 to L46, within 0.0001 at 10% and 50% random). Its one-type F1 at 0% matches breakdown (0.8546, 0.8490).

**Not done.** No literature outside the repository was opened (Zhao.pdf, Lee et al., Chen et al., Leaman et al., NEEDLE). `../papers/multi-annotator setting.pdf` and `archive/references/sub-backbone-research1.pdf` were not opened. No repository file was modified; the only files written are the two helper files above and these notes.
