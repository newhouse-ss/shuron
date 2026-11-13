"""Frozen inputs, prompts and parsers for the two-step pilot. No network on import."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import random
import shutil
import sys
import uuid
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
NODE = Path(__file__).resolve().parents[2]
for directory in (ROOT / "src", ROOT / "reproduction"):
    sys.path.insert(0, str(directory))

import haiku_batch_loops as hb  # noqa: E402
from llm_guideline_moderation.pipeline import (  # noqa: E402
    _entity_schema_text, annotate_with_guidelines, normalize_entity_labels,
)
from llm_guideline_moderation.prompt_utils import generate_schema_parts  # noqa: E402
from llm_guideline_moderation.prompts import render_prompt  # noqa: E402
from llm_guideline_moderation.text_utils import align_annotations  # noqa: E402
from llm_guideline_moderation.types import Annotation, EntityDefinition  # noqa: E402

SEED = 20261113
RUNS = (1, 2)
ARMS = ("S", "S+", "T")
TRAIN = ROOT / "data/datasets/ncbi_disease/train"
TASK = "annotate_with_guidelines"
SYSTEM = inspect.signature(annotate_with_guidelines).parameters["system_instruction"].default
S_PLUS = 'Annotate every span that could be a disease mention under the guidelines below, in any role. If the guidelines say a span should not be annotated, still return it and cite the section that excludes it. When a span is a disease mention only under some reading, include it. Give each span the type it would otherwise have, and set "excluded" to "yes" for spans the guidelines say should not be annotated and "no" otherwise.'
FIND = 'Annotate every span that could be a disease mention under the guidelines below, in any role. If the guidelines say a span should not be annotated, still return it and cite the section that excludes it. When a span is a disease mention only under some reading, include it. Do not give a type in this step.'
TYPE = "You are given the text, the guidelines and a numbered list of candidate spans. Decide each candidate exactly once: give its type from the entity schema, or NONE if the guidelines say it should not be annotated, and cite the guideline section. Keep each candidate's span as given and do not add spans."


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    """Atomic checkpoints, including a complete document after each unit of work."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def temporary_directory(parent: Path, prefix: str):
    """Inherit workspace ACLs on Windows and restrict cleanup to the named parent."""
    parent = parent.resolve()
    path = parent / f"{prefix}{uuid.uuid4().hex[:12]}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        resolved = path.resolve()
        if resolved.parent != parent:
            raise ValueError(f"temporary cleanup target escaped its parent: {resolved}")
        shutil.rmtree(resolved)


def manifest() -> dict:
    # Filter names before opening any training document. Held-out content is never read.
    held = read_json(ROOT / "reproduction/test_splits/ncbi_disease_heldout50.json")
    dev = set(read_json(ROOT / "reproduction/dev_splits/ncbi_disease_dev50.json")["documents"])
    excluded = dev | set(held["documents"]) | set(held["excluded_biored"])
    names = sorted(p.name for p in TRAIN.glob("*.json") if p.name not in excluded)
    assert len(names) == 487, f"expected 487 pool documents, got {len(names)}"
    order = random.Random(SEED).sample(names, len(names))
    return {"seed": SEED, "pool_size": len(names), "pool_names": names,
            "pool_sha256": sha("\n".join(names)), "pool_hash_encoding": "UTF-8, sorted filenames joined by LF, no trailing LF",
            "reserved_documents": order[:100], "pilot_documents": order[100:300],
            "runs": list(RUNS), "arms": list(ARMS)}


def load_inputs():
    guideline = hb.GUIDELINES.read_text(encoding="utf-8")
    assert sha(guideline).startswith(hb.rh.rs.GUIDELINE_SHA256_PREFIX), "guideline differs from the Haiku trial's"
    rows = read_json(hb.ENTITY_SCHEMA)
    entities = [EntityDefinition(name=row) if isinstance(row, str) else EntityDefinition(**row) for row in rows]
    return guideline, entities


def field_text(step: str) -> str:
    original, _ = generate_schema_parts(hb.CONFIG)
    if step == "S":
        return original
    if step == "S+":
        return original[:-2] + ',\n  "excluded": string\n}'
    if step == "find":
        return original.replace('  "entity": string,\n', "")
    if step == "type":
        return '{\n  "id": integer,\n  "entity": string,\n  "rationale": string,\n  "guideline_section": string\n}'
    raise ValueError(step)


