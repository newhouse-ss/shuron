from __future__ import annotations

from dataclasses import dataclass, field

from .types import Annotation


@dataclass(slots=True)
class PubAnnotationEvaluatorOptions:
    soft_match_characters: int = 0
    soft_match_words: int = 0


@dataclass(slots=True)
class PubAnnotationMetrics:
    study: float = 0
    reference: float = 0
    matched_study: float = 0
    matched_reference: float = 0
    precision: float = 0
    recall: float = 0
    f1: float = 0
    false_positives: float = 0
    false_negatives: float = 0


@dataclass(slots=True)
class DocumentPair:
    filename: str
    text: str
    llm_annotations: list[Annotation]
    gold_annotations: list[Annotation]
    gold_filename: str | None = None
    match_strategy: str | None = None


@dataclass(slots=True)
class ConflictCandidate:
    label: str
    span: str
    candidate_count: int
    candidates: list[str]


@dataclass(slots=True)
class ConflictSummary:
    candidate_count: int
    study_conflict_count: int
    reference_conflict_count: int
    top_study_conflicts: list[ConflictCandidate] = field(default_factory=list)
    top_reference_conflicts: list[ConflictCandidate] = field(default_factory=list)


@dataclass(slots=True)
class MatchedPair:
    label: str
    study_span: str
    reference_span: str
    study_text: str
    reference_text: str


@dataclass(slots=True)
class AnnotationView:
    label: str
    start: int
    end: int
    text: str


@dataclass(slots=True)
class PubAnnotationFileDiagnostic:
    filename: str
    gold_filename: str | None
    match_strategy: str | None
    study_total: float
    reference_total: float
    matched_study_total: float
    matched_reference_total: float
    by_label: dict[str, PubAnnotationMetrics]
    conflict_summary: ConflictSummary
    study_denotations: list[AnnotationView]
    reference_denotations: list[AnnotationView]
    matched_pairs: list[MatchedPair]


@dataclass(slots=True)
class PubAnnotationEvaluation:
    overall: PubAnnotationMetrics
    by_label: dict[str, PubAnnotationMetrics]


@dataclass(slots=True)
class PubAnnotationDiagnostics:
    overall: PubAnnotationEvaluation
    files: list[PubAnnotationFileDiagnostic]


@dataclass(slots=True)
class _CandidateMatch:
    study_index: int
    reference_index: int
    study: Annotation
    reference: Annotation
    weight: int


def _exact_entity_label(annotation: Annotation) -> str:
    return annotation.entity


def _count_spaces(text: str) -> int:
    return text.count(" ")


def _has_overlap(study: Annotation, reference: Annotation) -> bool:
    return not (study.end <= reference.start or study.start >= reference.end)


def _relatedness(
    study: Annotation,
    reference: Annotation,
    text: str,
    options: PubAnnotationEvaluatorOptions,
) -> int:
    if not _has_overlap(study, reference):
        return 0

    if (
        abs(study.start - reference.start) > options.soft_match_characters #能容许的最大偏差字符数
        or abs(study.end - reference.end) > options.soft_match_characters
    ):
        return 0

    front_mismatch = (# front of the mismatch part of the text between study and reference
        text[study.start:reference.start]
        if study.start < reference.start
        else text[reference.start:study.start]
    )
    if _count_spaces(front_mismatch) > options.soft_match_words: 
        return 0

    rear_mismatch = (
        text[study.end:reference.end]
        if study.end < reference.end
        else text[reference.end:study.end]
    )
    if _count_spaces(rear_mismatch) > options.soft_match_words:
        return 0

    return 1 if _exact_entity_label(study) == _exact_entity_label(reference) else 0


def _is_better_match(candidate: _CandidateMatch, current: _CandidateMatch) -> bool:
    if candidate.weight != current.weight:
        return candidate.weight > current.weight

    candidate_end_diff = abs(candidate.study.end - candidate.reference.end)
    current_end_diff = abs(current.study.end - current.reference.end)
    if candidate_end_diff != current_end_diff:
        return candidate_end_diff < current_end_diff

    candidate_start_diff = abs(candidate.study.start - candidate.reference.start)
    current_start_diff = abs(current.study.start - current.reference.start)
    return candidate_start_diff < current_start_diff


