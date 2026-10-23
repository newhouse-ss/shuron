from __future__ import annotations

from ..types import LLMTaskName

JSON_MODE_SYSTEM_PROMPT = (
    "You are a helpful assistant that outputs valid json. "
    "Always respond with a JSON object."
)

JSON_TASKS: set[LLMTaskName] = {
    "annotate_with_guidelines",
    "moderate_annotations",
}


def is_json_task(task: LLMTaskName) -> bool:
    return task in JSON_TASKS


def annotation_json_schema(config) -> dict[str, object]:
    """JSON Schema for {"annotations": [...]}, built from the field list the prompt itself shows
    (prompt_utils.generate_schema_parts), so a schema-constrained reply asks for nothing the prompt does not."""
    from ..prompt_utils import generate_schema_parts

    field_text, _ = generate_schema_parts(config)
    json_types = {"integer": "integer", "string": "string"}
    properties: dict[str, object] = {}
    for line in field_text.strip("{}\n ").split(","):
        name, kind = line.split(":")
        properties[name.strip().strip('"')] = {"type": json_types[kind.strip()]}
    item = {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    return {"type": "object", "properties": {"annotations": {"type": "array", "items": item}},
            "required": ["annotations"], "additionalProperties": False}


def gemini_response_schema(task: LLMTaskName) -> dict[str, object] | None:
    annotation_properties: dict[str, object] = {
        "start": {"type": "INTEGER"},
        "end": {"type": "INTEGER"},
        "text": {"type": "STRING"},
        "entity": {"type": "STRING"},
        "rationale": {"type": "STRING"},
        "guideline_section": {"type": "STRING"},
        "uncertain": {"type": "BOOLEAN"},
        "raw_entity": {"type": "STRING"},
    }

    if task == "annotate_with_guidelines":
        return {
            "type": "OBJECT",
            "properties": {
                "annotations": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": annotation_properties,
                        "required": ["start", "end", "text", "entity"],
                    },
                }
            },
            "required": ["annotations"],
        }

    if task == "moderate_annotations":
        return {
            "type": "OBJECT",
            "properties": {
                "annotations": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": annotation_properties,
                        "required": ["start", "end", "text", "entity"],
                    },
                },
                "changes": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "action": {"type": "STRING"},
                            "reason": {"type": "STRING"},
                            "guideline_section": {"type": "STRING"},
                        },
                        "required": ["action", "reason", "guideline_section"],
                    },
                },
            },
            "required": ["annotations", "changes"],
        }

    return None
