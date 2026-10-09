"""Build the English seminar deck for the P0-P4 follow-up checks.

Style follows archive/2026-10-02_seminar-conflict-casestudy/conflict_handle_casestudy.pptx:
10 x 5.62 in slides, Arial, slate #647386 / navy #24364A / blue #00529B, kicker +
24pt title + takeaway strip on content slides, giant-number section dividers,
quote cards with #F0F5FA fill. All evidence (guideline excerpts, matrices,
scores) is embedded as native shapes/tables — no external links.

    python todo-temp/build_p0p4_slides.py
Output: docs/slides/20261008_p0-p4_findings_en.pptx
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "slides" / "20261008_p0-p4_findings_en.pptx"

NAVY = RGBColor(0x24, 0x36, 0x4A)
SLATE = RGBColor(0x64, 0x73, 0x86)
BLUE = RGBColor(0x00, 0x52, 0x9B)
CARD = RGBColor(0xF0, 0xF5, 0xFA)
PANEL = RGBColor(0xF7, 0xF9, 0xFB)
RED = RGBColor(0xB3, 0x2D, 0x2D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FOOTER = "When Refinement Writes the Wrong Rule"
N_SLIDES = 23

prs = Presentation()
prs.slide_width = Inches(10)
prs.slide_height = Inches(5.625)
BLANK = prs.slide_layouts[6]


def box(slide, x, y, w, h, fill=None):
    sh = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))  # 1 = rectangle
    sh.fill.solid() if fill else sh.fill.background()
    if fill:
        sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def text(slide, x, y, w, h, runs, size=14, color=NAVY, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line_spacing=1.0):
    """runs: str, or list of paragraphs; each paragraph is str or list of (text, dict) runs."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    if isinstance(runs, str):
        runs = [runs]
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        if isinstance(para, str):
            para = [(para, {})]
        for txt, kw in para:
            r = p.add_run()
            r.text = txt
            r.font.name = "Arial"
            r.font.size = Pt(kw.get("size", size))
            r.font.bold = kw.get("bold", bold)
            r.font.color.rgb = kw.get("color", color)
    return tb


def chrome(slide, idx, kicker=None, title=None, takeaway=None):
    """footer + page number + optional kicker/title/takeaway (reference geometry)."""
    if takeaway:
        text(slide, 0.80, 5.08, 8.10, 0.30, takeaway, size=12.5, color=NAVY)
    else:
        text(slide, 0.80, 5.18, 7.70, 0.20, FOOTER, size=8.5, color=SLATE)
    text(slide, 8.93, 5.14, 0.77, 0.28, f"{idx} / {N_SLIDES}", size=9.5, color=SLATE)
    if kicker:
        text(slide, 0.80, 0.35, 8.40, 0.32, kicker, size=9, color=SLATE)
    if title:
        text(slide, 0.80, 0.75, 8.40, 0.60, title, size=24, color=NAVY, bold=True)


def divider(idx, num, title, subtitle):
    s = prs.slides.add_slide(BLANK)
    text(s, 0.80, 0.90, 8.40, 1.60, num, size=80, color=BLUE, bold=True)
    box(s, 0.80, 2.65, 0.70, 0.03, fill=BLUE)
    text(s, 0.80, 2.85, 8.40, 1.00, title, size=36, color=NAVY, bold=True)
    text(s, 0.80, 3.95, 8.40, 0.50, subtitle, size=14, color=SLATE)
    text(s, 0.80, 5.18, 7.70, 0.20, FOOTER, size=8.5, color=SLATE)
    text(s, 8.93, 5.14, 0.77, 0.28, f"{idx} / {N_SLIDES}", size=9.5, color=SLATE)
    return s


def label(slide, x, y, txt, color=BLUE):
    text(slide, x, y, 4.0, 0.26, txt, size=11, color=color, bold=True)


def quote_card(slide, x, y, w, h, body, size=13.5):
    box(slide, x, y, w, h, fill=CARD)
    text(slide, x + 0.22, y + 0.14, w - 0.44, h - 0.28, body, size=size, color=NAVY,
         line_spacing=1.05)


