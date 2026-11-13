"""Read-only check: were the original guideline's true misses ever found in other runs?

Input: nodes/shared/error-analysis/outputs/error_rows.csv (one row per error per run).
A gold mention absent from a run's rows was strictly correct in that run.
'missed' = true miss (no prediction overlaps the gold). Any other state = found.
Offline, no API calls. Run from the repository root:
    python nodes/2026-11-16_seminar/two-step-pilot/scripts/true_miss_recoverability.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/true_miss_recoverability_output.txt
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[4]
ROWS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'nodes/shared/error-analysis/outputs/error_rows.csv'
rows = list(csv.DictReader(ROWS.open(encoding='utf-8')))

runs = sorted({r['run'] for r in rows})
orig_runs = sorted({r['run'] for r in rows if r['guideline'] == 'original'})
mod_runs = sorted(set(runs) - set(orig_runs))
assert len(orig_runs) == 19 and len(mod_runs) == 11, (len(orig_runs), len(mod_runs))

state = defaultdict(dict)          # mention -> run -> kind
info = {}
for r in rows:
    if r['gold_label'] == 'O' or r['kind'] == 'extra':
        continue                    # no gold mention involved
    m = (r['doc'], int(r['gold_start']), int(r['gold_end']))
    k = r['kind']
    prev = state[m].get(r['run'])
    # a mention can appear twice in one run (e.g. label + unpaired); 'missed' only if nothing overlaps
    if prev is None or prev == 'missed':
        state[m][r['run']] = k if prev is None else (prev if k == 'missed' else k)
    info[m] = (r['gold_text'], r['gold_label'], r['context'])

def missed(m, run):
    return state[m].get(run) == 'missed'

def found(m, run):
    return not missed(m, run)       # correct (absent), label, boundary or unpaired

per_run = []
cat_of = {}
for run in orig_runs:
    M = [m for m in state if missed(m, run)]
    a = b = c = 0
    for m in M:
        if any(found(m, o) for o in orig_runs if o != run):
            cat = 'A'
        elif any(found(m, x) for x in mod_runs):
            cat = 'B'
        else:
            cat = 'C'
        a += cat == 'A'; b += cat == 'B'; c += cat == 'C'
    per_run.append((run, len(M), a, b, c))

print('== per original run: true misses split by whether found elsewhere')
print('run | true_miss | A_found_in_other_original_run | B_only_under_modified | C_never_in_30')
for t in per_run:
    print(' | '.join(str(x) for x in t))
print('mean | ' + ' | '.join(f'{mean(t[i] for t in per_run):.1f}' for i in range(1, 5)))

# mention-level view
ever_missed_orig = [m for m in state if any(missed(m, o) for o in orig_runs)]
always_missed_orig = [m for m in ever_missed_orig if all(missed(m, o) for o in orig_runs)]
B_ment = [m for m in always_missed_orig if any(found(m, x) for x in mod_runs)]
C_ment = [m for m in always_missed_orig if not any(found(m, x) for x in mod_runs)]
print()
print(f'== mentions: missed in >=1 original run: {len(ever_missed_orig)}; '
      f'missed in all 19: {len(always_missed_orig)} (found under >=1 modified: {len(B_ment)}; never in 30: {len(C_ment)})')

# how often the A-type mentions are found among the 19 original runs
A_ment = [m for m in ever_missed_orig if m not in set(always_missed_orig)]
hist = Counter(sum(found(m, o) for o in orig_runs) for m in A_ment)
print('A-type mentions (missed in some, found in other original runs): count by number of original runs that found them')
print('  ' + ', '.join(f'{k}/19:{hist[k]}' for k in sorted(hist)))
miss_weight = Counter()
for m in A_ment:
    nmiss = sum(missed(m, o) for o in orig_runs)
    miss_weight['found>=10' if 19 - nmiss >= 10 else 'found<10'] += nmiss
print('  true-miss instances in original runs carried by A mentions found in >=10 vs <10 of 19 runs:',
      dict(miss_weight), '(divide by 19 for per-run means)')

def by_label(ms):
    return dict(Counter(info[m][1] for m in ms).most_common())

print()
print('== gold label of mentions missed in all 19 original runs')
print('  found under >=1 modified guideline (B):', by_label(B_ment))
print('  never found in 30 runs (C):', by_label(C_ment))
print()
print('== C examples (never found in 30 runs), most frequent strings')
for s, n in Counter((info[m][0], info[m][1]) for m in C_ment).most_common(25):
    print(f'  {n} x {s[0]!r} [{s[1]}]')
print()
print('== B examples (missed in all 19 original runs, found under some modified guideline): how many modified runs found them')
for m in sorted(B_ment, key=lambda m: -sum(found(m, x) for x in mod_runs))[:25]:
    k = sum(found(m, x) for x in mod_runs)
    print(f'  {k}/11 {info[m][0]!r} [{info[m][1]}] ...{info[m][2][:90]}')