def _find_exclusive_matches(matches: list[_CandidateMatch]) -> list[_CandidateMatch]:
    if not matches:
        return []

    by_study: dict[int, list[_CandidateMatch]] = {}
    for match in matches:
        by_study.setdefault(match.study_index, []).append(match)

    reference_matched: set[int] = set()
    narrowed: list[_CandidateMatch] = []
    for study_matches in by_study.values():
        available = [match for match in study_matches if match.reference_index not in reference_matched]
        if not available:
            continue
        selected = available[0]
        for candidate in available[1:]:
            if _is_better_match(candidate, selected):
                selected = candidate
        reference_matched.add(selected.reference_index)
        narrowed.append(selected)

    by_reference: dict[int, list[_CandidateMatch]] = {}
    for match in narrowed:
        by_reference.setdefault(match.reference_index, []).append(match)

    final_matches: list[_CandidateMatch] = []
    for reference_matches in by_reference.values():
        selected = reference_matches[0]
        for candidate in reference_matches[1:]:
            if _is_better_match(candidate, selected):
                selected = candidate
        final_matches.append(selected)
    return final_matches


def _summarize_candidate_conflicts(matches: list[_CandidateMatch]) -> ConflictSummary:
    by_study: dict[int, list[_CandidateMatch]] = {}
    by_reference: dict[int, list[_CandidateMatch]] = {}
    for match in matches:
        by_study.setdefault(match.study_index, []).append(match)
        by_reference.setdefault(match.reference_index, []).append(match)

    top_study = [
        ConflictCandidate(
            label=_exact_entity_label(bucket[0].study),
            span=f"{bucket[0].study.start}-{bucket[0].study.end}",
            candidate_count=len(bucket),
            candidates=sorted(
                f"{_exact_entity_label(match.reference)}:{match.reference.start}-{match.reference.end}"
                for match in bucket
            ),
        )
        for bucket in sorted(
            [bucket for bucket in by_study.values() if len(bucket) > 1],
            key=len,
            reverse=True,
        )[:5]
    ]

    top_reference = [
        ConflictCandidate(
            label=_exact_entity_label(bucket[0].reference),
            span=f"{bucket[0].reference.start}-{bucket[0].reference.end}",
            candidate_count=len(bucket),
            candidates=sorted(
                f"{_exact_entity_label(match.study)}:{match.study.start}-{match.study.end}"
                for match in bucket
            ),
        )
        for bucket in sorted(
            [bucket for bucket in by_reference.values() if len(bucket) > 1],
            key=len,
            reverse=True,
        )[:5]
    ]

    return ConflictSummary(
        candidate_count=len(matches),
        study_conflict_count=len([bucket for bucket in by_study.values() if len(bucket) > 1]),
        reference_conflict_count=len([bucket for bucket in by_reference.values() if len(bucket) > 1]),
        top_study_conflicts=top_study,
        top_reference_conflicts=top_reference,
    )


def _compare_denotations(
    study_denotations: list[Annotation],
    reference_denotations: list[Annotation],
    text: str,
    options: PubAnnotationEvaluatorOptions,
) -> tuple[list[_CandidateMatch], ConflictSummary]:
    sorted_study = sorted(study_denotations, key=lambda ann: (ann.start, -ann.end))
    sorted_reference = sorted(reference_denotations, key=lambda ann: (ann.start, -ann.end))

    matches: list[_CandidateMatch] = []
    for study_index, study in enumerate(sorted_study):
        for reference_index, reference in enumerate(sorted_reference):
            weight = _relatedness(study, reference, text, options)#
            if weight > 0:
                matches.append(
                    _CandidateMatch(
                        study_index=study_index,
                        reference_index=reference_index,
                        study=study,
                        reference=reference,
                        weight=weight,
                    )
                )

    return _find_exclusive_matches(matches), _summarize_candidate_conflicts(matches)


def _finalize_metrics(
    study: float,
    reference: float,
    matched_study: float,
    matched_reference: float,
) -> PubAnnotationMetrics:
    precision = matched_study / study if study > 0 else 0
    recall = matched_reference / reference if reference > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return PubAnnotationMetrics(
        study=study,
        reference=reference,
        matched_study=matched_study,
        matched_reference=matched_reference,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positives=study - matched_study,
        false_negatives=reference - matched_reference,
    )


