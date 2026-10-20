"""Call counts and cost ESTIMATES for the revised plan (docs/RP/20261020_research_plan_v2.md).

Nothing here is measured. Per-call figures are the ones used for the first plan
(todo-temp/meeting-20261020/plan_cost.py): GPT-5.4 high full-guideline annotation call, input 4,834 tokens,
output mean 22,551 / max 36,459 tokens; Global prices $2.50 / $15.00 per 1M tokens; FX 158.086954 JPY/USD.
Refinement and typing-pass calls are priced like annotation calls (upper bound; their usage was never recorded).

    python todo-temp/direction-scan/plan_v2_cost.py
"""
from pathlib import Path

JPY = 158.086954
GPT_IN, GPT_OUT = 4_834, {"mean": 22_551, "max": 36_459}
PRICE_IN, PRICE_OUT = 2.50, 15.00
LOOP_CALLS_3REP = 3 * 10 + 4 * (3 + 3 * 10)  # same upper bound as plan_cost.py: 4 rounds, 3 repeats, dev10

# (step, calls, tier)
STEPS = [
    ("S1 fine-tuned yardstick and learning curve (GPU, no API)", 0, "core"),
    ("S2a validate 4 never-scored loop finals (top-1 run3, top-4 runs 1-3), 1 pass each", 400, "core"),
    ("S2b second pass of original and top-4 guidelines (same-guideline noise, agreement signal)", 200, "core"),
    ("S3 retrofit gold-consistency check on top-4 final: rewrites (<=5) + dev check (3) + 2 validation passes", 5 + 3 + 200, "core"),
    ("S6 final test split: chosen guideline x2 passes + original x1", 300, "core"),
    ("S4 typing pass: pilot on dev30 (1 repeat, 30 docs) then valid100 on 2 saved passes", 30 + 200, "conditional"),
    ("S5 reproducibility-gated acceptance: 3 loops (3 repeats) + 1 validation pass each", 3 * LOOP_CALLS_3REP + 300, "conditional"),
]


def call_usd(out):
    return (GPT_IN * PRICE_IN + out * PRICE_OUT) / 1e6


def main():
    lines = []
    tiers = {}
    for name, n, tier in STEPS:
        lo, hi = n * call_usd(GPT_OUT["mean"]), n * call_usd(GPT_OUT["max"])
        tiers.setdefault(tier, [0, 0.0, 0.0])
        tiers[tier][0] += n
        tiers[tier][1] += lo
        tiers[tier][2] += hi
        lines.append(f"{name:96s} {n:5d} calls  JPY {lo * JPY:8,.0f} to {hi * JPY:8,.0f}")
    lines.append("")
    for tier, (n, lo, hi) in tiers.items():
        lines.append(f"total {tier:11s} {n:5d} calls  JPY {lo * JPY:8,.0f} to {hi * JPY:8,.0f}")
    n = sum(v[0] for v in tiers.values())
    lo = sum(v[1] for v in tiers.values())
    hi = sum(v[2] for v in tiers.values())
    lines.append(f"total all         {n:5d} calls  JPY {lo * JPY:8,.0f} to {hi * JPY:8,.0f}")
    lines.append(f"one 100-document validation pass: JPY {100 * call_usd(GPT_OUT['mean']) * JPY:,.0f} "
                 f"to {100 * call_usd(GPT_OUT['max']) * JPY:,.0f}")
    lines.append("not included: the S7 LLM reviewer (Claude), priced once the model is chosen")
    out = "\n".join(lines)
    (Path(__file__).resolve().parent / "plan_v2_cost_output.txt").write_text(out + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
