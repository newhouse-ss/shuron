# Shared read-only loader: runs bar_attribution.py (which runs modifier_subset.py) with every file write blocked.
import contextlib, io, pathlib, runpy, statistics
from collections import Counter, defaultdict
EA = pathlib.Path(__file__).resolve().parents[2]   # nodes/2026-11-06_seminar/error-analysis
pathlib.Path.write_bytes = lambda self, data: len(data)
pathlib.Path.write_text = lambda self, data, *a, **k: len(data)
with contextlib.redirect_stdout(io.StringIO()):
    B = runpy.run_path(str(EA / "scripts" / "bar_attribution.py"))
texts, gold, state, orig, mod, name, cat, C = (B[k] for k in ("texts", "gold", "state", "orig", "mod", "name", "cat", "C"))
by = {name[x]: x for x in mod}
LABS = ["SpecificDisease", "DiseaseClass", "Modifier"]
def st(x, k):
    s = state[x].get(k)
    return "right" if not s else (f"label->{s[2]}" if s[0] == "label" else s[0])
P = {k: statistics.mean(st(x, k) == "right" for x in orig) for k in gold}          # original right-rate
def contrib(x, k): return (st(x, k) == "right") - P[k]
def otyp(k):  # the original's most common state
    return Counter(st(x, k) for x in orig).most_common(1)[0][0]
def s_(k): return texts[k[0]][k[1]:k[2]]
def ctx(k, w=45): return (texts[k[0]][max(0, k[1]-w):k[1]] + "[[" + s_(k) + "]]" + texts[k[0]][k[2]:k[2]+w]).replace("\n", " ")
