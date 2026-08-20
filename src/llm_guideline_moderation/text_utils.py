from __future__ import annotations

import re

from .types import Annotation


def normalize_text(
    text: str,
    *,
    preserve_multiple_spaces: bool = True,
    preserve_leading_trailing_spaces: bool = True,
) -> str:
    if not text:
        return ""

    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00A0", " ")
        .replace("\u202F", " ")
        .replace("\u2007", " ")
        .replace("\u2060", " ")
    )
    normalized = re.sub(r"[\u200B-\u200D\uFEFF]", "", normalized)

    if not preserve_multiple_spaces:
        normalized = re.sub(r" +", " ", normalized)

    if not preserve_leading_trailing_spaces:
        normalized = normalized.strip()

    return normalized


def normalize_text_preserve_spacing(text: str) -> str:
    return normalize_text(
        text,
        preserve_multiple_spaces=True,
        preserve_leading_trailing_spaces=True,
    )


def align_annotations(normalized_text: str, annotations: list[Annotation]) -> list[Annotation]:
    return align_annotations_with_stats(normalized_text, annotations)["aligned"]


def align_annotations_with_stats(
    normalized_text: str,
    annotations: list[Annotation],
) -> dict[str, object]:
    aligned_annotations: list[Annotation] = []
    dropped = 0
    comparable_text = normalize_text_preserve_spacing(normalized_text)

    for annotation in annotations:
        normalized_annotation_text = normalize_text_preserve_spacing(annotation.text)
        if not normalized_annotation_text:
            dropped += 1
            continue

        # Pick the occurrence nearest to the supplied offset.
        #
        # This previously searched the window [start - 50, start + 50 + len] and
        # took str.find's leftmost hit. That is biased backwards: the window
        # opens 50 characters *before* the target, so whenever the same string
        # also occurs earlier inside it, the annotation was relocated onto that
        # earlier occurrence - and then discarded, because the annotation
        # belonging there had already claimed the span. Short repeated
        # abbreviations trigger it constantly (CRF, DM, ESRD, rat), and roughly
        # 4% of the gold annotations in every shipped dataset were lost or
        # silently moved even when the offsets handed in were already exact.
        #
        # Ranking by |candidate - annotation.start| removes the bias: a correct
        # offset wins at distance 0, and a wrong one still snaps to the closest
        # real occurrence. This is the rule the fallback below already applied,
        # so it is now the only rule rather than the second attempt.
        all_matches: list[int] = []
        idx = comparable_text.find(normalized_annotation_text)
        while idx != -1:
            all_matches.append(idx)
            idx = comparable_text.find(normalized_annotation_text, idx + 1)

        if all_matches:
            found_index = min(
                all_matches,
                key=lambda current: abs(current - annotation.start),
            )
        else:
            found_index = -1
            fuzzy = find_fuzzy_match(
                comparable_text,
                normalized_annotation_text,
                annotation.start,
            )
            if fuzzy["start"] != -1:
                new_start = int(fuzzy["start"])
                new_end = int(fuzzy["end"])
                if not any(new_start < existing.end and new_end > existing.start for existing in aligned_annotations):
                    aligned_annotations.append(
                        Annotation(
                            start=new_start,
                            end=new_end,
                            text=comparable_text[new_start:new_end],
                            entity=annotation.entity,
                            rationale=annotation.rationale,
                            guideline_section=annotation.guideline_section,
                            uncertain=annotation.uncertain,
                            raw_entity=annotation.raw_entity,
                        )
                    )
                else:
                    dropped += 1
                continue

        if found_index != -1:
            new_start = found_index
            new_end = new_start + len(normalized_annotation_text)
            if not any(new_start < existing.end and new_end > existing.start for existing in aligned_annotations):
                aligned_annotations.append(
                    Annotation(
                        start=new_start,
                        end=new_end,
                        text=normalized_annotation_text,
                        entity=annotation.entity,
                        rationale=annotation.rationale,
                        guideline_section=annotation.guideline_section,
                        uncertain=annotation.uncertain,
                        raw_entity=annotation.raw_entity,
                    )
                )
            else:
                dropped += 1
        else:
            dropped += 1

    return {
        "aligned": sorted(aligned_annotations, key=lambda item: item.start),
        "dropped": dropped,
    }


def find_fuzzy_match(source: str, pattern: str, start_hint: int) -> dict[str, int]:
    def strip_whitespace(text: str) -> tuple[str, list[int]]:
        stripped_chars: list[str] = []
        indices: list[int] = []
        for index, char in enumerate(text):
            if not char.isspace():
                stripped_chars.append(char)
                indices.append(index)
        return "".join(stripped_chars), indices

    stripped_source, source_indices = strip_whitespace(source)
    stripped_pattern, _ = strip_whitespace(pattern)

    if not stripped_pattern:
        return {"start": -1, "end": -1}

    hint_index = 0
    while hint_index < len(source_indices) and source_indices[hint_index] < start_hint:
        hint_index += 1

    candidates: list[int] = []
    idx = stripped_source.find(stripped_pattern)
    while idx != -1:
        candidates.append(idx)
        idx = stripped_source.find(stripped_pattern, idx + 1)

    if not candidates:
        return {"start": -1, "end": -1}

    best_start = min(candidates, key=lambda current: abs(current - hint_index))
    start_original = source_indices[best_start]
    end_original = source_indices[best_start + len(stripped_pattern) - 1] + 1
    return {"start": start_original, "end": end_original}
