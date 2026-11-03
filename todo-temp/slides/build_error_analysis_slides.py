"""Build the error-analysis seminar deck (English) from the 10/24 error-analysis report (Chinese draft of 10/30).

Audience: the supervisor. The deck reports the main findings of the error analysis of the Haiku reproduction and
ends with questions on how to move the research goals forward. Local details of the report (line numbers, file
names, hand-coding categories, single-round traces) stay out; the backup slides hold three side results.

Terms follow the base paper and the earlier decks: round, loop, kept or rejected round, verified examples, LLM
Annotation, Evaluation, Discrepancy Analysis, Pattern Explanation, Principle Generation, Guideline Refinement,
original guideline, refined guideline, gold annotation, the four subtypes by their dataset names. "Missed mentions
(FN)" is the exact span and subtype false negative, as on the 10/23 deck; the paper's zero-overlap category is written
"missed with no overlapping prediction".

Every number on a slide is read from a saved output and asserted in load_evidence():
    todo-temp/seminar-20261023/reproduction_analysis_output.txt   method means, top-4 minus original and its interval
    todo-temp/error-analysis/outputs/error_overview.json           F1 of the 19 original runs and the 11 refined guidelines;
                                                                   change in exact matches per gold subtype
    todo-temp/error-analysis/outputs/error_overview_output.txt     rank correlations; counts outside the original range
    todo-temp/error-analysis/outputs/modifier_subset_output.txt    Modifier mislabels by position (P); copied phrases (Q)
    todo-temp/error-analysis/outputs/cited_sections_output.txt     the annotator's stated guideline section (B)
    todo-temp/error-analysis/outputs/history_tally_output.txt      family-history rule per round
    todo-temp/error-analysis/outputs/rule_chain_output.txt         verified examples shown for 10196379; training gold
    todo-temp/error-analysis/outputs/topk4_stability_output.txt    statements on five development phrases
    todo-temp/error-analysis/outputs/keep_criteria_output.txt      development mentions flipping between repeated runs
    todo-temp/error-analysis/outputs/tp_exposure_output.txt        copy rate of listed strings
    todo-temp/error-analysis/outputs/error_patterns_output.txt     error groups of the original guideline
    todo-temp/error-analysis/outputs/loop10_broken_coding.csv      top-4 loop10 misses checked against its rules
    outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop07/rounds/iteration_01/refine_guidelines.txt   one verified-examples block
    data/datasets/ncbi_disease/train/10196379.json, data/guidelines/ncbi_disease_guidelines.txt, top-4 loop10 final guideline

    python todo-temp/slides/build_error_analysis_slides.py [output.pptx]
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from build_faldh_slides import (FIG1, FIG1_ASPECT, FONT, INK, MUTED, NAVY, PALE, RED, STRONG, TEMPLATE,  # noqa: E402
                                boxed_text, drop, label_above, new_slide, normalize_slide_ids, place, put, table_at,
                                table_at_placeholder, text)

OUT = ROOT.parent / "presentations/20261030_error_analysis_en.pptx"
EA = "todo-temp/error-analysis/outputs"
SUBTYPES = ["SpecificDisease", "DiseaseClass", "Modifier"]
# chart colors: categorical slots 1 to 3 of the dataviz reference palette (validated: lightness, chroma, CVD, contrast
# warning on the third, relieved by the legend and the values in the notes); gray baseline for the original runs
C_SERIES = {"SpecificDisease": "2A78D6", "DiseaseClass": "1BAF7A", "Modifier": "EB6834"}
C_BASE, C_HIGH, C_GRID = "8A99A8", "2A78D6", "DCE4EC"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def grab(rel: str, pattern: str, flags: int = 0) -> tuple:
    m = re.search(pattern, read(rel), flags)
    assert m, (rel, pattern)
    return m.groups()


def r(x, places: int = 1) -> str:
    """Round half up, as written in the report."""
    q = Decimal(1).scaleb(-places)
    return str(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def signed(x, places: int = 1) -> str:
    s = r(x, places)
    return s if s.startswith("-") else "+" + s


def load_evidence() -> dict:
    ev = {}
    # method means and top-4 minus original
    rep = "todo-temp/seminar-20261023/reproduction_analysis_output.txt"
    ev["mean"] = {k: v for k, v in re.findall(r"^\s+(E1|top-1|top-4)\s+F1 ([\d.]+) \(", read(rep), re.M)}
    assert ev["mean"] == {"E1": "0.7048", "top-1": "0.7017", "top-4": "0.7115"}, ev["mean"]
    ev["p3"] = grab(rep, r"P3 top-4 - E1: difference (\+[\d.]+), 95% CI \[(-[\d.]+), (\+[\d.]+)\]")
    assert ev["p3"] == ("+0.0067", "-0.0145", "+0.0279")

    # F1 of the 19 original runs and the 11 refined guidelines; change per gold subtype
    eo = json.loads(read(f"{EA}/error_overview.json"))
    ev["orig_f1"] = sorted(m["f1"] for m in eo["original"]["metrics"].values())
    ev["refined"] = {name: d["metrics"]["f1"] for name, d in eo["changed"].items()}
    assert len(ev["orig_f1"]) == 19 and len(ev["refined"]) == 11
    lo, hi = ev["orig_f1"][0], ev["orig_f1"][-1]
    ev["below"] = sorted(n for n, f in ev["refined"].items() if f < lo)
    ev["above"] = sorted(n for n, f in ev["refined"].items() if f > hi)
    d_line = grab(f"{EA}/error_overview_output.txt", r"   F1: below the original range (\d+) .*?; above it (\d+) ")
    assert (len(ev["below"]), len(ev["above"])) == (4, 3) == tuple(map(int, d_line))
    ev["by_label"] = eo["by_label"]
    ev["rho"] = dict(re.findall(r"(SpecificDisease|DiseaseClass|Modifier|CompositeMention) \+([\d.]+)",
                                grab(f"{EA}/error_overview_output.txt", r"(rank correlation .*)")[0]))
    assert (ev["rho"]["SpecificDisease"], ev["rho"]["Modifier"]) == ("0.84", "0.44")
    ev["mod_up"] = sum(v["Modifier"] > 0 for v in ev["by_label"].values())
    assert ev["mod_up"] == 10
    comp = [v["CompositeMention"] for v in ev["by_label"].values()]
    assert min(comp) > -5 and max(comp) < 5
    # Track 2 counts (backup)
    fn = grab(f"{EA}/error_overview_output.txt", r"   FN: below the original range (\d+) .*?; above it (\d+) .*?; inside (\d+)")
    ms = grab(f"{EA}/error_overview_output.txt", r"   missed: fewer than the original mean \d+; below the original range (\d+); above it (\d+)")
    ev["fn_rng"] = tuple(map(int, fn))                       # below, above, inside
    ev["miss_rng"] = (int(ms[0]), int(ms[1]), 11 - int(ms[0]) - int(ms[1]))
    assert ev["fn_rng"] == (4, 3, 4) and ev["miss_rng"] == (6, 2, 3)
    l06 = eo["changed"]["top-4 loop06"]
    ev["l06"] = (signed(l06["delta_kinds"]["missed"]), signed(l06["delta"]["fn"]), signed(l06["delta"]["fp"]))
    assert ev["l06"] == ("-36.6", "-0.6", "+41.8")

    # Modifier mislabels on non-Modifier gold, by position (section P), and the copied phrases (section Q)
    msub = f"{EA}/modifier_subset_output.txt"
    b2 = grab(msub, r"after a relational noun \(B2 list\)\s+original\s+([\d.]+) per run \(\d+-\d+\); expected\s+[\d.]+; changed runs\s+(\d+)")
    el = grab(msub, r"\n   elsewhere\s+original\s+([\d.]+) per run \(\d+-\d+\); expected\s+[\d.]+; changed runs\s+(\d+)")
    n_b2 = int(grab(msub, r"B2 list: (\d+) non-Modifier mentions")[0])
    n_nm = int(grab(msub, r"non-Modifier gold mentions \(n=(\d+)\) predicted with the label Modifier")[0])
    ev["pos"] = {"phrase": (n_b2, float(b2[0]), int(b2[1]) / 11), "other": (n_nm - n_b2, float(el[0]), int(el[1]) / 11)}
    assert (n_b2, n_nm, int(b2[1]), int(el[1])) == (71, 573, 92, 83)
    assert grab(msub, r"'ovarian cancer' in 10196379: gold labels (\{[^}]*\})")[0] == "{'Modifier': 7, 'SpecificDisease': 1}"
    q = re.findall(r"^\s+(top-\d loop\d\d)\s+(\d+) of 9\s+(Modifier|not Modifier)\s+(\d+)\s+(\d+)\s+(\d+)$", read(msub), re.M)
    assert len(q) == 11
    ev["q"] = {g: (int(n), c, int(a) + int(b)) for g, n, c, a, b, _ in q}
    fh = [v for v in ev["q"].values() if v[1] == "Modifier"]
    nf = [v for v in ev["q"].values() if v[1] != "Modifier"]
    assert len(fh) == 7 and len(nf) == 4 and min(v[2] for v in fh) > 0 and all(v[2] == 0 for v in nf)
    ev["q_rng"] = {"fh": (min(v[0] for v in fh), max(v[0] for v in fh), min(v[2] for v in fh), max(v[2] for v in fh)),
                   "nf": (min(v[0] for v in nf), max(v[0] for v in nf))}
    ev["q_bo"] = grab(msub, r"after noun, breast/ovarian ([\d.]+) of (\d+); after noun, other names ([\d.]+) of (\d+)")
    assert ev["q_bo"] == ("9.6", "30", "3.6", "41")

    # the annotator's stated guideline section for the 92 phrase-position errors
    cs = grab(f"{EA}/cited_sections_output.txt", r"\n   total\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
    assert cs == ("92", "79", "13", "0")

    # family-history rule per round
    ht = f"{EA}/history_tally_output.txt"
    ev["first"] = tuple(map(int, grab(ht, r"where the guideline had none: (\d+); Modifier (\d+)")))
    assert ev["first"] == (17, 16)
    assert grab(ht, r"labelled right \(Specific\) before the rewrite in (\d+) of (\d+)") == ("17", "17")
    for loop, rnd in (("topk4_loop01", 5), ("topk4_loop02", 4), ("topk4_loop04", 2)):
        assert re.search(rf"{loop}\s+{rnd}\s+kept\s+yes\s+Modifier\s+Specific", read(ht)), loop
    assert re.search(r"topk4_loop09\s+2\s+kept\s+yes\s+Modifier\s+Modifier", read(ht))
    rc = f"{EA}/rule_chain_output.txt"
    assert grab(rc, r"'10196379\.json': (\d+)") == ("44",)
    ev["rc43"] = grab(rc, r"(\d+) x \[Modifier \"ovarian cancer\": 5\]")[0]
    assert ev["rc43"] == "43"
    assert "disease mention right after 'history of': {'SpecificDisease': 9, 'CompositeMention': 5, 'not annotated': 4, " \
           "'DiseaseClass': 3}" in read(rc)

    # one verified-examples block for 10196379, as Guideline Refinement saw it (top-4 loop07, round 1)
    dev = json.loads(read("data/datasets/ncbi_disease/train/10196379.json"))
    t = dev["text"]
    prompt = read("outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop07/rounds/iteration_01/refine_guidelines.txt")
    blk = prompt.split("DO NOT BREAK")[-1]
    blk = blk[blk.index("FILE: 10196379.json"):]
    blk = blk[:blk.find("FILE:", 10)] if blk.find("FILE:", 10) > 0 else blk
    listed = re.findall(r'^- (\w+) \[(\d+), (\d+)\] "([^"]+)"', blk, re.M)
    assert len(listed) == 5 and all(lab == "Modifier" and s == "ovarian cancer" for lab, _, _, s in listed)
    nxt = lambda e: re.match(r"\s*(\S+)", t[e:]).group(1)  # noqa: E731
    ev["listed"] = [f"ovarian cancer {nxt(int(e))}" for _, b, e, _ in listed]
    assert sorted(ev["listed"]) == sorted(["ovarian cancer population", "ovarian cancer cases", "ovarian cancer study",
                                           "ovarian cancer risk", "ovarian cancer risk"]), ev["listed"]
    oc = [(x["obj"], nxt(x["span"]["end"])) for x in dev["denotations"]
          if t[x["span"]["begin"]:x["span"]["end"]] == "ovarian cancer"]
    assert Counter(o for o, _ in oc) == {"Modifier": 7, "SpecificDisease": 1}
    h = re.search(r"history of ovarian cancer", t).start() + len("history of ")
    assert any(x["obj"] == "SpecificDisease" and x["span"]["begin"] == h for x in dev["denotations"])

    # statements on five development phrases; repeated-run flips; copy rate
    ts = f"{EA}/topk4_stability_output.txt"
    con = dict(re.findall(r"(FH ovarian cancer|FH cancer|Caucasian cancer cases|ichthyosis, spasticity|gene word) (\d+)",
                          grab(ts, r"(claims that contradict the development gold, by phrase: .*)")[0]))
    agr = dict(re.findall(r"(FH ovarian cancer|FH cancer|Caucasian cancer cases|ichthyosis, spasticity|gene word) (\d+)",
                          grab(ts, r"(claims that agree with it, by phrase: .*)")[0]))
    ev["phr"] = {k: (int(con[k]), int(agr[k])) for k in con}
    assert sum(v[0] for v in ev["phr"].values()) == 15 and sum(v[1] for v in ev["phr"].values()) == 17
    assert grab(ts, r"(\d+) contradicting claims entered in (\d+) rounds, all kept; in (\d+) of the 15") == ("15", "9", "12")
    kc = f"{EA}/keep_criteria_output.txt"
    ev["flip"] = (grab(kc, r"mentions broken mean ([\d.]+)")[0], grab(kc, r"Development gold mentions: (\d+)")[0])
    assert ev["flip"] == ("2.5", "74")
    ev["copy"] = grab(f"{EA}/tp_exposure_output.txt", r"\n   listed\s+(\d+)\s+(\d+)\s+(\d+)%")
    assert ev["copy"] == ("228", "104", "46")

    # error groups of the original guideline (backup)
    ep = f"{EA}/error_patterns_output.txt"
    ev["groups"] = re.findall(r"^\s+([\d.]+) \(\d+-\d+\)\s+([\d.]+)%\s+\+[\d.]+\s+(.+?) \[", read(ep), re.M)
    assert len(ev["groups"]) == 7 and grab(ep, r"total errors per run: ([\d.]+)") == ("297.1",)

    # top-4 loop10 (backup): the original rule it dropped, and its checked misses
    orig_g = read("data/guidelines/ncbi_disease_guidelines.txt").replace("\r\n", "\n").split("\n")
    assert "However, the terms “cancer” and “tumor” were retained." in orig_g[76]
    assert "Very general terms such as “disease,” “syndrome,”" in orig_g[75] and "were excluded" in orig_g[75]
    l10 = read("outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop10/final/final_guidelines.txt").replace("\r\n", "\n").split("\n")
    assert "A bare, unqualified “cancer” or “tumor” used generically" in l10[190] and "is not annotated" in l10[190]
    assert "routed to annotation audit rather than tagged automatically" in l10[83]
    rows = list(csv.DictReader((ROOT / EA / "loop10_broken_coding.csv").open(encoding="utf-8")))
    st = Counter(x["v3_clause_status"] for x in rows)
    ev["l10"] = (st["explicit"], sum(n for k, n in st.items() if k != "not coded"))
    assert ev["l10"] == (21, 38)
    assert "annotations: 3640" in read(f"{EA}/cited_sections_output.txt")
    assert "-- 9072974 295-302 gold DiseaseClass 'cancers'; right in 19/19 orig; loop10: missed" in \
        read(f"{EA}/outside_subset_output.txt")
    return ev


# ---------------------------------------------------------------- styling helpers
def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


def table_font(gf, size=14) -> None:
    for row in gf.table.rows:
        for cell in row.cells:
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(size)


def hide_axis(ax) -> None:
    ax.visible = False
    ax._element.find(qn("c:delete")).set("val", "1")  # python-pptx writes a bare <c:delete/>; ONLYOFFICE reads it as 0
    ax.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    ax.major_tick_mark = XL_TICK_MARK.NONE
    ax.has_major_gridlines = False
    ax.format.line.fill.background()


def quiet_axis(ax, size=14) -> None:
    ax.tick_labels.font.size = Pt(size)
    ax.tick_labels.font.color.rgb = rgb(INK)
    ax.tick_labels.font.name = FONT
    ax.major_tick_mark = XL_TICK_MARK.NONE
    ax.has_major_gridlines = True
    ax.major_gridlines.format.line.color.rgb = rgb(C_GRID)
    ax.major_gridlines.format.line.width = Pt(0.75)
    ax.format.line.color.rgb = rgb(C_GRID)


def legend_bottom(chart, size=14) -> None:
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(size)
    chart.legend.font.color.rgb = rgb(INK)
    chart.legend.font.name = FONT


# ---------------------------------------------------------------- slides
def build(out: Path = OUT) -> None:
    ev = load_evidence()
    prs = Presentation(TEMPLATE)
    sld_ids = prs.slides._sldIdLst
    for sld_id in list(sld_ids):  # drop the template's sample slides
        prs.part.drop_rel(sld_id.rId)
        sld_ids.remove(sld_id)
    p3 = ev["p3"]
    rng = f"{ev['orig_f1'][0]:.3f} to {ev['orig_f1'][-1]:.3f}"

    # 1 Cover
    s = new_slide(prs, "01 Cover", "Seminar with the supervisor. Purpose: report what the error analysis of the Haiku "
                  "reproduction found, then discuss how to move the research goals (Track 1 and Track 2) forward.")
    put(s, 0, "The University of Tokyo")
    put(s, 1, ["Optimizing Annotation Guideline Refinements", "for LLM-Based Annotation"], size=40)
    put(s, 2, "Hengyu Zhou")
    put(s, 3, "Error analysis of the Haiku reproduction, October 2026")

    # 2 Findings in brief
    s = new_slide(prs, "05 Key points",
                  "The five findings, in the order of the deck. All are descriptive: each refined guideline was scored "
                  "with one validation run, and no change has been tested yet. The last slide turns them into questions "
                  "for the discussion.")
    put(s, 0, "What the error analysis found")
    put(s, 1, ["Mean F1 did not improve; single refined guidelines differ",
               "Gains come from Modifier; F1 follows SpecificDisease losses",
               "New Modifier errors follow “a family history of X”-type phrases",
               "That rule was generalized from one development document",
               "Rounds are kept on development F1, so such rules stay"],
        bullets=True, space_after=10, size=24)

    # 3 The loop and the runs
    s = new_slide(prs, "07 Full figure",
                  "Figure 1 of the base paper, stage names as in the paper. A loop starts from the original guideline. "
                  "Each round: LLM Annotation of the 10 development documents, Evaluation against their gold annotation, "
                  "Discrepancy Analysis (errors grouped into clusters), Pattern Explanation, Principle Generation and "
                  "Guideline Refinement (the whole guideline rewritten). A round is kept only if development F1 rises; "
                  "the loop stops at the first round that is not kept. top-1 refines the largest cluster per round, "
                  "top-4 the four largest. The final guideline of each loop is scored once on the 100 validation "
                  "documents (791 gold mentions), exact span and subtype. Runs analyzed: the original guideline 10 times "
                  "plus the 9 loops that kept no round (19 original-guideline runs); 11 loops ended with a refined "
                  "guideline (top-1: 2, top-4: 9).")
    put(s, 0, "The refinement loop and the runs analyzed")
    label_above(s, "Rounds learn from 10 development documents; final guidelines are scored on 100 validation documents")
    drop(s, 1)
    fig_h = 3.3
    fig_w = fig_h * FIG1_ASPECT
    fig = s.shapes.add_picture(str(FIG1), Inches(0.833 + (11.667 - fig_w) / 2), Inches(2.5), height=Inches(fig_h))
    fig.name = "base-paper-figure-1"
    fig._element.nvPicPr.cNvPr.set("descr", "Figure 1 of the base paper: LLM Annotation and Evaluation, then "
                                   "Discrepancy Analysis, Pattern Explanation, Principle Generation, Guideline Refinement.")
    put(s, 2, "Analyzed: 19 original-guideline runs; 11 loops ending with a refined guideline")

    # 4 F1: no mean gain, refined guidelines differ
    vals = "\n".join(f"  {n}: {f:.3f}" for n, f in sorted(ev["refined"].items(), key=lambda kv: -kv[1]))
    s = new_slide(prs, "11 Line chart",
                  f"Each dot is one validation run. Gray: the 19 original-guideline runs, F1 {rng}. Blue: the 11 refined "
                  f"guidelines, one run each:\n{vals}\nMeans over 10 runs per method: original {ev['mean']['E1']}, "
                  f"top-1 {ev['mean']['top-1']}, top-4 {ev['mean']['top-4']}; top-4 minus original {p3[0]}, 95% interval "
                  f"{p3[1]} to {p3[2]} (Welch test fixed before the runs). The 95% interval is the range in which the "
                  "true difference likely lies, given how much single runs vary. A single original-guideline run falls "
                  "outside the range of the other runs about one time in ten, so about 1 of 11 is expected by chance.")
    put(s, 0, "Mean F1 did not improve, but refined guidelines differ")
    cd = XyChartData()
    so = cd.add_series("Original guideline, 19 runs")
    for i, f in enumerate(ev["orig_f1"]):
        so.add_data_point(f, 2 + (-0.14, 0.0, 0.14)[i % 3])
    sr = cd.add_series("Refined guidelines, 11 loops")
    for i, f in enumerate(sorted(ev["refined"].values())):
        sr.add_data_point(f, 1 + (-0.14, 0.0, 0.14)[i % 3])
    for x in (ev["orig_f1"][0], ev["orig_f1"][-1]):  # one dashed vertical line per end of the original range
        sb = cd.add_series("Range of the original runs")
        sb.add_data_point(x, 0.45)
        sb.add_data_point(x, 2.55)
    chart = s.placeholders[3].insert_chart(XL_CHART_TYPE.XY_SCATTER, cd).chart
    chart.font.name, chart.font.size = FONT, Pt(14)
    for series, color in zip(chart.plots[0].series, (C_BASE, C_HIGH, C_BASE, C_BASE)):
        series.smooth = False
        if series.name.startswith("Range"):
            series.marker.style = XL_MARKER_STYLE.NONE
            series.format.line.color.rgb = rgb(color)
            series.format.line.width = Pt(1.25)
            series.format.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            continue
        series.marker.style = XL_MARKER_STYLE.CIRCLE
        series.marker.size = 11
        series.marker.format.fill.solid()
        series.marker.format.fill.fore_color.rgb = rgb(color)
        series.marker.format.line.color.rgb = rgb("FFFFFF")
        series.marker.format.line.width = Pt(1.5)
        series.format.line.fill.background()
    ev_x = chart.category_axis  # the x value axis of an XY chart
    ev_x.minimum_scale, ev_x.maximum_scale, ev_x.major_unit = 0.65, 0.76, 0.02
    ev_x.tick_labels.number_format, ev_x.tick_labels.number_format_is_linked = "0.00", False
    quiet_axis(ev_x)
    ev_x.has_major_gridlines = False
    ev_y = chart.value_axis
    ev_y.minimum_scale, ev_y.maximum_scale = 0.3, 2.7
    hide_axis(ev_y)
    legend_bottom(chart)
    # the two range lines share one legend entry: hide the entry of the second (schema: after legendPos)
    leg = chart.legend._element
    entry = etree.Element(qn("c:legendEntry"))
    etree.SubElement(entry, qn("c:idx"), val="3")
    etree.SubElement(entry, qn("c:delete"), val="1")
    leg.find(qn("c:legendPos")).addnext(entry)
    put(s, 1, [[(f"{len(ev['below']) + len(ev['above'])} of 11", {"bold": True, "color": NAVY})],
               f"refined guidelines fall outside the range of the 19 original runs; chance alone gives about 1"],
        size=16, space_after=6)
    put(s, 2, f"Mean gain of top-4 over the original: {signed(p3[0], 3)} (95% interval {r(p3[1], 3)} to "
              f"{signed(p3[2], 3)}). One validation run per guideline.", size=12)

    # 5 Gains and losses by subtype
    order = sorted(ev["refined"], key=lambda n: ev["refined"][n])  # ascending F1: the bar chart draws the first at the bottom
    cd = CategoryChartData()
    cd.categories = [f"{n} · {ev['refined'][n]:.3f}" for n in order]
    for lab in SUBTYPES:
        cd.add_series(lab, [round(ev["by_label"][n][lab], 1) for n in order])
    table_view = "\n".join(f"  {n} (F1 {ev['refined'][n]:.3f}): " +
                           ", ".join(f"{lab} {signed(ev['by_label'][n][lab])}" for lab in SUBTYPES)
                           for n in reversed(order))
    s = new_slide(prs, "10 Bar chart",
                  "Change in exact matches (span and subtype) per gold subtype: each refined guideline's run minus the "
                  "mean of the 19 original-guideline runs. Guidelines from highest F1 (top) to lowest. Values:\n" +
                  table_view + "\nCompositeMention changes stay within ±4 and are left out. Rank correlation compares "
                  "only the two orderings (1 = same order): F1 against SpecificDisease change " +
                  ev["rho"]["SpecificDisease"] + ", against Modifier " + ev["rho"]["Modifier"] + ", against DiseaseClass " +
                  ev["rho"]["DiseaseClass"] + ". The largest single losses: SpecificDisease labelled Modifier (top-4 "
                  "loop07, loop06), SpecificDisease labelled DiseaseClass (top-1 loop05), DiseaseClass missed (top-4 "
                  "loop10, loop05).")
    put(s, 0, "F1 follows SpecificDisease losses, not Modifier gains")
    chart = s.placeholders[3].insert_chart(XL_CHART_TYPE.BAR_CLUSTERED, cd).chart
    chart.font.name, chart.font.size = FONT, Pt(12)
    plot = chart.plots[0]
    plot.gap_width, plot.overlap = 45, 0
    for series in plot.series:
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = rgb(C_SERIES[series.name])
        series.format.line.color.rgb = rgb("FFFFFF")
        series.format.line.width = Pt(0.5)
        series.invert_if_negative = False
    ca = chart.category_axis
    ca.tick_labels.font.size = Pt(12)
    ca.tick_labels.font.color.rgb = rgb(INK)
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    ca.format.line.color.rgb = rgb(MUTED)
    va = chart.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = -40, 60, 20
    quiet_axis(va, size=12)
    legend_bottom(chart, size=12)
    put(s, 1, [[(f"Modifier rises in {ev['mod_up']} of 11", {"bold": True, "color": NAVY})],
               f"Ranked by F1, guidelines line up with their SpecificDisease change (rank correlation "
               f"{ev['rho']['SpecificDisease']}; Modifier {ev['rho']['Modifier']})"], size=15, space_after=6)
    put(s, 2, "Exact matches gained or lost per gold subtype, against the original-guideline mean", size=12)

    # 6 Where the new Modifier errors are
    ph, ot = ev["pos"]["phrase"], ev["pos"]["other"]
    s = new_slide(prs, "12 Results table",
                  "Non-Modifier gold mentions (SpecificDisease, DiseaseClass, CompositeMention) that a run labels Modifier, "
                  "per validation run: the original guideline averaged over its 19 runs, the refined guidelines over their "
                  "11 runs. 'Right after a relational phrase' means the disease name directly follows a noun such as "
                  "history, risk, patients, families or cases plus of or with; the positions were found with a word list, "
                  "partly extended after looking at the errors. In all 92 such errors of the refined guidelines, the "
                  "annotator's stated reason cites the guideline's own clause that makes these positions Modifier, or the "
                  "section holding it.")
    put(s, 0, "New Modifier errors follow “history of”-type phrases")
    label_above(s, "Non-Modifier gold mentions labelled Modifier, per validation run", y=1.95)
    gf = table_at_placeholder(s, 2, [
        ["Position of the disease name", "Gold mentions", "Original guideline", "Refined guidelines"],
        ["Right after “history of”, “risk of”, “patients with” and similar", str(ph[0]), r(ph[1], 2), r(ph[2])],
        ["Anywhere else", str(ot[0]), r(ot[1]), r(ot[2])],
    ], [5.067, 2.2, 2.2, 2.2], [0.5, 0.72, 0.5], center_cols=(1, 2, 3), bold={(1, 3)}, colors={(1, 3): NAVY})
    table_font(gf, 16)
    place(s, 2, y=2.35)
    boxed_text(s, 0.833, 4.7, 11.667, 1.2, [
        [("Example  ", {"bold": True, "color": NAVY}),
         ("“… women with a family history of breast cancer”: gold SpecificDisease. The original guideline always gets it "
          "right. The 7 refined guidelines whose clause makes family history Modifier label it Modifier, and their "
          "stated reason cites that clause.", {})]], size=16)
    put(s, 1, f"The increase is almost all in the first row: {signed(ph[2] - ph[1])} per run, against "
              f"{signed(ot[2] - ot[1])} elsewhere", size=14)

    # 7 One development document, not copied strings
    fh, nf = ev["q_rng"]["fh"], ev["q_rng"]["nf"]
    s = new_slide(prs, "12 Results table",
                  "Development document 10196379 (BRCA1 in ovarian cancer) uses 'ovarian cancer' 8 times: 7 times gold "
                  "Modifier (ovarian cancer cases, population, study, risk), once gold SpecificDisease, after 'a family "
                  "history of'. Phrases copied: how many of the 9 phrases around this document's gold mentions appear in "
                  "the final guideline. Copying alone does not predict the errors: top-4 loop01 and loop02 copied the most "
                  "(7 and 8) and make none. The project's hard-coding check asks whether a clause still gives a condition "
                  "and a label once its examples are deleted; these family-history clauses do (for example 'the "
                  "complement of a history frame is Modifier'), so they are rules generalized from this document, not "
                  "copied answers. Within the 7 guidelines, mentions with breast or ovarian cancer names are hit most: "
                  f"{ev['q_bo'][0]} of {ev['q_bo'][1]} per guideline, against {ev['q_bo'][2]} of {ev['q_bo'][3]} other "
                  "names; disease name and abstract topic cannot be separated here.")
    put(s, 0, "A rule generalized from one development document")
    label_above(s, "Development document 10196379: “ovarian cancer” is gold Modifier 7 times, SpecificDisease once "
                   "(“a family history of ovarian cancer”)", y=1.95)
    gf = table_at_placeholder(s, 2, [
        ["Final guideline's clause on “a family history of X”", "Guidelines", "Phrases copied from 10196379",
         "Errors right after “history of”-type phrases"],
        ["Modifier", "7", f"{fh[0]} to {fh[1]} of 9", f"{fh[2]} to {fh[3]} each"],
        ["Not Modifier, or no clause", "4", f"{nf[0]} to {nf[1]} of 9", "none"],
    ], [4.067, 1.6, 2.6, 3.4], [0.75, 0.5, 0.5], center_cols=(1, 2, 3), bold={(1, 3)}, colors={(1, 3): NAVY})
    table_font(gf, 16)
    place(s, 2, y=2.7)
    boxed_text(s, 0.833, 5.0, 11.667, 1.0,
               "Copying the document's phrases does not predict the errors; the label the clause gives to the "
               "family-history mention does", size=18, color=NAVY, bold=True)
    drop(s, 1)

    # 8 Why the rule was written
    s = new_slide(prs, "14 Case comparison",
                  "What each step sees in a round: Pattern Explanation sees discrepancy examples with their gold annotation "
                  "(only the selected clusters, at most 5 examples each); Guideline Refinement sees the principle and the "
                  "verified examples: 5 development documents, at most 5 correctly labelled mentions each, and no "
                  f"discrepancy gold. 10196379 was in the verified examples of all 44 rounds; in "
                  f"{ev['rc43']} of them the five listed mentions "
                  "were all 'ovarian cancer' as Modifier (left: top-4 loop07, round 1). "
                  f"{ev['first'][0]} rewrites added a family-history rule to a guideline without one; {ev['first'][1]} "
                  "wrote Modifier. Before each of these 17 rewrites the family-history mention had been labelled "
                  "correctly, so it was never a discrepancy example. top-4 loop01, loop02 and loop04 switched the rule to "
                  "SpecificDisease in the round where Pattern Explanation showed its gold; top-4 loop09 saw it and kept "
                  "Modifier. Training gold: 21 disease mentions right after 'history of', none Modifier.")
    put(s, 0, "Guideline Refinement never saw that mention's gold")
    put(s, 1, "Verified examples, 10196379")
    put(s, 2, [[("Modifier  ", {"bold": True, "color": STRONG}), (x, {})] for x in ev["listed"]], size=16)
    put(s, 3, "Never listed")
    put(s, 4, [[("SpecificDisease  ", {"bold": True, "color": RED}), ("a family history of ovarian cancer", {})]],
        size=16)
    drop(s, 5)
    boxed_text(s, 0.833, 4.95, 11.667, 1.65, [
        "Guideline Refinement sees the principle and the verified examples only: 5 documents, at most 5 correct "
        "mentions each",
        f"{ev['first'][0]} rewrites first added a family-history rule; {ev['first'][1]} wrote Modifier. The mention was "
        "correct before each, so it was never a discrepancy example",
        "top-4 loop01, loop02, loop04 switched to SpecificDisease once Pattern Explanation showed its gold"],
        bullets=True, size=14, space_after=4, anchor=MSO_ANCHOR.MIDDLE)

    # 9 Why the rule was kept
    phr = ev["phr"]
    s = new_slide(prs, "12 Results table",
                  "A round is kept if development F1 rises; the new rules themselves are not checked. Five development "
                  "phrases were chosen after the fact; the table counts what the 9 top-4 final guidelines state about them "
                  "with an explicit label. All 15 statements against gold were written in kept rounds; in 12 of them the "
                  "same round turned that development mention from correct to wrong. Between repeated runs of the "
                  f"original guideline, only {ev['flip'][0]} of the {ev['flip'][1]} development mentions turn from correct "
                  "to wrong on average.")
    put(s, 0, "Rounds are kept on development F1 alone")
    label_above(s, "What the 9 top-4 final guidelines state about five development phrases", y=1.95)
    gf = table_at_placeholder(s, 2, [
        ["Development phrase", "Gold", "Against gold", "Matching gold"],
        ["a family history of ovarian cancer", "SpecificDisease", *map(str, phr["FH ovarian cancer"])],
        ["a family history of cancer", "DiseaseClass", *map(str, phr["FH cancer"])],
        ["91 Caucasian cancer cases", "Modifier", *map(str, phr["Caucasian cancer cases"])],
        ["ichthyosis, spasticity (listed symptoms)", "DiseaseClass", *map(str, phr["ichthyosis, spasticity"])],
        ["disease name before “gene” (e.g. the DTD gene)", "Modifier", *map(str, phr["gene word"])],
        ["All five", "", str(sum(v[0] for v in phr.values())), str(sum(v[1] for v in phr.values()))],
    ], [5.067, 2.6, 2.0, 2.0], 0.42, center_cols=(2, 3), bold={(6, 0), (6, 2), (6, 3)}, colors={(6, 2): RED})
    table_font(gf, 14)
    place(s, 2, y=2.4)
    put(s, 1, "All 15 were written in kept rounds; in most, that same round turned the development mention from correct to wrong",
        size=14)

    # 10 Candidate changes
    s = new_slide(prs, "12 Results table",
                  "Candidates only; none has been tested. Each would be tested alone (one change per experiment), with "
                  "new loops, and evaluated on documents not used in this analysis. Showing all discrepancy cases follows "
                  "the base paper, where Guideline Refinement also receives the discrepancy context (Section 3.4.4); the "
                  "current implementation does not pass it. The family-history mention was a discrepancy in 15 rounds, and "
                  "Pattern Explanation saw it in 7 of them. Copy cost: of the strings listed in verified examples, "
                  f"{ev['copy'][1]} of {ev['copy'][0]} ({ev['copy'][2]}%) were copied into the next guideline.")
    put(s, 0, "Candidate changes (untested)")
    gf = table_at_placeholder(s, 2, [
        ["Change", "What it targets", "Known limit or cost"],
        ["Check new rules against development gold before keeping a round", "Rules that contradict development gold",
         "Needs a rule-to-example check"],
        ["Give Pattern Explanation and Guideline Refinement all discrepancy cases with gold", "Correcting a wrong rule sooner",
         "Would not have stopped the family-history rule"],
        ["List every correct mention in the verified examples", "The hidden family-history gold",
         f"More copying: {ev['copy'][2]}% of listed strings get copied"],
        ["Narrow the Modifier rule for “history of”-type phrases", "The new Modifier errors",
         "Must keep the gains before gene words"],
    ], [5.0, 3.567, 3.1], [0.45, 0.66, 0.66, 0.66, 0.66])
    table_font(gf, 14)
    place(s, 2, y=2.25)
    put(s, 1, "Each change alone, with new loops, on documents not used in this analysis", size=14)

    # 11 Discussion
    s = new_slide(prs, "17 Summary",
                  "Questions for the discussion. Track 1: LLM annotation used as it is, judged by exact span and subtype "
                  "F1. Track 2: annotation corrected by experts; fewer missed mentions, extra mentions as the price. The "
                  "seven-group classification and the two miss counts are in the backup slides.")
    put(s, 0, "For discussion: moving the research goals forward")
    put(s, 1, ["Track 1: which single change should be tested first?",
               "Track 2: count misses as missed mentions (FN), or as missed with no overlapping prediction?",
               "Is the seven-group classification enough as the classification of all errors?"],
        bullets=True, space_after=10, size=20)
    put(s, 2, "Proposal: test the chosen change with new loops, on documents not used in this analysis", size=16,
        color=MUTED)

    # Backup
    s = new_slide(prs, "19 Appendix divider", "Backup slides: the error classification of the original guideline, the "
                  "two miss counts for Track 2, and the DiseaseClass losses of top-4 loop10.")
    put(s, 0, "A")
    put(s, 1, "Backup")
    put(s, 2, "Error classification, Track 2 counts, top-4 loop10")

    # B1 Error groups of the original guideline
    examples = {"disease name used as a modifier, missed": "“VHL” in “VHL gene”",
                "other missed mentions: symptoms, general words, tumors, deficiencies, the rest": "“short stature”",
                "span shorter or longer than the gold span": "“familial” left out",
                "Modifier against disease or Composite label": "HNPCC in “HNPCC kindreds” as SpecificDisease",
                "Specific against DiseaseClass": "“hereditary breast cancer” as DiseaseClass",
                "Composite label at the gold span, or one prediction over two gold mentions": "“AO2 / DTD” as one mention",
                "extra mentions and other": "mouse disease “scurfy”"}
    names = {"disease name used as a modifier, missed": "Disease name used as a modifier, missed",
             "other missed mentions: symptoms, general words, tumors, deficiencies, the rest": "Other missed: symptoms, general words",
             "span shorter or longer than the gold span": "Span shorter or longer than gold",
             "Modifier against disease or Composite label": "Modifier against another subtype",
             "Specific against DiseaseClass": "SpecificDisease against DiseaseClass",
             "Composite label at the gold span, or one prediction over two gold mentions": "Composite label, or one prediction over two",
             "extra mentions and other": "Extra mentions and other"}
    s = new_slide(prs, "12 Results table",
                  "All errors of the 19 original-guideline runs, sorted into seven groups by string and label rules; each "
                  "discrepancy is counted once, so the total (297.1 per run) is smaller than FN plus FP. Errors per run are "
                  "means over the 19 runs.")
    put(s, 0, "Where Haiku errs with the original guideline")
    rows = [["Error group", "Per run", "Share", "Example"]]
    for n, share, g in ev["groups"]:
        assert g in names, g
        rows.append([names[g], n, f"{share}%", examples[g]])
    gf = table_at_placeholder(s, 2, rows, [4.6, 1.3, 1.2, 4.567], 0.4, center_cols=(1, 2))
    table_font(gf, 13)
    place(s, 2, y=2.2)
    put(s, 1, "Each discrepancy counted once; 297.1 errors per run in total", size=12)

    # B2 Track 2: two miss counts
    s = new_slide(prs, "12 Results table",
                  "Track 2's main measure in the plan is missed mentions (FN, exact span and subtype). The base paper's "
                  "discrepancy categories also count misses with no overlapping prediction, which only reading the whole "
                  "text can find; label and boundary errors are visible to the expert. Counts of the 11 refined "
                  "guidelines below, inside or above the range of the 19 original-guideline runs. top-4 loop06: "
                  f"{ev['l06'][0]} misses with no overlapping prediction, {ev['l06'][1]} FN, {ev['l06'][2]} FP, per run "
                  "against the original mean.")
    put(s, 0, "Track 2: the two miss counts disagree")
    label_above(s, "11 refined guidelines against the range of the 19 original-guideline runs", y=1.95)
    gf = table_at_placeholder(s, 2, [
        ["Miss count", "Below the range", "Inside", "Above"],
        ["Missed mentions (FN): gold not matched exactly", str(ev["fn_rng"][0]), str(ev["fn_rng"][2]), str(ev["fn_rng"][1])],
        ["Missed with no overlapping prediction: no prediction touches it", str(ev["miss_rng"][0]), str(ev["miss_rng"][2]), str(ev["miss_rng"][1])],
    ], [5.267, 2.2, 2.0, 2.2], [0.5, 0.72, 0.72], center_cols=(1, 2, 3))
    table_font(gf, 16)
    place(s, 2, y=2.45)
    boxed_text(s, 0.833, 4.75, 11.667, 1.1,
               f"top-4 loop06: {ev['l06'][0][1:]} fewer misses with no overlapping prediction per run, but only "
               f"{ev['l06'][1][1:]} fewer FN and {ev['l06'][2][1:]} more FP. By FN it does not trade FP for fewer FN.", size=16)
    put(s, 1, "Which count Track 2 uses changes how the refined guidelines look", size=12)

    # B3 top-4 loop10
    s = new_slide(prs, "14 Case comparison",
                  "top-4 loop10 has the lowest F1 of the 11 refined guidelines; its main loss is missed DiseaseClass. It "
                  "rewrote the original rule that keeps 'cancer' and 'tumor' as disease mentions. Validation gold labels "
                  "such bare mentions DiseaseClass, for example 'human cancers' in document 9072974, which every "
                  f"original-guideline run gets right. Of its new misses checked one by one, {ev['l10'][0]} of "
                  f"{ev['l10'][1]} follow its own rules: bare cancer or tumor, and listed symptoms that its rules route to "
                  "annotation audit; the annotation output has no audit field, so routed mentions are simply missed.")
    put(s, 0, "top-4 loop10 lost DiseaseClass by rewriting one rule")
    put(s, 1, "Original guideline")
    put(s, 2, "“Very general terms such as ‘disease’, ‘syndrome’ … were excluded. However, the terms ‘cancer’ and ‘tumor’ were retained.”", size=16)
    put(s, 3, "top-4 loop10")
    put(s, 4, "“A bare, unqualified ‘cancer’ or ‘tumor’ used generically … is a general term and is not annotated.”",
        size=16)
    put(s, 5, [f"Example: “… mutated at considerable frequency in human cancers”, gold DiseaseClass; every "
               "original-guideline run labels it, top-4 loop10 misses it.",
               f"{ev['l10'][0]} of {ev['l10'][1]} new misses checked follow its own rules, including symptoms "
               "“routed to audit”: the annotation output has no audit field."], size=14, space_after=4)
    place(s, 5, y=4.85, h=1.35)

    normalize_slide_ids(prs)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"saved {out} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
