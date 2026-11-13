"""Calls, cost, time and detection numbers for running the whole RP v4 step 2 reproduction in one batch.
No API calls.

Design (thinking on, settings as in the stability test):
  E1 valid100, original guideline x10 (raised from 5 on 2026-10-22, see below)
  E2 top-1 loops on dev10 x15, each final annotated once on valid100
  E3 top-4 loops on dev10 x15, each final annotated once on valid100
  Alternative: 10 loops per method.
  (GPT-5.4-written guidelines were dropped on 2026-10-22: GPT-5.4 is no longer used.)

Why E1 x10: E1 is the only measure of DeepSeek's valid100 annotation noise, and that noise decides whether each
loop's final needs a second annotation. Five runs leave the true SD anywhere up to 2.86x the estimate, ten runs
up to 1.82x (repeat_count_sim_output.txt). The break-even section prints the noise share above which a second
annotation of every final beats spending the same calls on more loops.

Calls per loop: 10 initial dev10 annotations, then per round the analysis calls (top-1: discrepancy, principle,
rewrite = 3; top-4: 4 x 2 + 1 rewrite = 9) and 10 re-annotations. Rounds are planned at 4, the most any GPT-5.4
top-1 or top-4 loop used (status.json of the 7 loops listed below). The loop stops at the first round that does
not raise dev10 F1, at F1 0.9, or at 20 rounds.

Prices: annotation calls at the measured off-peak mean of the 200 thinking-on calls in units/. Analysis calls
are not measured; the estimate prices them like annotation calls, the upper bound at the 64,000-token output
cap with the largest saved GPT-5.4 analysis prompt, all of it a cache miss (characters counted as tokens).

Detection: as in plan_next_step.py (Welch t test, normal noise, 10,000 simulated experiments per cell), at
two-sided 5% and at 2.5% (two primary questions, each held to 0.05 / 2). SDs on valid100 are GPT-5.4
stand-ins: 0.0123 between loops (audit_helper_output.txt section 2), 0.0063 for one guideline annotated twice
(offline_direction_checks_output.txt line 14). The pessimistic case multiplies both by 0.0194 / 0.0150, the
ratio of DeepSeek's to GPT-5.4's dev10 SD.
"""
import contextlib
import io
import json
import math
import random
import statistics as st
from pathlib import Path

import run_stability as rs
import welch_on_off as wo

SIMS = 10_000
RUNS = rs.ROOT / "outputs/ncbi_disease"
GPT_LOOPS = ["20260802_gpt54-high_moderation", "20260902_gpt54-high_topk1_run1", "20260902_gpt54-high_topk1_run2",
             "20260902_gpt54-high_topk1_run3", "20260901_gpt54-high_topk4_dev10", "20260902_gpt54-high_topk4_run1",
             "20260902_gpt54-high_topk4_run2", "20260902_gpt54-high_topk4_run3"]
ANALYSIS_PROMPTS = ("infer_discrepancy_patterns.txt", "generate_moderation_principle.txt", "refine_guidelines.txt")
ROUNDS = 4
ANALYSIS_PER_ROUND = {"top-1": 3, "top-4": 9}
SD_LOOP, SD_ONE = 0.0123, 0.0063
PESSIMISTIC = 0.0194 / 0.0150


def bar(n_a, n_b, sd_a, sd_b, alpha):
    va, vb = sd_a ** 2 / n_a, sd_b ** 2 / n_b
    df = (va + vb) ** 2 / (va ** 2 / (n_a - 1) + vb ** 2 / (n_b - 1))
    return wo.t_crit(df, alpha) * math.sqrt(va + vb)


