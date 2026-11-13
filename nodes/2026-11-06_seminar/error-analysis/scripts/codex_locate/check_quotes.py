"""Validate manually located guideline quotes without performing any locating.

Run from any directory:
    python check_quotes.py --prefix top4_loop07
    python check_quotes.py --prefix top4_loop07 --allow-partial
    python check_quotes.py --prefix original_lookup
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PREFIXES = (
    "top4_loop01", "top4_loop02", "top4_loop04", "top4_loop05",
    "top4_loop06", "top4_loop07", "top4_loop08", "top4_loop09",
    "top4_loop10", "top1_loop05", "top1_loop07", "original_lookup",
)
STATUSES = {"located", "cannot_locate"}
ROLES = {"basis", "ruled_out", "context"}


def normalize(text: str) -> str:
    """Apply only the spec's markup removal and whitespace normalization."""
    return " ".join(text.replace("*", "").replace("_", "").split())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSON objects and report a malformed row with its file location."""
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            records.append(record)
    return records


def check_records(
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    guideline_lines: list[str],
    id_field: str,
    *,
    allow_partial: bool = False,
) -> list[str]:
    """Return all structural and verbatim-check failures, with row references.

    Partial mode relaxes only the requirement that all input IDs are present.
    It still rejects duplicate IDs, unknown IDs and invalid completed records.
    """
    errors: list[str] = []
    expected: set[str] = set()
    input_by_id: dict[str, dict[str, Any]] = {}
    for row_number, record in enumerate(inputs, 1):
        identifier = record.get(id_field)
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"input row {row_number}: missing/non-string {id_field}")
        elif identifier in expected:
            errors.append(f"input row {row_number}: duplicate {id_field} {identifier!r}")
        else:
            expected.add(identifier)
            input_by_id[identifier] = record

    seen: set[str] = set()
    for row_number, record in enumerate(outputs, 1):
        identifier = record.get(id_field)
        location = f"output row {row_number} ({identifier!r})"
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{location}: missing/non-string {id_field}")
        else:
            if identifier in seen:
                errors.append(f"{location}: duplicate {id_field}")
            if identifier not in expected:
                errors.append(f"{location}: unknown {id_field}")
            seen.add(identifier)

        status = record.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{location}: invalid status {status!r}")
        note = record.get("note")
        if not isinstance(note, str):
            errors.append(f"{location}: note must be a string")
        else:
            if len(note.split()) > 20:
                errors.append(f"{location}: note exceeds 20 words")
            if status == "cannot_locate" and not note.strip():
                errors.append(f"{location}: cannot_locate requires a note")

        quotes = record.get("quotes")
        if not isinstance(quotes, list):
            errors.append(f"{location}: quotes must be a list")
            continue
        if status == "cannot_locate" and quotes:
            errors.append(f"{location}: cannot_locate requires empty quotes")
        if status == "located" and not quotes:
            errors.append(f"{location}: located requires at least one quote")

        for quote_number, entry in enumerate(quotes, 1):
            quote_location = f"{location}, quote {quote_number}"
            if not isinstance(entry, dict):
                errors.append(f"{quote_location}: expected a JSON object")
                continue
            quote = entry.get("quote")
            normalized_quote = normalize(quote) if isinstance(quote, str) else ""
            if not normalized_quote:
                errors.append(f"{quote_location}: quote must contain text")
            start, end = entry.get("line_start"), entry.get("line_end")
            if (
                type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= len(guideline_lines)
            ):
                errors.append(f"{quote_location}: invalid inclusive line range {start!r}:{end!r}")
            elif normalized_quote:
                source = normalize("\n".join(guideline_lines[start - 1:end]))
                if normalized_quote not in source:
                    errors.append(f"{quote_location}: quote absent from specified lines")

            condition = entry.get("condition_words")
            if not isinstance(condition, str):
                errors.append(f"{quote_location}: condition_words must be a string")
            elif normalize(condition) not in normalized_quote:
                errors.append(f"{quote_location}: condition_words absent from quote")
            role = entry.get("role")
            if not isinstance(role, str) or role not in ROLES:
                errors.append(f"{quote_location}: invalid role {role!r}")
            if not isinstance(entry.get("cited_as"), str):
                errors.append(f"{quote_location}: cited_as must be a string")

        # This checks only literal citation bookkeeping, never where a rule is located.
        if isinstance(identifier, str) and identifier in input_by_id:
            citation = input_by_id[identifier].get("guideline_section", "")
            fragments = [part.strip() for part in citation.split(";") if part.strip()]
            cited = {entry.get("cited_as") for entry in quotes if isinstance(entry, dict) and isinstance(entry.get("cited_as"), str)}
            if isinstance(note, str) and not note.strip():
                for fragment in fragments:
                    if fragment not in cited:
                        errors.append(f"{location}: citation fragment absent and no explanatory note: {fragment!r}")

    missing = expected - seen
    if missing and not allow_partial:
        errors.append(f"missing {len(missing)} input IDs: {', '.join(sorted(missing))}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, choices=PREFIXES)
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="allow missing input IDs while validating every supplied output row",
    )
    args = parser.parse_args(argv)
    base = Path(__file__).resolve().parents[2] / "outputs" / "bar_clause_pilot" / "codex_locate"
    id_field = "lookup_id" if args.prefix == "original_lookup" else "pred_id"
    guideline = "original" if args.prefix == "original_lookup" else args.prefix
    try:
        inputs = read_jsonl(base / "inputs" / f"{args.prefix}_predictions.jsonl")
        outputs = read_jsonl(base / "outputs" / f"{args.prefix}_locate.jsonl")
        guideline_lines = (base / "inputs" / "guidelines" / f"{guideline}.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        errors = check_records(
            inputs, outputs, guideline_lines, id_field,
            allow_partial=args.allow_partial,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL {args.prefix}: {exc}", file=sys.stderr)
        return 2
    if errors:
        print(f"FAIL {args.prefix}: {len(errors)} error(s)", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    mode = "partial" if args.allow_partial else "complete"
    print(f"PASS {args.prefix}: {len(outputs)}/{len(inputs)} records ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
