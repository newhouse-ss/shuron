"""Semantic judgments for the 62 top-4 loop07 positions with no prediction (2026-11-05 pilot). Offline, no API calls.

The judgments below were made by reading the top-4 loop07 final guideline
(outputs/ncbi_disease/20261022_haiku-xhigh_topk4_loop07/final/final_guidelines.txt) and the original guideline
(data/guidelines/ncbi_disease_guidelines.txt) against each position's sentence and the original runs' cited sections
(outputs/bar_clause_pilot/loop07_noprediction_lookup.csv). Method: note 20261105_bar_cluster_sample_method.md, section 5.
Judgment values:
  explicit       a loop07 rule states the condition and says not to annotate (or gives a matching O example)
  possible       a loop07 rule covers it only by extension or analogy, or only routes it to review
  rule_unchanged the original guideline already has the same rule and loop07 did not change it
  rule_says_label a loop07 rule asks for the label the model omitted
  type_changed   loop07 predicted the same span with another type (still a false positive); deferred
  not_found      no loop07 content found
Output: outputs/bar_clause_pilot/loop07_noprediction_judgments.csv and a summary printed to stdout and saved as
outputs/bar_clause_pilot/loop07_noprediction_judgments_output.txt.
"""
import collections
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "outputs" / "bar_clause_pilot"

R_DOWN = ("L152-153 (What NOT to Annotate 7, new): complements of results in / leads to / is associated with are not "
          "disease mentions; also L41, Example 21")
R_DEF = ("L139 + L114 + L31 (new): a deficiency noun is part of a Specific Disease only under 1a; otherwise stays O")
R_REVIEW = ("L38 + L262 (new): generic, quantified or plural references and 'types of X' are flagged for review; "
            "the output has no review label")
R_LIST = "L26 + Example 22 L233 (new): a member of a characterized-by feature list keeps its current label, routed to review"
R_BRACKET = ("L69 + L75 (new): in a gene/protein designation, bracketed symbols and symbol tokens stay outside the entity")
R_VARIANT = ("L72(a) + Example 26 L245-246 (new): variant or gene designations with no disease-denoting token "
             "(e.g. G6PD A-, G6PD B) are O")
R_SYMBOL = "L72(a) (new): locus, organism or purely alphanumeric gene symbols get no Modifier"
R_PROCESS = ("L142-143 + L40 (original has the biological-process rule; loop07 adds angiogenesis, vasculogenesis and "
             "process-suffix heads)")
R_GENERAL = "What NOT to Annotate 4: 'disease' is a general term (same in the original)"
R_L69_LABEL = "L69 (new): a disease premodifier of a gene designation (tumour suppressor gene) is Modifier"
R_EX28 = "Example 28 L252-253 (new): 'G6PD deficient' premodifying a noun is Modifier"

