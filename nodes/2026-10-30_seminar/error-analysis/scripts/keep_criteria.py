"""What other keep criteria would have done to the 44 recorded rounds, compared with "development F1 rises".

Offline, no API calls. A round is kept when development F1 rises (the current criterion). This script asks, round by
round, what a few alternative criteria would have decided. It is retrospective: a different decision in one round would
change every later round of that loop, so it cannot say where a loop would have ended.

Chance level for gains and losses on the development documents: round 1 of each of the 20 loops starts from the
original guideline, so the "before" runs of the 20 first rounds are 20 runs of one guideline on the same 10 documents.
Every ordered pair of them gives a chance count of development gold mentions that went from right to wrong (broken)
and from wrong to right (fixed), with no change of guideline. A mention is right when a prediction has its exact span
and label.

Criteria:
  C0  development F1 rises (current);
  C1  development F1 rises by more than luck alone gives 1 time in 20 (normal, SD 0.021 for the difference of two runs);
  C2  development F1 rises and the round broke no more mentions than the 95th percentile of the chance pairs;
  C3  C1 and C2 together.
Groups of rounds: the 9 rounds that let in the 15 contradicting statements (topk4_stability.json), the 16 rounds that
first wrote a family-history Modifier rule and the 3 that reversed it to Specific (history_tally_output.txt).

Writes keep_criteria_output.txt and keep_criteria.json.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
DATA = ROOT / "data" / "datasets" / "ncbi_disease"
NOISE = 0.021
ORIGINAL = (ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt").read_text(encoding="utf-8").replace("\r\n", "\n")

dev_files = [d["filename"] for d in json.loads((OUT / "20261022_haiku-xhigh_topk4_loop08" / "inputs" / "sampled_train_documents.json").read_text(encoding="utf-8"))]
gold = {}
for f in dev_files:
    d = json.loads((DATA / "train" / f).read_text(encoding="utf-8"))
    gold[f] = {(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d["denotations"]}
n_gold = sum(len(v) for v in gold.values())


def right(diag: dict) -> set:
    """Development gold mentions a run got exactly right."""
    out = set()
    for f in diag["files"]:
        pred = {(d["start"], d["end"], d["label"]) for d in f["study_denotations"]}
        out |= {(f["filename"], *g) for g in gold[f["filename"]] & pred}
    return out


rounds = []
baselines = []
for k in ("topk1", "topk4"):
    for i in range(1, 11):
        loop = f"{k}_loop{i:02d}"
        for sp in sorted((OUT / f"20261022_haiku-xhigh_{loop}" / "rounds").glob("iteration_*/snapshot.json")):
            s = json.loads(sp.read_text(encoding="utf-8"))
            rb, rc = right(s["diagnostics_before"]), right(s["diagnostics_candidate"])
            d = s["summary_candidate"]["overall_f1"] - s["summary_before"]["overall_f1"]
            rounds.append({"loop": loop, "round": s["iteration"], "kept": s["improved"], "gain": d,
                           "broken": len(rb - rc), "fixed": len(rc - rb)})
            if s["iteration"] == 1:
                assert s["guidelines_before"].replace("\r\n", "\n").strip() == ORIGINAL.strip(), loop
                baselines.append(rb)
assert len(rounds) == 44 and len(baselines) == 20
assert all(r["kept"] == (r["gain"] > 0) for r in rounds)  # the recorded decision is C0

pairs_broken = sorted(len(a - b) for i, a in enumerate(baselines) for j, b in enumerate(baselines) if i != j)
q95 = pairs_broken[int(0.95 * (len(pairs_broken) - 1))]
cut = statistics.NormalDist(0, NOISE).inv_cdf(0.95)

out = [f"Development gold mentions: {n_gold} in {len(gold)} documents",
       f"Chance, two runs of the original guideline (20 runs, {len(pairs_broken)} ordered pairs): mentions broken "
       f"mean {statistics.mean(pairs_broken):.1f}, 95th percentile {q95}, max {max(pairs_broken)}",
       f"C1 threshold: development F1 gain above {cut:.4f}", ""]

CRIT = {
    "C0 F1 rises (current)": lambda r: r["gain"] > 0,
    "C1 gain beyond luck (1 in 20)": lambda r: r["gain"] > cut,
    f"C2 F1 rises, broken <= {q95}": lambda r: r["gain"] > 0 and r["broken"] <= q95,
    "C3 C1 and C2": lambda r: r["gain"] > cut and r["broken"] <= q95,
}

stab = json.loads((HERE / "topk4_stability.json").read_text(encoding="utf-8"))
contra = {("topk4_" + o["loop"].split()[1], o["round"]) for o in stab["origins"]}
hist = []
for line in (HERE / "history_tally_output.txt").read_text(encoding="utf-8").split("\n")[2:]:
    m = re.match(r"\s+(topk[14]_loop\d+)\s+(\d+) (kept|rejected)\s+(yes|no)\s+(no rule|Modifier|Specific|other)\s+(no rule|Modifier|Specific|other)\s", line)
    if m:
        hist.append(m.groups())
assert len(hist) == 44
fh_new = {(h[0], int(h[1])) for h in hist if h[4] == "no rule" and h[5] == "Modifier"}
fh_rev = {(h[0], int(h[1])) for h in hist if h[4] == "Modifier" and h[5] == "Specific"}
GROUPS = {
    "all 44 rounds": {(r["loop"], r["round"]) for r in rounds},
    "29 top-4 rounds": {(r["loop"], r["round"]) for r in rounds if r["loop"].startswith("topk4")},
    "9 rounds that let in contradicting statements": contra,
    f"{len(fh_new)} rounds that first wrote the family-history Modifier rule": fh_new,
    f"{len(fh_rev)} rounds that reversed it to Specific": fh_rev,
}
assert len(contra) == 9 and len(fh_new) == 16 and len(fh_rev) == 3

rec = {"n_gold": n_gold, "chance_broken": {"mean": statistics.mean(pairs_broken), "q95": q95, "max": max(pairs_broken)},
       "c1_threshold": cut, "rounds": rounds, "pass": {}}
out.append("Rounds each criterion would keep (retrospective, one round at a time)")
out.append(f"   {'criterion':<34}" + "".join(f" | {g}" for g in GROUPS))
for name, f in CRIT.items():
    cells = []
    for g, keys in GROUPS.items():
        rs = [r for r in rounds if (r["loop"], r["round"]) in keys]
        assert len(rs) == len(keys), g
        n = sum(1 for r in rs if f(r))
        rec["pass"].setdefault(name, {})[g] = [n, len(rs)]
        cells.append(f"{n} of {len(rs)}")
    out.append(f"   {name:<34}" + "".join(f" | {c}" for c in cells))

out.append("\nThe 9 rounds that let in contradicting statements, and the 3 reversal rounds")
for keys, label in ((contra, "contradicting"), (fh_rev, "reversal")):
    for r in rounds:
        if (r["loop"], r["round"]) in keys:
            verdict = ", ".join(n.split()[0] for n, f in CRIT.items() if f(r)) or "none"
            out.append(f"   {label:<13} {r['loop']} r{r['round']}: gain {r['gain']:+.3f}, broken {r['broken']}, fixed {r['fixed']}; kept by {verdict}")

kept = [r for r in rounds if r["kept"]]
out.append(f"\nKept rounds (C0): {len(kept)}; broken mentions per kept round: mean {statistics.mean(r['broken'] for r in kept):.1f}, "
           f"range {min(r['broken'] for r in kept)} to {max(r['broken'] for r in kept)}; "
           f"above the chance 95th percentile ({q95}): {sum(1 for r in kept if r['broken'] > q95)}")

(HERE / "keep_criteria_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
(HERE / "keep_criteria.json").write_bytes(json.dumps(rec, ensure_ascii=False, indent=1).encode("utf-8"))
print("\n".join(out))