def table(slide, x, y, w, h, rows, col_widths=None, header=True, size=11.5, align_first_left=True):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = shape.table
    if col_widths:
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = Inches(cw)
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            c = tbl.cell(ri, ci)
            c.margin_top = c.margin_bottom = Pt(2)
            c.margin_left = c.margin_right = Pt(6)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = c.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if (ci == 0 and align_first_left) else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = str(cell)
            r.font.name = "Arial"
            r.font.size = Pt(size)
            r.font.bold = header and ri == 0
            r.font.color.rgb = BLUE if (header and ri == 0) else NAVY
    return tbl


# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK)
box(s, 0.80, 0.69, 0.54, 0.09, fill=BLUE)
box(s, 1.43, 0.69, 0.25, 0.09, fill=SLATE)
text(s, 0.80, 1.10, 8.40, 0.37, "FIVE CONTROLLED CHECKS ON ITERATIVE GUIDELINE REFINEMENT",
     size=12, color=SLATE, bold=True)
text(s, 0.80, 1.80, 8.40, 1.40, "When Refinement Writes the Wrong Rule", size=38, color=NAVY, bold=True)
text(s, 0.80, 3.47, 8.40, 0.70, "One failure case, five follow-up experiments — NCBI Disease, GPT-5.4",
     size=18, color=SLATE)
text(s, 0.80, 4.58, 8.40, 0.36, "Hengyu Zhou · 2026-10-08", size=14, color=BLUE)
text(s, 8.93, 5.14, 0.77, 0.28, f"1 / {N_SLIDES}", size=9.5, color=SLATE)

# ------------------------------------------------------------- 2 divider
divider(2, "01", "SETUP", "The refinement loop, and the warning sign that started this")

# ------------------------------------------------------------- 3 the loop
s = prs.slides.add_slide(BLANK)
chrome(s, 3, "01 — SETUP / THE LOOP", "One error group per round, accepted if dev F1 rises",
       takeaway="Each round sees one error group and the already-correct cases — never the full evidence picture.")
steps = [
    ("1 · ANNOTATE", "Score 10 dev documents with the current guideline"),
    ("2 · GROUP", "Cluster mismatches by (gold label, predicted label)"),
    ("3 · ANALYZE", "Explain the largest group; condense to one principle"),
    ("4 · REWRITE", "Rewrite the guideline around the principle"),
    ("5 · ACCEPT?", "Keep the rewrite only if dev F1 improves"),
]
for i, (h, b) in enumerate(steps):
    x = 0.80 + i * 1.74
    box(s, x, 1.60, 1.60, 1.75, fill=CARD)
    text(s, x + 0.12, 1.72, 1.36, 0.30, h, size=11, color=BLUE, bold=True)
    text(s, x + 0.12, 2.06, 1.36, 1.20, b, size=11.5, color=NAVY, line_spacing=1.05)
text(s, 0.80, 3.80, 8.40, 0.30, "Reference run: dev F1 0.7972 → 0.9091 in 4 rounds (stop at F1 ≥ 0.90).",
     size=14, color=NAVY)
text(s, 0.80, 4.24, 8.40, 0.60, [
    [("The warning sign: ", dict(bold=True)),
     ("the refined guideline came to contain ", {}),
     ("do-not-annotate examples that gold actually annotates", dict(bold=True, color=RED)),
     (".", {})]],
    size=14, color=NAVY)

# ------------------------------------------------------------- 4 warning sign
s = prs.slides.add_slide(BLANK)
chrome(s, 4, "01 — SETUP / THE WARNING SIGN", "Two exclusions that contradict gold",
       takeaway="Both strings are gold mentions in the dev documents the loop was shown.")
label(s, 0.80, 1.45, "WRITTEN INTO THE GUIDELINE (EXAMPLE 27)")
quote_card(s, 0.80, 1.75, 8.40, 1.05,
           "\u201cDo not automatically annotate \u2018deficient activity of fatty aldehyde "
           "dehydrogenase\u2019 when it is only a biochemical/molecular abnormality or "
           "enzyme-activity readout\u2026\u201d")
