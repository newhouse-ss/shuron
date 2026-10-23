"""WITHDRAWN 2026-10-22: built on GPT-5.4 data; not used for any decision (see haiku_only_plan.py). Cost of the RP v4 step 2 reproduction on the main model chosen 2026-10-22: Claude Haiku 5.5, effort xhigh.

No API calls. Same design and call counts as todo-temp/deepseek-stability/full_reproduction_plan.py (E1 valid100
original guideline x10; E2 top-1 and E3 top-4 loops on dev10, finals annotated once on valid100; 4 rounds per
loop), priced for Haiku:

* Annotation calls at the measured mean of the 200 H_xhigh dev10 calls (Batch price). valid100 documents are
  priced like dev10 ones, as in the DeepSeek plan.
* Analysis calls (discrepancy, principle, rewrite) are not measured on any model. The estimate prices them like
  annotation calls; the upper bound uses the largest saved GPT-5.4 analysis prompt (characters counted as
  tokens) plus output at the 64,000-token cap.
* Batch price assumes every step is sent through the Message Batches API, i.e. the loops of a method run in
  lockstep and each step's calls go out as one batch. The standard API costs twice as much.
"""
import contextlib
import io
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "deepseek-stability"))

import full_reproduction_plan as frp  # noqa: E402
import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

ARM = "H_xhigh"


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        units = [u for u in rs.load_units(rh.UNITS) if u["arm"] == ARM]
    price = statistics.mean(rh.cost_jpy(u["usage"], True) for u in units)
    print(f"annotation call, {ARM}: JPY {price:.3f} at Batch price (mean of {len(units)} dev10 calls)")
    largest = max(len(p.read_text(encoding="utf-8")) for name in frp.GPT_LOOPS
                  for p in (frp.RUNS / name / "rounds").glob("iteration_*/*.txt") if p.name in frp.ANALYSIS_PROMPTS)
    worst = rh.cost_jpy({"input_tokens": largest, "output_tokens": rh.MAX_TOKENS}, True)
    print(f"analysis call upper bound: {largest:,} prompt tokens + {rh.MAX_TOKENS:,} output = JPY {worst:.2f} "
          f"at Batch price")

    for loops in (15, 10):
        rows = [("E1 valid100, original x10", 0, 1000)]
        for method, tag in (("top-1", "E2"), ("top-4", "E3")):
            analysis = frp.ROUNDS * frp.ANALYSIS_PER_ROUND[method]
            annotation = 10 + frp.ROUNDS * 10 + 100
            rows.append((f"{tag} {method} loops x{loops} ({analysis + annotation} calls per loop at "
                         f"{frp.ROUNDS} rounds)", loops * analysis, loops * annotation))
        print(f"\n== design with {loops} loops per method")
        total_a = total_n = 0
        for label, analysis, annotation in rows:
            total_a += analysis
            total_n += annotation
            print(f"  {label}: {analysis + annotation:,} calls, estimate JPY {(analysis + annotation) * price:,.0f}, "
                  f"upper JPY {annotation * price + analysis * worst:,.0f}")
        calls = total_a + total_n
        print(f"  total {calls:,} calls ({total_a:,} analysis); estimate JPY {calls * price:,.0f}; "
              f"upper JPY {total_n * price + total_a * worst:,.0f}; standard API doubles both")
    print("\n== other plan items")
    for method in ("top-1", "top-4"):
        analysis = frp.ROUNDS * frp.ANALYSIS_PER_ROUND[method]
        annotation = 10 + frp.ROUNDS * 10 + 100
        print(f"  one {method} loop incl. valid100 annotation of its final ({analysis + annotation} calls): estimate "
              f"JPY {(analysis + annotation) * price:,.0f}, upper JPY {annotation * price + analysis * worst:,.0f}")
    print(f"  test set evaluation (300 calls, as in RP v4): estimate JPY {300 * price:,.0f}")
    steps = 1 + frp.ROUNDS * 4 + 1
    print(f"\nsequential batch steps per method if the loops run in lockstep: {steps} (initial annotation; per round "
          f"3 analysis steps and 1 re-annotation; valid100 annotation of the finals). Observed batch durations so "
          f"far: 7 and 11 min (batch_state_*.json), not a guarantee.")


if __name__ == "__main__":
    main()
