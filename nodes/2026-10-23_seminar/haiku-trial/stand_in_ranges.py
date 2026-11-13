"""WITHDRAWN 2026-10-22: built on GPT-5.4 data; not used for any decision (see haiku_only_plan.py). Where the two valid100 planning spreads come from, and how uncertain they are. Offline, arithmetic only.

Both are GPT-5.4 numbers; nothing has been measured on valid100 for Haiku or DeepSeek.
* 0.0123: SD of 8 GPT-5.4 valid100 strict F1 values (nodes/2026-10-20_meeting/plan-v3/audit_helper_output.txt section 2,
  run labels and paths in audit_helper.py RUNS). The 8 are 7 guidelines from different methods, not loops of one
  method: the unrefined original, the R4 final annotated twice, top-4, dev20, dev30, noTP, abstraction.
* 0.0063: one guideline (R4) annotated twice, 0.7878 and 0.7789
  (nodes/2026-10-20_meeting/plan-v3/offline_direction_checks_output.txt line 14); SD from one pair = |difference| / sqrt(2).
95% ranges for a true SD from a sample SD: chi-square with n-1 df, tabled 2.5% / 97.5% quantiles.
"""
import math
import statistics

EIGHT = {"original": 0.7792, "R4": 0.7878, "R4_rerun": 0.7789, "topk4": 0.8023,
         "dev20": 0.7745, "dev30": 0.8050, "noTP": 0.7716, "abstraction": 0.7844}
PAIR = (0.7878, 0.7789)
CHI2 = {7: (1.690, 16.013), 1: (0.000982, 5.024)}


def true_range(sd: float, df: int) -> tuple[float, float]:
    low, high = CHI2[df]
    return sd * math.sqrt(df / high), sd * math.sqrt(df / low)


sd8 = statistics.stdev(EIGHT.values())
lo, hi = true_range(sd8, 7)
print(f"8 GPT-5.4 valid100 runs {EIGHT}: SD {sd8:.4f}; true SD 95% range {lo:.4f} to {hi:.4f}")
sd2 = abs(PAIR[0] - PAIR[1]) / math.sqrt(2)
lo2, hi2 = true_range(sd2, 1)
print(f"R4 annotated twice {PAIR}: SD {sd2:.4f}; true SD 95% range {lo2:.4f} to {hi2:.4f}")
print(f"ratio of the two point values {sd8 / sd2:.2f}")
