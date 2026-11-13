"""Post hoc, not part of the frozen decision rule: S+ minus S on Track 2 true misses, same method as score_pilot.

Reads the per-document counts that score_pilot.py saved in each arm/run metrics.json. Offline. Run from the
repository root:
    python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/posthoc_splus_vs_s.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/20261114_posthoc_splus_vs_s_output.txt
"""
import random
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, RUNS, SEED, read_json  # noqa: E402
from score_pilot import RESAMPLES, percentile  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20261114_haiku-xhigh_pilot_twostep"
names = read_json(RUN / "manifest.json")["pilot_documents"]


def means(folder):
    runs = [read_json(RUN / folder / f"run{r:02d}" / "metrics.json")["per_document"] for r in RUNS]
    return {n: statistics.mean(run[n]["true_misses"] for run in runs) for n in names}


s, s_plus = means("S"), means("Splus")
diff = [s_plus[n] - s[n] for n in names]
rng = random.Random(SEED)
draws = sorted(sum(diff[i] for i in rng.choices(range(len(names)), k=len(names))) for _ in range(RESAMPLES))
print(f"documents {len(names)}; true misses (mean of 2 runs, summed): S {sum(s.values())}, S+ {sum(s_plus.values())}")
print(f"S+ minus S: {sum(diff)}; 95% interval {percentile(draws, 0.025)} to {percentile(draws, 0.975)} "
      f"({RESAMPLES} document resamples, seed {SEED}); post hoc, not pre-registered")
print(f"documents where S+ has fewer / more / equal true misses than S: "
      f"{sum(d < 0 for d in diff)} / {sum(d > 0 for d in diff)} / {sum(d == 0 for d in diff)}")
