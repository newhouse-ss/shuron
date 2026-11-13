"""From the changed guidelines' validation gains and losses back to the rules, and from the rules back to what the rewrite saw.

Offline, no API calls. Reads rule_links.json (from rule_links.py), the validation, development and training gold
(the 50 test documents excluded), each loop's final guideline, and every round's prompts and snapshot.

A. Every fixed or broken validation mention gets one construction from the text around it (CONSTRUCTIONS, first
   match). Counts per changed guideline, against chance (each original run against the other 18, rule_links.py).
B. What the rewrite step could see. Each round's rewrite prompt shows five development documents as "do not break"
   examples (the analysis prompts show the same block as "true positive examples"): the full text, and under it at
   most n_examples = 5 of the mentions the annotator got right, in set order (iterative.py, lines 393 to 397). For
   the development gold mentions behind three rules, count three channels separately: the rewrite prompt's list
   (document shown, label listed), the analysis prompts' error examples (with the gold label), and whether the
   mention string appears in the round's principles (a string match, not a measure of what rule was passed on);
   and the rounds in which the run before the rewrite had the mention right. Also: how many document blocks hit the cap,
   and whether new Modifier labels after "history of" separate kept from rejected rounds.
C. Two rules that 10 of the 11 changed guidelines state in some form, read and coded by hand (HISTORY, SYMPTOM_LIST below:
   the label each final guideline gives, with the line that says so; the script checks the phrase is on that line),
   set against the validation mentions of the same construction that the guideline fixed or broke.
D. Training gold for the same constructions.

Writes rule_chain_output.txt and rule_chain.json.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
DATA = ROOT / "data" / "datasets" / "ncbi_disease"

from patterns_lib import AFTER_GENE  # noqa: E402

TEST = set(json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))["documents"])
DEV = [d["filename"] for d in json.loads((OUT / "20261022_haiku-xhigh_topk4_loop08" / "inputs" / "sampled_train_documents.json").read_text(encoding="utf-8"))]
assert not set(DEV) & TEST

POP = (r"risks?|incidence|prevalence|frequency|predisposition|susceptibility|famil(y|ies)|kindreds?|patients?|cases?|women|men|"
       r"carriers?|individuals|series|members|relatives|populations?|pedigrees?|probands?|boys|girls|males|females|subjects|children")
CONSTRUCTIONS = {
    "before a gene word": lambda t, b, e: bool(AFTER_GENE.match(t[e:e + 40])) or t[b:e].lower().endswith("deficient"),
    # the object of "history of", or a later conjunct of it ("history of breast cancer but not ovarian cancer")
    "after 'history of'": lambda t, b, e: re.search(r"histor(y|ies) of\s+((\S+\s+){1,4}(but not|and / or|and|or|,)\s+)?$", t[max(0, b - 70):b]) is not None,
    "after a risk or population noun": lambda t, b, e: re.search(r"\b(" + POP + r")\s+(of|with|for|to|in|from|among)\s+((the|a|an|other|their)\s+)?$", t[max(0, b - 50):b], re.I) is not None,
    "before a population noun": lambda t, b, e: re.match(r"\s*(" + POP + r"|stud(y|ies)|samples?|cells?|lines?|tissues?|types?|foci|suppressors?|growth|formation)\b", t[e:e + 30], re.I) is not None,
    "in a list": lambda t, b, e: re.search(r"(,|\band|\bor)\s+$", t[max(0, b - 6):b]) is not None or re.match(r"\s*(,|and\b|or\b)", t[e:e + 6]) is not None,
}
OTHER = "other"
CONS = list(CONSTRUCTIONS) + [OTHER]


def construction(t: str, b: int, e: int) -> str:
    return next((name for name, f in CONSTRUCTIONS.items() if f(t, b, e)), OTHER)


# C. Hand-coded: the label each final guideline gives (1) a single disease named after "a family history of" and
# (2) the bare symptoms "ichthyosis" and "spasticity" in the development sentence "characterized by ichthyosis,
# mental retardation, spasticity, and deficient activity of fatty aldehyde dehydrogenase" (gold: DiseaseClass).
HISTORY = {
    "top-4 loop08": ("Modifier", 48, "the complement of a history frame"),
    "top-4 loop04": ("Specific", 118, 'In "a family history of ovarian cancer," "ovarian cancer" is **Specific Disease**'),
    "top-4 loop01": ("not Modifier", 373, 'is not a Modifier. It is governed by Section 3.4(a)'),
    "top-1 loop07": ("no rule", None, None),
    "top-4 loop09": ("Modifier", 130, "A disease named in a family history of relatives"),
    "top-4 loop02": ("Specific", 30, "a single named disease that is the nominal head of an"),
    # line 160 leaves a bare, unspecified "cancer" in a family history unannotated; line 161 makes a named disease there Modifier
    "top-4 loop05": ("Modifier", 161, "the named disease is a **Modifier**"),
    "top-4 loop07": ("Modifier", 65, "or is the complement of, a context or population noun"),
    "top-4 loop06": ("Modifier", 120, "patients, cases, families, risk, population, history). It is **Modifier**"),
    "top-1 loop05": ("Modifier", 63, "keeps its existing treatment (Modifier under Section 3)"),
    "top-4 loop10": ("Modifier", 146, "A disease that qualifies a relational noun phrase"),
}
SYMPTOM_LIST = {
    "top-4 loop08": ("O", 104, "remains O"),
    "top-4 loop04": ("DiseaseClass", 285, "coordinated member of the manifestation list"),
    "top-4 loop01": ("DiseaseClass", 631, "bare sign nouns in a"),
    "top-1 loop07": ("O, flagged", 42, "It stays unannotated and is flagged for guideline review"),
    "top-4 loop09": ("sent to review", 205, "Route them to separate guideline-consistency review"),
    "top-4 loop02": ("DiseaseClass", 450, "pass the head-noun test"),
    "top-4 loop05": ("O", 273, "are physical signs and are not annotated"),
    "top-4 loop07": ("unchanged", 232, "its existing label stands"),
    "top-4 loop06": ("DiseaseClass", 323, "coordinated symptom list governed by"),
    "top-1 loop05": ("no rule", None, None),
    "top-4 loop10": ("O, sent to audit", 295, "They are routed to audit, not annotated"),
}
FOLDER = {f"top-{k} loop{i:02d}": OUT / f"20261022_haiku-xhigh_topk{k}_loop{i:02d}" for k in (1, 4) for i in range(1, 11)}

links = json.loads((HERE / "rule_links.json").read_text(encoding="utf-8"))
vtext = {p.stem: json.loads(p.read_text(encoding="utf-8"))["text"] for p in (DATA / "valid").glob("*.json")}


def tag(items: list) -> Counter:
    return Counter(construction(vtext[x["doc"]], *x["span"]) for x in items)


def symptom(items: list) -> list:
    """Missed symptoms and general words (patterns M7, M8) in a list."""
    return [x for x in items if x["pattern"] in ("M7", "M8") and construction(vtext[x["doc"]], *x["span"]) == "in a list"]


out = []
rec: dict = {}

# ---------- A ----------
ch = {k: {c: [] for c in CONS} for k in ("fixed", "broken")}
ch_sym = {"fixed": [], "broken": []}
for run in links["chance_items"]:
    for k in ("fixed", "broken"):
        c = tag(run[k])
        for name in CONS:
            ch[k][name].append(c[name])
        ch_sym[k].append(len(symptom(run[k])))
out.append("A. Validation mentions each changed guideline fixed / broke, by construction")
out.append(f"   {'':14} " + "".join(f"{c:>28}" for c in CONS) + f"{'symptom in a list (M7, M8)':>30}")
out.append(f"   {'chance mean':<14} " + "".join(f"{statistics.mean(ch['fixed'][c]):>13.1f} / {statistics.mean(ch['broken'][c]):<12.1f}" for c in CONS)
           + f"{statistics.mean(ch_sym['fixed']):>15.1f} / {statistics.mean(ch_sym['broken']):<12.1f}")
out.append(f"   {'chance max':<14} " + "".join(f"{max(ch['fixed'][c]):>13} / {max(ch['broken'][c]):<12}" for c in CONS)
           + f"{max(ch_sym['fixed']):>15} / {max(ch_sym['broken']):<12}")
rec["chance"] = {k: {c: [statistics.mean(v), max(v)] for c, v in d.items()} for k, d in ch.items()}
rec["chance_symptom_list"] = {k: [statistics.mean(v), max(v)] for k, v in ch_sym.items()}
rec["chance_runs"] = {"history_broken": ch["broken"][CONS[1]],
                      "symptom_list_net": [f - b for f, b in zip(ch_sym["fixed"], ch_sym["broken"])]}
rec["guidelines"] = {}
for g, r in links["guidelines"].items():
    fx, br = tag(r["items"].get("fixed", [])), tag(r["items"].get("broken", []))
    sf, sb = len(symptom(r["items"].get("fixed", []))), len(symptom(r["items"].get("broken", [])))
    rec["guidelines"][g] = {"f1": r["f1"], "true_miss": r["true_miss"], "fp": r["fp"],
                            "by_construction": {c: [fx[c], br[c]] for c in CONS}, "symptom_list": [sf, sb]}
    out.append(f"   {g:<14} " + "".join(f"{fx[c]:>13} / {br[c]:<12}" for c in CONS) + f"{sf:>15} / {sb:<12}")
out.append("   cells: fixed / broken. Chance: one original run against the other 18 (rule_links.py), mean and max over the 19 runs.\n")

# ---------- B ----------
gold_dev = {}
for f in DEV:
    d = json.loads((DATA / "train" / f).read_text(encoding="utf-8"))
    gold_dev[f] = (d["text"], [(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d["denotations"]])
t196, g196 = gold_dev["10196379.json"]
h = re.search(r"history of ovarian cancer", t196).start() + len("history of ")
targets = {"history": [("10196379.json", h, h + len("ovarian cancer"))]}
t577, g577 = gold_dev["10577908.json"]
targets["symptom list"] = [("10577908.json", b, e) for b, e, lab in g577 if t577[b:e] in ("ichthyosis", "spasticity")]
targets["gene word"] = [(f, b, e) for f, (t, g) in gold_dev.items() for b, e, lab in g if lab == "Modifier" and AFTER_GENE.match(t[e:e + 40])]
labels = {(f, b, e): lab for f, (t, g) in gold_dev.items() for b, e, lab in g}

out.append("B. What the rewrite step saw, over all 44 rounds of the 20 loops")
shown = [re.findall(r"^FILE: (\S+)", p.read_text(encoding="utf-8").split("DO NOT BREAK")[-1], re.M)
         for p in OUT.glob("20261022_haiku-xhigh_topk*_loop*/rounds/iteration_*/refine_guidelines.txt")]
per_doc = Counter(f for s in shown for f in s)
out.append(f"   'do not break' documents per rewrite prompt: {dict(Counter(len(s) for s in shown))}; rounds showing each document: {dict(sorted(per_doc.items()))}")
# three channels, counted separately for each development gold mention x round: (1) the rewrite prompt's "do not break"
# list (the document shown, the label listed); (2) the analysis prompts' error examples, which carry the gold label;
# (3) whether the mention string appears in the round's moderation principles, which reach the rewrite prompt
seen = {name: Counter() for name in targets}
right_before = {name: Counter() for name in targets}
blocks = at_cap = 0
listed_196: Counter = Counter()
history_new_modifier = Counter()
kept_rounds = Counter()
hist_spans = [(b, e) for b, e, _ in g196 if re.search(r"history of\s+$", t196[max(0, b - 12):b])]
nrounds = 0
for folder in sorted(OUT.glob("20261022_haiku-xhigh_topk*_loop*")):
    for it in sorted((folder / "rounds").glob("iteration_*")):
        nrounds += 1
        snap = json.loads((it / "snapshot.json").read_text(encoding="utf-8"))
        block = (it / "refine_guidelines.txt").read_text(encoding="utf-8").split("DO NOT BREAK")[-1]
        files = dict(re.findall(r"^FILE: (\S+)\n(.*?)(?=^FILE: |\Z)", block, re.M | re.S))
        for body in files.values():  # iterative.py lists at most n_examples (5) matched annotations per document
            blocks += 1
            at_cap += len(re.findall(r"^- \w+ \[", body, re.M)) == 5
        listed_196[tuple(sorted(Counter(re.findall(r'^- (\w+ \[)\d+, \d+\] ("[^"]*")', files.get("10196379.json", ""), re.M)).items()))] += 1
        errs = "".join(p.read_text(encoding="utf-8") for p in it.glob("infer_discrepancy_patterns_*.txt"))
        before = {fd["filename"]: {(d["start"], d["end"]): d["label"] for d in fd["study_denotations"]} for fd in snap["diagnostics_before"]["files"]}
        for name, ms in targets.items():
            for f, b, e in ms:
                t = gold_dev[f][0]
                right_before[name][before.get(f, {}).get((b, e)) == labels[(f, b, e)]] += 1
                matched = f in files and re.search(rf"- \w+ \[{b}, {e}\]", files[f]) is not None
                ctx = re.escape(t[max(0, b - 25):b].split("\n")[-1][-15:])
                as_error = re.search(r'\(Doc: ' + re.escape(f) + r'\):\nSnippet: "[^"]*' + ctx + r'[^"]*"\nGold: \w+, LLM: \w+\nEntity Text: "' + re.escape(t[b:e]) + '"', errs) is not None
                c = seen[name]
                c["mention x round"] += 1
                c["rewrite: document shown"] += f in files
                c["rewrite: label listed"] += matched
                c["rewrite: document shown, label not listed"] += f in files and not matched
                c["analysis: error example with gold"] += as_error
                c["analysis: error example, and rewrite showed the document without the label"] += as_error and f in files and not matched
                c["analysis: error example, and rewrite did not show the document"] += as_error and f not in files
                # a string match only: it does not show whether a rule, its context or its label direction was passed on
                c["target string appears in the principles"] += t[b:e] in str(snap["moderation_principle"])
        cand = {(d["start"], d["end"]): d["label"] for fd in snap["diagnostics_candidate"]["files"] if fd["filename"] == "10196379.json" for d in fd["study_denotations"]}
        k = "kept" if snap["improved"] else "rejected"
        kept_rounds[k] += 1
        history_new_modifier[k] += any(cand.get(s) == "Modifier" and before["10196379.json"].get(s) != "Modifier" for s in hist_spans)
out.append(f"   document blocks listing exactly 5 matched annotations (the n_examples cap): {at_cap} of {blocks}")
out.append("   what the list showed for 10196379 (label, text: count), rounds: " + "; ".join(
    f"{v} x [{', '.join(f'{lab.rstrip(chr(91)).strip()} {txt}: {n}' for (lab, txt), n in k)}]" for k, v in listed_196.most_common()))
for name, ms in targets.items():
    labs = Counter(labels[m] for m in ms)
    out.append(f"   {name}: {len(ms)} development gold mention(s), gold {dict(labs)}; labeled right in the run before the rewrite: "
               f"{right_before[name][True]} of {sum(right_before[name].values())}")
    out.append("      " + "; ".join(f"{k} {v}" for k, v in seen[name].items()))
out.append(f"   candidates that newly label a mention after 'history of' (development document 10196379) Modifier: "
           f"kept rounds {history_new_modifier['kept']} of {kept_rounds['kept']}, rejected rounds {history_new_modifier['rejected']} of {kept_rounds['rejected']}")
out.append(f"   rounds: {nrounds}\n")
rec["seen"] = {k: dict(v) for k, v in seen.items()}

# ---------- C ----------
out.append("C. The label each final guideline gives, and the validation mentions of that construction it fixed / broke")
out.append(f"   {'guideline':<14} {'F1':>6} {'true miss':>9}  {'history rule':<26} {'history broken':>14}  {'symptom-list rule':<28} {'symptoms fixed/broken':>21}  {'gene word fixed':>15}")
rec["coded"] = {}
for g, r in links["guidelines"].items():
    guide = (FOLDER[g] / "final" / "final_guidelines.txt").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    cells = []
    for name, table in (("history", HISTORY), ("symptom list", SYMPTOM_LIST)):
        lab, line, phrase = table[g]
        if line:
            assert phrase in guide[line - 1], (g, name, line)
        cells.append(f"{lab}{f' (L{line})' if line else ''}")
    gg = rec["guidelines"][g]
    out.append(f"   {g:<14} {r['f1']:6.3f} {r['true_miss']:>9}  {cells[0]:<26} {gg['by_construction'][CONS[1]][1]:>14}  {cells[1]:<28} "
               f"{gg['symptom_list'][0]:>10} / {gg['symptom_list'][1]:<8}  {gg['by_construction'][CONS[0]][0]:>15}")
    rec["coded"][g] = {"history": HISTORY[g][:2], "symptom_list": SYMPTOM_LIST[g][:2]}
for name, table, col in (("history", HISTORY, lambda gg: gg["by_construction"][CONS[1]][1]),
                         ("symptom list", SYMPTOM_LIST, lambda gg: gg["symptom_list"][0] - gg["symptom_list"][1])):
    groups = {}
    for g, (lab, _, _) in table.items():
        key = "Modifier" if name == "history" and lab == "Modifier" else "DiseaseClass" if lab == "DiseaseClass" else "O" if lab.startswith("O") else "other"
        groups.setdefault(key, []).append(col(rec["guidelines"][g]))
    out.append(f"   {name}: " + "; ".join(f"{k} {len(v)} guidelines, mean {statistics.mean(v):+.1f}" for k, v in groups.items())
               + ("  (history: validation mentions broken)" if name == "history" else "  (symptom list: fixed minus broken)"))
out.append("")

# ---------- D ----------
train = [p for p in sorted((DATA / "train").glob("*.json")) if p.name not in TEST]
hist, lists = Counter(), Counter()
for p in train:
    d = json.loads(p.read_text(encoding="utf-8"))
    t = d["text"]
    dens = [(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d["denotations"]]
    for m in re.finditer(r"\bhistor(y|ies) of\s+", t):
        after = [x for x in dens if m.end() <= x[0] <= m.end() + 3]
        hist[after[0][2] if after else "not annotated"] += 1
    for m in re.finditer(r"characteri[sz]ed by\s+([^.;(]+)", t):
        pos = m.start(1)
        for item in re.split(r"(,\s*|\s+and\s+|\s+or\s+)", m.group(1)):
            b, e = pos, pos + len(item)
            pos = e
            if not item.strip() or re.fullmatch(r",\s*|\s+and\s+|\s+or\s+", item):
                continue
            b += len(item) - len(item.lstrip())
            e -= len(item) - len(item.rstrip())
            item = t[b:e]
            if len(item.split()) != 1:
                continue
            hit = [lab for (x, y, lab) in dens if x <= b and e <= y]
            lists[hit[0] if hit else "not annotated"] += 1
# ---------- E ----------
pat = json.loads((HERE / "error_patterns.json").read_text(encoding="utf-8"))
orig_runs = [r for r in pat["runs"] if r["guideline"] == "original"]
m1_mean = statistics.mean(r["counts"]["M1"] for r in orig_runs)
m = [json.loads((OUT / r["run"] / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"] for r in orig_runs]
tp, fp, fn = (statistics.mean(x[k] for x in m) for k in ("true_positives", "false_positives", "false_negatives"))
base = 2 * tp / (2 * tp + fp + fn)
out.append("E. Construction coverage: the share of each changed guideline's fixed + broken mentions that fall in the three"
           " constructions (before a gene word, after 'history of', symptoms in a list), and its net change in gene-name misses"
           " (pattern M1). A string match on the construction only; it does not check that the guideline has a rule for the"
           " mention or that the change follows the rule")
out.append(f"   M1 in the 19 original runs: mean {m1_mean:.1f}, range {min(r['counts']['M1'] for r in orig_runs)}-{max(r['counts']['M1'] for r in orig_runs)};"
           f" F1 effect of the net change at the original mean (TP {tp:.1f}, FP {fp:.1f}, FN {fn:.1f})")
rec["coverage"] = {}
for g, r in links["guidelines"].items():
    items = r["items"].get("fixed", []) + r["items"].get("broken", [])
    t = sum(1 for x in items if construction(vtext[x["doc"]], *x["span"]) in (CONS[0], CONS[1])) + len(symptom(items))
    run = next(x for x in pat["runs"] if x["guideline"] != "original" and f"{x['method']} {x['loop']}" == g)
    net = m1_mean - run["counts"]["M1"]
    gain = 2 * (tp + net) / (2 * (tp + net) + fp + fn - net) - base
    rec["coverage"][g] = {"in_constructions": t, "all": len(items), "m1": run["counts"]["M1"], "m1_net_reduction": net, "f1_effect": gain}
    out.append(f"   {g:<14} in the three constructions {t:>3} of {len(items):>3} ({t / len(items):.0%});  M1 {run['counts']['M1']:>3}, "
               f"net reduction {net:+6.1f}, F1 effect {gain:+.4f}")
out.append("")

out.append(f"D. Training gold, {len(train)} documents (593 minus the 50 test documents)")
out.append(f"   disease mention right after 'history of': {dict(hist.most_common())}")
out.append(f"   single-word items of a 'characterized by' list: {dict(lists.most_common())}")
rec["training"] = {"history": dict(hist), "characterized_by_single_word_items": dict(lists)}

(HERE / "rule_chain.json").write_bytes((json.dumps(rec, indent=1) + "\n").encode("utf-8"))
(HERE / "rule_chain_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
