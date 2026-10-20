"""Offline error breakdown of saved valid100 runs (no API calls).

Question: which kinds of error make up the gap between current validation F1 and the target,
and how much F1 would each kind be worth if it were fixed (gold standing in for an expert)?

Inputs (all saved earlier):
    data/datasets/ncbi_disease/valid/*.json                 gold, PubAnnotation
    outputs/ncbi_disease/<run>/*.json or outputs/<run>/      predictions, PubAnnotation
    reproduction/results/<label>/discrepancies.json          categories from reproduction/lib/discrepancy.py
    reproduction/results/<label>/metrics.json                strict scores

Outputs: error_breakdown.json and error_breakdown_output.txt next to this script.

    python todo-temp/meeting-20261020/error_breakdown.py
"""
import json
import string
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GOLD_DIR = ROOT / "data/datasets/ncbi_disease/valid"
RUNS = [
    ("original guideline", "ncbi-g-gpt54", "outputs/ncbi_disease/20260802_gpt54-high_valid-G"),
    ("top-1 refined (R4)", "ncbi-m-gpt54", "outputs/ncbi_disease/20260802_gpt54-high_valid-M"),
    ("top-4 refined", "ncbi-valid-topk4-gpt54", "outputs/20261007_ncbi_gpt54-high_valid-topk4"),
    ("top-1 refined, dev30", "ncbi-m-dev30", "outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev30"),
]
TYPES = ["SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention"]
TRIM = string.whitespace + string.punctuation


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
            "tp": tp, "fp": fp, "fn": fn}


def spans(doc, trim=False, typed=True):
    text = doc["text"]
    out = Counter()
    for d in doc["denotations"]:
        b, e = d["span"]["begin"], d["span"]["end"]
        if trim:
            while b < e and text[b] in TRIM:
                b += 1
            while e > b and text[e - 1] in TRIM:
                e -= 1
        out[(b, e, d["obj"]) if typed else (b, e)] += 1
    return out


def match_counts(pred_dir, trim, typed):
    tp = fp = fn = 0
    for gold_path in sorted(GOLD_DIR.glob("*.json")):
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        pred = json.loads((pred_dir / gold_path.name).read_text(encoding="utf-8"))
        g, p = spans(gold, trim, typed), spans(pred, trim, typed)
        common = sum((g & p).values())
        tp += common
        fp += sum(p.values()) - common
        fn += sum(g.values()) - common
    return tp, fp, fn


def trims_equal(item):
    g, p = item["gold"]["text"], item["pred"]["text"]
    return g.strip(TRIM) == p.strip(TRIM)


