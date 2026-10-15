"""Build the Round 4 secondary-effects deck (seminar 2026-10-16) on the Academic Serif B template.

Story: Round 4 changed three entities outside its target errors (the base paper calls such changes
secondary effects). Were they caused by the Round 4 principle, or by run-to-run variation? Reruns
with the R4 guideline never reproduce the Tay-Sachs change, and cutaneous vasculitis varies with
an unchanged guideline. Round 4 was kept on a dev F1 gain that partly rests on the Tay-Sachs flip.

Evidence (every number on the slides is read or asserted from these files):
    todo-temp/r4-nontarget/20261015_r4_nontarget_report.md
    todo-temp/r4-nontarget/scores.json                       (E1 reruns)
    reproduction/results/size_noise/repeat_01..05.json        (original guideline, 5 runs)
    outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_0{1..4}/snapshot.json

Layout helpers come from todo-temp/r4-isolation/build_faldh_slides.py.

    python todo-temp/r4-nontarget/build_secondary_effects_slides.py [output.pptx]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "todo-temp/r4-isolation"))

import build_faldh_slides as kit  # noqa: E402
from build_faldh_slides import (BORDER, GREEN, INK, MUTED, NAVY, PALE, RED, WHITE, Inches, MSO_ANCHOR,  # noqa: E402,F401
                                PP_ALIGN, Presentation, boxed_text, box, drop, label_above, layout, new_slide,
                                normalize_slide_ids, place, put, table_at, table_at_placeholder, text)

OUT = ROOT.parent / "presentations/20261016_r4_secondary_effects_en.pptx"
RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
TAY, TSD = (193, 210), (213, 216)
VASC = (646, 666)
SHORT = {"Modifier": "Modifier", "SpecificDisease": "SpecificDisease", "DiseaseClass": "DiseaseClass", "O": "not annotated"}


# ---------------------------------------------------------------- evidence
def label_at(denotations, span, key="label"):
    hit = [d[key] for d in denotations if (d["start"], d["end"]) == span]
    return hit[0] if hit else "O"


def load_evidence() -> dict:
    ev = {}
    # per-round labels R0..R4 from the saved snapshots
    rounds = {}
    for it in range(1, 5):
        snap = json.loads((RUN / f"rounds/iteration_0{it}/snapshot.json").read_text(encoding="utf-8"))
        files = {f["filename"]: f for f in snap["diagnostics_after"]["files"]}
        if it == 1:
            before = {f["filename"]: f for f in snap["diagnostics_before"]["files"]}
            rounds["R0"] = before
        rounds[f"R{it}"] = files
        if it == 4:
            ev["summary_before"], ev["summary_after"] = snap["summary_before"], snap["summary_after"]
    ev["tay_rounds"] = [label_at(rounds[r]["8326491.json"]["study_denotations"], TAY) for r in ("R0", "R1", "R2", "R3", "R4")]
    ev["tsd_rounds"] = [label_at(rounds[r]["8326491.json"]["study_denotations"], TSD) for r in ("R0", "R1", "R2", "R3", "R4")]
    ev["vasc_rounds"] = [label_at(rounds[r]["6859721.json"]["study_denotations"], VASC) for r in ("R0", "R1", "R2", "R3", "R4")]
    assert ev["tay_rounds"] == ["Modifier"] * 4 + ["SpecificDisease"], ev["tay_rounds"]
    assert ev["tsd_rounds"] == ["Modifier"] * 4 + ["SpecificDisease"], ev["tsd_rounds"]
    assert ev["vasc_rounds"] == ["DiseaseClass", "SpecificDisease", "DiseaseClass", "SpecificDisease", "DiseaseClass"]

    # E1 reruns
    scores = json.loads((HERE / "scores.json").read_text(encoding="utf-8"))
    for cond in ("c1_R3", "c3_R4"):
        spans = scores["table"][cond]["spans"]
        assert len(spans["193-210"]) == 5 and set(spans["193-210"]) == {"Modifier"}, cond
        assert set(spans["213-216"]) == {"Modifier"}, cond
    ev["e1_specific"] = {c: sum(v == "SpecificDisease" for v in scores["table"][c]["spans"]["193-210"])
                         for c in ("c1_R3", "c3_R4")}
    sections = [a["guideline_section"] for u in scores["units"] for a in u["focus_detail"]["193-210"]]
    assert len(sections) == 10 and all("Modifier" in sec for sec in sections), sections

    # original guideline, 5 earlier runs (parameters not saved; script defaults at commit 2488342)
    repeats = [json.loads((ROOT / f"reproduction/results/size_noise/repeat_0{i}.json").read_text(encoding="utf-8"))
               for i in range(1, 6)]
    ev["tay_fixed"] = [label_at(r["8326491.json"], TAY, key="entity") for r in repeats]
    ev["vasc_fixed"] = [label_at(r["6859721.json"], VASC, key="entity") for r in repeats]
    assert ev["tay_fixed"] == ["Modifier"] * 5, ev["tay_fixed"]
    assert ev["vasc_fixed"] == ["DiseaseClass", "SpecificDisease", "SpecificDisease", "DiseaseClass", "DiseaseClass"]

    # dev F1 recount: R4 with both Tay-Sachs mentions as in the reruns (Modifier: TP-2, FP+2, FN+2)
    f1 = lambda tp, fp, fn: 2 * tp / (2 * tp + fp + fn)  # noqa: E731
    b, a = ev["summary_before"], ev["summary_after"]
    ev["f1_r3"] = f1(b["true_positives"], b["false_positives"], b["false_negatives"])
    ev["f1_r4"] = f1(a["true_positives"], a["false_positives"], a["false_negatives"])
    ev["f1_r4_rerun"] = f1(a["true_positives"] - 2, a["false_positives"] + 2, a["false_negatives"] + 2)
    assert (round(ev["f1_r3"], 4), round(ev["f1_r4"], 4), round(ev["f1_r4_rerun"], 4)) == (0.8873, 0.9091, 0.8811)
    return ev


# ---------------------------------------------------------------- slides
def build(out: Path = OUT) -> None:
    ev = load_evidence()
    prs = Presentation(kit.TEMPLATE)
    sld_ids = prs.slides._sldIdLst
    for sld_id in list(sld_ids):  # drop the 20 sample slides
        prs.part.drop_rel(sld_id.rId)
        sld_ids.remove(sld_id)

    # 1 Cover
    s = new_slide(prs, "01 Cover", "Topic: the changes Round 4 made outside its target errors in the NCBI dev10 "
                  "GPT-5.4 run (20260802), and whether the Round 4 principle caused them.")
    put(s, 0, "The University of Tokyo")
    put(s, 1, ["Round 4 secondary effects:", "caused by the principle?"])
    put(s, 2, "Hengyu Zhou")
    put(s, 3, "Lab seminar, 16 October 2026")

    # 2 Background: the base paper's framework (its Figure 1, cropped, not redrawn)
    s = new_slide(prs, "07 Full figure",
                  "Figure 1 of the base paper (archive/references/backbone-research.pdf, page 3). Each iteration: "
                  "LLM Annotation of the dev set, Evaluation against gold annotation (strict F1), then Moderation: "
                  "Discrepancy Analysis selects the most frequent discrepancy group as the target, and Pattern "
                  "Explanation, Principle Generation and Guideline Refinement produce the next guideline. R0 is the "
                  "original guideline, Rn the guideline after n moderation rounds. Run used here: "
                  "20260802_gpt54-high_moderation, GPT-5.4 high effort, dev10, seed 42.")
    put(s, 0, "Background: iterative moderation framework")
    label_above(s, "Rn: guideline after n moderation rounds")
    drop(s, 1)
    fig_w = min(3.54 * kit.FIG1_ASPECT, 11.667)
    fig = s.shapes.add_picture(str(kit.FIG1), Inches(0.833 + (11.667 - fig_w) / 2), Inches(2.42), width=Inches(fig_w))
    fig.name = "base-paper-figure-1"
    fig._element.nvPicPr.cNvPr.set("descr", "Figure 1 of the base paper: overview of the iterative moderation "
                                   "framework, from LLM Annotation and Evaluation to Moderation (Discrepancy "
                                   "Analysis, Pattern Explanation, Principle Generation, Guideline refinement).")
    put(s, 2, "Source: base paper, Figure 1")

    # 3 Terms from the base paper
    s = new_slide(prs, "12 Results table",
                  "Target errors: Discrepancy Analysis groups discrepancies by gold and predicted label and selects the "
                  "most frequent group as the target of moderation (section 3.4.1). Secondary effects: the paper's term "
                  "for effects of a guideline update on other annotation cases, both positive and negative (section "
                  "5.4, lines 447-448 and 458-477). Figure 4 calls single cases correct changes (resolved errors) and "
                  "false changes (newly introduced errors). The paper reads these as caused by the update; this deck "
                  "asks whether that holds for Round 4.")
    put(s, 0, "Terms from the base paper")
    label_above(s, "Used throughout this deck")
    table_at_placeholder(s, 2, [
        ["Term", "Meaning", "Source"],
        ["Target errors", "Discrepancy group a round addresses", "§3.4.1"],
        ["Secondary effect", "Change on any other case", "§5.4"],
        ["Correct change", "Wrong before, right after", "Fig. 4"],
        ["False change", "Right before, wrong after", "Fig. 4"],
    ], [3.4, 6.267, 2.0], 0.62, center_cols=(2,), bold={(1, 0), (2, 0), (3, 0), (4, 0)})
    put(s, 1, "Paper assumes the update caused them")

    # 4 Round 4: three secondary effects
    s = new_slide(prs, "13 Ablation table",
                  "Round 4 targeted three missed SpecificDisease mentions (FALDH, G6PD, PAH); one was fixed. Outside the "
                  "target errors, three entities changed between R3 and R4: 'Tay-Sachs disease' and its abbreviation "
                  "'TSD' in PMID 8326491 (Modifier to SpecificDisease; gold SpecificDisease), and 'cutaneous vasculitis' "
                  "at [646,666) in PMID 6859721 (SpecificDisease to DiseaseClass; gold SpecificDisease). The other seven "
                  "dev documents have identical predictions after R3 and R4 (P0 report).")
    put(s, 0, "Round 4: three secondary effects")
    label_above(s, "Outside the target errors, R3 → R4")
    table_at_placeholder(s, 2, [
        ["Entity", "After R3", "After R4", "Gold", "Type"],
        ["Tay-Sachs disease", "Modifier", "SpecificDisease", "SpecificDisease", "Correct change"],
        ["TSD (abbreviation)", "Modifier", "SpecificDisease", "SpecificDisease", "Correct change"],
        ["cutaneous vasculitis", "SpecificDisease", "DiseaseClass", "SpecificDisease", "False change"],
    ], [2.65, 2.25, 2.25, 2.25, 2.267], 0.72,
        colors={(1, 4): GREEN, (2, 4): GREEN, (3, 4): RED}, bold={(1, 4), (2, 4), (3, 4)})
    put(s, 1, "Other seven documents: no change")

    # 5 Research question
    s = new_slide(prs, "03 Research question",
                  "Two explanations. The Round 4 principle caused the changes; or the same guideline simply labels "
                  "these entities differently from run to run, so a single run can show a change that the guideline "
                  "did not cause.")
    put(s, 0, "Research question")
    put(s, 1, ["Did the Round 4 principle", "cause these changes?"])
    put(s, 2, "Or just run-to-run variation?")

    # 6 How to tell the two apart
    s = new_slide(prs, "12 Results table",
                  "Re-annotate the same document several times with the guideline before and after Round 4, with the same "
                  "model and settings, gold hidden. A change caused by the principle should reappear in most R4 runs and "
                  "not in R3 runs. Run-to-run variation shows as labels that differ across runs of one guideline, or as a "
                  "change that does not come back.")
    put(s, 0, "How to tell the two apart")
    label_above(s, "Rerun each guideline, compare the labels")
    table_at_placeholder(s, 2, [
        ["Explanation", "R3 guideline reruns", "R4 guideline reruns"],
        ["Caused by the principle", "Old label", "New label, most runs"],
        ["Run-to-run variation", "Labels vary or stay old", "Labels vary or stay old"],
    ], [3.9, 3.883, 3.884], 0.72, bold={(1, 0), (2, 0)})
    put(s, 1, "Same model, settings and document")

    # 7 Case 1: Tay-Sachs disease and TSD
    s = new_slide(prs, "07 Full figure",
                  "PMID 8326491. Both mentions are SpecificDisease in gold. Predictions: Modifier after R0, R1, R2 and "
                  "R3; SpecificDisease after R4. The other four mentions of Tay-Sachs disease or TSD in this document "
                  "(gold Modifier, e.g. 'TSD carriers') stay Modifier in every round.")
    put(s, 0, "Case 1: Tay-Sachs disease and TSD")
    drop(s, 1)
    boxed_text(s, 0.833, 2.29, 11.667, 1.2,
               [[("In a previous study we found that a ", {}),
                 ("Tay-Sachs disease ( TSD )", {"bold": True, "color": NAVY}),
                 (" causing mutation in the intron 9 donor splice site of the HEXA gene occurs at high frequency …", {})]],
               size=20, inset=0.25, name="case-sentence")
    facts = [("Gold annotation", "SpecificDisease, both mentions", INK),
             ("After R0 to R3", "Modifier in every round", INK),
             ("After R4", "SpecificDisease, both mentions", GREEN)]
    for i, (lab, val, col) in enumerate(facts):
        y = 3.85 + i * 0.6
        text(s, 0.833, y, 3.4, 0.45, lab, size=20, color=MUTED, bold=True, name=f"fact-label-{i}")
        text(s, 4.33, y, 8.17, 0.45, val, size=24, color=col, name=f"fact-value-{i}")
    put(s, 2, "NCBI Disease, PMID 8326491; GPT-5.4, dev10")

    # 8 Hypothesis: the new causation wording
    s = new_slide(prs, "14 Case comparison",
                  "R4 guideline line 12 (the merged Round 4 principle) is the first guideline text that ties 'causation' "
                  "context to Specific Disease; 'causation' does not occur in the R1 to R3 guidelines. The rule is written "
                  "for deficiency phrases such as 'deficient activity of fatty aldehyde dehydrogenase', not for disease "
                  "names. In the document, only the mention inside 'TSD causing mutation' changed; 'Tay-Sachs disease "
                  "patients', 'TSD carriers' and 'TSD families' stayed Modifier. Hypothesis: the model applied the causation "
                  "wording beyond the rule's scope. This is the hypothesis the next slides test.")
    put(s, 0, "Hypothesis: the new causation wording")
    put(s, 1, "R4 guideline, line 12")
    put(s, 2, [[("“… often signaled by disease-definition, causation, characterization, or responsibility-for-condition "
                 "context — annotate the whole phrase as Specific Disease.”", {"italic": True, "size": 18})],
               [("Written for deficiency phrases only", {"color": MUTED, "size": 20})]], space_after=8)
    put(s, 3, "Which mentions changed")
    put(s, 4, ["“TSD causing mutation”: changed", "“TSD carriers”, “TSD families”: unchanged",
               "“Tay-Sachs disease patients”: unchanged"], space_after=6, size=20)
    place(s, 2, y=2.95, h=2.7)
    place(s, 4, y=2.95, h=2.7)
    put(s, 5, "A hypothesis, tested next")
    s.placeholders[2].name = "prompt-quote-line12"

    # 9 Experiment
    s = new_slide(prs, "13 Ablation table",
                  "E1, 2026-10-15: document 8326491 re-annotated 5 times with the R3 guideline and 5 times with the R4 "
                  "guideline, alternating, GPT-5.4 high, same prompt template and output configuration as the original "
                  "run; gold used only for scoring. Decision rule fixed before running: the principle counts as the "
                  "cause only if the R4 guideline gives SpecificDisease for 'Tay-Sachs disease' in at least 3 of 5 runs "
                  "and the R3 guideline in at most 1 of 5.")
    put(s, 0, "Experiment: rerun both guidelines")
    label_above(s, "Tay-Sachs document; gold hidden")
    table_at_placeholder(s, 2, [
        ["Guideline given to the annotator", "Runs", "Question answered"],
        ["R3 guideline (before Round 4)", "5", "Label before the principle?"],
        ["R4 guideline (after Round 4)", "5", "Does R4 reproduce SpecificDisease?"],
    ], [4.9, 1.2, 5.567], 0.72, center_cols=(1,), bold={(1, 0), (2, 0)})
    put(s, 1, "Pre-set rule: caused if R4 ≥ 3/5")

    # 10 Result
    r3n, r4n = ev["e1_specific"]["c1_R3"], ev["e1_specific"]["c3_R4"]
    s = new_slide(prs, "08 Figure comparison",
                  f"'Tay-Sachs disease' labeled SpecificDisease in {r3n} of 5 R3 runs and {r4n} of 5 R4 runs; TSD the "
                  "same. All 10 rationales cite the Modifier rule (guideline section 3), reading the phrase as a "
                  "disease-causing mutation. The only SpecificDisease for these mentions in any run is the original "
                  "Round 4 run. Five earlier runs with the original guideline (reproduction/results/size_noise, "
                  "parameters not saved; script defaults: original guideline, GPT-5.4, high) also gave Modifier. "
                  "Source: todo-temp/r4-nontarget/scores.json.")
    put(s, 0, "Result: R4 never reproduces the change")
    put(s, 1, "R3 guideline, 5 runs")
    put(s, 3, "R4 guideline, 5 runs")
    drop(s, 5)
    drop(s, 4)
    drop(s, 2)
    for x, n, nm in ((0.833, r3n, "r3"), (6.917, r4n, "r4")):
        box(s, x, 2.92, 5.583, 1.6, name=f"result-frame-{nm}")
        text(s, x, 2.98, 5.583, 1.0, f"{n} / 5", size=60, color=RED if nm == "r4" else INK, bold=True,
             align=PP_ALIGN.CENTER, name=f"stat-{nm}")
        text(s, x, 3.95, 5.583, 0.42, "runs with SpecificDisease", size=20, color=INK, align=PP_ALIGN.CENTER,
             name=f"stat-label-{nm}")
    text(s, 0.833, 4.75, 11.667, 1.4,
         ["SpecificDisease appeared once: original R4 run", "All 10 reruns cite Modifier rule",
          "Original guideline, 5 earlier runs: Modifier"], size=20, space_after=6, name="result-notes")

    # 11 Case 2: cutaneous vasculitis
    s = new_slide(prs, "07 Full figure",
                  "PMID 6859721, the second mention of 'cutaneous vasculitis' [646,666), gold SpecificDisease. Its label "
                  "alternates across rounds although each round's principle targets something else (Round 2, for "
                  "example, only changes span boundaries). With the original guideline held fixed, five earlier runs "
                  "give DiseaseClass, SpecificDisease, SpecificDisease, DiseaseClass, DiseaseClass. No new runs were made "
                  "for this case. Source: rounds/iteration_0*/snapshot.json and reproduction/results/size_noise.")
    put(s, 0, "Case 2: cutaneous vasculitis")
    label_above(s, "Gold: SpecificDisease; no new runs")
    drop(s, 1)
    boxed_text(s, 0.833, 2.4, 11.667, 0.62,
               [[("… must be distinguished from other causes of ", {}),
                 ("cutaneous vasculitis", {"bold": True, "color": NAVY}), (" .", {})]],
               size=20, inset=0.15, name="case-sentence")

    def label_cell(lab):
        return SHORT.get(lab, lab)

    col_w = [11.667 / 5] * 5
    text(s, 0.833, 3.22, 11.667, 0.38, "Across rounds (guideline changes each round)", size=18, color=MUTED,
         name="rounds-label")
    table_at(s, 0.833, 3.62, [[f"After R{i}" for i in range(5)], [label_cell(v) for v in ev["vasc_rounds"]]],
             col_w, 0.53, center_cols=range(5),
             colors={(1, i): GREEN if v == "SpecificDisease" else RED for i, v in enumerate(ev["vasc_rounds"])})
    text(s, 0.833, 4.92, 11.667, 0.38, "Original guideline held fixed, five runs", size=18, color=MUTED,
         name="fixed-label")
    table_at(s, 0.833, 5.32, [[f"Run {i + 1}" for i in range(5)], [label_cell(v) for v in ev["vasc_fixed"]]],
             col_w, 0.53, center_cols=range(5),
             colors={(1, i): GREEN if v == "SpecificDisease" else RED for i, v in enumerate(ev["vasc_fixed"])})

    # 12 Verdict
    s = new_slide(prs, "12 Results table",
                  "Tay-Sachs disease and TSD: the R4 guideline gives SpecificDisease in 0 of 5 reruns, so the pre-set rule "
                  "(at least 3 of 5) is not met; the original R4 label is a change the guideline does not reproduce. "
                  "cutaneous vasculitis: no R4 reruns, but the label already varies with the guideline held fixed, so a "
                  "single R3-to-R4 change cannot be credited to the principle. In the paper's terms these are observed "
                  "changes on non-target cases, but there is no evidence that they are effects of the Round 4 update.")
    put(s, 0, "Verdict: variation, not the principle")
    label_above(s, "Each change against the two explanations")
    table_at_placeholder(s, 2, [
        ["Change", "Caused by principle?", "Evidence"],
        ["Tay-Sachs disease, TSD", "Not supported", "R4 reruns: SpecificDisease 0/5"],
        ["cutaneous vasculitis", "Not supported", "Varies with fixed guideline, 2/5"],
    ], [3.5, 3.2, 4.967], 0.72, center_cols=(1,), colors={(1, 1): RED, (2, 1): RED},
        bold={(1, 0), (2, 0), (1, 1), (2, 1)})
    put(s, 1, "Not secondary effects of the principle")

    # 13 Implication: Round 4's acceptance
    b, a = ev["summary_before"], ev["summary_after"]
    s = new_slide(prs, "12 Results table",
                  "Acceptance rule (base paper section 3.4; same in our loop): a round is kept only if dev F1 rises, "
                  "otherwise the refinement is discarded and the loop stops. Saved counts: after R3 "
                  f"{b['true_positives']} TP, {b['false_positives']} FP, {b['false_negatives']} FN; after R4 "
                  f"{a['true_positives']} TP, {a['false_positives']} FP, {a['false_negatives']} FN. Third row: the saved "
                  "R4 predictions with only the two Tay-Sachs mentions set to Modifier, as in every rerun (TP -2, FP +2, "
                  "FN +2). This is a recount, not a new run, and it does not estimate a true R4 score: cutaneous "
                  "vasculitis also varies. It shows that the decision to keep Round 4 rested on a change that does not "
                  "reproduce. Of the Round 4 changes, only the PAH target fix reproduced (0/3 with R3, 3/3 with R4, "
                  "isolation replay 2026-10-14).")
    put(s, 0, "Implication: keeping Round 4 was fragile")
    label_above(s, "Kept only if F1 rises (§3.4)")
    table_at_placeholder(s, 2, [
        ["Guideline and predictions", "Dev F1", "Decision"],
        ["After R3, saved", f"{ev['f1_r3']:.4f}", "Baseline"],
        ["After R4, saved", f"{ev['f1_r4']:.4f}", "Kept"],
        ["After R4, Tay-Sachs as in reruns", f"{ev['f1_r4_rerun']:.4f}", "Would be discarded"],
    ], [6.0, 2.2, 3.467], 0.72, center_cols=(1, 2), colors={(2, 2): GREEN, (3, 2): RED},
        bold={(2, 2), (3, 2)})
    put(s, 1, "Recount from saved predictions; no run")

    # 14 Conclusion
    s = new_slide(prs, "17 Summary",
                  "Round 4 changed three entities outside its target errors. The Tay-Sachs change does not come back "
                  "when the R4 guideline is rerun; the cutaneous vasculitis label varies even when the guideline does not "
                  "change. Neither change can be credited to the Round 4 principle, and the decision to keep Round 4 "
                  "depended on the Tay-Sachs change. Next: rerun a round's guideline a few times before keeping the round.")
    put(s, 0, "Conclusion and next steps")
    put(s, 1, ["Three changes outside the target errors", "Tay-Sachs change: not reproduced, 0/5",
               "Vasculitis: varies without guideline change", "No evidence the principle caused either",
               "Round 4's acceptance relied on Tay-Sachs"], bullets=True, space_after=8)
    place(s, 1, h=2.95)
    put(s, 2, "Next: rerun before keeping a round")
    place(s, 2, y=5.6)

    # 15 Limitations
    s = new_slide(prs, "14 Case comparison",
                  "Scope: 5 runs per guideline for one document; one model and setting (GPT-5.4, high reasoning effort); "
                  "the five earlier original-guideline runs did not save their parameters. Not yet tested: cutaneous "
                  "vasculitis under the R4 guideline; secondary effects of other rounds; an acceptance rule that uses "
                  "repeated runs.")
    put(s, 0, "Limitations")
    put(s, 1, "Scope of the evidence")
    put(s, 2, ["Five runs per guideline", "One document per case", "Single model: GPT-5.4, high effort",
               "Earlier runs: parameters not saved"], space_after=6)
    put(s, 3, "Not yet tested")
    put(s, 4, ["Vasculitis under the R4 guideline", "Secondary effects of other rounds",
               "Acceptance rule with reruns"], space_after=6)
    place(s, 2, y=3.0, h=2.6)
    place(s, 4, y=3.0, h=2.6)
    drop(s, 5)

    # 16 Questions
    s = prs.slides.add_slide(layout(prs, "18 Questions"))
    put(s, 0, "Questions")
    put(s, 1, "Hengyu Zhou")
    put(s, 2, "The University of Tokyo")

    normalize_slide_ids(prs)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"saved {out} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)  # optional output path, e.g. while the deck is open
