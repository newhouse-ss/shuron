"""The Modifier subset (10/29): gold mentions in modifier-like contexts, defined from text and gold only.

Offline, no API calls. Reuses error_rows.csv (error_table.py) for run states and pilot_cases.py's state table.

Members (fixed before looking at predictions; a mention can meet several conditions):
  G   gold label Modifier
  B1  the gold span is directly followed (optionally after one parenthetical "( X )") by a non-disease head noun from HEAD
  B2  the gold span directly follows a relational noun and a preposition from REL ("risk of", "history of", "patients with")
Subgroups for reporting: Modifier gold in B1 context, Modifier gold elsewhere, non-Modifier gold in B1, non-Modifier gold
in B2, non-Modifier gold in both. The prediction side (predictions labelled Modifier that are not strict matches) is
reported separately, because its membership depends on the prediction.

Checks: (1) gold Modifier mentions that neither B1 nor B2 catches are listed, so the context rules' misses are visible;
(2) a seeded sample of 15 non-Modifier B1/B2 members is printed for manual review of false inclusion; (3) label errors
that turn a non-Modifier gold into Modifier outside the subset are counted, as leakage of the definition.
Per run: state of every member (right, label->X, boundary, missed, unpaired). Per changed guideline: right count minus
the original mean, which is that subgroup's exact contribution to the TP difference.
P (10/29, after the independent review): label errors to Modifier against the original rate, by document; the nine
mentions after "history of" in every run.
Writes modifier_subset_output.txt and modifier_subset.json.
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import re
import runpy
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(HERE / "pilot_cases.py"))
texts, gold, state, extra, runs, orig, mod, name, rows = (g[k] for k in ("texts", "gold", "state", "extra", "runs", "orig", "mod", "name", "rows"))
OUTDIR = HERE.parent / "outputs"

# v1 lists (first pass) plus, in v2 (10/29), the words found by checks D1 (gold Modifier not caught; gold only) and D3
# (label errors to Modifier outside the subset; this check uses predictions, so the additions are disclosed as such).
HEAD = (r"genes?|proteins?|products?|locus|loci|alleles?|mutations?|mutants?|transcripts?|mRNA|cDNA|families|family|kindreds?|"
        r"pedigrees?|patients?|cases?|carriers?|probands?|individuals|cohorts?|populations?|series|risk|susceptibility|"
        r"predisposition|phenotypes?|cells?|lines?|tissues?|samples?|specimens?|mice|mouse|models?|stud(y|ies)|groups?|"
        r"types?|suppressors?|suppression|DNA|formation|sites?|foci|growth|region|factor|deficient|research|registry|clinic"
        r"|prevalence|incidence|pathogenesis|penetrance|regions|pathology|deaths?|isoforms?|chromosomes?|symptoms?|"
        r"hepatocytes|fibroblasts|thymocytes|mRNAs")
REL = (r"risks?|histor(y|ies)|cases?|patients?|carriers?|families|family|individuals|members|relatives|women|men|children|"
       r"frequency|incidence|prevalence|predisposition|susceptibility|subjects|probands?"
       r"|presence|diagnosis|factors|sisters?|brothers?|mothers?|fathers?|parents?|adults")
B1 = re.compile(r"\s*(\)\s*)?(\(\s*[^()]{1,25}?\s*\)\s*)?(" + HEAD + r")\b|\s*-(associated|mediated|related|linked|prone|specific)\b")
B2 = re.compile(r"\b(" + REL + r")\s+(of|with|for|to)\s+((the|a|an)\s+)?((\S+\s+){1,5}(but not|and / or|and|or)\s+)?$", re.I)
B3 = re.compile(r"(-(associated|mediated|related|linked|prone|specific)\b|\s(" + HEAD + r"))\s*$")


def b1(k):
    return B1.match(texts[k[0]][k[2]:k[2] + 50]) is not None


def b2(k):
    return B2.search(texts[k[0]][max(0, k[1] - 80):k[1]]) is not None


def b3(k):
    """The non-disease head is inside the gold span itself (cancer predisposition, cancer-prone)."""
    return B3.search(texts[k[0]][k[1]:k[2]]) is not None


member = {}
for k in gold:
    tags = [t for t, ok in (("G", k[3] == "Modifier"), ("B1", b1(k)), ("B2", b2(k)), ("B3", b3(k))) if ok]
    if tags:
        member[k] = tags


def sub(k):
    t = member[k]
    ctx = next((c for c in ("B1", "B2", "B3") if c in t), None)
    if "G" in t:
        return f"Modifier gold, {ctx} context" if ctx else "Modifier gold, no context"
    return f"other gold, {ctx} context"


SUBS = ["Modifier gold, B1 context", "Modifier gold, B2 context", "Modifier gold, B3 context", "Modifier gold, no context",
        "other gold, B1 context", "other gold, B2 context", "other gold, B3 context"]
groups = defaultdict(list)
for k in member:
    groups[sub(k)].append(k)


def st(x, k):
    s = state[x].get(k)
    return "right" if not s else (f"label->{s[2]}" if s[0] == "label" else s[0])


out, rec = [], {"members": {}, "by_guideline": {}}
out.append(f"Members: {len(member)} of 791 gold mentions")
for s_ in SUBS:
    out.append(f"   {s_:<34} {len(groups[s_]):4}")

out.append("\nA. Right count per subgroup: original mean (min-max) and each changed guideline minus the original mean")
cols = sorted(mod, key=lambda x: name[x])
out.append(f"   {'subgroup':<34} {'n':>4} {'orig':>14} " + " ".join(f"{name[x].replace('top-', '').replace(' loop', '-'):>6}" for x in cols))
for s_ in SUBS:
    ks = groups[s_]
    o = [sum(st(x, k) == "right" for k in ks) for x in orig]
    om = statistics.mean(o)
    out.append(f"   {s_:<34} {len(ks):4} {om:6.1f} ({min(o)}-{max(o)}) " + " ".join(f"{sum(st(x, k) == 'right' for k in ks) - om:+6.1f}" for x in cols))
    rec["by_guideline"][s_] = {"n": len(ks), "orig_mean_right": om, "orig_range": [min(o), max(o)],
                               "delta_right": {name[x]: sum(st(x, k) == "right" for k in ks) - om for x in cols}}
tot_o = statistics.mean(sum(st(x, k) == "right" for k in member) for x in orig)
out.append(f"   {'all members':<34} {len(member):4} {tot_o:6.1f}          " + " ".join(f"{sum(st(x, k) == 'right' for k in member) - tot_o:+6.1f}" for x in cols))
out.append(f"   {'all other gold (not members)':<34} {791 - len(member):4} "
           f"{statistics.mean(sum(st(x, k) == 'right' for k in gold if k not in member) for x in orig):6.1f}          "
           + " ".join(f"{sum(st(x, k) == 'right' for k in gold if k not in member) - statistics.mean(sum(st(y, k) == 'right' for k in gold if k not in member) for y in orig):+6.1f}" for x in cols))
out.append("   (each delta is that subgroup's exact share of the TP difference; the rows sum to the guideline's TP delta)")

out.append("\nB. Error states per subgroup: original mean per run, and each changed guideline's count")
for s_ in SUBS:
    ks = groups[s_]
    states = sorted({st(x, k) for x in runs for k in ks} - {"right"})
    out.append(f"   {s_}")
    for sv in states:
        o = statistics.mean(sum(st(x, k) == sv for k in ks) for x in orig)
        out.append(f"      {sv:<26} orig {o:5.1f}  " + " ".join(f"{sum(st(x, k) == sv for k in ks):>4}" for x in cols))
out.append("   (columns in the order of A)")

out.append("\nC. Prediction side: non-strict predictions labelled Modifier, per run (these count in FP)")
pm = {x: Counter() for x in runs}
for r in rows:
    if r["pred_label"] == "Modifier" and r["kind"] in ("label", "boundary", "extra", "unpaired"):
        gk = (r["doc"], int(r["gold_start"]), int(r["gold_end"]), r["gold_label"]) if r["gold_text"] else None
        where = "extra" if r["kind"] == "extra" else ("unpaired pred" if r["kind"] == "unpaired" else
                (f"{r['kind']} on member" if gk in member else f"{r['kind']} on non-member"))
        pm[r["run"]][where] += 1
for w in sorted({w for c in pm.values() for w in c}):
    o = statistics.mean(pm[x][w] for x in orig)
    out.append(f"   {w:<26} orig {o:5.1f}  " + " ".join(f"{pm[x][w]:>4}" for x in cols))

out.append("\nD. Checks of the definition")
nomatch = [k for k in groups["Modifier gold, no context"]]
out.append(f"   D1. Modifier gold that no context rule catches: {len(nomatch)}; next words after the span:")
nxt = Counter(re.match(r"\s*(\S+)", texts[k[0]][k[2]:k[2] + 30]).group(1) if re.match(r"\s*(\S+)", texts[k[0]][k[2]:k[2] + 30]) else "<end>" for k in nomatch)
out.append("      " + str(dict(nxt.most_common(40))))
rng = random.Random(20261029)
others = sorted(k for k in member if "G" not in member[k])
out.append(f"   D2. Seeded sample of 15 non-Modifier members for review of false inclusion (seed 20261029):")
for k in rng.sample(others, 15):
    t = texts[k[0]]
    out.append(f"      {k[0]} {k[1]}-{k[2]} {k[3]:<16} {member[k]} ...{t[max(0, k[1] - 50):k[1]]}[[{t[k[1]:k[2]]}]]{t[k[2]:k[2] + 40]}...".replace("\n", " "))
leak = Counter()
for x in runs:
    for k, s in state[x].items():
        if s[0] == "label" and s[2] == "Modifier" and k not in member:
            leak[k] += 1
out.append(f"   D3. Label errors to Modifier on gold mentions outside the subset: {sum(leak.values())} occurrences over 30 runs, {len(leak)} mentions:")
for k, n in leak.most_common():
    t = texts[k[0]]
    out.append(f"      {n:2} runs  {k[0]} {k[3]:<16} ...{t[max(0, k[1] - 50):k[1]]}[[{t[k[1]:k[2]]}]]{t[k[2]:k[2] + 30]}...".replace("\n", " "))

REL_GROUPS = [("history", r"histor(y|ies)"), ("risk/susceptibility/predisposition", r"risks?|susceptibility|predisposition|factors"),
              ("case(s) of", r"cases?"), ("person noun + with/of", r"patients?|carriers?|families|family|individuals|members|relatives|women|men|"
                                                                      r"children|subjects|probands?|sisters?|brothers?|mothers?|fathers?|parents?|adults"),
              ("frequency/incidence/prevalence/presence/diagnosis", r"frequency|incidence|prevalence|presence|diagnosis")]


def rel_group(k):
    m = B2.search(texts[k[0]][max(0, k[1] - 80):k[1]])
    noun = m.group(1).lower()
    return next(gname for gname, pat in REL_GROUPS if re.fullmatch(pat, noun))


out.append("\nF. Non-Modifier gold after a relational noun (other gold, B2 context), by relational noun:"
           " members; right count orig mean and each changed guideline minus it; label->Modifier orig mean and each guideline's count")
for gname, _ in REL_GROUPS:
    ks = [k for k in groups["other gold, B2 context"] if rel_group(k) == gname]
    if not ks:
        continue
    o = statistics.mean(sum(st(x, k) == "right" for k in ks) for x in orig)
    lm = statistics.mean(sum(st(x, k) == "label->Modifier" for k in ks) for x in orig)
    out.append(f"   {gname:<46} n={len(ks):3}  right {o:5.1f}: " + " ".join(f"{sum(st(x, k) == 'right' for k in ks) - o:+5.1f}" for x in cols))
    out.append(f"   {'':<46}        ->Mod {lm:5.1f}: " + " ".join(f"{sum(st(x, k) == 'label->Modifier' for k in ks):>5}" for x in cols))
    rec.setdefault("relational", {})[gname] = {"n": len(ks), "orig_right": o, "orig_to_modifier": lm,
                                               "right": {name[x]: sum(st(x, k) == "right" for k in ks) for x in cols},
                                               "to_modifier": {name[x]: sum(st(x, k) == "label->Modifier" for k in ks) for x in cols}}

out.append("\nG. Every non-Modifier B2 member that some changed guideline labels Modifier: relational group, context, guidelines, original runs")
for k in sorted(groups["other gold, B2 context"]):
    who = [name[x].replace("top-", "").replace(" loop", "-") for x in cols if st(x, k) == "label->Modifier"]
    if who:
        t = texts[k[0]]
        no = sum(st(x, k) == "label->Modifier" for x in orig)
        out.append(f"   {rel_group(k):<22.22} {k[0]} {k[1]}-{k[2]} {k[3]:<16} mod: {','.join(who):<34} orig {no}/19  "
                   f"...{t[max(0, k[1] - 60):k[1]]}[[{t[k[1]:k[2]]}]]{t[k[2]:k[2] + 25]}...".replace("\n", " "))

HEAD_GROUPS = [("molecular (gene, protein, locus, allele, mutation, ...)", r"genes?|proteins?|products?|locus|loci|alleles?|mutations?|mutants?|"
                r"transcripts?|mRNAs?|cDNA|DNA|factor|isoforms?|suppressors?|suppression|chromosomes?|region|regions|sites?|foci"),
               ("people and cases (families, patients, cases, ...)", r"families|family|kindreds?|pedigrees?|patients?|cases?|carriers?|probands?|"
                r"individuals|cohorts?|populations?|series|groups?|registry|clinic|stud(y|ies)|research|deaths?"),
               ("risk and frequency (risk, susceptibility, incidence, ...)", r"risk|susceptibility|predisposition|penetrance|incidence|prevalence"),
               ("other (cells, mice, phenotype, symptoms, -associated, ...)", r".*")]


def head_group(k):
    m = B1.match(texts[k[0]][k[2]:k[2] + 50])
    word = (m.group(3) if m and m.group(3) else "").strip()
    return next(gname for gname, pat in HEAD_GROUPS if re.fullmatch(pat, word, re.I))


out.append("\nH. Modifier gold in B1 context by the head noun that follows: members; right count orig mean (min-max) and each changed guideline minus it;"
           " missed orig mean and each guideline's count")
for gname, _ in HEAD_GROUPS:
    ks = [k for k in groups["Modifier gold, B1 context"] if head_group(k) == gname]
    o = [sum(st(x, k) == "right" for k in ks) for x in orig]
    om = statistics.mean(o)
    mo = statistics.mean(sum(st(x, k) == "missed" for k in ks) for x in orig)
    out.append(f"   {gname:<58} n={len(ks):3}  right {om:5.1f} ({min(o)}-{max(o)}): " + " ".join(f"{sum(st(x, k) == 'right' for k in ks) - om:+5.1f}" for x in cols))
    out.append(f"   {'':<58}        missed {mo:5.1f}: " + " ".join(f"{sum(st(x, k) == 'missed' for k in ks):>5}" for x in cols))
    rec.setdefault("head_groups", {})[gname] = {"n": len(ks), "orig_right": om, "orig_missed": mo,
                                                "right": {name[x]: sum(st(x, k) == "right" for k in ks) for x in cols}}

# ---- v3 (10/29, second pass) ----
STATES = ["right", "missed", "label->CompositeMention", "label->SpecificDisease", "label->DiseaseClass", "label->Modifier", "boundary", "unpaired"]
out.append("\nI. Modifier gold in B1 context: change in each state, changed guideline minus original mean (right = strict TP share;"
           " the error rows sum to minus the right row)")
ks = groups["Modifier gold, B1 context"]
for sv in STATES:
    o = statistics.mean(sum(st(x, k) == sv for k in ks) for x in orig)
    if o == 0 and all(sum(st(x, k) == sv for k in ks) == 0 for x in cols):
        continue
    out.append(f"   {sv:<26} orig {o:5.1f}: " + " ".join(f"{sum(st(x, k) == sv for k in ks) - o:+6.1f}" for x in cols))
    rec.setdefault("b1_state_delta", {})[sv] = {name[x]: sum(st(x, k) == sv for k in ks) - o for x in cols}

out.append("\nJ. Non-Modifier gold in B2 context labelled Modifier, split by how often the 19 original runs got the mention right"
           " (>=15: a new strict error; <=14: the mention was already often wrong, so the error form changed)")
ks = groups["other gold, B2 context"]
tot = Counter()
for x in cols:
    c = Counter()
    for k in ks:
        if st(x, k) == "label->Modifier":
            r = sum(st(y, k) == "right" for y in orig)
            c[">=15" if r >= 15 else "<=14"] += 1
    tot.update(c)
    out.append(f"   {name[x]:<14} label->Modifier {sum(c.values()):3}  (orig right >=15: {c['>=15']:3}; <=14: {c['<=14']:3})")
dist = {k for k in ks if any(st(x, k) == "label->Modifier" for x in cols)}
out.append(f"   total {sum(tot.values())} mention x guideline, on {len(dist)} distinct gold mentions; orig right >=15: {tot['>=15']}, <=14: {tot['<=14']}")

FALSE_INCL = {("8929264", 272): "colorectal cancer is the object of 'deleted in' inside a parenthetical gloss of DCC, not a modifier of 'gene'",
              ("8931695", 200): "'a family of chondrodysplasias': 'family' means a class of disorders, not kin"}
out.append("\nK. Clear false inclusions found by manual review (kept in the v2 membership, effect shown here)")
for k in member:
    if (k[0], k[1]) in FALSE_INCL:
        out.append(f"   {k[0]} {k[1]}-{k[2]} {k[3]} [{sub(k)}]: {FALSE_INCL[(k[0], k[1])]}")
        out.append(f"      right in {sum(st(x, k) == 'right' for x in orig)}/19 orig; changed guidelines: " + " ".join(f"{name[x].replace('top-', '').replace(' loop', '-')}:{st(x, k)}" for x in cols))

# ---- 10/29 final: the two questions on the full populations, and how much of each the two expression subsets cover ----
gm = [k for k in gold if k[3] == "Modifier"]
ngm = [k for k in gold if k[3] != "Modifier"]
out.append(f"\nL. Question 1, all gold Modifier mentions (n={len(gm)}): right and missed, original mean and each changed guideline")
o = statistics.mean(sum(st(x, k) == "right" for k in gm) for x in orig)
out.append(f"   right   orig {o:6.1f}: " + " ".join(f"{sum(st(x, k) == 'right' for k in gm) - o:+6.1f}" for x in cols))
o2 = statistics.mean(sum(st(x, k) == "missed" for k in gm) for x in orig)
out.append(f"   missed  orig {o2:6.1f}: " + " ".join(f"{sum(st(x, k) == 'missed' for k in gm) - o2:+6.1f}" for x in cols))
b1g = [k for k in gm if "B1" in member[k]]
out.append(f"   covered by the B1 word list (span followed by a listed non-disease noun): {len(b1g)} of {len(gm)}; "
           f"by B2 only: {sum(1 for k in gm if 'B1' not in member[k] and 'B2' in member[k])}; by no list: {sum(1 for k in gm if member[k] == ['G'])}")
out.append(f"   Question 2, non-Modifier gold mentions (n={len(ngm)}) predicted with the label Modifier: original mean per run, then each changed guideline's count")
lm = {x: [k for k in ngm if st(x, k) == "label->Modifier"] for x in runs}
o3 = statistics.mean(len(lm[x]) for x in orig)
out.append(f"   all          orig {o3:5.1f}: " + " ".join(f"{len(lm[x]):>5}" for x in cols))
where = lambda k: "B2 list" if k in member and "B2" in member[k] else ("other word lists" if k in member else "no list")
for w in ("B2 list", "other word lists", "no list"):
    ow = statistics.mean(sum(where(k) == w for k in lm[x]) for x in orig)
    out.append(f"   {w:<12} orig {ow:5.1f}: " + " ".join(f"{sum(where(k) == w for k in lm[x]):>5}" for x in cols))
tot_mod = sum(len(lm[x]) for x in cols)
out.append(f"   over the 11 changed guidelines: {tot_mod} mention x guideline, of which B2 list {sum(where(k) == 'B2 list' for x in cols for k in lm[x])}")
rec["questions"] = {"gold_modifier_n": len(gm), "nonmodifier_n": len(ngm),
                    "q1_right_delta": {name[x]: sum(st(x, k) == "right" for k in gm) - o for x in cols}, "q1_right_orig": o,
                    "q2_label_modifier": {name[x]: len(lm[x]) for x in cols}, "q2_orig": o3}

# ---- 10/29 rewrite of report section 4: actual counts, distinct positions, where the gain sits, two complete cases ----
out.append("\nM. Main table for report section 4: actual counts per changed guideline (original: mean of 19 runs)")
out.append(f"   {'guideline':<14} {'gold Modifier right (of 218)':>28} {'non-Modifier labelled Modifier (of 573)':>40} {'molecular-head share of the gain':>34}")
mol = [k for k in groups["Modifier gold, B1 context"] if head_group(k).startswith("molecular")]
mol_o = statistics.mean(sum(st(x, k) == "right" for k in mol) for x in orig)
out.append(f"   {'original':<14} {o:>28.1f} {o3:>40.1f}")
_r = [sum(st(x, k) == "right" for k in gm) for x in orig]
_l = [len(lm[x]) for x in orig]
out.append(f"   {'original range':<14} {str(min(_r)) + '-' + str(max(_r)):>28} {str(min(_l)) + '-' + str(max(_l)):>40}")
for x in cols:
    r = sum(st(x, k) == "right" for k in gm)
    dm = sum(st(x, k) == "right" for k in mol) - mol_o
    share = f"{dm:+.1f} of {r - o:+.1f}"
    out.append(f"   {name[x]:<14} {r:>28} {len(lm[x]):>40} {share:>34}")
occ = [(x, k) for x in cols for k in lm[x]]
dist = {k for _, k in occ}
b2d = {k for _, k in occ if where(k) == "B2 list"}
out.append(f"   non-Modifier labelled Modifier over the 11 changed runs: {len(occ)} times at {len(dist)} distinct text positions; "
           f"after a relational noun (B2 list): {sum(where(k) == 'B2 list' for _, k in occ)} times at {len(b2d)} positions; "
           f"elsewhere: {sum(where(k) != 'B2 list' for _, k in occ)} times at {len(dist - b2d)} positions")
out.append(f"   molecular-head gold Modifier (gene, protein, locus, ...): {len(mol)} mentions, original right {mol_o:.1f}")


# O (10/29): overview by gold label before report section 4, and the size and error share of each example group.
# FN is counted on the gold side by gold label (every gold mention in state is one FN); FP is counted on the prediction
# side by predicted label (label, boundary, extra and unpaired-prediction rows), so no error is counted twice.
LABELS = ["SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention"]
fn_by = {x: Counter(k[3] for k in state[x]) for x in runs}
miss_by = {x: Counter(k[3] for k, v in state[x].items() if v[0] == "missed") for x in runs}
fp_by = {x: Counter() for x in runs}
for r in rows:
    if r["kind"] in ("label", "boundary", "extra") or (r["kind"] == "unpaired" and not r["gold_text"]):
        fp_by[r["run"]][r["pred_label"]] += 1
fn_tot = statistics.mean(sum(fn_by[x].values()) for x in orig)
fp_tot = statistics.mean(sum(fp_by[x].values()) for x in orig)
out.append("\nO. Overview by label (original: mean of 19 runs; changed: range over the 11 guidelines of run minus original mean)")
out.append(f"   total FN orig {fn_tot:.1f}; total FP orig {fp_tot:.1f}")
out.append("   gold label         n   share   FN orig  FN share  FN rate  missed orig   FN delta range    missed delta range")
for lab in LABELS:
    n = sum(k[3] == lab for k in gold)
    fo = statistics.mean(fn_by[x][lab] for x in orig)
    mo = statistics.mean(miss_by[x][lab] for x in orig)
    fd = [fn_by[x][lab] - fo for x in cols]
    md = [miss_by[x][lab] - mo for x in cols]
    out.append(f"   {lab:<16} {n:4} {n / len(gold):6.1%}  {fo:7.1f}  {fo / fn_tot:7.1%}  {fo / n:6.1%}  {mo:9.1f}"
               f"   {min(fd):+6.1f} to {max(fd):+6.1f}   {min(md):+6.1f} to {max(md):+6.1f}")
out.append("   predicted label  FP orig  FP share   FP delta range")
for lab in LABELS:
    po = statistics.mean(fp_by[x][lab] for x in orig)
    pd = [fp_by[x][lab] - po for x in cols]
    out.append(f"   {lab:<16} {po:7.1f}  {po / fp_tot:7.1%}   {min(pd):+6.1f} to {max(pd):+6.1f}")
mfo = statistics.mean(fn_by[x]["Modifier"] for x in orig)
out.append("   example groups (FN orig = gold mentions of the group not strictly right, mean per original run):")
for gname, _ in HEAD_GROUPS:
    ks = [k for k in groups["Modifier gold, B1 context"] if head_group(k) == gname]
    fo = statistics.mean(sum(k in state[x] for k in ks) for x in orig)
    gains = [sum(k not in state[x] for k in ks) - (len(ks) - fo) for x in cols]
    out.append(f"      Modifier gold before {gname[:40]:<40} n={len(ks):3} ({len(ks) / 218:.1%} of 218); FN orig {fo:5.1f}"
               f" ({fo / mfo:.1%} of Modifier FN {mfo:.1f}, {fo / fn_tot:.1%} of all FN); right gain per guideline {[round(v, 1) for v in gains]}")
for gname, _ in REL_GROUPS:
    ks = [k for k in groups["other gold, B2 context"] if rel_group(k) == gname]
    fo = statistics.mean(sum(k in state[x] for k in ks) for x in orig)
    lm_ = {x: [k for k in ks if state[x].get(k, ("",))[0] == "label" and state[x][k][2] == "Modifier"] for x in cols}
    pos = {k for x in cols for k in lm_[x]}
    out.append(f"      non-Modifier gold after {gname[:30]:<30} n={len(ks):3} ({len(ks) / 573:.1%} of 573); FN orig {fo:4.1f};"
               f" labelled Modifier {sum(len(v) for v in lm_.values())} times over 11 runs at {len(pos)} positions;"
               f" per guideline {[len(lm_[x]) for x in cols]}")
hist = [k for k in groups["other gold, B2 context"] if rel_group(k) == "history"]
for k in hist:
    out.append(f"         history member {k[0]}:{k[1]} {k[3]:<16} ...{texts[k[0]][max(0, k[1] - 40):k[1]]}[[{texts[k[0]][k[1]:k[2]]}]]")


def case(doc, start):
    k = next(k for k in gold if k[0] == doc and k[1] == start)
    t = texts[doc]
    s0 = t.rfind(".", 0, k[1]) + 1
    e0 = t.find(".", k[2])
    out.append(f"   case {doc} {k[1]}-{k[2]} gold {k[3]} {t[k[1]:k[2]]!r}; sentence: {t[s0:e0 + 1].strip()}")
    oc = Counter(state[x][k][:3] if k in state[x] else ("right", t[k[1]:k[2]], k[3]) for x in orig)
    out.append(f"      original 19 runs: {dict(oc)}")
    for x in cols:
        v = state[x][k][:3] if k in state[x] else ("right", t[k[1]:k[2]], k[3])
        out.append(f"      {name[x]:<14} {v}")


out.append("\nN. Complete cases (state, predicted text, predicted label)")
case("9145677", 714)
case("8824873", 653)

out.append("\nE. Members right in all 30 runs (correct controls), by subgroup: " +
           ", ".join(f"{s_}: {sum(all(st(x, k) == 'right' for x in runs) for k in groups[s_])}" for s_ in SUBS))

# P (10/29, after the independent review): label errors to Modifier against the original rate, where the increment sits,
# how it spreads over documents, the gene-word group against its original range, and the nine mentions after 'history of'.
out.append("\nP. Non-Modifier gold labelled Modifier against the original rate (expected = 11 x the original mean per run)")
o_all = [len(lm[x]) for x in orig]
o_b2 = [sum(where(k) == "B2 list" for k in lm[x]) for x in orig]
o_el = [a - b for a, b in zip(o_all, o_b2)]
c_b2 = {x: sum(where(k) == "B2 list" for k in lm[x]) for x in cols}
inc = {}
for lab, o_, c_ in (("all", o_all, sum(len(lm[x]) for x in cols)), ("after a relational noun (B2 list)", o_b2, sum(c_b2.values())),
                    ("elsewhere", o_el, sum(len(lm[x]) - c_b2[x] for x in cols))):
    e = 11 * statistics.mean(o_)
    inc[lab] = c_ - e
    out.append(f"   {lab:<34} original {statistics.mean(o_):5.2f} per run ({min(o_)}-{max(o_)}); expected {e:5.1f}; changed runs {c_:4}; increment {c_ - e:+6.1f}")
out.append("   elsewhere per changed guideline (* outside the original range): " + ", ".join(
    f"{name[x]} {len(lm[x]) - c_b2[x]}{'*' if not min(o_el) <= len(lm[x]) - c_b2[x] <= max(o_el) else ''}" for x in cols))
seen_o = Counter(k for x in orig for k in lm[x])
el_occ = [k for x in cols for k in lm[x] if where(k) != "B2 list"]
out.append(f"   elsewhere occurrences on mentions that at least one original run also labels Modifier: {sum(seen_o[k] >= 1 for k in el_occ)} of {len(el_occ)}")
b2m = [k for k in ngm if where(k) == "B2 list"]
b2_occ = [(x, k) for x in cols for k in lm[x] if where(k) == "B2 list"]
by_doc = Counter(k[0] for _, k in b2_occ)
HOT = sorted(d for d, n in by_doc.items() if n >= 10)
out.append(f"   B2 list: {len(b2m)} non-Modifier mentions; its {len(b2_occ)} occurrences by document ({len(by_doc)} documents): {by_doc.most_common()}")
out.append(f"   documents with at least 10 occurrences: {HOT}; together {sum(by_doc[d] for d in HOT)} of {len(b2_occ)}")
for d in HOT:
    out.append(f"      {d}: {texts[d][:texts[d].find(chr(10))]}")
for lab, ks in (("B2 list, these documents", [k for k in b2m if k[0] in HOT]), ("B2 list, other documents", [k for k in b2m if k[0] not in HOT]),
                ("other non-Modifier, these documents", [k for k in ngm if where(k) != "B2 list" and k[0] in HOT]),
                ("other non-Modifier, other documents", [k for k in ngm if where(k) != "B2 list" and k[0] not in HOT])):
    e_ = sum(st(x, k) == "label->Modifier" for x in cols for k in ks)
    o_ = statistics.mean(sum(st(x, k) == "label->Modifier" for k in ks) for x in orig)
    out.append(f"   {lab:<36} {len(ks):3} mentions ({len({k[0] for k in ks})} documents); labelled Modifier per run: original {o_:.2f},"
               f" changed {e_ / len(cols):.1f} ({e_} times over the 11 runs, {e_ / (len(ks) * len(cols)):.1%} of its mentions)")
out.append(f"   B2 occurrences whose gold text contains 'breast' or 'ovarian': "
           f"{sum(any(w in texts[k[0]][k[1]:k[2]].lower() for w in ('breast', 'ovarian')) for _, k in b2_occ)} of {len(b2_occ)}")
for lab, sel in (("B2 list", lambda k: where(k) == "B2 list"), ("all", lambda k: True)):
    o_ = statistics.mean(sum(sel(k) and k[0] not in HOT for k in lm[x]) for x in orig)
    c_ = sum(sel(k) and k[0] not in HOT for x in cols for k in lm[x])
    out.append(f"   without these documents, {lab}: original {o_:.2f} per run, changed runs {c_}, increment {c_ - 11 * o_:+.1f}")
mol_r = [sum(st(x, k) == "right" for k in mol) for x in orig]
mol_above = [name[x] for x in cols if sum(st(x, k) == "right" for k in mol) > max(mol_r)]
out.append(f"   gene/protein-head Modifier gold ({len(mol)}): original right {statistics.mean(mol_r):.1f} ({min(mol_r)}-{max(mol_r)});"
           f" changed guidelines above the original maximum: {len(mol_above)} of {len(cols)}; inside the range: {[name[x] for x in cols if name[x] not in mol_above]}")
out.append("   the nine non-Modifier mentions after 'history of': original states, then each changed guideline's state")
for k in hist:
    oc = Counter(st(x, k) for x in orig)
    out.append(f"      {k[0]}:{k[1]} {k[3]:<16} {texts[k[0]][k[1]:k[2]]!r:<36} orig {dict(oc)}")
    out.append("         " + "  ".join(f"{name[x].replace('top-', '').replace(' loop', '-')}:{st(x, k)}" for x in cols))
rec["increment"] = {"increment": inc, "documents_10_plus": HOT, "b2_by_document": dict(by_doc.most_common()),
                    "molecular_above_original_max": mol_above}

# Q (10/30): is the label-Modifier increase explained by phrases copied from development document 10196379 (hard-coding)?
ROOT_ = HERE.parents[3]
dev = json.loads((ROOT_ / "data" / "datasets" / "ncbi_disease" / "train" / "10196379.json").read_text(encoding="utf-8"))
dev_lab = Counter(x["obj"] for x in dev["denotations"] if dev["text"][x["span"]["begin"]:x["span"]["end"]] == "ovarian cancer")
DEV_PHRASES = ["ovarian cancer cases", "ovarian cancer population", "ovarian cancer study", "ovarian cancer risk", "family history of ovarian cancer",
               "family history of breast or ovarian cancer", "family history of cancer", "Caucasian cancer cases", "breast cancer susceptibility gene"]
assert all(ph.lower() in dev["text"].lower() for ph in DEV_PHRASES)
# the 7 guidelines whose clause makes the family-history position Modifier (report section 4.2, clause column)
FH_MOD = {"top-1 loop05", "top-4 loop05", "top-4 loop06", "top-4 loop07", "top-4 loop08", "top-4 loop09", "top-4 loop10"}
bo = lambda k: re.search(r"breast|ovar", texts[k[0]][k[1]:k[2]], re.I) is not None
b2_bo = [k for k in b2m if bo(k)]
b2_ot = [k for k in b2m if not bo(k)]
nb_bo = [k for k in ngm if where(k) != "B2 list" and bo(k)]
out.append("\nQ. Phrases copied from development document 10196379 and the label errors to Modifier")
out.append(f"   'ovarian cancer' in 10196379: gold labels {dict(dev_lab)}; its {len(DEV_PHRASES)} phrases around gold mentions: {DEV_PHRASES}")
out.append(f"   non-Modifier gold after a relational noun: name contains breast/ovarian {len(b2_bo)}, other names {len(b2_ot)};"
           f" elsewhere with breast/ovarian {len(nb_bo)}")
out.append("   guideline       copied phrases  family-history clause  label->Modifier: after noun, breast/ovarian | after noun, other names | elsewhere, breast/ovarian")
o_q = [statistics.mean(sum(st(x, k) == "label->Modifier" for k in grp) for x in orig) for grp in (b2_bo, b2_ot, nb_bo)]
out.append(f"   {'original, mean per run':<44} {o_q[0]:12.2f} {o_q[1]:22.2f} {o_q[2]:22.2f}")
for x in cols:
    gl = (ROOT_ / "outputs" / "ncbi_disease" / x / "final" / "final_guidelines.txt").read_text(encoding="utf-8").lower()
    n_ph = sum(ph.lower() in gl for ph in DEV_PHRASES)
    c = [sum(st(x, k) == "label->Modifier" for k in grp) for grp in (b2_bo, b2_ot, nb_bo)]
    out.append(f"   {name[x]:<14} {n_ph:>8} of {len(DEV_PHRASES)} {'Modifier' if name[x] in FH_MOD else 'not Modifier':>20} {c[0]:12} {c[1]:22} {c[2]:22}")
fh = [x for x in cols if name[x] in FH_MOD]
avg = lambda grp: statistics.mean(sum(st(x, k) == "label->Modifier" for k in grp) for x in fh)
out.append(f"   the 7 with a family-history Modifier clause, mean per guideline: after noun, breast/ovarian {avg(b2_bo):.1f} of {len(b2_bo)};"
           f" after noun, other names {avg(b2_ot):.1f} of {len(b2_ot)}; elsewhere, breast/ovarian {avg(nb_bo):.1f} of {len(nb_bo)}")
bo_all = [k for k in ngm if bo(k)]
out.append(f"   non-Modifier breast/ovarian mentions in documents whose text mentions BRCA: {sum('BRCA' in texts[k[0]] for k in bo_all)} of {len(bo_all)}")
out.append("   the other 4: " + ", ".join(f"{name[x]} {sum(st(x, k) == 'label->Modifier' for grp in (b2_bo, b2_ot, nb_bo) for k in grp)}" for x in cols if name[x] not in FH_MOD))
rec["members"] = {f"{k[0]}:{k[1]}-{k[2]}:{k[3]}": {"tags": member[k], "subgroup": sub(k), "states": {name[x]: st(x, k) for x in runs}} for k in member}
(OUTDIR / "modifier_subset.json").write_bytes((json.dumps(rec, indent=1) + "\n").encode("utf-8"))
(OUTDIR / "modifier_subset_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
