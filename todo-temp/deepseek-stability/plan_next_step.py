"""Twenty-repeat noise of thinking-on dev10 F1, and repeat counts for the next experiments. No API calls.

1. dev10 F1 of the 20 thinking-on repeats (label mapping applied, as in report_run_output.txt), mean, SD,
   and a 95% range for the SD (chi-square with 19 degrees of freedom, tabled quantiles 8.907 and 32.852).
   Also how often a second run of the same guideline scores strictly higher than a first one, which is
   how often the loop's "F1 rises" rule would accept a candidate that changes nothing.
2. The two sessions (repeats 1-5 on 10/21 from 14:35 JST, repeats 6-20 from 19:01 JST) by Welch t test,
   to check that the time of day did not shift the scores.
3. Money spent, each call at the price of the window it started in, and the off-peak price of one call.
4. Simulated experiments (normal noise, Welch t test, two-sided 5%). For a planned SD and number of runs
   per arm: the bar (smallest observed gain that comes out significant when the measured SDs equal the
   planned ones) and the share of experiments that detect a true gain of a given size (significant and
   in the right direction). Means and variances are drawn directly (normal and scaled chi-square).
   a. dev10, a fixed guideline against the original: SD from section 1; the original's 20 runs reused,
      or both guidelines run N times.
   b. valid100, method against method, one valid100 score per loop: SD 0.0123 is the spread of 8 GPT-5.4
      valid100 runs over different guidelines (todo-temp/plan-v3/audit_helper_output.txt section 2), a
      stand-in until DeepSeek's own spread is measured.
   c. valid100, 5 loops against the original guideline run n times: loop SD 0.0123 as in b; the
      original's annotation SD 0.0063 is GPT-5.4's estimate from one pair of runs
      (todo-temp/plan-v3/offline_direction_checks_output.txt line 14), very rough.
"""
import contextlib
import io
import math
import random
import statistics as st

import run_stability as rs
import welch_on_off as wo

SIMS = 10_000
STEP2_START = "2026-10-21T10:00"
LOOP_CALLS = 162  # 62 dev calls + valid100 of the final (todo-temp/plan-v3/node_cost.py)
VALID_SD_LOOP = 0.0123
VALID_SD_ANNOTATION = 0.0063


def welch_bar(n_a: int, n_b: int, sd_a: float, sd_b: float) -> tuple[float, float]:
    va, vb = sd_a ** 2 / n_a, sd_b ** 2 / n_b
    df = (va + vb) ** 2 / (va ** 2 / (n_a - 1) + vb ** 2 / (n_b - 1))
    return wo.t_crit(df) * math.sqrt(va + vb), df


def detect_rate(n_a: int, n_b: int, sd_a: float, sd_b: float, delta: float, rng: random.Random) -> float:
    hits = 0
    for _ in range(SIMS):
        diff = rng.gauss(delta, math.sqrt(sd_a ** 2 / n_a + sd_b ** 2 / n_b))
        va = sd_a ** 2 * rng.gammavariate((n_a - 1) / 2, 2) / (n_a - 1) / n_a
        vb = sd_b ** 2 * rng.gammavariate((n_b - 1) / 2, 2) / (n_b - 1) / n_b
        df = (va + vb) ** 2 / (va ** 2 / (n_a - 1) + vb ** 2 / (n_b - 1))
        t = diff / math.sqrt(va + vb)
        significant = wo.p_two_sided(t, df) < 0.05
        hits += significant if delta == 0 else (significant and t > 0)
    return hits / SIMS


