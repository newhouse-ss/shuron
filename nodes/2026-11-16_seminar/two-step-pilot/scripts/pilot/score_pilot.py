"""Score a completed pilot offline, using the frozen document-paired decision rule."""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
from common import ARMS, RUNS, SEED, TRAIN, manifest, read_json, temporary_directory, write_json  # noqa: E402
from run_pilot import arm_dir, freeze_inputs, usage_report  # noqa: E402
from lib.discrepancy import FALSE_NEGATIVE, FALSE_POSITIVE, classify_document, to_spans  # noqa: E402
from lib.scoring import score_directory  # noqa: E402
from llm_guideline_moderation.pubannotation import pubannotation_to_annotations  # noqa: E402

RESAMPLES = 10_000


def document_counts(name, gold, prediction):
    if gold["text"] != prediction["text"]:
        raise ValueError(f"prediction text differs from gold: {name}")
    report = classify_document(name, gold["text"], to_spans(pubannotation_to_annotations(gold)),
                               to_spans(pubannotation_to_annotations(prediction)))
    misses = Counter(d.gold_label for d in report.discrepancies if d.category == FALSE_NEGATIVE)
    return {"true_misses": sum(misses.values()), "misses_by_gold_label": dict(misses),
            "nonoverlap_predictions": sum(d.category == FALSE_POSITIVE for d in report.discrepancies)}


def percentile(ordered, probability):
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def paired_comparisons(means, names, *, resamples=RESAMPLES, seed=SEED):
    differences = {arm: [means["T"][n] - means[arm][n] for n in names] for arm in ("S", "S+")}
    rng = random.Random(seed)
    draws = {arm: [] for arm in differences}
    for _ in range(resamples):
        # Resample the documents, retaining both runs and all arms together.
        indices = rng.choices(range(len(names)), k=len(names))
        for arm, values in differences.items():
            draws[arm].append(sum(values[i] for i in indices))
    comparisons = {}
    for arm, values in differences.items():
        ordered = sorted(draws[arm])
        interval = [percentile(ordered, 0.025), percentile(ordered, 0.975)]
        comparisons[f"T_minus_{arm}"] = {"sum_difference": sum(values), "ci95": interval,
                                          "passes": interval[1] < 0}
    if comparisons["T_minus_S"]["passes"] and comparisons["T_minus_S+"]["passes"]:
        outcome = "pass"
    elif comparisons["T_minus_S"]["passes"]:
        outcome = "wins S only, not S+"
    else:
        outcome = "does not win S"
    return {"outcome": outcome, "comparisons": comparisons, "resamples": resamples, "seed": seed,
            "interval_method": "two-sided document bootstrap percentile, linear quantiles"}


