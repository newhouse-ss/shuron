"""Specific labelled DiseaseClass, and DiseaseClass missed: which clauses, written in which rounds (11/03).

Offline, no API calls. Inputs: error_rows.csv through pilot_cases.py (state of every validation gold mention in the 30
runs), loop_label_tables.json (per-label changes and original-range flags), 20261030_rationale_audit/prediction_index.jsonl
(every saved validation prediction with its exact reply, rationale and cited section), the final guidelines, the round
snapshots, training gold minus the 50 test documents (filtered by file name before any file is read), and the hand coding
outputs/loop05_dc_missed_coding.csv.

A. Patterns: which of five label-level changes each changed guideline shows outside the original range.
B. Specific gold labelled DiseaseClass. The change of a guideline against the original mean is split exactly over mentions:
   each mention adds 1[guideline labels it DiseaseClass] minus the share of the 19 original runs that do. For top-1 loop05
   and top-4 loop06 the split is by the clause the annotator cites (earliest cited section) and by head word; then what the
   same clauses fixed; then, for all guidelines, Specific mentions ending in a tumour word labelled DiseaseClass, beside each
   guideline's clause on site words; then the gold convention for such names in training and development gold.
C. top-4 loop05, DiseaseClass gold missed: the change split by how often the original runs label the mention right; the
   mentions right in at least 15 of 19 original runs and missed by loop05, with the hand coding against loop05's clauses.
D. Rounds of top-1 loop05, top-4 loop06 and top-4 loop05: target clusters and the examples the analysis step saw, the round
   in which each key clause first appears and whether that round's principle already states it, the development mentions
   whose state changed, and whether the round was kept.
E. All 11 changed guidelines: the two development clusters (Specific labelled DiseaseClass, DiseaseClass missed) at the loop
   start and in the final guideline, beside the validation change of the same error.
F. Checks: every guideline line quoted in the report contains the quoted words.
Writes dc_loss_clauses_output.txt and dc_loss_clauses.json.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import re
import runpy
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(HERE / "pilot_cases.py"))
texts, gold, state, runs, orig, mod, name = (g[k] for k in ("texts", "gold", "state", "runs", "orig", "mod", "name"))
ROOT = HERE.parents[2]
OUT = HERE.parent / "outputs"
RUNS = ROOT / "outputs" / "ncbi_disease"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
TEST = set(json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))["documents"])
by = {name[x]: x for x in mod}
cols = sorted(mod, key=lambda x: name[x])
FOLDER = {n: RUNS / f"20261022_haiku-xhigh_{'topk1' if n.startswith('top-1') else 'topk4'}_loop{n[-2:]}" for n in by}


def st(x, k):
    s = state[x].get(k)
    return "right" if not s else (f"label->{s[2]}" if s[0] == "label" else s[0])


def lines(n):
    return (FOLDER[n] / "final" / "final_guidelines.txt").read_text(encoding="utf-8").splitlines()


def p_orig(k, s):
    return sum(st(x, k) == s for x in orig) / len(orig)


def right_orig(k):
    return sum(st(x, k) == "right" for x in orig)


pidx = defaultdict(list)
for line in (OUT / "20261030_rationale_audit" / "prediction_index.jsonl").open(encoding="utf-8"):
    r = json.loads(line)
    pidx[(r["run"], r["doc"])].append(r)


def pred_for(x, k, label):
    """The saved prediction with this label that overlaps the gold span most (the one the scorer paired)."""
    ov = [(min(int(r["end"]), k[2]) - max(int(r["start"]), k[1]), r) for r in pidx[(x, k[0])] if r["pred_label"] == label]
    ov = [o for o in ov if o[0] > 0]
    return max(ov, key=lambda o: o[0])[1] if ov else None


TUMOUR = re.compile(r"(cancers?|carcinomas?|tumou?rs?|neoplasms?|lymphomas?|sarcomas?|hamartomas?|adenomas?|melanomas?|gliomas?|"
                    r"leuka?emias?|blastomas?)$", re.I)


def tumour(txt):
    return TUMOUR.search(txt.strip()) is not None


# cited-clause groups (earliest match in the cited section wins); line numbers are of final/final_guidelines.txt
CLAUSES = {
    "top-1 loop05": [("1.2(b) generic category (L61)", r"1\.2\s*\(b\)|constraint \(?b\b|generic category"),
                     ("1.2(a) or (e) trait, umbrella, unframed list (L60, L64)", r"1\.2\s*\((a|e)\)|constraint \(?(a|e)\b|unframed list|umbrella"),
                     ("1.2, other parts (L46-L57)", r"1\.2"),
                     ("Section 1 only or other", r".")],
    "top-4 loop06": [("1.4 head-driven condition labeling (L93)", r"\b1\.4\b|head-driven"),
                     ("1.1 or 1.5: site, plural, inheritance qualifiers (L29, L35, L117, L119)", r"\b1\.1\b|\b1\.5\b"),
                     ("1.3 characterizing signs (L76)", r"\b1\.3\b"),
                     ("Section 1 only or other", r".")],
}


def clause(n, sec):
    best = None
    for tag, pat in CLAUSES[n]:
        m = re.search(pat, sec or "", re.I)
        if m and (best is None or m.start() < best[0]) and tag != "Section 1 only or other":
            best = (m.start(), tag)
    return best[1] if best else "Section 1 only or other"


out, rec = [], {}

# ---------- A ----------
lt = json.loads((OUT / "loop_label_tables.json").read_text(encoding="utf-8"))["by_label"]
PAT = [("Modifier right above range", lambda b: b["Modifier"]["tp_out"] and b["Modifier"]["tp"] > 0),
       ("Modifier wrong above range", lambda b: b["Modifier"]["fp_out"] and b["Modifier"]["fp"] > 0),
       ("Specific right below range", lambda b: b["SpecificDisease"]["tp_out"] and b["SpecificDisease"]["tp"] < 0),
       ("DiseaseClass wrong above range", lambda b: b["DiseaseClass"]["fp_out"] and b["DiseaseClass"]["fp"] > 0),
       ("DiseaseClass right below range", lambda b: b["DiseaseClass"]["tp_out"] and b["DiseaseClass"]["tp"] < 0)]
out.append("A. Label-level changes outside the 19 original runs' range (loop_label_tables.json); in brackets where the lost or wrong"
           " mentions mainly went")
rec["patterns"] = {}
for n in sorted(lt, key=lambda n: -lt[n]["f1"]):
    b = lt[n]
    hits = []
    for tag, f in PAT:
        if f(b):
            lab = tag.split()[0].replace("Specific", "SpecificDisease")
            top = b[lab]["fp_top" if "wrong" in tag else "tp_top"]
            hits.append(f"{tag} ({top[0]} {top[1]:+.1f})")
    rec["patterns"][n] = [h.split(" (")[0] for h in hits]
    out.append(f"   {n:<14} F1 {b['f1']:.4f}: " + ("; ".join(hits) if hits else "none"))

# ---------- B ----------
spec = [k for k in gold if k[3] == "SpecificDisease"]
out.append("\nB. Specific gold labelled DiseaseClass: count per run, original mean (min-max), each changed guideline's count and change")
o = [sum(st(x, k) == "label->DiseaseClass" for k in spec) for x in orig]
om = statistics.mean(o)
out.append(f"   original {om:.1f} ({min(o)}-{max(o)}); " + ", ".join(
    f"{name[x]} {sum(st(x, k) == 'label->DiseaseClass' for k in spec)} ({sum(st(x, k) == 'label->DiseaseClass' for k in spec) - om:+.1f})" for x in cols))
rec["spec_to_dc"] = {"orig_mean": om, "orig_range": [min(o), max(o)],
                     "count": {name[x]: sum(st(x, k) == "label->DiseaseClass" for k in spec) for x in cols}}

for n in ("top-1 loop05", "top-4 loop06"):
    x = by[n]
    on = [k for k in spec if st(x, k) == "label->DiseaseClass"]
    off = [k for k in spec if st(x, k) != "label->DiseaseClass"]
    total = sum(1 - p_orig(k, "label->DiseaseClass") for k in on) - sum(p_orig(k, "label->DiseaseClass") for k in off)
    out.append(f"\n   B.{n}: change {total:+.1f} = labelled DiseaseClass by {n} ({len(on)} mentions, each adds 1 minus the original"
               f" share) {sum(1 - p_orig(k, 'label->DiseaseClass') for k in on):+.1f}, plus mentions the original labels so and {n}"
               f" does not {-sum(p_orig(k, 'label->DiseaseClass') for k in off):+.1f}")
    grp = defaultdict(lambda: [0, 0.0, 0, 0.0])   # mentions, contribution; of which tumour word: mentions, contribution
    cells = []
    for k in on:
        r = pred_for(x, k, "DiseaseClass")
        c = clause(n, r["cited_section"] if r else "")
        add = 1 - p_orig(k, "label->DiseaseClass")
        grp[c][0] += 1
        grp[c][1] += add
        if tumour(texts[k[0]][k[1]:k[2]]):
            grp[c][2] += 1
            grp[c][3] += add
        cells.append({"doc": k[0], "start": k[1], "end": k[2], "text": texts[k[0]][k[1]:k[2]], "orig_right": right_orig(k),
                      "orig_dc": round(p_orig(k, "label->DiseaseClass") * 19), "clause": c,
                      "cited": r["cited_section"] if r else None, "rationale": r["raw_rationale"] if r else None})
    out.append(f"   {'cited clause (earliest cited section)':<72} mentions  change | ending in a tumour word: mentions  change")
    for c, v in sorted(grp.items(), key=lambda kv: -kv[1][1]):
        out.append(f"   {c:<72} {v[0]:8} {v[1]:+7.1f} | {v[2]:30} {v[3]:+7.1f}")
    nt = [k for k in on if tumour(texts[k[0]][k[1]:k[2]])]
    new = [k for k in on if right_orig(k) >= 15]
    out.append(f"   ending in a tumour word: {len(nt)} of {len(on)} mentions, change {sum(1 - p_orig(k, 'label->DiseaseClass') for k in nt):+.1f};"
               f" right in >=15 of 19 original runs: {len(new)}, of which ending in a tumour word {sum(tumour(texts[k[0]][k[1]:k[2]]) for k in new)}")
    out.append("   right in >=15 of 19 original runs, now DiseaseClass: " + "; ".join(
        f"{k[0]} {texts[k[0]][k[1]:k[2]]!r}" for k in new))
    # the same clauses on the fixed side: DiseaseClass gold now right where the original was right <=4 of 19
    fixed = [k for k in gold if k[3] == "DiseaseClass" and st(x, k) == "right" and right_orig(k) <= 4]
    fc = Counter()
    for k in fixed:
        r = pred_for(x, k, "DiseaseClass")
        fc[clause(n, r["cited_section"] if r else "")] += 1
    broken = Counter(clause(n, (pred_for(x, k, "DiseaseClass") or {}).get("cited_section", "")) for k in new)
    extra = Counter(clause(n, r["cited_section"]) for (rx, _), rs in pidx.items() if rx == x for r in rs
                    if r["pred_label"] == "DiseaseClass" and r["kind"] == "extra")
    xo = statistics.mean(sum(1 for (rx, _), rs in pidx.items() if rx == y for r in rs if r["pred_label"] == "DiseaseClass"
                             and r["kind"] == "extra") for y in orig)
    out.append(f"   same clauses, both sides: DiseaseClass gold fixed (original right <=4 of 19, now right) {len(fixed)}; Specific gold"
               f" broken (original right >=15 of 19, now DiseaseClass) {len(new)}; extra DiseaseClass predictions with no gold"
               f" {sum(extra.values())} (original mean {xo:.1f})")
    for c in [t for t, _ in CLAUSES[n]]:
        out.append(f"      {c:<72} fixed DiseaseClass {fc[c]:3}  broken Specific {broken[c]:3}  extra {extra[c]:3}")
    rec[f"spec_to_dc_{n}"] = {"change": total, "groups": {c: v for c, v in grp.items()}, "mentions": cells,
                             "fixed_dc_by_clause": dict(fc), "broken_spec_by_clause": dict(broken), "extra_by_clause": dict(extra),
                             "extra_orig_mean": xo}

# every guideline: Specific mentions ending in a tumour word labelled DiseaseClass, and its clause on site words
SITE = {  # guideline -> (direction, line numbers, words checked in F)
    "top-1 loop05": ("site word does not make it Specific", "L46, L52, L61"),
    "top-4 loop06": ("site word does not make it Specific", "L29, L35"),
    "top-4 loop01": ("site word makes it Specific", "L21"),
    "top-4 loop02": ("site word makes it Specific", "L58"),
    "top-4 loop09": ("site word makes it Specific", "L25"),
    "top-4 loop10": ("site word makes it Specific", "L66"),
}
st_ = [k for k in spec if tumour(texts[k[0]][k[1]:k[2]])]
o = [sum(st(x, k) == "label->DiseaseClass" for k in st_) for x in orig]
out.append(f"\n   Specific gold ending in a tumour word ({len(st_)} mentions): labelled DiseaseClass, original {statistics.mean(o):.1f}"
           f" ({min(o)}-{max(o)}); per changed guideline, with its clause on site words before a disease head")
rec["tumour_spec_to_dc"] = {"n": len(st_), "orig_mean": statistics.mean(o), "orig_range": [min(o), max(o)], "by_guideline": {}}
for x in sorted(cols, key=lambda x: -sum(st(x, k) == "label->DiseaseClass" for k in st_)):
    c = sum(st(x, k) == "label->DiseaseClass" for k in st_)
    d, ln = SITE.get(name[x], ("not stated", ""))
    out.append(f"      {name[x]:<14} {c:3} ({c - statistics.mean(o):+5.1f})  {d} {ln}")
    rec["tumour_spec_to_dc"]["by_guideline"][name[x]] = {"count": c, "clause": d, "lines": ln}

# gold convention: names ending in a tumour word, two or more tokens
lab_tr = Counter()
for p in sorted(TRAIN.glob("*.json")):
    if p.name in TEST:
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    for a in d.get("denotations", []):
        t = d["text"][a["span"]["begin"]:a["span"]["end"]]
        if tumour(t) and len(t.split()) >= 2:
            lab_tr[a["obj"]] += 1
lab_va = Counter(k[3] for k in gold if tumour(texts[k[0]][k[1]:k[2]]) and len(texts[k[0]][k[1]:k[2]].split()) >= 2)
dev_docs = [d["filename"] for d in json.loads((FOLDER["top-1 loop05"] / "inputs" / "sampled_train_documents.json").read_text(encoding="utf-8"))]
dev_t = []
for f in dev_docs:
    d = json.loads((TRAIN / f).read_text(encoding="utf-8"))
    for a in d["denotations"]:
        t = d["text"][a["span"]["begin"]:a["span"]["end"]]
        if tumour(t) and a["obj"] in ("SpecificDisease", "DiseaseClass"):
            dev_t.append((f, t, a["obj"], d["text"][max(0, a["span"]["begin"] - 30):a["span"]["begin"]]))
out.append(f"   gold labels of names of two or more tokens ending in a tumour word: training (543 documents, test excluded) {dict(lab_tr)};"
           f" validation {dict(lab_va)}")
out.append(f"   development documents (the same 10 in every loop): Specific or DiseaseClass gold ending in a tumour word: "
           + "; ".join(f"{f} {t!r} {lab} after '...{pre}'" for f, t, lab, pre in dev_t).replace("\n", " "))
rec["tumour_gold_convention"] = {"training": dict(lab_tr), "validation": dict(lab_va), "development": dev_t}

# ---------- C ----------
x5 = by["top-4 loop05"]
dcg = [k for k in gold if k[3] == "DiseaseClass"]
o = [sum(st(x, k) == "missed" for k in dcg) for x in orig]
om = statistics.mean(o)
miss = [k for k in dcg if st(x5, k) == "missed"]
out.append(f"\nC. top-4 loop05, DiseaseClass gold missed: original {om:.1f} ({min(o)}-{max(o)}), loop05 {len(miss)} ({len(miss) - om:+.1f});"
           " the change split by how many of the 19 original runs label the mention right")
for lo, hi in ((15, 19), (5, 14), (0, 4)):
    on = [k for k in miss if lo <= right_orig(k) <= hi]
    offk = [k for k in dcg if st(x5, k) != "missed" and lo <= right_orig(k) <= hi]
    ch = sum(1 - p_orig(k, "missed") for k in on) - sum(p_orig(k, "missed") for k in offk)
    out.append(f"   right in {lo}-{hi} of 19: missed by loop05 {len(on):3}; contribution to the change {ch:+6.1f}")
new5 = [k for k in miss if right_orig(k) >= 15]
coding = {(r["doc"], int(r["start"]), int(r["end"])): r for r in csv.DictReader((OUT / "loop05_dc_missed_coding.csv").open(encoding="utf-8"))}
assert set(coding) == {(k[0], k[1], k[2]) for k in new5}, "the coding must cover exactly the listed mentions"
for k in new5:
    assert coding[(k[0], k[1], k[2])]["text"] == texts[k[0]][k[1]:k[2]]
x10 = by["top-4 loop10"]
out.append(f"   right in >=15 of 19 original runs and missed by loop05: {len(new5)}; from document 9083764:"
           f" {sum(k[0] == '9083764' for k in new5)}; also missed by top-4 loop10: {sum(st(x10, k) == 'missed' for k in new5)}")
cc = Counter(coding[(k[0], k[1], k[2])]["relation"] for k in new5)
out.append("   hand coding against loop05's clauses (loop05_dc_missed_coding.csv): " + ", ".join(f"{a} {b}" for a, b in cc.most_common()))
for k in new5:
    c = coding[(k[0], k[1], k[2])]
    out.append(f"      {k[0]}:{k[1]} {c['text']!r:<36} {c['relation']:<26} {c['lines']:<14} {c['note']}")
rec["loop05_dc_missed"] = {"orig_mean": om, "orig_range": [min(o), max(o)], "count": len(miss), "new": len(new5),
                           "relations": dict(cc), "also_loop10": sum(st(x10, k) == "missed" for k in new5)}

# ---------- D ----------
KEY = {  # loop -> [(clause, final-guideline line, distinctive words)]
    "top-1 loop05": [("descriptive pathology terms are Specific only with a patient-level predicate or a single etiology", 46,
                      "even when its form is generic or category-like, if either of the following holds"),
                     ("generic category remains Disease Class", 61, "**(b) Generic category.**")],
    "top-4 loop06": [("site and inheritance qualifiers do not individuate a disorder-family head", 29,
                      "**Inheritance-pattern and anatomical-site qualifiers**"),
                     ("head-driven condition labeling: pathological-state heads are Disease Class", 93,
                      "IF the head noun of a noun phrase denotes a pathological state or disorder"),
                     ("plurals and sets are not subtype-restricted Specific", 117, "(c) The phrase denotes a family or set")],
    "top-4 loop05": [("physical signs and symptoms in feature lists remain unlabelled", 46, "(f) the span is a physical sign, symptom"),
                     ("signs and symptoms in feature lists are not annotated", 156, "**Do not annotate physical signs and symptoms in feature lists**"),
                     ("bare cancer in cohort or family-history descriptors is not annotated", 160,
                      "used to label a study population or a family history")],
}
PRINCIPLE_WORDS = {  # words showing that the round's principle (analysis step) already states the clause's direction
    "top-1 loop05": {46: "with or without a site, organism, or etiology modifier", 61: "used generically for a category of disorders"},
    "top-4 loop06": {29: "anatomical-site", 93: "Head-Driven Condition Labeling", 117: "plural"},
    "top-4 loop05": {46: "physical sign", 156: "physical sign", 160: "family history"},
}


def dev_states(diag):
    res = {}
    for f in diag["files"]:
        preds = f["study_denotations"]
        for gd in f["reference_denotations"]:
            key = (f["filename"].replace(".json", ""), gd["start"], gd["end"], gd["label"], gd["text"])
            same = [p for p in preds if (p["start"], p["end"]) == (gd["start"], gd["end"])]
            if same:
                res[key] = "right" if same[0]["label"] == gd["label"] else "as " + same[0]["label"]
            else:
                ov = [p for p in preds if min(p["end"], gd["end"]) > max(p["start"], gd["start"])]
                res[key] = f"overlap {ov[0]['label']} {ov[0]['text']!r}" if ov else "missed"
    return res


out.append("\nD. Rounds of the three loops: targets (dev count before -> with the candidate) and the examples shown to the analysis"
           " step; where each key clause first appears; development mentions whose state changed")
rec["rounds"] = {}
for n in ("top-1 loop05", "top-4 loop06", "top-4 loop05"):
    k_ = 1 if n.startswith("top-1") else 4
    final = (FOLDER[n] / "final" / "final_guidelines.txt").read_text(encoding="utf-8")
    fl = final.splitlines()
    for _, ln, words in KEY[n]:
        assert words in fl[ln - 1], (n, ln, words)
    out.append(f"   {n}")
    rr = []
    for snap in sorted((FOLDER[n] / "rounds").glob("iteration_*/snapshot.json")):
        s = json.loads(snap.read_text(encoding="utf-8"))
        b, c = s["summary_before"], s["summary_candidate"]
        cand = {cl["key"]: cl["count"] for cl in c["all_clusters"]}
        out.append(f"      round {s['iteration']}: {'kept' if s['improved'] else 'rejected'}, dev F1 {b['overall_f1']:.3f} -> {c['overall_f1']:.3f}")
        for cl in b["all_clusters"][:k_]:
            ex = Counter(e["entity_text"] for e in cl["examples"])
            docs = sorted({e["doc_id"].replace(".json", "") for e in cl["examples"]})
            out.append(f"         target {cl['key']} {cl['count']} -> {cand.get(cl['key'], 0)}; examples {dict(ex)} from {docs}")
        first = [(cl_, ln) for cl_, ln, words in KEY[n] if words not in s["guidelines_before"] and words in s["guidelines_candidate"]]
        for cl_, ln in first:
            pw = PRINCIPLE_WORDS[n][ln]
            out.append(f"         first written here: final L{ln} ({cl_}); principle of this round contains {pw!r}: {pw in s['moderation_principle']}")
        b_, c_ = dev_states(s["diagnostics_before"]), dev_states(s["diagnostics_candidate"])
        ch = [(kk, b_[kk], c_[kk]) for kk in sorted(b_) if b_[kk] != c_[kk]]
        for kk, x_, y_ in ch:
            out.append(f"         dev {kk[0]} {kk[4]!r} gold {kk[3]}: {x_} -> {y_}")
        rr.append({"round": s["iteration"], "kept": s["improved"], "first_written": [ln for _, ln in first],
                   "dev_changes": [[kk[0], kk[4], kk[3], x_, y_] for kk, x_, y_ in ch]})
    rec["rounds"][n] = rr
    out.append(f"      final guideline = last kept candidate: "
               f"{final.strip() == json.loads(sorted((FOLDER[n] / 'rounds').glob('iteration_*/snapshot.json'))[-1].read_text(encoding='utf-8'))['guidelines_before'].strip() or 'see snapshots'}")

# ---------- E ----------
CL = {"Specific labelled DiseaseClass": ("Gold: SpecificDisease vs LLM: DiseaseClass (Label Mismatch)", "SpecificDisease", "label->DiseaseClass"),
      "DiseaseClass missed": ("Gold: DiseaseClass vs LLM: O (Missed)", "DiseaseClass", "missed")}
start = {}
for m, kk in (("top-1", "topk1"), ("top-4", "topk4")):
    for i in range(1, 11):
        s = json.loads((RUNS / f"20261022_haiku-xhigh_{kk}_loop{i:02d}" / "rounds" / "iteration_01" / "snapshot.json").read_text(encoding="utf-8"))
        start[(m, i)] = {cl["key"]: cl["count"] for cl in s["summary_before"]["all_clusters"]}
out.append("\nE. Development cluster at loop start -> final guideline (the loop's own clusters), beside the validation change of the"
           " same error (guideline minus the 19-run original mean); original development range over the 20 loop starts")
rec["dev_vs_valid"] = {}
for tag, (key, lab, sv) in CL.items():
    dv = [start[s_].get(key, 0) for s_ in start]
    vo = [sum(st(x, k) == sv for k in gold if k[3] == lab) for x in orig]
    out.append(f"   {tag}: development, original guideline at the 20 loop starts {min(dv)}-{max(dv)}; validation original"
               f" {statistics.mean(vo):.1f} ({min(vo)}-{max(vo)})")
    rows = []
    for x in cols:
        n = name[x]
        snaps = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FOLDER[n] / "rounds").glob("iteration_*/snapshot.json"))]
        kept = [s for s in snaps if s["improved"]]
        fin = {cl["key"]: cl["count"] for cl in kept[-1]["summary_candidate"]["all_clusters"]}
        st0 = {cl["key"]: cl["count"] for cl in snaps[0]["summary_before"]["all_clusters"]}
        targeted = [s["iteration"] for s in kept if key in [cl["key"] for cl in s["summary_before"]["all_clusters"][:(1 if n.startswith("top-1") else 4)]]]
        vc = sum(st(x, k) == sv for k in gold if k[3] == lab) - statistics.mean(vo)
        rows.append((n, st0.get(key, 0), fin.get(key, 0), targeted, vc))
    for n, a, b_, t, vc in sorted(rows, key=lambda r: r[4]):
        out.append(f"      {n:<14} dev {a} -> {b_}   kept rounds targeting it {t}   validation {vc:+6.1f}")
    rec["dev_vs_valid"][tag] = {"dev_original_range": [min(dv), max(dv)], "rows": rows}
    # every round (44, kept or not) that targeted this cluster: which development documents its examples came from
    ex_docs, n_r = Counter(), 0
    for p in sorted(RUNS.glob("20261022_haiku-xhigh_topk*_loop*/rounds/iteration_*/snapshot.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        for cl in s["summary_before"]["all_clusters"][:(1 if "topk1" in p.parts[-4] else 4)]:
            if cl["key"] == key:
                n_r += 1
                ex_docs.update(e["doc_id"].replace(".json", "") for e in cl["examples"])
    out.append(f"      rounds of the 20 loops targeting it: {n_r}; their examples by development document: {dict(ex_docs.most_common())}")
    rec["dev_vs_valid"][tag]["targeting_rounds"] = n_r
    rec["dev_vs_valid"][tag]["example_documents"] = dict(ex_docs)

# ---------- F ----------
QUOTES = {
    ("top-1 loop05", 46): "with or without a site, organism, or etiology modifier",
    ("top-1 loop05", 52): "Inheritance patterns",
    ("top-1 loop05", 61): "It remains **Disease Class**",
    ("top-1 loop05", 71): "it never demotes a Specific Disease mention",
    ("top-4 loop06", 29): "“ovarian,” “colorectal”) do not count under (a)",
    ("top-4 loop06", 35): "the standard **Disease Class** criteria apply",
    ("top-4 loop06", 93): "THEN label the full phrase as **Disease Class**",
    ("top-4 loop06", 117): "plurals, enumerations",
    ("top-4 loop01", 21): "a specific anatomical site",
    ("top-4 loop02", 58): "an **anatomic locus**",
    ("top-4 loop09", 25): "subtype or site modifier",
    ("top-4 loop10", 66): "an anatomical-site or etiologic qualifier",
    ("top-4 loop05", 16): "“short stature,” “very short limbs,” and “joint problems”",
    ("top-4 loop05", 36): "rather than a physical sign or a process",
    ("top-4 loop05", 46): "“spasticity,” “short stature,” “joint problems,” “ichthyosis” as a skin feature, “abnormal retinal vascular development”",
    ("top-4 loop05", 48): "left unlabelled, even when they are symptom-like",
    ("top-4 loop05", 157): "are not annotated",
    ("top-4 loop05", 159): "bare cohort, family-history, or risk descriptors",
    ("top-4 loop05", 160): "“a family history of cancer”",
    ("top-4 loop05", 164): "describes a feature or manifestation of a disease",
}
bad = [(n, ln) for (n, ln), w in QUOTES.items() if w not in lines(n)[ln - 1]]
out.append(f"\nF. Quoted guideline lines checked: {len(QUOTES)}; not containing the quoted words: {bad or 'none'}")
assert not bad
for (n, ln) in sorted(QUOTES):
    out.append(f"   {n} L{ln}: {lines(n)[ln - 1].strip()[:260]}")

(OUT / "dc_loss_clauses.json").write_bytes((json.dumps(rec, indent=1, ensure_ascii=False, default=list) + "\n").encode("utf-8"))
(OUT / "dc_loss_clauses_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