def main() -> None:
    _, documents, entities = rs.load_inputs()
    units = rs.fix_labels(rs.load_units(rs.UNIT_DIRS["run"]), entities)
    with contextlib.redirect_stdout(io.StringIO()):
        cell = rs.score_run(units, documents)["scores"]["B_on"]
    f1, reps = cell["f1"], cell["complete_repeats"]
    assert reps == list(range(1, 21)), reps
    sd = st.stdev(f1)

    print("== 1 dev10 F1, thinking on, 20 repeats, label mapping applied")
    print(f"F1 {[round(x, 4) for x in f1]}")
    print(f"mean {st.mean(f1):.4f}  SD {sd:.4f}  min {min(f1):.4f}  max {max(f1):.4f}")
    lo, hi = sd * math.sqrt(19 / 32.852), sd * math.sqrt(19 / 8.907)
    print(f"95% range for the true SD (chi-square, 19 df): {lo:.4f} to {hi:.4f}")
    higher = sum(b > a for i, a in enumerate(f1) for j, b in enumerate(f1) if i != j)
    print(f"same guideline run twice: second strictly higher in {higher}/380 ordered pairs ({higher / 380:.1%}); "
          f"SD of the difference of two single runs {sd * math.sqrt(2):.4f}")

    print("\n== 2 session 1 (repeats 1-5) against session 2 (repeats 6-20)")
    w = wo.welch(f1[:5], f1[5:])
    print(f"session 1 mean {w['mean_a']:.4f} SD {w['sd_a']:.4f}; session 2 mean {w['mean_b']:.4f} SD {w['sd_b']:.4f}")
    print(f"diff {w['diff']:+.4f}  t {w['t']:.3f}  df {w['df']:.2f}  p {w['p']:.3f}  "
          f"95% CI [{w['ci'][0]:+.4f}, {w['ci'][1]:+.4f}]")

    print("\n== 3 money")
    probe = rs.load_units(rs.UNIT_DIRS["probe"])
    phases = {"probe (4 calls)": probe,
              "main run": [u for u in units if u["started_utc"] < STEP2_START],
              "step 2": [u for u in units if u["started_utc"] >= STEP2_START]}
    total = 0.0
    for name, us in phases.items():
        spent = sum(rs.cost_jpy(u["usage"], peak=u["peak"]) for u in us if u.get("usage"))
        total += spent
        print(f"{name}: {len(us)} saved units, {sum(bool(u['peak']) for u in us)} started in the peak window, "
              f"JPY {spent:.2f}")
    print(f"total recorded JPY {total:.2f} (the first attempt of B_on__10577908__r9 dropped at 60 s; "
          f"if it was billed, its usage is not recorded)")
    on = [u for u in units if u["arm"] == "B_on"]
    per_call = [rs.cost_jpy(u["usage"], peak=False) for u in on]
    price = st.mean(per_call)
    seconds = st.mean(u["seconds"] for u in on)
    print(f"thinking-on dev10 annotation call, off-peak price: mean JPY {price:.3f}, median {st.median(per_call):.3f}, "
          f"min {min(per_call):.3f}, max {max(per_call):.3f}; mean {seconds:.0f} s per call")
    print(f"one dev10 repeat (10 calls) about JPY {10 * price:.1f}; one valid100 annotation (100 calls) about "
          f"JPY {100 * price:.0f}; one loop ({LOOP_CALLS} calls) about JPY {LOOP_CALLS * price:.0f} "
          f"if loop calls cost like annotation calls (not measured)")
    drops = 1  # one IncompleteRead among the 250 calls of units/ (step2.log, 2026-10-21T10:28:59)
    print(f"dropped connections: {drops} in {len(units)} calls; chance that a {LOOP_CALLS}-call loop meets at least "
          f"one at that rate: {1 - (1 - drops / len(units)) ** LOOP_CALLS:.0%}")
    for name, calls in (("RP v4 step 2 as planned", 2020),
                        ("step 2 with the original run 3 times on valid100 (one more than planned)", 2120),
                        ("  stage A, pilot: one top-1 loop", LOOP_CALLS),
                        ("  stage B, the rest: original x3, GPT R4 x1, GPT top-4 x1 on valid100, 9 loops",
                         500 + 9 * LOOP_CALLS)):
        print(f"{name}: {calls} calls, about JPY {calls * price:,.0f} off-peak, "
              f"{calls * seconds / 3600:.0f} h if run one call at a time")

    rng = random.Random(20261021)
    print(f"\n== 4a dev10, new guideline against the original, planned SD {sd:.4f} ({SIMS:,} simulated experiments per cell)")
    deltas = (0.0, 0.01, 0.02, 0.03, 0.04)
    print("runs of the original / new; bar; detected share for true gain " + " / ".join(f"{d:.2f}" for d in deltas)
          + "; cost of the new runs")
    for n_new in (3, 5, 10, 20):
        for n_orig, label in ((20, "reuse 20"), (n_new, "run both")):
            if label == "run both" and n_new == 20:
                continue
            b, df = welch_bar(n_orig, n_new, sd, sd)
            rates = [detect_rate(n_orig, n_new, sd, sd, d, rng) for d in deltas]
            calls = 10 * n_new * (1 if label == "reuse 20" else 2)
            print(f"  {label:8s} {n_orig:2d} / {n_new:2d}: bar {b:.4f} (df {df:.1f}); "
                  + " / ".join(f"{r:.2f}" for r in rates) + f"; {calls} calls, about JPY {calls * price:.0f}")
    print(f"  if the true SD is {hi:.4f} (top of its range), every bar is {hi / sd:.2f}x as large")

    print(f"\n== 4b valid100, loops per method, planned SD {VALID_SD_LOOP} (GPT-5.4 stand-in)")
    deltas = (0.0, 0.01, 0.015, 0.02, 0.03)
    print("loops per method; bar; detected share for true gain " + " / ".join(f"{d:.3f}" for d in deltas)
          + "; cost per method")
    for loops in (3, 5, 8, 10, 15):
        b, df = welch_bar(loops, loops, VALID_SD_LOOP, VALID_SD_LOOP)
        rates = [detect_rate(loops, loops, VALID_SD_LOOP, VALID_SD_LOOP, d, rng) for d in deltas]
        print(f"  {loops:2d} vs {loops:2d}: bar {b:.4f} (df {df:.1f}); " + " / ".join(f"{r:.2f}" for r in rates)
              + f"; {loops * LOOP_CALLS} calls, about JPY {loops * LOOP_CALLS * price:,.0f}")
    print(f"  re-annotating each final twice only shrinks the loop SD from {VALID_SD_LOOP} to "
          f"{math.sqrt(VALID_SD_LOOP ** 2 - VALID_SD_ANNOTATION ** 2 / 2):.4f}, for 100 more calls per loop")

    print(f"\n== 4c valid100, 5 loops (SD {VALID_SD_LOOP}) against the original run n times (SD {VALID_SD_ANNOTATION})")
    deltas = (0.0, 0.02, 0.03)
    for n_orig in (2, 3, 5):
        b, df = welch_bar(n_orig, 5, VALID_SD_ANNOTATION, VALID_SD_LOOP)
        rates = [detect_rate(n_orig, 5, VALID_SD_ANNOTATION, VALID_SD_LOOP, d, rng) for d in deltas]
        print(f"  original x{n_orig}: bar {b:.4f} (df {df:.1f}); detected share for true gain "
              + " / ".join(f"{d:.2f}: {r:.2f}" for d, r in zip(deltas, rates))
              + f"; {100 * n_orig} calls, about JPY {100 * n_orig * price:.0f}")


if __name__ == "__main__":
    main()
