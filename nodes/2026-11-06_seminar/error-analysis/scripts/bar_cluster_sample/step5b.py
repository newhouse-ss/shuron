# Step 5 variant: the context-frame set widened from the text only (a parenthetical after the noun, a comma after the
# preposition, singular "factor"), written after seeing the four misses in step34; shows how the Specific remainder changes.
import sys; sys.dont_write_bytecode = True
import sys, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from load import *
M = B["m"]; G = "top-4 loop07"; x0 = by[G]
REL = M["REL"] + "|factor"
B2x = re.compile(r"\b(" + REL + r")\s*(\(\s*[^()]{1,30}?\s*\)\s*)?(of|with|for|to)\s*,?\s+((the|a|an)\s+)?((\S+\s+){1,5}(but not|and / or|and|or)\s+)?$", re.I)
FORM = re.compile(r"\b(?!the\b|a\b|an\b)([A-Za-z-]+)\s+(forms?|variants?|types?|stages?|subtypes?)\s+of\s+$", re.I)
S = [k for k in gold if k[3] == "SpecificDisease"]
c1 = [k for k in S if B2x.search(texts[k[0]][max(0, k[1] - 80):k[1]])]
c3 = [k for k in S if k not in c1 and FORM.search(texts[k[0]][max(0, k[1] - 60):k[1]])]
rest = [k for k in S if k not in c1 and k not in c3]
def loo(ks):
    v = {r: sum(st(r, k) == "right" for k in ks) for r in orig}
    d = [v[r] - statistics.mean(v[q] for q in orig if q != r) for r in orig]
    return min(d), max(d)
for lab, ks in (("context frame, widened", c1), ("span extension", c3), ("remainder", rest)):
    lo, hi = loo(ks)
    print(f"{lab:<24} n={len(ks):3} contribution {sum(contrib(x0, k) for k in ks):+6.1f}  noise {lo:+.1f} to {hi:+.1f}")
