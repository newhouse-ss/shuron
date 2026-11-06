"""Write Phase 2 tables from explicit manually reviewed item assignments.

This utility does not infer shared conditions, actions, overlap, or restatements.
"""

import argparse
import csv
import json
from pathlib import Path

from check_quotes import check_records, read_jsonl


BASE = Path(__file__).resolve().parents[2] / "outputs" / "bar_clause_pilot" / "codex_locate"
ITEM_FIELDS = ["item_id", "line_start", "line_end", "item_text", "condition_words", "action", "parent_item", "restates"]
QUOTE_FIELDS = ["line_start", "line_end", "quote", "condition_words", "item_id"]


def collect_entries(records):
    entries = []
    seen = set()
    for record in records:
        for quote in record["quotes"]:
            if quote["role"] != "basis":
                continue
            entry = {field: quote[field] for field in QUOTE_FIELDS[:-1]}
            key = tuple(entry.values())
            if key not in seen:
                seen.add(key)
                entries.append({"entry_id": len(entries) + 1, **entry})
    return entries


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export-entries", action="store_true")
    mode.add_argument("--decisions", type=Path)
    args = parser.parse_args()
    prefix = args.prefix
    records = read_jsonl(BASE / "outputs" / f"{prefix}_locate.jsonl")
    inputs = read_jsonl(BASE / "inputs" / f"{prefix}_predictions.jsonl")
    lines = (BASE / "inputs" / "guidelines" / f"{prefix}.txt").read_text(encoding="utf-8").splitlines()
    errors = check_records(inputs, records, lines, "pred_id")
    if errors:
        raise ValueError("Phase 1 must pass a complete check before Phase 2: " + repr(errors))
    entries = collect_entries(records)
    if args.export_entries:
        path = BASE / "outputs" / f"{prefix}_distinct_basis.json"
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return
    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    assert decisions["prefix"] == prefix
    assignments = {}
    items = []
    ids = {item["item_id"] for item in decisions["items"]}
    assert len(ids) == len(decisions["items"]), "Duplicate item IDs"
    for item in decisions["items"]:
        for entry_id in item["entry_ids"]:
            assert 1 <= entry_id <= len(entries), entry_id
            assert entry_id not in assignments, ("Entry assigned twice", entry_id)
            assignments[entry_id] = item["item_id"]
        assert not item["parent_item"] or item["parent_item"] in ids
        assert all(identifier in ids for identifier in item["restates"].split(";") if identifier)
        items.append({field: item[field] for field in ITEM_FIELDS})
    assert set(assignments) == set(range(1, len(entries) + 1)), "Every basis entry must be assigned exactly once"
    mappings = [{**{field: entry[field] for field in QUOTE_FIELDS[:-1]}, "item_id": assignments[entry["entry_id"]]} for entry in entries]
    write_csv(BASE / "outputs" / f"{prefix}_items.csv", ITEM_FIELDS, items)
    write_csv(BASE / "outputs" / f"{prefix}_quote_to_item.csv", QUOTE_FIELDS, mappings)
    progress_path = BASE / "outputs" / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    progress["guidelines"][prefix]["phase2_complete"] = True
    progress["guidelines"][prefix]["items"] = len(items)
    pending = [name for name in progress["order"] if not progress["guidelines"].get(name, {}).get("phase2_complete")]
    if pending:
        progress["current_guideline"] = pending[0]
        progress["next_input_row"] = progress["guidelines"].get(pending[0], {}).get("written", 0) + 1
    else:
        progress["phase"] = 3
        progress["current_guideline"] = None
        progress["next_input_row"] = None
    temporary = progress_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(progress_path)
    print(f"PASS {prefix}: {len(entries)} basis entries manually assigned to {len(items)} items")


if __name__ == "__main__":
    main()
