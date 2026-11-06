"""Validate the merge-step outputs of one guideline (notes/20261106_merge_spec.md). Offline, no API calls. 2026-11-06.

Usage: python -I validate_merge.py <prefix> [<prefix> ...]
Checks merge_outputs/<prefix>_items.json and _entry_map.json against merge_inputs/<prefix>_basis_entries.jsonl and the
guideline: every entry mapped exactly once; item ids unique and prefixed; parents exist; item_text verbatim in its lines
(after removing * and _ and collapsing whitespace); each entry's lines overlap its item's lines, or the item is the
parent (lead-in) of an item whose lines overlap; action_type values; label set only for label items. Prints PASS or the
problems (exit 1).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "todo-temp" / "error-analysis" / "outputs" / "bar_clause_pilot" / "codex_locate"
ACTIONS = {"label", "not_annotated", "span", "other"}


def norm(s):
    return re.sub(r"\s+", " ", s.replace("*", "").replace("_", "")).strip()


def check(prefix):
    p = []
    entries = {json.loads(l)["entry_id"]: json.loads(l) for l in
               (BASE / "merge_inputs" / f"{prefix}_basis_entries.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    lines = (BASE / "inputs" / "guidelines" / f"{prefix}.txt").read_text(encoding="utf-8").split("\n")
    try:
        items = json.loads((BASE / "merge_outputs" / f"{prefix}_items.json").read_text(encoding="utf-8"))
        emap = json.loads((BASE / "merge_outputs" / f"{prefix}_entry_map.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return [f"cannot read outputs: {e}"], None
    ids = [i.get("item_id") for i in items]
    if len(ids) != len(set(ids)):
        p.append("duplicate item_id")
    byid = {i["item_id"]: i for i in items}
    for it in items:
        need = {"item_id", "line_start", "line_end", "item_text", "action_type", "label", "parent_item"}
        if set(it) != need:
            p.append(f"{it.get('item_id')}: fields must be exactly {sorted(need)}")
            continue
        if not it["item_id"].startswith(prefix + "_"):
            p.append(f"{it['item_id']}: id must start with {prefix}_")
        if not (isinstance(it["line_start"], int) and isinstance(it["line_end"], int)
                and 1 <= it["line_start"] <= it["line_end"] <= len(lines)):
            p.append(f"{it['item_id']}: bad line range")
            continue
        if norm(it["item_text"]) not in norm("\n".join(lines[it["line_start"] - 1:it["line_end"]])) or not norm(it["item_text"]):
            p.append(f"{it['item_id']}: item_text not verbatim in its lines")
        if it["action_type"] not in ACTIONS:
            p.append(f"{it['item_id']}: bad action_type {it['action_type']!r}")
        if (it["action_type"] == "label") != bool(it["label"]):
            p.append(f"{it['item_id']}: label must be set exactly for label items")
        if it["parent_item"] and it["parent_item"] not in byid:
            p.append(f"{it['item_id']}: parent {it['parent_item']} not found")
    mapped = {}
    for m in emap:
        if set(m) != {"entry_id", "item_id", "branch"}:
            p.append(f"map row {m}: fields must be entry_id, item_id, branch")
            continue
        if m["entry_id"] in mapped:
            p.append(f"{m['entry_id']}: mapped twice")
        mapped[m["entry_id"]] = m
        if m["entry_id"] not in entries:
            p.append(f"{m['entry_id']}: not an input entry")
            continue
        if m["item_id"] not in byid:
            p.append(f"{m['entry_id']}: item {m['item_id']} not found")
            continue
        e, it = entries[m["entry_id"]], byid[m["item_id"]]
        overlap = lambda a: not (a["line_end"] < e["line_start"] or a["line_start"] > e["line_end"])
        children = [c for c in items if c.get("parent_item") == it["item_id"]]
        if not overlap(it) and not any(overlap(c) for c in children):
            p.append(f"{m['entry_id']}: lines {e['line_start']}-{e['line_end']} do not overlap item {it['item_id']}")
    missing = [k for k in entries if k not in mapped]
    if missing:
        p.append(f"{len(missing)} entries not mapped, e.g. {missing[:3]}")
    return p, (len(entries), len(items), sum(1 for m in emap if m.get("branch")))


def main():
    ok = True
    for prefix in sys.argv[1:]:
        p, stats = check(prefix)
        ok &= not p
        print(f"{prefix}: {'PASS' if not p else 'FAIL'}" + (f" | entries {stats[0]} items {stats[1]} entries with a branch {stats[2]}" if stats else ""))
        for x in p[:15]:
            print("   " + x)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
