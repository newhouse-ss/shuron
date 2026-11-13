"""Does the training gold follow the same conventions as the validation gold, for the constructions behind the main error patterns?

Offline, no API calls. Training documents only, minus the 50 test documents
(reproduction/test_splits/ncbi_disease_heldout50.json). For each construction, every occurrence in the
training text is looked up in the training gold: an exact gold mention (with its label), a gold mention
that covers it as part of a longer one, or nothing. Writes gold_precedent_output.txt.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
TEST = set(json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))["documents"])

from patterns_lib import AFTER_GENE  # noqa: E402

docs = []
doc_ids = []
for p in sorted(TRAIN.glob("*.json")):
    if p.name in TEST:
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    doc_ids.append(p.stem)
    docs.append((d["text"], [(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d.get("denotations", [])]))


def status(dens, b: int, e: int) -> str:
    exact = [lab for (x, y, lab) in dens if (x, y) == (b, e)]
    if exact:
        return exact[0]
    if any(x <= b and e <= y for (x, y, _) in dens):
        return "part of a longer mention"
    if any(x < e and b < y for (x, y, _) in dens):
        return "other overlapping span"
    return "not annotated"


def survey(regex: re.Pattern, group: int = 0, followed_by: re.Pattern | None = None) -> Counter:
    c: Counter = Counter()
    for text, dens in docs:
        for m in regex.finditer(text):
            if followed_by and not followed_by.match(text[m.end(group):m.end(group) + 40]):
                continue
            c[status(dens, m.start(group), m.end(group))] += 1
    return c


def fmt(c: Counter) -> str:
    n = sum(c.values())
    return f"n={n}: " + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in c.most_common()) if n else "n=0"


out = [f"training documents: {len(docs)} (593 minus the 50 test documents)\n"]

results: dict = {"constructions": {}, "qualifiers": {}}

# M1: a disease name directly before a gene or protein word, by the same rule as pattern M1 (patterns_lib.AFTER_GENE).
# Disease names: every string the training gold annotates.
vocab = sorted({text[b:e] for text, dens in docs for (b, e, _) in dens if len(text[b:e].strip()) >= 2}
               - {"cancer", "tumor", "tumour", "Cancer", "Tumor", "Tumour"}, key=len, reverse=True)
names = re.compile(r"(?<![\w-])(" + "|".join(re.escape(v) for v in vocab) + r")(?![\w-])")
out.append("M1  disease name directly before a gene or protein word (same rule as pattern M1, e.g. 'VHL gene'); validation gold: Modifier")
results["constructions"]["M1"] = survey(names, 1, AFTER_GENE)
out.append("    " + fmt(results["constructions"]["M1"]))

out.append("M2  tumor / cancer before a non-disease noun (tumor suppressor, tumor cells); validation gold: Modifier")
results["constructions"]["M2"] = survey(re.compile(r"(?<![\w-])(tumou?rs?|cancers?|Tumou?r|Cancer)(?=\s+(suppressor|suppression|cells?|types?|DNA|formation|site|foci|susceptibility|growth|samples?|tissues?|lines?)\b)"), 1)
out.append("    " + fmt(results["constructions"]["M2"]))

out.append("M3  X-deficient (Atm-deficient mice); validation gold: Modifier")
results["constructions"]["M3"] = survey(re.compile(r"(?<![\w-])([\w]+-deficient)\b"), 1)
out.append("    " + fmt(results["constructions"]["M3"]))

out.append("M7  qualifier + general word (genetic disorder, eye abnormalities); validation gold: DiseaseClass")
results["constructions"]["M7"] = survey(re.compile(
    r"(?<![\w-])((genetic|inherited|hereditary|developmental|behaviou?ral|immune|eye|brain|cellular|chromosom(e|al)|neurological|"
    r"neurodegenerative|metabolic|congenital|skeletal|neuromuscular|recessive|dominant|X-linked|human|autoimmune)\s+"
    r"(diseases?|disorders?|abnormalit(y|ies)|defects?|conditions?|anomal(y|ies)|manifestations?))\b", re.I), 1)
out.append("    " + fmt(results["constructions"]["M7"]))

# M8: the symptom and sign strings that the original guideline's runs miss on validation
items = list(csv.DictReader((HERE / "error_items_patterns.csv").open(encoding="utf-8")))
symptoms = sorted({x["gold_text"].strip() for x in items if x["pattern"] == "M8" and int(x["original_of19"]) >= 10
                   and not re.search(r"[A-Z]{2,}", x["gold_text"])})
c = Counter()
for s in symptoms:
    c += survey(re.compile(r"(?<![\w-])(" + re.escape(s) + r")(?![\w-])", re.I), 1)
out.append(f"M8  the {len(symptoms)} symptom / sign strings missed in >=10 of 19 runs ({', '.join(symptoms[:8])}, ...); validation gold: DiseaseClass or SpecificDisease")
out.append("    " + fmt(c))

# L1: coordinated disease names right before a noun they modify (breast and ovarian cancer families). The 10/24
# version counted any following word outside a short stop list as a noun, so verbs ("cancers harbour") were counted.
# Now only a fixed list of the nouns such a mention modifies counts; the other following words are printed.
HEAD_NOUN = re.compile(r"\s*(families|family|kindreds?|pedigrees?|patients?|cases?|probands?|carriers?|individuals|members|"
                       r"relatives|women|men|children|subjects|populations?|cohorts?|genes?|loci|locus|mutations?|"
                       r"susceptibility|predisposition|risks?|syndromes?|cells?|lines?)\b", re.I)
out.append("L1  gold mentions with 'and' / 'or' / '/', by what follows; validation gold: Modifier when a noun it modifies follows")
by_next: dict[str, Counter] = {"a person, family, gene or risk noun follows": Counter(), "another word follows": Counter(),
                               "nothing, or a function word, follows": Counter()}
other_words: Counter = Counter()
for text, dens in docs:
    for (b, e, lab) in dens:
        if re.search(r"\s(and|or)\s|/", text[b:e]):
            nxt = re.match(r"\s*([A-Za-z][\w-]*)", text[e:e + 30])
            if HEAD_NOUN.match(text[e:e + 30]):
                key = "a person, family, gene or risk noun follows"
            elif nxt and nxt.group(1).lower() not in {"and", "or", "in", "of", "with", "is", "are", "was", "were"}:
                key = "another word follows"
                other_words[nxt.group(1).lower()] += 1
            else:
                key = "nothing, or a function word, follows"
            by_next[key][lab] += 1
for k, v in by_next.items():
    out.append(f"    {k}: {fmt(v)}")
out.append(f"    words in 'another word follows': {dict(other_words.most_common())}")
results["constructions"]["L1"] = by_next["a person, family, gene or risk noun follows"]
results["L1_other_words"] = dict(other_words)

# B1 / B2: is the qualifier inside the gold span?
out.append("B1/B2 qualifier before a disease name: does the training gold include it? (counted where a gold mention starts at the qualifier or right after it)")
qualifier_examples: dict = {}
for q in ("familial", "sporadic", "inherited", "hereditary", "primary", "classical", "classic", "simple", "attenuated", "childhood", "early-onset", "severe", "mild"):
    inc = exc = 0
    pat = re.compile(r"(?<![\w-])" + q + r"\s+", re.I)
    for doc, (text, dens) in zip(doc_ids, docs):
        starts = {b for (b, _, _) in dens}
        ends = {b: e for (b, e, _) in dens}
        for m in pat.finditer(text):
            if m.start() in starts:
                inc += 1
                qualifier_examples.setdefault(q, []).append((doc, "included", text[m.start():ends[m.start()]]))
            elif m.end() in starts:
                exc += 1
                qualifier_examples.setdefault(q, []).append((doc, "left out", f"{m.group(0).strip()} [{text[m.end():ends[m.end()]]}]"))
    if inc + exc:
        results["qualifiers"][q] = [inc, exc]
        out.append(f"    {q:<12} included {inc:3}, left out {exc:3}  ({inc / (inc + exc):.0%} included)")

# L5 / L6: the label the training gold gives the same strings
for pat_id, want, desc in (("L5", "SpecificDisease", "Specific in validation gold, predicted DiseaseClass"),
                           ("L6", "DiseaseClass", "DiseaseClass in validation gold, predicted Specific")):
    strings = sorted({x["gold_text"].strip() for x in items if x["pattern"] == pat_id and int(x["original_of19"]) >= 5})
    c = Counter()
    for s in strings:
        c += survey(re.compile(r"(?<![\w-])(" + re.escape(s) + r")(?![\w-])"), 1)
    results["constructions"][pat_id] = c
    out.append(f"{pat_id}  the {len(strings)} strings {desc} in >=5 of 19 runs; labels in the training gold")
    out.append("    " + fmt(c))

# strings in the original guideline's own examples that the example does not annotate
out.append("Strings from the original guideline's examples that the example leaves unannotated: training gold")
results["guideline_examples"] = {}
for s, where in (("short stature", "Example under What to Annotate 1: the annotations listed omit it"),
                 ("infectious complications", "Example 6: 'too general a term'")):
    results["guideline_examples"][s] = survey(re.compile(r"(?<![\w-])(" + re.escape(s) + r")(?![\w-])", re.I), 1)
    out.append(f"   '{s}' ({where}): " + fmt(results["guideline_examples"][s]))

# 10/26: the size of the training gold, and every sporadic / classical occurrence counted under B1/B2
results["train_gold_mentions"] = sum(len(dens) for _, dens in docs)
out.append(f"Training gold mentions in the {len(docs)} documents: {results['train_gold_mentions']}")
out.append("B1/B2 examples for sporadic and classical (document, included or left out, gold span in brackets when left out)")
results["qualifier_examples"] = {q: qualifier_examples[q] for q in ("sporadic", "classical")}
for q, items in results["qualifier_examples"].items():
    for doc, kind, s in sorted(items, key=lambda t: (t[1], t[0])):
        out.append(f"    {q:<10} {kind:<9} {doc:<9} {s!r}")

(HERE / "gold_precedent.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
(HERE / "gold_precedent_output.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
