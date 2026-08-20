from __future__ import annotations

from dataclasses import dataclass

from .types import Annotation


@dataclass(slots=True)
class PubAnnotationDocument:
    text: str
    sourcedb: str
    sourceid: str
    denotations: list[dict]
    project: str | None = None
    target: str | None = None


def annotations_to_pubannotation(
    text: str,
    annotations: list[Annotation],
    sourcedb: str,
    sourceid: str,
    project: str | None = None,
    target: str | None = None,
) -> dict:
    denotations = []
    for idx, annotation in enumerate(annotations, start=1):
        denotation = {
            "id": f"T{idx}",
            "span": {"begin": annotation.start, "end": annotation.end},
            "obj": annotation.entity,
        }
        denotations.append(denotation)

    document = {
        "text": text,
        "sourcedb": sourcedb,
        "sourceid": sourceid,
        "denotations": denotations,
    }
    if project:
        document["project"] = project
    if target:
        document["target"] = target
    return document


def pubannotation_to_annotations(document: dict) -> list[Annotation]:
    text = document["text"]
    annotations: list[Annotation] = []
    for denotation in document.get("denotations", []):
        begin = denotation["span"]["begin"]
        end = denotation["span"]["end"]
        entity = denotation["obj"]
        annotations.append(
            Annotation(
                start=begin,
                end=end,
                text=text[begin:end],
                entity=entity,
            )
        )
    return annotations
