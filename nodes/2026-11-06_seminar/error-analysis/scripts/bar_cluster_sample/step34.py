# Steps 3-4 for top-4 loop07: each candidate cluster as a text-defined set; its statistic in all 11 guidelines against the
# original's own run-to-run range (each original run vs the mean of the other 18); grouping of guidelines by the clause
# coding in blind_clause_coding.csv; document+string cluster counts; cited sections; training-gold labels in the same context.
import sys; sys.dont_write_bytecode = True
import sys, csv, json, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from load import *

M = B["m"]
member, head_group, rel_group = M["member"], M["head_group"], M["rel_group"]
ROOT = EA.parents[2]
G = "top-4 loop07"
x0 = by[G]
code = defaultdict(dict)
for r in csv.DictReader(open(EA / "outputs" / "blind_clause_coding.csv", encoding="utf-8")):
    code[r["question"]][r["guideline"]] = r["option"]
cols = sorted(mod, key=lambda x: name[x])


def loo(f):
    """Original runs: each run's value minus the mean of the other 18. Returns (mean of all 19, min delta, max delta)."""
    v = {r: f(r) for r in orig}
    d = [v[r] - statistics.mean(v[q] for q in orig if q != r) for r in orig]
    return statistics.mean(v.values()), min(d), max(d)


def show(title, f, q=None):
    om, lo, hi = loo(f)
    print(f"\n  {title}\n     original mean {om:.1f}; one original run vs the other 18: {lo:+.1f} to {hi:+.1f}")
    rows = []
    for x in cols:
        v = f(x) - om
        rows.append((code[q].get(name[x], "") if q else "", name[x], v, "*" if v < lo or v > hi else " "))
    for opt in sorted({r[0] for r in rows}):
        lab = ("coded " + q + ": " + opt) if q else "all"
        print(f"     {lab:<40} " + "  ".join(f"{n.replace('top-', '').replace(' loop', '-')} {v:+5.1f}{s}" for o, n, v, s in rows if o == opt))


def right(ks):
    return lambda x: sum(st(x, k) == "right" for k in ks)


def count(ks, s):
    return lambda x: sum(st(x, k) == s for k in ks)


def clusters(ks, x):
    cl = defaultdict(float)
    for k in ks:
        cl[(k[0], s_(k).lower())] += contrib(x, k)
    return cl


print(f"=== {G}: the three bars against the original's own run-to-run range")
for t in LABS:
    ks = [k for k in gold if k[3] == t]
    om, lo, hi = loo(right(ks))
    print(f"   {t:<16} bar {right(ks)(x0) - om:+6.1f}   one original run vs the other 18: {lo:+.1f} to {hi:+.1f}")

# ---- C1: context / population frame (guideline L65-66, repeated L94, L112, L235)
c1 = [k for k in gold if k[3] in ("SpecificDisease", "DiseaseClass") and k in member and "B2" in member[k]]
print(f"\n### C1 context or population frame -> Modifier (L65): Specific/DiseaseClass gold right after a relational noun + of/with/for/to,"
      f" n={len(c1)} ({sum(k[3] == 'SpecificDisease' for k in c1)} Specific, {sum(k[3] == 'DiseaseClass' for k in c1)} DiseaseClass)")
show("labelled Modifier (count)", count(c1, "label->Modifier"), "Q1")
show("right count", right(c1), "Q1")
for gname in ("history", "risk/susceptibility/predisposition", "case(s) of", "person noun + with/of",
              "frequency/incidence/prevalence/presence/diagnosis"):
    ks = [k for k in c1 if rel_group(k) == gname]
    show(f"labelled Modifier, after '{gname}' (n={len(ks)})", count(ks, "label->Modifier"), "Q1")
cl = clusters(c1, x0)
print(f"   {G}: contribution {sum(cl.values()):+.1f}; {sum(1 for v in cl.values() if v < -0.5)} document+string clusters with a loss over 0.5")
out1 = [k for k in gold if k[3] in ("SpecificDisease", "DiseaseClass") and not (k in member and "B2" in member[k])]
show(f"out of scope: other Specific/DiseaseClass gold labelled Modifier (n={len(out1)})", count(out1, "label->Modifier"), "Q1")
print(f"   out-of-scope Modifier labels in {G} on mentions the original mostly got right:")
for k in out1:
    if st(x0, k) == "label->Modifier" and P[k] > 0.5:
        print(f"      orig right {round(P[k] * 19):2}/19  ...{ctx(k, 40)}...")

