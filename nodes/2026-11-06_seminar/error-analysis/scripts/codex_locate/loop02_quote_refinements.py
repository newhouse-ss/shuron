"""Serialize explicit reader-selected sentence spans, without locating or matching."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'outputs/bar_clause_pilot/codex_locate/outputs/top4_loop02_locate.jsonl'
rows = [json.loads(x) for x in PATH.read_text(encoding='utf-8').splitlines()]

def select(targets, text):
    for row, quote in targets:
        rows[row-1]['quotes'][quote]['quote'] = text

PRENOMINAL = 'A multiword disease name, or an abbreviation whose expansion names a disease defined earlier in the text, that directly precedes a head noun is annotated as **Modifier**, provided the span is not coordinated (Section 2).'
GENE_OR_CLINICAL = PRENOMINAL + ' The head noun and any following nomenclature tokens are left unannotated. This applies whether the head denotes a clinical or population entity (e.g., “ovarian cancer cases,” “fragile X syndrome patients”) or a gene, protein, or gene symbol (e.g., “ancient SLS genes,” where “SLS” is defined earlier in the abstract; “breast cancer susceptibility gene 1,” where “breast cancer” is the Modifier and “susceptibility gene 1” is not annotated).'
select([(r,0) for r in [5,20,32,47,53,62,65,69,80,92,96,97,99,107,108,110,112,115,146,148,152,177,197,208,209,216,217,229,230,232,233,234,242]], PRENOMINAL)
select([(r,0) for r in [6,9,21,27,36,45,46,48,52,57,60,68,85,98,100,101,106,109,111,119,120,133,134,153,169,170,171,172,178,182,183,184,193]], GENE_OR_CLINICAL)

HEAD = 'If the disease-denoting span is itself the nominal head of its noun phrase, including when that noun phrase is the complement of a preposition such as “of” or “with,” or is a clausal subject or object that refers to the disease as an entity, label the span **Specific Disease**.'
select([(1,0),(3,1),(7,2),(10,1),(11,1),(19,1),(28,0),(67,0),(72,1),(73,1),(74,1),(75,1),(76,1),(77,1),(78,1),(81,1),(86,2),(116,1),(117,0),(121,0),(122,1),(130,1),(136,0),(138,1),(149,0),(150,1),(173,0),(174,0),(175,0),(176,1),(186,1),(187,0),(191,1),(194,0),(220,0),(221,1),(222,1),(224,1),(231,0),(244,0)], HEAD)

ANCHOR = 'If a disease noun phrase has a **generic category head** (e.g., *infection*, *inflammation*, *syndrome*, *disorder*) and that head is preceded, within the same noun phrase, by a premodifier naming a **causal agent** (organism, gene, toxin) or an **anatomic locus**, label the entire phrase **Specific Disease**.'
EPONYM = ANCHOR + ' The anchor fixes one nosological entity. The same applies when the phrase contains a proper name, eponym, or acronym.'
select([(30,0),(72,0),(73,0),(74,0),(75,0),(76,0),(77,0),(78,0),(116,0),(129,1),(138,0),(165,0),(166,0),(176,0),(211,0),(218,0),(221,0),(222,0),(224,0)], ANCHOR)
select([(11,0),(19,0),(38,1),(86,0),(186,0),(238,0)], EPONYM)

GENERIC = 'A disease span whose head is an unqualified generic category noun, a superordinate term naming a class of conditions rather than one named condition, is labeled **Disease Class**.'
select([(23,0),(24,0),(29,0),(31,0),(34,0),(39,0),(40,0),(41,0),(82,1),(83,1),(131,1),(132,0),(154,0),(192,0),(215,1),(223,0),(225,0),(227,0),(236,0)], GENERIC)
INHERITANCE = 'Inheritance-pattern descriptors (“autosomal recessive,” “X-linked”) are not qualifiers of this kind. “Autosomal recessive disease” and “X-linked mental retardation syndrome” remain **Disease Class** (Examples 3, 10, 12).'
for row, index in [(12,0),(63,0),(66,0),(79,0),(102,0),(124,0),(237,0)]:
    q = rows[row-1]['quotes'][index]
    extra = dict(q, quote=INHERITANCE, line_start=136, line_end=136, condition_words='Inheritance-pattern descriptors')
    q.update(quote=GENERIC, line_start=134, line_end=134, condition_words='')
    if extra not in rows[row-1]['quotes']:
        rows[row-1]['quotes'].append(extra)

select([(8,1),(128,1)], 'Premodifiers of the molecular name (e.g., “complement component” in “deficiency of complement component C7”) are inside the span.')
select([(125,2),(126,1),(127,1),(219,2),(226,1)], 'Determiners and descriptors of the head state (e.g., “the,” “complete,” “heterozygous”) are outside it.')
select([(8,2),(128,0),(219,1)], 'A named disorder in premodifier form (e.g., “C7 deficiency,” “G6PD deficiency”) is a **Specific Disease** under Section 1 without further analysis.')
for row, index in [(8,2),(128,0),(219,1)]:
    rows[row-1]['quotes'][index].update(line_start=117, line_end=117)

ABBREVIATION = 'Abbreviation definitions such as “Huntington disease” (“HD”) are separated into two annotated mentions (one for the long form, one for the abbreviation).'
select([(4,0),(43,0),(51,0),(87,0),(89,2),(90,0),(95,0),(105,0),(123,0),(187,1),(243,1)], ABBREVIATION)
select([(15,1)], 'Parenthetical aliases that restate a disorder already named in the same phrase are likewise separate synonymous mentions, each with its own label (e.g., “Coats’ disease of the retina (unilateral retinal telangiectasis)”; Example 34).')

MINIMUM = 'Use the smallest span necessary to include all tokens expressing the most specific form of the disease.'
select([(7,3),(11,2),(18,1),(19,2),(38,2),(135,1),(201,1),(207,1),(212,1),(220,1),(228,1)], MINIMUM)

PATH.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')
