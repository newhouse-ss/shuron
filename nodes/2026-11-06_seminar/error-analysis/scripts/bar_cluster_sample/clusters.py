# Step 2 detail: members of the large cells, grouped by (document, lower-cased string); shows the context of each.
import sys; sys.dont_write_bytecode = True
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from load import *
G = sys.argv[1]; x = by[G]
CELLS = [("S after relational noun", "loss"), ("S other", "loss"), ("S tumour word", "loss"), ("S coordinated", "loss"),
         ("M abbreviation before gene/protein noun", "gain"), ("M full name before gene/protein noun", "gain"), ("M other", "gain"),
         ("D bare cancer/tumor", "loss"), ("D named or category", "loss")]
for c, d in CELLS:
    ks = [k for k in C[c] if (contrib(x, k) < -1e-9 if d == "loss" else contrib(x, k) > 0.3)]
    if not ks: continue
    print(f"\n### {c} {d}: {len(ks)} mentions, sum {sum(contrib(x, k) for k in ks):+.1f}")
    cl = defaultdict(list)
    for k in ks: cl[(k[0], s_(k).lower())].append(k)
    print(f"    clusters (document + string): {len(cl)}")
    for (doc, s), mem in sorted(cl.items(), key=lambda kv: sum(contrib(x, k) for k in kv[1])):
        k = mem[0]
        o = Counter(st(y, k) for y in orig).most_common(2)
        print(f"   {sum(contrib(x, k) for k in mem):+5.1f} x{len(mem)} {doc} now={st(x, k):<22} orig={o}  ...{ctx(k)}...")
