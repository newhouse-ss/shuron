"""The 10/30 slide-5 bar chart: why each changed guideline's three bars have the signs they have (11/03).

Offline, no API calls. The chart shows, for each of the 11 changed guidelines, its strict-TP change against the mean of the
19 original-guideline runs on Specific, DiseaseClass and Modifier gold. This script
A. recomputes the 33 bars and groups the guidelines by sign (a value below 0 is negative, as on the slide);
B. splits every bar exactly over construction types defined from text and gold only (no prediction is used to define
   them): each mention adds 1[right in the guideline] minus its share of right among the 19 original runs, so the types of
   one label sum to the bar;
C. reads the hand coding outputs/guideline_practices.csv (which guidelines write each clause, in which direction, at which
   line; every quoted line is checked) and sets each coded clause beside the bar part it bears on;
D. lists, per guideline, the sign pattern and the clauses it follows or breaks.
Types: Specific gold after a relational noun plus of/with (modifier_subset.py B2); coordinated with another gold mention
(only ",", "and", "or", "/" between them); two or more tokens ending in a tumour word; other. DiseaseClass gold: bare
cancer/tumor; signs, symptoms and states (head not a disease or category noun) in a coordinated list; such terms elsewhere;
category nouns. Modifier gold: before a gene or protein noun (modifier_subset.py, 99); bare cancer/tumor; other.
Writes bar_patterns_output.txt and bar_patterns.json.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import re
import runpy
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    m = runpy.run_path(str(HERE / "modifier_subset.py"))
texts, gold, state, orig, mod, name, member, head_group = (
    m[k] for k in ("texts", "gold", "state", "orig", "mod", "name", "member", "head_group"))
ROOT = HERE.parents[2]
OUT = HERE.parent / "outputs"
by = {name[x]: x for x in mod}
ORDER = ["top-4 loop01", "top-4 loop04", "top-4 loop08", "top-4 loop09", "top-4 loop02", "top-1 loop07", "top-1 loop05",
         "top-4 loop06", "top-4 loop07", "top-4 loop05", "top-4 loop10"]
LABS = ["SpecificDisease", "DiseaseClass", "Modifier"]
TUM = re.compile(r"(cancers?|carcinomas?|tumou?rs?|neoplasms?|lymphomas?|sarcomas?|hamartomas?|adenomas?|melanomas?|gliomas?|"
                 r"leuka?emias?|blastomas?)$", re.I)
CAT = re.compile(r"\b(diseases?|disorders?|syndromes?|conditions?|defects?|malformations?|cancers?|tumou?rs?|carcinomas?|"
                 r"neoplasms?|neoplasias?|dysplasias?|dystroph(y|ies)|infections?)$", re.I)
BARE = re.compile(r"(cancers?|tumou?rs?)", re.I)
bydoc = defaultdict(list)
for k in gold:
    bydoc[k[0]].append(k)


def right(x, k):
    return k not in state[x]


def coord(k):
    t = texts[k[0]]
    for j in bydoc[k[0]]:
        a, b = (k, j) if k[2] <= j[1] else (j, k)
        if j != k and a[2] <= b[1] and re.fullmatch(r"\s*(,|and|or|/|and / or|,\s*and|,\s*or)\s*", t[a[2]:b[1]]):
            return True
    return False


def typ(k):
    t = texts[k[0]][k[1]:k[2]].strip()
    if k[3] == "Modifier":
        if k in member and "B1" in member[k] and head_group(k).startswith("molecular"):
            return "M before gene/protein noun"
        return "M bare cancer/tumor" if BARE.fullmatch(t) else "M other"
    if k[3] == "CompositeMention":
        return "Composite"
    rel = k in member and "B2" in member[k]
    if k[3] == "SpecificDisease":
        if rel:
            return "S after relational noun"
        if coord(k):
            return "S coordinated"
        return "S tumour word, 2+ tokens" if TUM.search(t) and len(t.split()) >= 2 else "S other"
    if BARE.fullmatch(t):
        return "D bare cancer/tumor"
    if rel:
        return "D after relational noun"
    if not CAT.search(t):
        return "D sign/state in a list" if coord(k) else "D sign/state elsewhere"
    return "D category noun"


T = defaultdict(list)
for k in gold:
    T[typ(k)].append(k)
p_right = {k: sum(right(x, k) for x in orig) / len(orig) for k in gold}


def part(n, t):
    return sum((1 if right(by[n], k) else 0) - p_right[k] for k in T[t])


out, rec = [], {}
short = lambda n: n.replace("top-", "").replace(" loop", "-")

# ---------- A ----------
bars = {n: {lab: sum((1 if right(by[n], k) else 0) - p_right[k] for k in gold if k[3] == lab) for lab in LABS} for n in ORDER}
sign = {n: "".join("+" if bars[n][lab] > 0 else "-" for lab in LABS) for n in ORDER}
out.append("A. Strict-TP change against the 19-run original mean (the slide-5 bars), and the sign pattern S/D/M")
for n in ORDER:
    out.append(f"   {n:<13} " + "  ".join(f"{lab[:4]} {bars[n][lab]:+6.1f}" for lab in LABS) + f"   {sign[n]}")
groups = defaultdict(list)
for n in ORDER:
    groups[sign[n]].append(n)
out.append("   groups: " + "; ".join(f"{s}: {', '.join(v)}" for s, v in groups.items()))
rec["bars"], rec["sign"] = bars, sign

# ---------- B ----------
out.append("\nB. Each bar split over construction types (columns in the order of A; rows of one label sum to its bar)")
out.append(f"   {'type':<28} {'n':>4} {'orig':>6} " + " ".join(f"{short(n):>6}" for n in ORDER))
rec["parts"] = {}
for lab, pre in zip(LABS, "SDM"):
    for t in sorted(x for x in T if x.startswith(pre + " ")):
        o = sum(p_right[k] for k in T[t])
        out.append(f"   {t:<28} {len(T[t]):4} {o:6.1f} " + " ".join(f"{part(n, t):+6.1f}" for n in ORDER))
        rec["parts"][t] = {n: part(n, t) for n in ORDER}
    chk = {n: sum(part(n, t) for t in T if t.startswith(pre + " ")) - bars[n][lab] for n in ORDER}
    assert all(abs(v) < 1e-9 for v in chk.values()), chk
    out.append(f"   {'= ' + lab + ' bar':<28} {'':4} {'':6} " + " ".join(f"{bars[n][lab]:+6.1f}" for n in ORDER))

# ---------- C ----------
RUNS = ROOT / "outputs" / "ncbi_disease"


def gl(n):
    f = RUNS / f"20261022_haiku-xhigh_{'topk1' if n.startswith('top-1') else 'topk4'}_loop{n[-2:]}" / "final" / "final_guidelines.txt"
    return f.read_text(encoding="utf-8").splitlines()


rows = list(csv.DictReader((OUT / "guideline_practices.csv").open(encoding="utf-8")))
bad = [(r["guideline"], r["line"]) for r in rows if r["words"] not in gl(r["guideline"])[int(r["line"]) - 1]]
assert not bad, bad


def dc_as_spec(n):
    ks = [k for k in gold if k[3] == "DiseaseClass"]
    lab = lambda x, k: state[x].get(k, ("r", "", ""))
    o = statistics.mean(sum(lab(x, k)[0] == "label" and lab(x, k)[2] == "SpecificDisease" for k in ks) for x in orig)
    return -(sum(lab(by[n], k)[0] == "label" and lab(by[n], k)[2] == "SpecificDisease" for k in ks) - o)


EFFECT = {"gene names": ("Modifier gold before a gene/protein noun", lambda n: part(n, "M before gene/protein noun")),
          "relational nouns": ("Specific gold after a relational noun", lambda n: part(n, "S after relational noun")),
          "site words": ("Specific gold, 2+ tokens ending in a tumour word", lambda n: part(n, "S tumour word, 2+ tokens")),
          "coordination": ("Specific gold coordinated with another", lambda n: part(n, "S coordinated")),
          "manifestations": ("DiseaseClass signs/states, in lists and elsewhere",
                             lambda n: part(n, "D sign/state in a list") + part(n, "D sign/state elsewhere")),
          "bare cancer": ("bare cancer/tumor, DiseaseClass and Modifier gold",
                          lambda n: part(n, "D bare cancer/tumor") + part(n, "M bare cancer/tumor")),
          "patient promotion": ("DiseaseClass gold not labelled Specific (minus the original)", dc_as_spec)}
out.append("\nC. Each coded clause beside the bar part it bears on (good = the direction of the gold convention)")
rec["practices"] = {}
for pr, (what, f) in EFFECT.items():
    st = {r["guideline"]: (r["stance"], r["line"]) for r in rows if r["practice"] == pr}
    out.append(f"   {pr}: {what}")
    res = {}
    for s in ("good", "bad", "silent"):
        ns = [n for n in ORDER if st.get(n, ("silent",))[0] == s]
        if ns:
            vals = [f(n) for n in ns]
            res[s] = {n: f(n) for n in ns}
            out.append(f"      {s:<7} mean {statistics.mean(vals):+6.1f}: " + ", ".join(
                f"{n} {f(n):+.1f}" + (f" (L{st[n][1]})" if n in st else "") for n in ns))
    rec["practices"][pr] = res

# ---------- D ----------
out.append("\nD. Per guideline: sign pattern, clauses written in the gold direction (+) and against it (-)")
for n in ORDER:
    g_ = [r["practice"] for r in rows if r["guideline"] == n and r["stance"] == "good"]
    b_ = [r["practice"] for r in rows if r["guideline"] == n and r["stance"] == "bad"]
    out.append(f"   {n:<13} {sign[n]}  + {', '.join(dict.fromkeys(g_)) or '-'}  | - {', '.join(dict.fromkeys(b_)) or '-'}")
out.append(f"\nQuoted guideline lines checked: {len(rows)}, all contain the quoted words")
(OUT / "bar_patterns.json").write_bytes((json.dumps(rec, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
(OUT / "bar_patterns_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
