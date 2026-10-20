"""Call counts and cost ESTIMATES for the experiment plan in docs/RP/20261020_research_plan_to_draft.md.

Nothing here is measured; every per-call figure comes from earlier saved measurements or estimates:
    GPT-5.4 high, full-guideline annotation call: output mean 22,551 / max 36,459 tokens (n=31),
        input 4,834 tokens (largest measured, R4 minus FALDH)      todo-temp/deepseek-stability/cost_estimate_output.txt
    Refinement calls (3 per round): usage never recorded, so priced like an annotation call (assumption).
    DeepSeek flash, off-peak: per-call input split from the "valid100 once, refined-size guideline" line of the
        same file; output per call assumed equal to GPT-5.4 high (scenarios on_mean, on_max), as in that file.
    Prices per 1M tokens: GPT-5.4 Global $2.50/$15.00, Data Zone $2.75/$16.50; DeepSeek off-peak miss $0.15,
        hit $0.003, output $0.60. FX 158.086954 JPY/USD (2026-10-16).

    python todo-temp/meeting-20261020/plan_cost.py
"""
from pathlib import Path

JPY = 158.086954
GPT_IN, GPT_OUT = 4_834, {"mean": 22_551, "max": 36_459}
GPT_PRICE = {"Global": (2.50, 15.00), "Data Zone": (2.75, 16.50)}
DS_MISS, DS_HIT = 35_684 / 100, 456_890 / 100
DS_OUT = {"mean": 2_311_996 / 100, "max": 3_702_780 / 100}


def gpt_call(price, out):
    return (GPT_IN * price[0] + out * price[1]) / 1e6


def ds_call(out):
    return (DS_MISS * 0.15 + DS_HIT * 0.003 + out * 0.60) / 1e6


def calls(repeats, loops, arms, iterations=4, dev_docs=10, valid_docs=100):
    """Upper bound: every loop runs the largest iteration count seen so far (4)."""
    per_loop = repeats * dev_docs + iterations * (3 + repeats * dev_docs)
    per_arm = loops * (per_loop + valid_docs)
    return per_loop, per_arm, arms * per_arm


def main():
    lines = []
    plans = {"full plan (3 repeats, 3 loops, 4 arms)": (3, 3, 4),
             "lighter plan (2 repeats, 2 loops, 4 arms)": (2, 2, 4)}
    for name, (r, l, a) in plans.items():
        per_loop, per_arm, total = calls(r, l, a)
        lines.append(f"== {name}: per loop {per_loop} calls, per arm {per_arm}, total {total}")
        for scen, out in GPT_OUT.items():
            for pname, price in GPT_PRICE.items():
                usd = total * gpt_call(price, out)
                lines.append(f"  GPT-5.4 {pname:9s} output {scen:4s}: ${usd:8.0f} = JPY {usd * JPY:9,.0f}")
        for scen, out in DS_OUT.items():
            usd = total * ds_call(out)
            lines.append(f"  DeepSeek off-peak     output {scen:4s}: ${usd:8.1f} = JPY {usd * JPY:9,.0f}"
                         f"   (peak hours: x2)")
    lines.append("")
    lines.append("per call: GPT-5.4 Global mean $%.3f, DeepSeek off-peak mean $%.4f (ratio %.0f)"
                 % (gpt_call(GPT_PRICE["Global"], GPT_OUT["mean"]), ds_call(DS_OUT["mean"]),
                    gpt_call(GPT_PRICE["Global"], GPT_OUT["mean"]) / ds_call(DS_OUT["mean"])))
    out = "\n".join(lines)
    (Path(__file__).resolve().parent / "plan_cost_output.txt").write_text(out + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
