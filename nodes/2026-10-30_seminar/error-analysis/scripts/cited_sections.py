"""The annotator's stated reasons in the saved replies (10/29, after the independent review). Offline, no API calls.

Every validation annotation reply (outputs/ncbi_disease/20261022_haiku-xhigh_batchqueue/replies/) gives, for each
predicted mention, its label, a rationale and the guideline section the annotator says it applied. This script matches
each changed guideline's validation predictions to its replies and reads that section for:
  A. the reply format: which top-level fields an annotation reply has;
  B. the 92 label errors to Modifier after a relational noun (modifier_subset.py, B2 list): does the cited section name the
     guideline's clause that makes such positions Modifier? Cross-tabulated with the hand coding (v5 csv);
  C. the nine non-Modifier mentions after "history of": state and cited section in each changed guideline;
  D. coverage: how many fixed or broken mentions (rule_links.py) the hand coding reaches;
  E. checks that the guideline lines quoted in the report contain the quoted words.
A cited section shows which clause the annotator says it followed, not that the clause caused the label. A missed mention
has no prediction and so no reason.
Matching: the reply for a document is the one whose (text, label) multiset contains the saved predictions' multiset with
the fewest extra items (alignment can drop mentions); within it, the mention with the same text and label nearest in offset.
Writes cited_sections_output.txt and cited_sections.csv.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
RUNS = ROOT / "outputs" / "ncbi_disease"
REPLIES = RUNS / "20261022_haiku-xhigh_batchqueue" / "replies"
ORIGINAL = ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt"
LOOP = {"top-1 loop05": "topk1L05", "top-1 loop07": "topk1L07",
        **{f"top-4 loop{i:02d}": f"topk4L{i:02d}" for i in (1, 2, 4, 5, 6, 7, 8, 9, 10)}}
FOLDER = {g: RUNS / f"20261022_haiku-xhigh_{'topk1' if g.startswith('top-1') else 'topk4'}_loop{g[-2:]}" for g in LOOP}

# The clause in each guideline that makes these positions Modifier (line numbers in final/final_guidelines.txt), and the
# words by which a cited section names it. "section only": the citation gives just the Modifier section that holds it.
CLAUSE = {
    "top-1 loop05": ("L63, 1.2(d) family-history or relative frame", ("1.2(d)", "constraint (d)")),
    "top-4 loop05": ("L159-161, What NOT 8", ("what not 8",)),
    "top-4 loop06": ("L120 1.5(f) and L150 in Section 3", ("1.5(f)", "family-history")),
    "top-4 loop07": ("L65, context and population frames", ("context and population",)),
    "top-4 loop08": ("L46-48, narrower condition: complement of a history frame", ("history frame", "narrower condition")),
    "top-4 loop09": ("L130 and L158, family-history descriptors (3.1 step 4)", ("family-history", "3.1")),
    "top-4 loop10": ("L145-146, 3c relational complements", ("3c",)),
}
SECTION = ("section 3", "3 modifier", "item 3", "§3", "what to annotate 3")

# copied from modifier_subset.py (REL, B2), to find the mentions after "history of" the same way
REL = (r"risks?|histor(y|ies)|cases?|patients?|carriers?|families|family|individuals|members|relatives|women|men|children|"
       r"frequency|incidence|prevalence|predisposition|susceptibility|subjects|probands?"
       r"|presence|diagnosis|factors|sisters?|brothers?|mothers?|fathers?|parents?|adults")
B2 = re.compile(r"\b(" + REL + r")\s+(of|with|for|to)\s+((the|a|an)\s+)?((\S+\s+){1,5}(but not|and / or|and|or)\s+)?$", re.I)

out, csv_rows = [], []

# A. reply format, and the replies of the changed loops
keys = Counter()
replies = defaultdict(list)
for p in sorted(REPLIES.glob("*.json")):
    r = json.loads(p.read_text(encoding="utf-8"))
    if r["meta"].get("task") != "annotate_with_guidelines":
        continue
    text = next((b["text"] for b in r["message"]["content"] if b.get("type") == "text"), "")
    try:
        j = json.loads(text)
    except json.JSONDecodeError:
        keys["(not parsable)"] += 1
        continue
    keys[", ".join(sorted(j))] += 1
    replies[r["meta"]["loop"]].append(j.get("annotations", []))
out.append("A. Annotation replies by their top-level fields: " + "; ".join(f"{k}: {v}" for k, v in keys.items()))
out.append("   (no field for flagging a mention for review: a mention a guideline routes to review or audit is not output)")

preds = {}


def predictions(g, doc):
    if (g, doc) not in preds:
        preds[(g, doc)] = json.loads((FOLDER[g] / "valid_predictions" / f"{doc}.json").read_text(encoding="utf-8"))
    return preds[(g, doc)]


def reason(g, doc, start, end):
    """The prediction overlapping the gold span most, and the annotator's section and rationale for it."""
    p = predictions(g, doc)
    ov = [x for x in p["denotations"] if min(end, x["span"]["end"]) - max(start, x["span"]["begin"]) > 0]
    if not ov:
        return None
    x = max(ov, key=lambda x: min(end, x["span"]["end"]) - max(start, x["span"]["begin"]))
    ptext = p["text"][x["span"]["begin"]:x["span"]["end"]]
    want = Counter((p["text"][d["span"]["begin"]:d["span"]["end"]], d["obj"]) for d in p["denotations"])
    best = None
    for ann in replies[LOOP[g]]:
        have = Counter((a["text"], a["entity"]) for a in ann)
        if all(have[k] >= v for k, v in want.items()):
            extra = sum((have - want).values())
            if best is None or extra < best[0]:
                best = (extra, ann)
    if best is None:
        return {"pred_text": ptext, "pred_label": x["obj"], "section": "(no matching reply)", "rationale": ""}
    cands = [a for a in best[1] if a["text"] == ptext and a["entity"] == x["obj"]]
    a = min(cands, key=lambda a: abs(a["start"] - x["span"]["begin"]))
    return {"pred_text": ptext, "pred_label": x["obj"], "section": a.get("guideline_section", ""), "rationale": a.get("rationale", "")}


