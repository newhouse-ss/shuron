"""Where does the noise in true-miss counts come from: documents or repeated runs?  Offline, existing runs only.

Unit: one document. M(d, run) = true misses in document d in one run.
- Run noise: for each document, the variance of M(d, .) over the 19 original-guideline runs (same guideline,
  same document, only the model's randomness differs); averaged over documents.
- Spread of a real effect over documents: for each refined guideline whose true misses fall below the original
  range, delta(d) = M_g(d) - mean over original runs of M(d, .). Its variance over documents contains the
  guideline's own run noise (one run) plus how unevenly the effect is spread; subtracting the average run
  noise leaves the spread (tau^2).
Then, for a paired design (same documents in both arms, r runs per arm per document), the per-document
difference has variance tau^2 + 2 * runnoise / r, and the total over n documents is judged by whether its
interval excludes 0 (two-sided 95%, as in RP v4). Power is computed with the normal approximation.
The spread is also shown without document 8733131, whose 13 VHL mentions are found or missed together.
Offline, no API calls. Run from the repository root:
    python nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot_variance.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/pilot_variance_output.txt
"""
import csv
import sys
from collections import defaultdict
from math import erf, sqrt
from pathlib import Path
from statistics import mean, pvariance

ROOT = Path(__file__).resolve().parents[4]
ROWS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'nodes/shared/error-analysis/outputs/error_rows.csv'
VALID = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'data/datasets/ncbi_disease/valid'
rows = list(csv.DictReader(ROWS.open(encoding='utf-8')))
docs = sorted(p.stem for p in VALID.glob('*.json'))
orig = sorted({r['run'] for r in rows if r['guideline'] == 'original'})
mods = sorted({r['run'] for r in rows if r['guideline'] != 'original'})

M = defaultdict(lambda: defaultdict(int))
seen = set()
for r in rows:
    if r['kind'] != 'missed':
        continue
    key = (r['run'], r['doc'], r['gold_start'], r['gold_end'])
    if key in seen:
        continue
    seen.add(key)
    M[r['run']][r['doc']] += 1

per_doc_mean = {d: mean(M[o][d] for o in orig) for d in docs}
run_var = {d: pvariance([M[o][d] for o in orig]) * 19 / 18 for d in docs}
w = mean(run_var.values())
tot = [sum(M[o][d] for d in docs) for o in orig]
print(f'original: true misses per run {mean(tot):.1f}; per document {mean(per_doc_mean.values()):.3f}')
print(f'run noise: mean over documents of the within-document variance across 19 runs = {w:.4f} '
      f'(if documents were independent, SD of a 100-document total = {sqrt(100 * w):.2f}; observed {sqrt(pvariance(tot) * 19 / 18):.2f})')
nonzero = sum(1 for d in docs if run_var[d] > 0)
print(f'documents whose true-miss count ever changes across the 19 runs: {nonzero} of {len(docs)}')

lo = min(tot)
print('\nrefined guidelines below the original range (fewer true misses than every original run):')
taus = []
for g in mods:
    total = sum(M[g][d] for d in docs)
    if total >= lo:
        continue
    delta = [M[g][d] - per_doc_mean[d] for d in docs]
    v = pvariance(delta) * 100 / 99
    tau2 = v - w
    taus.append(tau2)
    print(f'  {g}: total {total}, mean change per document {mean(delta):+.3f}, '
          f'variance over documents {v:.3f}, minus run noise -> spread tau^2 {tau2:.3f}')
tau2 = mean(taus)
print(f'average spread tau^2 = {tau2:.3f}')

below = [g for g in mods if sum(M[g][d] for d in docs) < lo]
rest = [d for d in docs if d != '8733131']
pm_rest = {d: mean(M[o][d] for o in orig) for d in rest}
w_rest = mean(pvariance([M[o][d] for o in orig]) * 19 / 18 for d in rest)
taus_rest = [pvariance([M[g][d] - pm_rest[d] for d in rest]) * len(rest) / (len(rest) - 1) - w_rest for g in below]
print(f'without document 8733131: run noise {w_rest:.3f}; spread tau^2 per guideline '
      f'{[round(t, 2) for t in taus_rest]}; average {mean(taus_rest):.3f}')

def power(effect_per_doc, n, r, tau2, w, z=1.959964):
    se = sqrt(n * (tau2 + 2 * w / r))
    zz = effect_per_doc * n / se - z
    return 0.5 * (1 + erf(zz / sqrt(2)))

base = mean(per_doc_mean.values())
anchors = {
    'top-4 average reduction on valid100 (10-run means 136.9 -> 126.8, -7.4%)': 0.074 * base,
    '15% reduction': 0.15 * base,
}
print('\npower = chance that the two-sided 95% interval of the paired total excludes 0')
for label, eff in anchors.items():
    print(f'\n{label}: {eff:.3f} fewer true misses per document')
    print('  docs \\ runs per arm ' + ''.join(f'{r:>8d}' for r in (1, 2, 3, 5)))
    for n in (40, 100, 200, 387):
        print(f'  {n:>4d}               ' + ''.join(f'{power(eff, n, r, tau2, w):8.2f}' for r in (1, 2, 3, 5)))
