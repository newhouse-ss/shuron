"""Serialize explicitly human/model-read locating decisions without text matching."""

import argparse
import hashlib
import json
from pathlib import Path


BASE = Path("nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot/codex_locate")
ORDER = ["top4_loop07", "top4_loop01", "top4_loop02", "top4_loop04", "top4_loop05", "top4_loop06", "top4_loop08", "top4_loop09", "top4_loop10", "top1_loop05", "top1_loop07"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    prefix = batch["prefix"]
    source = BASE / "inputs" / f"{prefix}_predictions.jsonl"
    inputs = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    output = BASE / "outputs" / f"{prefix}_locate.jsonl"
    existing = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()] if output.exists() else []
    done = {row["pred_id"] for row in existing}
    pending = [(i, row) for i, row in enumerate(inputs, 1) if row["pred_id"] not in done]
    expected = [i for i, _ in pending[:20]]
    assert [row["row"] for row in batch["rows"]] == expected, ("Batch must be next 20 input rows", expected)
    quotes = batch["quotes"]
    result = []
    for decision in batch["rows"]:
        prediction = inputs[decision["row"] - 1]
        # Citation indices are explicit manual assignments, never inferred from text.
        fragments = [fragment.strip() for fragment in prediction["guideline_section"].split(";")]
        entries = []
        for reference in decision.get("refs", []):
            key, citation_index, *role = reference
            quote = dict(quotes[key])
            quote["cited_as"] = fragments[citation_index] if citation_index is not None else ""
            quote["role"] = role[0] if role else "basis"
            entries.append(quote)
        note = decision.get("note", "")
        assert len(note.split()) <= 20, note
        result.append({"pred_id": prediction["pred_id"], "status": decision.get("status", "located"), "quotes": entries, "note": note})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8", newline="\n") as stream:
        for row in result:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    progress_path = BASE / "outputs" / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {"order": ORDER, "phase": 1, "guidelines": {}}
    all_rows = existing + result
    progress["guidelines"][prefix] = {
        "total": len(inputs), "written": len(all_rows),
        "located": sum(row["status"] == "located" for row in all_rows),
        "cannot_locate": sum(row["status"] == "cannot_locate" for row in all_rows),
        "batches": (len(all_rows) + 19) // 20,
        "phase1_complete": len(all_rows) == len(inputs), "phase2_complete": False,
        "last_pred_id": all_rows[-1]["pred_id"],
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    progress["current_guideline"] = prefix
    progress["next_input_row"] = len(all_rows) + 1
    temporary = progress_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(progress_path)
    print(json.dumps(progress["guidelines"][prefix], ensure_ascii=False))


if __name__ == "__main__":
    main()
