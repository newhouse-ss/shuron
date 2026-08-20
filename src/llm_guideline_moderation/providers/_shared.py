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
