# Step 5 for top-4 loop07: each bar split exactly into the parts of the clauses that passed the checks and the remainder;
# the remainder is compared with the original's own run-to-run range of the same set, and its largest clusters are listed.
import sys; sys.dont_write_bytecode = True
import sys, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from load import *

M = B["m"]
member, head_group = M["member"], M["head_group"]
G = "top-4 loop07"
x0 = by[G]
c1 = {k for k in gold if k[3] in ("SpecificDisease", "DiseaseClass") and k in member and "B2" in member[k]}
c2 = {k for k in gold if k[3] == "Modifier" and k in member and "B1" in member[k] and head_group(k).startswith("molecular")}
FORM = re.compile(r"\b(?!the\b|a\b|an\b)([A-Za-z-]+)\s+(forms?|variants?|types?|stages?|subtypes?)\s+of\s+$", re.I)
c3 = {k for k in gold if k[3] == "SpecificDisease" and FORM.search(texts[k[0]][max(0, k[1] - 60):k[1]])}
vhl = {k for k in c2 if s_(k) == "VHL"}
PARTS = [("context-frame clause L65 (C1)", c1), ("gene-designation clause L69 (C2), string VHL", vhl),
         ("gene-designation clause L69 (C2), other", c2 - vhl), ("span-extension clause L90 (C3)", c3)]


def loo(ks):
    v = {r: sum(st(r, k) == "right" for k in ks) for r in orig}
    d = [v[r] - statistics.mean(v[q] for q in orig if q != r) for r in orig]
    return min(d), max(d)


for t in LABS:
    ks = [k for k in gold if k[3] == t]
    bar = sum(contrib(x0, k) for k in ks)
    lo, hi = loo(ks)
    print(f"\n=== {G} {t}: bar {bar:+.1f} (one original run vs the other 18: {lo:+.1f} to {hi:+.1f})")
    used = set()
    for lab, s in PARTS:
        part = [k for k in ks if k in s and k not in used]
        if not part:
            continue
        used |= set(part)
        lo, hi = loo(part)
        print(f"   {sum(contrib(x0, k) for k in part):+6.1f}  {lab:<46} n={len(part):3}  noise {lo:+.1f} to {hi:+.1f}")
    rest = [k for k in ks if k not in used]
    lo, hi = loo(rest)
    print(f"   {sum(contrib(x0, k) for k in rest):+6.1f}  {'remainder':<46} n={len(rest):3}  noise {lo:+.1f} to {hi:+.1f}")
    cl = defaultdict(list)
    for k in rest:
        cl[(k[0], s_(k).lower())].append(k)
    big = sorted(cl.items(), key=lambda kv: -abs(sum(contrib(x0, k) for k in kv[1])))[:8]
    for (d, s), mem in big:
        k = mem[0]
        print(f"        {sum(contrib(x0, k) for k in mem):+5.1f} x{len(mem)} now={st(x0, k):<24} ...{ctx(k, 35)}...")