def analyse(name, label, pred_rel):
    metrics = json.loads((ROOT / "reproduction/results" / label / "metrics.json").read_text(encoding="utf-8"))
    disc = json.loads((ROOT / "reproduction/results" / label / "discrepancies.json").read_text(encoding="utf-8"))
    pred_dir = ROOT / pred_rel
    strict = match_counts(pred_dir, trim=False, typed=True)
    saved = metrics["strict_match"]["pubannotation"]
    assert strict == (saved["true_positives"], saved["false_positives"], saved["false_negatives"]), (name, strict)
    tp, fp, fn = strict

    cat = Counter(d["category"] for d in disc)
    label_pairs = Counter((d["gold_label"], d["pred_label"]) for d in disc if d["category"] == "label_mismatch")
    label_same_span = sum(1 for d in disc if d["category"] == "label_mismatch"
                          and (d["gold"]["start"], d["gold"]["end"]) == (d["pred"]["start"], d["pred"]["end"]))
    boundary = [d for d in disc if d["category"] == "boundary_mismatch"]
    boundary_by_type = Counter(d["gold_label"] for d in boundary)
    boundary_trim_only = sum(1 for d in boundary if trims_equal(d))
    fn_by_type = Counter(d["gold_label"] for d in disc if d["category"] == "false_negative")
    fp_by_type = Counter(d["pred_label"] for d in disc if d["category"] == "false_positive")
    unpaired_gold = sum(1 for d in disc if d["category"] == "unpaired_overlap" and d["gold"])
    unpaired_pred = sum(1 for d in disc if d["category"] == "unpaired_overlap" and d["pred"])
    assert fp == cat["label_mismatch"] + cat["boundary_mismatch"] + cat["false_positive"] + unpaired_pred, name
    assert fn == cat["label_mismatch"] + cat["boundary_mismatch"] + cat["false_negative"] + unpaired_gold, name

    # Oracle fixes: gold replaces the model's answer for one kind of error, everything else unchanged.
    lm, bm = cat["label_mismatch"], cat["boundary_mismatch"]
    oracle = {
        "label mismatch fixed": prf(tp + lm, fp - lm, fn - lm),
        "boundary mismatch fixed": prf(tp + bm, fp - bm, fn - bm),
        "missed entities added": prf(tp + cat["false_negative"], fp, fn - cat["false_negative"]),
        "spurious entities removed": prf(tp, fp - cat["false_positive"], fn),
        # An expert who checks every predicted entity can fix its label or boundary or delete it,
        # but finds nothing the model never proposed.
        "expert checks every predicted entity": prf(tp + lm + bm, 0, fn - lm - bm),
    }
    for t in TYPES:
        k = sum(v for (g, _), v in label_pairs.items() if g == t)
        oracle[f"label mismatch fixed, gold {t} only"] = prf(tp + k, fp - k, fn - k)
        m = fn_by_type[t]
        oracle[f"missed {t} added"] = prf(tp + m, fp, fn - m)

    total_disc = len(disc)
    return {
        "run": name, "label": label, "pred_dir": pred_rel,
        "strict": prf(*strict),
        "strict_trimmed_spans": prf(*match_counts(pred_dir, trim=True, typed=True)),
        "span_only": prf(*match_counts(pred_dir, trim=False, typed=False)),
        "span_only_trimmed": prf(*match_counts(pred_dir, trim=True, typed=False)),
        "categories": dict(cat), "discrepancies_total": total_disc,
        "label_mismatch_pairs": {f"{g}->{p}": v for (g, p), v in label_pairs.most_common()},
        "label_mismatch_same_span": label_same_span,
        "boundary_by_gold_type": dict(boundary_by_type),
        "boundary_whitespace_or_punctuation_only": boundary_trim_only,
        "missed_by_gold_type": dict(fn_by_type),
        "spurious_by_pred_type": dict(fp_by_type),
        "unpaired_gold": unpaired_gold, "unpaired_pred": unpaired_pred,
        "missed_modifier_share_of_discrepancies": round(fn_by_type["Modifier"] / total_disc, 4),
        "oracle": oracle,
        "predicted_entities": tp + fp,
    }


def main():
    results = [analyse(*r) for r in RUNS]
    (HERE / "error_breakdown.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    lines = []
    for r in results:
        s = r["strict"]
        lines.append(f"== {r['run']} ({r['label']})")
        lines.append(f"strict F1 {s['f1']}  P {s['precision']}  R {s['recall']}  TP {s['tp']} FP {s['fp']} FN {s['fn']}")
        for key in ("strict_trimmed_spans", "span_only", "span_only_trimmed"):
            lines.append(f"{key:22s} F1 {r[key]['f1']}  (TP {r[key]['tp']} FP {r[key]['fp']} FN {r[key]['fn']})")
        lines.append(f"discrepancies {r['discrepancies_total']}: {r['categories']}")
        lines.append(f"label mismatch pairs (gold->pred): {r['label_mismatch_pairs']}  same span: {r['label_mismatch_same_span']}")
        lines.append(f"boundary by gold type: {r['boundary_by_gold_type']}  whitespace/punctuation only: {r['boundary_whitespace_or_punctuation_only']}")
        lines.append(f"missed by gold type: {r['missed_by_gold_type']}  (missed Modifier = {r['missed_modifier_share_of_discrepancies']:.1%} of discrepancies)")
        lines.append(f"spurious by predicted type: {r['spurious_by_pred_type']}  unpaired gold {r['unpaired_gold']} pred {r['unpaired_pred']}")
        lines.append("F1 if one kind of error were fixed by gold:")
        for k, v in r["oracle"].items():
            lines.append(f"  {k:48s} F1 {v['f1']:.4f}  (+{v['f1'] - s['f1']:.4f})")
        lines.append(f"predicted entities to check: {r['predicted_entities']}")
        lines.append("")
    out = "\n".join(lines)
    (HERE / "error_breakdown_output.txt").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
