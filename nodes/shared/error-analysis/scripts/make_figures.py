"""Figures for 20261024_error_analysis_report.md, as plain SVG (no plotting library needed).

Offline. Reads error_patterns.json, gold_precedent.json, rounds.json, rule_links.json and rule_chain.json (written
by error_patterns.py, gold_precedent.py, rounds_table.py, rule_links.py and rule_chain.py) and writes
figures/*.svg. Colors: the dataviz skill's reference
palette (categorical slots 1-3 validated together; the two diverging arms validated as ordinal ramps).
Every mark carries a <title>, so a viewer that shows SVG tooltips gives the exact value on hover.
"""

from __future__ import annotations

import json
import statistics
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "outputs"
FIG = Path(__file__).resolve().parents[1] / "reports" / "figures"
N1030 = Path(__file__).resolve().parents[3] / "2026-10-30_seminar" / "error-analysis" / "outputs"
FIG.mkdir(exist_ok=True)

SURFACE, INK, INK2, MUTED, GRID, AXIS, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#f0efec"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
BLUE_ARM = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # fewer errors than any original run
RED_ARM = ["#ea9a93", "#d75853", "#9e3432", "#621b1a"]  # more errors than any original run
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

patterns = json.loads((N1030 / "error_patterns.json").read_text(encoding="utf-8"))
precedent = json.loads((N1030 / "gold_precedent.json").read_text(encoding="utf-8"))
rounds = json.loads((N1030 / "rounds.json").read_text(encoding="utf-8"))
links = json.loads((N1030 / "rule_links.json").read_text(encoding="utf-8"))
chain = json.loads((N1030 / "rule_chain.json").read_text(encoding="utf-8"))
runs = patterns["runs"]
orig = [r for r in runs if r["guideline"] == "original"]
changed = [r for r in runs if r["guideline"] != "original"]
assert len(orig) == 19 and len(changed) == 11


class Svg:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.parts = w, h, []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x, y, s, size=12, fill=INK, anchor="start", weight="normal") -> None:
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}">{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke=GRID, width=1) -> None:
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"/>')

    def bar(self, x0, x1, y, h, fill, tip="", r=4.0) -> None:
        """Horizontal bar from baseline x0 to data end x1; square at the baseline, rounded at the data end."""
        if abs(x1 - x0) < 0.5:
            return
        r = min(r, abs(x1 - x0) / 2, h / 2)
        if x1 > x0:
            d = f"M{x0:.1f},{y:.1f} H{x1 - r:.1f} A{r},{r} 0 0 1 {x1:.1f},{y + r:.1f} V{y + h - r:.1f} A{r},{r} 0 0 1 {x1 - r:.1f},{y + h:.1f} H{x0:.1f} Z"
        else:
            d = f"M{x0:.1f},{y:.1f} H{x1 + r:.1f} A{r},{r} 0 0 0 {x1:.1f},{y + r:.1f} V{y + h - r:.1f} A{r},{r} 0 0 0 {x1 + r:.1f},{y + h:.1f} H{x0:.1f} Z"
        self.add(f'<path d="{d}" fill="{fill}"><title>{escape(tip)}</title></path>')

    def rect(self, x, y, w, h, fill, tip="") -> None:
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"><title>{escape(tip)}</title></rect>')

    def dot(self, x, y, fill, tip="", r=4.5) -> None:
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{SURFACE}" stroke-width="2"><title>{escape(tip)}</title></circle>')

    def swatch(self, x, y, fill, label) -> float:
        self.add(f'<rect x="{x:.1f}" y="{y - 9:.1f}" width="10" height="10" rx="2" fill="{fill}"/>')
        self.text(x + 15, y, label, 12, INK2)
        return x + 15 + 6.6 * len(label) + 18

    def save(self, name: str) -> None:
        body = "\n".join(self.parts)
        (FIG / name).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'font-family="{FONT}">\n<rect width="{self.w}" height="{self.h}" fill="{SURFACE}"/>\n{body}\n</svg>\n', encoding="utf-8")


