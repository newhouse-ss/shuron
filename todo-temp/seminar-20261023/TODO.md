# TODO: scope confirmation and the phase plan

Created 2026-10-23. Source: the user's eight-step process (① to ⑧) and the scope review of 2026-10-23. Tick items as they finish and write each answer next to its question.

## ① Scope confirmation (today, 10/23 seminar)

Goal: agree with the professor on "one main line, one main change, necessary supplementary analysis": what must be done, what is optional, what is not done, and what is left to the concrete plan. Use the current v4; do not rewrite it before the seminar.

### Before the seminar

- [x] Review the scope questions against v4 and the 10/20 deck (done 10/23).
- [x] Confirmation slides: `修論/presentations/20261023_scope_confirmation_en.pptx` (19 slides after the 10/23 review of the first draft), built by `todo-temp/slides/build_scope_confirmation_slides.py` from the current v4. Keep three distinctions:
  - **Positioning:** "Track 1 main, Track 2 supplementary" is shown as our proposal waiting for the professor's answer, not as an agreement.
  - **Narrower claims:**
    - no claim that expert working time goes down (no timed study); Track 2 measures edits needed to reach gold (FN and FP counts);
    - 593 is the size of the training split the supervised SOTA used, not a proven requirement;
    - the literature learning curve (10 documents: LLM about 0.85, supervised about 0.68) is outside support, with a different split and one entity type;
    - Track 1 gains are compared within one model; the base paper's 0.73 / 0.76 are a reference only.
  - **Status labels:** done / candidate, not chosen / needs permission / estimate. No GPT-5.4 numbers.
  - Style: at most 6 lines of 6 words, paper terms, no unexplained codes; check the file in ONLYOFFICE (x2t).
