"""Run-to-run noise of FN, recall and F1 on dev10, per model and effort, from the saved repeat runs. Offline, no API calls.

How easily a method's recall gain shows up as significant depends on the gain divided by this noise, so the
headroom question (is Haiku a better testbed for the method?) needs both: how many FN there are to remove, and
how much the FN count moves between identical runs. Also prints the per-repeat error breakdown: predictions,
TP, FP (and how many of those have a gold span with the wrong type), FN, precision and recall. Arms without
saved units (H_max before its batch) are skipped.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

from llm_guideline_moderation.types import Annotation  # noqa: E402

it = rs.it
FIELDS = ("predictions", "tp", "fp", "wrong_type", "fn", "precision", "recall", "f1")


def per_repeat(units: list[dict], arm: str, documents: dict) -> list[dict]:
    by_rep: dict[int, dict] = {}
    for u in units:
        if u["arm"] == arm and u["status"] == "ok":
            by_rep.setdefault(u["rep"], {})[u["doc"]] = u["annotations"]
    rows = []
    for rep, preds in sorted(by_rep.items()):
        if set(preds) != set(documents):
            continue
        predictions = {doc: [Annotation(start=a["start"], end=a["end"], entity=a["entity"], text=a["text"])
                             for a in anns] for doc, anns in preds.items()}
        s = it._summarize_moderation_pairs(it._build_pairs(list(documents.values()), predictions), 1.0)
        n_pred = wrong_type = 0
        for doc, anns in predictions.items():
            gold = {it._annotation_to_key(a) for a in documents[doc].gold_annotations}
            keys = {it._annotation_to_key(a) for a in anns}
            n_pred += len(keys)
            wrong_type += sum((k[0], k[1]) in {(g[0], g[1]) for g in gold} for k in keys - gold)
        rows.append({"rep": rep, "predictions": n_pred, "tp": s.true_positives, "fp": s.false_positives,
                     "wrong_type": wrong_type, "fn": s.false_negatives, "precision": s.precision,
                     "recall": s.recall, "f1": s.overall_f1})
    return rows


def sources(documents: dict, entities) -> dict[str, list[dict]]:
    haiku = rs.fix_labels(rs.load_units(rh.UNITS), entities)
    deepseek = rs.fix_labels(rs.load_units(rs.UNIT_DIRS["run"]), entities)
    out = {"DeepSeek B_on": per_repeat(deepseek, "B_on", documents)}
    for arm in rh.ARMS:
        rows = per_repeat(haiku, arm, documents)
        if rows:
            out[f"Haiku {arm}"] = rows
    return out


def main() -> None:
    _, documents, entities = rs.load_inputs()
    data = sources(documents, entities)
    for name, rows in data.items():
        fn = [r["fn"] for r in rows]
        mean = {f: statistics.mean(r[f] for r in rows) for f in FIELDS}
        print(f"{name}: {len(rows)} complete repeats; per repeat mean predictions {mean['predictions']:.1f}, "
              f"TP {mean['tp']:.1f}, FP {mean['fp']:.1f} (of which right span, wrong type {mean['wrong_type']:.1f}), "
              f"FN {mean['fn']:.2f} SD {statistics.stdev(fn):.2f} (min {min(fn)}, max {max(fn)}); "
              f"precision {mean['precision']:.4f}; recall {mean['recall']:.4f} "
              f"SD {statistics.stdev(r['recall'] for r in rows):.4f}; "
              f"F1 {mean['f1']:.4f} SD {statistics.stdev(r['f1'] for r in rows):.4f}")
    base = statistics.stdev(r["fn"] for r in data["DeepSeek B_on"])
    for name, rows in data.items():
        if name != "DeepSeek B_on":
            ratio = statistics.stdev(r["fn"] for r in rows) / base
            print(f"FN SD ratio {name} / DeepSeek B_on = {ratio:.2f} "
                  f"(an FN drop must be this many times larger on {name} to reach the same t statistic)")


if __name__ == "__main__":
    main()
