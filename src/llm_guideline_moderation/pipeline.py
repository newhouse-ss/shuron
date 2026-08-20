from __future__ import annotations

import json
from dataclasses import asdict

from .prompt_utils import format_sample_sections_for_prompt, generate_schema_parts
from .prompts import render_prompt
from .risk import assess_risk
from .text_utils import align_annotations
from .types import (
    Annotation,
    AnnotationAuditChange,
    FullSimulationResult,
    InitialAnnotationResult,
    ModeratedAnnotationResult,
    ModerationRoundInput,
    ModerationRoundResult,
    ModerationRunResult,
)
from .providers.base import ModerationProvider

DISCREPANCY_SENTINEL = "__DISCREPANCY_INSIGHT__"
PRINCIPLE_SENTINEL = "__MODERATION_PRINCIPLE__"
GUIDELINES_SENTINEL = "__REFINED_GUIDELINES__"


def _entity_schema_text(entities) -> str:
    lines = []
    for entity in entities:
        if entity.description:
            lines.append(f"- {entity.name}: {entity.description}")
        else:
            lines.append(f"- {entity.name}")
    return "\n".join(lines)


def _annotation_json(annotations: list[Annotation]) -> str:
    return json.dumps([asdict(annotation) for annotation in annotations], indent=2, ensure_ascii=False)


def _parse_moderated_annotation_result(raw_text: str) -> ModeratedAnnotationResult:
    parsed = json.loads(raw_text)
    raw_annotations = parsed.get("annotations", [])
    raw_changes = parsed.get("changes", [])

    annotations = [Annotation(**item) for item in raw_annotations]
    changes = [AnnotationAuditChange(**item) for item in raw_changes]
    return ModeratedAnnotationResult(
        annotations=annotations,
        changes=changes,
        raw_response=parsed,
    )


def _parse_initial_annotation_result(raw_text: str) -> InitialAnnotationResult:
    parsed = json.loads(raw_text)
    raw_annotations = parsed.get("annotations", [])
    annotations = [Annotation(**item) for item in raw_annotations]
    return InitialAnnotationResult(
        annotations=annotations,
        raw_response=parsed,
    )


def annotate_with_guidelines(
    text: str,
    guidelines: str,
    entities,
    provider: ModerationProvider,
    instructions: str = "",
    system_instruction: str = (
        "You are an expert AI for text annotation. "
        "Your task is to annotate all entities from the provided text based on a strict schema and guidelines."
    ),
    output_configuration=None,
) -> InitialAnnotationResult:
    if output_configuration is None:
        output_configuration = ModerationRoundInput(
            text=text,
            guidelines=guidelines,
            initial_annotations=[],
            entities=entities,
        ).output_configuration #?

    json_schema, rationale_instruction = generate_schema_parts(output_configuration) #?
    prompt = render_prompt(
        "annotate_with_guidelines",
        system_instruction=system_instruction,
        entity_schema=_entity_schema_text(entities),
        guidelines=guidelines or "(no guidelines provided)",
        instructions=instructions or "Follow the provided guidelines exactly.",
        json_schema=json_schema,
        rationale_instruction=rationale_instruction,
        input_text=text,
    )
    result = _parse_initial_annotation_result(
        provider.complete("annotate_with_guidelines", prompt)
    )
    return InitialAnnotationResult(
        annotations=align_annotations(text, result.annotations),
        raw_response=result.raw_response,
    )


