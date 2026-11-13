# The Specific bar's null values: each original run's right count minus the mean of the other 18, and the identity
# d_r = 19/18 * (v_r - mean of all 19).
import sys; sys.dont_write_bytecode = True
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from load import *
S = [k for k in gold if k[3] == "SpecificDisease"]
v = {r: sum(st(r, k) == "right" for k in S) for r in orig}
m19 = statistics.mean(v.values())
for r in orig:
    d = v[r] - statistics.mean(v[q] for q in orig if q != r)
    print(f"{r:<36} v={v[r]:3}  d={d:+6.1f}  19/18*(v-mean19)={19 / 18 * (v[r] - m19):+6.1f}")
print(f"mean19={m19:.2f}; top-4 loop07 v={sum(st(by['top-4 loop07'], k) == 'right' for k in S)}")
