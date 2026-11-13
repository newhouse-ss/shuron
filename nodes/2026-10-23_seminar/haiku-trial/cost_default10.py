"""Cost of the RP v4 step 2 reproduction with the default counts: E1 x10, 10 top-1 loops, 10 top-4 loops.

No API calls, no GPT-5.4 data. Inputs:
* Measured: Haiku xhigh price per annotation call, mean of the 200 dev10 calls at Batch price.
* From the code: a loop annotates the 10 dev10 documents, then per round makes the analysis calls (top-1: 3,
  iterative.py; top-4: 4 x 2 + 1 = 9, reproduction/moderate_topk.py) and 10 re-annotations, and stops at the
  first round that does not raise dev10 F1, at F1 0.9, or after 20 rounds (SAFE_MAX_ITERATIONS). Each final
  guideline is annotated once on valid100 (100 calls).
* Not measured, so shown as scenarios: the number of rounds per loop. Analysis calls are priced like annotation
  calls; the bound prices them at a 100,000-token prompt plus the 64,000-token output cap.
* valid100 calls are priced like dev10 calls.
"""
import contextlib
import io
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

E1_RUNS = 10
LOOPS = 10
ANALYSIS = {"top-1": 3, "top-4": 9}
ROUND_SCENARIOS = (1, 2, 3, 5, 10, 20)


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        units = [u for u in rs.load_units(rh.UNITS) if u["arm"] == "H_xhigh"]
    price = statistics.mean(rh.cost_jpy(u["usage"], True) for u in units)
    bound = rh.cost_jpy({"input_tokens": rh.PROMPT_CARD_LIMIT, "output_tokens": rh.MAX_TOKENS}, True)
    print(f"annotation call JPY {price:.3f} (measured, {len(units)} calls); analysis call bound JPY {bound:.2f}")
    e1_calls = E1_RUNS * 100
    print(f"E1 x{E1_RUNS}: {e1_calls:,} calls, JPY {e1_calls * price:,.0f}")
    print(f"\nrounds per loop | top-1 x{LOOPS} | top-4 x{LOOPS} | total with E1: calls, estimate, bound")
    for rounds in ROUND_SCENARIOS:
        cells, calls, analysis_calls = [], e1_calls, 0
        for method, per_round in ANALYSIS.items():
            a = LOOPS * rounds * per_round
            n = LOOPS * (10 + rounds * 10 + 100)
            calls += a + n
            analysis_calls += a
            cells.append(f"{a + n:,} calls JPY {(a + n) * price:,.0f}")
        estimate = calls * price
        upper = (calls - analysis_calls) * price + analysis_calls * bound
        print(f"{rounds:>2} | {cells[0]} | {cells[1]} | {calls:,} calls, JPY {estimate:,.0f}, at most JPY {upper:,.0f}")
    print(f"\ntest set evaluation: 300 calls, JPY {300 * price:,.0f}")


if __name__ == "__main__":
    main()
