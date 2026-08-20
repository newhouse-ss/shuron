from __future__ import annotations

from .types import Annotation, AnnotationAuditChange, RiskAssessmentResult


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _compute_span_risk(input_text: str, annotations: list[Annotation]) -> list[str]:
    reasons: list[str] = []
    for annotation in annotations:
        out_of_bounds = (
            annotation.start < 0
            or annotation.end > len(input_text)
            or annotation.start >= annotation.end
        )
        if out_of_bounds:
            reasons.append(
                f"Span {annotation.start}-{annotation.end} is misaligned with the source text."
            )
    return reasons


def _compare_annotation_volume(
    baseline_annotations: list[Annotation], updated_annotations: list[Annotation]
) -> list[str]:
    if not baseline_annotations:
        return []

    delta = abs(len(updated_annotations) - len(baseline_annotations))
    if delta >= max(2, int(len(baseline_annotations) * 0.5 + 0.9999)):
        return ["Large change in span count detected during moderation."]
    return []


def assess_risk(
    input_text: str,
    annotations: list[Annotation],
    baseline_annotations: list[Annotation] | None = None,
    audit_trail: list[AnnotationAuditChange] | None = None,
    model_confidence: float | None = None,
) -> RiskAssessmentResult:
    baseline_annotations = baseline_annotations or []
    audit_trail = audit_trail or []

    risk_score = _clamp(model_confidence if model_confidence is not None else 0.9)
    reasons: list[str] = []

    if any(annotation.uncertain for annotation in annotations):
        reasons.append("One or more spans were flagged as uncertain.")
        risk_score -= 0.15

    span_issues = _compute_span_risk(input_text, annotations)
    if span_issues:
        reasons.extend(span_issues)
        risk_score -= 0.2

    volume_changes = _compare_annotation_volume(baseline_annotations, annotations)
    if volume_changes:
        reasons.extend(volume_changes)
        risk_score -= 0.1

    if audit_trail:
        reasons.append("Moderator reported guideline or span changes.")
        risk_score -= 0.1

    risk_score = _clamp(risk_score)
    if not reasons:
        reasons.append("Heuristic checks passed; no risks detected.")

    return RiskAssessmentResult(risk_score=risk_score, risk_reasons=reasons)
