"""Numbers for reproduction_design.md (top-1 against top-4 on Haiku). Offline, no API calls.

1. Budget split, from phase1_budget_output.txt only: the 9 + 9 remaining loops, the 10 original-guideline
   validation runs (E1), and the batch-queue spend so far, which the runner's --cap-usd also counts.
2. What a two-sided Welch t-test can detect with n loops per method: the gap between the two means, as a multiple
   of the loop-to-loop SD, that the test finds 80% of the time. Simulated with normal data and equal SDs, so the
   result is scale-free; the SD itself is unknown until the loops run, so no gap in F1 points is given.
   The critical value comes from the same simulation under no gap, so no t table is needed.
"""
import math
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUDGET = HERE.parent / "haiku-trial/phase1_budget_output.txt"
RATE = 158.086954  # run_stability.JPY_PER_USD, as phase1_budget.py
POWER = 0.8
SIMS = 200_000
SEED = 20261023


def grab(pattern: str) -> list[float]:
    m = re.search(pattern, BUDGET.read_text(encoding="utf-8"))
    assert m, pattern
    return [float(g.replace(",", "")) for g in m.groups()]


(run,) = grab(r"one original-guideline valid100 run: JPY ([\d.]+)")
scenarios = {"like the pilot": grab(r"like the pilot: top-1 loop JPY ([\d.]+), top-4 loop JPY ([\d.]+)"),
             "four rounds each": grab(r"four rounds each: top-1 loop JPY ([\d.]+), top-4 loop JPY ([\d.]+)")}
(pilot,) = grab(r"spent, Haiku batch pilot \(two loops\): JPY ([\d.]+)")

print(f"E1, 10 original-guideline validation runs: JPY {10 * run:,.2f}")
highest = 0.0
for name, (top1, top4) in scenarios.items():
    loops = 9 * top1 + 9 * top4
    highest = max(highest, loops + 10 * run)
    print(f"{name}: 9 top-1 loops JPY {9 * top1:,.2f} + 9 top-4 loops JPY {9 * top4:,.2f} = JPY {loops:,.2f}; "
          f"with E1 JPY {loops + 10 * run:,.2f}")
print(f"batch-queue spend so far (pilot): JPY {pilot:.2f} = USD {pilot / RATE:.2f}")
print(f"--cap-usd that just covers the pilot plus the higher estimate: USD {(pilot + highest) / RATE:.2f}")


def welch_parts(rng: random.Random, n: int) -> list[tuple[float, float]]:
    """Per simulated experiment: (mean of b minus mean of a, standard error) for two groups of n draws from N(0, 1).
    Shifting group b by a gap d moves only the difference, so t(d) = (difference + d) / standard error."""
    parts = []
    for _ in range(SIMS):
        a = [rng.gauss(0, 1) for _ in range(n)]
        b = [rng.gauss(0, 1) for _ in range(n)]
        ma, mb = sum(a) / n, sum(b) / n
        va = sum((x - ma) ** 2 for x in a) / (n - 1)
        vb = sum((x - mb) ** 2 for x in b) / (n - 1)
        parts.append((mb - ma, math.sqrt(va / n + vb / n)))
    return parts


def power(parts, gap: float, critical: float) -> float:
    return sum(abs((diff + gap) / se) > critical for diff, se in parts) / len(parts)


rng = random.Random(SEED)
print(f"detectable gap, as a multiple of the loop-to-loop SD (two-sided Welch, power {POWER}, {SIMS:,} simulations):")
for n in (5, 10, 15, 20):
    parts = welch_parts(rng, n)
    null = sorted(abs(diff / se) for diff, se in parts)
    row = []
    for alpha in (0.025, 0.05):
        critical = null[math.ceil((1 - alpha) * len(null)) - 1]
        low, high = 0.0, 5.0
        for _ in range(40):
            mid = (low + high) / 2
            low, high = (mid, high) if power(parts, mid, critical) < POWER else (low, mid)
        row.append(f"alpha {alpha}: {high:.2f} SD (critical |t| {critical:.3f})")
    print(f"  n = {n:2d} per method: " + "; ".join(row))
