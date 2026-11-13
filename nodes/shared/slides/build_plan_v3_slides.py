"""Build the 2026-10-20 meeting deck from plan v3 (English; plan v3 was superseded by
nodes/2026-10-20_meeting/20261020_research_plan_v4.md after the meeting and deleted; it is in the git history).

Story: midterm baseline and feedback, how annotated corpora are built, the updated goals, where we stand,
the case study since the midterm (terms and argument as in presentations/20261016_faldh_attribution_en.pptx:
principle, exception rule, named exclusions, trace to Guideline Refinement, deletion tests), the midterm
points then and now, expert workload, the plan, cost, questions. No backup section.

Every number on a slide is asserted against a saved file (see load_all) or cited in the speaker notes:
    nodes/2026-09-07_midterm-defense/midterm_slides.pptx           midterm text (slides 2, 4, 8, 9, 10)
    nodes/2026-10-20_meeting/plan-v3/error_breakdown.json                   error kinds, one-type F1
    nodes/2026-10-20_meeting/plan-v3/offline_direction_checks_output.txt      paired bootstrap, top-4 vs original
    outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04/   round-4 guideline and prompt
    nodes/2026-10-20_meeting/plan-v3/node_cost_output.txt                     DeepSeek call counts and cost estimates
    nodes/2026-10-20_meeting/plan-v3/expert_study_size_output.txt             expert study cost estimates
    reproduction/results/<run>/metrics.json, nodes/2026-10-16_seminar/r4-attribution/isolation/scores*.json,
    outputs/ncbi_disease/20260902_gpt54-high_topk4_run{1,2,3}/status.json   (load_evidence)

    python nodes/shared/slides/build_plan_v3_slides.py [output.pptx]
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from build_faldh_slides import (GREEN, MUTED, NAVY, RED, TEMPLATE, boxed_text, drop,  # noqa: E402
                                label_above, new_slide, normalize_slide_ids, place, put, table_at,
                                table_at_placeholder, text)

OUT = ROOT.parent / "presentations/20261020_progress_and_plan_en.pptx"
R4 = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation/rounds/iteration_04"
RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
ISO = ROOT / "nodes/2026-10-16_seminar/r4-attribution/isolation"


def f1_of(label: str) -> float:
    m = json.loads((ROOT / "reproduction/results" / label / "metrics.json").read_text(encoding="utf-8"))
    return m["strict_match"]["pubannotation"]["f1"]


def load_evidence() -> dict:
    ev = {"valid": {k: f1_of(v) for k, v in (("orig", "ncbi-g-gpt54"), ("top1", "ncbi-m-gpt54"),
                                              ("top4", "ncbi-valid-topk4-gpt54"))}}
    assert ev["valid"] == {"orig": 0.7792, "top1": 0.7878, "top4": 0.8023}, ev["valid"]

    eb = {r["label"]: r for r in json.loads((ROOT / "nodes/2026-10-20_meeting/plan-v3/error_breakdown.json").read_text(encoding="utf-8"))}
    ev["any_subtype"] = {k: eb[v]["span_only"]["f1"] for k, v in (("orig", "ncbi-g-gpt54"),
                                                                  ("top1", "ncbi-m-gpt54"),
                                                                  ("top4", "ncbi-valid-topk4-gpt54"))}
    assert ev["any_subtype"] == {"orig": 0.8351, "top1": 0.849, "top4": 0.8546}, ev["any_subtype"]
    t4 = eb["ncbi-valid-topk4-gpt54"]
    c = t4["categories"]
    assert (c["label_mismatch"], c["boundary_mismatch"], c["false_negative"], c["false_positive"],
            c["unpaired_overlap"], t4["discrepancies_total"]) == (57, 45, 55, 45, 6, 208)
    lp = t4["label_mismatch_pairs"]
    assert lp["SpecificDisease->DiseaseClass"] == lp["DiseaseClass->SpecificDisease"] == 21
    assert t4["boundary_by_gold_type"]["SpecificDisease"] == 32
    assert (t4["missed_by_gold_type"]["Modifier"], t4["missed_by_gold_type"]["DiseaseClass"]) == (27, 25)
    assert t4["spurious_by_pred_type"]["SpecificDisease"] == 28
    assert eb["ncbi-m-gpt54"]["missed_by_gold_type"]["Modifier"] == 40
    o = t4["oracle"]
    ev["oracle"] = {k: o[k]["f1"] for k in ("label mismatch fixed", "boundary mismatch fixed",
                                            "missed entities added", "spurious entities removed",
                                            "expert checks every predicted entity")}
    assert ev["oracle"] == {"label mismatch fixed": 0.875, "boundary mismatch fixed": 0.8597,
                            "missed entities added": 0.8429, "spurious entities removed": 0.826,
                            "expert checks every predicted entity": 0.9606}, ev["oracle"]
    assert t4["predicted_entities"] == 777

    # FALDH tests (10/14 isolation, 10/14 deletion in round 4, 10/17 deletion in round 3)
    units = [u for u in json.loads((ISO / "scores.json").read_text(encoding="utf-8"))["units"]
             if u["target"] == "FALDH"]
    principle = [u for u in units if u["condition"] == "c2_principle"]
    r4 = [u for u in units if u["condition"] == "c3_R4"]
    assert len(principle) == len(r4) == 3
    assert sum(u["target_status"] != "O" for u in principle) == 3 and sum(u["target_status"] != "O" for u in r4) == 0
    minus4 = [u for u in json.loads((ISO / "scores_c3minus.json").read_text(encoding="utf-8"))["units"]
              if u["target"] == "FALDH"]
    assert len(minus4) == 3 and sum(u["target_correct"] for u in minus4) == 3
    minus3 = [u for u in json.loads((ISO / "scores_r3minus.json").read_text(encoding="utf-8"))["units"]
              if u["condition"] == "c4_R3_minus_faldh"]
    assert len(minus3) == 5 and all(u["faldh"] == "O" for u in minus3)

    # Round 4 acceptance: recorded values and the value with the two rerun predictions (63 TP, 6 FP, 11 FN)
    snap = json.loads((RUN / "rounds/iteration_04/snapshot.json").read_text(encoding="utf-8"))
    ev["r3_dev"] = round(snap["summary_before"]["overall_f1"], 4)
    ev["r4_dev"] = round(snap["summary_after"]["overall_f1"], 4)
    ev["r4_rerun_dev"] = round(2 * 63 / (2 * 63 + 6 + 11), 4)
    assert (ev["r3_dev"], ev["r4_dev"], ev["r4_rerun_dev"]) == (0.8873, 0.9091, 0.8811)
    assert "deficient activity of fatty aldehyde dehydrogenase" in snap["guidelines_before"]

    # Top-4 replicate loops: final development F1
    reps = [json.loads((ROOT / f"outputs/ncbi_disease/20260902_gpt54-high_topk4_run{i}/status.json")
                       .read_text(encoding="utf-8"))["final_f1"] for i in (1, 2, 3)]
    assert [round(x, 3) for x in reps] == [0.825, 0.855, 0.884], reps
    return ev


def f3(x: float) -> str:
    return f"{x:.3f}"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def load_all() -> dict:
    ev = load_evidence()

    # Midterm deck text
    z = zipfile.ZipFile(ROOT / "nodes/2026-09-07_midterm-defense/midterm_slides.pptx")
    mid = {i: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", z.read(f"ppt/slides/slide{i}.xml").decode("utf8")))
           for i in (2, 4, 8, 9, 10)}
    assert "593 gold-annotated documents required" in mid[2]
    assert "initial guideline: 0.73" in mid[4] and "refined guideline: 0.76" in mid[4] and "+0.03" in mid[4]
    assert "Grouped into three axes" in mid[4]
    assert "38 of 52 new lines in round 1" in mid[8]
    assert "0.0150 (10 docs) to 0.0092 (30 docs)" in mid[9]
    assert "currently around 0.79, and SOTA at 0.87" in mid[10] and "10 docs for refinement vs. 593" in mid[10]

    # Round-4 guideline: the three named exclusions; round-4 Guideline Refinement prompt
    lines = (R4 / "guidelines_after.txt").read_text(encoding="utf-8").splitlines()
    for n in (54, 167, 263):
        assert "fatty aldehyde dehydrogenase" in lines[n - 1].lower(), n
    prompt = (R4 / "refine_guidelines.txt").read_text(encoding="utf-8")
    assert "currently handled CORRECTLY" in prompt
    assert "prioritize specific sub-cases to avoid regression" in prompt

    # Corrections per guideline (validation, one run each)
    eb = {r["label"]: r for r in json.loads((ROOT / "nodes/2026-10-20_meeting/plan-v3/error_breakdown.json").read_text(encoding="utf-8"))}
    ev["corr"] = {}
    for key, label in (("orig", "ncbi-g-gpt54"), ("top4", "ncbi-valid-topk4-gpt54")):
        c = eb[label]["categories"]
        ev["corr"][key] = (eb[label]["discrepancies_total"], c["false_negative"], c["false_positive"],
                           c["boundary_mismatch"], c["label_mismatch"], c["unpaired_overlap"])
    assert ev["corr"] == {"orig": (229, 73, 34, 44, 67, 11), "top4": (208, 55, 45, 45, 57, 6)}, ev["corr"]

    assert "topk4 - original                 diff +0.0231  95% CI [-0.0192, +0.0683]" in \
        read("nodes/2026-10-20_meeting/plan-v3/offline_direction_checks_output.txt")

    nc = read("nodes/2026-10-20_meeting/plan-v3/node_cost_output.txt")
    assert "per call JPY: off 0.069, on_mean 2.204, on_max 3.523" in nc
    assert "TOTAL core (unconditional): calls 3876 | off JPY 377 | on JPY 8,430 to 13,475" in nc
    assert "TOTAL all: calls 4376 | off JPY 412 | on JPY 9,532 to 15,236" in nc

    es = read("nodes/2026-10-20_meeting/plan-v3/expert_study_size_output.txt")
    assert "JPY 1,500/h: 7,396 to 18,948" in es and "JPY 5,000/h: 24,653 to 63,159" in es
    assert "JPY 1,500/h: 18,979 to 58,738" in es and "JPY 5,000/h: 63,265 to 195,794" in es
    return ev


def build(out: Path = OUT) -> None:
    ev = load_all()
    prs = Presentation(TEMPLATE)
    sld_ids = prs.slides._sldIdLst
    for sld_id in list(sld_ids):  # drop the template's sample slides
        prs.part.drop_rel(sld_id.rId)
        sld_ids.remove(sld_id)
    v, a = ev["valid"], ev["any_subtype"]
    co, ct = ev["corr"]["orig"], ev["corr"]["top4"]

    # 1 Cover
    s = new_slide(prs, "01 Cover", "Meeting with the supervisor and the authors of the base paper. The deck follows "
                  "the research plan docs/RP/20261020_research_plan_v3.md and starts from the midterm presentation (9/7).")
    put(s, 0, "The University of Tokyo")
    put(s, 1, ["Optimizing Annotation Guideline Refinements", "for LLM-Based Annotation"], size=40)
    put(s, 2, "Hengyu Zhou")
    put(s, 3, "Progress since the midterm and plan, 20 October 2026")

    # 2 Midterm baseline
    s = new_slide(prs, "12 Results table",
                  "Midterm slides (nodes/2026-09-07_midterm-defense/midterm_slides.pptx). Slide 2: a supervised "
                  "model needs 593 gold documents; an LLM learns the conventions from the guideline instead. Slide 4: "
                  "in the base paper (GPT-5, NCBI Disease) the guideline adds +0.27 (0.46 to 0.73) and refinement only "
                  "+0.03 (0.73 to 0.76); six points limiting the gain were grouped into three axes: extraction "
                  "(points 2, 3, 6), generalization (1, 4), reliability (5). Slide 10: goal 'close the gap between "
                  "validation F1, currently around 0.79, and SOTA at 0.87, without giving up the low-supervision "
                  "advantage (10 docs for refinement vs. 593 docs for fine-tuning)'.")
    put(s, 0, "Where the midterm left off")
    text(s, 0.833, 1.95, 11.667, 0.45,
         [[("Finding: ", {"bold": True, "color": NAVY}),
           ("refinement added only +0.03 (0.73 → 0.76)", {})]], size=20, name="finding")
    label_above(s, "Development data: the 10 gold documents the loop learns from", y=2.5)
    table_at(s, 0.833, 2.95, [
        ["Axis", "Question", "Points found"],
        ["Extraction", "Is the development data fully used?", "3"],
        ["Generalization", "Do development gains reach validation?", "2"],
        ["Reliability", "Is one annotation stable?", "1"],
    ], [2.8, 6.667, 2.2], 0.55, center_cols=(2,))
    drop(s, 2)
    put(s, 1, "Midterm goal: 0.79 → 0.87, still with 10 documents, not 593")
    place(s, 1, y=5.6)

    # 3 Feedback after the midterm (no names)
    s = new_slide(prs, "05 Key points",
                  "Comments on the midterm presentation, from the supervisor's e-mail of 9/12 and the reviewers' "
                  "questions recorded in the 9/15 plan. Supervisor: 'F1 = 0.8 (SOTA) may not be good enough for "
                  "replacing manual annotation ... you can also consider that the LLM annotation will be still have "
                  "some supports for manual annotation'; 'not just adding some sentences from the gold examples, but "
                  "also modifying or deleting the original texts'. Reviewers: scores not sufficient for product-level "
                  "use and how to balance cost and performance; what the research goal is; whether the 10-document "
                  "selection may be biased.")
    put(s, 0, "Feedback after the midterm")
    put(s, 1, ["F1 0.8 is not enough to replace annotators",
               "Frame the LLM as support, not replacement",
               "Refinement should also modify or delete rules",
               "How to balance cost and quality?",
               "What exactly is the research goal?",
               "Are 10 development documents biased?"], bullets=True, space_after=8)

    # 4 How annotated corpora are built
    s = new_slide(prs, "12 Results table",
                  "NCBI Disease (Dogan and Lu 2012): an in-house CRF disease tagger trained on the AZDC corpus "
                  "pre-annotated each abstract; two of 12 annotators edited it independently (keep, delete, adjust, "
                  "add), revised after seeing their differences, then met to agree. BC5CDR (Li et al. 2016): DNorm and "
                  "tmChem output shown in PubTator; two MeSH indexers with medical training per article; a senior "
                  "annotator resolved differences. BioRED (Luo et al. 2022): earlier labels plus PubTator "
                  "pre-annotation; three annotators per article; a senior annotator reviewed disagreements; 'a small "
                  "set of PubMed articles were first used to develop our annotation guidelines and familiarize our "
                  "annotators'. The LLM would take the place of the machine pre-annotation; the 10 development "
                  "documents correspond to that pilot set.")
    put(s, 0, "How annotated corpora are built")
    label_above(s, "Machine pre-annotates; experts edit; disagreements are resolved", y=2.0)
    table_at_placeholder(s, 2, [
        ["Corpus", "Pre-annotation", "Then"],
        ["NCBI Disease (2012)", "In-house CRF tagger", "2 experts, then consensus"],
        ["BC5CDR (2016)", "DNorm and tmChem", "2 MeSH indexers, then senior"],
        ["BioRED (2022)", "PubTator, older labels", "3 experts, then senior"],
    ], [3.3, 3.6, 4.767], 0.55)
    place(s, 2, y=2.5)
    text(s, 0.833, 4.85, 11.667, 0.4, "Projects start with a small pilot set to write the guideline",
         size=18, color=MUTED, name="pilot")
    put(s, 1, "An LLM can replace the machine step, not an expert")
    place(s, 1, y=5.45)

    # 5 Goal update
    s = new_slide(prs, "12 Results table",
                  "Why an LLM: the midterm argued that an LLM learns the dataset conventions from the guideline, so "
                  "it does not need the 593 gold documents a supervised model needs. Now the same argument is applied "
                  "to the start of a new corpus, when little gold exists. Quality target: 0.87 (midterm) and 0.86 "
                  "(project notes) have no source for NCBI Disease; 0.86 is the base paper's moderated score on "
                  "BC5CDR. The NCBI Disease SOTA is NEEDLE, F1 0.9228 (Jiang et al. 2021, Table 9), one Disease type, "
                  "official test split, trained on all 593 training documents plus weak dictionary labels. Model "
                  "change: cost, see the DeepSeek slide; GPT-5.4 results stay as the case study, in separate tables.")
    put(s, 0, "Goal update: midterm → now")
    table_at_placeholder(s, 2, [
        ["", "Midterm", "Now"],
        ["Why an LLM", "No need for 593 gold documents", "Same, when a new corpus starts"],
        ["Quality target", "Validation F1 0.79 → 0.87", "Distance to expert annotation"],
        ["Human role", "Measure replacement later", "Reduce expert workload"],
        ["Supervision", "10 documents, not 593", "Kept: 10 = pilot set"],
        ["Model", "GPT-5.4", "DeepSeek V4.1 flash"],
    ], [2.4, 4.6, 4.667], 0.55, bold={(i, 0) for i in range(1, 6)})
    place(s, 2, y=2.0)
    put(s, 1, "No NCBI source for 0.87; SOTA is 0.9228, one type")
    place(s, 1, y=5.5)

    # 6 Two goals
    s = new_slide(prs, "12 Results table",
                  "Focus: the low-resource stage of building a corpus, before there is enough gold to train a "
                  "supervised model. Exact span and subtype F1: span and one of the four subtypes must both match "
                  "gold (the base paper's measure). Edits: the changes needed to turn the LLM output into the gold "
                  "annotation (add missed, delete extra, fix boundary, fix subtype). Minutes per document need real "
                  "experts. Training a supervised model on the finished corpus is discussed, not tested.")
    put(s, 0, "Two goals")
    label_above(s, "Focus: early stage, before a supervised model can be trained", y=2.0)
    table_at_placeholder(s, 2, [
        ["Goal", "Question", "Measure"],
        ["Quality", "How far is LLM pre-annotation from experts?", "Exact span and subtype F1"],
        ["Workload", "At expert standard, how much work remains?", "Edits, then minutes"],
    ], [2.0, 5.9, 3.767], [0.55, 0.85, 0.85])
    place(s, 2, y=2.5)
    put(s, 1, "Not claimed: an LLM replaces an independent annotator")
    place(s, 1, y=5.0)

    # 7 Where we stand
    s = new_slide(prs, "12 Results table",
                  "Validation: the 100 NCBI Disease documents of the base paper (791 gold mentions). Base paper: "
                  "GPT-5, Table 1. Ours: GPT-5.4, reasoning high, one run each. top-4: each round refines the four "
                  "largest discrepancy clusters instead of only the largest (top-1). Exact span, one type: the same "
                  "predictions scored with the four subtypes merged, the only way to compare with supervised models. "
                  "NEEDLE: official test split, so indicative only. 95% CI: paired bootstrap over documents; the 100 "
                  "documents are resampled with replacement 10,000 times (seed 42), both guidelines are rescored on "
                  "each resample, and the 2.5th and 97.5th percentiles of the difference are taken "
                  "(nodes/2026-10-20_meeting/plan-v3/offline_direction_checks.py, function boot). The interval includes 0, "
                  "so the gain is not established.")
    put(s, 0, "Where we stand")
    label_above(s, "top-4: four largest discrepancy clusters refined per round", y=2.0)
    table_at_placeholder(s, 2, [
        ["System", "Exact span and subtype", "Exact span, one type"],
        ["Base paper (GPT-5), original guideline", "0.73", "n/a"],
        ["Base paper (GPT-5), refined", "0.76", "n/a"],
        ["Ours (GPT-5.4), original guideline", f3(v["orig"]), f3(a["orig"])],
        ["Ours (GPT-5.4), top-4 refined", f3(v["top4"]), f3(a["top4"])],
        ["NEEDLE, supervised SOTA (test split)", "n/a", "0.923"],
    ], [4.9, 3.4, 3.367], 0.5, center_cols=(1, 2))
    place(s, 2, y=2.45)
    put(s, 1, "top-4 vs original: +0.023, 95% CI [−0.019, +0.068]")
    place(s, 1, y=5.95)

    # 8 Case: a disease never annotated
    s = new_slide(prs, "07 Full figure",
                  "Evidence since the midterm. Document PMID 10577908, one of the 10 development documents. Gold: "
                  "SpecificDisease, span [245,295), 'deficient activity of fatty aldehyde dehydrogenase'. Model "
                  "predictions with the original guideline (round 0) and after rounds 1 to 4: not annotated. Round 4 "
                  "targeted three SpecificDisease misses: FALDH, 'deficiency in G6PD' and 'deficiency of hepatic "
                  "phenylalanine hydroxylase'.")
    put(s, 0, "Case study: a disease never annotated")
    drop(s, 1)
    boxed_text(s, 0.833, 2.2, 11.667, 1.25,
               [[("“Sjogren-Larsson syndrome (SLS) is an autosomal recessive disorder characterized by ichthyosis, "
                  "mental retardation, spasticity, and ", {}),
                 ("deficient activity of fatty aldehyde dehydrogenase", {"bold": True, "color": NAVY}),
                 (" (FALDH).”", {})]], size=20, inset=0.25, name="case-sentence")
    text(s, 0.833, 3.75, 3.2, 0.45, "Gold annotation", size=20, color=MUTED, bold=True, name="gold-label")
    text(s, 4.2, 3.75, 8.3, 0.45, "SpecificDisease, whole phrase", size=22, color=GREEN, name="gold-value")
    text(s, 0.833, 4.35, 3.2, 0.45, "Model", size=20, color=MUTED, bold=True, name="model-label")
    text(s, 4.2, 4.35, 8.3, 0.45, "Not annotated, rounds 0 to 4", size=22, color=RED, name="model-value")
    text(s, 0.833, 4.95, 3.2, 0.45, "Round 4", size=20, color=MUTED, bold=True, name="round-label")
    text(s, 4.2, 4.95, 8.3, 0.45, "Targeted it, with two other misses", size=22, name="round-value")
    put(s, 2, "NCBI Disease, PMID 10577908; GPT-5.4, 10 development documents")

    # 9 One guideline, two opposite instructions
    s = new_slide(prs, "08 Figure comparison",
                  "Principle: the IF-THEN rule written each round from the target discrepancy cluster (Principle "
                  "Generation), merged into the guideline by Guideline Refinement. Exception rule: the principle's "
                  "trailing restrictive clause ('DO NOT apply ...'). Left: the round-4 principle as merged into "
                  "guideline lines 12 to 14. Right: three lines in the same round-4 guideline that exclude FALDH by "
                  "name; we call them named exclusions. Line 54 (block 54 to 58): example 'Deficient activity of fatty "
                  "aldehyde dehydrogenase' marked 'Do not annotate'. Line 167: 'This also excludes isolated "
                  "molecular-function or laboratory-abnormality phrases such as deficient activity of fatty aldehyde "
                  "dehydrogenase ...'. Line 263: 'the phrase is not annotated because here it refers to enzyme "
                  "activity/biochemical abnormality'. Lines 54 and 263 descend from round-3 lines 41 and 241; line "
                  "167 is new in round 4.")
    put(s, 0, "One guideline, two opposite instructions")
    put(s, 1, "Round-4 principle: annotate", size=20)
    put(s, 3, "Three named exclusions: do not", size=20)
    drop(s, 4)
    drop(s, 2)
    boxed_text(s, 0.833, 2.92, 5.583, 2.5,
               ["Deficiency + specific molecule",
                "In a defining or causal context",
                [("→ annotate as SpecificDisease", {"bold": True, "color": GREEN})],
                "Exception rule: not mere lab findings"],
               size=20, inset=0.25, anchor=MSO_ANCHOR.TOP, space_after=10, name="principle")
    boxed_text(s, 6.917, 2.92, 5.583, 2.5,
               ["Line 54: example “Do not annotate”",
                "Line 167: lists FALDH as excluded",
                "Line 263: “the phrase is not annotated”",
                [("Two inherited from round 3, one new", {"color": MUTED})]],
               size=20, inset=0.25, anchor=MSO_ANCHOR.TOP, space_after=10, name="exclusions")
    put(s, 5, "Named exclusion: a guideline line excluding FALDH by name")

    # 10 Where FALDH was lost
    s = new_slide(prs, "12 Results table",
                  "Rule chain from the saved round-4 prompts (rounds/iteration_04), stage names as in the base paper. "
                  "Discrepancy Analysis clusters the discrepancies; FALDH falls in the target cluster 'Gold: "
                  "SpecificDisease vs LLM: missed' (3 cases). Pattern Explanation sees FALDH with its gold label and "
                  "suggests SpecificDisease in 'characterized by' contexts. Principle Generation writes a principle "
                  "whose condition covers FALDH. Guideline Refinement keeps the two round-3 named exclusions and adds "
                  "a third (line 167). LLM Annotation with the round-4 guideline: FALDH still not annotated.")
    put(s, 0, "Where FALDH was lost: Guideline Refinement")
    label_above(s, "FALDH through the round-4 stages (base paper names)", y=2.0)
    table_at_placeholder(s, 2, [
        ["Stage", "Sees gold?", "What happened to FALDH"],
        ["Discrepancy Analysis", "Yes", "Put in the target cluster"],
        ["Pattern Explanation", "Yes", "Suggested SpecificDisease"],
        ["Principle Generation", "Yes", "Principle covers FALDH"],
        ["Guideline Refinement", "No", "Kept two, added a third exclusion"],
        ["LLM Annotation", "No, by design", "Still not annotated"],
    ], [3.9, 2.3, 5.467], 0.5, colors={(4, 1): RED, (4, 2): RED}, bold={(4, 0), (4, 1), (4, 2)})
    place(s, 2, y=2.45)
    put(s, 1, "The only rewriting step never sees gold")
    place(s, 1, y=5.95)

    # 11 Why Guideline Refinement wrote them
    s = new_slide(prs, "08 Figure comparison",
                  "The saved round-4 Guideline Refinement prompt contains, in order: the current (round-3) guideline, "
                  "the new principle, 'CONSTRAINT: DO NOT BREAK THESE EXAMPLES' with the verified examples, and "
                  "instructions; no discrepancy cases and no gold. Verified examples guard against regression (base "
                  "paper section 3.4.4): each is a whole development document as plain text plus at most 5 of its "
                  "correct annotations, introduced as 'currently handled CORRECTLY'; missed gold entities are not "
                  "marked. They are the first five development documents, sorted by file name, that have a correct "
                  "annotation; FALDH's document is the fourth, so it is shown every round. Instruction 3: 'If a "
                  "trade-off is required, prioritize specific sub-cases to avoid regression.' The output files FALDH "
                  "under the exception rule. The last step is inferred from the prompts; the model's reasoning is not "
                  "observed. Midterm point 1: verified examples are copied into the guideline; point 2: they never "
                  "change with the error cluster.")
    put(s, 0, "Why Guideline Refinement excluded FALDH")
    put(s, 1, "What the step receives", size=20)
    put(s, 3, "What follows (inferred)", size=20)
    drop(s, 4)
    drop(s, 2)
    boxed_text(s, 0.833, 2.92, 5.583, 2.85,
               ["Verified examples: 5 whole documents",
                "Shown so correct cases stay correct",
                "Labeled “handled CORRECTLY”",
                "Always the first five by file name",
                [("Missed gold is never marked", {"bold": True, "color": RED})]],
               size=20, inset=0.25, anchor=MSO_ANCHOR.TOP, space_after=8, name="refinement-inputs")
    boxed_text(s, 6.917, 2.92, 5.583, 2.85,
               ["FALDH's document is the fourth",
                "FALDH appears there unannotated",
                "Told: avoid regression on examples",
                [("Output: FALDH filed as excluded", {"bold": True, "color": RED})]],
               size=20, inset=0.25, anchor=MSO_ANCHOR.TOP, space_after=8, name="consequence")
    put(s, 5, "Midterm points 1 and 2 meet in this case")

    # 12 Tests
    s = new_slide(prs, "13 Ablation table",
                  "Re-annotation of the FALDH document only, GPT-5.4 high, same prompt template as the original run; "
                  "the annotator never sees gold. Round-4 principle alone: the four label definitions plus the "
                  "principle, no other guideline text; FALDH labeled as a disease 3 of 3. Without named exclusions: "
                  "round 4 minus lines 54 to 58, 167 and 263; round 3 minus lines 41 to 45 and 241; everything else "
                  "verbatim. Round 4 then gets FALDH exactly right 3 of 3 and the document 14 of 14 with no false "
                  "positive; round 3 still misses FALDH 5 of 5. Runs on 10/14 (first three rows) and 10/17 (last row).")
    put(s, 0, "Tests: named exclusions block the fix")
    label_above(s, "FALDH document, re-annotated with each guideline", y=2.0)
    table_at_placeholder(s, 2, [
        ["Guideline given to the annotator", "FALDH result"],
        ["Round-4 principle alone", "Labeled as disease, 3 of 3"],
        ["Full round-4 guideline", "Missed, 0 of 3"],
        ["Round 4 without named exclusions", "Exactly right, 3 of 3"],
        ["Round 3 without named exclusions", "Missed, 0 of 5"],
    ], [6.4, 5.267], 0.58, colors={(1, 1): GREEN, (2, 1): RED, (3, 1): GREEN, (4, 1): RED},
        bold={(1, 1), (2, 1), (3, 1), (4, 1)})
    place(s, 2, y=2.5)
    put(s, 1, "Exclusions block the fix; round 4's principle is also needed")

    # 13 Midterm points then and now
    s = new_slide(prs, "12 Results table",
                  "Point 1: removing the verified examples from the Guideline Refinement prompt (tested at the "
                  "midterm) stopped the copying, but the loop no longer reached development F1 0.9. Since then, the "
                  "case study shows the same input also produces named exclusions that contradict gold. Point 2: "
                  "verified examples are always the first five development documents by file name. Point 3: the loop "
                  "discards the rationale each annotation gives; missed mentions have none. Point 5: round 4 was kept "
                  f"at development F1 {f3(ev['r4_dev'])}; with the rerun values of two unstable labels it would be "
                  f"{f3(ev['r4_rerun_dev'])}, below round 3 ({f3(ev['r3_dev'])}), so the loop would have undone it; "
                  "across 13 saved loops, 14 of the 18 kept rounds gained less than the noise band 0.0416. Point 6: "
                  "top-4 gave the best single validation score (0.8023), but its gain is not established. Point 4 "
                  "(10 development documents do not cover the validation error types) is not explored further. New: "
                  "SpecificDisease and DiseaseClass mix-ups are the largest loss under exact span and subtype.")
    put(s, 0, "Midterm points: then and now")
    label_above(s, "Point 4 (coverage of the development set) is dropped", y=2.0)
    table_at_placeholder(s, 2, [
        ["Midterm point", "At the midterm", "Since the midterm"],
        ["1  Verified examples copied", "Removal stalls the loop", "Also cause named exclusions"],
        ["2  Verified examples never change", "Untested", "Always the first five files"],
        ["3  Rationales unused", "Untested", "Still untested"],
        ["5  One annotation is noisy", "SD 0.015", "14 of 18 gains within noise"],
        ["6  One cluster per round", "top-4 being tested", "top-4 best, gain unproven"],
    ], [4.3, 3.2, 4.167], 0.5)
    place(s, 2, y=2.45)
    put(s, 1, "New: subtype mix-ups are the largest loss")
    place(s, 1, y=5.95)

    # 14 Expert workload today
    s = new_slide(prs, "12 Results table",
                  "Edits needed to turn the LLM output into the gold annotation, counted with the base paper's "
                  "discrepancy categories on the 100 validation documents (one run per guideline). Totals also "
                  f"include overlaps that fit no category ({co[5]} and {ct[5]}). From scratch, all 791 mentions must "
                  "be created. Adding a missed mention is the costliest edit because it has to be found in the text; "
                  "deleting an extra one is a click. These are counts of edits, not minutes: time needs real experts. "
                  "Published pre-annotation studies: Neveol et al. 2010, 28.9% fewer actions; Lingren et al. 2014, "
                  "13.85% to 21.5% less time per entity; an LLM user study (AnnoHID, ACL 2026 demo) saw no time saved.")
    put(s, 0, "Expert workload today: edits to reach gold")
    label_above(s, "100 validation documents, 791 gold mentions; one run each", y=2.0)
    table_at_placeholder(s, 2, [
        ["Starting point", "Total", "Add missed", "Delete extra", "Fix boundary", "Fix subtype"],
        ["Nothing (from scratch)", "791", "791", "0", "0", "0"],
        ["Original guideline", str(co[0]), str(co[1]), str(co[2]), str(co[3]), str(co[4])],
        ["top-4 refined guideline", str(ct[0]), str(ct[1]), str(ct[2]), str(ct[3]), str(ct[4])],
    ], [3.4, 1.35, 1.75, 1.75, 1.75, 1.667], 0.58, center_cols=(1, 2, 3, 4, 5), bold={(3, 2)})
    place(s, 2, y=2.5)
    put(s, 1, f"Costliest edit, adding missed mentions: {co[1]} → {ct[1]}")

    # 15 DeepSeek
    s = new_slide(prs, "05 Key points",
                  "Cost per full annotation call, estimates: GPT-5.4 high JPY 55 to 88; DeepSeek V4.1 flash JPY 2.2 to "
                  "3.5 with thinking at the same output length, JPY 0.07 with thinking off "
                  "(nodes/2026-10-20_meeting/plan-v3/node_cost_output.txt). Best possible p: two methods are compared by an "
                  "exact permutation test on their loop-level validation scores. With 4 loops each there are "
                  "C(8,4) = 70 ways to split the 8 scores into two groups; even if every loop of one method beats "
                  "every loop of the other, that split and its mirror are 2 of 70, so p cannot go below 2/70 = 0.029, "
                  "which fails a correction for three comparisons (0.029 x 3 = 0.086). With 5 each: C(10,5) = 252, "
                  "p can reach 2/252 = 0.008. The stability test (thinking on and off, 5 repeats on 10 documents) "
                  "comes first. GPT-5.4 and DeepSeek results are never mixed in one comparison.")
    put(s, 0, "Next: reproduce main results on DeepSeek")
    put(s, 1, ["GPT-5.4: about JPY 55 to 88 per call",
               "DeepSeek: about JPY 2 to 4 per call",
               "Repeats decide whether a gain is real",
               "4 loops per method: best possible p 0.029",
               "5 loops per method: best possible p 0.008",
               "First, measure DeepSeek's own noise"], bullets=True, space_after=8)

    # 16 Goal 1 changes
    s = new_slide(prs, "12 Results table",
                  "Each change alters one thing and is compared with the 5 loops of the same method from the DeepSeek "
                  "reproduction (top-4 or top-1, whichever the reproduction supports). Delete named exclusions: unlike "
                  "the midterm test, the verified examples stay in the prompt; after refinement, the finished guideline "
                  "is scanned against development gold and only the named exclusions that contradict gold are "
                  "deleted, keeping the general rule text; the two flagged documents are re-annotated 3 times before "
                  "and after (12 calls). Pick verified examples by error cluster: the five documents shown are those "
                  "with correct annotations of the target cluster's gold type, instead of the first five by file name "
                  "(810 calls). Rationales: the annotator's rationale for each wrong entity is given to Pattern "
                  "Explanation, the step that infers why an error happened; missed entities have none (810 calls). "
                  "Separate subtype call: a short call decides only the subtype of each found span; first on 30 "
                  "development documents (120 calls), then validation only if mix-ups halve (200 calls).")
    put(s, 0, "Goal 1: four changes, tested one at a time")
    label_above(s, "Each compared with 5 loops of the same method on DeepSeek", y=2.0)
    table_at_placeholder(s, 2, [
        ["Change", "Midterm point", "Success means"],
        ["Delete named exclusions against gold", "1", "Target fixed, nothing new broken"],
        ["Pick verified examples by error cluster", "2", "Fewer named exclusions"],
        ["Give rationales to Pattern Explanation", "3", "More targets fixed next round"],
        ["Decide the subtype in a separate call", "New", "Subtype mix-ups halved"],
    ], [5.2, 2.0, 4.467], 0.58, center_cols=(1,))
    place(s, 2, y=2.5)
    put(s, 1, "A gain counts only if its 95% CI excludes 0")

    # 17 Goal 2
    s = new_slide(prs, "12 Results table",
                  "What saved data can and cannot show. Edits to reach gold: counted by comparing saved LLM output "
                  "with the gold annotation, no new calls. Where errors concentrate: entities on which runs disagree "
                  "are more often wrong, so experts can look there first. Minutes per document and the quality of an "
                  "expert's own annotation cannot be read from saved data; they need an expert annotation study. "
                  "Proposed crossover: two experts, the 100 validation documents; expert A annotates documents 1 to 50 "
                  "from scratch and 51 to 100 on the LLM pre-annotation, expert B the reverse.")
    put(s, 0, "Goal 2: measuring expert workload")
    label_above(s, "Saved data give edit counts; time needs real experts", y=2.0)
    table_at_placeholder(s, 2, [
        ["Measure", "Possible now?", "How"],
        ["Edits to reach gold", "Yes", "Compare LLM output with gold"],
        ["Where errors concentrate", "Yes", "Disagreement across runs"],
        ["Minutes per document", "No", "Expert annotation study"],
        ["Expert annotation quality", "No", "Expert annotation study"],
    ], [4.2, 2.4, 5.067], 0.55, colors={(3, 1): RED, (4, 1): RED})
    place(s, 2, y=2.5)
    put(s, 1, "Proposed: 2 experts, 100 documents, half with LLM")

    # 18 Timeline
    s = new_slide(prs, "16 Timeline",
                  "Code changes: picking verified examples by error cluster, and giving rationales to Pattern "
                  "Explanation. Reproduction: 5 loops per method on DeepSeek. Deletion check: the 12-call test of "
                  "deleting named exclusions. Experiments end in early December (9/15 plan), then writing. The expert "
                  "study runs in November only if it is approved and funded; the test split is used once, after the "
                  "pipeline is frozen and only with the authors' agreement.")
    put(s, 0, "Plan: six weeks")
    for i, (when, task) in enumerate((("Oct 20 to 26", ["Stability test", "Code changes"]),
                                      ("Oct 27 to Nov 2", ["Reproduction", "Deletion check"]),
                                      ("Nov 3 to 16", ["Example choice", "Rationales", "Subtype call"]),
                                      ("Nov 17 to 30", ["Workload analysis", "Test split, once"]))):
        put(s, 1 + 2 * i, when)
        put(s, 2 + 2 * i, task, space_after=4)
    put(s, 9, "Experiments end early December, then writing")

    # 19 Cost
    s = new_slide(prs, "12 Results table",
                  "DeepSeek ranges: thinking off (low end) to thinking on at the length of GPT-5.4 high (high end); "
                  "output length was never measured, so all figures are estimates. Required steps: stability test, "
                  "reproduction, deletion check, the two prompt changes, subtype pilot. All steps add subtype "
                  "validation and the test split. Expert study: 1.4 to 6.9 minutes per document from published "
                  "speeds, 4 to 8 training hours per person, wage JPY 1,500 to 5,000 per hour as placeholders "
                  "(nodes/2026-10-20_meeting/plan-v3/expert_study_size_output.txt).")
    put(s, 0, "Cost estimates")
    table_at_placeholder(s, 2, [
        ["Item", "Estimate"],
        ["DeepSeek, required steps (3,876 calls)", "JPY 377 to 13,475"],
        ["DeepSeek, all steps (4,376 calls)", "JPY 412 to 15,236"],
        ["Expert pilot: 1 person, 40 documents", "JPY 7,396 to 63,159"],
        ["Expert study: 2 people, 100 documents", "JPY 18,979 to 195,794"],
    ], [7.0, 4.667], 0.58)
    place(s, 2, y=2.2)
    put(s, 1, "Wage unknown; JPY 1,500 to 5,000 per hour assumed")

    def small_table(gf, size=16):
        for row in gf.table.rows:
            for cell in row.cells:
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(size)

    # 20 Questions for the authors
    s = new_slide(prs, "12 Results table",
                  "1: base paper section 3.4.4: 'We provide the current guideline, the newly generated principle, and "
                  "the discrepancy context.' The released code (llm-guideline-moderation-official, iterative.py, "
                  "render of refine_guidelines) passes only the guideline, the principle and the verified examples. "
                  "Our diagnosis (Guideline Refinement never sees gold, and wrote the named exclusions) holds for the "
                  "code; if the paper's runs passed the discrepancy context, it may not hold for them. 2: "
                  "_build_true_positive_examples walks the development documents in file-name order and takes the "
                  "first five with at least one correct entity. If the order was a deliberate choice, picking by error "
                  "cluster changes the design; if not, it is a fair fix. 3: top-4 run, 21 SpecificDisease to "
                  "DiseaseClass and 21 the other way; if part of this is gold inconsistency, the subtype step has a "
                  "lower ceiling. 4: PubAnnotation lists projects such as ncbi-valid-gemini-r-m; if they hold the "
                  "base paper's runs, we can rescore them with one entity type and compare gains on both scales. 5: "
                  "any human annotation other than gold (for example single-annotator files from the NCBI corpus "
                  "team) gives an expert-versus-gold level without hiring annotators.")
    put(s, 0, "Questions for the authors")
    label_above(s, "Facts only you can confirm, and what each answer changes", y=1.95)
    gf = table_at_placeholder(s, 2, [
        ["Question", "What the answer decides"],
        ["Paper §3.4.4 gives Guideline Refinement the discrepancy context; the released code does not. "
         "Which did your runs use?", "Whether our diagnosis holds for your runs"],
        ["Verified examples are the first five files with a correct entity. Was that order intended?",
         "Whether picking examples by cluster is fair"],
        ["SpecificDisease ↔ DiseaseClass errors, 21 each way: your largest loss too? Model or gold?",
         "Whether the subtype step is worth running"],
        ["Are the PubAnnotation “ncbi-valid” projects your GPT-5 runs?", "Base paper scored on one entity type"],
        ["Besides gold, any human annotation of the 100 documents?", "Expert level without hiring annotators"],
    ], [7.6, 4.067], 0.45)
    small_table(gf)
    place(s, 2, y=2.4)
    drop(s, 1)

    # 21 Decisions needed today
    s = new_slide(prs, "12 Results table",
                  "Test split: the base paper withheld the official test split for future benchmarking; one run of the "
                  "frozen pipeline (300 calls) would compare with supervised SOTA on the same split. Workload measure: "
                  "edit counts come from saved data at no cost; minutes need a timed study. Timed pilot: 1 annotator, "
                  "20 documents from scratch and 20 on the LLM pre-annotation, about 4.9 to 12.6 hours including "
                  "training, JPY 7,396 to 63,159 at a placeholder wage of JPY 1,500 to 5,000 per hour; it also measures "
                  "how much time per document varies, which sets the size of a full study. Main model: DeepSeek V4.1 "
                  "flash for cost; GPT-5.4 results stay as the case study, never mixed in one comparison. Overlap: our "
                  "two new steps are deleting named exclusions that contradict gold, and picking verified examples by "
                  "error cluster.")
    put(s, 0, "Decisions needed today")
    gf = table_at_placeholder(s, 2, [
        ["Decision", "Options", "Our proposal"],
        ["Official test split", "Use once at the end, or never", "Once, after freezing"],
        ["Workload measure", "Edit counts, or plus timed study", "Edit counts plus a pilot"],
        ["Timed pilot: 1 annotator, 40 documents", "Fund (JPY 7k to 63k), or skip", "Fund, if someone is available"],
        ["Main model", "DeepSeek V4.1 flash, or GPT-5.4", "DeepSeek; GPT-5.4 as case study"],
        ["Overlap with your current work", "Deleting named exclusions; picking examples by cluster", "Tell us which steps overlap"],
    ], [4.3, 3.8, 3.567], 0.5)
    small_table(gf)
    place(s, 2, y=2.0)
    drop(s, 1)

    normalize_slide_ids(prs)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"saved {out} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
