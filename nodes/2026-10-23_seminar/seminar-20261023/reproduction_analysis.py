"""Reproduction results (design: reproduction_design.md, §5). Offline: reads the saved runs, no API calls.

Groups (one validation score per run, strict span-and-subtype matching on the 100 validation documents):
  E1     the original guideline, no refinement: 20261022_haiku-xhigh_e1_run01..10
  top-1  final guideline of each top-1 loop:     20261022_haiku-xhigh_topk1_loop01..10 (01 = 10/22 pilot)
  top-4  final guideline of each top-4 loop:     20261022_haiku-xhigh_topk4_loop01..10 (01 = 10/22 pilot)
F1 is recomputed from the saved TP / FP / FN counts (valid_metrics.json rounds it to 4 decimals).

Tests fixed before the run (user, 10/23): three Welch t-tests, two-sided, each at 5%:
  P1 top-1 vs E1, P2 top-4 vs top-1, P3 top-4 vs E1. Each reports the difference of means with its 95% CI and p.
Welch's test compares two means without assuming equal spread; its p-value comes from Student's t distribution,
computed here from the regularized incomplete beta function (no SciPy in this environment), and checked against
two table values before use. Secondary measures (FN, FP, precision, recall, rounds, guideline length, cost) are
reported without tests.
"""
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "nodes/2026-10-23_seminar/haiku-trial"))
import run_haiku as rh  # noqa: E402

RUNS = ROOT / "outputs/ncbi_disease"
TAG = "20261022_haiku-xhigh"
GROUPS = {"E1": [f"{TAG}_e1_run{i:02d}" for i in range(1, 11)],
          "top-1": [f"{TAG}_topk1_loop{i:02d}" for i in range(1, 11)],
          "top-4": [f"{TAG}_topk4_loop{i:02d}" for i in range(1, 11)]}
LOOP_IDS = {"E1": "E1R{:02d}", "top-1": "topk1L{:02d}", "top-4": "topk4L{:02d}"}
TESTS = [("P1", "top-1", "E1"), ("P2", "top-4", "top-1"), ("P3", "top-4", "E1")]
ALPHA = 0.05


def betacf(a: float, b: float, x: float) -> float:
    """Continued fraction of the incomplete beta function (Numerical Recipes, betacf)."""
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)), -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1 + aa * d
            d = 1 / (d if abs(d) > 1e-300 else 1e-300)
            c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
            h *= d * c
        if abs(d * c - 1) < 1e-15:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * betacf(a, b, x) / a
    return 1 - front * betacf(b, a, 1 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    return betai(df / 2, 0.5, df / (df + t * t))


def t_quantile(prob: float, df: float) -> float:
    """t with P(T <= t) = prob, by bisection on the two-sided p."""
    low, high = 0.0, 100.0
    for _ in range(200):
        mid = (low + high) / 2
        low, high = (mid, high) if t_two_sided_p(mid, df) > 2 * (1 - prob) else (low, mid)
    return (low + high) / 2


# Table checks before use: t(0.975, 18) = 2.101, t(0.975, 10) = 2.228.
assert abs(t_quantile(0.975, 18) - 2.1009) < 1e-3 and abs(t_quantile(0.975, 10) - 2.2281) < 1e-3
assert abs(t_two_sided_p(2.1009, 18) - 0.05) < 1e-3


def welch(a: list[float], b: list[float]) -> dict:
    """Welch t-test of mean(a) - mean(b)."""
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    diff = statistics.mean(a) - statistics.mean(b)
    half = t_quantile(0.975, df) * se
    return {"diff": diff, "low": diff - half, "high": diff + half, "t": diff / se, "df": df,
            "p": t_two_sided_p(diff / se, df)}


def run_row(group: str, index: int, name: str, cost: dict) -> dict:
    folder = RUNS / name
    status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "completed" and status["valid_documents"] == 100, (name, status)
    m = json.loads((folder / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    tp, fp, fn = m["true_positives"], m["false_positives"], m["false_negatives"]
    assert tp + fn == m["gold_total"] == 791, (name, m)
    final = folder / "final/final_guidelines.txt"
    guideline = final.read_text(encoding="utf-8") if final.exists() else (folder / "inputs/initial_guidelines.txt").read_text(encoding="utf-8")
    return {"run": name.removeprefix(f"{TAG}_"), "f1": 2 * tp / (2 * tp + fp + fn), "precision": tp / (tp + fp),
            "recall": tp / (tp + fn), "tp": tp, "fp": fp, "fn": fn, "rounds": status.get("iterations", 0),
            "stop": status.get("stop_reason", "-"), "dev": (status.get("initial_f1"), status.get("final_f1")),
            "guideline": guideline, "chars": len(guideline), "cost": cost.get(LOOP_IDS[group].format(index), 0.0)}


def main() -> None:
    cost: dict[str, float] = {}
    for p in (RUNS / f"{TAG}_batchqueue/replies").glob("*.json"):
        r = json.loads(p.read_text(encoding="utf-8"))
        cost[r["meta"]["loop"]] = cost.get(r["meta"]["loop"], 0.0) + rh.cost_jpy(r["message"].get("usage") or {}, True)
    rows = {g: [run_row(g, i, n, cost) for i, n in enumerate(names, 1)] for g, names in GROUPS.items()}

    print("Per run (validation strict F1 from TP/FP/FN; dev10 F1 start -> end; rounds run; guideline characters; JPY)")
    for g, rs in rows.items():
        for r in rs:
            dev = "-" if r["dev"][0] is None else f"{r['dev'][0]:.4f} -> {r['dev'][1]:.4f}"
            print(f"  {g:5s} {r['run']:13s} F1 {r['f1']:.4f}  P {r['precision']:.4f}  R {r['recall']:.4f}  "
                  f"TP {r['tp']}  FP {r['fp']}  FN {r['fn']}  dev {dev}  rounds {r['rounds']} ({r['stop']})  "
                  f"chars {r['chars']:,}  JPY {r['cost']:.2f}")

    print("\nGroup summary: mean (SD) over 10 runs")
    for g, rs in rows.items():
        def ms(key):
            values = [r[key] for r in rs]
            return f"{statistics.mean(values):.4f} ({statistics.stdev(values):.4f})"
        print(f"  {g:5s} F1 {ms('f1')}  precision {ms('precision')}  recall {ms('recall')}  "
              f"FN {statistics.mean(r['fn'] for r in rs):.1f} ({statistics.stdev(r['fn'] for r in rs):.1f})  "
              f"FP {statistics.mean(r['fp'] for r in rs):.1f} ({statistics.stdev(r['fp'] for r in rs):.1f})  "
              f"guideline chars {statistics.mean(r['chars'] for r in rs):,.0f}  "
              f"cost JPY {sum(r['cost'] for r in rs):,.2f} total")
    original = rows["E1"][0]["guideline"]
    for g in ("top-1", "top-4"):
        unchanged = sum(r["guideline"] == original for r in rows[g])
        print(f"  {g} loops whose final guideline is the original one (round 1 rejected): {unchanged} of 10")

    print(f"\nTests fixed before the run: Welch, two-sided, each at {ALPHA}")
    for name, a, b in TESTS:
        w = welch([r["f1"] for r in rows[a]], [r["f1"] for r in rows[b]])
        verdict = "significant" if w["p"] < ALPHA else "not significant"
        print(f"  {name} {a} - {b}: difference {w['diff']:+.4f}, 95% CI [{w['low']:+.4f}, {w['high']:+.4f}], "
              f"t {w['t']:.3f}, df {w['df']:.1f}, p {w['p']:.4f} -> {verdict}")


if __name__ == "__main__":
    main()
