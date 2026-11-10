"""Pilot text similarity on the three guidelines judged so far (original, top-4 loop08, top-4 loop04). Offline, 2026-11-10.
Same formula as notes/20261110_type_text_similarity_spec.md step 2, but idf is over these 3 texts only, so the values
are not comparable with the later 12-guideline matrices.
Usage: python -I type_text_pilot_similarity.py [units_dir] > output.txt (default units_dir: outputs/type_text)
"""
import csv, math, re, collections
from pathlib import Path
import sys
D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "outputs" / "type_text"
NAMES = ["original", "top4_loop08", "top4_loop04"]
STOP = set("""i me my myself we our ours ourselves you you're you've you'll you'd your yours yourself yourselves he him his himself
she she's her hers herself it it's its itself they them their theirs themselves what which who whom this that that'll these those
am is are was were be been being have has had having do does did doing a an the and but if or because as until while of at by for
with about against between into through during before after above below to from up down in out on off over under again further
then once here there when where why how all any both each few more most other some such no nor not only own same so than too very
s t can will just don don't should should've now d ll m o re ve y ain aren aren't couldn couldn't didn didn't doesn doesn't hadn
hadn't hasn hasn't haven haven't isn isn't ma mightn mightn't mustn mustn't needn needn't shan shan't shouldn shouldn't wasn
wasn't weren weren't won won't wouldn wouldn't""".split())
def toks(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]
units = {n: list(csv.DictReader(open(D / f"units_{n}.csv", encoding="utf-8"))) for n in NAMES}
for T in ["Modifier", "SpecificDisease", "DiseaseClass"]:
    texts = {n: " ".join(r["text"] for r in units[n] if r["judgement"] == "types" and T in r["types"].split(";")) for n in NAMES}
    tf = {n: collections.Counter(toks(texts[n])) for n in NAMES}
    df = collections.Counter(w for n in NAMES for w in tf[n])
    vec = {}
    for n in NAMES:
        v = {w: c * (math.log((1 + len(NAMES)) / (1 + df[w])) + 1) for w, c in tf[n].items()}
        norm = math.sqrt(sum(x * x for x in v.values()))
        vec[n] = {w: x / norm for w, x in v.items()}
    cos = lambda a, b: sum(x * vec[b].get(w, 0.0) for w, x in vec[a].items())
    print(T)
    for n in NAMES:
        print(f"  {n}: units={sum(1 for r in units[n] if r['judgement']=='types' and T in r['types'].split(';'))}, words={len(toks(texts[n]))}")
    print(f"  cos(top4_loop08, top4_loop04) = {cos('top4_loop08', 'top4_loop04'):.3f}")
    print(f"  cos(top4_loop08, original)    = {cos('top4_loop08', 'original'):.3f}")
    print(f"  cos(top4_loop04, original)    = {cos('top4_loop04', 'original'):.3f}")
