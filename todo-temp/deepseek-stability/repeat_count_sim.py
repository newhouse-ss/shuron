"""How many dev10 repeats per guideline an F1 improvement needs (planning only, no API calls).

Simulated with normal noise and the GPT-5.4 dev10 F1 SD (0.0150, gpt54_reference_output.txt) as a
stand-in until DeepSeek's own SD is measured. Standard library only.

1. How far a sample SD from n runs can fall from the true SD (2.5% and 97.5% quantiles of s/sigma).
2. Repeats per guideline for an 80% chance of detecting a true gain delta with a two-sided 5% t test.
"""
import math
import random
import statistics as st

SD = 0.015
# Two-sided 5% Student t critical values by degrees of freedom (standard table).
T = {4: 2.776, 6: 2.447, 8: 2.306, 10: 2.228, 12: 2.179, 14: 2.145, 16: 2.120, 18: 2.101, 20: 2.086,
     22: 2.074, 24: 2.064, 26: 2.056, 28: 2.048, 30: 2.042, 40: 2.021, 50: 2.009, 60: 2.000, 70: 1.994, 80: 1.990}


def tcrit(df: int) -> float:
    return T[min(T, key=lambda k: abs(k - df))]


def main() -> None:
    rng = random.Random(0)
    for n in (5, 10, 20):
        s = sorted(st.stdev([rng.gauss(0, 1) for _ in range(n)]) for _ in range(40000))
        lo, hi = s[int(0.025 * len(s))], s[int(0.975 * len(s))]
        print(f"n={n}: s/sigma 95% range {lo:.2f} to {hi:.2f}; true SD up to {1 / lo:.2f}x the estimate; "
              f"repeat count too small by up to {1 / lo ** 2:.1f}x")
    for delta in (0.03, 0.02, 0.015, 0.01):
        normal = 2 * (1.96 + 0.8416) ** 2 * SD ** 2 / delta ** 2
        for n in range(max(3, int(normal) - 1), 60):
            sims, hits = 8000, 0
            for _ in range(sims):
                a = [rng.gauss(0, SD) for _ in range(n)]
                b = [rng.gauss(delta, SD) for _ in range(n)]
                pooled = (st.variance(a) + st.variance(b)) / 2
                hits += (st.fmean(b) - st.fmean(a)) / math.sqrt(2 * pooled / n) > tcrit(2 * n - 2)
            if hits / sims >= 0.80:
                print(f"delta={delta}: {n} repeats per guideline (power {hits / sims:.2f}; normal formula {normal:.1f})")
                break


if __name__ == "__main__":
    main()