def clause_class(g, section):
    s = section.lower()
    if any(m in s for m in CLAUSE[g][1]):
        return "names the clause"
    if any(m in s for m in SECTION) or s.startswith("3"):
        return "section only"
    return "other"


# B. the 92 label errors to Modifier after a relational noun
members = json.loads((HERE / "modifier_subset.json").read_text(encoding="utf-8"))["members"]
b2 = {k: v for k, v in members.items() if "B2" in v["tags"] and not k.endswith(":Modifier")}
v5 = {(r["doc"], r["span"], r["guideline"]): r["clause_status"]
      for r in csv.DictReader((HERE / "modifier_b2_clause_coding_v5.csv").open(encoding="utf-8"))}
errs = []
for g in LOOP:
    for k, v in b2.items():
        if v["states"][g] != "label->Modifier":
            continue
        doc, span, lab = k.split(":")
        s, e = map(int, span.split("-"))
        r = reason(g, doc, s, e)
        cls = clause_class(g, r["section"])
        errs.append((g, doc, span, lab, r, cls, v5.get((doc, span, g), "(not coded)")))
assert len(errs) == 92, len(errs)
out.append(f"\nB. The {len(errs)} label errors to Modifier after a relational noun: the section the annotator cites")
out.append(f"   {'guideline':<14} {'errors':>6} {'names the clause':>17} {'section only':>13} {'other':>6}  clause in the guideline")
for g in LOOP:
    sel = [x for x in errs if x[0] == g]
    if not sel:
        continue
    c = Counter(x[5] for x in sel)
    out.append(f"   {g:<14} {len(sel):6} {c['names the clause']:17} {c['section only']:13} {c['other']:6}  {CLAUSE[g][0]}")
c = Counter(x[5] for x in errs)
out.append(f"   {'total':<14} {len(errs):6} {c['names the clause']:17} {c['section only']:13} {c['other']:6}")
out.append("   citations by guideline (count):")
for g in LOOP:
    cc = Counter(x[4]["section"] for x in errs if x[0] == g)
    if cc:
        out.append(f"      {g}: " + "; ".join(f"{s} ({n})" for s, n in cc.most_common()))
out.append("   hand coding (v5) against the citation:")
tab = Counter((x[6], x[5]) for x in errs)
for status in ("explicit", "unclear", "no applicable clause", "against own clause"):
    out.append(f"      {status:<20} " + ", ".join(f"{cls} {tab[(status, cls)]}" for cls in ("names the clause", "section only", "other")))
for x in errs:
    csv_rows.append({"part": "B", "guideline": x[0], "doc": x[1], "span": x[2], "gold_label": x[3], "state": "label->Modifier",
                     "pred_text": x[4]["pred_text"], "pred_label": x[4]["pred_label"], "cited_section": x[4]["section"],
                     "rationale": x[4]["rationale"], "clause_class": x[5], "v5_status": x[6]})

# C. the nine non-Modifier mentions after "history of"
texts = {}
hist = []
for k in sorted(b2):
    doc, span, lab = k.split(":")
    s, e = map(int, span.split("-"))
    if doc not in texts:
        texts[doc] = predictions("top-4 loop10", doc)["text"]
    m = B2.search(texts[doc][max(0, s - 80):s])
    if m and re.fullmatch(r"histor(y|ies)", m.group(1), re.I):
        hist.append((k, doc, s, e, lab))
