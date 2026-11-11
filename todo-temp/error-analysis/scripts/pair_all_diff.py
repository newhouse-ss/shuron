"""top-4 loop04 against top-4 loop08 on the whole validation set: on how many gold mentions of each type the two runs
differ, and how many predictions without a gold mention appear in only one run (11/11). Answers whether the 42 gold
Modifiers that only one of the two gets right (pair_vs_original_output.txt section D) are all the differences.

Offline, no API calls. Inputs: validation gold and error_rows.csv. A gold mention is right in a run when the run has no
error row for it; otherwise its outcome is the set of its error rows (kind, predicted label, predicted span), so two
runs that are both wrong differ when they are wrong in different ways.
Run from the repository root. Writes outputs/overall_view/pair_all_diff_output.txt.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
RUN = {"loop04": "20261022_haiku-xhigh_topk4_loop04", "loop08": "20261022_haiku-xhigh_topk4_loop08"}
NAME = {"loop04": "top-4 loop04", "loop08": "top-4 loop08"}
LABELS = ["Modifier", "SpecificDisease", "DiseaseClass", "CompositeMention"]

gold: dict[tuple[str, int, int], str] = {}
for path in sorted(VALID.glob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    for a in doc["denotations"]:
        key = (doc["sourceid"], a["span"]["begin"], a["span"]["end"])
        assert key not in gold, key
        gold[key] = a["obj"]
assert set(gold.values()) == set(LABELS)

outcome: dict[str, dict] = {n: defaultdict(list) for n in RUN}
no_gold: dict[str, set] = {n: set() for n in RUN}
for r in csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")):
    for n, run in RUN.items():
        if r["run"] != run:
            continue
        pred = (r["kind"], r["pred_label"], r["pred_start"], r["pred_end"])
        if r["gold_start"]:
            g = (r["doc"], int(r["gold_start"]), int(r["gold_end"]))
            assert gold[g] == r["gold_label"], (g, r["gold_label"])
            outcome[n][g].append(pred)
        else:
            no_gold[n].add((r["doc"], r["pred_start"], r["pred_end"], r["pred_label"], r["kind"]))


def state(n, g):
    return tuple(sorted(outcome[n][g])) if g in outcome[n] else None


table = {lab: Counter() for lab in LABELS}
for g, lab in gold.items():
    s4, s8 = state("loop04", g), state("loop08", g)
    if s4 is None and s8 is None:
        table[lab]["both right"] += 1
    elif s4 is None:
        table[lab]["only loop04 right"] += 1
    elif s8 is None:
        table[lab]["only loop08 right"] += 1
    elif s4 == s8:
        table[lab]["both wrong, same way"] += 1
    else:
        table[lab]["both wrong, different ways"] += 1
assert table["Modifier"]["only loop08 right"] == 33 and table["Modifier"]["only loop04 right"] == 9

out: list[str] = []
w = out.append
w("top-4 loop04 与 top-4 loop08 在整个验证集上的全部差别（2026-11-11，离线）")
w("")
w("A. gold 提及：两份结果相同还是不同。都错时，错法（错误类型、标成的类型、标出的范围）不同也算不同")
cols = ["both right", "only loop08 right", "only loop04 right", "both wrong, different ways", "both wrong, same way"]
head = ["都标对", "只有 top-4 loop08 标对", "只有 top-4 loop04 标对", "都错但错法不同", "都错且错法相同"]
w("  gold 类型 | 提及数 | " + " | ".join(head) + " | 结果不同合计")
tot = Counter()
for lab in LABELS:
    c = table[lab]
    differ = c["only loop08 right"] + c["only loop04 right"] + c["both wrong, different ways"]
    tot.update(c)
    tot["differ"] += differ
    w(f"  {lab} | {sum(c[k] for k in cols)} | " + " | ".join(str(c[k]) for k in cols) + f" | {differ}")
w(f"  合计 | {sum(tot[k] for k in cols)} | " + " | ".join(str(tot[k]) for k in cols) + f" | {tot['differ']}")
mod = table["Modifier"]
in_table = mod["only loop08 right"] + mod["only loop04 right"]
w(f"  条文对应表里的是 gold Modifier 只有一份标对的 {in_table} 个；结果不同的 gold 提及在表外还有 {tot['differ'] - in_table} 个")
w(f"  gold 不是 Modifier 的提及：只有 top-4 loop08 标对 {tot['only loop08 right'] - mod['only loop08 right']} 个，"
  f"只有 top-4 loop04 标对 {tot['only loop04 right'] - mod['only loop04 right']} 个")
w("")
w("B. 不对应任何 gold 提及的预测（多标，按标成的类型）：只在一份里出现的个数")
shared = no_gold["loop04"] & no_gold["loop08"]
for n in RUN:
    only = no_gold[n] - shared
    by = Counter(x[3] for x in only)
    w(f"  只在 {NAME[n]} 里：{len(only)} 个（" + "，".join(f"{lab} {by[lab]}" for lab in LABELS if by[lab]) + "）")
w(f"  两份都有：{len(shared)} 个")
w("")
w("PASS：gold Modifier 只有 top-4 loop08 标对 33 个、只有 top-4 loop04 标对 9 个，与 pair_vs_original_output.txt D 节一致。")

dest = HERE / "overall_view" / "pair_all_diff_output.txt"
with dest.open("w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
