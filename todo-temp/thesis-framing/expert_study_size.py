"""How many documents an expert-annotation study needs, and what it may cost (ESTIMATES).

Part 1 (measured from saved runs): resample n of the 100 valid100 documents with replacement and report the
95% interval half-width of (a) one run's strict F1 and (b) a paired difference between two runs on the same
documents. This approximates how precise an n-document study would be. Loader and scorer copy
todo-temp/direction-scan/offline_direction_checks.py.

Part 2 (assumptions, not data): documents per condition for a timing study, and hours and yen for the study.
    per-entity time 28.7 to 52.7 s (Lingren et al. 2014, Table 3, pre-annotated and manual sets);
    BioRED: about 2 h per annotator per 20-article batch for entities, 34 entity spans per document (Luo et al. 2022);
    NCBI valid100: 791 gold mentions in 100 documents.
    Training time per annotator and hourly rates are placeholders to be replaced with real figures.

    python todo-temp/thesis-framing/expert_study_size.py
"""
import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD_VALID = ROOT / "data/datasets/ncbi_disease/valid"
RUNS = {
    "original": ("outputs/ncbi_disease/20260802_gpt54-high_valid-G", 0.7792),
    "R4": ("outputs/ncbi_disease/20260802_gpt54-high_valid-M", 0.7878),
    "R4_rerun": ("outputs/ncbi_disease/20260824_gpt54-high_valid-published-rerun", 0.7789),
    "topk4": ("outputs/20261007_ncbi_gpt54-high_valid-topk4", 0.8023),
}


def load_dir(d):
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(d).glob("*.json"))}


def ents(doc):
    return [(d["span"]["begin"], d["span"]["end"], d["obj"]) for d in doc["denotations"]]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


docs = load_dir(GOLD_VALID)
names = sorted(docs)
gold = {n: ents(d) for n, d in docs.items()}
runs = {}
for label, (rel, expected) in RUNS.items():
    pred = {n: ents(d) for n, d in load_dir(ROOT / rel).items()}
    assert set(pred) == set(names), label
    runs[label] = pred


def rows(pred):
    out = []
    for n in names:
        gc, pc = Counter(gold[n]), Counter(pred[n])
        c = sum((gc & pc).values())
        out.append((c, sum(pc.values()) - c, sum(gc.values()) - c))
    return out


R = {k: rows(v) for k, v in runs.items()}
for k, (_, expected) in RUNS.items():
    got = prf(*[sum(r[j] for r in R[k]) for j in range(3)])
    assert abs(got - expected) < 1e-4, (k, got)


def halfwidth(fn, n, reps=4000, seed=7):
    rng = random.Random(seed)
    vals = sorted(fn([rng.randrange(len(names)) for _ in range(n)]) for _ in range(reps))
    return (vals[int(0.975 * reps)] - vals[int(0.025 * reps)]) / 2


def f1_of(key):
    return lambda idx: prf(*[sum(R[key][i][j] for i in idx) for j in range(3)])


def diff_of(a, b):
    return lambda idx: f1_of(a)(idx) - f1_of(b)(idx)


lines = ["== Part 1: 95% interval half-width when n valid100 documents are annotated (resampled from saved runs)",
         "n   | one run's strict F1 (topk4) | paired diff, different guidelines (topk4 - original) | paired diff, same guideline (R4 - R4_rerun)"]
for n in (20, 30, 40, 50, 60, 80, 100):
    lines.append(f"{n:<3} | {halfwidth(f1_of('topk4'), n):.3f} | {halfwidth(diff_of('topk4', 'original'), n):.3f} | "
                 f"{halfwidth(diff_of('R4', 'R4_rerun'), n):.3f}")
mentions = sum(len(v) for v in gold.values())
lines.append(f"gold mentions in valid100: {mentions} ({mentions / len(names):.2f} per document)")

lines.append("")
lines.append("== Part 2a: documents per condition for a timing study (ASSUMED coefficient of variation of time per document;")
lines.append("   two-sided alpha 0.05, power 0.8, unpaired; a design paired by document needs fewer)")
z = 1.959964 + 0.841621
for cv in (0.3, 0.5, 0.7):
    cells = [f"saving {int(s * 100)}%: {math.ceil(2 * (z * cv / s) ** 2)}" for s in (0.15, 0.2, 0.3)]
    lines.append(f"CV {cv}: " + ", ".join(cells))

lines.append("")
lines.append("== Part 2b: minutes per document from published speeds x 7.91 NCBI mentions per document")
per_doc = {"Lingren fast (28.7 s/entity)": 28.7 * mentions / len(names) / 60,
           "Lingren slow (52.7 s/entity)": 52.7 * mentions / len(names) / 60,
           "BioRED (2 h / (20 docs x 34 spans) per span)": 7200 / (20 * 34) * mentions / len(names) / 60}
for k, v in per_doc.items():
    lines.append(f"{k}: {v:.1f} min per document")
lo, hi = min(per_doc.values()), max(per_doc.values())

lines.append("")
lines.append("== Part 2c: study hours and yen (PLACEHOLDER training hours and hourly rates)")
TRAIN_H = (4, 8)
RATES = (1500, 3000, 5000)
designs = {"pilot: 1 annotator x 40 docs (20 scratch + 20 with LLM)": (1, 40),
           "crossover: 2 annotators x 100 docs (each doc once scratch, once with LLM)": (2, 200)}
for name, (people, doc_annotations) in designs.items():
    h_lo = doc_annotations * lo / 60 + people * TRAIN_H[0]
    h_hi = doc_annotations * hi / 60 + people * TRAIN_H[1]
    cost = ", ".join(f"JPY {r:,}/h: {h_lo * r:,.0f} to {h_hi * r:,.0f}" for r in RATES)
    lines.append(f"{name}: {h_lo:.1f} to {h_hi:.1f} hours | {cost}")

out = "\n".join(lines)
(Path(__file__).resolve().parent / "expert_study_size_output.txt").write_text(out + "\n", encoding="utf-8")
print(out)