- [x] User reviews the slides before the seminar (the user's edited deck, 10/23).

### Seminar of 10/23: questions and answers

Source: the meeting transcript (automatic speech-to-text, no speaker labels, several gaps of one to two minutes), read by Claude on 10/23; the second-corpus answer is the user's (10/23). Times in brackets are minutes into the recording. Q1 to Q4 are the four main questions (deck slides 3, 17, 18); Q5 to Q7 the "if time allows" ones (slide 19).

**Q1. Should the thesis converge on one main track plus one supplementary analysis?**
- Answer: no. Both tracks are necessary; Track 2 is not a supplementary analysis. The professor said the reviewers' comments point the same way (the transcript names Kasahara-san) [05:24 to 07:55, 51:32].
- Track 2 must not come from voting across repeated runs: that only uses the randomness of the LLM output and "should not be considered" [41:13 to 47:12, 52:29 to 53:03].
- Track 2 comes from the method: change the guideline so it misses fewer mentions at the price of more extra ones, while keeping F1. Discuss how this differs from raising F1 alone, in terms of how easy the output is for human annotators, even if F1 itself is not high [47:33 to 48:24, 64:12 to 65:52, 78:06 to 79:09].
- No timed expert study needed: "a missed mention costs an expert the whole document, an extra one only a deletion" can be argued as a reasoned assumption, stated as such. Better still if F1 also improves [79:28 to 85:46].

**Q2. Is "systematic error analysis plus one targeted change" the right scope for the contribution?**
- Answer: deferred. Asked whether all six improvement directions must be done: "we can hold this ... discuss this later", after the error analysis [85:52 to 88:27].
- First action named by the professor: error case analysis and classification [53:59 to 54:12].

**Q3. How deep must the error classification and analysis go?**
- Answer: not discussed on its own; it waits with Q2 (Claude's reading of the transcript).

**Q4. What is the completion standard for the thesis?**
- Answer: a result without a stable F1 gain is acceptable if the thesis discusses the merits and limits of the change: "if you can discuss about this, some merits, it's okay" [88:34 to 90:18].

**Q5 (if time allows). Is Haiku acceptable as the main model? Is a stronger-model control needed?**
- Answer: the cheap model is fine, for F1 and for the FN/FP trade-off [64:12]. A stronger-model control was not decided; the lab API offers only GPT-5.2 and GPT-5.4 [71:01].

**Q6 (if time allows). Second corpus (BC5CDR or BioRED)?**
- Answer: the experiments must be done on NCBI Disease; other datasets only if time allows (user, 10/23).

**Q7 (if time allows). Is the API cost reimbursed?**
- Answer: not settled. Ask first whether DBCLS can provide a Claude API key (it may not). Until then, pay yourself. A claim needs the form, the receipt and a bank statement showing the USD conversion rate; the e-mail address for submitting it will be sent [61:42 to 77:37].

### Points to note

- **Order of work:** the professor named error analysis as the first thing to do; v4 puts the error taxonomy after the reproduction (⑥). Settle whether it starts on existing outputs or waits for the reproduction.
- **The voting slide (slide 8) took about 40 minutes to explain** [08:01 to 47:12]. If repeated runs are shown again, start from a matrix of runs × gold mentions with TP, FP and FN, and justify the number of runs: the professor asked why 20 and not 30, 40 or more, and suggested looking for where the result stops changing [44:57 to 45:31].
- **top-2 and top-3:** the professor asked about them; none has run [91:47 to 92:10].
- **The pilot gain of top-4 (+0.04 on validation)** needs the repeated loops and a t-test before it means anything [90:29 to 93:59].
### The six midterm comments (deck slide 5)

| Feedback | Answer in the plan | Status after 10/23 |
| --- | --- | --- |
| F1 0.8 is not enough to replace annotators | Replacement is not claimed | Settled |
| Frame the LLM as support | Track 2, expert correction | Both tracks required (Q1) |
| Refinement should also modify or delete rules | The rewrite already edits the whole guideline | Settled (deck slide 5) |
| How to balance cost and quality? | Cheaper model, more rounds | Cheap model accepted (Q5) |
| What exactly is the research goal? | Two tracks | Both tracks required (Q1) |
| Are 10 development documents biased? | Not explored further | Dropped (user, 10/23) |

### After the seminar

- [x] Write the answers into the Q&A above (10/23).
- [x] Write what the answers mean for the research line into `PROGRESS.md` (10/23).
- [ ] Reproduction design: `todo-temp/seminar-20261023/reproduction_design.md` (draft 10/23), waiting for the user's approval.
- [ ] Sort every plan item into: must do / optional / not done / left to the concrete plan.
- [ ] Ask whether DBCLS can provide a Claude API key; get the reimbursement form and the submission address; check that the bank statement shows the USD conversion rate (Q7).
- [ ] Error case analysis and classification first (Q2; see "Order of work").
- [ ] Research proposal with the statistical tests (Points to note).

## ② Revise the RP and slides (next week, after ①)

Only what ① confirmed; no new directions.

- [ ] Fixes in `docs/RP/20261020_research_plan_v4.md` already known:
  - line 7: status (the 1+1 pilot loops ran on 10/22);
  - lines 15 and 18: the 593 wording;
  - lines 38 and 40: the base paper comparison contradicts "compare gains within one model";
  - lines 42 to 48: the GPT-5.4 Track 2 table;
  - line 53: the literature learning curve as outside support;
  - line 79: max_tokens is 128000 since 10/22;
  - line 85: DeepSeek ¥1.27 per call assumes every call off-peak; the actual was ¥1.409 (22 of 200 calls at peak; `todo-temp/deepseek-stability/actual_cost_output.txt`);
  - §5: recompute the cost table from the pilot measurements; shift the schedule (v4 still puts the reproduction on 10/27 to 11/02, before ④'s approval);
  - §6 line 147 and §7: timed pilot, data use and budget per the ① answers.
- [ ] Discuss the two points deferred on 10/23:
  - the top-4 guideline fits dev10 (dev10 0.9583 against valid100 0.7411, one loop);
  - the guideline keeps growing (7,367 to 113,338 characters in 6 rounds; round-5 rewrite at 99.4% of the 128,000 cap; valid100 calls ¥1.093 against ¥0.634).
- [ ] Decide whether future top-4 loops use `--stop-at-cap`.
- [ ] Update the slides to match.

Done when: the RP and slides agree on goals, numbers and experiment scope.

## ③ One round of mutual review (after ②, within next week if possible)

- [ ] Commit, then hand over to Codex with a spec: check experiment logic and implementation feasibility.
- [ ] Claude answers each point and revises; one more check if needed.

Done when: no unresolved key contradiction in data, statistics, cost or scheduling.

## ④ First confirmation by email (after ② and ③, within that week)

- [ ] Email the professor the revised plan and its main changes; ask to confirm the experiment design, data use, budget and the boundary with Ken's work.
- [ ] Ask whether the official test split may be used once at the end (v4 §7; needs the authors' consent).
- [ ] Before phase 1, notify the admin of any spend over ¥1,000 (v4 §5).

Done when: confirmation and permission for the pilot and phase 1.

## ⑤ End-to-end pilot, then phase 1 (after ④ is approved)

- [x] 1 top-1 loop and 1 top-4 loop on Haiku xhigh (10/22); cost and batch time measured; each counts as loop 1 of 10 for its method (user, 10/22).
- [x] Top up the API balance (user, 10/23: USD 20.35 before the run).
- [x] Run E1, E2 and E3 at the approved scale (10/23, user's go): 10 E1 runs, top-1 and top-4 loops 02 to 10; JPY 2,517. No test significant; see `reproduction_analysis_output.txt` and PROGRESS.md (10/23).

Done when: complete reproduction results usable for the taxonomy and method choice.

## ⑥ Taxonomy, one change, second confirmation (after ⑤)

- [ ] Error taxonomy on the reproduction outputs (v4 step 3).
- [ ] Propose one priority change and the necessary controls; Claude updates the plan, Codex reviews it, the professor confirms.

Done when: method, hypothesis, comparison conditions, budget, and how to close out if results are poor are all fixed.

## ⑦ Formal change experiment (after ⑥)

- [ ] Run the frozen plan. No new directions or extra runs because results look poor.

Done when: the planned full results and analysis exist; "finally significant" is not a stopping rule.

## ⑧ Freeze the final evaluation and the thesis (after ⑦)

- [ ] Fix the final method and thresholds; run the approved test protocol once; report as is.

Done when: test results are not used to choose methods, and the thesis matches the experiments.

## Housekeeping

- [ ] Commit the uncommitted work (runner, tests, pilot outputs, LOG, PROGRESS, RP v4 edits); needs user approval.

## Verification record

- Steps ① to ⑧: the user's message of 10/23.
- Seminar Q&A: `C:\Users\zhouh\Music\meetily-recordings\Meeting 23_10_26_15_31_09_2026-10-23_06-31\transcripts.json` (e1c50a9e215a, 1,077 segments, 96:56), read in full as plain text; questions from `修論/presentations/20261023_scope_confirmation_en.pptx` as presented (61b60c43371b); Q6 answer from the user (10/23).
- Review inputs: `docs/RP/20261020_research_plan_v4.md` (6f60ee6e5ed4); `修論/presentations/20261020_progress_and_plan_en.pptx` (1cdc7dada8b4), slides 3 and 21.
- 0.6986: `outputs/ncbi_disease/20261022_haiku-xhigh_topk1_loop01/valid_metrics.json` (69c2c429c81b). 0.7411: `outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop01/valid_metrics.json` (ef9709468122).
- 0.046 and p < 0.0001: v4 line 92, from `todo-temp/haiku-trial/report_with_max_output.txt` (4b1f7003f6f8).
- Guideline length, rewrite tokens, per-call costs: `todo-temp/haiku-trial/batch_pilot_costs_output.txt` (319a5ea59fa4).