def output_schema(step: str, entities) -> dict:
    # Keep the original S schema byte-identical, including its unconstrained entity string.
    if step == "S":
        return hb.make_template().json_schemas[TASK]
    properties = {}
    for field in field_text(step).strip("{}\n ").split(","):
        key, kind = field.split(":")
        properties[key.strip().strip('"')] = {"type": kind.strip()}
    if step == "type":
        properties["entity"]["enum"] = [e.name for e in entities] + ["NONE"]
    if "excluded" in properties:
        properties["excluded"]["enum"] = ["yes", "no"]
    key = "decisions" if step == "type" else "annotations"
    item = {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    return {"type": "object", "properties": {key: {"type": "array", "items": item}},
            "required": [key], "additionalProperties": False}


def prompt(step: str, text: str, guideline: str, entities, candidates=None) -> str:
    _, rationale = generate_schema_parts(hb.CONFIG)
    if step != "type":
        return render_prompt(TASK, system_instruction=SYSTEM, entity_schema=_entity_schema_text(entities),
                             instructions={"S": "Follow the provided guidelines exactly.", "S+": S_PLUS, "find": FIND}[step],
                             json_schema=field_text(step), rationale_instruction=rationale,
                             guidelines=guideline or "(no guidelines provided)", input_text=text)
    numbered = [{"id": i, "start": a.start, "end": a.end, "text": a.text}
                for i, a in enumerate(candidates, 1)]
    # Same system instruction, entity schema, guideline and text blocks as the existing template.
    return f'''{SYSTEM}

**ENTITY SCHEMA:**
{_entity_schema_text(entities)}

**HIGH-LEVEL INSTRUCTIONS:**
{TYPE}

**ANNOTATION RULES:**
- Output MUST be a valid JSON object with a single key "decisions".
- "decisions" MUST be an array of objects following this JSON schema:
  {field_text("type")}
- Every decision MUST include a meaningful "rationale" and cite the corresponding "guideline_section".

**ANNOTATION GUIDELINES:**
{guideline or "(no guidelines provided)"}

**TEXT TO ANNOTATE:**
---
{text}
---

**CANDIDATE SPANS:**
{json.dumps(numbered, ensure_ascii=False, indent=2)}

Provide your response as a single JSON object.'''


def parse_annotations(step: str, raw: dict, text: str, entities) -> tuple[list, list]:
    """Use the existing alignment in its original order, including overlap removal."""
    annotations = []
    for row in raw["annotations"]:
        row = dict(row)
        if step == "find":
            row["entity"] = "Candidate"
        excluded = row.pop("excluded", "no")
        if step == "S+" and excluded not in ("yes", "no"):
            raise ValueError(f"invalid excluded value: {excluded!r}")
        # raw_entity survives alignment and retains the exclusion flag for the matching candidate.
        if step == "S+":
            row["raw_entity"] = excluded
        annotations.append(Annotation(**row))
    aligned = normalize_entity_labels(align_annotations(text, annotations), entities)
    track1 = [a for a in aligned if a.raw_entity == "no"] if step == "S+" else aligned
    return track1, aligned


def type_candidates(candidates: list, raw: dict, entities) -> tuple[list, list, int]:
    labels = {e.name for e in entities}
    decisions = {}
    for decision in raw["decisions"]:
        ident = decision["id"]
        if type(ident) is int and 1 <= ident <= len(candidates):
            decisions.setdefault(ident, decision)  # first repeated id wins; unknown ids ignored
    track1, track2, undecided = [], [], 0
    for ident, candidate in enumerate(candidates, 1):
        decision = decisions.get(ident)
        label = decision.get("entity") if decision else None
        if label not in labels and label != "NONE":
            undecided += 1
        annotation = replace(candidate, entity=label if label in labels else "Candidate",
                             rationale=decision.get("rationale") if decision else candidate.rationale,
                             guideline_section=decision.get("guideline_section") if decision else candidate.guideline_section)
        track2.append(annotation)
        if label in labels:
            track1.append(annotation)
    return track1, track2, undecided
