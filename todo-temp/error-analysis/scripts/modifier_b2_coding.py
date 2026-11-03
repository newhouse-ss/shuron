"""Hand coding (10/29): does the guideline text cover each Modifier label error on a non-Modifier gold after a relational noun?

Offline. Unit: one gold mention x one changed guideline in which that mention is predicted as Modifier (92 such pairs on 35
distinct mentions, from modifier_subset.json). The coding is manual; this script stores it and checks that it covers exactly
those pairs. It answers only "for the errors that occurred, how many have a compatible clause"; it does not measure how often
a clause is followed when it applies, because correct predictions are not coded.

v1 (first pass): explicit / by analogy / unclear / no applicable clause / against the guideline's own clause.
v2 (one rule for all): "explicit" when the clause's stated condition, including its general description, covers the instance on
a direct reading, whether or not an example names the word; "unclear" when the condition admits both readings for the instance
(vague term, or a competing Composite or Specific clause); "by analogy" only when the condition does not cover the instance and
only an example resembles it (no pair needed this in v2); "no applicable clause" and "against own clause" as in v1.
v3: the "no applicable clause" and "against own clause" codes rechecked for positive rules, exceptions and cross-references.
Writes modifier_b2_clause_coding_v1.csv, _v2.csv, _v3.csv and modifier_b2_coding_output.txt.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "outputs"
J = json.loads((OUT / "modifier_subset.json").read_text(encoding="utf-8"))
G = {"1-05": "top-1 loop05", "4-05": "top-4 loop05", "4-06": "top-4 loop06", "4-07": "top-4 loop07", "4-08": "top-4 loop08",
     "4-09": "top-4 loop09", "4-10": "top-4 loop10"}
REF = {"1-05": "L63 family-history or relative frame keeps Modifier", "4-05": "L159-161 disease named in cohort, family-history or risk descriptors is Modifier",
       "4-06": "L150 disease names that modify human or clinical nouns (patients, cases, families, risk, population) and family-history constructions; L120 attributive only",
       "4-07": "L65 premodifier or complement of a context or population noun such as cases, population, history, risk, incidence",
       "4-08": "L46-48 attributive premodifier, complement of a history frame; L55 with/has frames are Specific",
       "4-09": "L130/L158 family-history and cohort descriptors are Modifier; L135 coordinated lists are Composite; L149 other prepositional complements are Specific",
       "4-10": "L146 a disease that qualifies a relational noun phrase such as 'a family history of X' is Modifier; L191 bare cancer in a family history is not annotated"}
M, A, U, N, C = "explicit", "by analogy", "unclear", "no applicable clause", "against own clause"
V1 = {
 "8589723:202": {"4-07": M, "4-10": A}, "8589723:235": {"4-07": M, "4-10": A}, "8589723:999": {"4-07": M, "4-10": A},
 "8589723:1302": {"4-07": A, "4-10": A}, "8589723:1354": {"4-07": A, "4-10": A},
 "8636252:839": {"4-06": N}, "8636252:861": {"4-06": U}, "8640236:986": {"4-07": M},
 "8651278:136": {"4-07": A}, "8659549:86": {"4-07": A}, "8659549:256": {"4-07": A},
 "8841191:234": {"4-07": M, "4-10": A}, "8931709:444": {"4-06": U, "4-07": M, "4-09": A},
 "8968716:936": {"4-06": U, "4-08": U}, "9012404:314": {"1-05": U, "4-06": U, "4-07": U},
 "9012404:793": {"1-05": M, "4-06": M, "4-07": M, "4-08": M}, "9012404:819": {"1-05": A, "4-06": U, "4-07": M, "4-09": A},
 "9012404:945": {"1-05": U, "4-06": U, "4-07": U}, "9028321:598": {"4-06": U}, "9063749:158": {"4-09": U},
 "9144439:1125": {"4-07": M}, "9145677:69": {"4-07": M, "4-10": A}, "9145677:196": {"4-07": M, "4-10": A},
 "9145677:507": {"4-05": N},
 "9145677:714": {g: M for g in G}, "9145677:786": {g: M for g in G}, "9145677:808": {g: A for g in G},
 "9145677:1024": {"1-05": N, "4-06": N, "4-09": C}, "9145677:1056": {"1-05": N, "4-05": N, "4-06": N, "4-09": C},
 "9145677:1475": {"1-05": A, "4-05": N, "4-06": N, "4-09": C}, "9145677:1534": {"4-05": N},
 "9195227:335": {"1-05": M, "4-06": M, "4-07": M, "4-08": M}, "9195227:645": {"1-05": M, "4-06": M, "4-07": M, "4-08": M},
 "9195227:697": {"1-05": A, "4-06": U, "4-09": A}, "9222760:633": {"4-06": U, "4-07": A, "4-09": U},
}
# v2 changes, with the reason for each
V2_CHANGES = {
 # loop10 L146: "relational noun phrase" is a general description; whether "risk of X" is one, and whether the disease there
 # "characterizes the relational noun phrase rather than naming a diagnosis", admits both readings.
 **{(k, "4-10"): (U, "L146 general description; risk-of as a relational noun phrase admits both readings")
    for k in ("8589723:202", "8589723:235", "8589723:999", "8589723:1302", "8589723:1354", "8841191:234", "9145677:69", "9145677:196")},
 # loop07 L65 names "context or population noun such as ...": risk factors for, susceptibility to, patients with, families with
 ("8589723:1302", "4-07"): (U, "X is the complement of 'factors' in 'risk factors', not of 'risk'"),
 ("8589723:1354", "4-07"): (U, "whether 'susceptibility' is a context noun under L65 admits both readings"),
 ("8651278:136", "4-07"): (U, "whether 'patients' is a population noun under L65 admits both readings"),
 ("8659549:86", "4-07"): (U, "same as above"), ("8659549:256", "4-07"): (U, "same as above"),
 ("9222760:633", "4-07"): (U, "whether 'families' is a population noun under L65 admits both readings"),
 # "history of breast cancer but not ovarian cancer": the conjunct is inside the complement, but the Composite rules also apply
 **{("9145677:808", g): (U, "conjunct inside the history complement; Composite rules compete") for g in G},
 # top-1 loop05 L63 is stated as "the condition belongs to relatives rather than to the patients"
 ("9012404:819", "1-05"): (M, "L63 general description: the condition belongs to a first-degree relative"),
 ("9195227:697", "1-05"): (M, "L63 general description: a sister's condition"),
 ("9145677:1475", "1-05"): (U, "'in a family' does not say whose condition it is"),
 # loop09 L130: "a disease named in a family history of relatives, or used to describe a cohort or case series"
 ("8931709:444", "4-09"): (U, "whether 'most cases of FAP' describes a case series admits both readings"),
 ("9012404:819", "4-09"): (M, "named inside the family-history description of a relative"),
 ("9195227:697", "4-09"): (U, "a sister's condition, but no family-history phrase"),
}
V2 = {k: dict(d) for k, d in V1.items()}
reasons = {}
for (k, g), (c, why) in V2_CHANGES.items():
    assert g in V2[k], (k, g)
    V2[k][g] = c
    reasons[(k, g)] = why

# v3 (10/29, third pass): the "no applicable clause" and "against own clause" codes were rechecked for positive rules,
# exceptions and cross-references outside the clause first read.
V3_CHANGES = {
 ("9145677:1475", "4-05"): (U, "L159-161: 'the presence of ovarian cancer in a family' may be a family-history descriptor (Modifier) or a predictor variable"),
 ("8636252:839", "4-06"): (U, "L150 'disease names that modify human or clinical nouns': whether 'prevalence' is such a noun and a complement 'modifies' it admits both readings"),
 ("9145677:1024", "4-06"): (U, "L150: 'diagnosis' is a clinical noun; whether a complement 'modifies' it admits both readings"),
 ("9145677:1475", "4-06"): (U, "L150 family-history constructions: 'presence of ovarian cancer in a family' may be one"),
 ("9145677:1056", "4-09"): (U, "L158 excepts family-history descriptors from L149; whether 'the presence of ovarian cancer' (a mutation predictor) is one admits both readings"),
 ("9145677:1475", "4-09"): (U, "L158: 'in a family' reads as a family-history descriptor; L149 would make it Specific"),
}
V3 = {k: dict(d) for k, d in V2.items()}
reasons3 = dict(reasons)
for (k, g), (c, why) in V3_CHANGES.items():
    assert g in V3[k], (k, g)
    V3[k][g] = c
    reasons3[(k, g)] = why

# v4 (10/29, evidence audit): the "Composite rules compete" reason was checked against each guideline's Composite rule and
# precedence list. A Composite rule competes only when its own condition holds (a conjunct depends on a shared head, or
# splitting loses information). "a history of breast cancer but not ovarian cancer" joins two separately headed names, so the
# Composite rule does not apply there (loop09 L104-105 say so explicitly; the other guidelines keep the original information-
# loss condition). For the three shared-head complements the competition is real, unless a precedence list settles it: loop06
# L135 excludes Modifier spans from the step that applies the Composite rule. Only these 15 records were re-read in this pass.
HIST = {"1-05": "L63 relative frame", "4-05": "L159-161 named disease in a family-history descriptor", "4-06": "L150 family-history constructions",
        "4-07": "L65 complement of a context noun such as history", "4-08": "L48 complement of a history frame",
        "4-10": "L146 qualifies a relational noun phrase such as 'a family history of X'"}
V4_CHANGES = {
 **{("9145677:808", g): (M, f"{why}; the conjunct is inside the history complement; Composite does not apply (two separately headed names)")
    for g, why in HIST.items()},
 ("9145677:808", "4-09"): (U, "readings: L130 'a disease named in a family history ... is a Modifier when it names one disease' -> Modifier; or L268 "
                             "limits Modifier to a single-disease descriptor, this one names two, and L149 makes a prepositional complement Specific. "
                             "Composite does not apply (L104-105)"),
 ("9012404:314", "4-06"): (M, "L150 family-history constructions are Modifier; L135 precedence excludes Modifier spans from the Composite step"),
 ("9012404:945", "4-06"): (M, "same as above"),
 ("8968716:936", "4-06"): (M, "same as above"),
 ("9012404:314", "1-05"): (U, "shared head: the Composite rule and L63 both apply; no precedence section"),
 ("9012404:945", "1-05"): (U, "same as above"),
 ("9012404:314", "4-07"): (U, "shared head: the Composite rule and L65 both apply; L111-112 rank Modifier only above Section 1b, not above Composite"),
 ("9012404:945", "4-07"): (U, "same as above"),
 ("8968716:936", "4-08"): (U, "shared head: the Composite rule and L48 both apply; L159 ranks Modifier only above Specific/Class, L163 ranks Composite only above item 8"),
}
V4 = {k: dict(d) for k, d in V3.items()}
reasons4 = dict(reasons3)
for (k, g), (c, why) in V4_CHANGES.items():
    assert g in V4[k], (k, g)
    V4[k][g] = c
    reasons4[(k, g)] = why

# v5 (10/29, final): v4 treated "a conjunct depends on a shared head" as the condition of every guideline's Composite rule.
# Only loop09 (L104-105) states that condition. top-1 loop05 L76, top-4 loop05 L70, loop07 L48, loop08 L29 and loop10 L106 keep the
# broad rule ("a textual string may refer to two or more separate disease mentions ... Composite"); information loss appears only
# in the Duchenne example, which shows one case where the rule applies, not a necessary condition. So for "a history of breast
# cancer but not ovarian cancer" those five guidelines give two readings. loop06 keeps "explicit", but on its precedence rule
# (L135), not on the Composite condition.
BROAD = {"1-05": "L76", "4-05": "L70", "4-07": "L48", "4-08": "L29", "4-10": "L106"}
V5_CHANGES = {
 **{("9145677:808", g): (U, f"readings: the broad Composite rule ({ln}) covers one string naming two separate diseases -> Composite; or, reading "
                            f"the Duchenne example as the rule's condition, the names are split and the history clause makes this one Modifier")
    for g, ln in BROAD.items()},
 ("9145677:808", "4-06"): (M, "L150 family-history constructions are Modifier; L135 precedence excludes Modifier spans from the Composite step"),
}
V5 = {k: dict(d) for k, d in V4.items()}
reasons5 = dict(reasons4)
for (k, g), (c, why) in V5_CHANGES.items():
    assert g in V5[k], (k, g)
    V5[k][g] = c
    reasons5[(k, g)] = why

seen = set()
pairs = []
for key, m in J["members"].items():
    if m["subgroup"] != "other gold, B2 context":
        continue
    doc, rest, lab = key.split(":")
    start = rest.split("-")[0]
    for short, g in G.items():
        if m["states"][g] == "label->Modifier":
            pairs.append((doc, rest, lab, short, f"{doc}:{start}"))
            seen.add((f"{doc}:{start}", short))
assert {(k, s) for k, d in V1.items() for s in d} == seen
out = [f"{len(pairs)} pairs on {len({p[4] for p in pairs})} distinct gold mentions"]
for ver, code in (("v1", V1), ("v2", V2), ("v3", V3), ("v4", V4), ("v5", V5)):
    with (OUT / f"modifier_b2_clause_coding_{ver}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["doc", "span", "gold_label", "guideline", "clause_status", "clause_read"] + ([f"{ver}_change_reason"] if ver != "v1" else []))
        for doc, rest, lab, short, key in pairs:
            w.writerow([doc, rest, lab, G[short], code[key][short], REF[short]] + ([{"v2": reasons, "v3": reasons3, "v4": reasons4, "v5": reasons5}[ver].get((key, short), "")] if ver != "v1" else []))
    tab = Counter((G[s], code[k][s]) for *_, s, k in pairs)
    out.append(f"\n{ver}: " + str(dict(Counter(code[k][s] for *_, s, k in pairs))))
    for g in G.values():
        out.append(f"   {g:<14} " + "  ".join(f"{c}: {tab[(g, c)]}" for c in (M, A, U, N, C)))
out.append(f"\nv2 changed {len(V2_CHANGES)} of {len(pairs)} codes")
out.append(f"v3 changed {len(V3_CHANGES)} more codes")
out.append(f"v4 re-read {len(V4_CHANGES)} records (the Composite-competition reason); the other records were not re-read in this pass")
out.append(f"v5 changed {len(V5_CHANGES)} records back where v4 had applied loop09's Composite condition to other guidelines")
(OUT / "modifier_b2_coding_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