def ticks(svg: Svg, x_of, values, y_top, y_bottom, fmt=str) -> None:
    for v in values:
        x = x_of(v)
        svg.line(x, y_top, x, y_bottom, GRID)
        svg.text(x, y_bottom + 16, fmt(v), 11, MUTED, "middle")


# ---------------------------------------------------------------- 1. error groups
def fig_groups() -> None:
    names = {
        "disease name used as a modifier, missed": ("Disease name used as a modifier, missed", "VHL gene, tumor suppressor, Atm-deficient"),
        "other missed mentions: symptoms, general words, tumors, deficiencies, the rest": ("Other mentions missed", "short stature, genetic disorder, these tumours"),
        "span shorter or longer than the gold span": ("Span shorter or longer than gold", "familial / sporadic left out, classical added"),
        "Modifier against disease or Composite label": ("Modifier against disease or Composite", "HNPCC kindreds labeled Specific"),
        "Specific against DiseaseClass": ("Specific against DiseaseClass", "hereditary breast cancer labeled DiseaseClass"),
        "Composite label at the gold span, or one prediction over two gold mentions": ("Composite label, or one span over two", "AO2 / DTD as one prediction"),
        "extra mentions and other": ("Extra mentions and other", "scurfy, LA phenotype, infantile form"),
    }
    total = statistics.mean(sum(r["counts"].values()) for r in orig)
    rows = []
    for fam, members in patterns["families"].items():
        vals = [sum(r["counts"][p] for p in members) for r in orig]
        rows.append((fam, statistics.mean(vals), min(vals), max(vals), patterns["family_f1_gain"][fam]))
    svg = Svg(780, 70 + 46 * len(rows) + 55)
    x0, scale = 330, 330 / 90
    x_of = lambda v: x0 + v * scale
    top, bottom = 30, 30 + 46 * len(rows)
    ticks(svg, x_of, [0, 20, 40, 60, 80], top - 6, bottom)
    svg.line(x0, top - 6, x0, bottom, AXIS)
    for i, (fam, mean, lo, hi, gain) in enumerate(rows):
        y = top + 46 * i
        title, example = names[fam]
        svg.text(x0 - 12, y + 14, title, 12.5, INK, "end")
        svg.text(x0 - 12, y + 29, example, 11, MUTED, "end")
        svg.bar(x0, x_of(mean), y + 8, 20, BLUE, f"{title}: mean {mean:.1f} errors per run, lowest {lo}, highest {hi}")
        cy = y + 18
        svg.line(x_of(lo), cy, x_of(hi), cy, INK, 1.5)
        svg.line(x_of(lo), cy - 5, x_of(lo), cy + 5, INK, 1.5)
        svg.line(x_of(hi), cy - 5, x_of(hi), cy + 5, INK, 1.5)
        svg.text(x_of(max(hi, mean)) + 8, y + 22, f"{mean:.1f} ({mean / total:.0%})  F1 +{gain:.3f}", 11.5, INK2)
    svg.text(x0 - 310, bottom + 36, "Errors per run: bar = mean of the 19 original-guideline runs, line = lowest to highest run. Label: mean (share of all", 11, MUTED)
    svg.text(x0 - 310, bottom + 51, "errors) and how much F1 would rise if the whole group were fixed.", 11, MUTED)
    svg.save("fig1_error_groups.svg")


