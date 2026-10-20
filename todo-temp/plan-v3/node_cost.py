"""Call counts, cost ESTIMATES and serial run time for the steps in docs/RP/20261020_research_plan_v3.md.

Nothing here is measured. Per-call DeepSeek prices reuse todo-temp/plan-v3/plan_cost.py:
    thinking on  = output length assumed equal to GPT-5.4 high (mean 22,551 / max 36,459 tokens)
    thinking off = output per call from the "one loop + valid100" off scenario of
                   todo-temp/deepseek-stability/cost_estimate_output.txt (99,237 tokens / 162 calls)
Serial time uses the August DeepSeek logs: 46 to 489 seconds per document call
(todo-temp/deepseek-stability/20261016_deepseek_stability_design.md §7).

    python todo-temp/plan-v3/node_cost.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_cost as p  # noqa: E402

RATE = {
    "off": (p.DS_MISS * 0.15 + p.DS_HIT * 0.003 + (99_237 / 162) * 0.60) / 1e6,
    "on_mean": p.ds_call(p.DS_OUT["mean"]),
    "on_max": p.ds_call(p.DS_OUT["max"]),
}

# (node, calls with thinking as chosen by the stability test, calls fixed thinking on, calls fixed thinking off, conditional?)
NODES = [
    ("Delete contradicting examples: check (2 docs x 2 conditions x 3 passes)", 12, 0, 0, False),
    ("Stability test: arm A thinking off 52, arm B thinking on 52", 0, 52, 52, False),
    ("Main-result reproduction, baselines: valid100 x4 (original x2, GPT R4, GPT top-4)", 400, 0, 0, False),
    ("Main-result reproduction, loops: 10 x (62 dev calls + valid100 of final)", 1_620, 0, 0, False),
    ("Subtype typing, pilot: dev30 x2 + two typing variants on dev30", 120, 0, 0, False),
    ("Point 2: verified examples chosen by error cluster, 5 loops x (62 dev + valid100)", 810, 0, 0, False),
    ("Point 3: rationales passed to pattern explanation, 5 loops x (62 dev + valid100)", 810, 0, 0, False),
    ("Subtype typing, validation if gate passes: valid100 x2", 200, 0, 0, True),
    ("Test-split evaluation: frozen x2 + original x1", 300, 0, 0, True),
]


def yen(calls, rate):
    return calls * rate * p.JPY


def main():
    lines = ["per call JPY: " + ", ".join(f"{k} {v * p.JPY:.3f}" for k, v in RATE.items()), ""]
    tot = {"calls": 0, "off": 0.0, "on_mean": 0.0, "on_max": 0.0}
    tot_core = dict(tot)
    for name, n, n_on, n_off, cond in NODES:
        # calls fixed to thinking on (stability test arm B) are priced at on_mean in the "off" column
        c = {k: yen(n, RATE[k]) + yen(n_on, RATE["on_mean" if k == "off" else k]) + yen(n_off, RATE["off"])
             for k in RATE}
        calls = n + n_on + n_off
        lines.append(f"{name}: calls {calls}{' (conditional)' if cond else ''} | "
                     f"off JPY {c['off']:,.0f} | on JPY {c['on_mean']:,.0f} to {c['on_max']:,.0f}")
        for t in (tot, tot_core) if not cond else (tot,):
            t["calls"] += calls
            for k in RATE:
                t[k] += c[k]
    for label, t in (("core (unconditional)", tot_core), ("all", tot)):
        lines.append(f"TOTAL {label}: calls {t['calls']} | off JPY {t['off']:,.0f} | "
                     f"on JPY {t['on_mean']:,.0f} to {t['on_max']:,.0f}")
    repro = 400 + 1_620
    lines.append("")
    lines.append(f"Main-result reproduction serial time at 46 to 489 s per call: {repro * 46 / 3600:.1f} to {repro * 489 / 3600:.1f} hours; "
                 f"with 8 parallel workers {repro * 46 / 3600 / 8:.1f} to {repro * 489 / 3600 / 8:.1f} hours")
    out = "\n".join(lines)
    (Path(__file__).resolve().parent / "node_cost_output.txt").write_text(out + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
