"""Distinct basis entries per guideline, as input to the merge step (notes/20261106_merge_spec.md). Offline. 2026-11-06.

Reads the locate outputs (<prefix>_locate.jsonl, and <prefix>_locate_haiku.jsonl where it exists), keeps quotes with role
"basis", and groups identical (line_start, line_end, quote, condition_words). Writes one JSON line per distinct entry
with the number of predictions that used it and up to 3 cited_as examples. No gold labels or outcome differences are read.
Output: outputs/bar_clause_pilot/codex_locate/merge_inputs/<prefix>_basis_entries.jsonl and _summary.txt.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "todo-temp" / "error-analysis" / "outputs" / "bar_clause_pilot" / "codex_locate"
PREFIXES = ["top4_loop01", "top4_loop02", "top4_loop04", "top4_loop05", "top4_loop06", "top4_loop07", "top4_loop08",
            "top4_loop09", "top4_loop10", "top1_loop05", "top1_loop07"]

out_dir = BASE / "merge_inputs"
out_dir.mkdir(exist_ok=True)
lines = []
for prefix in PREFIXES:
    recs = []
    for f in (BASE / "outputs" / f"{prefix}_locate.jsonl", BASE / "outputs" / f"{prefix}_locate_haiku.jsonl"):
        if f.exists():
            recs += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    entries = {}
    for r in recs:
        for q in r["quotes"]:
            if q["role"] != "basis":
                continue
            k = (q["line_start"], q["line_end"], q["quote"], q["condition_words"])
            e = entries.setdefault(k, {"preds": set(), "cited": []})
            e["preds"].add(r["pred_id"])
            if q["cited_as"] and q["cited_as"] not in e["cited"] and len(e["cited"]) < 3:
                e["cited"].append(q["cited_as"])
    rows = []
    for i, (k, e) in enumerate(sorted(entries.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3], kv[0][2])), 1):
        rows.append({"entry_id": f"{prefix}_e{i:03d}", "line_start": k[0], "line_end": k[1], "quote": k[2],
                     "condition_words": k[3], "n_predictions": len(e["preds"]), "cited_as_examples": e["cited"]})
    with open(out_dir / f"{prefix}_basis_entries.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    lines.append(f"{prefix}: {len(recs)} predictions, {len(rows)} distinct basis entries, "
                 f"{len({(r['line_start'], r['line_end']) for r in rows})} distinct line ranges")
(out_dir / "_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