text(s, 0.80, 2.88, 8.40, 0.28, [[
    ("gold: ", dict(bold=True)), ("SpecificDisease", dict(bold=True, color=RED)),
    ("  ·  doc 10577908  ·  model misses it in every arm we tested", dict(color=SLATE))]],
    size=12.5)
label(s, 0.80, 3.36, "WRITTEN INTO THE GUIDELINE (COATS EXAMPLE)")
quote_card(s, 0.80, 3.66, 8.40, 1.05,
           "\u201cDo not annotate \u2018abnormal retinal vascular development\u2019 when it is used "
           "only as a mechanistic/process description rather than the condition mention itself.\u201d")
text(s, 0.80, 4.79, 8.40, 0.28, [[
    ("gold: ", dict(bold=True)), ("DiseaseClass", dict(bold=True, color=RED)),
    ("  ·  doc 10484772  ·  also never recovered", dict(color=SLATE))]], size=12.5)

# ------------------------------------------------------------- 5 five checks
s = prs.slides.add_slide(BLANK)
chrome(s, 5, "01 — SETUP / THE PLAN", "Five checks, one variable each",
       takeaway="P0 establishes the facts; P1–P4 each vary exactly one thing.")
rows = [
    ("P0", "What did Round 4 actually change?", "Replay the scoring; per-entity history"),
    ("P1", "Is the safety clause to blame?", "Delete it, change nothing else"),
    ("P2", "What if the clause only scopes its own rule?", "Rewrite it scoped, same everything"),
    ("P3", "Does moderating 4 groups at once help?", "Top-4 vs Top-1, then a 100-doc validation"),
    ("P4", "Does more development data help?", "10 vs 20 vs 30 docs; hardcoding vs valid F1"),
]
for i, (tag, q, how) in enumerate(rows):
    y = 1.55 + i * 0.68
    box(s, 0.80, y, 0.62, 0.52, fill=BLUE)
    text(s, 0.80, y + 0.10, 0.62, 0.32, tag, size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 1.66, y + 0.02, 5.30, 0.30, q, size=14, color=NAVY, bold=True)
    text(s, 1.66, y + 0.30, 7.60, 0.26, how, size=11.5, color=SLATE)

# ------------------------------------------------------------- 6 divider P0
divider(6, "02", "P0 · WHAT DID ROUND 4 CHANGE?", "Full scoring replay, per-entity, before blaming the round")

# ------------------------------------------------------------- 7 P0 results
s = prs.slides.add_slide(BLANK)
chrome(s, 7, "02 — P0 / ROUND 4 REPLAY", "Round 4: +0.022, three fixes, one new regression",
       takeaway="norrin and FALDH were missed before Round 4 — they are pre-existing misses, not new regressions.")
text(s, 0.80, 1.45, 4.0, 0.28, "DEV F1 PER ROUND (10 DOCS)", size=11, color=BLUE, bold=True)
table(s, 0.80, 1.78, 4.10, 1.60,
      [["start", "R1", "R2", "R3", "R4"],
       ["0.7972", "0.8369", "0.8592", "0.8873", "0.9091"]],
      header=False, size=12.5)
text(s, 0.80, 3.55, 4.1, 1.20, [
    [("Fixed: ", dict(bold=True)), ("spasticity + 2 more; ", {})],
    [("New regression: ", dict(bold=True)), ("1 case", {})],
    [("Still missed: ", dict(bold=True)), ("norrin, FALDH — both already missed in Round 2", {})]],
    size=12, line_spacing=1.15)
text(s, 5.30, 1.45, 4.2, 0.28, "DISCREPANCY MATRIX, R4 IN → OUT", size=11, color=BLUE, bold=True)
hdr = ["", "C", "D", "M", "S", "O"]
before = [hdr, ["C", 0, 0, 0, 0, 1], ["D", 0, 0, 0, 0, 2], ["M", 0, 0, 0, 0, 0],
          ["S", 0, 2, 2, 1, 3], ["O", 0, 0, 0, 0, 0]]
