"""Count per-instance differences per guideline item (step 2g). Offline, no API calls. 2026-11-06.

Joins, for each changed guideline: the instance table (<prefix>_instances.csv: per-instance difference d against the 19
original-guideline runs), the locate records (basis quotes per prediction), the merge-step entry map and items. Rules agreed
with the user on 2026-11-06:
- only quotes with role "basis" attribute an instance to an item ("ruled_out" and "context" are not counted);
- an instance relying on several items is counted under each, so item rows overlap and do not add up; every instance is
  counted once in the guideline totals, and instances relying on two or more items are also listed by item set;
- each item is reported as a whole, per branch (the condition named in the rationale) and as "branch not stated";
- gains (d > 0 on gold) and losses (d < 0 on gold) are kept apart; no-gold positions predicted this run (new false
  positives) are reported separately; positions with no prediction in this run have no rationale and form their own bucket.
Check: per guideline, the sum of d over gold instances of each label equals the slide-5 bar (bar_attribution.json).
Outputs: outputs/bar_clause_pilot/codex_locate/aggregate/<prefix>_items.csv, <prefix>_joint.csv, aggregate_output.txt.
"""
import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PILOT = ROOT / "todo-temp" / "error-analysis" / "outputs" / "bar_clause_pilot"
BASE = PILOT / "codex_locate"
OUT = BASE / "aggregate"
PREFIXES = ["top4_loop01", "top4_loop02", "top4_loop04", "top4_loop05", "top4_loop06", "top4_loop07", "top4_loop08",
            "top4_loop09", "top4_loop10", "top1_loop05", "top1_loop07"]
BAR_NAME = {p: p.replace("top4_", "top-4 ").replace("top1_", "top-1 ") for p in PREFIXES}
GOLD = {"gold_now_right", "gold_now_wrong_with_prediction"}


def jl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def new_acc():
    return {"n": 0, "gain": 0.0, "loss": 0.0, "fp_n": 0, "fp_d": 0.0, "docs": set(), "strings": set()}


def add(acc, r, d):
    acc["n"] += 1
    acc["docs"].add(r["doc"])
    acc["strings"].add(r["text"].strip().lower())
    if r["category"] == "nogold_new_prediction":
        acc["fp_n"] += 1
        acc["fp_d"] += d
    elif d > 0:
        acc["gain"] += d
    else:
        acc["loss"] += d


def fmt(acc):
    return (f"n {acc['n']:3d} | gold +{acc['gain']:5.2f} {acc['loss']:6.2f} | new FP {acc['fp_n']:2d} ({acc['fp_d']:+.2f})"
            f" | docs {len(acc['docs']):2d} strings {len(acc['strings']):2d}")


