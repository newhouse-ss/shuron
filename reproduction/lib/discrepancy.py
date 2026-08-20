"""Discrepancy categorisation following the paper, Section 3.4.1.

The paper defines four *mutually exclusive* categories, resolved in this
priority order, using a soft matching criterion of at least one character of
overlap:

1. Label mismatch    - overlap, different types
2. Boundary mismatch - overlap, same type, different offsets
3. False negative    - a gold entity with zero overlap against any prediction
4. False positive    - a prediction with zero overlap against any gold entity

The upstream implementation (``iterative.py:_build_discrepancy_clusters``)
resolves categories 1 and 2 inside a single document-order greedy loop, so a
gold entity that could pair with either a differently-typed or a same-typed
prediction is classified by whichever it happens to meet first. This module
applies the stated priority explicitly and pairs by largest overlap first, so
the categorisation is order-independent.

A residual bucket (``unpaired_overlap``) catches entities that overlap
something which an earlier pairing already consumed. Those fit none of the four
definitions literally, so they are counted and reported rather than folded into
false negatives or false positives.
"""

from __future__ import annotations

from dataclasses import dataclass

NO_ENTITY = "O"

LABEL_MISMATCH = "label_mismatch"
BOUNDARY_MISMATCH = "boundary_mismatch"
FALSE_NEGATIVE = "false_negative"
FALSE_POSITIVE = "false_positive"
UNPAIRED_OVERLAP = "unpaired_overlap"

CATEGORIES = (
    LABEL_MISMATCH,
    BOUNDARY_MISMATCH,
    FALSE_NEGATIVE,
    FALSE_POSITIVE,
    UNPAIRED_OVERLAP,
)

CONTEXT_WINDOW = 60


@dataclass(slots=True)
class Span:
    start: int
    end: int
    label: str
    text: str

    def as_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "label": self.label, "text": self.text}


@dataclass(slots=True)
class Discrepancy:
    category: str
    doc_id: str
    gold_label: str
    pred_label: str
    gold: Span | None
    pred: Span | None
    context: str
    context_start: int

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "doc_id": self.doc_id,
            "gold_label": self.gold_label,
            "pred_label": self.pred_label,
            "gold": self.gold.as_dict() if self.gold else None,
            "pred": self.pred.as_dict() if self.pred else None,
            "context": self.context,
            "context_start": self.context_start,
        }


@dataclass(slots=True)
class DocumentDiscrepancies:
    doc_id: str
    strict_true_positives: int
    discrepancies: list[Discrepancy]


def to_spans(annotations) -> list[Span]:
    """Convert upstream ``Annotation`` objects into local spans."""
    return [
        Span(start=a.start, end=a.end, label=a.entity, text=a.text)
        for a in annotations
    ]


def _overlap(a: Span, b: Span) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start))


def _context(text: str, start: int, end: int, window: int) -> tuple[str, int]:
    begin = max(0, start - window)
    finish = min(len(text), end + window)
    return text[begin:finish], begin


def _pair_by_overlap(
    gold: list[Span],
    pred: list[Span],
    gold_open: set[int],
    pred_open: set[int],
    *,
    same_label: bool,
) -> list[tuple[int, int]]:
    """Greedily pair open gold/pred spans, largest overlap first."""
    candidates: list[tuple[int, int, int, int, int]] = []
    for gi in sorted(gold_open):
        for pi in sorted(pred_open):
            g, p = gold[gi], pred[pi]
            if (g.label == p.label) is not same_label:
                continue
            overlap = _overlap(g, p)
            if overlap <= 0:
                continue
            # Sort key: widest overlap first, then earliest offsets, for determinism.
            candidates.append((-overlap, g.start, p.start, gi, pi))

    candidates.sort()
    pairs: list[tuple[int, int]] = []
    for _, _, _, gi, pi in candidates:
        if gi in gold_open and pi in pred_open:
            gold_open.discard(gi)
            pred_open.discard(pi)
            pairs.append((gi, pi))
    return pairs