after = [hdr, ["C", 0, 0, 0, 0, 1], ["D", 0, 0, 0, 0, 2], ["M", 0, 0, 0, 0, 0],
         ["S", 0, 3, 0, 1, 2], ["O", 0, 0, 0, 0, 0]]
text(s, 5.30, 1.74, 2.0, 0.22, "before R4 (11)", size=10, color=SLATE)
t1 = table(s, 5.30, 1.96, 2.05, 1.45, before, size=9)
text(s, 7.55, 1.74, 2.0, 0.22, "after R4 (9)", size=10, color=SLATE)
t2 = table(s, 7.55, 1.96, 2.05, 1.45, after, size=9)
for _t in (t1, t2):
    for _row in _t.rows:
        _row.height = Inches(0.21)
text(s, 5.30, 4.12, 4.0, 0.90, "S→D label errors 2 → 3, S-span errors 1 → 0, missed S 3 → 2. "
     "Composite: 1 over-generation in both.", size=11, color=SLATE, line_spacing=1.15)

# ------------------------------------------------------------- 8 divider P1
divider(8, "03", "P1 · DELETE THE SAFETY CLAUSE?", "Single-variable ablation of the \u201cdo not apply\u201d half")

# ------------------------------------------------------------- 9 P1 design
s = prs.slides.add_slide(BLANK)
chrome(s, 9, "03 — P1 / WHAT WAS CUT", "The Round-3 principle has two halves",
       takeaway="Same prompt, same documents, same model — the only change is the cut.")
label(s, 0.80, 1.50, "RECALL HALF — KEPT")
quote_card(s, 0.80, 1.80, 8.40, 0.95,
           "\u201cIF a noun phrase in a definitional, characterization, or causal/etiologic context "
           "denotes an abnormal clinical or pathological state … THEN annotate it as DiseaseClass\u201d",
           size=12.5)
label(s, 0.80, 2.98, "SAFETY HALF — REMOVED", color=RED)
quote_card(s, 0.80, 3.28, 8.40, 0.95,
           "\u201cdo not apply this rule when the phrase refers only to a normal biological process, "
           "a molecular/substance entity or level, or an isolated descriptive finding\u2026\u201d",
           size=12.5)
text(s, 0.80, 4.42, 8.40, 0.30, "Hypothesis: the clause over-excludes, causing the norrin/FALDH-type misses.",
     size=13, color=NAVY)

# ------------------------------------------------------------- 10 P1 result
s = prs.slides.add_slide(BLANK)
chrome(s, 10, "03 — P1 / RESULT", "Misses do not come back; errors get worse",
       takeaway="The model re-wrote an equivalent restriction on its own — the clause reflects its judgment, not its instructions.")
table(s, 0.80, 1.55, 8.40, 1.85,
      [["", "original clause", "clause removed"],
       ["dev F1 (R3 replay)", "0.8873", "0.8671"],
       ["focal misses recovered (norrin / FALDH / retinal vascular)", "—", "0 of 3"],
       ["S→D label errors", "2", "4  (doubled)"],
       ["equivalent restriction in output", "yes", "re-generated by the model"]],
      col_widths=[3.9, 2.2, 2.3], size=12)
text(s, 0.80, 3.70, 8.40, 0.75, [
    [("Verdict: ", dict(bold=True, color=BLUE)),
     ("the \u201cdo not apply\u201d clause is a precision guardrail. The misses are the model\u2019s "
      "own reading of these contexts; deleting the clause only removes the guardrail.", {})]],
    size=14, line_spacing=1.15)

# ------------------------------------------------------------- 11 divider P2
divider(11, "04", "P2 · RESCOPE THE CLAUSE?", "Same edit, but the clause is rewritten to bind only its own rule")

# ------------------------------------------------------------- 12 P2 result
s = prs.slides.add_slide(BLANK)
chrome(s, 12, "04 — P2 / RESULT", "Scoping is even weaker — and still no misses return",
       takeaway="All three principle variants leave the same three gold mentions missed.")
