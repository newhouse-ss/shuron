from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class EntityDefinition:
    name: str
    description: str = ""


@dataclass(slots=True)
class Annotation:
    start: int
    end: int
    text: str
    entity: str
    rationale: str | None = None
    guideline_section: str | None = None
    uncertain: bool = False
    raw_entity: str | None = None


@dataclass(slots=True)
class AnnotationAuditChange:
    action: str
    reason: str
    guideline_section: str


@dataclass(slots=True)
class GuidelineSample:
    sample_id: str
    text: str
    annotations: list[Annotation]
    raw_annotations: str | None = None


@dataclass(slots=True)
class SampleSections:
    primary_gold_sample: GuidelineSample | None = None
    initial_annotations_sample: GuidelineSample | None = None
    additional_gold_samples: list[GuidelineSample] = field(default_factory=list)


@dataclass(slots=True)
class OutputConfiguration:
    include_rationale: bool = True
    include_guideline_section: bool = True


@dataclass(slots=True)
class ModerationQueueItem:
    item_id: str
    stage: str
    risk_score: float
    risk_reasons: list[str]
    paired_review_disagreement: bool = False
    audit_trail: list[AnnotationAuditChange] = field(default_factory=list)


@dataclass(slots=True)
class RiskAssessmentResult:
    risk_score: float
    risk_reasons: list[str]


@dataclass(slots=True)
class ModeratedAnnotationResult:
    annotations: list[Annotation]
    changes: list[AnnotationAuditChange] = field(default_factory=list)
    raw_response: Any | None = None


@dataclass(slots=True)
class InitialAnnotationResult:
    annotations: list[Annotation]
    raw_response: Any | None = None


@dataclass(slots=True)
class ModerationRoundInput:
    text: str
    guidelines: str
    initial_annotations: list[Annotation]
    entities: list[EntityDefinition]
    instructions: str = ""
    sample_sections: SampleSections = field(default_factory=SampleSections)
    discrepancy_examples: str = ""
    true_positive_examples: str = ""
    raw_examples: str = ""
    verified_examples: str = ""
    output_configuration: OutputConfiguration = field(default_factory=OutputConfiguration)


@dataclass(slots=True)
class ModerationRoundResult:
    round_index: int
    discrepancy_insight: str
    moderation_principle: str
    refined_guidelines: str
    moderated_annotations: list[Annotation]
    audit_trail: list[AnnotationAuditChange]
    risk: RiskAssessmentResult
    prompts: dict[str, str] = field(default_factory=dict)
    raw_outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ModerationRunResult:
    rounds: list[ModerationRoundResult]
    final_guidelines: str
    final_annotations: list[Annotation]


@dataclass(slots=True)
class FullSimulationResult:
    initial_annotations: list[Annotation]
    moderation: ModerationRunResult


LLMTaskName = Literal[
    "annotate_with_guidelines",
    "infer_discrepancy_patterns",
    "generate_moderation_principle",
    "refine_guidelines",
    "moderate_annotations",
]