def main():
    OUT.mkdir(exist_ok=True)
    bars = json.loads((ROOT / "todo-temp" / "error-analysis" / "outputs" / "bar_attribution.json").read_text(encoding="utf-8"))["bars"]
    report = []
    for prefix in PREFIXES:
        inst = list(csv.DictReader(open(PILOT / f"{prefix}_instances.csv", encoding="utf-8")))
        loc = {r["pred_id"]: r for f in (f"{prefix}_locate.jsonl", f"{prefix}_locate_haiku.jsonl")
               for r in jl(BASE / "outputs" / f)}
        entries = {(e["line_start"], e["line_end"], e["quote"], e["condition_words"]): e["entry_id"]
                   for e in jl(BASE / "merge_inputs" / f"{prefix}_basis_entries.jsonl")}
        emap = {m["entry_id"]: m for m in json.loads((BASE / "merge_outputs" / f"{prefix}_entry_map.json").read_text(encoding="utf-8"))}
        items = {i["item_id"]: i for i in json.loads((BASE / "merge_outputs" / f"{prefix}_items.json").read_text(encoding="utf-8"))}
        per_item = collections.defaultdict(new_acc)
        per_branch = collections.defaultdict(new_acc)
        joint = collections.defaultdict(new_acc)
        buckets = collections.defaultdict(new_acc)
        totals = collections.Counter()
        unmatched = 0
        for r in inst:
            d = float(r["d"])
            if r["category"] in GOLD or r["category"] == "gold_now_unlabelled":
                totals[r["gold_label"]] += d
            if not r["target_pred_label"]:
                add(buckets[f"no prediction: {r['category']}"], r, d)
                continue
            pid = f"{prefix}|{r['doc']}|{r['target_pred_start']}|{r['target_pred_end']}|{r['target_pred_label']}"
            rec = loc.get(pid)
            if rec is None:
                unmatched += 1
                continue
            hits = set()
            for q in rec["quotes"]:
                if q["role"] != "basis":
                    continue
                eid = entries[(q["line_start"], q["line_end"], q["quote"], q["condition_words"])]
                hits.add((emap[eid]["item_id"], emap[eid]["branch"]))
            if not hits:
                add(buckets["located, no basis quote"], r, d)
                continue
            its = sorted({i for i, _ in hits})
            for i in its:
                add(per_item[i], r, d)
            for i, b in hits:
                add(per_branch[(i, b)], r, d)
            if len(its) > 1:
                add(joint[tuple(its)], r, d)
        # write item table
        with open(OUT / f"{prefix}_items.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["item_id", "level", "branch", "lines", "action_type", "label", "parent_item", "n", "gold_gain",
                        "gold_loss", "new_fp_n", "new_fp_d", "documents", "strings", "item_text"])
            for i, acc in sorted(per_item.items(), key=lambda kv: -(kv[1]["gain"] - kv[1]["loss"])):
                it = items[i]
                row = [i, "item", "", f"{it['line_start']}-{it['line_end']}", it["action_type"], it["label"], it["parent_item"]]
                w.writerow(row + [acc["n"], round(acc["gain"], 4), round(acc["loss"], 4), acc["fp_n"], round(acc["fp_d"], 4),
                                  len(acc["docs"]), len(acc["strings"]), it["item_text"]])
                for (j, b), bacc in sorted(per_branch.items(), key=lambda kv: kv[0][1]):
                    if j == i and (len([k for k in per_branch if k[0] == i]) > 1 or b):
                        w.writerow([i, "branch", b or "(branch not stated)", "", "", "", "", bacc["n"], round(bacc["gain"], 4),
                                    round(bacc["loss"], 4), bacc["fp_n"], round(bacc["fp_d"], 4), len(bacc["docs"]),
                                    len(bacc["strings"]), ""])
        with open(OUT / f"{prefix}_joint.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["item_set", "n", "gold_gain", "gold_loss", "new_fp_n", "new_fp_d", "documents"])
            for k, acc in sorted(joint.items(), key=lambda kv: -kv[1]["n"]):
                w.writerow([" + ".join(k), acc["n"], round(acc["gain"], 4), round(acc["loss"], 4), acc["fp_n"],
                            round(acc["fp_d"], 4), len(acc["docs"])])
        # report
        report.append(f"=== {prefix}")
        name = BAR_NAME[prefix]
        for lab in ("SpecificDisease", "DiseaseClass", "Modifier"):
            ok = abs(totals[lab] - bars[lab][name]) < 0.05
            report.append(f"   check {lab:<16} sum d {totals[lab]:+8.2f} bar {bars[lab][name]:+8.2f} {'ok' if ok else 'MISMATCH'}")
        report.append(f"   instances with a prediction not found in locate output: {unmatched}")
        for k, acc in sorted(buckets.items()):
            report.append(f"   bucket {k:<45} {fmt(acc)}")
        report.append(f"   instances relying on two or more items: {sum(a['n'] for a in joint.values())}")
        for i, acc in sorted(per_item.items(), key=lambda kv: -(kv[1]["gain"] - kv[1]["loss"]))[:12]:
            it = items[i]
            report.append(f"   {i} L{it['line_start']}-{it['line_end']} {it['action_type']:<13} {it['label'][:14]:<14} {fmt(acc)}"
                          f" | {it['item_text'][:70]!r}")
    (OUT / "aggregate_output.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
