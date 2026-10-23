"""WITHDRAWN 2026-10-22: built on GPT-5.4 data; not used for any decision (see haiku_only_plan.py). How much an average of n valid100 scores wobbles (spread / sqrt(n)), for E1 runs and for loops, and the
wobble of the P1 difference (top-1 loops minus E1). Planning spreads: GPT-5.4 stand-ins at Haiku's factor 1.00
(plan_counts_haiku_output.txt). Offline, arithmetic only."""
import math

SD_ONE, SD_LOOP = 0.0063, 0.0123
for n in (5, 10, 15, 20):
    print(f"average of {n:2d}: E1 runs wobble {SD_ONE / math.sqrt(n):.4f}; loops wobble {SD_LOOP / math.sqrt(n):.4f}")
for loops, e1 in ((15, 5), (15, 10), (15, 15), (20, 10)):
    print(f"P1 difference, {loops} loops minus E1 x{e1}: wobble "
          f"{math.sqrt(SD_LOOP ** 2 / loops + SD_ONE ** 2 / e1):.4f}")
