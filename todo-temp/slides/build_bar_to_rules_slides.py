"""Build the ten-slide 2026-11-06 seminar deck on Academic Serif B.

Run with an optional output path to build a verification copy:
    python -B todo-temp/slides/build_bar_to_rules_slides.py [output.pptx]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import the adjacent builders without creating bytecode files in the repository.
sys.dont_write_bytecode = True

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from build_error_analysis_slides import (
    C_SERIES, EA, FONT, INK, MUTED, NAVY, PALE, STRONG, SUBTYPES, TEMPLATE,
    boxed_text, drop, legend_bottom, new_slide, place, put, quiet_axis,
    read, rgb, table_at_placeholder, table_font, text,
)
from build_faldh_slides import WHITE, arrow, normalize_slide_ids, style_run


OUT = TEMPLATE.parents[1] / "20261106_bar_to_rules_en.pptx"
PREVIOUS = OUT.with_name("20261030_error_analysis_en.pptx")
LEFT, WIDTH = 5 / 6, 35 / 3


def content_slide(prs, layout_name, title, notes, keep=()):
    slide = new_slide(prs, layout_name, notes)
    for placeholder in list(slide.placeholders):
        idx = placeholder.placeholder_format.idx
        if idx not in (0, 90, 91, *keep):
            drop(slide, idx)
    put(slide, 0, title)
    return slide


def body(slide, top, lines, *, size=24, spacing=9):
    text(slide, LEFT, top, WIDTH, 6.78 - top, lines, size=size,
         space_after=spacing, name="Body")


def results_table(slide, top, rows, widths, heights, *, center=(), size=18):
    table = table_at_placeholder(slide, 2, rows, widths, heights, center_cols=center)
    place(slide, 2, y=top)
    table_font(table, size)
    for cell in table.table.iter_cells():
        cell.margin_left = cell.margin_right = Inches(0.10)
        cell.margin_top = cell.margin_bottom = Inches(0.045)
    return table


def add_bar_chart(slide):
    """Rebuild slide 5 of the October 30 deck using its data and styling."""
    evidence = json.loads(read(f"{EA}/error_overview.json"))
    scores = {name: data["metrics"]["f1"] for name, data in evidence["changed"].items()}
    order = sorted(scores, key=scores.__getitem__)
    data = CategoryChartData()
    data.categories = [f"{name} · {scores[name]:.3f}" for name in order]
    for label in SUBTYPES:
        data.add_series(label, [round(evidence["by_label"][name][label], 1) for name in order])

    place(slide, 3, y=2.10, w=7.0, h=4.43)
    chart = slide.placeholders[3].insert_chart(XL_CHART_TYPE.BAR_CLUSTERED, data).chart
    chart.font.name, chart.font.size = FONT, Pt(12)
    plot = chart.plots[0]
    plot.gap_width, plot.overlap = 45, 0
    for series in plot.series:
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = rgb(C_SERIES[series.name])
        series.format.line.color.rgb = rgb(WHITE)
        series.format.line.width = Pt(0.5)
        series.invert_if_negative = False
    category = chart.category_axis
    category.tick_labels.font.name = FONT
    category.tick_labels.font.size = Pt(12)
    category.tick_labels.font.color.rgb = rgb(INK)
    category.major_tick_mark = XL_TICK_MARK.NONE
    category.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    category.format.line.color.rgb = rgb(MUTED)
    value = chart.value_axis
    value.minimum_scale, value.maximum_scale, value.major_unit = -40, 60, 20
    quiet_axis(value, size=12)
    legend_bottom(chart, size=12)

    # The chart schema defaults omitted Boolean values to true. ONLYOFFICE
    # expects explicit values, so preserve that meaning in the exported XML.
    boolean_tags = (
        "autoTitleDeleted", "date1904", "delete", "invertIfNegative", "noMultiLvlLbl",
        "overlay", "plotVisOnly", "roundedCorners", "showDLblsOverMax", "varyColors",
    )
    for tag in boolean_tags:
        for element in chart._chartSpace.iter(qn(f"c:{tag}")):
            if element.get("val") is None:
                element.set("val", "1")


def add_workflow(slide):
    steps = [
        ("Split each bar into the mentions behind it", "Done"),
        ("Find the guideline sentence each annotation relied on", "Done: 2,918 annotations"),
        ("Group the sentences into rules", "Running"),
        ("Sum the differences rule by rule", "Running: top-4 loop07 done"),
        ("Controlled re-annotation of candidate rules", "Planned"),
    ]
    width, top, height = 2.02, 2.84, 1.68
    positions = [LEFT + i * 2.38 for i in range(4)] + [12.5 - width]
    for index, (x, (step, status)) in enumerate(zip(positions, steps), start=1):
        planned = index == len(steps)
        shape = boxed_text(slide, x, top, width, height, step, size=16,
                           fill=WHITE if planned else PALE, inset=0.12,
                           align=PP_ALIGN.CENTER, name=f"Step {index}")
        if planned:
            shape.line.color.rgb = rgb(STRONG)
            shape.line.width = Pt(1.25)
            shape.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        text(slide, x, top + height + 0.22, width, 0.70, status, size=16,
             color=MUTED, align=PP_ALIGN.CENTER, name=f"Status {index}")
    middle = top + height / 2
    for x, following in zip(positions, positions[1:]):
        arrow(slide, x + width + 0.05, middle, following - 0.05, middle)


def add_matching_rows(slide):
    example = '"an 80 % risk of [breast cancer]"'
    highlight = {"bold": True, "color": STRONG}
    rows = [
        ('Citation: where to look → "Section 3 - Context and population frames"', 0.78),
        ('Rationale: condition and label → complement of "risk", so Modifier', 0.78),
        ([
            "The sentence there with that condition and label (guideline line 65):",
            [
                ('"A disease name that premodifies, or ', {}),
                ("is the complement of", highlight),
                (", a context or population noun (such as cases, population, history, risk, or incidence) "
                 "is annotated ", {}),
                ("Modifier", highlight),
                ('."', {}),
            ],
        ], 1.55),
        ('Record: the sentence, the condition used ("is the complement of"), its use: reason for the label',
         0.88),
    ]
    y = 2.00
    for index, (detail, height) in enumerate(rows, start=1):
        boxed_text(slide, LEFT, y, 0.43, height, f"{index}.", size=18, color=NAVY,
                   bold=True, inset=0, align=PP_ALIGN.CENTER, name=f"Row {index} number")
        text(slide, LEFT + 0.59, y, 2.50, height, example, size=17,
             anchor=MSO_ANCHOR.MIDDLE, name=f"Row {index} example")
        text(slide, LEFT + 3.30, y, WIDTH - 3.30, height,
             detail, size=18,
             anchor=MSO_ANCHOR.MIDDLE, name=f"Row {index} detail")
        y += height + 0.09
    text(slide, LEFT, 6.50, WIDTH, 0.30,
         "Uses: reason for the label · cited as not applicable · mentioned only",
         size=14, color=MUTED, name="Uses footer")


def build(out):
    prs = Presentation(TEMPLATE)
    slide_ids = prs.slides._sldIdLst
    for slide_id in list(slide_ids):
        prs.part.drop_rel(slide_id.rId)
        slide_ids.remove(slide_id)

    # 1. Use the previous seminar's cover layout and presenter details.
    previous_cover = Presentation(PREVIOUS).slides[0]
    slide = new_slide(prs, previous_cover.slide_layout.name, "")
    for idx in (0, 2):
        put(slide, idx, previous_cover.placeholders[idx].text)
    put(slide, 1, "From bars to guideline rules: tracing annotations back to the guideline", size=40)
    put(slide, 3, "Error analysis: method and first results")
    text(slide, LEFT, 6.76, WIDTH, 0.28, "2026-11-06", size=16, color=MUTED, name="Date")

    # 2. Read the bars.
    slide = content_slide(
        prs, "10 Bar chart", "Which guideline rules are behind each bar?",
        "Strict TP means same span and same type as the gold annotation. A refined guideline is the final "
        "guideline of one refinement loop; a loop is a sequence of rounds, and in the top-4 method each round "
        "merges four principles. On 2026-10-30 the professor asked to connect each guideline's results to "
        "its rules. Today: the method, and first results for one guideline.", keep=(3,),
    )
    add_bar_chart(slide)
    text(slide, 7.97, 2.82, 4.53, 2.82, [
        "One bar: one refined guideline, one entity type",
        "Bar value: strict TP minus the baseline mean",
        "Baseline: 19 runs with the original guideline",
        "Goal: candidate rules for good guideline writing",
    ], size=16, space_after=15, name="Body")

    # 3. Trace the workflow.
    slide = content_slide(
        prs, "09 Workflow", "Four steps lead from a bar to candidate rules",
        "Steps 1 to 4 propose candidate rules from the saved annotations without new model calls. "
        "Step 5 re-annotates with a candidate rule removed or added, to test whether that rule changes the annotations.",
    )
    add_workflow(slide)

    # 4. Split the difference by mention.
    slide = content_slide(
        prs, "12 Results table", "Each mention's difference from the baseline adds up to the bar",
        "Both mentions come from the run with the guideline of top-4 loop07, the seventh loop of the top-4 method. "
        "The bar is a difference of two counts, so it splits exactly into one difference per mention. One mention "
        "alone can be noise; differences are read only after summing them per rule.", keep=(2,),
    )
    text(slide, LEFT, 2.13, WIDTH, 0.48,
         "Difference = this run (1 right, 0 not) − share of baseline runs right", size=22, name="Formula")
    results_table(slide, 2.82, [
        ["Mention", "Gold type", "Baseline runs right", "This run", "Difference"],
        ['"ability to produce [metastatic tumors] in nude mice"', "Disease Class", "19 of 19", "missed", "−1"],
        ['"Germline [VHL] gene mutations predispose"', "Modifier", "0 of 19", "right", "+1"],
    ], [5.27, 1.64, 2.00, 1.22, 1.5366667], [0.66, 0.77, 0.77], center=(2, 3, 4))
    body(slide, 5.36, [
        "All Modifier mentions add up to the Modifier bar: +40.7",
        "False positives (FPs) with no gold overlap are counted separately.",
        "FP difference = (1 if predicted this run, 0 otherwise) − baseline rate for that prediction",
    ], size=21, spacing=6)

    # 5. Show the saved annotation evidence.
    slide = content_slide(
        prs, "12 Results table", "For every annotation, the model wrote a citation and a rationale",
        "The annotation prompt asks for a rationale and the corresponding guideline section with every annotation. "
        "Both examples are from the run with the top-4 loop07 guideline.", keep=(2,),
    )
    results_table(slide, 2.24, [
        ["Text", "Label", "Citation", "Rationale"],
        ['"an 80 % risk of [breast cancer]"', "Modifier", '"Section 3 - Context and population frames"',
         '"The disease name is the complement of the context noun risk in \'risk of breast cancer\', '
         'so it is a Modifier rather than a standalone disease."'],
        ['"Germline [VHL] gene mutations"', "Modifier",
         '"§3 Disease premodifier within a gene or protein designation"',
         '"Disease abbreviation premodifies the gene head \'gene\' in \'VHL gene mutations\', '
         'matching the DTD gene example."'],
    ], [2.15, 1.20, 2.94, 5.3766667], [0.48, 1.16, 1.26], size=18)
    body(slide, 5.53, [
        "Citations are free text, often only a section",
        "Rationales describe the reason; they rarely quote the guideline",
    ], size=22)

    # 6. Match a citation and rationale.
    slide = content_slide(
        prs, "05 Key points", "Step 2 matches citation and rationale to one guideline sentence",
        "The matching sees the text, the label, the citation and the rationale, but not whether the annotation is "
        "correct. If the cited place does not state the condition and label in the rationale, the sentence is "
        "searched in the whole guideline (next slide). Every recorded sentence is checked word for word against "
        "the guideline.",
    )
    add_matching_rows(slide)

    # 7. Resolve imprecise citations.
    slide = content_slide(
        prs, "12 Results table", "When the citation is imprecise, the rationale decides",
        "The left column quotes the model's citation and explains how to read it. The last column quotes excerpts "
        "from the final guideline used for each annotation. Row 1: Section 1.6 lists route (iii) within a sentence "
        "on line 205. The same line gives ovarian cancer as an example of a fixed site-plus-category compound. "
        "Row 2: the Section 3 exception is item (c) on line 74, under the heading Not applied on line 71. "
        "Row 3: rule 1b(d) on line 58 covers the generic statement. The negative constraint in rule 1b(b) concerns "
        "enumerated findings and does not apply to this example.",
        keep=(2,),
    )
    evidence_table = results_table(slide, 1.78, [
        ["Model citation and how to read it", "Clue from the rationale", "Verbatim guideline excerpt"],
        ['"Section 1.6(iii)"',
         '"[breast carcinoma]" combines a site and a cancer type in a fixed expression.',
         '"(iii) a fixed nomenclature compound in which the modifier is attached directly to the head rather than '
         'linked by a free preposition"'],
        ['"§1 Specific Disease; §3 gene designation not applied (position)"',
         '"DCC (deleted in [colorectal cancer]) gene": the disease name is inside the gene’s expanded name.',
         '"(c) The span is not in the leading premodifying position."'],
        ['"Rule 1b(d) unanchored generic frame; Rule 1b(b) negative constraints"',
         '"the [tumours] they develop" refers to tumours as a class.',
         '"(d) Unanchored, generic frame → Disease Class. An unanchored head noun in a generic frame is a Disease Class."'],
    ], [3.62, 3.30, 4.7466667], [0.48, 1.25, 1.25, 1.24], size=15)
    for row, (explanation, source) in enumerate([
        ("Section 1.6 lists (iii) within a sentence.", "top-4 loop01 · line 205"),
        ("The §3 citation points to an exception.", "top-4 loop07 · line 74"),
        ("Only 1b(d) fits. Rule 1b(b) concerns lists of findings.", "top-4 loop04 · line 58"),
    ], start=1):
        for column, detail in ((0, explanation), (2, source)):
            paragraph = evidence_table.table.cell(row, column).text_frame.add_paragraph()
            paragraph.space_before = Pt(4)
            run = paragraph.add_run()
            run.text = detail
            style_run(run, size=13, color=MUTED, font=FONT)
    body(slide, 6.34, ["All 2,918 annotations that differ from the baseline were matched"], size=20)

    # 8. Group the rule conditions.
    slide = content_slide(
        prs, "12 Results table", "Step 3 groups sentences into rules and counts each condition",
        "Excerpts of different lengths from the same guideline sentence or list item are grouped into one rule. "
        "If the same rule appears elsewhere in the guideline, that occurrence is tracked separately. "
        "Line 65 assigns Modifier in both examples. In risk of breast cancer, breast cancer is the complement "
        "of risk. In cancer risk, cancer comes before and modifies risk. Three annotations were linked to line 65 "
        "without a condition identified in the rationale.", keep=(2,),
    )
    body(slide, 2.00, [
        "Group excerpts from the same guideline sentence or list item as one rule.",
        "Count annotations by the condition named in each rationale.",
    ], size=22)
    text(slide, LEFT, 3.50, WIDTH, 0.34,
         "45 annotations linked to one Modifier rule (top-4 loop07, line 65)",
         size=18, color=MUTED, name="Table title")
    results_table(slide, 3.91, [
        ["Condition named in the rationale", "Example", "Annotations"],
        ['"is the complement of"', '"risk of [breast cancer]"', "27"],
        ['"premodifies"', '"[cancer] risk"', "15"],
        ["No condition named", "", "3"],
    ], [4.95, 4.64, 2.0766667], [0.56, 0.59, 0.59, 0.59], center=(2,))

    # 9. Sum the differences.
    slide = content_slide(
        prs, "05 Key points", "Step 4 sums the differences rule by rule",
        "Gains and losses are sums of the per-mention differences of slide 4, so they are in strict-TP units. "
        "A mention the run did not annotate has no citation and no rationale, so it cannot be matched to a rule; "
        "for top-4 loop07 these are 25 gold mentions (−8.2) and 37 positions the baseline runs predicted without "
        "a gold mention (−8.3).",
    )
    body(slide, 2.18, [
        "Gains: mentions this run gets right more often",
        "Losses: mentions this run gets wrong more often",
        "Extra predictions without gold: counted separately",
        "Annotation relying on two rules: counted under both",
        "Mentions not annotated: no rationale, listed separately",
        "Check: sums equal the bars (top-4 loop07: all three)",
    ], spacing=12)

    # 10. Report the preliminary results.
    slide = content_slide(
        prs, "12 Results table", "top-4 loop07: candidate rules behind its bars",
        "Gains and losses are in strict-TP units against the baseline mean. Line 65 helps when the disease name "
        "premodifies the noun and hurts when it is the complement: 27 annotations, mostly gold Specific Disease "
        "labelled Modifier. Line 69's gain is concentrated: 16.0 of it comes from VHL in two documents. "
        "Re-annotation: remove the rule from the refined guideline, or add it to the original guideline, and run "
        "with the unchanged guideline in the same batch.", keep=(2,),
    )
    results_table(slide, 1.71, [
        ["Rule in the top-4 loop07 guideline", "Annotations", "Gains", "Losses", "Extra predictions"],
        ["Disease premodifier of a gene or protein name → Modifier (line 69)", "60", "+36.0", "−0.1", "4"],
        ['Context or population noun, "is the complement of" → Modifier (line 65)', "27", "0", "−26.5", "0"],
        ['Context or population noun, "premodifies" → Modifier (line 65)', "15", "+6.3", "0", "0"],
        ["Composite Mention rule, same as the original guideline (line 48)", "37", "+2.1", "−9.3", "0"],
    ], [6.25, 1.50, 0.94, 1.00, 1.9766667], [0.51, 0.68, 0.68, 0.68, 0.68],
        center=(1, 2, 3, 4), size=16)
    body(slide, 5.24, [
        "VHL alone: +16.0, from 2 documents",
        "Across all 11 guidelines, the largest gain in 10 comes from a premodifier → Modifier rule",
        "These rules are candidates; re-annotation tests them",
        "Next: all 11 refined guidelines, then re-annotation",
    ], size=20, spacing=5)

    normalize_slide_ids(prs)
    assert len(prs.slides) == 10
    prs.save(out)
    print(f"Saved {out} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=OUT)
    build(parser.parse_args().output)