# ---- C2: disease token before a gene/protein head (L69-75, repeated L43, L111, L238-243)
c2 = [k for k in gold if k[3] == "Modifier" and k in member and "B1" in member[k] and head_group(k).startswith("molecular")]
ab = [k for k in c2 if not re.search(r"[a-z]{4,}", s_(k))]
print(f"\n### C2 disease name or abbreviation before a gene/protein head -> Modifier (L69): Modifier gold, n={len(c2)} ({len(ab)} abbreviations)")
show("right count, all", right(c2), "Q6")
show("right count, abbreviations", right(ab), "Q6")
show("right count, full names", right([k for k in c2 if k not in ab]), "Q6")
noVHL = [k for k in c2 if s_(k) != "VHL"]
show(f"right count, without the string VHL (n={len(noVHL)})", right(noVHL), "Q6")
cl = clusters(c2, x0)
print(f"   {G}: contribution {sum(cl.values()):+.1f}; {sum(1 for v in cl.values() if v > 0.5)} document+string clusters with a gain over 0.5;"
      " the largest: " + ", ".join(f"{s} ({d}) {v:+.1f}" for (d, s), v in sorted(cl.items(), key=lambda kv: -kv[1])[:3]))
out2 = [k for k in gold if k[3] == "Modifier" and k not in c2]
show(f"out of scope: other Modifier gold, right count (n={len(out2)})", right(out2), "Q6")

# ---- C3: span extension after '<premodifier> form/variant/type/stage of' (L90-97)
FORM = re.compile(r"\b(?!the\b|a\b|an\b)([A-Za-z-]+)\s+(forms?|variants?|types?|stages?|subtypes?)\s+of\s+$", re.I)
c3 = [k for k in gold if k[3] == "SpecificDisease" and FORM.search(texts[k[0]][max(0, k[1] - 60):k[1]])]
print(f"\n### C3 subtype/state-head span extension (L90): Specific gold after '<premodifier> form/variant/type/stage of', n={len(c3)}")
for k in c3:
    print(f"      now {st(x0, k):<22} orig right {round(P[k] * 19):2}/19  ...{ctx(k, 40)}...")
show("boundary count", count(c3, "boundary"))

# ---- cited sections of top-4 loop07's predictions on C1 and C2 mentions
pidx = defaultdict(list)
for line in open(ROOT / "nodes/shared/error-analysis/outputs" / "20261030_rationale_audit" / "prediction_index.jsonl", encoding="utf-8"):
    r = json.loads(line)
    if r["run"].endswith("topk4_loop07"):
        pidx[r["doc"]].append(r)


def cites(ks, want):
    c = Counter()
    for k in ks:
        if st(x0, k) != want:
            continue
        ps = [r for r in pidx[k[0]] if r["start"] < k[2] and r["end"] > k[1]]
        c[(ps[0]["cited_section"] or "")[:70] if ps else "(no overlapping prediction)"] += 1
    return sum(v for s, v in c.items() if re.search(r"context and population|population frame", s, re.I)), sum(c.values()), sum(v for s, v in c.items() if re.search(r"gene or protein|gene/protein", s, re.I))


print(f"\n### cited sections, {G}")
print("   C1 mentions labelled Modifier:", cites(c1, "label->Modifier"))
print("   C2 mentions right:", cites(c2, "right"))

# ---- training gold (heldout50 excluded): labels in the same contexts
DATA = ROOT / "data" / "datasets" / "ncbi_disease"
TEST = set(json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))["documents"])
train = [p for p in sorted((DATA / "train").glob("*.json")) if p.name not in TEST]
B2re = M["B2"]
mol = re.compile(r"\s*(\(\s*[^()]{1,25}?\s*\)\s*)?(genes?|proteins?|products?|locus|loci|alleles?|mutations?|transcripts?|mRNA|cDNA|kinase)\b", re.I)
t1, t2 = Counter(), Counter()
for p in train:
    d = json.loads(p.read_text(encoding="utf-8"))
    t = d["text"]
    for a in d["denotations"]:
        b, e = a["span"]["begin"], a["span"]["end"]
        if B2re.search(t[max(0, b - 80):b]):
            t1[a["obj"]] += 1
        if mol.match(t[e:e + 40]):
            t2[a["obj"]] += 1
print(f"\n### training gold, {len(train)} documents")
print("   gold mentions right after a relational noun + of/with/for/to:", dict(t1))
print("   gold mentions directly before a gene/protein/locus/mutation head:", dict(t2))
