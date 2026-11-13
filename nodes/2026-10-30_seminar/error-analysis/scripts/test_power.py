"""How many runs per arm would a test of one guideline change on the 50 held-out documents need?

Offline, no API calls. Uses the 19 original-guideline validation runs (error_patterns.json) as the model of
run-to-run noise. For 2000 random halves (50 documents) of the validation set it computes, per run, strict F1,
true misses (gold mentions no prediction overlaps) and gene-word misses (gold mentions directly before a gene or
protein word, patterns_lib.AFTER_GENE, not predicted exactly), and the SD of each across the 19 runs. Runs per
arm for a two-sided test at 5% with 80% power: n = 2 (1.960 + 0.842)^2 SD^2 / effect^2.

Also: the F1 effect, at the mean of the 19 runs, of fixing or breaking k mentions; and how many gene-word gold
mentions a random set of 50 training documents holds (training minus the 50 test documents and the 10 development
documents; the test documents' gold is not read).

Writes test_power_output.txt.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
DATA = ROOT / "data" / "datasets" / "ncbi_disease"
OUT = ROOT / "outputs" / "ncbi_disease"

from patterns_lib import AFTER_GENE  # noqa: E402

SEED, DRAWS = 20261025, 2000
Z = 1.959964 + 0.841621
orig = [r["run"] for r in json.loads((HERE / "error_patterns.json").read_text(encoding="utf-8"))["runs"] if r["guideline"] == "original"]
assert len(orig) == 19


def load(path: Path) -> tuple[str, set]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("text", ""), {(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d.get("denotations", [])}


docs = sorted(p.name for p in (DATA / "valid").glob("*.json"))
gold = {d: load(DATA / "valid" / d) for d in docs}
gene_gold = {d: {g for g in gold[d][1] if g[2] == "Modifier" and AFTER_GENE.match(gold[d][0][g[1]:g[1] + 40])} for d in docs}
per = {}
for run in orig:
    per[run] = {}
    for d in docs:
        pred = load(OUT / run / "valid_predictions" / d)[1]
        g = gold[d][1]
        miss = sum(1 for a in g if not any(min(a[1], b[1]) > max(a[0], b[0]) for b in pred))
        per[run][d] = (len(g & pred), len(pred - g), len(g - pred), miss, len(gene_gold[d] - pred))
    tp, fp, fn = (sum(v[i] for v in per[run].values()) for i in range(3))
    saved = json.loads((OUT / run / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    assert (tp, fp, fn) == (saved["true_positives"], saved["false_positives"], saved["false_negatives"]), run

out = [f"check: strict TP/FP/FN reproduce valid_metrics.json for the {len(orig)} original-guideline runs"]


def measures(run: str, subset: list[str]) -> tuple[float, int, int]:
    tp, fp, fn, miss, gene = (sum(per[run][d][i] for d in subset) for i in range(5))
    return 2 * tp / (2 * tp + fp + fn), miss, gene


rng = random.Random(SEED)
halves = [rng.sample(docs, 50) for _ in range(DRAWS)]
sds = {k: [] for k in ("F1", "true misses", "gene-word misses")}
for h in halves:
    vals = [measures(r, h) for r in orig]
    for i, k in enumerate(sds):
        sds[k].append(statistics.stdev(v[i] for v in vals))
full = [measures(r, docs) for r in orig]
out.append(f"\nRun-to-run SD over the 19 runs: all 100 documents, and the mean over {DRAWS} random halves of 50 (seed {SEED})")
for i, k in enumerate(sds):
    out.append(f"   {k:<17} 100 docs {statistics.stdev(v[i] for v in full):7.4f}   50 docs {statistics.mean(sds[k]):7.4f}"
               f"   (mean per run on 50 docs: {statistics.mean(v[i] for h in halves[:200] for v in [measures(r, h) for r in orig]):.3f})")
out.append("\nRuns per arm, two-sided 5%, power 80%, 50 documents")
for k, effects in (("F1", (0.01, 0.015, 0.02)), ("true misses", (3, 5, 8)), ("gene-word misses", (3, 5, 8))):
    sd = statistics.mean(sds[k])
    out.append(f"   {k:<17} " + "; ".join(f"effect {e}: {math.ceil(2 * Z ** 2 * sd ** 2 / e ** 2)}" for e in effects))

# comparing two loop methods instead of two fixed guidelines: one validation run per loop, so the SD is the
# loop-to-loop spread of the 10 top-4 loops
top4 = [f"20261022_haiku-xhigh_topk4_loop{i:02d}" for i in range(1, 11)]
for run in top4:
    per[run] = {}
    for d in docs:
        pred = load(OUT / run / "valid_predictions" / d)[1]
        g = gold[d][1]
        per[run][d] = (len(g & pred), len(pred - g), len(g - pred), 0, 0)
loop_sd = statistics.mean(statistics.stdev(measures(r, h)[0] for r in top4) for h in halves)
out.append(f"   comparing loop methods (one validation run per loop; SD of F1 over the 10 top-4 loops on 50 docs {loop_sd:.4f}): "
           + "; ".join(f"effect {e}: {math.ceil(2 * Z ** 2 * loop_sd ** 2 / e ** 2)} loops" for e in (0.02, 0.03)))

tp, fp, fn = (statistics.mean(sum(per[r][d][i] for d in docs) for r in orig) for i in range(3))
base = 2 * tp / (2 * tp + fp + fn)
out.append(f"\nF1 effect at the mean of the 19 runs (TP {tp:.1f}, FP {fp:.1f}, FN {fn:.1f}, F1 {base:.4f}), 100 documents")
for k in (5, 13, 22, 26):
    out.append(f"   {k:>2} missed mentions found:              {2 * (tp + k) / (2 * (tp + k) + fp + fn - k) - base:+.4f}")
for m in (5, 10, 20):
    out.append(f"   {m:>2} correct mentions given another label: {2 * (tp - m) / (2 * (tp - m) + fp + m + fn + m) - base:+.4f}")

test = set(json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))["documents"])
dev = {d["filename"] for d in json.loads((OUT / "20261022_haiku-xhigh_topk4_loop08" / "inputs" / "sampled_train_documents.json").read_text(encoding="utf-8"))}
pool = [p for p in sorted((DATA / "train").glob("*.json")) if p.name not in test and p.name not in dev]
gene_train = []
for p in pool:
    t, g = load(p)
    gene_train.append(sum(1 for a in g if a[2] == "Modifier" and AFTER_GENE.match(t[a[1]:a[1] + 40])))
counts = sorted(sum(rng.sample(gene_train, 50)) for _ in range(DRAWS))
out.append(f"\nGene-word gold mentions: validation {sum(len(v) for v in gene_gold.values())} in 100 documents; random 50 of the "
           f"{len(pool)} other training documents: median {counts[DRAWS // 2]}, 5-95% {counts[DRAWS // 20]}-{counts[-DRAWS // 20]}")

(HERE / "test_power_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
