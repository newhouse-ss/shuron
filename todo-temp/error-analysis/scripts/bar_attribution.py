"""Slide-5 bars, second version (11/03, after the review): which bar parts are outside the noise, and which clauses they meet.

Offline, no API calls. Replaces the attribution of bar_patterns.py, keeps its exact split. Inputs:
  outputs/bar_attribution_rules.json  categories, the error type each clause option predicts, the evidence rule; frozen
                                      before any recomputation, its SHA-256 is asserted below
  outputs/blind_clause_coding.csv     clause coding of the 11 final guidelines and the original by a coder who saw only the
                                      guideline texts (no results); line numbers and quotes are checked here
  error_rows.csv via pilot_cases.py, modifier_subset.py (contexts), 20261030_rationale_audit/prediction_index.jsonl (cited
  sections of every saved prediction), final guidelines.
A. The 33 bars, their sign groups, and whether each bar lies outside the 19 original runs' range.
B. Each bar split exactly over the frozen categories; each part with the original mean and range; the count of parts outside
   range against the count expected if every changed guideline were one more original run (about 1 in 10, see report 读前须知).
C. Each predicted error type per guideline, with the original mean and range.
D. Each coded clause option: its category part, its predicted error type, and the share of the guideline's changed
   predictions in that category whose citation names the clause's section; credited when at least two of the three hold.
E. Controls: DiseaseClass categories a guideline's clauses do not govern, for guidelines whose clauses predict DiseaseClass losses.
F. Per guideline: parts outside range, the clauses credited, and the parts left unexplained.
Writes bar_attribution_output.txt and bar_attribution.json.
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import re
import runpy
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
ROOT = HERE.parents[2]
RULES = OUT / "bar_attribution_rules.json"
assert hashlib.sha256(RULES.read_bytes()).hexdigest().startswith("6fc87d4c82e2"), "rules changed after freezing"
with contextlib.redirect_stdout(io.StringIO()):
    m = runpy.run_path(str(HERE / "modifier_subset.py"))
texts, gold, state, orig, mod, name, member, head_group = (
    m[k] for k in ("texts", "gold", "state", "orig", "mod", "name", "member", "head_group"))
by = {name[x]: x for x in mod}
ORDER = ["top-4 loop01", "top-4 loop04", "top-4 loop08", "top-4 loop09", "top-4 loop02", "top-1 loop07", "top-1 loop05",
         "top-4 loop06", "top-4 loop07", "top-4 loop05", "top-4 loop10"]
LABS = ["SpecificDisease", "DiseaseClass", "Modifier"]
short = lambda n: n.replace("top-", "").replace(" loop", "-")
TUM = re.compile(r"(cancers?|carcinomas?|tumou?rs?|neoplasms?|lymphomas?|sarcomas?|hamartomas?|adenomas?|melanomas?|gliomas?|"
                 r"leuka?emias?|blastomas?)$", re.I)
CATW = re.compile(r"^(diseases?|disorders?|syndromes?|conditions?|defects?|malformations?|cancers?|tumou?rs?|carcinomas?|neoplasms?|"
                  r"neoplasias?|dysplasias?|dystroph(y|ies)|infections?)$|(itis|pathy|plegia|osis|omas?)$", re.I)
BARE = re.compile(r"(cancers?|tumou?rs?)", re.I)
bydoc = defaultdict(list)
for k in gold:
    bydoc[k[0]].append(k)


def coord(k):
    t = texts[k[0]]
    for j in bydoc[k[0]]:
        a, b = (k, j) if k[2] <= j[1] else (j, k)
        if j != k and a[2] <= b[1] and re.fullmatch(r"\s*(,|and|or|/|and / or|,\s*and|,\s*or)\s*", t[a[2]:b[1]]):
            return True
    return False


def rel(k):
    return k in member and "B2" in member[k]


def head(t):
    w = t.split(" of ")[0].split()
    return w[-1] if w else t


def cat(k):
    t = texts[k[0]][k[1]:k[2]].strip()
    if k[3] == "Modifier":
        if BARE.fullmatch(t):
            return "M bare cancer/tumor"
        if t.endswith("deficient"):
            return "M deficient adjective"
        if re.search(r" and | or | / ", t):
            return "M coordinated names"
        if k in member and "B1" in member[k] and head_group(k).startswith("molecular"):
            return "M full name before gene/protein noun" if re.search(r"[a-z]{4,}", t) else "M abbreviation before gene/protein noun"
        return "M other"
    if k[3] == "CompositeMention":
        return "Composite"
    if k[3] == "SpecificDisease":
        if rel(k):
            return "S after relational noun"
        if coord(k):
            return "S coordinated"
        return "S tumour word" if TUM.search(t) and len(t.split()) >= 2 else "S other"
    if BARE.fullmatch(t):
        return "D bare cancer/tumor"
    if rel(k):
        return "D after relational noun"
    if CATW.search(head(t)):
        return "D named or category"
    return "D sign/state in a list" if coord(k) else "D sign/state elsewhere"


C = defaultdict(list)
for k in gold:
    C[cat(k)].append(k)


def st(x, k):
    s = state[x].get(k)
    return "right" if not s else (f"label->{s[2]}" if s[0] == "label" else s[0])


def rng(f):
    o = [f(x) for x in orig]
    return statistics.mean(o), min(o), max(o)


def flag(v, lo, hi):
    return "*" if v < lo or v > hi else " "


out, rec = [], {}

# ---------- A ----------
right = lambda x, ks: sum(st(x, k) == "right" for k in ks)
out.append("A. Slide-5 bars (strict TP change against the 19-run original mean); * outside the original range")
bars = {}
for lab in LABS:
    ks = [k for k in gold if k[3] == lab]
    mu, lo, hi = rng(lambda x: right(x, ks))
    bars[lab] = {n: (right(by[n], ks) - mu, flag(right(by[n], ks), lo, hi)) for n in ORDER}
    out.append(f"   {lab:<16} orig range {lo - mu:+.1f}..{hi - mu:+.1f}: " + " ".join(f"{short(n)} {bars[lab][n][0]:+.1f}{bars[lab][n][1]}" for n in ORDER))
sign = {n: "".join("+" if bars[l][n][0] > 0 else "-" for l in LABS) for n in ORDER}
out.append("   sign groups: " + "; ".join(f"{s}: {', '.join(n for n in ORDER if sign[n] == s)}" for s in dict.fromkeys(sign.values())))
rec["bars"] = {l: {n: v[0] for n, v in d.items()} for l, d in bars.items()}

# ---------- B ----------
out.append("\nB. Each bar split over the frozen categories: part = guideline right count minus original mean; * outside the original range")
out.append(f"   {'category':<40} {'n':>4} {'orig':>6} {'range':>12} " + " ".join(f"{short(n):>7}" for n in ORDER))
parts, n_out, n_cells = {}, 0, 0
for pre, lab in (("S ", "SpecificDisease"), ("D ", "DiseaseClass"), ("M ", "Modifier")):
    for c in sorted(x for x in C if x.startswith(pre)):
        ks = C[c]
        mu, lo, hi = rng(lambda x: right(x, ks))
        parts[c] = {n: (right(by[n], ks) - mu, flag(right(by[n], ks), lo, hi)) for n in ORDER}
        n_out += sum(v[1] == "*" for v in parts[c].values())
        n_cells += len(ORDER)
        out.append(f"   {c:<40} {len(ks):4} {mu:6.1f} {f'{lo - mu:+.1f}..{hi - mu:+.1f}':>12} " + " ".join(f"{parts[c][n][0]:+6.1f}{parts[c][n][1]}" for n in ORDER))
    for n in ORDER:
        assert abs(sum(parts[c][n][0] for c in parts if c.startswith(pre)) - bars[lab][n][0]) < 1e-9
out.append(f"   parts outside the original range: {n_out} of {n_cells}; if each changed guideline were one more original run, about"
           f" {n_cells / 10:.0f} (a single run falls outside 19 others' range about 1 time in 10)")
rec["parts"] = {c: {n: v[0] for n, v in d.items()} for c, d in parts.items()}

# ---------- C ----------
coordSD = [k for k in gold if k[3] in ("SpecificDisease", "DiseaseClass") and coord(k)]
sign_dc = C["D sign/state in a list"] + C["D sign/state elsewhere"]
MEAS = {
    "rel->Modifier": ("non-Modifier gold after a relational noun labelled Modifier", +1,
                      lambda x: sum(st(x, k) == "label->Modifier" for k in gold if k[3] != "Modifier" and rel(k))),
    "tumour->DC": ("Specific tumour-word gold labelled DiseaseClass", +1, lambda x: sum(st(x, k) == "label->DiseaseClass" for k in C["S tumour word"])),
    "merge": ("coordinated Specific/DiseaseClass gold labelled Composite or unpaired", -1,
              lambda x: sum(st(x, k) in ("label->CompositeMention", "unpaired") for k in coordSD)),
    "sign right": ("DiseaseClass sign/state gold right", +1, lambda x: right(x, sign_dc)),
    "sign missed": ("DiseaseClass sign/state gold missed", +1, lambda x: sum(st(x, k) == "missed" for k in sign_dc)),
    "bare missed": ("bare cancer/tumor gold missed", +1, lambda x: sum(st(x, k) == "missed" for k in C["D bare cancer/tumor"] + C["M bare cancer/tumor"])),
    "fullname missed": ("Modifier gold, full name before gene/protein noun, missed", +1,
                        lambda x: sum(st(x, k) == "missed" for k in C["M full name before gene/protein noun"])),
    "fullname right": ("Modifier gold, full name before gene/protein noun, right", +1, lambda x: right(x, C["M full name before gene/protein noun"])),
    "DC->Spec": ("DiseaseClass gold labelled Specific", +1, lambda x: sum(st(x, k) == "label->SpecificDisease" for k in gold if k[3] == "DiseaseClass")),
    "deficient right": ("Modifier gold, deficient adjective, right", +1, lambda x: right(x, C["M deficient adjective"])),
    "coordmod right": ("Modifier gold, coordinated names, right", +1, lambda x: right(x, C["M coordinated names"])),
}
out.append("\nC. Predicted error types: guideline value minus original mean; * outside the original range")
meas = {}
for key, (desc, _, f) in MEAS.items():
    mu, lo, hi = rng(f)
    meas[key] = {n: (f(by[n]) - mu, flag(f(by[n]), lo, hi)) for n in ORDER}
    out.append(f"   {desc:<70} orig {mu:5.1f} ({lo}-{hi}): " + " ".join(f"{short(n)} {meas[key][n][0]:+.1f}{meas[key][n][1]}" for n in ORDER))
rec["measures"] = {k: {n: v[0] for n, v in d.items()} for k, d in meas.items()}

# ---------- D ----------
RUNS = ROOT / "outputs" / "ncbi_disease"


def gl(n):
    if n == "original":
        return (ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt").read_text(encoding="utf-8").splitlines()
    return (RUNS / f"20261022_haiku-xhigh_{'topk1' if n.startswith('top-1') else 'topk4'}_loop{n[-2:]}" / "final" / "final_guidelines.txt").read_text(encoding="utf-8").splitlines()


def section(n, line):
    """Number of the section holding a line: nearest heading or numbered item above it."""
    ls = gl(n)
    for i in range(line - 1, -1, -1):
        l = ls[i]
        mm = re.match(r"#{2,5}\s*(\d+(?:\.\d+)*[a-z]?)\b", l) or re.match(r"\*\*(\d+(?:\.\d+)*[a-z]?)[\.\s]", l)
        if mm:
            return mm.group(1)
        if re.match(r"#{3,5}\s", l):
            return None  # an unnumbered subsection heading: no number to cite
        mm = re.match(r"(\d+)\.\s+\*\*", l)
        if mm:
            top = next((x for x in reversed(ls[:i + 1]) if x.startswith("## ")), "")
            return ("NOT" if top.startswith("## What NOT") else "") + mm.group(1)
        if l.startswith("## "):
            return None
    return None


def cites(sec, token):
    if not token:
        return False
    if token.startswith("NOT"):
        return re.search(rf"(what not|item)[^0-9]*{token[3:]}\b", sec or "", re.I) is not None
    return re.search(rf"(?<![\d.]){re.escape(token)}(?![\d])", sec or "") is not None


pidx = defaultdict(list)
for line in (OUT / "20261030_rationale_audit" / "prediction_index.jsonl").open(encoding="utf-8"):
    r = json.loads(line)
    pidx[(r["run"], r["doc"])].append(r)


PRED_STATE = {"rel->Modifier": "label->Modifier", "tumour->DC": "label->DiseaseClass", "merge": "right", "sign right": "right",
              "sign missed": "missed", "bare missed": "missed", "fullname missed": "missed", "fullname right": "right",
              "DC->Spec": "label->SpecificDisease", "deficient right": "right", "coordmod right": "right"}


def cited_share(n, cats, tokens, mk):
    """Among mentions of the categories that the guideline puts in the predicted state while the original runs mostly did
    not, the share whose cited section names the clause's section. Missed mentions have no prediction and no rationale."""
    x = by[n]
    want = PRED_STATE[mk]
    hit = tot = 0
    for c in cats:
        for k in C[c]:
            s = st(x, k)
            if s != want or s == "missed" or sum(st(o, k) == want for o in orig) / 19 >= 0.5:
                continue
            ov = [(min(int(r["end"]), k[2]) - max(int(r["start"]), k[1]), r) for r in pidx[(x, k[0])]]
            ov = [o for o in ov if o[0] > 0]
            if not ov:
                continue
            tot += 1
            hit += any(cites(max(ov, key=lambda o: o[0])[1]["cited_section"], t) for t in tokens)
    return hit, tot


