"""WITHDRAWN 2026-10-22: built on GPT-5.4 data; not used for any decision (see haiku_only_plan.py). Repeat and loop counts for the RP v4 step 2 reproduction, recomputed for Haiku 5.5 xhigh. No API calls.

The DeepSeek plan (todo-temp/deepseek-stability/full_reproduction_plan.py) chose E1 x10 and 15 loops per method
from GPT-5.4 valid100 stand-in SDs (0.0123: 8 runs of 7 guidelines from different methods, standing in for the
spread between loops; 0.0063: one guideline annotated twice; see stand_in_ranges_output.txt),
scaled by DeepSeek's dev10 SD over GPT-5.4's (0.0194 / 0.0150 = 1.29) as the pessimistic case, and DeepSeek
prices. Here the same stand-ins are scaled by Haiku's own numbers, and priced at Haiku xhigh Batch cost:

    k point  Haiku xhigh dev10 SD (20 repeats) / GPT-5.4 dev10 SD 0.0150
    k upper  the same with Haiku's SD at the top of its 95% range (chi-square, 19 df, tabled 8.907)

Both SDs are scaled by k, i.e. the guidelines Haiku writes are assumed to vary as much, relative to its
annotation noise, as GPT-5.4's did. Nothing on valid100 has been measured for Haiku; E1 and the loops replace
these stand-ins.

1. E1 repeats: how far the measured annotation SD can be from the true one, and whether a second annotation of
   every final can be ruled out (break-even 70% for top-4, 76% for top-1, full_reproduction_plan_output.txt)
   if E1 measures the planning value.
2. P1 (top-1 loops vs E1) and 3. P2 (top-4 vs top-1): bar and share of simulated experiments that detect a
   true gain, Welch t test, two-sided alpha 0.025 (two primary questions), 10,000 simulations per cell, the
   simulation of full_reproduction_plan.py.
4. Costs at the measured xhigh Batch price per annotation call, analysis calls priced like annotation calls.
5. The counts picked by the rule stated there.
"""
import contextlib
import io
import math
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "deepseek-stability"))

import fn_noise  # noqa: E402
import full_reproduction_plan as frp  # noqa: E402
import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

GPT_DEV10_SD = 0.0150  # repeat_count_sim.py, gpt54_reference_output.txt
CHI2_LOW_19 = 8.907  # 2.5% quantile, 19 df (as in plan_next_step.py)
ALPHA = 0.025
POWER = 0.80
DELTAS = (0.01, 0.015, 0.02)
E1_OPTIONS = (5, 10, 15, 20)
LOOP_OPTIONS = (10, 15, 20, 25)
BREAK_EVEN = 0.70  # the lower of the two (top-4)


def sd_upper_factor(n: int, rng: random.Random, sims: int = 40000) -> float:
    s = sorted(statistics.stdev([rng.gauss(0, 1) for _ in range(n)]) for _ in range(sims))
    return 1 / s[int(0.025 * sims)]


