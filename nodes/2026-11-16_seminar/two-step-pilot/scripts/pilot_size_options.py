"""Pilot size options: paired by document, two-sided 95% interval of the total must exclude 0 (RP v4).

Inputs (from pilot_variance_output.txt): run noise w = 0.355 per document; spread of the effect across documents
tau^2 = 1.045 with document 8733131 (pessimistic) or 0.500 without it (typical); true misses per document under
the original guideline 1.356 (valid100). Normal approximation, as in pilot_variance.py.
Offline, no API calls. Run from the repository root:
    python nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot_size_options.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/pilot_size_options_output.txt
"""
from math import erf, sqrt

W, BASE, Z, Z90 = 0.355, 1.356, 1.959964, 1.281552
TAU2 = {'pessimistic': 1.045, 'typical': 0.500}

def var_per_doc(tau2, r):
    return tau2 + 2 * W / r

def power(eff, n, tau2, r):
    se = sqrt(n * var_per_doc(tau2, r))
    return 0.5 * (1 + erf((eff * n / se - Z) / sqrt(2)))

def min_detect(n, tau2, r):
    return (Z + Z90) * sqrt(var_per_doc(tau2, r) / n) / BASE

print('variance of one document\'s paired difference, by runs per arm (pessimistic / typical):')
for r in (1, 2, 3):
    print(f'  {r} run(s): {var_per_doc(TAU2["pessimistic"], r):.3f} / {var_per_doc(TAU2["typical"], r):.3f}')
for a, b in ((1, 2), (2, 3)):
    cut = [1 - var_per_doc(t, b) / var_per_doc(t, a) for t in TAU2.values()]
    print(f'  going from {a} to {b} runs lowers it by {cut[0]:.0%} (pessimistic) / {cut[1]:.0%} (typical)')

R = 2
print(f'\n{R} runs per arm; docs | detectable at 90% (pessimistic / typical) | chance to detect 15% | chance to detect 20%  (pess / typ) | calls')
for n in (100, 150, 200, 250, 387):
    p, t = TAU2['pessimistic'], TAU2['typical']
    print(f'{n:4d} | {min_detect(n, p, R):5.1%} / {min_detect(n, t, R):5.1%} | '
          f'{power(0.15 * BASE, n, p, R):.2f} / {power(0.15 * BASE, n, t, R):.2f} | '
          f'{power(0.20 * BASE, n, p, R):.2f} / {power(0.20 * BASE, n, t, R):.2f} | {n * R * 4}')
