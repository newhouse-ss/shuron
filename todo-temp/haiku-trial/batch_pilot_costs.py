"""Measured cost and tokens of the 2026-10-22 batch pilot (one top-1 and one top-4 loop), from the saved replies.

Offline. Every billed reply in outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies is grouped by loop and
step (dev10 annotation, valid100 annotation, discrepancy, principle, rewrite). A reply counts as "used" when the
loop's calls.json lists it; the others were billed but not used: the top-4 rewrites cut off at the first cap
(64000) and the top-4 analysis replies of the first attempt, which the restart could not replay (its prompts
changed with the hash seed). Also printed: each rewrite's tokens and the length of the guideline it wrote.
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_haiku as rh  # noqa: E402

ROOT = HERE.parents[1]
RUNS = ROOT / "outputs/ncbi_disease"
REPLIES = RUNS / "20261022_haiku-xhigh_batchqueue/replies"
VALID_BATCHES = {"msgbatch_01FvhHKev44AWKpfh6hEcK28", "msgbatch_01R1jVu59HiTZP3HXmZqRfZ4"}  # batch_loops_run.log
LOOPS = {"topk1L01": "20261022_haiku-xhigh_topk1_loop01", "topk4L01": "20261022_haiku-xhigh_topk4_loop01"}

used = {cid for run in LOOPS.values()
        for cid in (c["custom_id"] for c in json.loads((RUNS / run / "calls.json").read_text(encoding="utf-8")))}
rows = [json.loads(p.read_text(encoding="utf-8")) for p in REPLIES.glob("*.json")]
groups: dict[tuple, list] = {}
rewrites = []
for r in rows:
    meta, msg = r["meta"], r["message"]
    task = meta["task"].rstrip("_1234")
    if task == "annotate_with_guidelines":
        task = "valid100 annotation" if r["batch_id"] in VALID_BATCHES else "dev10 annotation"
    state = "used" if r["custom_id"] in used else ("cut off" if msg["stop_reason"] == "max_tokens" else "not used")
    groups.setdefault((meta["loop"], task, state), []).append(msg["usage"])
    if task == "refine_guidelines":
        text = "".join(b.get("text", "") for b in msg["content"] if b["type"] == "text")
        rewrites.append((meta["loop"], r["saved_utc"], state, msg["usage"], len(text)))

total = {"used": 0.0, "cut off": 0.0, "not used": 0.0}
for key in sorted(groups):
    usage = groups[key]
    cost = [rh.cost_jpy(u, True) for u in usage]
    total[key[2]] += sum(cost)
    print(f"{key[0]} {key[1]} [{key[2]}]: {len(usage)} calls, JPY {sum(cost):.2f} (mean {statistics.mean(cost):.3f}), "
          f"input tokens mean {statistics.mean(u['input_tokens'] for u in usage):,.0f}, output tokens mean "
          f"{statistics.mean(u['output_tokens'] for u in usage):,.0f}, max {max(u['output_tokens'] for u in usage):,}")
for loop in LOOPS:
    cost = sum(rh.cost_jpy(u, True) for (lp, _, state), us in groups.items() if lp == loop and state == "used"
               for u in us)
    print(f"{loop}: used replies cost JPY {cost:.2f}")
print(f"total {len(rows)} billed replies, JPY {sum(total.values()):.2f} = USD "
      f"{sum(total.values()) / rh.rs.JPY_PER_USD:.2f}; used JPY {total['used']:.2f}, cut off JPY {total['cut off']:.2f}, "
      f"billed but not used JPY {total['not used']:.2f}")
print("\nrewrites in order: loop, state, input tokens, output tokens (thinking), guideline characters written")
for loop, saved, state, u, chars in sorted(rewrites, key=lambda x: (x[0], x[1])):
    print(f"  {loop} {saved} {state}: in {u['input_tokens']:,}, out {u['output_tokens']:,} "
          f"({u['output_tokens_details']['thinking_tokens']:,}), {chars:,} chars")
