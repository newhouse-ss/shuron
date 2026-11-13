"""Pilot summary for top-4 loop07 (2026-11-05). Offline, no API calls.

Reads outputs/bar_clause_pilot/loop07_instances.csv (build_instances.py). For each cited guideline item (finest resolved
line), sums the per-instance difference d separately for the gold side (gold mentions: d > 0 more right, d < 0 fewer
right) and the false-positive side (no-gold positions newly predicted: d > 0 means more false positives). An instance
citing several items counts under each. Line 65 is split by the model's own rationale wording ("complement" versus
"premodif"/"modifies the"); all 43 members were also read by hand (method note section 4).
Output: outputs/bar_clause_pilot/loop07_pilot_summary_output.txt
"""
import collections
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "outputs" / "bar_clause_pilot"
rows = list(csv.DictReader(open(OUT / "loop07_instances.csv", encoding="utf-8")))
withp = [r for r in rows if r["category"] in ("gold_now_right", "gold_now_wrong_with_prediction", "nogold_new_prediction")]


def tally(sel):
    g = [r for r in sel if r["category"] != "nogold_new_prediction"]
    f = [r for r in sel if r["category"] == "nogold_new_prediction"]
    gp = sum(float(r["d"]) for r in g if float(r["d"]) > 0)
    gn = sum(float(r["d"]) for r in g if float(r["d"]) < 0)
    fp = sum(float(r["d"]) for r in f)
    return (f"gold n{len(g):3d} +{gp:5.2f} {gn:6.2f} docs{len({r['doc'] for r in g}):3d} | "
            f"new no-gold predictions n{len(f):2d} +{fp:4.2f}")


lines = ["A. Per cited item (instances with a prediction in top-4 loop07)"]
items = collections.Counter(i for r in withp for i in r["finest_item"].split(" | ") if i)
for item, _ in items.most_common():
    sel = [r for r in withp if item in r["finest_item"].split(" | ")]
    lines.append(f"   {item:<10} {tally(sel)}")

l65 = [r for r in withp if "L65" in r["finest_item"].split(" | ")]
lines.append("\nB. Line 65 split by the rationale's wording")
for name, test in (("complement of a context noun", lambda t: "complement" in t),
                   ("premodifier of a context/population noun", lambda t: "complement" not in t and ("premodif" in t or "modifies the" in t)),
                   ("neither (cohort reading of the disease noun itself)", lambda t: "complement" not in t and "premodif" not in t and "modifies the" not in t)):
    sel = [r for r in l65 if test(r["raw_rationale"].lower())]
    lines.append(f"   {name:<52} {tally(sel)}  labels(gold): {dict(collections.Counter(r['gold_label'] for r in sel))}")

l69 = [r for r in withp if "L69" in r["finest_item"].split(" | ") and r["category"] != "nogold_new_prediction"]
vhl = [r for r in l69 if r["text"].lower() == "vhl"]
lines.append("\nC. Line 69 gold side: string VHL")
lines.append(f"   VHL {tally(vhl)}; rest {tally([r for r in l69 if r not in vhl])}")

(OUT / "loop07_pilot_summary_output.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
