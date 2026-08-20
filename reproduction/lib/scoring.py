"""Local strict-match scoring of valid-set predictions against gold.

This closes the gap where the upstream valid-set runner
(``scripts/annotate_pubannotation_dir.py``) writes prediction files but never
scores them, leaving PubAnnotation upload as the only way to obtain the
Table 1 numbers. Nothing here calls an LLM.

Two strict-match implementations are reported side by side:

* ``pubannotation`` - upstream ``evaluate_pubannotation_pairs`` with default
  options, which is what the refinement loop's own diagnostics use. Exclusive
  greedy matching, so duplicate spans are counted individually.
* ``set`` - the set-of-(start, end, label) computation from
  ``iterative.py:_calculate_f1``, which drives the loop's stopping rule.
  Duplicate spans collapse.

They agree unless a document contains duplicate annotations. Divergence is
reported rather than hidden, because Table 1's TP column needs one definite
number.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .bootstrap import ensure_upstream_importable
from .discrepancy import (
    PRED_ROWS,
    Discrepancy,
    DocumentDiscrepancies,
    category_counts,
    classify_document,
    confusion_matrix,
    dominant_group,
    to_spans,
)

ensure_upstream_importable()

from llm_guideline_moderation.evaluation import (  # noqa: E402
    DocumentPair,
    PubAnnotationEvaluatorOptions,
    evaluate_pubannotation_pairs,
)
from llm_guideline_moderation.pubannotation import pubannotation_to_annotations  # noqa: E402


@dataclass(slots=True)
class Metrics:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int
    gold_total: int
    pred_total: int

    def as_dict(self) -> dict:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "gold_total": self.gold_total,
            "pred_total": self.pred_total,
        }


@dataclass(slots=True)
class Alignment:
    """Which documents were scored, and what did not line up."""

    scored: list[str] = field(default_factory=list)
    missing_predictions: list[str] = field(default_factory=list)
    extra_predictions: list[str] = field(default_factory=list)
    text_mismatches: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "scored_documents": len(self.scored),
            "missing_predictions": self.missing_predictions,
            "extra_predictions": self.extra_predictions,
            "text_mismatches": self.text_mismatches,
        }

    @property
    def is_complete(self) -> bool:
        return not (self.missing_predictions or self.extra_predictions or self.text_mismatches)


@dataclass(slots=True)
class ScoringResult:
    label: str
    gold_dir: str
    pred_dir: str
    alignment: Alignment
    strict_pubannotation: Metrics
    strict_set: Metrics
    by_label: dict[str, Metrics]
    discrepancy_counts: dict[str, int]
    confusion: dict[str, dict[str, int]]
    dominant: tuple[str, int]
    per_document: list[dict]
    discrepancies: list[Discrepancy]
    entity_labels: list[str]
    orientation: str

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "gold_dir": self.gold_dir,
            "pred_dir": self.pred_dir,
            "alignment": self.alignment.as_dict(),
            "strict_match": {
                "pubannotation": self.strict_pubannotation.as_dict(),
                "set": self.strict_set.as_dict(),
                "implementations_agree": (
                    self.strict_pubannotation.true_positives == self.strict_set.true_positives
                ),
            },
            "by_label": {label: metrics.as_dict() for label, metrics in sorted(self.by_label.items())},
            "discrepancy_counts": self.discrepancy_counts,
            "confusion_matrix": {
                "orientation": self.orientation,
                "rows": "predictions" if self.orientation == PRED_ROWS else "gold",
                "columns": "gold" if self.orientation == PRED_ROWS else "predictions",
                "cells": self.confusion,
            },
            "dominant_discrepancy_group": {"key": self.dominant[0], "count": self.dominant[1]},
            "entity_labels": self.entity_labels,
        }


def _read_documents(directory: Path) -> dict[str, dict]:
    if not directory.is_dir():
        raise FileNotFoundError(f"directory not found: {directory}")
    documents: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        key = str(raw.get("sourceid") or path.stem)
        documents[key] = raw
    if not documents:
        raise ValueError(f"no PubAnnotation JSON files found in {directory}")
    return documents


def _finalize(tp: int, fp: int, fn: int, gold_total: int, pred_total: int) -> Metrics:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    return Metrics(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        gold_total=gold_total,
        pred_total=pred_total,
    )


def _set_strict_metrics(pairs: list[DocumentPair]) -> Metrics:
    tp = fp = fn = gold_total = pred_total = 0
    for pair in pairs:
        gold_keys = {(a.start, a.end, a.entity) for a in pair.gold_annotations}
        pred_keys = {(a.start, a.end, a.entity) for a in pair.llm_annotations}
        tp += len(gold_keys & pred_keys)
        fp += len(pred_keys - gold_keys)
        fn += len(gold_keys - pred_keys)
        gold_total += len(pair.gold_annotations)
        pred_total += len(pair.llm_annotations)
    return _finalize(tp, fp, fn, gold_total, pred_total)


def score_directory(
    gold_dir: str | Path,
    pred_dir: str | Path,
    *,
    label: str = "run",
    entity_labels: list[str] | None = None,
    orientation: str = PRED_ROWS,
) -> ScoringResult:
    gold_dir = Path(gold_dir)
    pred_dir = Path(pred_dir)
    gold_documents = _read_documents(gold_dir)
    pred_documents = _read_documents(pred_dir)

    alignment = Alignment(
        missing_predictions=sorted(set(gold_documents) - set(pred_documents)),
        extra_predictions=sorted(set(pred_documents) - set(gold_documents)),
    )

    pairs: list[DocumentPair] = []
    document_reports: list[DocumentDiscrepancies] = []
    for key in sorted(set(gold_documents) & set(pred_documents)):
        gold_raw = gold_documents[key]
        pred_raw = pred_documents[key]
        if gold_raw["text"] != pred_raw.get("text"):
            alignment.text_mismatches.append(key)
            continue

        text = gold_raw["text"]
        gold_annotations = pubannotation_to_annotations(gold_raw)
        pred_annotations = pubannotation_to_annotations(pred_raw)
        alignment.scored.append(key)
        pairs.append(
            DocumentPair(
                filename=key,
                text=text,
                llm_annotations=pred_annotations,
                gold_annotations=gold_annotations,
                gold_filename=key,
                match_strategy="pubannotation",
            )
        )
        document_reports.append(
            classify_document(key, text, to_spans(gold_annotations), to_spans(pred_annotations))
        )

    if not pairs:
        raise ValueError(
            "no documents could be aligned between gold and predictions "
            f"({len(alignment.missing_predictions)} missing, "
            f"{len(alignment.text_mismatches)} text mismatches)"
        )

    evaluation = evaluate_pubannotation_pairs(pairs, PubAnnotationEvaluatorOptions())
    overall = evaluation.overall
    strict_pubannotation = _finalize(
        tp=int(overall.matched_reference),
        fp=int(overall.study - overall.matched_study),
        fn=int(overall.reference - overall.matched_reference),
        gold_total=int(overall.reference),
        pred_total=int(overall.study),
    )

    by_label = {
        name: _finalize(
            tp=int(metrics.matched_reference),
            fp=int(metrics.study - metrics.matched_study),
            fn=int(metrics.reference - metrics.matched_reference),
            gold_total=int(metrics.reference),
            pred_total=int(metrics.study),
        )
        for name, metrics in evaluation.by_label.items()
    }

    all_discrepancies = [item for report in document_reports for item in report.discrepancies]
    labels = entity_labels or sorted(
        {a.entity for pair in pairs for a in pair.gold_annotations}
        | {a.entity for pair in pairs for a in pair.llm_annotations}
    )

    per_document = [
        {
            "doc_id": report.doc_id,
            "strict_true_positives": report.strict_true_positives,
            "gold_total": len(pair.gold_annotations),
            "pred_total": len(pair.llm_annotations),
            "discrepancy_counts": category_counts(report.discrepancies),
        }
        for report, pair in zip(document_reports, pairs)
    ]

    return ScoringResult(
        label=label,
        gold_dir=str(gold_dir),
        pred_dir=str(pred_dir),
        alignment=alignment,
        strict_pubannotation=strict_pubannotation,
        strict_set=_set_strict_metrics(pairs),
        by_label=by_label,
        discrepancy_counts=category_counts(all_discrepancies),
        confusion=confusion_matrix(all_discrepancies, labels, orientation=orientation),
        dominant=dominant_group(all_discrepancies),
        per_document=per_document,
        discrepancies=all_discrepancies,
        entity_labels=labels,
        orientation=orientation,
    )
