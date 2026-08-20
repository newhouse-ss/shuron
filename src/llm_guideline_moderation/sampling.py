from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from .pubannotation import pubannotation_to_annotations
from .types import Annotation


@dataclass(slots=True)
class SampledDocument:
    filename: str
    path: str
    text: str
    sourcedb: str
    sourceid: str
    gold_annotations: list[Annotation]
    raw_document: dict


def list_pubannotation_documents(directory: str | Path) -> list[Path]:
    root = Path(directory)
    return sorted(path for path in root.glob("*.json") if path.is_file())


def load_sampled_document(path: str | Path) -> SampledDocument:
    doc_path = Path(path)
    raw_document = json.loads(doc_path.read_text(encoding="utf-8"))
    return SampledDocument(
        filename=doc_path.name,
        path=str(doc_path),
        text=raw_document["text"],
        sourcedb=raw_document.get("sourcedb", "unknown"),
        sourceid=raw_document.get("sourceid", doc_path.stem),
        gold_annotations=pubannotation_to_annotations(raw_document),
        raw_document=raw_document,
    )


def sample_pubannotation_documents(
    directory: str | Path,
    sample_size: int,
    seed: int | None = None,
) -> list[SampledDocument]:
    candidates = list_pubannotation_documents(directory)
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if sample_size > len(candidates):
        raise ValueError(
            f"sample_size={sample_size} exceeds available documents ({len(candidates)}) in {directory}"
        )

    rng = random.Random(seed)
    selected_paths = sorted(rng.sample(candidates, sample_size), key=lambda path: path.name)
    return [load_sampled_document(path) for path in selected_paths]