table(s, 0.80, 1.55, 8.40, 1.60,
      [["principle variant", "dev F1", "focal misses recovered"],
       ["original (R3)", "0.8873", "0 of 3"],
       ["P1 · clause removed", "0.8671", "0 of 3"],
       ["P2 · clause rescoped", "0.8511  (below baseline → reverted)", "0 of 3"]],
      col_widths=[3.0, 3.4, 2.0], size=12)
text(s, 0.80, 3.45, 8.40, 1.10, [
    [("Verdict: ", dict(bold=True, color=BLUE)),
     ("the gold-contradicting examples are a ", {}),
     ("symptom", dict(bold=True)),
     (" of the model\u2019s upstream judgment, not the cause. Wording edits — delete or rescope — "
      "cannot recover these mentions, and only trade away precision.", {})]],
    size=14, line_spacing=1.15)

# ------------------------------------------------------------- 13 divider P3
divider(13, "05", "P3 · MODERATE 4 GROUPS AT ONCE?", "Top-4 versus Top-1, then a 100-document validation")

# ------------------------------------------------------------- 14 P3 dev + hardcoding
s = prs.slides.add_slide(BLANK)
chrome(s, 14, "05 — P3 / DEV RESULT + HARD-CODING CHECK", "Faster, not more memorized",
       takeaway="Parallelizing the rewrite does not turn into more answer-key copying.")
table(s, 0.80, 1.55, 8.40, 1.60,
      [["", "Top-1 (reference)", "Top-4"],
       ["dev F1", "0.7972 → 0.9091 (4 rounds)", "0.8028 → 0.9155 (2 rounds, threshold)"],
       ["gold strings absorbed into guideline", "15 / 37  (41%)", "12 / 37  (32%)"],
       ["new lines quoting already-correct cases", "15%", "11%"]],
      col_widths=[3.0, 2.9, 2.5], size=12)
text(s, 0.80, 3.50, 8.40, 0.90, "Absorption = share of distinct dev gold strings that appear verbatim in the "
     "final guideline (and were not in the shipped one). The dev gap 0.9155 vs 0.9091 is inside the "
     "dev-10 noise band — the validation set decides.", size=12, color=SLATE, line_spacing=1.15)

# ------------------------------------------------------------- 15 P3 valid
s = prs.slides.add_slide(BLANK)
chrome(s, 15, "05 — P3 / 100 UNSEEN DOCUMENTS", "The dev gain holds up on validation — barely",
       takeaway="Gain concentrates in Modifier recall; SpecificDisease over-predicts more than Top-1.")
table(s, 0.80, 1.50, 8.40, 1.35,
      [["guideline", "P", "R", "F1"],
       ["shipped (original)", "0.8011", "0.7585", "0.7792"],
       ["Top-1 refined", "0.8121", "0.7649", "0.7878"],
       ["Top-4 refined", "0.8095", "0.7952", "0.8023"]],
      col_widths=[3.4, 1.6, 1.6, 1.8], size=12.5)
table(s, 0.80, 3.05, 8.40, 1.15,
      [["per label, Top-1 → Top-4", "Modifier", "SpecificDisease", "DiseaseClass"],
       ["F1", "0.765 → 0.851  (TP +26)", "0.851 → 0.824  (FP 58 → 83)", "0.650 → 0.637"]],
      col_widths=[2.8, 2.2, 2.2, 1.2], size=11.5)
text(s, 0.80, 4.42, 8.40, 0.50, "Paired bootstrap on the 100 documents: Top-4 − Top-1 = +0.0145, "
     "95% CI [−0.021, +0.050] — a real but not-yet-significant edge.", size=11.5, color=SLATE)

# ------------------------------------------------------------- 16 P3 side effect
s = prs.slides.add_slide(BLANK)
chrome(s, 16, "05 — P3 / SIDE EFFECT, TRACED", "Gold shown — the exclusion was written anyway",
       takeaway="Evidence reaches the analysis calls but never the call that writes the guideline.")