OPT = {  # (question, coded option) -> (categories, predicted sign of the part, measure key)
    ("Q1", "Modifier"): (["S after relational noun"], -1, "rel->Modifier"),
    ("Q2", "not enough"): (["S tumour word"], -1, "tumour->DC"),
    ("Q3", "separate"): (["S coordinated"], +1, "merge"),
    ("Q4", "DiseaseClass"): (["D sign/state in a list", "D sign/state elsewhere"], +1, "sign right"),
    ("Q4", "exception"): (["D sign/state in a list", "D sign/state elsewhere"], -1, "sign missed"),
    ("Q5", "not annotated"): (["D bare cancer/tumor", "M bare cancer/tumor"], -1, "bare missed"),
    ("Q6", "official not annotated"): (["M full name before gene/protein noun"], -1, "fullname missed"),
    ("Q6", "Modifier incl official"): (["M full name before gene/protein noun"], +1, "fullname right"),
    ("Q7", "Specific"): (["D named or category", "D sign/state in a list", "D sign/state elsewhere"], -1, "DC->Spec"),
    ("Q8a", "Modifier"): (["M deficient adjective"], +1, "deficient right"),
    ("Q8b", "Modifier"): (["M coordinated names"], +1, "coordmod right"),
}
coding = list(csv.DictReader((OUT / "blind_clause_coding.csv").open(encoding="utf-8")))
bad = []
for r in coding:
    first = int(r["lines"].split()[0]) if r["lines"].strip() else None
    if first and r["quote"] and r["quote"] not in " ".join(gl(r["guideline"])[int(l) - 1] for l in r["lines"].split()):
        bad.append((r["guideline"], r["question"], r["lines"]))
