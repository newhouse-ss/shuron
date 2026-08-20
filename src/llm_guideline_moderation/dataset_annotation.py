from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .pipeline import annotate_with_guidelines
from .pubannotation import annotations_to_pubannotation
from .types import EntityDefinition, OutputConfiguration


@dataclass(slots=True)
class DatasetAnnotationResult:
    filename: str
    sourceid: str
    output_document: dict


def annotate_pubannotation_directory(
    input_dir: str | Path,
    output_dir: str | Path,
    guidelines: str,
    entities: list[EntityDefinition],
    provider,
    *,
    instructions: str = "",
    output_configuration: OutputConfiguration | None = None,
) -> list[DatasetAnnotationResult]:
    input_root = Path(input_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    output_configuration = output_configuration or OutputConfiguration(
        include_rationale=True,
        include_guideline_section=True,
    )

    results: list[DatasetAnnotationResult] = []
    for input_path in sorted(input_root.glob("*.json")):
        raw_document = json.loads(input_path.read_text(encoding="utf-8"))
        annotation_result = annotate_with_guidelines(
            text=raw_document["text"],
            guidelines=guidelines,
            entities=entities,
            provider=provider,
            instructions=instructions,
            output_configuration=output_configuration,
        )
        output_document = annotations_to_pubannotation(
            text=raw_document["text"],
            annotations=annotation_result.annotations,
            sourcedb=raw_document.get("sourcedb", "unknown"),
            sourceid=raw_document.get("sourceid", input_path.stem),
            project=raw_document.get("project"),
            target=raw_document.get("target"),
        )
        (output_root / input_path.name).write_text(
            json.dumps(output_document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        results.append(
            DatasetAnnotationResult(
                filename=input_path.name,
                sourceid=output_document["sourceid"],
                output_document=output_document,
            )
        )
    return results
