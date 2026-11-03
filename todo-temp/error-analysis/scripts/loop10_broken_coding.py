"""Hand coding (10/29): the 48 gold mentions outside the Modifier subset that top-4 loop10 gets wrong while the 19 original runs
get them right at least 15 times. Offline. The coding is manual; this script stores it, checks it covers exactly those 48
mentions (from outside_subset.py), and writes loop10_broken_coding.csv and loop10_broken_coding_output.txt.

Clauses read in full (final_guidelines.txt of top-4 loop10): lines 52-60 (Section 1b and its exceptions), 123-140 (Section 3a and
its exceptions), 185-191 (What NOT to Annotate, items 3-4). Status as in modifier_b2_coding.py v2: explicit / unclear /
no applicable clause / against own clause; here "explicit" means the clause's condition covers the mention and tells it not to be
annotated (or to be labelled as predicted).

v2 (10/29, third pass): lines 61-101 (Section 1b exceptions 6-7, specifier-anchored heads, Section 1c(i) and 1c(ii) with their
exceptions) were also read in full. A clause that does not exclude a mention does not end the check: the positive rule 1c(ii)
(L87: a generic condition term filling the complement of a predicate of manifestation, consequence or association with a named
disease is Disease Class) and its exception (f) (L99: signs listed among the manifestations of an annotated disease go to audit)
were applied to the nine "outside an enumeration" mentions, and the qualified-tumor and other codes were rechecked. Each
"unclear" code names the two readings that the text does not decide between.
"""

from __future__ import annotations

import contextlib
import csv
import io
import runpy
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(HERE / "outside_subset.py"))
broken = g["broken"]
texts, st, L10 = g["texts"], g["st"], g["L10"]

BARE = ("bare or generic cancer/tumor", "explicit", "L191: a bare, unqualified cancer or tumor used generically is not annotated "
        "(the original guideline says cancer and tumor are retained)")
ENUM = ("sign or feature inside an enumeration", "explicit", "L60: a generic phenotype or symptom descriptor within a presenting-feature "
        "enumeration is not annotated automatically")