out.append(f"\nD. Coded clause options (blind_clause_coding.csv, {len(coding)} rows; quotes checked, not found: {bad or 'none'})")
credit = defaultdict(list)
rec["credits"] = []
for r in coding:
    key = (r["question"], r["option"])
    n = r["guideline"]
    if key not in OPT or n == "original":
        continue
    cats, sgn, mk = OPT[key]
    tokens = {section(n, int(l)) for l in r["lines"].split()} - {None}
    part = sum(parts[c][n][0] for c in cats)
    p_out = any(parts[c][n][1] == "*" and parts[c][n][0] * sgn > 0 for c in cats)
    mv, mf = meas[mk][n]
    m_ok = mf == "*" and (mv < 0 if mk == "merge" else mv > 0)
    hit, tot = cited_share(n, cats, tokens, mk)
    c_ok = tot > 0 and hit / tot >= 0.5
    ok = sum([p_out, m_ok, c_ok]) >= 2
    if ok:
        for c in [c for c in cats if parts[c][n][1] == "*" and parts[c][n][0] * sgn > 0]:
            credit[(n, c)].append(f"{r['question']} {r['option']} (L{r['lines']})" + ("" if m_ok else " [weak: predicted error type did not move]"))
    rec["credits"].append({"guideline": n, "question": r["question"], "option": r["option"], "lines": r["lines"],
                           "inherited": r["inherited"], "part": part, "part_outside": p_out, "measure": mv,
                           "measure_outside": mf == "*", "cited": [hit, tot], "credited": ok})
    out.append(f"   {n:<13} {r['question']:<4} {r['option']:<24} L{r['lines']:<12} sec {','.join(sorted(tokens)) or '-':<8} part {part:+6.1f}{'*' if p_out else ' '}"
               f"  {mk} {mv:+5.1f}{mf}  cited {hit}/{tot}  -> {'CREDITED' if ok else 'not credited'}"
               + ("  (inherited)" if r["inherited"].startswith("y") else ""))