def detect(n_a, n_b, sd_a, sd_b, delta, alpha, rng):
    hits = 0
    for _ in range(SIMS):
        diff = rng.gauss(delta, math.sqrt(sd_a ** 2 / n_a + sd_b ** 2 / n_b))
        va = sd_a ** 2 * rng.gammavariate((n_a - 1) / 2, 2) / (n_a - 1) / n_a
        vb = sd_b ** 2 * rng.gammavariate((n_b - 1) / 2, 2) / (n_b - 1) / n_b
        df = (va + vb) ** 2 / (va ** 2 / (n_a - 1) + vb ** 2 / (n_b - 1))
        t = diff / math.sqrt(va + vb)
        hits += t > 0 and wo.p_two_sided(t, df) < alpha
    return hits / SIMS


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        on = [u for u in rs.load_units(rs.UNIT_DIRS["run"]) if u["arm"] == "B_on"]
    price = st.mean(rs.cost_jpy(u["usage"], peak=False) for u in on)
    seconds = st.mean(u["seconds"] for u in on)
    print(f"annotation call: JPY {price:.3f} off-peak, {seconds:.0f} s (mean of {len(on)} thinking-on calls)")

    print("\n== GPT-5.4 loops: rounds used, largest analysis prompt")
    largest = 0
    for name in GPT_LOOPS:
        status = json.loads((RUNS / name / "status.json").read_text(encoding="utf-8"))
        sizes = [len(p.read_text(encoding="utf-8")) for p in (RUNS / name / "rounds").glob("iteration_*/*.txt")
                 if p.name in ANALYSIS_PROMPTS]
        largest = max([largest, *sizes])
        print(f"  {name}: {status['iterations']} rounds, stop {status['stop_reason']}, "
              f"largest analysis prompt {max(sizes) if sizes else 0:,} chars")
    worst = rs.cost_jpy({"prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": largest,
                         "completion_tokens": rs.MAX_TOKENS}, peak=False)
    print(f"analysis call upper bound: {largest:,} prompt tokens as cache miss + {rs.MAX_TOKENS:,} output = "
          f"JPY {worst:.2f} off-peak")

    def loop_calls(method):
        analysis = ROUNDS * ANALYSIS_PER_ROUND[method]
        return analysis, 10 + ROUNDS * 10 + 100

    for loops in (15, 10):
        rows = [("E1 valid100, original x10", 0, 1000)]
        for method, tag in (("top-1", "E2"), ("top-4", "E3")):
            analysis, annotation = loop_calls(method)
            rows.append((f"{tag} {method} loops x{loops} ({analysis + annotation} calls per loop at {ROUNDS} rounds)",
                         loops * analysis, loops * annotation))
        print(f"\n== design with {loops} loops per method")
        total_a = total_n = 0
        for label, analysis, annotation in rows:
            total_a += analysis
            total_n += annotation
            calls = analysis + annotation
            print(f"  {label}: {calls:,} calls, estimate JPY {calls * price:,.0f}, "
                  f"upper JPY {annotation * price + analysis * worst:,.0f}")
        calls = total_a + total_n
        print(f"  total {calls:,} calls ({total_a:,} analysis); estimate JPY {calls * price:,.0f}; "
              f"upper JPY {total_n * price + total_a * worst:,.0f}; peak hours double any call made in them")
        print(f"  {calls * seconds / 3600:.0f} call-hours; wall time with 15 calls in flight about "
              f"{calls * seconds / 3600 / 15:.1f} h")

    print("\n== break-even: second annotation of every final against more loops for the same calls")
    for method in ("top-1", "top-4"):
        per_loop = sum(loop_calls(method))
        # Same calls: n single-annotation loops or n * per_loop / (per_loop + 100) double-annotation loops.
        # With annotation share s of the loop-score variance, doubling wins when 1 - s / 2 < per_loop / (per_loop + 100).
        share = 2 * (1 - per_loop / (per_loop + 100))
        print(f"  {method} ({per_loop} calls per loop): doubling wins only if annotation noise is more than "
              f"{share:.0%} of the loop-score variance")
    print(f"  planning values: annotation share {SD_ONE ** 2 / SD_LOOP ** 2:.0%} ({SD_ONE} against {SD_LOOP})")

    rng = random.Random(20261022)
    for case, k in (("GPT-5.4 stand-in SDs", 1.0), (f"pessimistic, SDs x{PESSIMISTIC:.2f}", PESSIMISTIC)):
        loop_sd, one_sd = SD_LOOP * k, SD_ONE * k
        print(f"\n== detection, {case}: loop SD {loop_sd:.4f}, one-guideline SD {one_sd:.4f}")
        for alpha in (0.05, 0.025):
            for loops in (10, 15):
                p2 = [detect(loops, loops, loop_sd, loop_sd, d, alpha, rng) for d in (0.015, 0.02)]
                print(f"  alpha {alpha}, {loops} loops: P2 top-4 vs top-1 bar "
                      f"{bar(loops, loops, loop_sd, loop_sd, alpha):.4f}, detects +0.015 {p2[0]:.2f}, +0.02 {p2[1]:.2f}")
        for n_orig in (5, 10):
            p1 = [detect(n_orig, 15, one_sd, loop_sd, d, 0.025, rng) for d in (0.01, 0.015, 0.02)]
            print(f"  alpha 0.025, P1 15 top-1 loops vs original x{n_orig}: bar "
                  f"{bar(n_orig, 15, one_sd, loop_sd, 0.025):.4f}, detects +0.01 {p1[0]:.2f}, +0.015 {p1[1]:.2f}, "
                  f"+0.02 {p1[2]:.2f}")


if __name__ == "__main__":
    main()