def score(root: Path, report_dir: Path) -> dict:
    # Verify the exact manifest without creating a missing one or opening excluded documents.
    if not (root / "manifest.json").is_file():
        raise ValueError("no paid-run manifest; scoring has not been started")
    frozen, _, entities = freeze_inputs(root)
    names = frozen["pilot_documents"]
    assert names == manifest()["pilot_documents"] and len(names) == 200
    report_dir.mkdir(parents=True, exist_ok=False)
    usages, unusable, missing_units = {}, [], []
    for arm in ARMS:
        for run in RUNS:
            directory = arm_dir(root, arm, run)
            usage = usage_report(directory)
            usages[arm, run] = usage
            unusable.extend(usage["unusable_calls"])
            for name in names:
                status_path = directory / "documents" / name
                if not status_path.exists() or read_json(status_path)["status"] != "completed":
                    missing_units.append(f"{arm}/run{run:02d}/{name}")
                for track in ("track1_predictions", "track2_predictions"):
                    if not (directory / track / name).is_file():
                        missing_units.append(f"{arm}/run{run:02d}/{track}/{name}")
    count = sum(u["logical_calls"] for u in usages.values())
    fraction = len(unusable) / count if count else 1
    summary = {"logical_calls": count, "unusable_fraction": fraction, "unusable_calls": unusable,
               "missing_units": missing_units, "per_call_usage": {f"{a}/run{r:02d}": u for (a, r), u in usages.items()}}
    if fraction > 0.05 or missing_units:
        summary.update(outcome="inconclusive", reason="more than 5% unusable calls" if fraction > 0.05
                       else "the prescribed 200-document paired comparison is incomplete")
        write_json(report_dir / "metrics.json", summary)
        return summary
    gold = {name: read_json(TRAIN / name) for name in names}
    by_arm, means = {}, {}
    with temporary_directory(report_dir, "pilot_gold_") as gold_dir:
        for name, document in gold.items():
            write_json(gold_dir / name, document)
        for arm in ARMS:
            runs, means[arm] = [], {}
            for run in RUNS:
                directory = arm_dir(root, arm, run)
                for track in ("track1_predictions", "track2_predictions"):
                    actual = {p.name for p in (directory / track).glob("*.json")}
                    if actual != set(names):
                        raise ValueError(f"predictions must contain exactly the 200 pilot documents: {directory / track}")
                strict = score_directory(gold_dir, directory / "track1_predictions", label=f"{arm}/run{run:02d}",
                                         entity_labels=[e.name for e in entities])
                if not strict.alignment.is_complete or len(strict.alignment.scored) != 200:
                    raise ValueError(f"incomplete strict F1 alignment: {arm}/run{run:02d}")
                per_document = {name: document_counts(name, gold[name], read_json(directory / "track2_predictions" / name))
                                for name in names}
                missed_labels = Counter()
                for counts in per_document.values():
                    missed_labels.update(counts["misses_by_gold_label"])
                metrics = {"track1_strict": strict.strict_pubannotation.as_dict(),
                           "track1_f1": strict.strict_pubannotation.f1,
                           "track2_true_misses": sum(c["true_misses"] for c in per_document.values()),
                           "track2_nonoverlap_predictions": sum(c["nonoverlap_predictions"] for c in per_document.values()),
                           "true_misses_by_gold_label": {e.name: missed_labels[e.name] for e in entities},
                           "per_document": per_document,
                           "undecided": sum(read_json(directory / "documents" / name)["undecided"] for name in names),
                           "usage": usages[arm, run]}
                write_json(directory / "metrics.json", metrics)
                runs.append(metrics)
            means[arm] = {name: statistics.mean(r["per_document"][name]["true_misses"] for r in runs) for name in names}
            by_arm[arm] = {"track1_f1_mean": statistics.mean(r["track1_f1"] for r in runs),
                           "track2_true_misses_mean": statistics.mean(r["track2_true_misses"] for r in runs),
                           "track2_nonoverlap_predictions_mean": statistics.mean(r["track2_nonoverlap_predictions"] for r in runs),
                           "true_misses_by_gold_label_mean": {e.name: statistics.mean(r["true_misses_by_gold_label"][e.name]
                                                                                     for r in runs) for e in entities},
                           "undecided_total": sum(r["undecided"] for r in runs)}
    summary.update(paired_comparisons(means, names), arms=by_arm)
    write_json(report_dir / "metrics.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True, help="new directory for this offline analysis")
    args = parser.parse_args()
    result = score(args.run_root.resolve(), args.report_dir.resolve())
    print(f"Outcome: {result['outcome']}")
    for label, comparison in result.get("comparisons", {}).items():
        print(f"{label}: sum difference={comparison['sum_difference']}; 95% CI={comparison['ci95']}")
    for arm, metrics in result.get("arms", {}).items():
        print(f"{arm}: {metrics}")
    for call in result["unusable_calls"]:
        print(f"Unusable call: {call}")
    for unit in result["missing_units"]:
        print(f"Missing unit: {unit}")
    print(f"Per-call usage and cost: {args.report_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()