# ---------------------------------------------------------------- 2. training gold consistency
def fig_gold() -> None:
    rows = [
        ("M1", "Modifier", "Disease name before a gene / protein word", "'VHL gene'; validation gold: Modifier"),
        ("M2", "Modifier", "tumor / cancer before a non-disease noun", "'tumor suppressor'; validation gold: Modifier"),
        ("M3", "Modifier", "X-deficient", "'Atm-deficient mice'; validation gold: Modifier"),
        ("M7", "DiseaseClass", "Qualifier + general word", "'genetic disorder'; validation gold: DiseaseClass"),
        ("L1", "Modifier", "Coordinated names before a noun", "'breast and ovarian cancer families'; gold: Modifier"),
        ("L5*", "SpecificDisease", "Strings Haiku labels DiseaseClass", "'hereditary breast cancer'; validation gold: Specific"),
        ("L6*", "DiseaseClass", "Strings Haiku labels Specific", "'lipomas', 'cancers'; validation gold: DiseaseClass"),
    ]
    svg = Svg(780, 80 + 46 * len(rows) + 40)
    x0, width = 330, 360
    x = 20
    for color, label in ((BLUE, "same label as the validation gold"), (ORANGE, "another label or span"), (AQUA, "not annotated")):
        x = svg.swatch(x, 20, color, label)
    top = 44
    for i, (pid, want, title, example) in enumerate(rows):
        c = dict(precedent["constructions"][pid.rstrip("*")])
        if pid.endswith("*"):  # used as a modifier: a different construction, not the Specific / DiseaseClass question
            c.pop("Modifier", None)
        same = c.get(want, 0)
        none = c.get("not annotated", 0)
        other = sum(v for k, v in c.items() if k not in (want, "not annotated", "part of a longer mention"))
        n = same + other + none
        y = top + 46 * i
        svg.text(x0 - 12, y + 14, title, 12.5, INK, "end")
        svg.text(x0 - 12, y + 29, example, 11, MUTED, "end")
        pos = x0
        segs = [(same, BLUE, "same label"), (other, ORANGE, "another label or span"), (none, AQUA, "not annotated")]
        last = max(j for j, s in enumerate(segs) if s[0] > 0)
        for j, (v, color, lab) in enumerate(segs):
            if v == 0:
                continue
            w = width * v / n
            end = pos + w - (0 if j == last else 2)  # 2px surface gap between segments
            tip = f"{title}: {lab} {v} of {n} ({v / n:.0%})"
            if j == last:
                svg.bar(pos, end, y + 8, 20, color, tip)
            else:
                svg.rect(pos, y + 8, end - pos, 20, color, tip)
            if j == 0 and w > 44:
                svg.text(pos + 8, y + 22, f"{v / n:.0%}", 11.5, "#ffffff", "start", "600")
            pos += w
        longer = c.get("part of a longer mention", 0)
        svg.text(x0 + width + 10, y + 22, f"n = {n}", 11, INK2)
    foot = top + 46 * len(rows) + 16
    svg.text(20, foot, "Occurrences in the training gold (543 documents, the 50 test documents excluded). Left out of the bars: occurrences", 11, MUTED)
    svg.text(20, foot + 15, "inside a longer gold mention, and, in the last two rows, uses as a modifier. Neither tests the convention.", 11, MUTED)
    svg.save("fig2_training_gold.svg")


# ---------------------------------------------------------------- 3. qualifiers
def fig_qualifiers() -> None:
    q = sorted(precedent["qualifiers"].items(), key=lambda kv: -kv[1][0] / sum(kv[1]))
    svg = Svg(780, 40 + 30 * len(q) + 40)
    x0, width = 150, 420
    x_of = lambda v: x0 + width * v
    top, bottom = 24, 24 + 30 * len(q)
    ticks(svg, x_of, [0, 0.25, 0.5, 0.75, 1.0], top - 6, bottom, lambda v: f"{v:.0%}")
    svg.line(x0, top - 6, x0, bottom, AXIS)
    for i, (word, (inc, exc)) in enumerate(q):
        y = top + 30 * i
        share = inc / (inc + exc)
        svg.text(x0 - 12, y + 15, word, 12.5, INK, "end")
        svg.bar(x0, x_of(share), y + 4, 16, BLUE, f"{word}: included {inc} of {inc + exc}")
        svg.text(max(x_of(share), x0) + 8, y + 16, f"{share:.0%}  ({inc} of {inc + exc})", 11.5, INK2)
    svg.text(x0, bottom + 34, "Share of training-gold mentions next to the word that include it in the span", 11, MUTED)
    svg.save("fig3_qualifiers.svg")