# ---------- E ----------
out.append("\nE. Controls: DiseaseClass categories that no coded clause of the guideline governs")
for n in ORDER:
    gov = {c for r in coding if r["guideline"] == n and (r["question"], r["option"]) in OPT for c in OPT[(r["question"], r["option"])][0]}
    dcl = [c for c in parts if c.startswith("D ") and c not in gov and c != "D after relational noun"]
    if any(c.startswith("D ") for c in gov):
        out.append(f"   {n:<13} governed {sorted(c for c in gov if c.startswith('D '))}; not governed: "
                   + ", ".join(f"{c} {parts[c][n][0]:+.1f}{parts[c][n][1]}" for c in dcl))

# ---------- F ----------
out.append("\nF. Per guideline: parts outside range, with the clauses credited; parts without a credited clause are unexplained")
rec["summary"] = {}
for n in ORDER:
    rows = []
    for c in parts:
        v, f = parts[c][n]
        if f == "*":
            rows.append(f"{c} {v:+.1f}: " + ("; ".join(credit[(n, c)]) if credit[(n, c)] else "UNEXPLAINED"))
    rec["summary"][n] = rows
    out.append(f"   {n} [{sign[n]}]")
    for x in rows:
        out.append(f"      {x}")
# ---------- G ----------
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
TEST = set(json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))["documents"])
ann = tot = 0
for p_ in sorted(TRAIN.glob("*.json")):
    if p_.name in TEST:
        continue
    d = json.loads(p_.read_text(encoding="utf-8"))
    spans = [(a_["span"]["begin"], a_["span"]["end"]) for a_ in d.get("denotations", [])]
    for mm in re.finditer(r"\b(cancers?|tumou?rs?)\b", d["text"], re.I):
        b_, e_ = mm.span()
        if any(x <= b_ and e_ <= y and (x, y) != (b_, e_) for x, y in spans):
            continue  # part of a longer gold mention (breast cancer): not a bare use
        tot += 1
        ann += (b_, e_) in spans
out.append(f"\nG. Training gold (543 documents, test excluded): bare cancer/tumor tokens not inside a longer gold mention: {tot}, annotated as a"
           f" mention of their own: {ann}")
rec["bare_training"] = [ann, tot]
(OUT / "bar_attribution.json").write_bytes((json.dumps(rec, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
(OUT / "bar_attribution_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
