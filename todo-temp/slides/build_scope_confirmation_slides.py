"""Build the 2026-10-23 seminar deck: scope confirmation before the experiments (English).

Purpose: agree with the supervisor on the thesis requirements before any paid experiment, so that the plan, the
slides and the experiments match. The deck is built around four questions (the user's, from the slide-15 note of
the first draft, Chinese originals in the speaker notes): one main line plus one supplementary analysis; error
analysis plus one targeted change as the contribution; how deep the error analysis must go; what result finishes the
thesis. They open the deck as the agenda and close it as the decision slides; the slides between are evidence.
Proposals are marked as proposals; every item has a status. No GPT-5.4 numbers. Revised 2026-10-23 after the user's
notes on the first draft (questions Q1 to Q15 of that review).

Every number on a slide is asserted against a saved file in load_evidence():
    todo-temp/haiku-trial/fn_noise_with_max_output.txt    dev10 F1 and missed mentions, DeepSeek and Haiku xhigh
    todo-temp/haiku-trial/report_with_max_output.txt      Haiku xhigh cost per call; Haiku minus DeepSeek
    todo-temp/deepseek-stability/actual_cost_output.txt   DeepSeek cost per call at the price each call paid
    todo-temp/haiku-trial/loop4_estimate_output.txt       one four-round loop and one validation run, Haiku and DeepSeek
    todo-temp/haiku-trial/phase1_budget_output.txt        spend so far; one loop; rest of the reproduction
    todo-temp/haiku-trial/vote_curve_output.txt           voting across the 20 Haiku dev10 runs
    outputs/ncbi_disease/20261022_haiku-xhigh_topk{1,4}_loop01/   pilot loops (status, snapshots, valid metrics)

    python todo-temp/slides/build_scope_confirmation_slides.py [output.pptx]
"""
from __future__ import annotations

import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from build_faldh_slides import (FIG1, FIG1_ASPECT, GREEN, MUTED, NAVY, RED, STRONG, TEMPLATE,  # noqa: E402
                                boxed_text, drop, label_above, new_slide, normalize_slide_ids, place, put,
                                table_at_placeholder)

OUT = ROOT.parent / "presentations/20261023_scope_confirmation_en.pptx"
PILOT = ROOT / "outputs/ncbi_disease"

# The four thesis-requirement questions: (agenda line, question, our proposal, please confirm, Chinese original)
QUESTIONS = [
    ("One main line plus one supplementary analysis?",
     "Should the thesis converge on one main line plus one supplementary analysis?",
     "Track 1, improving guideline refinement to raise annotation quality, is the main line. Track 2 only analyzes "
     "the FN/FP trade-off on outputs we already have: no timed expert study, and no claim that real working time "
     "goes down.",
     "Must both tracks be independent contributions, or can the thesis focus on doing Track 1 well?",
     "1. 论文是否收敛为“一条主线＋一项补充分析”？我想以 Track 1——改进指南 refinement、提高标注质量——作为论文主线。"
     "Track 2 只利用已有输出分析 FN／FP 的取舍，不另做人工计时，也不直接主张实际工时下降。这样的主次划分是否合适？"
     "需要确认：两条 Track 是否都必须形成独立贡献，还是可以集中做好 Track 1。"),
    ("Error analysis plus one targeted change: enough?",
     "Is “systematic error analysis plus one targeted change” the right scope for the contribution?",
     "top-1 and top-4 belong to the reproduction and its controls. The main contribution is the systematic error "
     "analysis and one refinement change chosen from it. Is this enough, or is a required piece missing?",
     "One main change is enough, rather than trying every candidate; which one is decided after the error analysis.",
     "2. “系统错误分析＋一个针对性改动”的贡献范围是否合适？我计划把 top-1／top-4 放在复现和对照部分，主要贡献集中在系统错误分析，"
     "以及根据分析选出的一个 refinement 改动。这个范围是否足够？还是您认为还缺少某个必须完成的研究内容？"
     "需要确认：是否只需选一个主要改动，而不必把六个候选都做一遍。具体改哪个，留到分类结果出来后决定。"),
    ("How deep must the error analysis go?",
     "How deep must the error classification and analysis go?",
     "Cover every error category, but analyze one main problem in depth and test a fix for it. For the other "
     "categories, report counts, typical cases and limits, without proposing a fix for each.",
     "Does “cover all errors” mean a complete classification, or must every category get a cause, a fix and "
     "a test?",
     "3. 错误分类与分析需要做到多深？错误分析是否可以采用“覆盖全部错误大类，但只对一个主要问题深入分析并验证改进”的方式？"
     "其他类别报告数量、典型现象和局限，而不逐一提出解决方法，这样是否满足您的要求？"
     "需要确认：“覆盖全部错误”要求的是分类完整，还是每一类都必须解释原因、设计改进并验证效果。"),
    ("What result is enough to finish the thesis?",
     "What is the completion standard for the thesis?",
     "If, after proper controls and repeated runs, the change gives no stable overall F1 gain, but the thesis clearly "
     "shows the benefits, limits and failure conditions of refinement: is that a complete conclusion? Or must the "
     "thesis contain a reliably verified performance gain?",
     "What evidence and conclusions are enough to finish, so the scope does not keep growing when no significant "
     "gain appears?",
     "4. 论文的完成标准是什么？如果经过充分对照和重复实验，改动没有带来稳定的整体 F1 提升，但能够清楚说明 refinement 的收益、"
     "局限和失败条件，这是否可以形成完整的研究结论？还是这篇论文必须包含一个得到可靠验证的性能改进？"
     "需要确认：怎样的证据和结论足以收尾，避免后期因为没有显著提升而不断扩大研究范围。"),
]


