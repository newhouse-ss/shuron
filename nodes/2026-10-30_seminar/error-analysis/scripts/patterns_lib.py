"""Error patterns shared by error_patterns.py, gold_precedent.py and rule_links.py: names, groups, and the
string and label rules that sort one error into one pattern."""

from __future__ import annotations

import re

PATTERNS = {
    "M1": "missed: disease name before a gene or protein word (VHL gene, WAS protein)",
    "M2": "missed: tumor/cancer modifying a non-disease noun (tumor suppressor, tumor cells)",
    "M3": "missed: X-deficient (Atm-deficient mice)",
    "M4": "missed: other modifier (X patients, X families)",
    "M5": "missed: tumor(s)/cancer(s) as a disease class (these tumours, sporadic tumours)",
    "M6": "missed: enzyme or protein deficiency (deficiency of ASPA, diminished GALC activity)",
    "M7": "missed: general word with a qualifier (eye abnormalities, genetic disorder, disorder of skeletal muscle)",
    "M8": "missed: symptom, sign or other",
    "L1": "subtype: gold Modifier, predicted Composite (breast and ovarian cancer families)",
    "L2": "subtype: modifier labeled as a disease (HNPCC kindreds, ACG1B patients)",
    "L3": "subtype: disease labeled as a modifier",
    "L4": "subtype: labeled Composite at the gold span, gold another label",
    "L5": "subtype: Specific labeled DiseaseClass (hereditary breast cancer)",
    "L6": "subtype: DiseaseClass labeled Specific (lipomas, cancers)",
    "L7": "subtype: other",
    "B1": "boundary: prediction inside the gold span (qualifier left out: familial, sporadic; also any other shorter span)",
    "B2": "boundary: prediction covers the gold span (qualifier added: classical, simple; also any other longer span)",
    "B3": "boundary: other",
    "U1": "unpaired: gold mention swallowed by a longer prediction",
    "U2": "unpaired: prediction overlapping a gold mention used elsewhere",
    "X1": "extra: gene or locus symbol taken as a disease (AT region, AKU)",
    "X2": "extra: animal disease or mutant (scurfy, Small eye)",
    "X3": "extra: other (disease forms and types, variant names: infantile form, LA phenotype)",
}
FAMILIES = {
    "disease name used as a modifier, missed": ["M1", "M2", "M3", "M4"],
    "other missed mentions: symptoms, general words, tumors, deficiencies, the rest": ["M5", "M6", "M7", "M8"],
    "span shorter or longer than the gold span": ["B1", "B2"],
    "Modifier against disease or Composite label": ["L1", "L2", "L3"],
    "Specific against DiseaseClass": ["L5", "L6"],
    "Composite label at the gold span, or one prediction over two gold mentions": ["L4", "U1"],
    "extra mentions and other": ["X1", "X2", "X3", "U2", "L7", "B3"],
}
GENE_WORDS = r"(exon|exons|mutant|-mutated|gene|genes|protein|proteins|product|products|mRNA|mRNAs|locus|loci|region|regions|kinase|factor|homolog|homologue|transcript|transcripts|cDNA|allele|alleles|isoform|isoforms|polypeptide|-mediated|-associated|domain|promoter|subunit|sequence)\b"
AFTER_GENE = re.compile(r"^\s*(\)\s*)?(\(\s*[\w-]+\s*\)\s*)?(and\s+[\w-]+\s+)?(tumou?r\s+)?(suppressor\s+)?(locus-associated|" + GENE_WORDS + r")")
TUMOR = {"tumor", "tumour", "tumors", "tumours", "cancer", "cancers", "Tumor", "Tumour", "Cancer"}
GENERAL = re.compile(r"\b(abnormalit\w*|defects?|disorders?|diseases?|deficienc\w*|conditions?|anomal\w*|lesions?|manifestations?|complications?|syndromes?|problems?|dysfunction)$", re.I)
DEFICIENCY = re.compile(r"((?i:deficien)\w*\s+of\s+|diminished\s+\w+\s+activity|defective\s+formation|^[A-Z0-9][A-Za-z0-9]*[\s-]+deficienc)")
ANIMAL = re.compile(r"\b(mice|mouse|murine|rats?|dogs?|cattle)\b")


def pattern(r: dict, after_gold: str, after_pred: str) -> str:
    kind, gl, pl, gt, pt = r["kind"], r["gold_label"], r["pred_label"], r["gold_text"], r["pred_text"]
    if kind == "missed":
        if gl == "Modifier":
            if gt in TUMOR:
                return "M2"
            if gt.lower().endswith("deficient"):
                return "M3"
            if AFTER_GENE.match(after_gold):
                return "M1"
            return "M4"
        head = gt.split(" of ")[0].split()[-1].lower()
        if gt.lower() in {t.lower() for t in TUMOR} or (gl == "DiseaseClass" and head in {"tumors", "tumours", "cancers", "neoplasms"}):
            return "M5"
        if DEFICIENCY.search(gt):
            return "M6"
        if GENERAL.search(gt.split(" of ")[0]) and len(gt.split()) > 1:
            return "M7"
        return "M8"
    if kind == "label":
        if gl == "Modifier" and pl == "CompositeMention":
            return "L1"
        if gl == "Modifier":
            return "L2"
        if pl == "Modifier":
            return "L3"
        if pl == "CompositeMention":
            return "L4"
        if (gl, pl) == ("SpecificDisease", "DiseaseClass"):
            return "L5"
        if (gl, pl) == ("DiseaseClass", "SpecificDisease"):
            return "L6"
        return "L7"
    if kind == "boundary":
        gs, ge, ps, pe = (int(r[k]) for k in ("gold_start", "gold_end", "pred_start", "pred_end"))
        if ps >= gs and pe <= ge:
            return "B1"
        if ps <= gs and pe >= ge:
            return "B2"
        return "B3"
    if kind == "unpaired":
        return "U1" if gt else "U2"
    if pl == "Modifier" and AFTER_GENE.match(after_pred):
        return "X1"
    if ANIMAL.search(r["context"]):
        return "X2"
    return "X3"


def key(r: dict) -> tuple:
    return (r["doc"], r["kind"], r["gold_start"], r["gold_end"], r["gold_label"], r["pred_start"], r["pred_end"], r["pred_label"])
