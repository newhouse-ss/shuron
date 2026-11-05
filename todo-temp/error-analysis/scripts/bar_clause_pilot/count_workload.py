"""Workload count for the bar-to-clause pilot (2026-11-05). Offline, no API, reads only error_rows.csv.

For each of the 11 changed guidelines, every position whose difference from the 19 original runs is non-zero:
  difference = (1 if this run has the outcome there else 0) - (share of the 19 original runs that have it)
Outcome is "gold mention labelled right (strict)" for gold positions and "prediction made" for positions with no gold
(same start, end and type). Positions are split into those where this run has a prediction (the rationale can be
grouped by cited section) and those where it has none (gold mention with no overlapping prediction, or a no-gold
prediction the original made that this run dropped), which need a semantic lookup.
A gold mention is right in a run when error_rows.csv has no row for it in that run.
"""
import collections
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "outputs"
rows = list(csv.DictReader(open(OUT / "error_rows.csv", encoding="utf-8")))
key = lambda r: (r["method"], r["loop"], r["run"])
orig = sorted({key(r) for r in rows if r["guideline"] == "original"})
ref = sorted({key(r) for r in rows if r["guideline"] != "original"})
assert len(orig) == 19 and len(ref) == 11, (len(orig), len(ref))

gstate, gtext = collections.defaultdict(dict), {}
extra = collections.defaultdict(dict)
for r in rows:
    if r["gold_start"]:
        g = (r["doc"], r["gold_start"], r["gold_end"], r["gold_label"])
        gtext[g] = r["gold_text"]
        gstate[key(r)][g] = "missed" if r["kind"] == "missed" else "wrong"
    if r["kind"] == "extra":
        extra[key(r)][(r["doc"], r["pred_start"], r["pred_end"], r["pred_label"])] = r["pred_text"]
orig_extra = {}
for o in orig:
    orig_extra.update(extra[o])


def positions(x):
    """Yield (has_prediction, kind, n_orig_of_19, difference, position, text) for every non-zero position."""
    for g, t in gtext.items():
        n = sum(gstate[o].get(g) is None for o in orig)
        st = gstate[x].get(g)
        d = (1 if st is None else 0) - n / 19
        if abs(d) > 1e-9:
            yield st != "missed", "gold", n, d, g, t
    for e in set(orig_extra) | set(extra[x]):
        n = sum(e in extra[o] for o in orig)
        made = e in extra[x]
        d = (1 if made else 0) - n / 19
        if abs(d) > 1e-9:
            yield made, "no-gold", n, d, e, extra[x].get(e) or orig_extra.get(e)


lines = ["A. Per guideline: positions with a prediction this run | without (all; original >= 10/19; summed difference)"]
for x in ref:
    p = list(positions(x))
    withp = [q for q in p if q[0]]
    nop = [q for q in p if not q[0]]
    big = [q for q in nop if q[2] >= 10]
    lines.append(f"   {x[0]} {x[1]}: {len(withp):4d} | {len(nop):4d} ({sum(q[3] for q in nop):+.1f}); "
                 f">=10/19: {len(big):3d} ({sum(q[3] for q in big):+.1f})")

x = next(k for k in ref if k[:2] == ("top-4", "loop07"))
nop = [q for q in positions(x) if not q[0]]
for kind, title in (("gold", "gold mentions top-4 loop07 left with no overlapping prediction"),
                    ("no-gold", "no-gold predictions the original made that top-4 loop07 dropped")):
    qs = sorted((q for q in nop if q[1] == kind), key=lambda q: (-q[2], q[4]))
    lines.append(f"\nB. {title}: {len(qs)} positions, summed difference {sum(q[3] for q in qs):+.1f}")
    for q in qs:
        lines.append(f"   {q[2]:2d}/19  {q[3]:+.2f}  {q[4][0]}  {q[4][1]}-{q[4][2]}  {q[5]!r}  {q[4][3]}")

(OUT / "bar_clause_pilot").mkdir(exist_ok=True)
(OUT / "bar_clause_pilot" / "count_workload_output.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:13]))