flow = [
    ("SHOWN (round 1, analysis call)", "Gold: SpecificDisease, LLM: O, Entity Text: "
     "\u201cdeficient activity of fatty aldehyde dehydrogenase\u201d", CARD, NAVY),
    ("DROPPED (principle step)", "The generated principle abstracts the case away — "
     "the entity name does not survive into the principle text.", CARD, NAVY),
    ("NEVER SEEN (rewrite call)", "refine_guidelines receives only the principles and the "
     "already-correct cases — no gold-labeled discrepancies.", CARD, NAVY),
    ("WRITTEN (final guideline)", "The do-not-annotate example for FALDH appears in round 1 "
     "and survives to the final guideline.", CARD, RED),
]
for i, (h, b, fill, hc) in enumerate(flow):
    y = 1.50 + i * 0.88
    box(s, 0.80, y, 8.40, 0.76, fill=fill)
    text(s, 1.02, y + 0.07, 3.1, 0.24, h, size=10.5, color=hc, bold=True)
    text(s, 1.02, y + 0.32, 7.96, 0.40, b, size=11.5, color=NAVY)

# ------------------------------------------------------------- 17 divider P4
divider(17, "06", "P4 · MORE DEVELOPMENT DATA?", "10 vs 20 vs 30 dev documents; hardcoding count vs validation")

# ------------------------------------------------------------- 18 P4 table
s = prs.slides.add_slide(BLANK)
chrome(s, 18, "06 — P4 / SCALE 10 / 20 / 30", "Hardcoding collapses; validation does not follow",
       takeaway="Less copying does not turn into better unseen-document performance.")
table(s, 0.80, 1.50, 8.40, 1.85,
      [["dev size", "dev F1", "absorbed", "valid F1 (100 docs)"],
       ["10", "0.7972 → 0.9091", "15 / 37  (41%)", "0.7878"],
       ["20", "0.7821 → 0.8105", "6 / 68  (9%)", "0.7745  (below original 0.7792)"],
       ["30", "0.8092 → 0.8577", "3 / 115  (3%)", "0.8050"]],
      col_widths=[1.3, 2.5, 2.1, 2.5], size=12)
text(s, 0.80, 3.62, 8.40, 1.05, [
    "Paired bootstrap: only dev30 vs original is near-significant (+0.026, one-sided 97%); "
    "every arm-to-arm difference has a 95% CI crossing 0. Correction to earlier notes: all three "
    "runs used n_examples = 5 (verified in configs and prompts) — no example-count confound. "
    "One trajectory per size; replicate runs were designed but not executed."],
    size=11.5, color=SLATE, line_spacing=1.2)

# ------------------------------------------------------------- 19 P4 gold check
s = prs.slides.add_slide(BLANK)
chrome(s, 19, "06 — P4 / SAME-KIND GOLD CHECK", "Scale does not stop gold-contradicting exclusions",
       takeaway="The dev-30 guideline excludes norrin — whose home document is inside the dev-30 split.")
label(s, 0.80, 1.50, "WRITTEN INTO THE DEV-30 GUIDELINE")
quote_card(s, 0.80, 1.80, 8.40, 0.95,
           "\u201c\u2018BRCA1 alterations\u2019, \u2018PEX1 mutations\u2019, and \u2018deficiency of "
           "norrin\u2019 are not annotated merely because they contain gene/protein or deficiency "
           "language.\u201d", size=13)
text(s, 0.80, 2.88, 8.40, 0.30, [[
    ("gold: ", dict(bold=True)), ("DiseaseClass", dict(bold=True, color=RED)),
    ("  ·  doc 10484772 — inside dev30  ·  still missed", dict(color=SLATE))]], size=12.5)
table(s, 0.80, 3.42, 8.40, 1.10,
      [["guideline", "conflicting exclusion examples (manual audit)", "valid F1"],
       ["dev10 / dev20", "0 at the flat-example level  (dev20 has zero gold overlap at all)", "0.7878 / 0.7745"],
       ["dev30", "1 real (norrin) + inherited conditional rules", "0.8050"]],
      col_widths=[1.7, 4.7, 2.0], size=11.5)

