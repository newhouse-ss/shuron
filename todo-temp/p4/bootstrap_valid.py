"""P4: paired bootstrap CIs for valid100 F1 differences between guideline arms.

All five arms annotated the same 100 valid documents, so per-document TP/FP/FN
triplets allow a paired bootstrap: resample documents with replacement, recompute
micro F1 per arm, and take the difference. This puts a confidence interval on the
single-point comparisons used in P3/P4 (dev30 vs dev10, top-4 vs dev10, ...).

    python todo-temp/p4/bootstrap_valid.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "reproduction" / "results"

ARMS = {
    "original": "ncbi-g-gpt54",
    "dev10": "ncbi-m-gpt54",
    "dev20": "ncbi-m-dev20",
    "dev30": "ncbi-m-dev30",
    "topk4": "ncbi-valid-topk4-gpt54",
}

PAIRS = [
    ("dev10", "original"),
    ("dev20", "original"),
    ("dev30", "original"),
    ("topk4", "original"),
    ("dev30", "dev10"),
    ("dev30", "dev20"),
    ("dev20", "dev10"),
    ("topk4", "dev10"),
    ("topk4", "dev30"),
]

N_BOOT = 10000
SEED = 42


def micro_f1(docs):
    tp = sum(d["strict_true_positives"] for d in docs)
    fp = sum(d["pred_total"] - d["strict_true_positives"] for d in docs)
    fn = sum(d["gold_total"] - d["strict_true_positives"] for d in docs)
    return 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0


def main() -> None:
    per_arm = {}
    for arm, label in ARMS.items():
        rows = json.loads((RESULTS / label / "per_document.json").read_text(encoding="utf-8"))
        per_arm[arm] = {r["doc_id"]: r for r in rows}
    doc_ids = sorted(set.intersection(*(set(v) for v in per_arm.values())))
    assert len(doc_ids) == 100, f"expected 100 shared docs, got {len(doc_ids)}"

    rng = random.Random(SEED)
    out = {"n_boot": N_BOOT, "seed": SEED, "arms": {}, "pairs": []}
    for arm in ARMS:
        docs = [per_arm[arm][d] for d in doc_ids]
        out["arms"][arm] = round(micro_f1(docs), 4)

    print(f"{'pair':<18}{'point diff':>12}{'95% CI':>22}{'P(diff>0)':>11}")
    for a, b in PAIRS:
        diffs = []
        for _ in range(N_BOOT):
            sample = [doc_ids[rng.randrange(100)] for _ in range(100)]
            fa = micro_f1([per_arm[a][d] for d in sample])
            fb = micro_f1([per_arm[b][d] for d in sample])
            diffs.append(fa - fb)
        diffs.sort()
        lo, hi = diffs[int(0.025 * N_BOOT)], diffs[int(0.975 * N_BOOT)]
        point = out["arms"][a] - out["arms"][b]
        frac_pos = sum(1 for d in diffs if d > 0) / N_BOOT
        out["pairs"].append({"pair": f"{a} - {b}", "point": round(point, 4),
                             "ci95": [round(lo, 4), round(hi, 4)],
                             "frac_positive": round(frac_pos, 4)})
        print(f"{a + ' - ' + b:<18}{point:>12.4f}[{lo:>8.4f},{hi:>8.4f} ]{frac_pos:>11.1%}")

    (Path(__file__).parent / "bootstrap_valid.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nwritten to todo-temp/p4/bootstrap_valid.json")


if __name__ == "__main__":
    main()