# (doc, text, label) -> (judgment, rule, note)
J = {
    # gold mentions left with no overlapping prediction
    ("9019400", "metastatic tumors", "DiseaseClass"): ("possible", R_DOWN,
        "'the ability to produce metastatic tumors in nude mice'; 'produce' is not among the listed predicates"),
    ("8640236", "pancreatic tumour", "Modifier"): ("not_found", "", "'a pancreatic tumour cell line'; cell line is not a gene/protein head"),
    ("8636252", "adrenal insufficiency", "DiseaseClass"): ("explicit", R_DOWN,
        "'ALD is a genetic disease associated with ... adrenal insufficiency'"),
    ("8968760", "cerebellar degeneration", "DiseaseClass"): ("possible", R_LIST,
        "'A-T, characterized by cerebellar degeneration, immunodeficiency and cancer predisposition'"),
    ("8786135", "AT", "Modifier"): ("possible", R_BRACKET, "'Atm (ataxia-telangiectasia (AT)-mutated)'"),
    ("9182899", "complete deficiency of C9", "SpecificDisease"): ("explicit", R_DEF, "'heterozygous for a complete deficiency of C9'; not a 1a predicate"),
    ("8894695", "deficiency of APRT", "SpecificDisease"): ("explicit", R_DEF, "subject of 'may lead to'; not a 1a predicate"),
    ("8640236", "tumours", "DiseaseClass"): ("possible", R_REVIEW, "'the tumours they develop'"),
    ("8644702", "tumors", "DiseaseClass"): ("possible", R_REVIEW, "'in associated tumors'"),
    ("9195227", "tumours", "DiseaseClass"): ("possible", R_REVIEW, "'any of the tumours studied'"),
    ("8649785", "tumour", "DiseaseClass"): ("not_found", "",
        "'established from the tumour of the proband'; 1b (L34) would ask for Specific Disease, not O"),
    ("9195227", "tumour", "Modifier"): ("not_found", "", "'tumour DNA'"),
    ("8636252", "genetic disease", "DiseaseClass"): ("rule_unchanged", R_GENERAL, ""),
    ("9241281", "tumour", "Modifier"): ("possible", R_PROCESS, "'acceleration of tumour formation'; process by meaning, not by suffix"),
    ("8644702", "tumor", "Modifier"): ("possible", R_REVIEW, "'Other tumor types'"),
    ("8938427", "tumor", "Modifier"): ("not_found", "", "'tumor suppressive function'"),
    ("9241281", "acute radiation toxicity", "SpecificDisease"): ("not_found", "", ""),
    ("8640236", "tumour", "Modifier"): ("possible", R_REVIEW, "'twelve other tumour types'"),
    ("8649785", "tumour", "Modifier"): ("rule_says_label", R_L69_LABEL, "'the tumour suppressor gene TP53'"),
    ("8651278", "tumor", "Modifier"): ("not_found", "", "'the number of tumor foci'"),
    ("8758207", "tumours", "DiseaseClass"): ("possible", R_REVIEW, "'None of these tumours'"),
    ("8828602", "PAH-deficient", "Modifier"): ("rule_says_label", R_EX28, "'PAH-deficient hepatocytes / mice'"),
    ("8892662", "deficiencies of complement components", "DiseaseClass"): ("explicit", R_DEF, ""),
    # no-gold predictions the original made that loop07 did not make
    ("8666397", "sf", "Modifier"): ("possible", R_SYMBOL + "; L69 bracketed symbols outside", "scurfy (sf) mouse mutant symbol"),
    ("8666397", "sf", "SpecificDisease"): ("possible", R_SYMBOL + "; L69 bracketed symbols outside", "scurfy (sf) mouse mutant symbol"),
    ("8666397", "scurfy", "Modifier"): ("type_changed", "", "loop07 labels the same span SpecificDisease"),
    ("8666397", "scurfy", "SpecificDisease"): ("type_changed", "", "loop07 labels the same span Modifier"),
    ("8689689", "Small eye", "Modifier"): ("type_changed", "", "loop07 labels the same span SpecificDisease"),
    ("9069115", "AKU", "Modifier"): ("explicit", R_BRACKET, "'the human alkaptonuria gene (AKU)': bracketed symbol after the gene head"),
    ("9069115", "AKU", "SpecificDisease"): ("explicit", R_BRACKET, "same position"),
    ("9012409", "Duarte", "Modifier"): ("possible", R_VARIANT, "GALT variant name"),
    ("9012409", "Los Angeles", "Modifier"): ("possible", R_VARIANT, "GALT variant name"),
    ("9012409", "Los Angeles", "SpecificDisease"): ("possible", R_VARIANT, "GALT variant name"),
    ("9012409", "LA", "Modifier"): ("possible", R_VARIANT, "GALT variant name"),
    ("9012409", "LA", "SpecificDisease"): ("possible", R_VARIANT, "GALT variant name"),
    ("8808605", "G6PD Portici", "SpecificDisease"): ("explicit", R_VARIANT, "named G6PD variant, like G6PD A- / G6PD B"),
    ("8808605", "G6PD Bari", "SpecificDisease"): ("explicit", R_VARIANT, "named G6PD variant, like G6PD A- / G6PD B"),
    ("8825599", "Mediterranean , Seattle-like and A-variants", "CompositeMention"): ("possible", R_VARIANT, "G6PD variants"),
    ("8808605", "G6PD", "Modifier"): ("explicit", R_SYMBOL, "'class I G6PD mutations'"),
    ("8808605", "glucose-6-phosphate dehydrogenase", "Modifier"): ("possible", R_SYMBOL, "enzyme name before 'mutations'"),
    ("9050868", "aortic rupture", "SpecificDisease"): ("explicit", R_DOWN, "'a disease leading to aortic rupture'"),
    ("9083764", "type 1B", "SpecificDisease"): ("not_found", "", "bare SJS subtype label"),
    ("9083764", "type 1A", "SpecificDisease"): ("not_found", "", "bare SJS subtype label"),
    ("9083764", "type 2", "SpecificDisease"): ("not_found", "", "bare SJS subtype label"),
    ("8871666", "C7 defect", "SpecificDisease"): ("possible", R_DEF, "'defect' treated like 'deficiency' by analogy"),
    ("8625410", "WAS", "SpecificDisease"): ("not_found", "", "'WAS' cut from the gene token 'WASP'"),
    ("8931701", "WAS", "Modifier"): ("not_found", "", "'WAS' cut from the gene token 'WASP'"),
    ("8931701", "WAS", "SpecificDisease"): ("not_found", "", "'WAS' cut from the gene token 'WASP'"),
    ("8700509", "breast / ovarian", "CompositeMention"): ("rule_unchanged", R_PROCESS, "premodifier of 'tumorigenesis'"),
    ("9028321", "lymphoproliferation", "SpecificDisease"): ("possible", R_PROCESS, "process-suffix nominal"),
}

rows = list(csv.DictReader(open(OUT / "loop07_noprediction_lookup.csv", encoding="utf-8")))
assert len(rows) == 62, len(rows)
out, missing = [], []
for r in rows:
    label = r["gold_label"] or r["nogold_label"]
    k = (r["doc"], r["text"], label)
    if k not in J:
        missing.append(k)
        continue
    j, rule, note = J[k]
    out.append({"category": r["category"], "doc": r["doc"], "start": r["start"], "end": r["end"], "text": r["text"],
                "label": label, "n_orig_of_19": r["n_orig_of_19"], "d": r["d"], "judgment": j, "loop07_rule": rule,
                "note": note, "original_cited_sections": r["original_cited_sections"]})
assert not missing, missing

with open(OUT / "loop07_noprediction_judgments.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)

lines = ["Judgments for the 62 top-4 loop07 positions with no prediction (n | summed d)"]
for cat in ("gold_now_unlabelled", "nogold_dropped_prediction"):
    lines.append(f"\n{cat}")
    by = collections.defaultdict(list)
    for o in out:
        if o["category"] == cat:
            by[(o["judgment"], o["loop07_rule"])].append(float(o["d"]))
    for (j, rule), ds in sorted(by.items(), key=lambda kv: sum(kv[1])):
        lines.append(f"   {j:<15} {len(ds):3d} {sum(ds):+6.2f}  {rule[:110]}")
    tot = [float(o["d"]) for o in out if o["category"] == cat]
    lines.append(f"   total           {len(tot):3d} {sum(tot):+6.2f}")
(OUT / "loop07_noprediction_judgments_output.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