def main() -> None:
    _, documents, entities = rs.load_inputs()
    with contextlib.redirect_stdout(io.StringIO()):
        xhigh = fn_noise.sources(documents, entities)["Haiku H_xhigh"]
        units = [u for u in rs.load_units(rh.UNITS) if u["arm"] == "H_xhigh"]
    sd = statistics.stdev(r["f1"] for r in xhigh)
    k_point = sd / GPT_DEV10_SD
    k_upper = k_point * math.sqrt((len(xhigh) - 1) / CHI2_LOW_19)
    price = statistics.mean(rh.cost_jpy(u["usage"], True) for u in units)
    print(f"Haiku xhigh dev10 SD {sd:.4f} over {len(xhigh)} repeats; GPT-5.4 dev10 SD {GPT_DEV10_SD}")
    print(f"k point {k_point:.2f}; k upper {k_upper:.2f} (DeepSeek plan used 1.00 and 1.29)")
    cases = {"point": k_point, "upper": k_upper}
    for name, k in cases.items():
        print(f"  {name}: loop SD {frp.SD_LOOP * k:.4f}, one-guideline SD {frp.SD_ONE * k:.4f}")
    share = frp.SD_ONE ** 2 / frp.SD_LOOP ** 2
    rng = random.Random(20261022)

    print(f"\n1. E1 repeats; planning annotation share of the loop variance {share:.0%}; break-even {BREAK_EVEN:.0%}")
    e1_ok = {}
    for n in E1_OPTIONS:
        f = sd_upper_factor(n, rng)
        upper_share = min(1.0, share * f ** 2)
        e1_ok[n] = upper_share < BREAK_EVEN
        print(f"   x{n}: true SD up to {f:.2f}x the measured one; if E1 measures the planning value, the true share "
              f"could be up to {upper_share:.0%} -> second annotation {'ruled out' if e1_ok[n] else 'not ruled out'}")

    print(f"\n2. P1, top-1 loops vs E1 (alpha {ALPHA}); detected share for true gain {' / '.join(map(str, DELTAS))}")
    p1 = {}
    for name, k in cases.items():
        for loops in (15, 20):
            for n in E1_OPTIONS:
                det = [frp.detect(n, loops, frp.SD_ONE * k, frp.SD_LOOP * k, d, ALPHA, rng) for d in DELTAS]
                p1[(name, loops, n)] = det
                print(f"   k {name}, {loops} loops vs E1 x{n}: bar "
                      f"{frp.bar(n, loops, frp.SD_ONE * k, frp.SD_LOOP * k, ALPHA):.4f}; "
                      + " / ".join(f"{x:.2f}" for x in det))

    print(f"\n3. P2, top-4 vs top-1 loops (alpha {ALPHA}); detected share for true gain {' / '.join(map(str, DELTAS))}")
    p2 = {}
    for name, k in cases.items():
        for loops in LOOP_OPTIONS:
            det = [frp.detect(loops, loops, frp.SD_LOOP * k, frp.SD_LOOP * k, d, ALPHA, rng) for d in DELTAS]
            p2[(name, loops)] = det
            print(f"   k {name}, {loops} vs {loops} loops: bar "
                  f"{frp.bar(loops, loops, frp.SD_LOOP * k, frp.SD_LOOP * k, ALPHA):.4f}; "
                  + " / ".join(f"{x:.2f}" for x in det))

    analysis = {m: frp.ROUNDS * frp.ANALYSIS_PER_ROUND[m] for m in ("top-1", "top-4")}
    per_loop = {m: analysis[m] + 10 + frp.ROUNDS * 10 + 100 for m in analysis}
    print(f"\n4. costs at JPY {price:.3f} per call (Batch, xhigh dev10 mean; analysis calls priced the same)")
    print(f"   E1: JPY {100 * price:,.0f} per valid100 run; one top-1 loop JPY {per_loop['top-1'] * price:,.0f}, "
          f"one top-4 loop JPY {per_loop['top-4'] * price:,.0f}")
    with contextlib.redirect_stdout(io.StringIO()):
        largest = max(len(p.read_text(encoding="utf-8")) for name in frp.GPT_LOOPS
                      for p in (frp.RUNS / name / "rounds").glob("iteration_*/*.txt") if p.name in frp.ANALYSIS_PROMPTS)
    worst = rh.cost_jpy({"input_tokens": largest, "output_tokens": rh.MAX_TOKENS}, True)
    for n, loops in ((10, 15), (15, 15), (20, 15), (15, 20), (20, 20)):
        calls = 100 * n + loops * (per_loop["top-1"] + per_loop["top-4"])
        n_analysis = loops * (analysis["top-1"] + analysis["top-4"])
        upper = (calls - n_analysis) * price + n_analysis * worst
        print(f"   E1 x{n} + {loops} loops per method: {calls:,} calls, estimate JPY {calls * price:,.0f}, "
              f"upper JPY {upper:,.0f}")

    i015, i02 = DELTAS.index(0.015), DELTAS.index(0.02)
    print(f"\n5. rule: the fewest loops per method with P2 power >= {POWER:.0%} for +0.015 at k point and for +0.02 at "
          f"k upper; the fewest E1 repeats that rule out the second annotation and give P1 power >= {POWER:.0%} "
          f"for +0.015 at k point with those loops")
    loops = next((n for n in LOOP_OPTIONS if p2[("point", n)][i015] >= POWER and p2[("upper", n)][i02] >= POWER),
                 None)
    print(f"   loops per method: {loops}")
    if loops in (15, 20):
        e1 = next((n for n in E1_OPTIONS if e1_ok[n] and p1[("point", loops, n)][i015] >= POWER), None)
        print(f"   E1 repeats: {e1}")


if __name__ == "__main__":
    main()
