"""Break down selected items.csv rows of the loop08/loop04 Modifier pair by category and gold label. Offline, 2026-11-08.
Same join as aggregate_items.py (basis quotes only). Output columns: prefix, (item, category, gold_label, pred_label), count, sum of d.
Usage: python -I item_gold_labels.py > ../outputs/overall_view/item_gold_labels_output.txt
"""
import csv, json, collections, sys
from pathlib import Path
ROOT = Path(r"H:/Git/research/修論/llm-guideline-moderation-source")
PILOT = ROOT/"nodes/2026-11-06_seminar/error-analysis/outputs/bar_clause_pilot"; BASE = PILOT/"codex_locate"
def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if p.exists() else []
for prefix, want in [("top4_loop08", {"top4_loop08_013","top4_loop08_015","top4_loop08_057"}), ("top4_loop04", {"top4_loop04_040"})]:
    inst = list(csv.DictReader(open(PILOT/f"{prefix}_instances.csv", encoding="utf-8")))
    loc = {r["pred_id"]: r for f in (f"{prefix}_locate.jsonl", f"{prefix}_locate_haiku.jsonl") for r in jl(BASE/"outputs"/f)}
    entries = {(e["line_start"], e["line_end"], e["quote"], e["condition_words"]): e["entry_id"] for e in jl(BASE/"merge_inputs"/f"{prefix}_basis_entries.jsonl")}
    emap = {m["entry_id"]: m for m in json.loads((BASE/"merge_outputs"/f"{prefix}_entry_map.json").read_text(encoding="utf-8"))}
    acc = collections.defaultdict(lambda: [0, 0.0])
    for r in inst:
        if not r["target_pred_label"]: continue
        rec = loc.get(f"{prefix}|{r['doc']}|{r['target_pred_start']}|{r['target_pred_end']}|{r['target_pred_label']}")
        if rec is None: continue
        its = {emap[entries[(q["line_start"], q["line_end"], q["quote"], q["condition_words"])]]["item_id"] for q in rec["quotes"] if q["role"] == "basis"}
        for i in its & want:
            k = (i, r["category"], r["gold_label"] or "-", r["target_pred_label"])
            acc[k][0] += 1; acc[k][1] += float(r["d"])
    for k in sorted(acc): print(prefix, k, acc[k][0], round(acc[k][1], 4))
