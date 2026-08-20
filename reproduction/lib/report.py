"""Console rendering for scoring results, shaped like the paper's tables."""

from __future__ import annotations

from .discrepancy import CATEGORIES, NO_ENTITY, PRED_ROWS, UNPAIRED_OVERLAP
from .scoring import ScoringResult


def _rule(width: int = 72) -> str:
    return "-" * width


def render(result: ScoringResult) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"run          : {result.label}")
    add(f"gold         : {result.gold_dir}")
    add(f"predictions  : {result.pred_dir}")
    add(f"documents    : {len(result.alignment.scored)} scored")
    add("")

    # --- Table 1 shape: P / R / F1 / TP -------------------------------------
    add("Strict match (Section 3.3: exact boundary + exact type)")
    add(_rule())
    add(f"{'impl':<16}{'P':>8}{'R':>8}{'F1':>8}{'TP':>8}{'FP':>8}{'FN':>8}")
    for name, metrics in (
        ("pubannotation", result.strict_pubannotation),
        ("set", result.strict_set),
    ):
        add(
            f"{name:<16}"
            f"{metrics.precision:>8.2f}"
            f"{metrics.recall:>8.2f}"
            f"{metrics.f1:>8.2f}"
            f"{metrics.true_positives:>8d}"
            f"{metrics.false_positives:>8d}"
            f"{metrics.false_negatives:>8d}"
        )
    add(_rule())
    add(f"gold entities: {result.strict_pubannotation.gold_total}   "
        f"predicted entities: {result.strict_pubannotation.pred_total}")

    if result.strict_pubannotation.true_positives != result.strict_set.true_positives:
        add("")
        add("WARNING: the two strict-match implementations disagree on TP.")
        add("         This happens when a document contains duplicate spans;")
        add("         the set implementation collapses them, pubannotation does not.")
    add("")

    # --- Per-label breakdown ------------------------------------------------
    add("Per entity type")
    add(_rule())
    add(f"{'label':<24}{'P':>8}{'R':>8}{'F1':>8}{'TP':>8}{'gold':>8}{'pred':>8}")
    for name, metrics in sorted(result.by_label.items()):
        add(
            f"{name:<24}"
            f"{metrics.precision:>8.2f}"
            f"{metrics.recall:>8.2f}"
            f"{metrics.f1:>8.2f}"
            f"{metrics.true_positives:>8d}"
            f"{metrics.gold_total:>8d}"
            f"{metrics.pred_total:>8d}"
        )
    add("")

    # --- Section 3.4.1 categories -------------------------------------------
    add("Discrepancy categories (Section 3.4.1, soft match >= 1 character)")
    add(_rule())
    for category in CATEGORIES:
        count = result.discrepancy_counts.get(category, 0)
        suffix = "   (overlaps a span already paired; fits none of the four)" \
            if category == UNPAIRED_OVERLAP and count else ""
        add(f"{category:<24}{count:>8d}{suffix}")
    add("")
    add(f"dominant group: {result.dominant[0]}  (n={result.dominant[1]})")
    add("")

    # --- Figure 3 confusion matrix ------------------------------------------
    axis = [*result.entity_labels, NO_ENTITY]
    pred_rows = result.orientation == PRED_ROWS
    corner = "pred \\ gold" if pred_rows else "gold \\ pred"
    add(f"Confusion matrix (Figure 3, orientation={result.orientation})")
    add(
        "diagonal = span boundary mismatches, "
        + ("O column = FP, O row = FN" if pred_rows else "O column = FN, O row = FP")
    )
    add(_rule())
    add(f"{corner:<24}" + "".join(f"{_fit(name, 10):>10}" for name in axis))
    for row in axis:
        cells = "".join(f"{result.confusion[row][column]:>10d}" for column in axis)
        add(f"{_fit(row, 24):<24}{cells}")
    add("")

    # --- Alignment problems -------------------------------------------------
    if not result.alignment.is_complete:
        add("Alignment problems")
        add(_rule())
        if result.alignment.missing_predictions:
            add(f"missing predictions ({len(result.alignment.missing_predictions)}): "
                f"{_preview(result.alignment.missing_predictions)}")
        if result.alignment.extra_predictions:
            add(f"extra predictions ({len(result.alignment.extra_predictions)}): "
                f"{_preview(result.alignment.extra_predictions)}")
        if result.alignment.text_mismatches:
            add(f"text mismatches ({len(result.alignment.text_mismatches)}): "
                f"{_preview(result.alignment.text_mismatches)}")
        add("")
        add("Scores above cover only the documents that aligned. Fix the gaps")
        add("before comparing against the paper's tables.")

    return "\n".join(lines)


def _fit(name: str, width: int) -> str:
    return name if len(name) < width else name[: width - 1]


def _preview(items: list[str], limit: int = 8) -> str:
    head = ", ".join(items[:limit])
    return head if len(items) <= limit else f"{head}, ... (+{len(items) - limit} more)"