def evaluate_pubannotation_pairs(
    pairs: list[DocumentPair],
    options: PubAnnotationEvaluatorOptions | None = None,
) -> PubAnnotationEvaluation:
    options = options or PubAnnotationEvaluatorOptions()

    study_counts: dict[str, float] = {}
    reference_counts: dict[str, float] = {}
    matched_study_counts: dict[str, float] = {}
    matched_reference_counts: dict[str, float] = {}
    study_all = 0.0
    reference_all = 0.0
    matched_study_all = 0.0
    matched_reference_all = 0.0

    for pair in pairs:
        for annotation in pair.llm_annotations:
            label = _exact_entity_label(annotation)
            study_counts[label] = study_counts.get(label, 0) + 1
            study_all += 1

        for annotation in pair.gold_annotations:
            label = _exact_entity_label(annotation)
            reference_counts[label] = reference_counts.get(label, 0) + 1
            reference_all += 1

        matches, _ = _compare_denotations(
            pair.llm_annotations,
            pair.gold_annotations,
            pair.text,
            options,
        )
        for match in matches:
            study_label = _exact_entity_label(match.study)
            reference_label = _exact_entity_label(match.reference)
            matched_study_counts[study_label] = matched_study_counts.get(study_label, 0) + match.weight
            matched_reference_counts[reference_label] = matched_reference_counts.get(reference_label, 0) + match.weight
            matched_study_all += match.weight
            matched_reference_all += match.weight

    labels = set(study_counts) | set(reference_counts) | set(matched_study_counts) | set(matched_reference_counts)
    by_label = {
        label: _finalize_metrics(
            study_counts.get(label, 0),
            reference_counts.get(label, 0),
            matched_study_counts.get(label, 0),
            matched_reference_counts.get(label, 0),
        )
        for label in labels
    }

    return PubAnnotationEvaluation(
        overall=_finalize_metrics(study_all, reference_all, matched_study_all, matched_reference_all),
        by_label=by_label,
    )


def build_pubannotation_diagnostics(
    pairs: list[DocumentPair],
    options: PubAnnotationEvaluatorOptions | None = None,
) -> PubAnnotationDiagnostics:
    options = options or PubAnnotationEvaluatorOptions()
    files: list[PubAnnotationFileDiagnostic] = []

    for pair in pairs:
        study_counts: dict[str, float] = {}
        reference_counts: dict[str, float] = {}
        matched_study_counts: dict[str, float] = {}
        matched_reference_counts: dict[str, float] = {}

        for annotation in pair.llm_annotations:
            label = _exact_entity_label(annotation)
            study_counts[label] = study_counts.get(label, 0) + 1

        for annotation in pair.gold_annotations:
            label = _exact_entity_label(annotation)
            reference_counts[label] = reference_counts.get(label, 0) + 1

        matches, conflict_summary = _compare_denotations(
            pair.llm_annotations,
            pair.gold_annotations,
            pair.text,
            options,
        )
        for match in matches:
            study_label = _exact_entity_label(match.study)
            reference_label = _exact_entity_label(match.reference)
            matched_study_counts[study_label] = matched_study_counts.get(study_label, 0) + match.weight
            matched_reference_counts[reference_label] = matched_reference_counts.get(reference_label, 0) + match.weight

        labels = set(study_counts) | set(reference_counts) | set(matched_study_counts) | set(matched_reference_counts)
        by_label = {
            label: _finalize_metrics(
                study_counts.get(label, 0),
                reference_counts.get(label, 0),
                matched_study_counts.get(label, 0),
                matched_reference_counts.get(label, 0),
            )
            for label in labels
        }

        files.append(
            PubAnnotationFileDiagnostic(
                filename=pair.filename,
                gold_filename=pair.gold_filename,
                match_strategy=pair.match_strategy,
                study_total=sum(study_counts.values()),
                reference_total=sum(reference_counts.values()),
                matched_study_total=sum(matched_study_counts.values()),
                matched_reference_total=sum(matched_reference_counts.values()),
                by_label=by_label,
                conflict_summary=conflict_summary,
                study_denotations=[
                    AnnotationView(
                        label=_exact_entity_label(annotation),
                        start=annotation.start,
                        end=annotation.end,
                        text=annotation.text,
                    )
                    for annotation in pair.llm_annotations
                ],
                reference_denotations=[
                    AnnotationView(
                        label=_exact_entity_label(annotation),
                        start=annotation.start,
                        end=annotation.end,
                        text=annotation.text,
                    )
                    for annotation in pair.gold_annotations
                ],
                matched_pairs=[
                    MatchedPair(
                        label=_exact_entity_label(match.study),
                        study_span=f"{match.study.start}-{match.study.end}",
                        reference_span=f"{match.reference.start}-{match.reference.end}",
                        study_text=match.study.text,
                        reference_text=match.reference.text,
                    )
                    for match in matches
                ],
            )
        )

    return PubAnnotationDiagnostics(
        overall=evaluate_pubannotation_pairs(pairs, options),
        files=files,
    )


def aggregate_pubannotation_metrics(
    evaluation: PubAnnotationEvaluation | None,
    selected_labels: list[str],
) -> PubAnnotationMetrics:
    if evaluation is None:
        return PubAnnotationMetrics()
    if not selected_labels:
        return evaluation.overall

    study = reference = matched_study = matched_reference = 0.0
    for label in selected_labels:
        metrics = evaluation.by_label.get(label, PubAnnotationMetrics())
        study += metrics.study
        reference += metrics.reference
        matched_study += metrics.matched_study
        matched_reference += metrics.matched_reference
    return _finalize_metrics(study, reference, matched_study, matched_reference)
