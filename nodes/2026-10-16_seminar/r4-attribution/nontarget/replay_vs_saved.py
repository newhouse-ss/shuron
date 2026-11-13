"""Offline: do today's replays look like extra draws of the saved 08/02 annotations?

For each (guideline, document) replayed on 10/14 or 10/15 with the saved R3 or R4 guideline,
count predictions (start, end, label) that differ between
  a) each replay and the saved 08/02 prediction for that guideline, and
  b) each pair of replays.
If a) is about as large as b), the saved run behaves like one more draw from the same process.
No API calls.
"""
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
snap = json.loads((RUN / "rounds/iteration_04/snapshot.json").read_text(encoding="utf-8"))
saved = {"R3": {f["filename"]: f for f in snap["diagnostics_before"]["files"]},
         "R4": {f["filename"]: f for f in snap["diagnostics_after"]["files"]}}
key = lambda xs: {(x["start"], x["end"], x["label"]) for x in xs}

groups = {}
for unit_dir, cond_map in ((ROOT / "nodes/2026-10-16_seminar/r4-attribution/isolation/units", {"c1_R3": "R3", "c3_R4": "R4"}),
                           (ROOT / "nodes/2026-10-16_seminar/r4-attribution/nontarget/units", {"c1_R3": "R3", "c3_R4": "R4"})):
    for p in sorted(unit_dir.glob("*.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        if u.get("status") != "ok" or u["condition"] not in cond_map:
            continue
        g = cond_map[u["condition"]]
        pred = key({"start": a["start"], "end": a["end"], "label": a["entity"]} for a in u["annotations"])
        groups.setdefault((g, u["doc"]), []).append(pred)

print(f"{'guideline':9s} {'doc':14s} n  replay-vs-saved diffs        replay-vs-replay diffs")
for (g, doc), preds in sorted(groups.items()):
    s = key(saved[g][doc]["study_denotations"])
    vs_saved = [len(p ^ s) for p in preds]
    pairs = [len(a ^ b) for a, b in itertools.combinations(preds, 2)]
    print(f"{g:9s} {doc:14s} {len(preds)}  {str(vs_saved):28s} {pairs}")
    for p in preds:
        extra = sorted(p - s)
        missing = sorted(s - p)
        if extra or missing:
            print(f"{'':27s} replay-only {extra}  saved-only {missing}")
