# Step 1 and 2 for top-4 loop07: exact per-mention split of each bar, by context category and destination.
import sys; sys.dont_write_bytecode = True
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from load import *
G = sys.argv[1] if len(sys.argv) > 1 else "top-4 loop07"
x = by[G]
for t in LABS:
    ks = [k for k in gold if k[3] == t]
    bar = sum(contrib(x, k) for k in ks)
    print(f"\n=== {G} {t}: bar {bar:+.1f} (n={len(ks)})")
    # by destination: for each mention, the move = (original typical state -> this run's state)
    cell = defaultdict(float); cnt = Counter()
    for k in ks:
        c = contrib(x, k)
        if abs(c) < 1e-9: continue
        key = (cat(k), "gain" if c > 0 else "loss", st(x, k) if c < 0 else "now right (orig: " + otyp(k) + ")")
        cell[key] += c; cnt[key] += 1
    for key, v in sorted(cell.items(), key=lambda kv: kv[1]):
        if abs(v) >= 1.0:
            print(f"   {v:+6.1f}  n={cnt[key]:3}  {key[0]:<38} {key[1]:4}  {key[2]}")
    small = sum(v for key, v in cell.items() if abs(v) < 1.0)
    print(f"   {small:+6.1f}  (cells under 1.0 in size, summed)")
