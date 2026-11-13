"""How much noisier is a 50-document test set than a 100-document one?

Offline, no API calls. Uses the 30 saved validation runs of the 10/23 reproduction
(E1 runs 01-10, top-1 and top-4 loops 01-10). For many random halves of the 100
validation documents it rescores every run on the half (strict exact span and
subtype matching, micro F1) and reports, per group, the SD of F1 across the 10 runs,
averaged over halves, next to the same SD on all 100 documents. It also reports the
Welch t-test's detectable gap in units that matter here: the 95% CI half-width of
the top-4 minus E1 difference.

Per-document counts are checked against each run's valid_metrics.json first.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GOLD = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
OUT = ROOT / "outputs" / "ncbi_disease"
GROUPS = {
    "E1": [f"20261022_haiku-xhigh_e1_run{i:02d}" for i in range(1, 11)],
    "top-1": [f"20261022_haiku-xhigh_topk1_loop{i:02d}" for i in range(1, 11)],
    "top-4": [f"20261022_haiku-xhigh_topk4_loop{i:02d}" for i in range(1, 11)],
}
DRAWS = 2000
SEED = 20261024


def keys(path: Path) -> set[tuple[int, int, str]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {(d["span"]["begin"], d["span"]["end"], d["obj"]) for d in doc.get("denotations", [])}


def f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


docs = sorted(p.name for p in GOLD.glob("*.json"))
gold = {d: keys(GOLD / d) for d in docs}
counts: dict[str, dict[str, tuple[int, int, int]]] = {}
for runs in GROUPS.values():
    for run in runs:
        per = {}
        for d in docs:
            pred = keys(OUT / run / "valid_predictions" / d)
            per[d] = (len(gold[d] & pred), len(pred - gold[d]), len(gold[d] - pred))
        tp, fp, fn = (sum(v[i] for v in per.values()) for i in range(3))
        saved = json.loads((OUT / run / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
        assert (tp, fp, fn) == (saved["true_positives"], saved["false_positives"], saved["false_negatives"]), run
        counts[run] = per
print(f"check: per-document counts reproduce valid_metrics.json for all {len(counts)} runs")


def run_f1(run: str, subset: list[str]) -> float:
    per = counts[run]
    return f1(*(sum(per[d][i] for d in subset) for i in range(3)))


def welch_half_width(a: list[float], b: list[float]) -> float:
    # 95% CI half-width of mean(b) - mean(a); t quantile for the Welch df, from a small table
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    table = {9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
             16: 2.120, 17: 2.110, 18: 2.101}
    t = table[max(9, min(18, round(df)))]
    return t * (va + vb) ** 0.5


print(f"\nSD of F1 across the 10 runs of each group ({DRAWS} random halves, seed {SEED})")
print(f"{'group':<7} {'100 docs':>9} {'50 docs, mean':>14} {'50 docs, 5-95%':>16}")
rng = random.Random(SEED)
halves = [rng.sample(docs, 50) for _ in range(DRAWS)]
for name, runs in GROUPS.items():
    full = statistics.stdev(run_f1(r, docs) for r in runs)
    sds = sorted(statistics.stdev(run_f1(r, h) for r in runs) for h in halves)
    print(f"{name:<7} {full:9.4f} {statistics.mean(sds):14.4f} {sds[len(sds) // 20]:7.4f}-{sds[-len(sds) // 20]:.4f}")

print("\n95% CI half-width of the top-4 minus E1 difference (Welch)")
full = welch_half_width([run_f1(r, docs) for r in GROUPS["E1"]], [run_f1(r, docs) for r in GROUPS["top-4"]])
hw = [welch_half_width([run_f1(r, h) for r in GROUPS["E1"]], [run_f1(r, h) for r in GROUPS["top-4"]]) for h in halves]
print(f"100 docs: {full:.4f}   50 docs, mean over halves: {statistics.mean(hw):.4f}")