# ---------------------------------------------------------------- 4. changed guidelines against the original range
def fig_changed() -> None:
    short = {
        "M1": "missed: disease name before gene / protein word", "M2": "missed: tumor in 'tumor suppressor', 'tumor cells'",
        "M3": "missed: X-deficient", "M4": "missed: other modifier", "M5": "missed: tumors / cancers as a class",
        "M6": "missed: enzyme or protein deficiency", "M7": "missed: general word with a qualifier", "M8": "missed: symptom, sign or other",
        "L1": "label: Modifier as Composite", "L2": "label: modifier as a disease", "L3": "label: disease as a modifier",
        "L5": "label: Specific as DiseaseClass", "L6": "label: DiseaseClass as Specific", "L4": "label: Composite at the gold span",
        "U1": "unpaired: gold swallowed by a longer span", "B1": "boundary: span shorter than gold", "B2": "boundary: span longer than gold",
        "X1": "extra: gene or locus symbol", "X2": "extra: animal disease or mutant", "X3": "extra: other", "U2": "unpaired: prediction",
    }
    order = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "L1", "L2", "L3", "L5", "L6", "L4", "U1", "B1", "B2", "X1", "X2", "X3", "U2"]
    gaps_after = {"M4", "M8", "L3", "L6", "U1", "B2"}
    cols = sorted(changed, key=lambda r: -r["f1"])
    cw, rh = 40, 21
    x_lab, x_rng, x0 = 300, 352, 372
    n_gaps = len(gaps_after)
    top = 74
    svg = Svg(x0 + cw * len(cols) + 20, top + rh * len(order) + 8 * n_gaps + 96)
    svg.text(x_rng, top - 10, "original", 10.5, MUTED, "middle")
    svg.text(x_rng, top - 24, "range of", 10.5, MUTED, "middle")
    for j, r in enumerate(cols):
        cx = x0 + cw * j + cw / 2
        name = ("top-1 " if r["method"] == "top-1" else "top-4 ") + r["loop"][-2:]
        svg.text(cx, top - 38, name.split()[0], 10.5, INK2, "middle")
        svg.text(cx, top - 24, name.split()[1], 11.5, INK, "middle", "600")
        svg.text(cx, top - 10, f"{r['f1']:.3f}", 10.5, MUTED, "middle")
    svg.text(x0 - 4, top - 52, "Changed guidelines, best validation F1 first (loop, F1)", 11, MUTED)

    def large(v: int, ref: list[int]) -> bool:
        """Outside the range of ref and at least 3 SD (taken as at least 1) from its mean."""
        return (v < min(ref) or v > max(ref)) and abs(v - statistics.mean(ref)) >= 3 * max(statistics.stdev(ref), 1)

    # chance: how many cells one original run would color against the other 18
    by_chance = statistics.mean(sum(large(x["counts"][p], [y["counts"][p] for y in orig if y is not x]) for p in order) for x in orig)
    colored = 0
    y = top
    for pid in order:
        vals = [r["counts"][pid] for r in orig]
        lo, hi, mean = min(vals), max(vals), statistics.mean(vals)
        svg.text(x_lab, y + 14, f"{pid}  {short[pid]}", 11.5, INK, "end")
        svg.text(x_rng, y + 14, f"{lo}-{hi}", 11, INK2, "middle")
        for j, r in enumerate(cols):
            v = r["counts"][pid]
            out = v - hi if v > hi else (lo - v if v < lo else 0)
            if not large(v, vals):
                fill, text_fill = NEUTRAL, None
            else:
                colored += 1
                step = 0 if out < 5 else 1 if out < 10 else 2 if out < 20 else 3
                fill = (RED_ARM if v > hi else BLUE_ARM)[step]
                text_fill = INK if step == 0 else "#ffffff"
            x = x0 + cw * j
            tip = f"{r['method']} {r['loop']}, {pid}: {v} errors (original runs {lo}-{hi}, mean {mean:.1f}, SD {statistics.stdev(vals):.1f})"
            svg.rect(x + 1, y + 1, cw - 2, rh - 2, fill, tip)
            if text_fill:
                svg.text(x + cw / 2, y + 14.5, str(v), 11, text_fill, "middle", "600")
        y += rh + (8 if pid in gaps_after else 0)
    # legend
    ly = y + 22
    svg.text(20, ly, "Cell: errors per run of that guideline. Colored only for a large move: outside the 19 original runs' range and at least", 11, MUTED)
    ly += 15
    svg.text(20, ly, f"3 SD from their mean (SD taken as at least 1). {colored} of {len(order) * len(cols)} cells; one original run against the other 18 colors {by_chance:.1f} of {len(order)}.", 11, MUTED)
    print(f"  fig6: {colored} colored cells; chance {by_chance:.2f} per column")
    ly += 24
    x = 20
    svg.text(x, ly, "fewer errors, by", 11, INK2)
    x += 96
    for lab, color in zip(("1-4", "5-9", "10-19", "20+"), BLUE_ARM):
        svg.rect(x, ly - 11, 30, 14, color, f"{lab} fewer than the lowest original run")
        svg.text(x + 15, ly + 15, lab, 10, MUTED, "middle")
        x += 32
    x += 14
    svg.rect(x, ly - 11, 30, 14, NEUTRAL, "inside the original range")
    svg.text(x + 15, ly + 15, "inside", 10, MUTED, "middle")
    x += 46
    for lab, color in zip(("1-4", "5-9", "10-19", "20+"), RED_ARM):
        svg.rect(x, ly - 11, 30, 14, color, f"{lab} more than the highest original run")
        svg.text(x + 15, ly + 15, lab, 10, MUTED, "middle")
        x += 32
    svg.text(x + 6, ly, "more errors, by", 11, INK2)
    svg.save("fig6_changed_guidelines.svg")


