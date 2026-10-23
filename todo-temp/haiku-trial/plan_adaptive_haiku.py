"""WITHDRAWN 2026-10-22: built on GPT-5.4 data; not used for any decision (see haiku_only_plan.py). Fixed 15, fixed 20, or 15 extended to 20 only when the measured loop spread is high? No API calls.

Balances reliability and cost for P2 (top-4 vs top-1 loops on valid100, Welch t test, two-sided alpha 0.025,
counted as detected when significant in the right direction). Loop scores are simulated as normal with the
planning SD of plan_counts_haiku.py (GPT-5.4 stand-in 0.0123 scaled by k point 1.00 or k upper 1.46).

Adaptive rule, fixed before any loop runs: after 15 loops per method, compute the pooled within-method SD of
the valid100 scores (each method around its own mean, so the gap between methods plays no part). If it is above
T, the SD at which 15 loops give an 80% chance to detect +0.015, run 5 more loops per method and test on all
20; otherwise test on the 15. T uses the normal approximation with the t critical value at 28 df.

Printed per true k and true gain (0, +0.015, +0.02): detection share (for gain 0, the share significant in
either direction, the false-alarm rate) of fixed 15, fixed 20 and adaptive; the adaptive design's chance of
extending; expected loop cost at the measured xhigh Batch price (analysis calls priced like annotation calls).
"""
import math
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "deepseek-stability"))

import full_reproduction_plan as frp  # noqa: E402
import run_haiku as rh  # noqa: E402
from run_haiku import rs, wo  # noqa: E402

SIMS = 10_000
ALPHA = 0.025
K = {"point": 1.00, "upper": 1.46}  # plan_counts_haiku_output.txt
GAINS = (0.0, 0.015, 0.02)
FIRST, EXTRA = 15, 5
Z80 = 0.8416


def welch_detect(a: list[float], b: list[float], either: bool) -> bool:
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    t = (statistics.mean(b) - statistics.mean(a)) / math.sqrt(va + vb)
    return (either or t > 0) and wo.p_two_sided(t, df) < ALPHA


def main() -> None:
    units = [u for u in rs.load_units(rh.UNITS) if u["arm"] == "H_xhigh"]
    price = statistics.mean(rh.cost_jpy(u["usage"], True) for u in units)
    per_loop = {m: frp.ROUNDS * frp.ANALYSIS_PER_ROUND[m] + 10 + frp.ROUNDS * 10 + 100 for m in ("top-1", "top-4")}
    pair = (per_loop["top-1"] + per_loop["top-4"]) * price  # one more loop of each method
    threshold = 0.015 / ((wo.t_crit(2 * FIRST - 2, ALPHA) + Z80) * math.sqrt(2 / FIRST))
    print(f"extension threshold T = {threshold:.4f} (pooled SD after {FIRST} loops per method); planning SD "
          f"{frp.SD_LOOP:.4f} at k point, {frp.SD_LOOP * K['upper']:.4f} at k upper")
    e1 = 15 * 100 * price
    print(f"one loop of each method JPY {pair:,.0f}; {FIRST} per method JPY {FIRST * pair:,.0f}; "
          f"{FIRST + EXTRA} per method JPY {(FIRST + EXTRA) * pair:,.0f}; E1 x15 JPY {e1:,.0f}")
    rng = random.Random(20261022)
    for name, k in K.items():
        sd = frp.SD_LOOP * k
        for gain in GAINS:
            hits = {"fixed 15": 0, "fixed 20": 0, "adaptive": 0}
            extended = 0
            for _ in range(SIMS):
                a = [rng.gauss(0, sd) for _ in range(FIRST + EXTRA)]
                b = [rng.gauss(gain, sd) for _ in range(FIRST + EXTRA)]
                either = gain == 0
                hits["fixed 15"] += welch_detect(a[:FIRST], b[:FIRST], either)
                hits["fixed 20"] += welch_detect(a, b, either)
                pooled = math.sqrt((statistics.variance(a[:FIRST]) + statistics.variance(b[:FIRST])) / 2)
                if pooled > threshold:
                    extended += 1
                    hits["adaptive"] += welch_detect(a, b, either)
                else:
                    hits["adaptive"] += welch_detect(a[:FIRST], b[:FIRST], either)
            share = extended / SIMS
            label = "false alarms" if gain == 0 else f"detects +{gain}"
            print(f"k {name} (SD {sd:.4f}), {label}: fixed 15 {hits['fixed 15'] / SIMS:.2f}, fixed 20 "
                  f"{hits['fixed 20'] / SIMS:.2f}, adaptive {hits['adaptive'] / SIMS:.2f}; extends {share:.0%}, "
                  f"expected loop cost JPY {(FIRST + EXTRA * share) * pair:,.0f}, "
                  f"with E1 x15 JPY {e1 + (FIRST + EXTRA * share) * pair:,.0f}")


if __name__ == "__main__":
    main()
