"""Welch t test, thinking on vs thinking off, on dev10 F1 of the 100-call run. No API calls.

Two scorings: the planned one (labels as written) and the one agreed on 2026-10-21 (spaces removed from
label names, e.g. "Specific Disease" -> "SpecificDisease"). The t distribution is computed here with the
standard library (regularized incomplete beta), so no scipy is needed; the self-check at the top compares
it with tabled critical values.

welch_on_off_output.txt was written when units/ held 5 repeats per arm. After step 2 (2026-10-21) units/
holds 20 thinking-on repeats, so a rerun now compares 5 against 20; the 20-repeat analysis is
plan_next_step.py.
"""
import contextlib
import copy
import io
import math
import statistics as st

import run_stability as rs


def _betacf(a: float, b: float, x: float) -> float:
    # Continued fraction for the incomplete beta function (Numerical Recipes, betacf).
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > 1e-300 else 1e-300
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def p_two_sided(t: float, df: float) -> float:
    return _betai(df / 2, 0.5, df / (df + t * t))


def t_crit(df: float, alpha: float = 0.05) -> float:
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if p_two_sided(mid, df) > alpha else (lo, mid)
    return (lo + hi) / 2


def welch(a: list[float], b: list[float]) -> dict:
    va, vb = st.variance(a) / len(a), st.variance(b) / len(b)
    se = math.sqrt(va + vb)
    diff = st.mean(b) - st.mean(a)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    t = diff / se
    tc = t_crit(df)
    return {"mean_a": st.mean(a), "mean_b": st.mean(b), "sd_a": st.stdev(a), "sd_b": st.stdev(b), "diff": diff,
            "se": se, "t": t, "df": df, "t_crit": tc, "p": p_two_sided(t, df), "ci": (diff - tc * se, diff + tc * se)}


def scores(units, documents) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        return rs.score_run(units, documents)["scores"]


def main() -> None:
    for df, tabled in ((4, 2.776), (8, 2.306), (18, 2.101)):
        print(f"self-check: t_crit(df={df}) = {t_crit(df):.3f} (table {tabled}); p(t={tabled}) = {p_two_sided(tabled, df):.4f}")
    _, documents, _ = rs.load_inputs()
    units = rs.load_units(rs.UNIT_DIRS["run"])
    fixed = copy.deepcopy(units)
    for u in fixed:
        for a in u.get("annotations") or []:
            a["entity"] = a["entity"].replace(" ", "")
    for name, us in (("planned scoring (labels as written)", units), ("label spaces removed (agreed fix)", fixed)):
        s = scores(us, documents)
        a, b = s["A_off"]["f1"], s["B_on"]["f1"]
        w = welch(a, b)
        print(f"\n== {name} ==")
        print(f"A thinking off F1 {[round(x, 6) for x in a]}")
        print(f"B thinking on  F1 {[round(x, 6) for x in b]}")
        print(f"mean A {w['mean_a']:.6f}  mean B {w['mean_b']:.6f}  SD A {w['sd_a']:.6f}  SD B {w['sd_b']:.6f}")
        print(f"diff B-A {w['diff']:.6f}  SE {w['se']:.6f}  t {w['t']:.4f}  df {w['df']:.4f}  t_crit {w['t_crit']:.4f}")
        print(f"p (two-sided) {w['p']:.3g}  95% CI [{w['ci'][0]:.4f}, {w['ci'][1]:.4f}]")


if __name__ == "__main__":
    main()
