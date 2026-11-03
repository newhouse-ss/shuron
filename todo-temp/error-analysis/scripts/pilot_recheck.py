"""New cases for checking the revised classification (10/28 v2), drawn by boundary type from text and gold only.

Offline, no API calls. Reuses pilot_cases.py (run states from error_rows.csv). Mentions and documents of the first
30 pilot cases are excluded. Each boundary finder below looks only at the validation text and gold; one or two
candidates per finder are drawn with seed 20261029, plus three random control mentions. Two output files:
  pilot_recheck_text.txt   text and gold only (coded first)
  pilot_recheck_pred.txt   the predictions of all 30 runs for the same cases (read after coding the text)
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import re
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(HERE / "pilot_cases.py"))
texts, gold, state, extra, runs, orig, mod, name = (g[k] for k in ("texts", "gold", "state", "extra", "runs", "orig", "mod", "name"))
OUTDIR = HERE.parent / "outputs"
pilot = json.loads((OUTDIR / "pilot_cases.json").read_text(encoding="utf-8"))
used_docs = {c["doc"] for c in pilot}
pool = [k for k in gold if k[0] not in used_docs]

HEAD = r"(gene|genes|protein|mRNA|locus|alleles?|mutations?|families|kindreds|patients|cases|carriers|cells?|mice|phenotype|susceptibility)"


def after(k, n=40):
    return texts[k[0]][k[2]:k[2] + n]


def before(k, n=60):
    return texts[k[0]][max(0, k[1] - n):k[1]]


def s(k):
    return texts[k[0]][k[1]:k[2]]


FINDERS = {
    "parenthetical before head noun": (1, lambda k: re.match(r"\s*\(\s*[\w-]+\s*\)\s+" + HEAD + r"\b", after(k)) is not None),
    "relational complement": (2, lambda k: re.search(r"\b(patients|carriers|families|individuals|frequency|incidence|prevalence|risk|history|cases?)\s+(with|of|for)\s+$", before(k), re.I) is not None),
    "short symbol before gene word": (1, lambda k: re.fullmatch(r"[A-Z0-9-]{2,6}", s(k)) is not None and re.match(r"\s+(gene|protein|mRNA)\b", after(k)) is not None),
    "finding in a feature list": (2, lambda k: k[3] == "DiseaseClass" and re.search(r"(characterized by|including|such as|features?|symptoms?|signs?)[^.]{0,80}$", before(k, 120), re.I) is not None
                                  and not re.search(r"(disease|disorder|syndrome|cancer|tumou?r|carcinoma)s?$", s(k), re.I)),
    "age or severity qualifier": (2, lambda k: re.match(r"(early-onset|late-onset|severe|mild|childhood|juvenile|adult|congenital|primary)\b", s(k), re.I) is not None
                                  or re.search(r"\b(early-onset|late-onset|severe|mild|childhood|juvenile|adult|congenital|primary)\s+$", before(k, 20), re.I) is not None),
    "coordinated qualifiers": (1, lambda k: re.search(r"\b(type|stage|form)s?\s+\w+\s+(and|or)\s+", s(k), re.I) is not None
                               or re.search(r"\w+\s+(and|or)\s+\w+\s+forms?\s+of\s+$", before(k, 40), re.I) is not None),
    "general head noun": (1, lambda k: k[3] == "DiseaseClass" and re.search(r"\b(disease|diseases|disorder|disorders|syndromes)$", s(k)) is not None),
}

rng = random.Random(20261029)
picked, seen = [], set()
for ftype, (n, f) in FINDERS.items():
    cand = [k for k in pool if f(k) and k not in seen]
    for k in rng.sample(cand, min(n, len(cand))):
        picked.append((ftype, len(cand), k))
        seen.add(k)
# extras: one extra made in exactly one run, one prediction-side unpaired overlap
xo = {}
for x in runs:
    for k in extra[x]:
        xo.setdefault(k, set()).add(x)
cand = [k for k, rs in xo.items() if len(rs) == 1 and k[0] not in used_docs]
k = rng.choice(sorted(cand))
picked.append(("extra in one run", len(cand), k))
import csv
rows = list(csv.DictReader((OUTDIR / "error_rows.csv").open(encoding="utf-8")))
upr = sorted({(r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"]) for r in rows if r["kind"] == "unpaired" and r["pred_text"] and r["doc"] not in used_docs})
k = rng.choice(upr)
picked.append(("prediction-side unpaired", len(upr), k))
for k in rng.sample([k for k in pool if k not in seen], 3):
    picked.append(("random control", len(pool), k))

text_out, pred_out = [], []
for i, (ftype, n, k) in enumerate(picked, 1):
    d, b, e, lab = k
    t = texts[d]
    ctx = (t[max(0, b - 180):b] + "[[" + t[b:e] + "]]" + t[e:e + 180]).replace("\n", " ")
    gold_near = [(t[x[1]:x[2]], x[3], x[1], x[2]) for x in gold if x[0] == d and x[2] > b - 180 and x[1] < e + 180 and x[:3] != k[:3]]
    kind = "prediction" if ftype in ("extra in one run", "prediction-side unpaired") else "gold"
    text_out.append(f"N{i:02d} [{ftype}; {n} candidates] {d} {b}-{e} {kind} {lab} {t[b:e]!r}")
    text_out.append(f"   other gold nearby: {gold_near}")
    text_out.append(f"   context: {ctx}")
    pred_out.append(f"N{i:02d} {d} {b}-{e} {t[b:e]!r}")
    if kind == "gold":
        for x in runs:
            st = state[x].get(k)
            if st:
                pred_out.append(f"   {name[x]:<14} {'orig' if x in orig else 'mod '} {st[0]} -> {st[1]!r} {st[2]}")
        pred_out.append(f"   right in {sum(k not in state[x] for x in orig)}/19 orig, {sum(k not in state[x] for x in mod)}/11 mod")
    else:
        rs = [name[x] for x in runs if k in extra[x]] or [name[r['run']] for r in rows if r['kind'] == 'unpaired' and r['pred_text'] and (r['doc'], int(r['pred_start']), int(r['pred_end']), r['pred_label']) == k]
        pred_out.append(f"   made by: {rs}")
(OUTDIR / "pilot_recheck_text.txt").write_bytes(("\n".join(text_out) + "\n").encode("utf-8"))
(OUTDIR / "pilot_recheck_pred.txt").write_bytes(("\n".join(pred_out) + "\n").encode("utf-8"))
print(len(picked), "cases")