# ---------------------------------------------------------------- 5. development rounds
def fig_rounds() -> None:
    noise = 0.021
    lo_x, hi_x = -0.13, 0.09
    svg = Svg(780, 250)
    x0, width = 110, 620
    x_of = lambda v: x0 + width * (v - lo_x) / (hi_x - lo_x)
    rows = {True: 70, False: 160}
    top, bottom = 30, 205
    svg.rect(x_of(-noise), top, x_of(noise) - x_of(-noise), bottom - top, NEUTRAL, "noise: one SD of the difference between two development runs, 0.021")
    svg.text(x_of(0), bottom - 8, "+/- 1 SD (0.021)", 10.5, MUTED, "middle")
    ticks(svg, x_of, [-0.12, -0.08, -0.04, 0, 0.04, 0.08], top, bottom, lambda v: f"{v:+.2f}" if v else "0")
    svg.line(x_of(0), top, x_of(0), bottom, AXIS)
    for kept, cy in rows.items():
        n = sum(1 for r in rounds if r["kept"] == kept)
        svg.text(x0 - 12, cy + 4, f"{'kept' if kept else 'rejected'} ({n})", 12.5, INK, "end")
    placed: dict[bool, list[tuple[float, float]]] = {True: [], False: []}
    callout = None
    for r in sorted(rounds, key=lambda r: r["f1_candidate"] - r["f1_before"]):
        d = r["f1_candidate"] - r["f1_before"]
        x = x_of(d)
        level = 0
        while any(abs(px - x) < 9.5 and pl == level for px, pl in placed[r["kept"]]):
            level += 1
        placed[r["kept"]].append((x, level))
        cy = rows[r["kept"]] + (level // 2 + level % 2) * (10 if level % 2 else -10)
        tip = f"{r['method']} loop{r['loop']:02d} round {r['round']}: dev F1 {r['f1_before']:.3f} -> {r['f1_candidate']:.3f} ({d:+.3f}), FP {r['fp'][0]}->{r['fp'][1]}, FN {r['fn'][0]}->{r['fn'][1]}"
        svg.dot(x, cy, BLUE if r["kept"] else ORANGE, tip)
        if r["method"] == "top-4" and r["loop"] == 10 and r["round"] == 1:
            callout = (x, cy)
    if callout:
        x, cy = callout
        tm = links["true_miss_original"]
        svg.line(x - 5, cy - 4, x - 60, top + 2, INK2, 1)
        svg.text(x - 64, top + 6, f"top-4 loop 10, round 1: kept at +0.010 (validation: {links['guidelines']['top-4 loop10']['true_miss']} true misses,"
                 f" original {min(tm)}-{max(tm)})", 11, INK2, "end")
    inside = sum(1 for r in rounds if r["kept"] and r["f1_candidate"] - r["f1_before"] < noise)
    svg.text(x0, bottom + 36, f"Change in development F1 made by each round's rewrite (44 rounds, 20 loops). {inside} of the kept rounds fall within 1 SD.", 11, MUTED)
    svg.save("fig5_dev_rounds.svg")


# ---------------------------------------------------------------- 6. the 9 rejected first rewrites
def fig_first_rewrites() -> None:
    first = [r for r in rounds if r["round"] == 1 and not r["kept"]]
    rows = []
    for r in first:
        target = sum(c - b for b, c in r["targets"].values())
        modifier = sum(c - b for k, (b, c) in r["clusters"].items() if "Modifier" in k and k not in r["targets"])
        rows.append((r, target, modifier))
    svg = Svg(780, 70 + 40 * len(rows) + 40)
    x0, lo_x, hi_x, width = 380, -8, 16, 330
    x_of = lambda v: x0 + width * (v - lo_x) / (hi_x - lo_x) - width * (0 - lo_x) / (hi_x - lo_x)
    zero = x_of(0)
    x = 20
    x = svg.swatch(x, 20, BLUE, "change in the targeted cluster(s)")
    svg.swatch(x, 20, ORANGE, "change in all other errors involving the Modifier label")
    top, bottom = 40, 40 + 40 * len(rows)
    ticks(svg, x_of, [-8, -4, 0, 4, 8, 12, 16], top, bottom, lambda v: f"{v:+d}" if v else "0")
    svg.line(zero, top, zero, bottom, AXIS)
    for i, (r, target, modifier) in enumerate(rows):
        y = top + 40 * i
        d = r["f1_candidate"] - r["f1_before"]
        svg.text(zero - 150, y + 15, f"{r['method']} loop {r['loop']:02d}", 12.5, INK, "end")
        svg.text(zero - 150, y + 29, f"dev F1 {d:+.3f}{' (within 1 SD)' if abs(d) < 0.021 else ''}", 11, MUTED, "end")
        svg.bar(zero, x_of(target), y + 7, 12, BLUE, f"targeted cluster(s): {target:+d} errors")
        svg.bar(zero, x_of(modifier), y + 21, 12, ORANGE, f"other Modifier errors: {modifier:+d}")
        if target < 0:
            svg.text(x_of(target) - 6, y + 17, f"{target:+d}", 11, INK2, "end")
        elif target > 0:
            svg.text(x_of(target) + 6, y + 17, f"{target:+d}", 11, INK2)
        else:
            svg.text(zero - 6, y + 17, "0", 11, INK2, "end")
        svg.text(max(x_of(modifier), zero) + 6, y + 31, f"{modifier:+d}", 11, INK2)
    svg.text(zero - 150 - 120, bottom + 34, "Errors on the 10 development documents (74 mentions), rewrite candidate minus the guideline before it", 11, MUTED)
    svg.save("fig4_rejected_first_rewrites.svg")
    for r, target, modifier in rows:
        print(f"  {r['method']} loop{r['loop']:02d}: target {target:+d}, other Modifier errors {modifier:+d}")


# ---------------------------------------------------------------- 7. two rules most changed guidelines state
def fig_rules() -> None:
    coded, gl = chain["coded"], chain["guidelines"]
    panels = [
        ("history", "What the guideline says about a disease after 'a family history of'",
         "development gold: Specific; training gold: Specific 9, Composite 5, DiseaseClass 3, Modifier 0",
         "validation mentions after 'history of' that the guideline broke",
         lambda g: gl[g]["by_construction"]["after 'history of'"][1], chain["chance_runs"]["history_broken"], (0, 12, 2),
         [("says Modifier", ORANGE, lambda lab: lab == "Modifier"),
          ("says Specific / not Modifier / nothing", BLUE, lambda lab: lab in ("Specific", "not Modifier", "no rule"))]),
        ("symptom_list", "What the guideline says about 'ichthyosis', 'spasticity' in a symptom list",
         "development gold: DiseaseClass for both",
         "symptoms in a list, validation mentions fixed minus broken",
         lambda g: gl[g]["symptom_list"][0] - gl[g]["symptom_list"][1], chain["chance_runs"]["symptom_list_net"], (-14, 12, 4),
         [("says O (not annotated)", ORANGE, lambda lab: lab.startswith("O")),
          ("says DiseaseClass", BLUE, lambda lab: lab == "DiseaseClass"),
          ("other or nothing", MUTED, lambda lab: not lab.startswith("O") and lab != "DiseaseClass")]),
    ]
    # one row per guideline, grouped by what its rule says; no dot labels to collide
    row_h, head_h, panel_gap = 19, 22, 46
    heights = [44 + sum(head_h + row_h * sum(1 for g in coded if t(coded[g][p[0]][0])) for _, _, t in p[7]) + 36 for p in panels]
    svg = Svg(780, sum(heights) + panel_gap + 10)
    x0, width = 330, 400
    y_panel = 18
    for (key, title, sub, axis, value, chance, (lo, hi, step), groups), h in zip(panels, heights):
        assert all(sum(t(coded[g][key][0]) for _, _, t in groups) == 1 for g in coded), key  # every guideline in one group
        x_of = lambda v, lo=lo, hi=hi: x0 + width * (v - lo) / (hi - lo)
        svg.text(20, y_panel, title, 13, INK, "start", "600")
        svg.text(20, y_panel + 16, sub, 11, MUTED)
        top = y_panel + 34
        bottom = top + h - 44 - 36
        svg.rect(x_of(min(chance)) - 4, top, x_of(max(chance)) - x_of(min(chance)) + 8, bottom - top, NEUTRAL,
                 f"19 original-guideline runs, each against the other 18: {min(chance)} to {max(chance)}")
        ticks(svg, x_of, list(range(lo, hi + 1, step)), top, bottom, lambda v: f"{v:+d}" if v and lo < 0 else str(v))
        svg.line(x_of(0), top, x_of(0), bottom, AXIS)
        y = top
        for lab, color, test in groups:
            members = sorted((g for g in coded if test(coded[g][key][0])), key=value)
            svg.add(f'<rect x="20" y="{y + 7:.1f}" width="10" height="10" rx="2" fill="{color}"/>')
            svg.text(36, y + 16, f"{lab} ({len(members)})", 12, INK, "start", "600")
            y += head_h
            for g in members:
                v, line = value(g), coded[g][key][1]
                cy = y + row_h / 2
                svg.text(x0 - 14, cy + 4, f"{g}{f'  (line {line})' if line else ''}", 11.5, INK2, "end")
                svg.dot(x_of(v), cy, color, f"{g}: {v:+d}" + (f"; the rule is at line {line} of its final guideline" if line else "; no such rule"))
                svg.text(x_of(v) + 9, cy + 4, f"{v:+d}" if lo < 0 else str(v), 11, INK2)
                y += row_h
        svg.text(x0, bottom + 30, axis + "; gray band: 19 original runs", 11, MUTED)
        y_panel += h + panel_gap
    svg.save("fig7_rules_and_gold.svg")


for f in (fig_groups, fig_gold, fig_qualifiers, fig_changed, fig_rounds, fig_first_rewrites, fig_rules):
    f()
print("wrote", ", ".join(sorted(p.name for p in FIG.glob("*.svg"))))