def grab(rel: str, pattern: str) -> tuple:
    m = re.search(pattern, (ROOT / rel).read_text(encoding="utf-8"))
    assert m, (rel, pattern)
    return m.groups()


def load_evidence() -> dict:
    ev = {}
    fn = "todo-temp/haiku-trial/fn_noise_with_max_output.txt"
    ev["ds_fn"], ev["ds_f1"] = grab(fn, r"DeepSeek B_on: 20 complete repeats;.*FN ([\d.]+) SD.*; F1 ([\d.]+) SD")
    ev["hk_fn"], ev["hk_f1"] = grab(fn, r"Haiku H_xhigh: 20 complete repeats;.*FN ([\d.]+) SD.*; F1 ([\d.]+) SD")
    assert (ev["ds_fn"], ev["ds_f1"], ev["hk_fn"], ev["hk_f1"]) == ("16.80", "0.8062", "22.15", "0.7605")

    rep = "todo-temp/haiku-trial/report_with_max_output.txt"
    (ev["hk_call"],) = grab(rep, r"H_xhigh: 200/200 ok.*\n.*\n    cost JPY [\d.]+ at batch price, per call mean ([\d.]+)")
    assert ev["hk_call"] == "0.511"
    ev["diff"] = grab(rep, r"H_xhigh minus DeepSeek: (-[\d.]+), t .*95% CI \[(-[\d.]+), (-[\d.]+)\]")
    assert ev["diff"] == ("-0.0457", "-0.0568", "-0.0346")

    (ev["ds_call"],) = grab("todo-temp/deepseek-stability/actual_cost_output.txt",
                            r"units B_on: 200 calls, 22 at peak; JPY [\d.]+, per call mean ([\d.]+)")
    assert ev["ds_call"] == "1.409"

    est = "todo-temp/haiku-trial/loop4_estimate_output.txt"
    ev["loop4_hk"], ev["loop4_ds"] = grab(est, r"top-4, 4 rounds, 186 calls.*\n  Haiku xhigh Batch: JPY ([\d.]+) .*\n"
                                               r"  DeepSeek off-peak: JPY ([\d.]+) ")
    assert (ev["loop4_hk"], ev["loop4_ds"]) == ("148.33", "372.43")
    ev["valid_hk"], ev["valid_ds"] = grab(est, r"one valid100 run with the original guideline \(pilot top-1 loop, "
                                               r"100 calls\): Haiku xhigh Batch JPY ([\d.]+); DeepSeek off-peak JPY ([\d.]+)")
    assert (ev["valid_hk"], ev["valid_ds"]) == ("63.38", "154.03")
    assert "largest output in one call: 112,135 tokens" in (ROOT / est).read_text(encoding="utf-8")

    bud = (ROOT / "todo-temp/haiku-trial/phase1_budget_output.txt").read_text(encoding="utf-8")
    for line in ("one original-guideline valid100 run: JPY 63.38",
                 "like the pilot: top-1 loop JPY 75.96, top-4 loop JPY 199.19; rest of phase 1 (9 + 9 loops, "
                 "10 runs) JPY 3,110",
                 "four rounds each: top-1 loop JPY 110.09, top-4 loop JPY 148.33; rest of phase 1 (9 + 9 loops, "
                 "10 runs) JPY 2,960",
                 "spent, DeepSeek stability test and probe: JPY 303.30",
                 "spent, Haiku dev10 trial (high, xhigh, max): JPY 451.48",
                 "spent, Haiku batch pilot (two loops): JPY 284.89",
                 "spent since 10/21, total: JPY 1,040"):
        assert line in bud, line

    vote = (ROOT / "todo-temp/haiku-trial/vote_curve_output.txt").read_text(encoding="utf-8")
    assert "H_xhigh: 20 complete repeats x 10 documents; gold mentions 74" in vote
    assert "single run, mean of 20: kept 62.4, FP 10.50, FN 22.15, precision 0.8316, recall 0.7007, F1 0.7605" in vote
    assert "rules fixed in advance: union k = 1; majority (more than half) k = 11; unanimous k = 20" in vote
    rows = {int(m[0]): m[1:] for m in re.findall(r"^ ?(\d+) \| \d+ \| \d+ \| (\d+) \| (\d+) \| [\d.]+ \| [\d.]+ \| "
                                                  r"([\d.]+)$", vote, re.M)}
    ev["vote"] = {"union": rows[1], "majority": rows[11], "unanimous": rows[20]}
    assert ev["vote"] == {"union": ("17", "16", "0.7785"), "majority": ("10", "21", "0.7737"),
                          "unanimous": ("8", "32", "0.6774")}, ev["vote"]

    for name, rounds, start, last, valid, fn_, fp in (("topk1", 1, 0.7681, 0.7591, 0.6986, 288, 146),
                                                      ("topk4", 6, 0.7313, 0.9583, 0.7411, 237, 150)):
        run = PILOT / f"20261022_haiku-xhigh_{name}_loop01"
        status = json.loads((run / "status.json").read_text(encoding="utf-8"))
        assert status["iterations"] == rounds and status["valid_strict_f1"] == valid, status
        assert round(status["initial_f1"], 4) == start, status
        snaps = [json.loads((run / f"rounds/iteration_{i:02d}/snapshot.json").read_text(encoding="utf-8"))
                 for i in range(1, rounds + 1)]
        assert round(snaps[-1]["summary_candidate"]["overall_f1"], 4) == last, name  # the last round's candidate
        ev[name] = {"kept": sum(s["improved"] for s in snaps), "rounds": rounds, "start": start, "last": last,
                    "valid": valid}
        m = json.loads((run / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
        assert (m["f1"], m["false_negatives"], m["false_positives"], m["gold_total"]) == (valid, fn_, fp, 791), m
        ev[name].update(fn=fn_, fp=fp)
    assert ev["topk1"]["kept"] == 0 and ev["topk4"]["kept"] == 6
    return ev


def f3(x) -> str:
    """Three decimals, half up (0.7605 -> 0.761; a float format would give 0.760)."""
    return str(Decimal(str(x)).quantize(Decimal("0.001"), ROUND_HALF_UP))


def small_table(gf, size=16) -> None:
    for row in gf.table.rows:
        for cell in row.cells:
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size)


def question_block(slide, y, number, q) -> None:
    """One thesis-requirement question: the question, our proposal, and what we ask the supervisor to confirm."""
    _, question, proposal, confirm, _ = q
    boxed_text(slide, 0.833, y, 11.667, 1.95,
               [[(f"{number}. {question}", {"bold": True, "color": NAVY, "size": 18})],
                [("Our proposal: ", {"bold": True}), (proposal, {})],
                [("Please confirm: ", {"bold": True, "color": STRONG}), (confirm, {"color": STRONG})]],
               size=15, inset=0.18, anchor=MSO_ANCHOR.TOP, space_after=6, name=f"question-{number}")


def build(out: Path = OUT) -> None:
    ev = load_evidence()
    prs = Presentation(TEMPLATE)
    sld_ids = prs.slides._sldIdLst
    for sld_id in list(sld_ids):  # drop the template's sample slides
        prs.part.drop_rel(sld_id.rId)
        sld_ids.remove(sld_id)
    t1, t4 = ev["topk1"], ev["topk4"]
    jpy = lambda x: f"JPY {float(x):,.0f}"  # noqa: E731

    # 1 Cover
    s = new_slide(prs, "01 Cover", "Seminar with the supervisor, 23 October 2026. Goal: agree on the thesis "
                  "requirements and the scope of the experiments before any paid run. Follows "
                  "docs/RP/20261020_research_plan_v4.md; nothing in this deck is decided yet.")
    put(s, 0, "The University of Tokyo")
    put(s, 1, ["Optimizing Annotation Guideline Refinements", "for LLM-Based Annotation"], size=40)
    put(s, 2, "Hengyu Zhou")
    put(s, 3, "Scope check before the experiments, 23 October 2026")

    # 2 Today's goal
    s = new_slide(prs, "03 Research question",
                  "Nothing in this deck is decided. Items marked 'proposal' wait for your answer; costs beyond the "
                  "pilot are estimates. After today the research plan and these slides are revised to match your "
                  "answers, reviewed once more, and sent to you by e-mail; paid experiments start only after your "
                  "approval of that e-mail.")
    put(s, 0, "Today's goal")
    put(s, 1, ["Agree on the thesis scope before any paid experiment",
               [("One main line, one main change, the analyses it needs", {"size": 22, "color": MUTED})]],
        space_after=12)
    put(s, 2, "For each item: must do, optional, not done, or decided later")

    # 3 Agenda: the four questions
    s = new_slide(prs, "04 Outline", "The four questions this seminar should settle; each comes back at the end with "
                  "our proposal and what we ask you to confirm. Chinese originals:\n" +
                  "\n".join(q[4] for q in QUESTIONS))
    put(s, 0, "Four questions for today")
    for i, q in enumerate(QUESTIONS):
        put(s, 1 + i, q[0])

    # 4 The loop under test
    s = new_slide(prs, "07 Full figure",
                  "Figure 1 of the base paper (archive/references/backbone-research.pdf, page 3), stage names as in the "
                  "paper. Each round: LLM Annotation of the development documents with the current guideline, "
                  "Evaluation against their gold annotation, then Discrepancy Analysis (group the errors into "
                  "clusters), Pattern Explanation, Principle Generation (an IF-THEN rule) and Guideline Refinement "
                  "(rewrite the guideline with the principle). top-1 refines the largest cluster per round, as in the "
                  "base paper; top-4 the four largest, with one rewrite. A round is kept only if development F1 "
                  "improves; the loop stops at the first round that does not improve, at F1 0.9, or after 20 rounds. "
                  "Development: 10 NCBI Disease training documents with gold, which the loop sees. Validation: the base "
                  "paper's 100 documents (791 gold mentions), never shown to the loop. F1 here is exact span and "
                  "subtype F1: a predicted mention counts only if its span and one of the four subtypes both match "
                  "gold (the base paper's measure).")
    put(s, 0, "The refinement loop under test")
    label_above(s, "The loop learns from 10 development documents; scored on 100 validation documents")
    drop(s, 1)
    fig_h = 3.35
    fig_w = fig_h * FIG1_ASPECT
    fig = s.shapes.add_picture(str(FIG1), Inches(0.833 + (11.667 - fig_w) / 2), Inches(2.5), height=Inches(fig_h))
    fig.name = "base-paper-figure-1"
    fig._element.nvPicPr.cNvPr.set("descr", "Figure 1 of the base paper: LLM Annotation and Evaluation, then "
                                   "Moderation (Discrepancy Analysis, Pattern Explanation, Principle Generation, "
                                   "Guideline Refinement).")
    put(s, 2, "top-1: refine the largest error cluster per round; top-4: the four largest")

    # 5 Six comments from the midterm
    s = new_slide(prs, "12 Results table",
                  "The six comments on the midterm, as listed on the 10/20 deck (slide 3): the supervisor's e-mail of "
                  "9/12 and the reviewers' questions. 'Answer in the plan' is where research plan v4 stands now. "
                  "Modify or delete rules: settled, because Guideline Refinement already rewrites the whole guideline "
                  "every round. The last comment (midterm point 4, coverage of the development set) is not explored "
                  "further. The two scenarios are explained on the Track slide.")
    put(s, 0, "Six questions from the midterm")
    gf = table_at_placeholder(s, 2, [
        ["Comment", "Answer in the plan", "Status"],
        ["F1 0.8 is not enough to replace annotators", "Replacement is not claimed", "Settled"],
        ["Frame the LLM as support", "A scenario with expert correction", "To confirm"],
        ["Refinement should also modify or delete rules", "The rewrite already edits the whole guideline", "Settled"],
        ["How to balance cost and quality?", "Cheaper model; extra for fewer missed", "To confirm"],
        ["What exactly is the research goal?", "Two scenarios, one main line", "To confirm"],
        ["Are 10 development documents biased?", "Not explored further", "Dropped"],
    ], [4.9, 4.767, 2.0], 0.46, colors={(2, 2): STRONG, (4, 2): STRONG, (5, 2): STRONG, (6, 2): MUTED},
        bold={(2, 2), (4, 2), (5, 2)})
    small_table(gf)
    place(s, 2, y=2.2)
    put(s, 1, "Today: the three marked 'To confirm'")

    # 6 Status
    s = new_slide(prs, "12 Results table",
                  "Repeated-run test: the same guideline and documents annotated 20 times per setting, to measure how "
                  "much one run varies and to choose the model (16 to 22 October, DeepSeek and Haiku). Pilot: one "
                  "top-1 and one top-4 loop on Haiku, 22 October, to check that the pipeline runs end to end and to "
                  "measure cost. The reproduction reruns the method before anything is changed: the original guideline "
                  "10 times on validation, 10 top-1 loops and 10 top-4 loops. Everything after the pilot has not run.")
    put(s, 0, "Where things stand")
    gf = table_at_placeholder(s, 2, [
        ["Item", "Status"],
        ["Repeated-run test, model choice", "Done"],
        ["Pilot: one top-1 and one top-4 loop", "Done; no conclusion"],
        ["Reproduction: rerun the method, 10 loops each", "Needs your approval"],
        ["The one change after the reproduction", "Candidate, not chosen"],
        ["Costs beyond the pilot", "Estimates"],
    ], [6.6, 5.067], 0.46, colors={(1, 1): GREEN, (2, 1): GREEN, (3, 1): RED, (4, 1): STRONG, (5, 1): STRONG},
        bold={(i, 1) for i in range(1, 6)})
    small_table(gf)
    place(s, 2, y=2.2)
    put(s, 1, "Nothing beyond the pilot has run")

    # 7 Two scenarios
    s = new_slide(prs, "12 Results table",
                  "From the 10/20 meeting: not every annotation is corrected by experts. Benchmarks are; more and more "
                  "uses take LLM annotation as it is. Experts do not know which mentions are wrong, so they read every "
                  "document: deleting an extra mention is cheap, but adding a missed one needs the whole text, like "
                  "annotating by hand. So Track 2 counts missed mentions (false negatives, FN) first and extra "
                  "mentions (false positives, FP) as the price. Track 2 method: annotate the same documents N times "
                  "and keep a mention if at least k runs found it; the next slide shows how far this goes. It reuses "
                  "the reproduction's repeated validation runs, with no new API calls. Proposal: Track 1 is the main "
                  "line, Track 2 a supplementary analysis.")
    put(s, 0, "Two scenarios, one main line (proposal)")
    label_above(s, "Proposal for today: Track 1 is the main line, Track 2 supplementary", y=1.85)
    gf = table_at_placeholder(s, 2, [
        ["", "Track 1: used as is", "Track 2: corrected by experts"],
        ["Goal", "Better LLM annotation", "Less correction work for experts"],
        ["Main measure", "Exact span and subtype F1", "Missed mentions (FN); extra mentions (FP) are the price"],
        ["Method", "The base loop plus one targeted change", "Annotate N times; keep a mention at least k runs found"],
        ["New API calls", "Yes", "None: reuses the reproduction runs"],
        ["Role (proposed)", "Main line", "Supplementary analysis"],
    ], [2.4, 4.3, 4.967], 0.42, bold={(i, 0) for i in range(1, 6)} | {(5, 1), (5, 2)},
        colors={(5, 1): STRONG, (5, 2): STRONG})
    small_table(gf)
    place(s, 2, y=2.3)  # two wrapped rows; higher than the other tables so it clears the caption
    put(s, 1, "Track 2: how far repeated runs cut missed mentions, at what price")
    place(s, 1, y=6.2)

    # 8 Voting
    v = ev["vote"]
    s = new_slide(prs, "12 Results table",
                  "Haiku xhigh trial: the original guideline, the 10 development documents (74 gold mentions), 20 runs "
                  "with the same prompt. A mention (exact span and subtype) is kept if at least k of the 20 runs found "
                  "it. Only rules fixed in advance are shown: when experts use the output, no gold exists to pick k, "
                  "so a k chosen by its score here would be cheating. Majority: more than half, at least 11 of 20. "
                  "Majority barely cuts missed mentions (22.15 to 21); it mainly makes the output stable. Only a low "
                  "threshold such as union cuts them (to 16), at the price of more extra ones. 16 gold mentions are "
                  "found by no run, so no threshold can recover them; fixing those is Track 1's job. In the thesis the "
                  "threshold is fixed in advance, or chosen on the development documents and applied unchanged to the "
                  "repeated validation runs of the reproduction. Development documents, so illustration only "
                  "(todo-temp/haiku-trial/vote_curve_output.txt).")
    put(s, 0, "Track 2: voting across repeated runs")
    label_above(s, "Development documents, original guideline, 20 runs, 74 gold mentions; illustration only")
    table_at_placeholder(s, 2, [
        ["Rule, fixed in advance", "Missed (FN)", "Extra (FP)", "F1"],
        ["One run (average of 20)", ev["hk_fn"], "10.50", f3(ev["hk_f1"])],
        ["Majority: at least 11 of 20 runs", v["majority"][1], v["majority"][0], f3(v["majority"][2])],
        ["Union: any run found it", v["union"][1], v["union"][0], f3(v["union"][2])],
        ["Unanimous: all 20 runs found it", v["unanimous"][1], v["unanimous"][0], f3(v["unanimous"][2])],
    ], [5.2, 2.2, 2.2, 2.067], 0.55, center_cols=(1, 2, 3), bold={(3, 1)})
    place(s, 2, y=2.5)
    put(s, 1, f"{v['union'][1]} of 74 gold mentions are found by no run")

    # 9 Claims
    s = new_slide(prs, "08 Figure comparison",
                  "Gains are compared within one model: the base paper used GPT-5 (0.73 with the original guideline, "
                  "0.76 refined), our main model is Haiku, so an absolute comparison mixes models; the base paper's "
                  "numbers stay as a reference. Expert annotation is the gold; we do not claim the LLM reaches it. "
                  "Edits to reach gold: add missed, delete extra, fix boundary, fix subtype, counted against gold. "
                  "Expert minutes need a timed study, which is future work. Low resource: refinement learns from 10 "
                  "gold documents. 593 is the size of the NCBI Disease training split that supervised models, "
                  "including the SOTA, were trained on; it is not a measured minimum. A published learning curve is "
                  "cited as outside support only (different split, one entity type).")
    put(s, 0, "What we claim, and what we do not")
    put(s, 1, "We claim, if the data hold", size=20)
    put(s, 3, "We do not claim", size=20)
    drop(s, 4)
    drop(s, 2)
    boxed_text(s, 0.833, 2.92, 5.583, 2.7,
               ["Performance gains, compared within one model",
                "Scored on 100 validation documents",
                "Fewer edits needed to reach gold",
                "Low resource: refinement uses only 10 gold documents"],
               size=18, inset=0.25, anchor=MSO_ANCHOR.TOP, space_after=10, name="claims")
    boxed_text(s, 6.917, 2.92, 5.583, 2.7,
               ["Quality equal to expert annotation",
                "Less expert time, before any timed study",
                "Supervised models need 593 documents",
                "An LLM can replace an annotator"],
               size=18, inset=0.25, anchor=MSO_ANCHOR.TOP, space_after=10, color=RED, name="not-claimed")
    put(s, 5, "593: the training split the supervised SOTA used")

    # 10 Main model
    ratio = round(100 * float(ev["loop4_hk"]) / float(ev["loop4_ds"]))
    assert ratio == 40
    s = new_slide(prs, "12 Results table",
                  "F1 and missed mentions: the repeated-run test, same prompt, the 10 development documents, 20 runs "
                  "per model. DeepSeek V4.1 flash with thinking on, standard API (22 of 200 calls fell in peak hours "
                  "at double price). Claude Haiku 5.5 at reasoning effort xhigh through the Batch API (requests "
                  f"submitted together, half price, answers within minutes). Haiku minus DeepSeek: {ev['diff'][0]}, "
                  f"95% CI [{ev['diff'][1]}, {ev['diff'][2]}] (Welch t-test). Why xhigh: high has the same mean with a "
                  "larger spread; max scores higher but costs 2.8 times as much per call and 5% of its replies were cut "
                  "off. Validation run: 100 calls with the original guideline; Haiku measured in the pilot, DeepSeek "
                  "estimated by pricing Haiku's token counts at DeepSeek's list price. Loop: rounds 1 to 4 of the pilot "
                  "top-4 loop plus one validation run; DeepSeek never ran a loop, so it is estimated the same way. A "
                  "top-4 rewrite needed up to 112,135 output tokens on Haiku; our DeepSeek setting stops a call at "
                  "64,000. GPT-5.4 results stay only as the earlier case study.")
    put(s, 0, "Main model: from DeepSeek to Haiku")
    label_above(s, "F1 and FN: 10 development documents, 20 runs per model; DeepSeek costs below estimated")
    gf = table_at_placeholder(s, 2, [
        ["", "DeepSeek V4.1 flash", "Claude Haiku 5.5"],
        ["F1, exact span and subtype", f3(ev["ds_f1"]), f3(ev["hk_f1"])],
        ["Missed mentions (FN) per run", ev["ds_fn"], ev["hk_fn"]],
        ["Cost per annotation call", f"JPY {float(ev['ds_call']):.2f}", f"JPY {float(ev['hk_call']):.2f}"],
        ["One validation run, original guideline", jpy(ev["valid_ds"]), jpy(ev["valid_hk"])],
        ["One top-4 loop, 4 rounds, with validation", jpy(ev["loop4_ds"]), jpy(ev["loop4_hk"])],
    ], [5.4, 3.133, 3.134], 0.5, center_cols=(1, 2))
    small_table(gf, 17)
    place(s, 2, y=2.5)
    put(s, 1, f"Haiku: F1 {abs(float(ev['diff'][0])):.3f} lower, loop cost about {ratio}%")

    # 11 Pilot
    s = new_slide(prs, "12 Results table",
                  "Haiku xhigh, Batch API, 22 October. top-1: its only candidate scored lower on the development "
                  "documents and was rejected, so its final guideline is the original one and its validation score is "
                  "one run of the original guideline. What this pilot compares is top-4's final guideline against the "
                  f"original guideline (+{t4['valid'] - t1['valid']:.4f}). That gap mixes any top-4 effect with two "
                  "variations not yet measured on Haiku: annotating the same guideline again, and a new loop writing a "
                  "different guideline. The two loops' first annotations used the same original guideline and scored "
                  f"{f3(t1['start'])} and {f3(t4['start'])} on development. top-4 stopped at the 0.9 threshold. The "
                  "output cap was raised to 128,000 tokens after the first top-4 rewrite was cut off at 64,000.")
    put(s, 0, "Pilot: one loop per method")
    label_above(s, "Haiku, 22 October; validation: 100 documents, exact span and subtype F1")
    table_at_placeholder(s, 2, [
        ["", "top-1 loop", "top-4 loop"],
        ["Rounds kept", f"{t1['kept']} of {t1['rounds']}", f"{t4['kept']} of {t4['rounds']}"],
        ["Development F1, start → last round", f"{f3(t1['start'])} → {f3(t1['last'])}, rejected",
         f"{f3(t4['start'])} → {f3(t4['last'])}"],
        ["Validation F1", f3(t1["valid"]), f3(t4["valid"])],
        ["Missed / extra mentions", f"{t1['fn']} / {t1['fp']}", f"{t4['fn']} / {t4['fp']}"],
        ["Cost, with validation", "JPY 76", "JPY 199"],
    ], [5.0, 3.333, 3.334], 0.5, center_cols=(1, 2))
    place(s, 2, y=2.5)
    put(s, 1, "One loop each: no conclusion yet")

    # 12 The reproduction
    s = new_slide(prs, "12 Results table",
                  "Defaults set on 10/22 before any Haiku noise data: 10 runs of the original guideline on validation, "
                  "10 loops per method, every loop's final guideline annotated once on validation. The pilot loops "
                  "count as loop 1 of 10. Each question compares the average validation F1 of two groups of 10 with a "
                  "Welch t-test (a test of whether two averages differ by more than their spread explains); 0.025 is "
                  "the usual 0.05 split over the two questions. The noise measured here also tells how precise the "
                  "comparisons are. All loops of a method advance together, one batch per step.")
    put(s, 0, "The reproduction: rerun before changing")
    label_above(s, "Every loop's final guideline is annotated once on validation")
    table_at_placeholder(s, 2, [
        ["Run", "Count", "Question it answers"],
        ["Original guideline, validation only", "10 runs", "How much one run varies"],
        ["top-1 loops", "10 loops", "Does top-1 beat the original?"],
        ["top-4 loops", "10 loops", "Does top-4 beat top-1?"],
    ], [4.6, 2.0, 5.067], 0.55, center_cols=(1,))
    place(s, 2, y=2.5)
    boxed_text(s, 0.833, 4.95, 11.667, 0.6, "Each question: 10 against 10 averages, t-test, p < 0.025",
               size=18, inset=0.2, name="rule")
    put(s, 1, "The pilot loops count as loop 1 of 10")

    # 13 Data use
    s = new_slide(prs, "12 Results table",
                  "Development: 10 NCBI Disease training documents with gold; the loop sees their gold. Validation: "
                  "the base paper's 100 documents; their gold is never shown to the loop, but comparing methods on "
                  "them again and again turns them into a set we choose with. Official test split: withheld by the "
                  "base paper; whether to use it once at the end is not decided.")
    put(s, 0, "Which data is used for what")
    label_above(s, "Validation is reused for choices; the test split is not decided")
    table_at_placeholder(s, 2, [
        ["Data", "Used for", "Never used for"],
        ["10 development documents", "Refinement: the loop sees gold", "Final claims"],
        ["100 validation documents", "Comparing methods, error analysis", "Refinement"],
        ["Official test split", "To be decided", "Any choice"],
    ], [3.8, 4.8, 3.067], 0.55, colors={(3, 1): STRONG}, bold={(3, 1)})
    place(s, 2, y=2.5)
    put(s, 1, "Gold of the validation documents never enters refinement")

    # 14 After the reproduction
    s = new_slide(prs, "12 Results table",
                  "Error taxonomy on the reproduction's validation outputs: every error sorted by kind (missed, extra, "
                  "boundary, subtype, by entity type) and by cause (a rule against gold, an exclusion too broad, not "
                  "covered, gold ambiguity, model instability, not in the development set); rules first, then 50 "
                  "checked by hand. Guideline Refinement's examples: the up to five development documents it sees as "
                  "'handled correctly'; the code always takes the first five by file name. Annotation reasons: each "
                  "annotation comes with a reason, which the loop discards. Two candidates come from the GPT-5.4 case "
                  "study; the choice is made only from the Haiku error counts. The change alters one thing and is "
                  "compared with the reproduction loops of the same method; it needs a second approval.")
    put(s, 0, "After the reproduction: one change")
    label_above(s, "First, sort every validation error by kind and cause")
    gf = table_at_placeholder(s, 2, [
        ["Candidate change", "Origin"],
        ["Delete guideline lines that contradict gold", "Case study, GPT-5.4"],
        ["Pick Guideline Refinement's examples by error type", "Code: always the first five files"],
        ["Give annotation reasons to Pattern Explanation", "Code: reasons are discarded"],
        ["Decide the subtype in a separate call", "Case study, GPT-5.4"],
        ["Redesign the clusters or the principle format", "Suggested at the 10/20 meeting"],
    ], [6.6, 5.067], 0.46)
    small_table(gf)
    place(s, 2, y=2.5)
    put(s, 1, "One change, chosen from the Haiku error counts")

    # 15 Cost
    s = new_slide(prs, "12 Results table",
                  "Like the pilot: every top-1 loop stops after 1 round and every top-4 loop after 6, as the pilot loops "
                  "did. Four rounds each: estimated from the pilot's top-4 rounds 1 to 4 and its two validation runs "
                  "(todo-temp/haiku-trial/loop4_estimate_output.txt). A loop can stop after 1 to 20 rounds, so a "
                  "longer loop costs more. Haiku Batch prices; the standard API doubles them. Calls cut off and "
                  "retried are not included (the pilot lost JPY 7.79 that way). Spent so far: DeepSeek tests JPY 303, "
                  "Haiku trial JPY 451, pilot JPY 285 (todo-temp/haiku-trial/phase1_budget_output.txt).")
    put(s, 0, "Cost: spent and expected")
    label_above(s, "Spent on tests since 21 October: JPY 1,040; a loop runs 1 to 20 rounds")
    table_at_placeholder(s, 2, [
        ["Item", "Like the pilot", "Four rounds each"],
        ["One validation run, original guideline", "JPY 63", "JPY 63"],
        ["One top-1 loop, with validation", "JPY 76", "JPY 110"],
        ["One top-4 loop, with validation", "JPY 199", "JPY 148"],
        ["Rest of the reproduction: 9 + 9 loops, 10 runs", "JPY 3,110", "JPY 2,960"],
    ], [6.0, 2.833, 2.834], 0.55, center_cols=(1, 2), bold={(4, 0), (4, 1), (4, 2)})
    place(s, 2, y=2.5)
    put(s, 1, "Estimates, not bounds: longer loops cost more")

    # 16 Process
    s = new_slide(prs, "16 Timeline",
                  "Steps of the work plan. Next week: the research plan and the slides are revised to today's answers "
                  "only, then checked once by an independent review of the experiment logic and feasibility, then sent "
                  "to you by e-mail with the design, data use, budget and collaboration boundary. After approval: "
                  "the reproduction, the error taxonomy, then one proposed change. After the second approval: the "
                  "change experiment runs as planned, without extra runs because a result looks poor; then the method "
                  "is frozen and the thesis is written from the runs actually done.")
    put(s, 0, "From today to the thesis")
    for i, (when, task) in enumerate((("Today", ["Agree on scope"]),
                                      ("Next week", ["Revise the plan", "Independent review", "E-mail for approval"]),
                                      ("After approval", ["Reproduction", "Error taxonomy", "Pick one change"]),
                                      ("Second approval", ["Change experiment", "Freeze the method", "Write the thesis"]))):
        put(s, 1 + 2 * i, when)
        put(s, 2 + 2 * i, task, space_after=4)
    put(s, 9, "No paid run before your e-mail approval")

    # 17, 18 Decisions: the four questions, two per slide
    for title, pair in (("Decisions today: main line and contribution", (0, 1)),
                        ("Decisions today: depth and finish", (2, 3))):
        s = new_slide(prs, "05 Key points", "Chinese originals:\n" + "\n".join(QUESTIONS[i][4] for i in pair))
        put(s, 0, title)
        drop(s, 1)
        for j, i in enumerate(pair):
            question_block(s, 2.0 + j * 2.2, i + 1, QUESTIONS[i])

    # 19 If time allows
    s = new_slide(prs, "12 Results table",
                  "Main model: Haiku's development F1 is 0.046 below DeepSeek's; a stronger-model control would run the "
                  "same method on a stronger model at extra cost. Second corpus: the plan has no step for BC5CDR or "
                  "BioRED. Cost: JPY 1,040 spent on tests since 21 October; the rest of the reproduction is estimated "
                  "at JPY 2,960 to 3,110 (todo-temp/haiku-trial/phase1_budget_output.txt).")
    put(s, 0, "If time allows")
    gf = table_at_placeholder(s, 2, [
        ["Question", "What the answer decides"],
        ["Is Haiku acceptable as the main model? Is a stronger-model control needed?", "Main model; cost"],
        ["Second corpus (BC5CDR or BioRED): required, optional, or out?", "Scope and budget"],
        ["Is the API cost reimbursed? Spent JPY 1,040; about JPY 3,000 to go", "How many loops we can run"],
    ], [7.9, 3.767], 0.55)
    small_table(gf)
    place(s, 2, y=2.2)
    put(s, 1, "Answers can also come by e-mail")

    normalize_slide_ids(prs)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"saved {out} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