def classify_document(
    doc_id: str,
    text: str,
    gold: list[Span],
    pred: list[Span],
    *,
    context_window: int = CONTEXT_WINDOW,
) -> DocumentDiscrepancies:
    gold_open = set(range(len(gold)))
    pred_open = set(range(len(pred)))

    # Strict matches are true positives (Section 3.3), not discrepancies.
    strict_true_positives = 0
    for gi in sorted(gold_open):
        g = gold[gi]
        for pi in sorted(pred_open):
            p = pred[pi]
            if g.start == p.start and g.end == p.end and g.label == p.label:
                gold_open.discard(gi)
                pred_open.discard(pi)
                strict_true_positives += 1
                break

    found: list[Discrepancy] = []

    # Priority 1 then 2: label mismatch is resolved before boundary mismatch.
    for category, same_label in ((LABEL_MISMATCH, False), (BOUNDARY_MISMATCH, True)):
        for gi, pi in _pair_by_overlap(gold, pred, gold_open, pred_open, same_label=same_label):
            g, p = gold[gi], pred[pi]
            context, context_start = _context(
                text, min(g.start, p.start), max(g.end, p.end), context_window
            )
            found.append(
                Discrepancy(
                    category=category,
                    doc_id=doc_id,
                    gold_label=g.label,
                    pred_label=p.label,
                    gold=g,
                    pred=p,
                    context=context,
                    context_start=context_start,
                )
            )

    # Priority 3: gold entities with zero overlap against *any* prediction.
    for gi in sorted(gold_open):
        g = gold[gi]
        overlaps_any = any(_overlap(g, p) > 0 for p in pred)
        context, context_start = _context(text, g.start, g.end, context_window)
        found.append(
            Discrepancy(
                category=UNPAIRED_OVERLAP if overlaps_any else FALSE_NEGATIVE,
                doc_id=doc_id,
                gold_label=g.label,
                pred_label=NO_ENTITY,
                gold=g,
                pred=None,
                context=context,
                context_start=context_start,
            )
        )

    # Priority 4: predictions with zero overlap against *any* gold entity.
    for pi in sorted(pred_open):
        p = pred[pi]
        overlaps_any = any(_overlap(g, p) > 0 for g in gold)
        context, context_start = _context(text, p.start, p.end, context_window)
        found.append(
            Discrepancy(
                category=UNPAIRED_OVERLAP if overlaps_any else FALSE_POSITIVE,
                doc_id=doc_id,
                gold_label=NO_ENTITY,
                pred_label=p.label,
                gold=None,
                pred=p,
                context=context,
                context_start=context_start,
            )
        )

    return DocumentDiscrepancies(
        doc_id=doc_id,
        strict_true_positives=strict_true_positives,
        discrepancies=found,
    )


def category_counts(discrepancies: list[Discrepancy]) -> dict[str, int]:
    counts = {category: 0 for category in CATEGORIES}
    for item in discrepancies:
        counts[item.category] += 1
    return counts


PRED_ROWS = "pred-rows"
GOLD_ROWS = "gold-rows"
ORIENTATIONS = (PRED_ROWS, GOLD_ROWS)


def confusion_matrix(
    discrepancies: list[Discrepancy],
    labels: list[str],
    *,
    orientation: str = PRED_ROWS,
) -> dict[str, dict[str, int]]:
    """Build the Figure 3 confusion matrix.

    Orientation only affects layout - ``Discrepancy`` always stores gold_label
    and pred_label explicitly, so the underlying counts never depend on it.

    ``pred-rows`` (default) matches how Figure 3's numbers actually line up with
    the Section 5.4 narrative. That section makes two label-specific claims about
    the NCBI run, and both land correctly only under this orientation:

    * the iteration-0 dominant pattern is "Predicted: DiseaseClass, Gold: No
      Entity" with frequency 7, which is Figure 3a's D row, O column;
    * "five label mismatch cases ... incorrectly labeled as SpecificDisease
      instead of the gold label Modifier", which is Figure 3a's S row, M column
      (=5), falling to 0 in Figure 3b.

    Under this orientation the ``O`` column holds false positives and the ``O``
    row holds false negatives.

    ``gold-rows`` follows the Figure 3 caption instead ("Rows correspond to the
    gold labels and columns to the model predictions"), which is also what
    Figure 2 implies - it describes the same dominant pattern as *suppressed*
    DiseaseClass mentions whose fix is "to reduce DiseaseClass false negatives".
    That reading cannot be reconciled with either Section 5.4 claim, so the
    paper is internally inconsistent somewhere here regardless of choice. Keep
    both available and let an actual run settle which dominant pattern appears.

    The diagonal holds span boundary mismatches under either orientation.
    """
    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {ORIENTATIONS}, got {orientation!r}")

    axis = [*labels, NO_ENTITY]
    matrix = {row: {column: 0 for column in axis} for row in axis}

    for item in discrepancies:
        if item.category == UNPAIRED_OVERLAP:
            continue
        if orientation == PRED_ROWS:
            first, second = item.pred_label, item.gold_label
        else:
            first, second = item.gold_label, item.pred_label
        row = first if first in matrix else NO_ENTITY
        column = second if second in matrix[row] else NO_ENTITY
        matrix[row][column] += 1

    return matrix


def dominant_group(discrepancies: list[Discrepancy]) -> tuple[str, int]:
    """Most frequent (gold, pred) label pair - the moderation target in 3.4.1."""
    groups: dict[str, int] = {}
    for item in discrepancies:
        if item.category == UNPAIRED_OVERLAP:
            continue
        key = f"Gold: {item.gold_label} vs Pred: {item.pred_label}"
        groups[key] = groups.get(key, 0) + 1
    if not groups:
        return ("none", 0)
    return max(groups.items(), key=lambda kv: (kv[1], kv[0]))
