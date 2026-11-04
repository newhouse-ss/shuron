"""Cost of annotating the 100 validation documents twice more with each of the 11 changed guidelines (11/03, estimate only).

Offline, nothing is sent. Each changed guideline was run once on validation; its saved replies give the measured batch
price of every (guideline, document) call (run_haiku.cost_jpy, the function behind the recorded reproduction cost). Two more
runs cost twice that sum if the replies are about as long again. The spread across the 19 original-guideline runs shows
how much one run's total varies, which bounds how far a repeat may drift from the first run.
Writes rerun_cost_output.txt.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "todo-temp" / "haiku-trial"))
import run_haiku as rh  # noqa: E402  (price table and cost_jpy only)

REPEATS = 2
prov = [json.loads(l) for l in (HERE.parent / "outputs" / "20261030_rationale_audit" / "provenance_documents.jsonl").open(encoding="utf-8")]
per_run = defaultdict(float)
calls = defaultdict(int)
group = {}
for r in prov:
    rep = json.loads((ROOT / r["candidate_replies"][0]["reply_file"]).read_text(encoding="utf-8"))
    per_run[r["run"]] += rh.cost_jpy(rep["message"]["usage"], True)
    calls[r["run"]] += 1
    group[r["run"]] = r["guideline_group"]
changed = sorted(x for x in per_run if group[x] != "original")
orig = [x for x in per_run if group[x] == "original"]
assert len(changed) == 11 and len(orig) == 19 and all(calls[x] == 100 for x in per_run)
out = [f"Measured cost of one validation run (100 calls, batch price, JPY per USD {rh.rs.JPY_PER_USD})"]
for x in changed:
    out.append(f"   {x.replace('20261022_haiku-xhigh_', ''):<14} JPY {per_run[x]:7.1f}")
tot1 = sum(per_run[x] for x in changed)
o = [per_run[x] for x in orig]
out.append(f"   11 changed guidelines, one run each: JPY {tot1:,.1f}")
out.append(f"   original guideline, 19 runs: mean JPY {statistics.mean(o):.1f}, min {min(o):.1f}, max {max(o):.1f}"
           f" (max/min {max(o) / min(o):.2f})")
est = REPEATS * tot1
out.append(f"Two more runs per changed guideline: {REPEATS * 11 * 100:,} calls, about JPY {est:,.0f} (USD {est / rh.rs.JPY_PER_USD:.2f});"
           f" if every run cost as much, relative to its first run, as the dearest original run did relative to the cheapest:"
           f" JPY {est * max(o) / min(o):,.0f}")
(HERE.parent / "outputs" / "rerun_cost_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
