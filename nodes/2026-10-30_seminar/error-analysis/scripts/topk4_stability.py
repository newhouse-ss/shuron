"""Why some top-4 loops improved on validation and others fell, and whether the development gold could have told them apart.

Offline, no API calls. The 10 top-4 loops started from the same guideline and the same 10 development documents; 9 ended
with a changed guideline (loop03 kept the original). Inputs: rule_links.json (validation mentions each changed guideline
fixed or broke against the 19 original runs), rounds.json, history_tally_output.txt, the round snapshots, the final
guidelines, the development gold (training documents) and the validation texts.

A. Validation. Broken mentions split by what went wrong: a disease labeled Modifier (pattern L3), a mention left out
   (M5 tumors or cancer as a class, M7 general words, M8 symptoms and the rest), everything else. Chance from the 19
   original runs, each against the other 18 (rule_links.json chance_items).
B. Claims. What each final guideline says about five development phrases, read by hand (CLAIMS below: label, line, and a
   phrase the script checks is on that line), set against the development gold label of that phrase.
C. Origin. For each claim that contradicts the development gold, the first round whose candidate guideline holds the
   coded phrase, and what that round did on the development documents.
D. Keep rates. Rounds that wrote a family-history Modifier rule where the guideline had none: kept or rejected, top-1
   against top-4 (from history_tally_output.txt).

Writes topk4_stability_output.txt and topk4_stability.json.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
DATA = ROOT / "data" / "datasets" / "ncbi_disease"
NOISE = 0.021  # SD of the difference between two development runs of one guideline (rounds_table.py)

from patterns_lib import AFTER_GENE  # noqa: E402

# same definitions as rule_chain.py
POP = (r"risks?|incidence|prevalence|frequency|predisposition|susceptibility|famil(y|ies)|kindreds?|patients?|cases?|women|men|"
       r"carriers?|individuals|series|members|relatives|populations?|pedigrees?|probands?|boys|girls|males|females|subjects|children")
CONSTRUCTIONS = {
    "after 'history of'": lambda t, b, e: re.search(r"histor(y|ies) of\s+((\S+\s+){1,4}(but not|and / or|and|or|,)\s+)?$", t[max(0, b - 70):b]) is not None,
    "after a risk or population noun": lambda t, b, e: re.search(r"\b(" + POP + r")\s+(of|with|for|to|in|from|among)\s+((the|a|an|other|their)\s+)?$", t[max(0, b - 50):b], re.I) is not None,
    "in a list": lambda t, b, e: re.search(r"(,|\band|\bor)\s+$", t[max(0, b - 6):b]) is not None or re.match(r"\s*(,|and\b|or\b)", t[e:e + 6]) is not None,
}


def construction(t: str, b: int, e: int) -> str:
    return next((name for name, f in CONSTRUCTIONS.items() if f(t, b, e)), "other")


LOOPS = [f"top-4 loop{i:02d}" for i in (1, 2, 4, 5, 6, 7, 8, 9, 10)]
FOLDER = {g: OUT / f"20261022_haiku-xhigh_topk4_{g.split()[1]}" for g in LOOPS}

# B. The five development phrases. Each finds its gold mention(s) in the development gold by text and context.
DEV_DOC = {"FH ovarian cancer": "10196379", "FH cancer": "10196379", "Caucasian cancer cases": "10196379",
           "ichthyosis, spasticity": "10577908", "gene word": None}
PHRASE = {
    "FH ovarian cancer": lambda t, b, e: t[b:e] == "ovarian cancer" and t[:b].endswith("family history of "),
    "FH cancer": lambda t, b, e: t[b:e] == "cancer" and t[:b].endswith("family history of "),
    "Caucasian cancer cases": lambda t, b, e: t[b:e] == "cancer" and t[:b].endswith("Caucasian ") and t[e:].startswith(" cases"),
    "ichthyosis, spasticity": lambda t, b, e: t[b:e] in ("ichthyosis", "spasticity"),
    "gene word": lambda t, b, e: bool(AFTER_GENE.match(t[e:e + 40])),
}
# What each final guideline says about the phrase: (label, line, phrase on that line). "no claim": the guideline does not
# give the phrase a label. "review": routed to review with no label given. "not labeled": left unannotated (or flagged
# for manual checking without a label), which the annotation output records as O.
M, S, DC, NL, NC, RV = "Modifier", "SpecificDisease", "DiseaseClass", "not labeled", "no claim", "review"
CLAIMS = {
    "top-4 loop01": {"FH ovarian cancer": (S, 383, '"ovarian cancer" as **Specific Disease**'),
                     "FH cancer": (DC, 389, 'bare "cancer" in "a family history of cancer"'),
                     "Caucasian cancer cases": (NC, None, None),
                     "ichthyosis, spasticity": (DC, 631, '"ichthyosis" and "spasticity" as **Disease Class**'),
                     "gene word": (M, 348, '"the DTD gene" → "DTD" as **Modifier**')},
    "top-4 loop02": {"FH ovarian cancer": (S, 241, "“family history of ovarian cancer,” “relatives with ovarian cancer”) is annotated as **Specific Disease**"),
                     "FH cancer": (NL, 482, "Bare “cancer” in “a family history of cancer” = not labeled"),
                     "Caucasian cancer cases": (NL, 483, "flagged for manual verification rather than auto-labeled"),
                     "ichthyosis, spasticity": (DC, 450, "“ichthyosis,” “mental retardation,” and “spasticity” = **Disease Class**"),
                     "gene word": (M, 428, "“SLS” is a **Modifier**")},
    "top-4 loop04": {"FH ovarian cancer": (S, 118, 'In "a family history of ovarian cancer," "ovarian cancer" is **Specific Disease**'),
                     "FH cancer": (NC, None, None),
                     "Caucasian cancer cases": (NC, None, None),
                     "ichthyosis, spasticity": (DC, 285, '"spasticity" = **Disease Class**'),
                     "gene word": (M, 122, 'In "SLS genes," "SLS" is **Modifier**')},
    # line 161 makes a disease named in a family-history phrase Modifier; the guideline does not quote this phrase
    "top-4 loop05": {"FH ovarian cancer": (M, 161, "the named disease is a **Modifier**"),
                     "FH cancer": (NL, 160, "“a family history of cancer”) is not annotated"),
                     "Caucasian cancer cases": (NL, 160, "(e.g., “91 Caucasian cancer cases,”"),
                     "ichthyosis, spasticity": (NL, 273, "“ichthyosis” and “spasticity” are physical signs and are not annotated"),
                     "gene word": (M, 91, "“the DTD gene” → “DTD” as **Modifier**")},
    "top-4 loop06": {"FH ovarian cancer": (M, 340, "“ovarian cancer” is **Modifier**. It appears in a family-history construction"),
                     "FH cancer": (NC, None, None),
                     "Caucasian cancer cases": (NC, None, None),
                     "ichthyosis, spasticity": (DC, 323, "“ichthyosis,” “mental retardation,” and “spasticity” are **Disease Class**"),
                     "gene word": (M, 171, "“ancient SLS genes”: “SLS” is **Modifier**")},
    # line 232 leaves "ichthyosis" with its existing label and gives "spasticity" none
    "top-4 loop07": {"FH ovarian cancer": (M, 66, "“family history of ovarian cancer,” and “ovarian cancer risk” are annotated as **Modifier**"),
                     "FH cancer": (NC, None, None),
                     "Caucasian cancer cases": (NC, None, None),
                     "ichthyosis, spasticity": (NC, 232, "its existing label stands"),
                     "gene word": (M, 70, "“DTD gene” → “DTD” as **Modifier**")},
    "top-4 loop08": {"FH ovarian cancer": (M, 48, 'the complement of a history frame (e.g., "a family history of ovarian cancer")'),
                     "FH cancer": (NC, None, None),
                     "Caucasian cancer cases": (NC, None, None),
                     "ichthyosis, spasticity": (NL, 247, "“ichthyosis” and “spasticity” = O"),
                     "gene word": (M, 259, "“DTD” as a premodifier of “gene” is **Modifier**")},
    "top-4 loop09": {"FH ovarian cancer": (M, 132, "“a family history of ovarian cancer” → “ovarian cancer” = **Modifier**"),
                     "FH cancer": (NC, None, None),
                     "Caucasian cancer cases": (NC, None, None),
                     "ichthyosis, spasticity": (RV, 205, "Route them to separate guideline-consistency review"),
                     "gene word": (M, 127, "“SLS genes” → “SLS” = **Modifier**")},
    "top-4 loop10": {"FH ovarian cancer": (M, 148, "“a family history of ovarian cancer”: “ovarian cancer” is **Modifier**."),
                     "FH cancer": (NL, 191, "used generically (e.g., “a family history of cancer”)"),
                     "Caucasian cancer cases": (NL, 191, "or used as a premodifier (e.g., “91 Caucasian cancer cases”), is a general term and is not annotated"),
                     "ichthyosis, spasticity": (NL, 209, "(e.g., ichthyosis, spasticity, or a deficient activity"),
                     "gene word": (M, 130, "“the DTD gene”: “DTD” is **Modifier**")},
}
# How far each family-history Modifier rule reaches, by its own wording: "history only" names no frame noun besides
# history; "wider" names other nouns or a general class (line and phrase asserted).
SCOPE = {
    "top-4 loop05": ("wider", 159, "Do not annotate bare cohort, family-history, or risk descriptors"),
    "top-4 loop06": ("wider", 150, "disease names that modify human or clinical nouns (e.g., patients, cases, families, risk, population, phenotype)"),
    "top-4 loop07": ("wider", 65, "is the complement of, a context or population noun (such as *cases*, *population*, *history*, *risk*, or *incidence*)"),
    "top-4 loop08": ("history only", 48, "the complement of a history frame"),
    "top-4 loop09": ("wider", 158, "**Family-history and cohort descriptors** are **Modifier** (Section 3), even when the disease term is the complement of “of”"),
    "top-4 loop10": ("wider", 146, "A disease that qualifies a relational noun phrase"),
}

out: list[str] = []
rec: dict = {"loops": {}, "claims": {}, "origins": [], "keep_rates": {}}

# ---------------------------------------------------------------- A. validation
links = json.loads((HERE / "rule_links.json").read_text(encoding="utf-8"))
vtext = {p.stem: json.loads(p.read_text(encoding="utf-8"))["text"] for p in (DATA / "valid").glob("*.json")}
LEFT_OUT = ("M5", "M7", "M8")


def split(items: list) -> dict:
    l3 = [x for x in items if x["pattern"] == "L3"]
    lo = [x for x in items if x["pattern"] in LEFT_OUT]
    return {"turned Modifier": len(l3),
            "turned Modifier, by construction": dict(Counter(construction(vtext[x["doc"]], *x["span"]) for x in l3)),
            "left out": len(lo),
            "left out, by construction": dict(Counter(construction(vtext[x["doc"]], *x["span"]) for x in lo)),
            "rest": len(items) - len(l3) - len(lo)}


def split_fixed(items: list) -> dict:
    gene = sum(1 for x in items if x["pattern"] == "M1")
    lo = sum(1 for x in items if x["pattern"] in LEFT_OUT)
    return {"gene word": gene, "left out": lo, "rest": len(items) - gene - lo}


# validation F1 of the 19 original-guideline runs, from the per-run table of error_table_output.txt
orig_f1 = []
for line in (ROOT / "nodes/shared/error-analysis/outputs" / "error_table_output.txt").read_text(encoding="utf-8").split("\n"):
    m = re.match(r"(E1|top-[14])\s+(run|loop)\d+\s+original\s+(\d+)\s+(\d+)\s+(\d+)\s", line)
    if m:
        tp, fp, fn = map(int, m.groups()[2:])
        orig_f1.append(2 * tp / (2 * tp + fp + fn))
assert len(orig_f1) == 19
lo_o, hi_o = min(orig_f1), max(orig_f1)
rec["original_f1"] = {"mean": statistics.mean(orig_f1), "min": lo_o, "max": hi_o}

chance = [split(c["broken"]) for c in links["chance_items"]]
chance_fixed = [split_fixed(c["fixed"]) for c in links["chance_items"]]
out.append("A. Validation: what the 9 changed top-4 guidelines fixed and broke (one run each, against the 19 original runs)")
out.append(f"   original runs: F1 mean {statistics.mean(orig_f1):.3f}, range {lo_o:.3f} to {hi_o:.3f}")
out.append(f"   {'loop':<13} {'F1':>6} {'group':<7} {'fixed':>5} ({'gene word':>9} {'left out':>8} {'rest':>4}) "
           f"{'broken':>6} ({'turned Modifier':>15} {'left out':>8} {'rest':>4})")
rows = []
for g in sorted(LOOPS, key=lambda g: -links["guidelines"][g]["f1"]):
    G = links["guidelines"][g]
    sp, fx = split(G["items"]["broken"]), split_fixed(G["items"]["fixed"])
    grp = "above" if G["f1"] > hi_o else ("below" if G["f1"] < lo_o else "inside")
    rows.append((g, G["f1"], len(G["items"]["fixed"]), len(G["items"]["broken"]), sp))
    rec["loops"][g] = {"f1": G["f1"], "group": grp, "fixed": len(G["items"]["fixed"]), "fixed_split": fx,
                       "broken": len(G["items"]["broken"]), "broken_split": sp}
    out.append(f"   {g:<13} {G['f1']:>6.3f} {grp:<7} {len(G['items']['fixed']):>5} ({fx['gene word']:>9} {fx['left out']:>8} {fx['rest']:>4}) "
               f"{len(G['items']['broken']):>6} ({sp['turned Modifier']:>15} {sp['left out']:>8} {sp['rest']:>4})")
for k in ("gene word", "left out", "rest"):
    xs = [c[k] for c in chance_fixed]
    out.append(f"   chance level, fixed '{k}': mean {statistics.mean(xs):.1f}, max {max(xs)}")
for k in ("turned Modifier", "left out", "rest"):
    xs = [c[k] for c in chance]
    out.append(f"   chance level, broken '{k}': mean {statistics.mean(xs):.1f}, max {max(xs)}")
xs = [len(c["broken"]) for c in links["chance_items"]]
out.append(f"   chance level for all broken: mean {statistics.mean(xs):.1f}, max {max(xs)}")
for grp in ("above", "below"):
    L = [v for v in rec["loops"].values() if v["group"] == grp]
    rec.setdefault("group_means", {})[grp] = {
        "n": len(L), "fixed": statistics.mean(v["fixed"] for v in L), "broken": statistics.mean(v["broken"] for v in L),
        "turned_modifier_plus_left_out": statistics.mean(v["broken_split"]["turned Modifier"] + v["broken_split"]["left out"] for v in L)}
gm = rec["group_means"]
out.append(f"   loops above the original range ({gm['above']['n']}) against loops below it ({gm['below']['n']}), means: "
           f"fixed {gm['above']['fixed']:.1f} vs {gm['below']['fixed']:.1f}, broken {gm['above']['broken']:.1f} vs {gm['below']['broken']:.1f}, "
           f"of which turned Modifier + left out {gm['above']['turned_modifier_plus_left_out']:.1f} vs {gm['below']['turned_modifier_plus_left_out']:.1f}")


def ranks(v: list) -> list:
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
            j += 1
        for k in range(i, j + 1):
            r[s[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


f1 = [r[1] for r in rows]
for name, col in (("fixed", [r[2] for r in rows]), ("broken", [r[3] for r in rows]),
                  ("turned Modifier + left out", [r[4]["turned Modifier"] + r[4]["left out"] for r in rows])):
    rho = statistics.correlation(ranks(f1), ranks(col))
    rec.setdefault("spearman_f1", {})[name] = rho
    out.append(f"   Spearman between validation F1 and {name}: {rho:+.2f} (n = 9)")
out.append("   'turned Modifier' by construction of the mention:")
for g, *_r, sp in rows:
    out.append(f"      {g}: {sp['turned Modifier, by construction']}")
out.append("   'left out' by construction of the mention:")
for g, *_r, sp in rows:
    out.append(f"      {g}: {sp['left out, by construction']}")

# ---------------------------------------------------------------- B. claims against the development gold
dev_files = [d["filename"] for d in json.loads((FOLDER["top-4 loop08"] / "inputs" / "sampled_train_documents.json").read_text(encoding="utf-8"))]
dev = {}
for f in dev_files:
    d = json.loads((DATA / "train" / f).read_text(encoding="utf-8"))
    dev[f[:-5]] = (d["text"], [(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d["denotations"]])
targets = {}
for p, test in PHRASE.items():
    docs = [DEV_DOC[p]] if DEV_DOC[p] else list(dev)
    targets[p] = [(doc, b, e, lab) for doc in docs for b, e, lab in dev[doc][1] if test(dev[doc][0], b, e)]
    assert targets[p], p
gold_of = {p: Counter(lab for *_x, lab in v) for p, v in targets.items()}
out.append("\nB. What each final guideline says about five development phrases, against their development gold label")
out.append("   development gold: " + "; ".join(f"{p}: {dict(c)}" for p, c in gold_of.items()))
by_cons = {name: Counter() for name in ("after 'history of'", "after a risk or population noun")}
cons_items = {name: [] for name in by_cons}
for doc, (t, gold) in dev.items():
    for b, e, lab in gold:
        c = construction(t, b, e)
        if c in by_cons:
            by_cons[c][lab] += 1
            cons_items[c].append(f"{t[max(0, b - 25):b].split(chr(10))[-1].strip()} [{t[b:e]}] {lab}")
rec["dev_by_construction"] = {c: dict(v) for c, v in by_cons.items()}
for c, v in by_cons.items():
    out.append(f"   development gold {c}: {dict(v)}")
    for x in cons_items[c]:
        out.append(f"      {x}")
for g in LOOPS:
    lines = (FOLDER[g] / "final" / "final_guidelines.txt").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    rec["claims"][g] = {}
    cells = []
    for p, (claim, line, phrase) in CLAIMS[g].items():
        if line:
            assert phrase in lines[line - 1], (g, p, line)
        gold = gold_of[p].most_common(1)[0][0]
        assert len(gold_of[p]) == 1, p  # each phrase has one gold label in the development set
        verdict = "-" if claim in (NC, RV) else ("agrees" if claim == gold else "CONTRADICTS")
        rec["claims"][g][p] = {"claim": claim, "line": line, "gold": gold, "verdict": verdict}
        cells.append(f"{p}: {claim}{f' (L{line})' if line else ''} {verdict}")
    n = sum(1 for v in rec["claims"][g].values() if v["verdict"] == "CONTRADICTS")
    out.append(f"   {g} (F1 {links['guidelines'][g]['f1']:.3f}): {n} contradicting")
    for c in cells:
        out.append(f"      {c}")
for g, (scope, line, phrase) in SCOPE.items():
    lines = (FOLDER[g] / "final" / "final_guidelines.txt").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    assert phrase in lines[line - 1], (g, line)
    rec["claims"][g]["FH ovarian cancer"]["scope"] = scope
out.append("   reach of the family-history Modifier rule, by its own wording: "
           + "; ".join(f"{g.split()[1]} {s[0]} (L{s[1]})" for g, s in SCOPE.items()))
contra = Counter(p for g in LOOPS for p, v in rec["claims"][g].items() if v["verdict"] == "CONTRADICTS")
agree = Counter(p for g in LOOPS for p, v in rec["claims"][g].items() if v["verdict"] == "agrees")
out.append("   claims that contradict the development gold, by phrase: " + ", ".join(f"{p} {contra[p]}" for p in PHRASE))
out.append("   claims that agree with it, by phrase: " + ", ".join(f"{p} {agree[p]}" for p in PHRASE))

# ---------------------------------------------------------------- C. origin round of each contradicting claim
rounds = {(r["loop"], r["round"]): r for r in json.loads((HERE / "rounds.json").read_text(encoding="utf-8")) if r["method"] == "top-4"}


def labels(diag: dict, doc: str) -> dict:
    f = next(x for x in diag["files"] if x["filename"] == f"{doc}.json")
    return {(d["start"], d["end"]): d["label"] for d in f["study_denotations"]}


def dev_moves(s: dict) -> tuple[int, int]:
    """Development gold mentions that went from right to wrong and from wrong to right in this round."""
    broke = fixed = 0
    for doc, (t, gold) in dev.items():
        bef, cand = labels(s["diagnostics_before"], doc), labels(s["diagnostics_candidate"], doc)
        for b, e, lab in gold:
            was, now = bef.get((b, e)) == lab, cand.get((b, e)) == lab
            broke += was and not now
            fixed += now and not was
    return broke, fixed


def p_chance(d: float) -> float:
    return 1 - statistics.NormalDist(0, NOISE).cdf(abs(d))


hist = []
for line in (HERE / "history_tally_output.txt").read_text(encoding="utf-8").split("\n")[2:]:
    m = re.match(r"\s+(topk[14]_loop\d+)\s+(\d+) (kept|rejected)\s+(yes|no)\s+(no rule|Modifier|Specific|other)\s+(no rule|Modifier|Specific|other)\s", line)
    if m:
        hist.append(m.groups())
assert len(hist) == 44

out.append("\nC. The round in which each contradicting claim entered the guideline, and that round on the development documents")
out.append("   (family-history rule: first kept round coded Modifier in history_tally_output.txt; other claims: first kept candidate holding the coded phrase)")
for g in LOOPS:
    snaps = sorted((FOLDER[g] / "rounds").glob("iteration_*/snapshot.json"))
    for p, v in rec["claims"][g].items():
        if v["verdict"] != "CONTRADICTS":
            continue
        phrase = CLAIMS[g][p][2]
        first = None
        for sp in snaps:
            s = json.loads(sp.read_text(encoding="utf-8"))
            if p == "FH ovarian cancer":
                h = next(h for h in hist if h[0] == "topk4_" + g.split()[1] and int(h[1]) == s["iteration"])
                hit = h[2] == "kept" and h[5] == "Modifier"
            else:
                hit = s["improved"] and phrase in s["guidelines_candidate"]
            if hit:
                first = s
                break
        assert first is not None, (g, p)
        r = rounds[(int(g[-2:]), first["iteration"])]
        d = r["f1_candidate"] - r["f1_before"]
        bef = [labels(first["diagnostics_before"], doc).get((b, e), "O") for doc, b, e, _lab in targets[p]]
        cand = [labels(first["diagnostics_candidate"], doc).get((b, e), "O") for doc, b, e, _lab in targets[p]]
        broke, fixed = dev_moves(first)
        rec["origins"].append({"loop": g, "phrase": p, "round": first["iteration"], "dev_gain": d, "chance": p_chance(d),
                               "phrase_labels_before": bef, "phrase_labels_candidate": cand,
                               "dev_right_to_wrong": broke, "dev_wrong_to_right": fixed})
        out.append(f"   {g} {p}: round {first['iteration']}, dev F1 {r['f1_before']:.3f} -> {r['f1_candidate']:.3f} "
                   f"({d:+.3f}, chance {p_chance(d):.1%}); the phrase's dev label {bef} -> {cand}; "
                   f"dev gold mentions right -> wrong {broke}, wrong -> right {fixed}")
og = rec["origins"]
gold_lab = {p: gold_of[p].most_common(1)[0][0] for p in PHRASE}
flipped = [o for o in og if any(b == gold_lab[o["phrase"]] and c != gold_lab[o["phrase"]]
                                for b, c in zip(o["phrase_labels_before"], o["phrase_labels_candidate"]))]
rounds_seen = {(o["loop"], o["round"]): o for o in og}
out.append(f"   {len(og)} contradicting claims entered in {len(rounds_seen)} rounds, all kept; in {len(flipped)} of the {len(og)} the "
           f"round's own development run turned the phrase from right to wrong; "
           f"{sum(1 for o in rounds_seen.values() if o['chance'] >= 0.05)} of the {len(rounds_seen)} rounds gained so little that luck alone gives that at least 1 time in 20")

# ---------------------------------------------------------------- D. keep rates, top-1 against top-4
def fisher2(a: int, n1: int, c: int, n2: int) -> float:
    """Two-sided Fisher exact test: a of n1 against c of n2."""
    k, n = a + c, n1 + n2
    probs = {i: comb(n1, i) * comb(n2, k - i) / comb(n, k) for i in range(max(0, k - n2), min(k, n1) + 1)}
    return sum(q for q in probs.values() if q <= probs[a] + 1e-12)


out.append("\nD. Keep decisions on rounds that wrote a family-history Modifier rule where the guideline had none (history_tally_output.txt)")
for k in ("topk1", "topk4"):
    rs = [h for h in hist if h[0].startswith(k) and h[4] == "no rule" and h[5] == "Modifier"]
    others = [h for h in hist if h[0].startswith(k) and h not in rs]
    kept, ko = sum(1 for h in rs if h[2] == "kept"), sum(1 for h in others if h[2] == "kept")
    rec["keep_rates"][k] = {"new_rule": [kept, len(rs)], "other_rounds": [ko, len(others)]}
    out.append(f"   {k.replace('topk', 'top-')}: rounds that wrote it kept {kept} of {len(rs)} "
               f"({', '.join(f'{h[0][-6:]} r{h[1]} {h[2]}' for h in rs)}); other rounds kept {ko} of {len(others)}")
t1, t4 = rec["keep_rates"]["topk1"], rec["keep_rates"]["topk4"]
p_method = fisher2(t1["new_rule"][0], t1["new_rule"][1], t4["new_rule"][0], t4["new_rule"][1])
p_within = fisher2(t4["new_rule"][0], t4["new_rule"][1], t4["other_rounds"][0], t4["other_rounds"][1])
rec["keep_rates"]["fisher_top1_vs_top4_new_rule"] = p_method
rec["keep_rates"]["fisher_top4_new_rule_vs_other"] = p_within
out.append(f"   two-sided Fisher exact p: rounds that wrote it, top-1 against top-4 {p_method:.3f}; "
           f"within top-4, rounds that wrote it against other rounds {p_within:.3f}")
allr = {k: [sum(1 for h in hist if h[0].startswith(k) and h[2] == "kept"), sum(1 for h in hist if h[0].startswith(k))] for k in ("topk1", "topk4")}
rec["keep_rates"]["all_rounds"] = allr
out.append(f"   all rounds: top-1 kept {allr['topk1'][0]} of {allr['topk1'][1]}, top-4 kept {allr['topk4'][0]} of {allr['topk4'][1]}")
n_coded = sum(1 for g in LOOPS for v in rec["claims"][g].values())
n_agree = sum(1 for g in LOOPS for v in rec["claims"][g].values() if v["verdict"] == "agrees")
n_contra = sum(1 for g in LOOPS for v in rec["claims"][g].values() if v["verdict"] == "CONTRADICTS")
out.append(f"\nCoded statements: {n_coded} (9 guidelines x 5 phrases); contradict the development gold {n_contra}, agree {n_agree}, "
           f"no label or sent to review {n_coded - n_contra - n_agree}")

(HERE / "topk4_stability_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
(HERE / "topk4_stability.json").write_bytes(json.dumps(rec, ensure_ascii=False, indent=1).encode("utf-8"))
print("\n".join(out))
