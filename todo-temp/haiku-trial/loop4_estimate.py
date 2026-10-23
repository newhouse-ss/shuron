"""Estimated cost of one loop with four accepted refinement rounds and no failed calls, plus 100 valid100 annotation
calls, for Haiku 5.5 xhigh (Batch) and DeepSeek V4.1 flash (thinking on), top-1 and top-4.

Offline. Inputs: the 2026-10-22 batch pilot replies and the two stability tests.
- Haiku top-4: initial dev10 annotation and rounds 1-4 of topk4L01 as billed (per round 4 discrepancy, 4 principle,
  1 rewrite, 10 dev10 annotations). valid100 with the round-4 guideline never ran: its input and output tokens per
  call are interpolated linearly in guideline length between the two valid100 runs that did (original guideline,
  round-6 top-4 guideline).
- Haiku top-1: only round 1 ran (its candidate was rejected). Assumed: rounds 2-4 repeat round 1's discrepancy,
  principle and rewrite calls, and every round adds as many guideline characters as round 1 did. dev10 and valid100
  annotation tokens are interpolated in guideline length from the measured runs.
- DeepSeek never ran a loop. Every call above is priced at DeepSeek's off-peak list price with Haiku's token counts
  and no cache hits; the calibration line compares this with what DeepSeek actually cost on the one step both ran.
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_haiku as rh  # noqa: E402

rs = rh.rs
ROOT = HERE.parents[1]
RUNS = ROOT / "outputs/ncbi_disease"
REPLIES = RUNS / "20261022_haiku-xhigh_batchqueue/replies"
ROUNDS = 4


def haiku(u):
    return rh.cost_jpy({"input_tokens": u[0], "output_tokens": u[1]}, True)


def deepseek(u):
    return rs.cost_jpy({"prompt_tokens": u[0], "prompt_cache_hit_tokens": 0, "completion_tokens": u[1]}, False)


def interp(points, x):
    points = sorted(points)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            w = (x - x0) / (x1 - x0)
            return tuple(a + w * (b - a) for a, b in zip(y0, y1))
    raise ValueError(x)


usage = {}
for p in REPLIES.glob("*.json"):
    r = json.loads(p.read_text(encoding="utf-8"))
    usage[r["custom_id"]] = (r["message"]["usage"]["input_tokens"], r["message"]["usage"]["output_tokens"])

steps, length = {}, {}  # (loop, round, step) -> [(in, out)]; (loop, round) -> guideline characters after the round
for name in ("topk1", "topk4"):
    run = RUNS / f"20261022_haiku-xhigh_{name}_loop01"
    length[name, 0] = len((run / "inputs/initial_guidelines.txt").read_text(encoding="utf-8"))
    for d in sorted((run / "rounds").iterdir()):
        length[name, int(d.name[-2:])] = len((d / "guidelines_candidate.txt").read_text(encoding="utf-8"))
    rnd, annotated, previous = 0, 0, None
    for c in json.loads((run / "calls.json").read_text(encoding="utf-8")):
        task = c["task"].rstrip("_1234")
        if task == "infer_discrepancy_patterns" and previous == "annotate_with_guidelines":
            rnd, annotated = rnd + 1, 0  # a round starts with its first discrepancy call
        previous = c["task"]
        if task == "annotate_with_guidelines":
            annotated += 1
            task = "dev10" if annotated <= 10 else "valid100"
        steps.setdefault((name, rnd, task), []).append(usage[c["custom_id"]])


def mean_tokens(calls):
    return tuple(statistics.mean(u[i] for u in calls) for i in (0, 1))


dev_points = [(length[n, r], mean_tokens(v)) for (n, r, t), v in steps.items() if t == "dev10"]
valid_points = [(length[n, r], mean_tokens(v)) for (n, r, t), v in steps.items() if t == "valid100"]

plans = {}
calls = steps[("topk4", 0, "dev10")][:]
for r in range(1, ROUNDS + 1):
    for t in ("infer_discrepancy_patterns", "generate_moderation_principle", "refine_guidelines", "dev10"):
        calls += steps[("topk4", r, t)]
calls += [interp(valid_points, length["topk4", ROUNDS])] * 100
plans["top-4"] = (calls, length["topk4", ROUNDS])

growth = length["topk1", 1] - length["topk1", 0]
calls = steps[("topk1", 0, "dev10")][:]
for r in range(1, ROUNDS + 1):
    for t in ("infer_discrepancy_patterns", "generate_moderation_principle", "refine_guidelines"):
        calls += steps[("topk1", 1, t)]
    calls += [interp(dev_points, length["topk1", 0] + r * growth)] * 10
top1_len = length["topk1", 0] + ROUNDS * growth
calls += [interp(valid_points, top1_len)] * 100
plans["top-1"] = (calls, top1_len)

print("measured guideline characters:", {f"{n} r{r}": v for (n, r), v in sorted(length.items())})
for name, (calls, final_len) in plans.items():
    h = sum(haiku(u) for u in calls)
    d = sum(deepseek(u) for u in calls)
    valid = calls[-100:]
    print(f"{name}, {ROUNDS} rounds, {len(calls)} calls, guideline after round {ROUNDS}: {final_len:,.0f} chars")
    print(f"  Haiku xhigh Batch: JPY {h:.2f} (valid100 part {sum(haiku(u) for u in valid):.2f}); "
          f"standard API JPY {2 * h:.2f}")
    print(f"  DeepSeek off-peak: JPY {d:.2f} (valid100 part {sum(deepseek(u) for u in valid):.2f}); "
          f"all at peak JPY {2 * d:.2f}")
    big = max(u[1] for u in calls)
    print(f"  largest output in one call: {big:,} tokens")

original_valid = steps[("topk1", 1, "valid100")]  # the pilot top-1 loop kept the original guideline
print(f"one valid100 run with the original guideline (pilot top-1 loop, {len(original_valid)} calls): Haiku xhigh "
      f"Batch JPY {sum(haiku(u) for u in original_valid):.2f}; DeepSeek off-peak JPY "
      f"{sum(deepseek(u) for u in original_valid):.2f}")

trial = [json.loads(p.read_text(encoding="utf-8")) for p in (HERE / "units").glob("H_xhigh__*.json")]
trial_tokens = [(t["usage"]["input_tokens"], t["usage"]["output_tokens"]) for t in trial if t.get("usage")]
ds_units = [json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "todo-temp/deepseek-stability/units").glob("B_on__*.json")]
print(f"calibration, dev10 annotation with the original guideline: Haiku xhigh tokens at DeepSeek off-peak price "
      f"JPY {statistics.mean(deepseek(u) for u in trial_tokens):.3f} per call ({len(trial_tokens)} calls); DeepSeek's "
      f"own off-peak cost JPY {statistics.mean(rs.cost_jpy(u['usage'], False) for u in ds_units):.3f} per call "
      f"({len(ds_units)} calls)")
