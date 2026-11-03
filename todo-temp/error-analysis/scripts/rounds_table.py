"""Every refinement round of the 20 loops, on the 10 development documents.

Offline, no API calls. Reads rounds/iteration_NN/snapshot.json of top-1 and top-4 loop01-10. For each
round: kept or rejected, development F1 / FP / FN before and with the candidate guideline, guideline
length, the cluster(s) the round targeted, and how each error cluster changed. The development F1 of
one run varies with SD 0.015 (Haiku trial, 20 runs of the original guideline), so the difference
between two runs varies with SD about 0.021. Writes rounds_table_output.txt.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
NOISE = 0.021

out = []
kept_gains = []
records = []
for method, k in (("top-1", "topk1"), ("top-4", "topk4")):
    for i in range(1, 11):
        folder = OUT / f"20261022_haiku-xhigh_{k}_loop{i:02d}" / "rounds"
        for snap in sorted(folder.glob("iteration_*/snapshot.json")):
            s = json.loads(snap.read_text(encoding="utf-8"))
            b, c = s["summary_before"], s["summary_candidate"]
            d = c["overall_f1"] - b["overall_f1"]
            if s["improved"]:
                kept_gains.append(d)
            before = {x["key"]: x["count"] for x in b["all_clusters"]}
            cand = {x["key"]: x["count"] for x in c["all_clusters"]}
            targets = [x["key"] for x in b["all_clusters"][: (1 if k == "topk1" else 4)]]
            records.append({"method": method, "loop": i, "round": s["iteration"], "kept": s["improved"],
                            "f1_before": b["overall_f1"], "f1_candidate": c["overall_f1"],
                            "fp": [b["false_positives"], c["false_positives"]], "fn": [b["false_negatives"], c["false_negatives"]],
                            "targets": {t: [before.get(t, 0), cand.get(t, 0)] for t in targets},
                            "clusters": {x: [before.get(x, 0), cand.get(x, 0)] for x in sorted(set(before) | set(cand))}})
            out.append(f"{method} loop{i:02d} round {s['iteration']}: {'kept' if s['improved'] else 'rejected'}  "
                       f"dev F1 {b['overall_f1']:.3f} -> {c['overall_f1']:.3f} ({d:+.3f}{', within 1 SD' if abs(d) < NOISE else ''})  "
                       f"FP {b['false_positives']} -> {c['false_positives']}  FN {b['false_negatives']} -> {c['false_negatives']}  "
                       f"guideline {len(s['guidelines_before']):,} -> {len(s['guidelines_candidate']):,} chars")
            for t in targets:
                out.append(f"    target: {t} ({before.get(t, 0)} -> {cand.get(t, 0)})")
            moved = sorted(((cand.get(x, 0) - before.get(x, 0), x) for x in set(before) | set(cand)), reverse=True)
            ups = [f"{x} +{v}" for v, x in moved if v > 0]
            downs = [f"{x} {v}" for v, x in moved if v < 0]
            out.append(f"    rose: {'; '.join(ups) or '-'}")
            out.append(f"    fell: {'; '.join(downs) or '-'}")
out.append("")
inside = sum(1 for g in kept_gains if g < NOISE)
out.append(f"kept rounds: {len(kept_gains)}; dev F1 gain below {NOISE} (one SD of the difference between two runs): {inside}")


def modifier_errors(r: dict, i: int) -> int:
    return sum(v[i] for k, v in r["clusters"].items() if "Modifier" in k)


for kept in (True, False):
    rose = [r for r in records if r["kept"] == kept and modifier_errors(r, 1) > modifier_errors(r, 0)]
    out.append(f"{'kept' if kept else 'rejected'} rounds in which errors involving the Modifier label rose on dev: "
               f"{len(rose)} of {sum(1 for r in records if r['kept'] == kept)}")

# dev mentions that a rejected first rewrite newly labeled Modifier (gold another label)
out.append("\nFirst rounds that were rejected: development mentions newly labeled Modifier (gold another label)")
newmod = Counter()
first_rejected = [r for r in records if r["round"] == 1 and not r["kept"]]
for r in first_rejected:
    k = "topk1" if r["method"] == "top-1" else "topk4"
    s = json.loads((OUT / f"20261022_haiku-xhigh_{k}_loop{r['loop']:02d}" / "rounds" / "iteration_01" / "snapshot.json").read_text(encoding="utf-8"))
    items = []
    for fb, fc in zip(s["diagnostics_before"]["files"], s["diagnostics_candidate"]["files"]):
        gold = {(d["start"], d["end"]): d["label"] for d in fc["reference_denotations"]}
        before = {(d["start"], d["end"]): d["label"] for d in fb["study_denotations"]}
        text = json.loads((TRAIN / fc["filename"]).read_text(encoding="utf-8"))["text"]
        for d in fc["study_denotations"]:
            span = (d["start"], d["end"])
            if d["label"] == "Modifier" and gold.get(span, "Modifier") != "Modifier" and before.get(span) != "Modifier":
                items.append(d["text"] + (" (after 'history of')" if "history of" in text[max(0, d["start"] - 25):d["start"]] else ""))
    newmod.update(items)
    out.append(f"   {r['method']} loop{r['loop']:02d}: {len(items)}: {', '.join(sorted(items)) or '-'}")
tsd = newmod["Tay-Sachs disease"] + newmod["TSD"]
hist = sum(v for k, v in newmod.items() if "history of" in k)
out.append(f"   total {sum(newmod.values())}: Tay-Sachs disease or TSD {tsd}, after 'history of' {hist}")

# baseline noise and the keep decision
r1 = [r for r in records if r["round"] == 1]
base = [r["f1_before"] for r in r1]
gain = [r["f1_candidate"] - r["f1_before"] for r in r1]
out.append(f"\nround 1 of the 20 loops: Pearson r between the baseline dev F1 and the round-1 gain {statistics.correlation(base, gain):+.2f}")
out.append(f"   mean baseline dev F1: loops whose round 1 was rejected {statistics.mean(r['f1_before'] for r in r1 if not r['kept']):.3f}, "
           f"kept {statistics.mean(r['f1_before'] for r in r1 if r['kept']):.3f}")


def ranks(xs: list) -> list:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k2 in range(i, j + 1):
            rk[order[k2]] = (i + j) / 2
        i = j + 1
    return rk


ends, starts, vals = [], [], []
for method, k in (("top-1", "topk1"), ("top-4", "topk4")):
    for i in range(1, 11):
        rs = [r for r in records if r["method"] == method and r["loop"] == i]
        if not any(r["kept"] for r in rs):
            continue
        ends.append(max(r["f1_candidate"] for r in rs if r["kept"]))
        starts.append(rs[0]["f1_before"])
        m = json.loads((OUT / f"20261022_haiku-xhigh_{k}_loop{i:02d}" / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
        vals.append(m["f1"])
out.append(f"changed loops ({len(vals)}): Spearman between final dev F1 and validation F1 {statistics.correlation(ranks(ends), ranks(vals)):+.2f}; "
           f"between dev gain and validation F1 {statistics.correlation(ranks([e - s for e, s in zip(ends, starts)]), ranks(vals)):+.2f}")
# Could run-to-run noise alone give a change this large? Two development runs of an unchanged guideline differ with
# SD NOISE (normal approximation). For a drop d: chance of a drop at least that large; for a gain g: of a gain at
# least that large.
nd = statistics.NormalDist(0, NOISE)
out.append(f"\nchance that two runs of an unchanged guideline differ this much in the same direction (normal, SD {NOISE})")
out.append("   rejected first rewrites:")
for r in first_rejected:
    d = r["f1_candidate"] - r["f1_before"]
    out.append(f"      {r['method']} loop{r['loop']:02d}: {d:+.3f}, chance {nd.cdf(d):.1%}")
small = sum(1 for r in first_rejected if nd.cdf(r["f1_candidate"] - r["f1_before"]) < 0.05)
out.append(f"   drops with chance below 5%: {small} of {len(first_rejected)}; below 5% / {len(first_rejected)} (Bonferroni): "
           f"{sum(1 for r in first_rejected if nd.cdf(r['f1_candidate'] - r['f1_before']) < 0.05 / len(first_rejected))}")
kept_rounds = [r for r in records if r["kept"]]
gains = [r["f1_candidate"] - r["f1_before"] for r in kept_rounds]
out.append(f"   kept rounds with a gain whose chance is above 5% (could be noise alone): "
           f"{sum(1 for g in gains if 1 - nd.cdf(g) >= 0.05)} of {len(gains)}")
for r, g in zip(kept_rounds, gains):
    if r["method"] == "top-4" and r["loop"] == 10 and r["round"] == 1:
        out.append(f"   top-4 loop10 round 1 (kept): {g:+.3f}, chance {1 - nd.cdf(g):.1%}")
(HERE / "rounds.json").write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8")
(HERE / "rounds_table_output.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