def simulate_moderation_round(
    round_index: int,
    round_input: ModerationRoundInput,
    provider: ModerationProvider,
) -> ModerationRoundResult:
    formatted_samples = format_sample_sections_for_prompt(
        round_input.sample_sections,
        max_sample_text_length=2000,
    ) or "(no reference samples provided)"
    json_schema, rationale_instruction = generate_schema_parts(
        round_input.output_configuration
    )

    prompts = {
        "infer_discrepancy_patterns": render_prompt(
            "infer_discrepancy_patterns",
            entity_schema=_entity_schema_text(round_input.entities),
            discrepant_examples=round_input.discrepancy_examples or "(no discrepancy examples provided)",
            true_positive_examples=round_input.true_positive_examples or "(no true positive examples provided)",
            raw_examples=round_input.raw_examples or "(no raw examples provided)",
        ),
        "generate_moderation_principle": render_prompt(
            "generate_moderation_principle",
            entity_schema=_entity_schema_text(round_input.entities),
            discrepancy_pattern=DISCREPANCY_SENTINEL,
            discrepant_examples=round_input.discrepancy_examples or "(no discrepancy examples provided)",
        ),
        "refine_guidelines": render_prompt(
            "refine_guidelines",
            guidelines=round_input.guidelines or "(no guidelines provided)",
            new_principles=PRINCIPLE_SENTINEL,
            verified_examples=round_input.verified_examples or "(no verified examples provided)",
        ),
        "moderate_annotations": render_prompt(
            "moderate_annotations",
            formatted_samples=formatted_samples,
            json_schema=json_schema,
            rationale_instruction=rationale_instruction,
            enhanced_guidelines=GUIDELINES_SENTINEL,
            input_text=round_input.text,
            initial_annotations=_annotation_json(round_input.initial_annotations),
        ),
    }

    discrepancy_insight = provider.complete(
        "infer_discrepancy_patterns", prompts["infer_discrepancy_patterns"]
    )
    principle_prompt = prompts["generate_moderation_principle"].replace(
        DISCREPANCY_SENTINEL, discrepancy_insight
    )
    moderation_principle = provider.complete(
        "generate_moderation_principle", principle_prompt
    )
    refine_prompt = prompts["refine_guidelines"].replace(
        PRINCIPLE_SENTINEL, moderation_principle
    )
    refined_guidelines = provider.complete("refine_guidelines", refine_prompt)
    moderate_prompt = prompts["moderate_annotations"].replace(
        GUIDELINES_SENTINEL, refined_guidelines
    )
    moderated = _parse_moderated_annotation_result(
        provider.complete("moderate_annotations", moderate_prompt)
    )
    moderated = ModeratedAnnotationResult(
        annotations=align_annotations(round_input.text, moderated.annotations),
        changes=moderated.changes,
        raw_response=moderated.raw_response,
    )

    risk = assess_risk(
        input_text=round_input.text,
        annotations=moderated.annotations,
        baseline_annotations=round_input.initial_annotations,
        audit_trail=moderated.changes,
    )

    return ModerationRoundResult(
        round_index=round_index,
        discrepancy_insight=discrepancy_insight,
        moderation_principle=moderation_principle,
        refined_guidelines=refined_guidelines,
        moderated_annotations=moderated.annotations,
        audit_trail=moderated.changes,
        risk=risk,
        prompts={
            "infer_discrepancy_patterns": prompts["infer_discrepancy_patterns"],
            "generate_moderation_principle": principle_prompt,
            "refine_guidelines": refine_prompt,
            "moderate_annotations": moderate_prompt,
        },
        raw_outputs={
            "moderate_annotations": moderated.raw_response,
        },
    )


def simulate_moderation_iterations(
    initial_input: ModerationRoundInput,
    provider: ModerationProvider,
    num_rounds: int = 1,
) -> ModerationRunResult:
    if num_rounds <= 0:
        raise ValueError("num_rounds must be at least 1")

    rounds: list[ModerationRoundResult] = []
    current_input = initial_input

    for round_index in range(1, num_rounds + 1):
        result = simulate_moderation_round(
            round_index=round_index,
            round_input=current_input,
            provider=provider,
        )
        rounds.append(result)
        current_input = ModerationRoundInput(
            text=current_input.text,
            guidelines=result.refined_guidelines,
            initial_annotations=result.moderated_annotations,
            entities=current_input.entities,
            instructions=current_input.instructions,
            sample_sections=current_input.sample_sections,
            discrepancy_examples=current_input.discrepancy_examples,
            true_positive_examples=current_input.true_positive_examples,
            raw_examples=current_input.raw_examples,
            verified_examples=current_input.verified_examples,
            output_configuration=current_input.output_configuration,
        )

    return ModerationRunResult(
        rounds=rounds,
        final_guidelines=rounds[-1].refined_guidelines,
        final_annotations=rounds[-1].moderated_annotations,
    )


def run_full_simulation(
    text: str,
    guidelines: str,
    entities,
    provider: ModerationProvider,
    instructions: str = "",
    system_instruction: str = (
        "You are an expert AI for text annotation. "
        "Your task is to annotate all entities from the provided text based on a strict schema and guidelines."
    ),
    discrepancy_examples: str = "",
    true_positive_examples: str = "",
    raw_examples: str = "",
    verified_examples: str = "",
    output_configuration=None,
    num_rounds: int = 1,
) -> FullSimulationResult:
    initial = annotate_with_guidelines(
        text=text,
        guidelines=guidelines,
        entities=entities,
        provider=provider,
        instructions=instructions,
        system_instruction=system_instruction,
        output_configuration=output_configuration,
    )
    round_input = ModerationRoundInput(
        text=text,
        guidelines=guidelines,
        initial_annotations=initial.annotations,
        entities=entities,
        instructions=instructions,
        discrepancy_examples=discrepancy_examples,
        true_positive_examples=true_positive_examples,
        raw_examples=raw_examples,
        verified_examples=verified_examples,
        output_configuration=output_configuration
        if output_configuration is not None
        else ModerationRoundInput(
            text=text,
            guidelines=guidelines,
            initial_annotations=[],
            entities=entities,
        ).output_configuration,
    )
    moderation = simulate_moderation_iterations(
        initial_input=round_input,
        provider=provider,
        num_rounds=num_rounds,
    )
    return FullSimulationResult(
        initial_annotations=initial.annotations,
        moderation=moderation,
    )