assert len(hist) == 9, len(hist)
out.append("\nC. The nine non-Modifier mentions after 'history of': state and cited section in each changed guideline")
for k, doc, s, e, lab in hist:
    out.append(f"   {doc}:{s}-{e} {lab} {texts[doc][s:e]!r}")
    for g in LOOP:
        st = b2[k]["states"][g]
        r = reason(g, doc, s, e)
        out.append(f"      {g:<14} {st:<17} " + (f"{r['pred_label']:<16} cites: {r['section'][:90]}" if r else "(no prediction)"))
        csv_rows.append({"part": "C", "guideline": g, "doc": doc, "span": f"{s}-{e}", "gold_label": lab, "state": st,
                         "pred_text": r["pred_text"] if r else "", "pred_label": r["pred_label"] if r else "",
                         "cited_section": r["section"] if r else "", "rationale": r["rationale"] if r else "",
                         "clause_class": clause_class(g, r["section"]) if r and g in CLAUSE else "", "v5_status": ""})

# D. coverage of the hand coding
links = json.loads((HERE / "rule_links.json").read_text(encoding="utf-8"))
fixed = sum(len(v["items"]["fixed"]) for v in links["guidelines"].values())
broken = sum(len(v["items"]["broken"]) for v in links["guidelines"].values())
chance = len(links["guidelines"]) * (links["chance_total"]["fixed"][0] + links["chance_total"]["broken"][0])
l10 = Counter(r["v3_clause_status"] for r in csv.DictReader((HERE / "loop10_broken_coding.csv").open(encoding="utf-8")))
v5c = Counter(v5.values())
coded = len(v5) + sum(n for st, n in l10.items() if st != "not coded")
out.append("\nD. Coverage of the hand coding")
out.append(f"   fixed {fixed} + broken {broken} = {fixed + broken} mention x guideline over the {len(links['guidelines'])} changed guidelines"
           f" (rule_links.py); one original run against the other 18 gives {chance:.0f} over 11 runs by chance")
out.append(f"   hand-coded against the guideline text: {len(v5)} label errors to Modifier (v5: {dict(v5c)})"
           f" + {coded - len(v5)} loop10 misses (v3: {dict(l10)}) = {coded} errors; none of the fixed side")
orig_names = [g for g in next(iter(members.values()))["states"] if g not in LOOP]
assert len(orig_names) == 19
b_v5 = sum(sum(b2[f"{x[1]}:{x[2]}:{x[3]}"]["states"][g] == "right" for g in orig_names) >= 15 for x in errs)
out.append(f"   of these, on the broken side (original right in at least 15 of 19): {b_v5} of the {len(v5)} label errors to Modifier"
           f" + all {coded - len(v5)} loop10 misses (chosen that way) = {b_v5 + coded - len(v5)}")
out.append(f"   coded as an explicit clause: {v5c['explicit']} + {l10['explicit']} = {v5c['explicit'] + l10['explicit']}")

# E. guideline lines quoted in the report
CHECKS = [(ORIGINAL, 77, "the terms “cancer” and “tumor” were retained"),
          ("top-4 loop10", 84, "routed to annotation audit rather than tagged automatically"),
          ("top-4 loop10", 99, "These are routed to audit"),
          ("top-4 loop10", 145, "3c. Relational complements"),
          ("top-4 loop10", 146, "such as “a family history of X,” is annotated **Modifier**"),
          ("top-4 loop10", 190, "are retained when they are part of a specific disease or disease-class mention"),
          ("top-4 loop10", 191, "is a general term and is not annotated"),
          ("top-1 loop05", 63, "keeps its existing treatment (Modifier under Section 3)"),
          ("top-4 loop05", 160, "“a family history of cancer”) is not annotated"),
          ("top-4 loop05", 161, "the named disease is a **Modifier**"),
          ("top-4 loop02", 245, "is not labeled. It is flagged for manual verification"),
          ("top-4 loop07", 65, "or is the complement of, a context or population noun"),
          ("top-4 loop09", 130, "A disease named in a family history of relatives"),
          ("top-4 loop09", 158, "even when the disease term is the complement of “of”"),
          ("top-4 loop09", 243, "the terms “cancer” and “tumor” were retained"),
          ("top-4 loop09", 268, "single-disease family-history or cohort descriptor, is a Modifier")]


def lines(src):
    path = src if isinstance(src, Path) else FOLDER[src] / "final" / "final_guidelines.txt"
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")


out.append("\nE. Guideline lines quoted in the report")
for src, n, words in CHECKS:
    assert words in lines(src)[n - 1], (src, n, words)
    out.append(f"   ok  {'original' if isinstance(src, Path) else src} L{n}: {words}")
sec3 = "\n".join(lines("top-1 loop05")[82:97]).lower()
assert sec3.startswith("### 3.") and "history" not in sec3 and "relative" not in sec3
out.append("   ok  top-1 loop05 L83-97 (its Section 3) never mentions history or relatives")
assert "family history of cancer" not in "\n".join(lines("top-4 loop09")).lower()
out.append("   ok  top-4 loop09 never mentions 'family history of cancer'")

with (HERE / "cited_sections.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
    w.writeheader()
    w.writerows(csv_rows)
(HERE / "cited_sections_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