# ------------------------------------------------------------- 20 divider synthesis
divider(20, "07", "WHAT FIVE CHECKS RULE OUT", "Every wording- and evidence-side lever was tried")

# ------------------------------------------------------------- 21 the gap
s = prs.slides.add_slide(BLANK)
chrome(s, 21, "07 — SYNTHESIS / THE GAP", "The evidence never reaches the call that writes the rule",
       takeaway="Edit the wording (P1/P2), add parallel evidence (P3), add data (P4) — none of it reaches this call.")
flow = [
    ("annotate + score dev docs", False),
    ("cluster mismatches", False),
    ("per-cluster analysis — gold labels visible here", False),
    ("principles — entity names dropped", False),
    ("rewrite guideline — sees principles + already-correct cases only", True),
]
for i, (t, hot) in enumerate(flow):
    x = 0.55 + i * 1.94
    box(s, x, 1.70, 1.80, 1.50, fill=(RED if hot else CARD))
    text(s, x + 0.10, 1.82, 1.60, 1.26, t, size=10.5,
         color=(WHITE if hot else NAVY), bold=hot, line_spacing=1.05)
text(s, 0.80, 3.55, 8.40, 1.10, [
    [("Ruled out: ", dict(bold=True, color=BLUE)),
     ("the safety clause (P1), its scope (P2), parallel evidence to the analysis calls (P3), "
      "and dev-set size (P4).", {})],
    [("Located: ", dict(bold=True, color=BLUE)),
     ("gold-labeled discrepancy evidence is dropped at the principle step and never shown to "
      "the rewrite call.", {})]],
    size=13.5, line_spacing=1.25)

# ------------------------------------------------------------- 22 next steps
s = prs.slides.add_slide(BLANK)
chrome(s, 22, "07 — SYNTHESIS / NEXT", "Two candidate fixes, aimed at the gap",
       takeaway="Validate on the small split first; only then spend the 100-document evaluation.")
box(s, 0.80, 1.55, 4.05, 2.30, fill=CARD)
text(s, 1.02, 1.70, 3.6, 0.30, "A · FEED THE REWRITE", size=11.5, color=BLUE, bold=True)
text(s, 1.02, 2.06, 3.65, 1.65, "Inject the gold-labeled discrepancy cases into the rewrite call "
     "itself (\u201cnew rules must not contradict these\u201d), not only into the analysis calls.",
     size=13, color=NAVY, line_spacing=1.15)
box(s, 5.15, 1.55, 4.05, 2.30, fill=CARD)
text(s, 5.37, 1.70, 3.6, 0.30, "B · VERIFY AFTER WRITING", size=11.5, color=BLUE, bold=True)
text(s, 5.37, 2.06, 3.65, 1.65, "Check every new do-not-annotate example against gold before "
     "accepting the guideline; reject or rewrite contradicting ones (post-verify probe direction).",
     size=13, color=NAVY, line_spacing=1.15)
text(s, 0.80, 4.15, 8.40, 0.50, "Either arm is a one-variable replay of the Round-3 boundary — "
     "same cost class as P1/P2.", size=12.5, color=SLATE)

# ------------------------------------------------------------- 23 summary
s = prs.slides.add_slide(BLANK)
chrome(s, 23, "SUMMARY", "Five questions, five answers",
       takeaway="The failure is structural: the rewrite call is blind to labeled evidence.")
table(s, 0.80, 1.50, 8.40, 3.20,
      [["check", "question", "answer"],
       ["P0", "What did Round 4 change?", "+0.022 F1; 3 fixes, 1 regression; the famous misses pre-date it"],
       ["P1", "Blame the safety clause?", "No — a precision guardrail; deleting it doubles S→D errors"],
       ["P2", "Rescope the clause?", "No — misses stay; wording is symptom, not cause"],
       ["P3", "Top-4 over Top-1?", "Yes on validation (0.8023 vs 0.7878), not yet significant; same wrong examples"],
       ["P4", "More dev data?", "Hardcoding collapses 41%→3%; validation flat; exclusions persist"]],
      col_widths=[0.8, 2.9, 4.7], size=11.5)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f"saved {OUT} ({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
