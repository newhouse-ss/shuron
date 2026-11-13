"""Every validation error of the 30 reproduction runs, by the paper's kinds (Section 3.4.1).

Offline, no API calls. Runs: E1 run01-10 (original guideline), top-1 and top-4 loop01-10 (each loop's
final guideline, annotated once). Each document is classified with reproduction/lib/discrepancy.py:
label mismatch, boundary mismatch, missed (false_negative), extra (false_positive), unpaired overlap.

Writes:
- error_rows.csv: one row per error occurrence (run, document, kind, gold, prediction, context)
- error_items.csv: one row per distinct error (same document, kind, gold span/label, prediction
  span/label), with the number of runs per method that make it
- error_table_output.txt: per-run and per-method counts, check against valid_metrics.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "reproduction"))
from lib.discrepancy import CATEGORIES, Span, classify_document  # noqa: E402

HERE = Path(__file__).resolve().parents[1] / "outputs"
GOLD = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
OUT = ROOT / "outputs" / "ncbi_disease"
ORIGINAL = ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt"
RUNS = (
    [("E1", f"run{i:02d}", f"20261022_haiku-xhigh_e1_run{i:02d}") for i in range(1, 11)]
    + [("top-1", f"loop{i:02d}", f"20261022_haiku-xhigh_topk1_loop{i:02d}") for i in range(1, 11)]
    + [("top-4", f"loop{i:02d}", f"20261022_haiku-xhigh_topk4_loop{i:02d}") for i in range(1, 11)]
)
SHORT = {"label_mismatch": "label", "boundary_mismatch": "boundary", "false_negative": "missed",
         "false_positive": "extra", "unpaired_overlap": "unpaired"}


def norm_hash(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")).hexdigest()[:12]


def spans(doc: dict, text: str) -> list[Span]:
    return [Span(d["span"]["begin"], d["span"]["end"], d["obj"], text[d["span"]["begin"]:d["span"]["end"]])
            for d in doc.get("denotations", [])]


original_hash = norm_hash(ORIGINAL)
docs = sorted(p.name for p in GOLD.glob("*.json"))
gold_docs = {d: json.loads((GOLD / d).read_text(encoding="utf-8")) for d in docs}

rows = []
per_run = {}
lines = []
for method, tag, run in RUNS:
    folder = OUT / run
    final = folder / "final" / "final_guidelines.txt"
    ghash = norm_hash(final) if final.exists() else original_hash
    guideline = "original" if ghash == original_hash else f"changed:{ghash}"
    counts = Counter()
    tp = 0
    for d in docs:
        g = gold_docs[d]
        text = g["text"]
        pred = json.loads((folder / "valid_predictions" / d).read_text(encoding="utf-8"))
        res = classify_document(d, text, spans(g, text), spans(pred, text))
        tp += res.strict_true_positives
        for x in res.discrepancies:
            counts[x.category] += 1
            rows.append({
                "method": method, "loop": tag, "run": run, "guideline": guideline, "doc": d.removesuffix(".json"),
                "kind": SHORT[x.category],
                "gold_text": x.gold.text if x.gold else "", "gold_label": x.gold_label,
                "gold_start": x.gold.start if x.gold else "", "gold_end": x.gold.end if x.gold else "",
                "pred_text": x.pred.text if x.pred else "", "pred_label": x.pred_label,
                "pred_start": x.pred.start if x.pred else "", "pred_end": x.pred.end if x.pred else "",
                "context": x.context.replace("\n", " "),
            })
    # check: strict counts implied by the kinds equal the saved metrics
    saved = json.loads((folder / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    paired = counts["label_mismatch"] + counts["boundary_mismatch"]
    run_rows = [r for r in rows if r["run"] == run]
    fp = paired + counts["false_positive"] + sum(1 for r in run_rows if r["kind"] == "unpaired" and r["pred_text"])
    fn = paired + counts["false_negative"] + sum(1 for r in run_rows if r["kind"] == "unpaired" and r["gold_text"])
    assert (tp, fp, fn) == (saved["true_positives"], saved["false_positives"], saved["false_negatives"]), run
    per_run[run] = (method, tag, guideline, tp, fp, fn, counts)

with (HERE / "error_rows.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# distinct errors
items = defaultdict(lambda: {"E1": 0, "top-1": 0, "top-4": 0, "original": 0, "changed": 0, "runs": []})
first = {}
for r in rows:
    key = (r["doc"], r["kind"], r["gold_start"], r["gold_end"], r["gold_label"], r["pred_start"], r["pred_end"], r["pred_label"])
    it = items[key]
    it[r["method"]] += 1
    it["original" if r["guideline"] == "original" else "changed"] += 1
    it["runs"].append(f"{r['method']}:{r['loop']}")
    first.setdefault(key, r)
n_orig = sum(1 for v in per_run.values() if v[2] == "original")
with (HERE / "error_items.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["item", "doc", "kind", "gold_text", "gold_label", "pred_text", "pred_label", "E1_of10", "top1_of10",
                "top4_of10", f"original_of{n_orig}", f"changed_of{30 - n_orig}", "total_of30", "context", "runs"])
    for i, (key, v) in enumerate(sorted(items.items(), key=lambda kv: (-(kv[1]["E1"] + kv[1]["top-1"] + kv[1]["top-4"]), kv[0][0], str(kv[0][2]), str(kv[0][5]))), 1):
        r = first[key]
        w.writerow([f"I{i:04d}", r["doc"], r["kind"], r["gold_text"], r["gold_label"], r["pred_text"], r["pred_label"],
                    v["E1"], v["top-1"], v["top-4"], v["original"], v["changed"], v["E1"] + v["top-1"] + v["top-4"],
                    r["context"], " ".join(v["runs"])])

out = []
out.append(f"check: strict TP/FP/FN implied by the kinds reproduce valid_metrics.json for all {len(per_run)} runs")
out.append(f"original guideline hash {original_hash}; runs with the original guideline: {n_orig}, with a changed one: {30 - n_orig}")
out.append(f"error occurrences {len(rows)}, distinct errors {len(items)}\n")
kinds = list(CATEGORIES)
out.append("Per run: strict TP FP FN, then error counts by kind")
out.append(f"{'method':<6} {'loop':<6} {'guideline':<21} {'TP':>4} {'FP':>4} {'FN':>4} " + " ".join(f"{SHORT[k]:>9}" for k in kinds))
for run, (method, tag, guideline, tp, fp, fn, c) in per_run.items():
    out.append(f"{method:<6} {tag:<6} {guideline:<21} {tp:>4} {fp:>4} {fn:>4} " + " ".join(f"{c[k]:>9}" for k in kinds))
out.append("\nMean per run (SD) by method")
for method in ("E1", "top-1", "top-4"):
    sel = [v for v in per_run.values() if v[0] == method]
    out.append(f"{method:<6} " + "  ".join(f"{SHORT[k]} {statistics.mean(v[6][k] for v in sel):.1f} ({statistics.stdev(v[6][k] for v in sel):.1f})" for k in kinds))
(HERE / "error_table_output.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
