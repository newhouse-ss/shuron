"""Reproduction sizing from Haiku measurements, the loop's definition and plain statistics only. No API calls.

No GPT-5.4 number enters anything here (the earlier plan_counts_haiku.py, plan_adaptive_haiku.py and
plan_cost_haiku.py used GPT-5.4 valid100 SDs, GPT-5.4 round counts and GPT-5.4 prompt sizes; withdrawn
2026-10-22). Inputs:

* Haiku: the 200 H_xhigh dev10 calls (price per annotation call, dev10 F1 of the 20 repeats).
* Loop definition: 10 dev10 annotations to start; per round the analysis calls (top-1: discrepancy, principle,
  rewrite = 3; top-4: 4 x 2 + 1 = 9) and 10 re-annotations; the final guideline annotated once on valid100
  (100 calls). A loop stops at the first round that does not raise dev10 F1, at F1 0.9, or after 20 rounds.
* Price bounds: an analysis call costs at most a 100,000-token prompt (the limit of the lower rate card) plus
  output at the 64,000-token cap, at Batch price. valid100 documents are priced like dev10 ones.
* Statistics: how far a measured SD can be from the true one, from simulated normal samples (no model data).

1. Haiku's dev10 noise and how often a rerun of an unchanged guideline scores strictly higher (the share of
   ordered repeat pairs), i.e. how often noise alone lets a loop continue.
2. Precision of a measured SD: E1 (n runs, n-1 df) and loops (n per method, pooled within methods, 2(n-1) df).
3. Calls and cost per loop at 1 round and at the 20-round limit; stage-1 options.
"""
import contextlib
import io
import itertools
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fn_noise  # noqa: E402
import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

ANALYSIS_PER_ROUND = {"top-1": 3, "top-4": 9}
MAX_ROUNDS = 20


def upper_factor(df: int, rng: random.Random, sims: int = 40000) -> float:
    """97.5th percentile of sigma / s for a sample SD with df degrees of freedom."""
    ratios = sorted((sum(rng.gauss(0, 1) ** 2 for _ in range(df)) / df) ** 0.5 for _ in range(sims))
    return 1 / ratios[int(0.025 * sims)]


def loop_calls(method: str, rounds: int) -> tuple[int, int]:
    return rounds * ANALYSIS_PER_ROUND[method], 10 + rounds * 10 + 100


def main() -> None:
    _, documents, entities = rs.load_inputs()
    with contextlib.redirect_stdout(io.StringIO()):
        reps = fn_noise.sources(documents, entities)["Haiku H_xhigh"]
        units = [u for u in rs.load_units(rh.UNITS) if u["arm"] == "H_xhigh"]
    f1 = [r["f1"] for r in reps]
    pairs = list(itertools.permutations(f1, 2))
    higher = sum(b > a for a, b in pairs) / len(pairs)
    print(f"1. Haiku xhigh dev10 F1 SD {statistics.stdev(f1):.4f} over {len(f1)} repeats; an unchanged guideline "
          f"rerun scores strictly higher in {higher:.1%} of ordered pairs")

    rng = random.Random(20261022)
    print("\n2. a measured SD can understate the true one by up to (95%):")
    for n in (10, 15, 20):
        print(f"   E1 x{n} ({n - 1} df): {upper_factor(n - 1, rng):.2f}x")
    for n in (5, 8, 10):
        print(f"   {n} loops per method, pooled ({2 * (n - 1)} df): {upper_factor(2 * (n - 1), rng):.2f}x")

    price = statistics.mean(rh.cost_jpy(u["usage"], True) for u in units)
    bound = rh.cost_jpy({"input_tokens": rh.PROMPT_CARD_LIMIT, "output_tokens": rh.MAX_TOKENS}, True)
    print(f"\n3. annotation call JPY {price:.3f} (measured, Batch); analysis call at most JPY {bound:.2f} (bound)")
    low_high = {}
    for method in ANALYSIS_PER_ROUND:
        a1, n1 = loop_calls(method, 1)
        a20, n20 = loop_calls(method, MAX_ROUNDS)
        low = (a1 + n1) * price
        high = n20 * price + a20 * bound
        low_high[method] = (low, high)
        print(f"   one {method} loop: 1 round {a1 + n1} calls, JPY {low:,.0f} (analysis at annotation price); "
              f"{MAX_ROUNDS} rounds {a20 + n20} calls, at most JPY {high:,.0f}")
    for e1, loops in ((15, 5), (15, 8), (15, 10)):
        e1_cost = e1 * 100 * price
        low = e1_cost + loops * sum(v[0] for v in low_high.values())
        high = e1_cost + loops * sum(v[1] for v in low_high.values())
        calls_low = e1 * 100 + loops * sum(sum(loop_calls(m, 1)) for m in ANALYSIS_PER_ROUND)
        calls_high = e1 * 100 + loops * sum(sum(loop_calls(m, MAX_ROUNDS)) for m in ANALYSIS_PER_ROUND)
        print(f"   stage 1, E1 x{e1} + {loops} loops per method: {calls_low:,} calls, JPY {low:,.0f} if every loop "
              f"stops after 1 round; {calls_high:,} calls, at most JPY {high:,.0f} if every loop runs {MAX_ROUNDS} rounds")
    print(f"   E1 per valid100 run JPY {100 * price:,.0f}, x15 JPY {1500 * price:,.0f}; test set evaluation "
          f"(300 calls) JPY {300 * price:,.0f}")


if __name__ == "__main__":
    main()
