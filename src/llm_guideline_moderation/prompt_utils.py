from __future__ import annotations

import json
from dataclasses import asdict

from .types import GuidelineSample, OutputConfiguration, SampleSections


def _truncate(text: str, max_length: int | None) -> str:
    if max_length is None or max_length <= 0 or len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


def format_initial_samples_for_prompt(
    samples: list[GuidelineSample], max_sample_text_length: int | None = None
) -> str:
    if not samples:
        return ""

    blocks: list[str] = []
    for idx, sample in enumerate(samples, start=1):
        annotations = [asdict(annotation) for annotation in sample.annotations]
        blocks.append(
            "\n".join(
                [
                    f"Sample {idx} Text:",
                    _truncate(sample.text.strip() or "(empty)", max_sample_text_length),
                    f"Sample {idx} Annotations (JSON):",
                    json.dumps(annotations, indent=2, ensure_ascii=False),
                ]
            )
        )
    return "\n\n".join(blocks)


def format_sample_sections_for_prompt(
    sections: SampleSections, max_sample_text_length: int | None = None
) -> str:
    parts: list[str] = []

    if sections.primary_gold_sample:
        parts.append(
            "\n".join(
                [
                    "PRIMARY GOLD SAMPLE (highest priority, ground truth for this text):",
                    format_initial_samples_for_prompt(
                        [sections.primary_gold_sample], max_sample_text_length
                    )
                    or "(no primary gold sample provided)",
                ]
            )
        )

    if sections.initial_annotations_sample:
        parts.append(
            "\n".join(
                [
                    "INITIAL ANNOTATIONS SAMPLE (compare against primary gold first):",
                    "Use this to identify disagreements between the model output and the primary gold sample.",
                    format_initial_samples_for_prompt(
                        [sections.initial_annotations_sample], max_sample_text_length
                    )
                    or "(no initial annotations sample provided)",
                ]
            )
        )

    if sections.additional_gold_samples:
        parts.append(
            "\n".join(
                [
                    "ADDITIONAL GOLD SAMPLES (contextual guidance after resolving primary vs. initial differences):",
                    format_initial_samples_for_prompt(
                        sections.additional_gold_samples, max_sample_text_length
                    )
                    or "(no additional gold samples)",
                ]
            )
        )

    return "\n\n".join(parts)


def generate_schema_parts(config: OutputConfiguration) -> tuple[str, str]:
    fields = [
        '"start": integer',
        '"end": integer',
        '"text": string',
        '"entity": string',
    ]

    if config.include_rationale:
        fields.append('"rationale": string')

    if config.include_guideline_section:
        fields.append('"guideline_section": string')

    json_schema = "{\n  " + ",\n  ".join(fields) + "\n}"

    if config.include_rationale and config.include_guideline_section:
        rationale_instruction = (
            'Every annotation MUST include a meaningful "rationale" and cite the corresponding "guideline_section".'
        )
    elif config.include_rationale:
        rationale_instruction = 'Every annotation MUST include a meaningful "rationale".'
    elif config.include_guideline_section:
        rationale_instruction = 'Every annotation MUST cite the corresponding "guideline_section".'
    else:
        rationale_instruction = "Return only the required fields."

    return json_schema, rationale_instruction
