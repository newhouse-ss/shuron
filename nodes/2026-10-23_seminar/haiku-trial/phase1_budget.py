"""API spend so far and the cost of the rest of phase 1 (the reproduction), from saved cost outputs only.

Offline. Phase 1 = the original guideline annotated on valid100 10 times, 10 top-1 loops and 10 top-4 loops, each
loop followed by one valid100 annotation of its final guideline. Loop 1 of each method ran in the 10/22 pilot, so
9 + 9 loops and 10 original-guideline runs remain. Two scenarios for a loop, since the number of rounds is not
known in advance (the stop rule allows 1 to 20):
- like the pilot: top-1 as the pilot top-1 loop (1 round), top-4 as the pilot top-4 loop (6 rounds), as billed;
- four rounds each: loop4_estimate.py.
One original-guideline run costs what the pilot's 100 valid100 calls with the original guideline cost.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TODO = HERE.parent


def grab(path: Path, pattern: str) -> float:
    m = re.search(pattern, path.read_text(encoding="utf-8"))
    assert m, (path.name, pattern)
    return float(m.group(1).replace(",", ""))


pilot = HERE / "batch_pilot_costs_output.txt"
est = HERE / "loop4_estimate_output.txt"
trial = HERE / "report_with_max_output.txt"
ds = TODO / "deepseek-stability/actual_cost_output.txt"

run_original = grab(pilot, r"topk1L01 valid100 annotation \[used\]: 100 calls, JPY ([\d.]+)")
loops = {"like the pilot": (grab(pilot, r"topk1L01: used replies cost JPY ([\d.]+)"),
                            grab(pilot, r"topk4L01: used replies cost JPY ([\d.]+)")),
         "four rounds each": (grab(est, r"top-1, 4 rounds.*\n  Haiku xhigh Batch: JPY ([\d.]+)"),
                              grab(est, r"top-4, 4 rounds.*\n  Haiku xhigh Batch: JPY ([\d.]+)"))}
rate = 158.086954  # run_stability.JPY_PER_USD

print(f"one original-guideline valid100 run: JPY {run_original:.2f}")
for name, (top1, top4) in loops.items():
    rest = 9 * top1 + 9 * top4 + 10 * run_original
    full = 10 * top1 + 10 * top4 + 10 * run_original
    print(f"{name}: top-1 loop JPY {top1:.2f}, top-4 loop JPY {top4:.2f}; rest of phase 1 (9 + 9 loops, "
          f"10 runs) JPY {rest:,.0f} = USD {rest / rate:.0f}; whole phase 1 JPY {full:,.0f}")

spent = {"DeepSeek stability test and probe": grab(ds, r"total JPY ([\d.]+)"),
         "Haiku dev10 trial (high, xhigh, max)": sum(grab(trial, rf"{arm}: .*\n.*\n    cost JPY ([\d.]+)")
                                                     for arm in ("H_high", "H_xhigh", "H_max")),
         "Haiku batch pilot (two loops)": grab(pilot, r"total 358 billed replies, JPY ([\d.]+)")}
for k, v in spent.items():
    print(f"spent, {k}: JPY {v:.2f}")
print(f"spent since 10/21, total: JPY {sum(spent.values()):,.0f} = USD {sum(spent.values()) / rate:.2f}")