FEAT = ("sign or feature outside an enumeration", "unclear", "L60 speaks of presenting-feature enumerations; here the term is not in one")
QUAL = ("qualified tumor term", "unclear", "L191 requires a qualified family name for Disease Class; whether this qualifier counts is open")
UMB = ("umbrella class term", "against own clause", "L59: an umbrella spanning several disorders (e.g. autosomal recessive disease) is Disease Class")
OTHER = ("other missed", "no applicable clause", "no clause found in the lines read")
NONMISS = ("not a miss (label, boundary or unpaired)", "not coded", "")
code = {
    "8589723:722": BARE, "8640236:63": BARE, "8640236:179": BARE, "8640236:1361": BARE, "8674108:267": BARE, "8782829:111": BARE,
    "8782829:1628": BARE, "8938427:256": BARE, "8968716:1389": BARE, "9072974:295": BARE, "9174057:681": BARE, "9174057:920": BARE,
    "9241281:1548": BARE,
    "8673131:804": ENUM, "8673131:817": ENUM, "8968760:178": ENUM, "8968760:204": ENUM, "9083764:191": ENUM, "9083764:222": ENUM,
    "9090524:410": ENUM, "8636252:233": ENUM,
    "8673131:68": FEAT, "8689689:261": FEAT, "9083764:737": FEAT, "9083764:803": FEAT, "9083764:823": FEAT, "9083764:1066": FEAT,
    "9083764:1240": FEAT, "9083764:1347": FEAT, "9272171:507": FEAT,
    "8651278:1408": QUAL, "9019400:260": QUAL, "8758207:224": QUAL,
    "8968760:100": UMB, "8692963:435": UMB,
    "8954016:186": OTHER, "8954016:1718": OTHER, "8954016:784": OTHER,
    "8589723:742": NONMISS, "9063749:434": NONMISS, "8636252:658": NONMISS, "8789439:1114": NONMISS, "8892662:156": NONMISS,
    "9066888:97": NONMISS, "9012409:112": NONMISS, "9012409:1778": NONMISS, "8758207:779": NONMISS, "8758207:816": NONMISS,
}
V2 = {
    "9083764:1066": ("sign or feature outside an enumeration", "against own clause",
                     "L87 1c(ii): 'type 1A ..., with moderate bone dysplasia' is a manifestation complement of a named disease (SJS type 1A), "
                     "so Disease Class; L99 (f) needs a list of manifestations, and here there is none"),
    "9083764:1240": ("sign or feature outside an enumeration", "against own clause",
                     "L87 1c(ii): 'type 1B ..., with more pronounced bone dysplasia' as above; no list, so L99 (f) does not apply"),
    "9083764:1347": ("sign or feature outside an enumeration", "unclear",
                     "readings: L87 1c(ii) applies ('type 2 ..., with increased mortality and bone dysplasia') -> Disease Class; or the two "
                     "coordinated items count as manifestations listed for type 2 -> L99 (f), audit"),
    "8673131:68": ("sign or feature outside an enumeration", "explicit",
                   "L82 / L98 (e): the subject is an experimental manipulation (protein kinase levels in mice), so neither 1c rule applies"),
    "9083764:737": ("sign or feature outside an enumeration", "no applicable clause",
                    "'secondary consequences of myotonia' relates two findings, not a named disease, so L87 is not met; no exclusion applies either"),
    "9083764:823": ("sign or feature outside an enumeration", "no applicable clause",
                    "'bone dysplasia with myotonia': the anchor is a generic condition, not a named disease, so L87 is not met"),
    "8689689:261": ("sign or feature outside an enumeration", "no applicable clause",
                    "'heterozygotes suffer from iris hypoplasia': no named disease in the predicate, so L87 is not met"),
    "9083764:803": ("sign or feature outside an enumeration", "unclear",
                    "readings: Section 1b (a category-form head naming the condition a patient group has) -> annotated; or 'dysplasia' "
                    "is not a superordinate category head and no rule applies"),
    "9272171:507": ("sign or feature outside an enumeration", "unclear",
                    "readings: 'initial symptoms were the onset of ... spastic paraplegia' is a manifestation predicate of the named "
                    "disease of the document (L87) -> Disease Class; or the clause names no disease, so L87 is not met"),
    "8651278:1408": ("qualified tumor term", "unclear",
                     "readings: L190 keeps tumor when it is part of a disease-class mention and 'nonocular tumors' is one; or L191 gives "
                     "qualification only as a necessary condition, so it does not license annotation"),
    "9019400:260": ("qualified tumor term", "unclear", "same two readings for 'metastatic tumors'"),
    "8758207:224": ("qualified tumor term", "unclear", "same two readings for 'parenchymal tumours of the kidney'"),
    "8954016:186": ("other missed", "unclear",
                    "readings: Section 1b (the condition the document studies) -> annotated; or the mention denotes tissue samples "
                    "examined for loss of heterozygosity, which no rule covers"),
    "8954016:1718": ("other missed", "unclear", "same two readings for 'seven renal hamartomas'"),
    "8954016:784": ("other missed", "unclear",
                    "readings: 'JT' is a disease abbreviation and is annotated as a synonymous mention; or it is not defined as a disease "
                    "abbreviation in the document, so no rule covers it"),
}
# v3 (10/29, evidence audit): four statuses kept apart. "explicit" = a clause states that such a mention is not annotated
# (L191, L60, L84, L99); "against own clause" = a positive rule applies and requires a label; "no applicable clause" = within the
# lines read (52-101, 123-140, 185-191, What NOT 1 at 172-174) no rule covers the mention, which is not the same as a clause
# excluding it; "unclear" = two readings named. 8673131:68 was "explicit" in v2 on the strength of L82/L98, which only say that
# rule 1c does not apply; Section 1b may still apply, so it is now "unclear".
V3 = dict(V2)
V3["8673131:68"] = ("sign or feature outside an enumeration", "unclear",
                    "L82 and L98 (e) only say that 1c does not apply (the subject is an experimental manipulation). Readings: Section 1b "
                    "(L53) applies, since 'myopathy' is a generic pathology head naming the condition the document studies -> annotated; "
                    "or 'myopathy' is not a superordinate category term and no rule covers it")
keys = {f"{k[0]}:{k[1]}": k for k in broken}
assert set(code) == set(keys), (set(code) ^ set(keys))
for kk, c in code.items():
    k = keys[kk]
    assert (st(L10, k) == "missed") == (c is not NONMISS), kk
rows = []
for kk in sorted(code):
    k = keys[kk]
    grp, status, ref = code[kk]
    grp2, status2, ref2 = V2.get(kk, code[kk])
    grp3, status3, ref3 = V3.get(kk, code[kk])
    rows.append([k[0], f"{k[1]}-{k[2]}", texts[k[0]][k[1]:k[2]], k[3], st(L10, k), grp, status, ref, status2, ref2 if kk in V2 else "",
                 status3, ref3 if kk in V3 else ""])
OUT = HERE.parent / "outputs"
with (OUT / "loop10_broken_coding.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["doc", "span", "text", "gold_label", "loop10_state", "group", "v1_clause_status", "v1_clause", "v2_clause_status", "v2_reason", "v3_clause_status", "v3_reason"])
    w.writerows(rows)
c = Counter((r[5], r[6]) for r in rows)
out = [f"{len(rows)} mentions", "v1:"] + [f"   {grp:<44} {status:<22} {n}" for (grp, status), n in c.most_common()]
c2 = Counter((r[5], r[8]) for r in rows)
out += ["v2:"] + [f"   {grp:<44} {status:<22} {n}" for (grp, status), n in c2.most_common()]
out += ["v2 by status: " + str(dict(Counter(r[8] for r in rows)))]
out += ["v3 by status: " + str(dict(Counter(r[10] for r in rows)))]
(OUT / "loop10_broken_coding_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
