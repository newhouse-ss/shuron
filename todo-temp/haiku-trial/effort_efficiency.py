"""Cost per unit of precision for each model and effort level, and whether a max-effort test could pay off.

Offline, no API calls. The number of runs needed for a given significance grows with the variance (SD squared),
so the money needed for the same precision is proportional to (cost per call) x (variance). Printed:

1. Mean cost per call, run-to-run SD of FN and F1 (dev10, 20 repeats each), and cost x variance relative to
   Haiku high.
2. F-test (two-sided) of high vs xhigh variances, and xhigh vs max once max has run: is a smaller SD proven?
3. With 20 runs per level, the smallest SD ratio an F-test can call significant.
4. Max effort pays off only if SD_max / SD_xhigh < sqrt(cost_xhigh / cost_max). For several cost ratios: that
   break-even SD ratio and the runs per level an F-test needs to detect it with 80% power; once max has run, its
   measured cost step and SD ratio.
5. The worst-case cost of a 20-repeat max batch (every call at the 64,000-token cap).
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fn_noise  # noqa: E402
import run_haiku as rh  # noqa: E402
from run_haiku import rs, wo  # noqa: E402

ALPHA = 0.05
POWER = 0.80


def f_cdf(x: float, d1: int, d2: int) -> float:
    return wo._betai(d1 / 2, d2 / 2, d1 * x / (d1 * x + d2)) if x > 0 else 0.0


def f_quantile(q: float, d1: int, d2: int) -> float:
    lo, hi = 0.0, 1.0
    while f_cdf(hi, d1, d2) < q:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f_cdf(mid, d1, d2) < q else (lo, mid)
    return (lo + hi) / 2


def f_test_p(a: list[float], b: list[float]) -> tuple[float, float]:
    ratio = statistics.variance(a) / statistics.variance(b)
    c = f_cdf(ratio, len(a) - 1, len(b) - 1)
    return ratio, min(1.0, 2 * min(c, 1 - c))


def power(n: int, sd_ratio: float) -> float:
    d = n - 1
    upper, lower = f_quantile(1 - ALPHA / 2, d, d), f_quantile(ALPHA / 2, d, d)
    true_var_ratio = 1 / sd_ratio ** 2  # variance of the noisier level over the quieter one
    return (1 - f_cdf(upper / true_var_ratio, d, d)) + f_cdf(lower / true_var_ratio, d, d)


def runs_needed(sd_ratio: float) -> int:
    n = 2
    while power(n, sd_ratio) < POWER:
        n += 1
    return n


def main() -> None:
    _, documents, entities = rs.load_inputs()
    data = fn_noise.sources(documents, entities)
    haiku = rs.fix_labels(rs.load_units(rh.UNITS), entities)
    deepseek = [u for u in rs.fix_labels(rs.load_units(rs.UNIT_DIRS["run"]), entities) if u["arm"] == "B_on"]
    rows = {}
    for name, reps in data.items():
        if name == "DeepSeek B_on":
            label, calls = "DeepSeek B_on (standard API, off-peak)", [rs.cost_jpy(u["usage"], False) for u in deepseek]
        else:
            arm = name.split()[1]
            label = f"{name} (batch)"
            # Every billed call, cut-off replies included (a batch request that errored has empty usage and costs 0).
            calls = [rh.cost_jpy(u["usage"], True) for u in haiku if u["arm"] == arm]
        rows[label] = {"fn": [r["fn"] for r in reps], "f1": [r["f1"] for r in reps], "call": statistics.mean(calls)}
    ref = rows["Haiku H_high (batch)"]
    print("1. cost per call, run-to-run SD, and money for the same precision (cost x variance, Haiku high = 1.00)")
    for name, r in rows.items():
        fn_rel = r["call"] * statistics.variance(r["fn"]) / (ref["call"] * statistics.variance(ref["fn"]))
        f1_rel = r["call"] * statistics.variance(r["f1"]) / (ref["call"] * statistics.variance(ref["f1"]))
        print(f"   {name}: JPY {r['call']:.3f}/call; FN SD {statistics.stdev(r['fn']):.2f}, "
              f"F1 SD {statistics.stdev(r['f1']):.4f}; relative money for same precision: "
              f"FN {fn_rel:.2f}, F1 {f1_rel:.2f}")

    high, xhigh = rows["Haiku H_high (batch)"], rows["Haiku H_xhigh (batch)"]
    top = rows.get("Haiku H_max (batch)")
    pairs = [("high", high, "xhigh", xhigh)] + ([("xhigh", xhigh, "max", top)] if top else [])
    print("\n2. F-test of variances (two-sided)")
    for name_a, a, name_b, b in pairs:
        for key in ("fn", "f1"):
            ratio, p = f_test_p(a[key], b[key])
            print(f"   {name_a} vs {name_b}, {key.upper()}: variance ratio {name_a}/{name_b} {ratio:.2f} "
                  f"(SD ratio {name_b}/{name_a} {ratio ** -0.5:.2f}), p {p:.3f}")

    n = len(high["fn"])
    upper = f_quantile(1 - ALPHA / 2, n - 1, n - 1)
    print(f"\n3. with {n} runs per level, an F-test calls an SD difference significant only when the smaller SD is "
          f"below {upper ** -0.5:.2f} x the larger one")

    measured = xhigh["call"] / high["call"]
    print(f"\n4. max vs xhigh, worked out before the max batch: measured cost step high -> xhigh = {measured:.2f}x")
    for cost_ratio in (1.3, measured, 2.0, 3.0):
        break_even = (1 / cost_ratio) ** 0.5
        print(f"   if max costs {cost_ratio:.2f}x xhigh per call: worth it only if SD_max < {break_even:.2f} x "
              f"SD_xhigh; runs per level to detect that with {POWER:.0%} power: {runs_needed(break_even)}")
    if top:
        step = top["call"] / xhigh["call"]
        for key in ("fn", "f1"):
            print(f"   measured: max costs {step:.2f}x xhigh per call (break-even SD ratio {step ** -0.5:.2f}); "
                  f"{key.upper()} SD ratio max/xhigh {statistics.stdev(top[key]) / statistics.stdev(xhigh[key]):.2f}")

    chars = {u["doc"]: u["prompt_chars"] for u in haiku}
    worst = n * sum(rh.worst_call_jpy(c, True) for c in chars.values())
    print(f"\n5. a {n}-repeat max batch on dev10 ({n * len(chars)} calls): worst case JPY {worst:.0f} "
          f"(every call at the {rh.MAX_TOKENS:,}-token cap); xhigh's measured batch for comparison: "
          f"JPY {xhigh['call'] * n * len(chars):.0f}")


if __name__ == "__main__":
    main()
