# How to code error causes: tutorial for the second coder

Not used. On 10/24 the user dropped the second-coder check. The analysis that was run is `20261024_error_analysis_report.md`.

Draft, 2026-10-24. Follows `20261024_analysis_rules.md` §2.3 as sent for review. If the review changes the rules, this tutorial changes with them before you start.

## What you do and why

- You get a sheet with 50 errors from the validation runs, and you give each one a cause from 1 to 6.
- Claude codes the same errors separately. Neither of you sees the other's codes until both are done.
- The two codings are compared with Cohen's kappa: agreement corrected for chance, where 1 means perfect agreement and 0 means chance level. If kappa is below 0.6, the cause definitions are unclear: they are revised once, and everything is recoded.
- You see no run, method, loop or score, so your codes cannot follow expectations about "good" or "bad" loops.
- Time: about 2 to 5 minutes per error, so 2 to 4 hours for 50 (Claude's estimate). Stop at about 5 minutes on any one item: code it 6 (unclear) and write why.

## What the sheet looks like

An `.xlsx` file, one row per error, plus a folder of guideline files named by code (`G07.txt` and so on).

| Column | Content | You |
| --- | --- | --- |
| `item` | Random ID | read |
| `kind` | missed / extra / subtype / boundary / unpaired overlap | read |
| `context` | About 60 characters each side, mention in [brackets] | read |
| `gold` | Gold text and subtype, or "none" for an extra | read |
| `prediction` | Predicted text and subtype, or "none" for a missed mention | read |
| `rationale` | The model's reason and cited section (empty for a missed mention) | read, as a hint only |
| `guideline` | Code of the guideline this run used | open that file |
| `precedent` | How training gold annotates the same string: "k of n as predicted" | read |
| `cause` | 1 to 6 | **fill** |
| `rule` | Section and a short quote of the rule you used | **fill** for causes 2, 3, 4 |
| `note` | Anything unusual; required for cause 6 | fill if needed |

## The decision, in two steps

**Step 1. Is the gold itself doubtful?** Look at `precedent`. If the training gold annotates the same string the way the prediction does in more than half of at least 3 occurrences, and the string means the same thing here, code **1** and stop. If the string means something else in this context, ignore the precedent.

**Step 2. What does the guideline say?** Open the guideline file. Search (Ctrl+F) for the mention's words and its head noun, and check "What to Annotate", "What NOT to Annotate" and "Examples". Answer two yes/no questions:

- **A.** Does a rule or a listed example cover the **gold** annotation?
- **B.** Does a rule or a listed example cover the **prediction**? For a missed mention, the prediction is "not annotated", so B asks whether a rule excludes it. For an extra mention, B asks whether a rule includes it.

| A (gold covered) | B (prediction covered) | Cause |
| --- | --- | --- |
| no | yes | **2** The rule leads to the error |
| yes | no | **3** The model ignores the rule |
| yes | yes | **4** The guideline contradicts itself |
| no | no | **5** The guideline is silent |
| cannot tell | cannot tell | **6** Unclear (write why) |

## Four conventions

1. **Literal reading.** A rule "covers" a mention only through its own words, or through a listed example with the same construction (for example, "X patients" is the same construction as "colorectal cancer families"). Not through what the annotators probably meant.
2. **Specific beats general.** The general definitions in "What to Annotate" 1 do not count as support when a more specific rule addresses the case: Modifier (3), Composite Mention (2), minimum span (5), or any "What NOT" item.
3. **An open choice decides nothing.** A rule that leaves the choice to the annotator ("may or may not include ... depending on the annotator", Examples 2, 14, 16) counts as no rule for that question.
4. **For a boundary error,** ask A and B about the tokens that differ, not about the whole mention.

## Five worked examples

All five come from the development documents, annotated with the original guideline (`data/guidelines/ncbi_disease_guidelines.txt`). None will appear on your sheet. Real items can be less clear-cut. Try the first one yourself before reading the answer.

**Example 1.** "...frequency estimates of [breast cancer] susceptibility gene 1 ( BRCA1 ) germline alterations..."
Gold: "breast cancer", Modifier. Prediction: none (missed).
- A: yes. "What to Annotate" 3, a disease name modifying a noun phrase; same construction as its example "colorectal cancer families".
- B: no rule excludes disease names inside gene names.
- **Cause 3.** Rule: "What to Annotate 3, 'colorectal cancer families'".

**Example 2.** "...characterized by ichthyosis , mental retardation , [spasticity] , and deficient activity of..."
Gold: "spasticity", DiseaseClass. Prediction: none (missed).
- A: yes. Example 11 annotates symptom terms in a phenotype list ("convulsive disorders", "motor retardation") as Disease Class.
- B: no rule excludes symptoms.
- **Cause 3.** Rule: "Example 11".

**Example 3.** "...a [Tay-Sachs disease] ( TSD ) causing mutation in the intron 9 donor splice site..."
Gold: "Tay-Sachs disease", SpecificDisease. Prediction: "Tay-Sachs disease", Modifier (subtype error).
- B: yes. "What to Annotate" 3 covers a disease name that modifies a noun ("causing mutation").
- A: only the general definition in "What to Annotate" 1, which does not count under convention 2.
- **Cause 2**, assuming the precedent column shows no majority. Rule: "What to Annotate 3".

**Example 4.** "...the large variety of mutant genotypes associated with [PAH deficiencies] ."
Gold: SpecificDisease. Prediction: DiseaseClass (subtype error).
- B: yes. The Disease Class definition, "a family of multiple specific diseases", covers a plural set of genotype-specific deficiencies.
- A: yes. Example 6 makes "C7 deficiency", an enzyme deficiency, a Specific Disease: the same construction.
- **Cause 4.** Rules: "What to Annotate 1 (Disease Class)" against "Example 6".

**Example 5.** "...four generations showed [heterozygous deficiency of C7] in five members."
Gold: "deficiency of C7". Prediction: "heterozygous deficiency of C7", same subtype (boundary error).
- The differing token is "heterozygous". Examples 14 and 16 leave qualifiers such as "acute" and "inherited" to the annotator, so by convention 3 there is no rule. "Minimum necessary span" (5) does not say whether a genotype word belongs to "the most specific form".
- **Cause 5.**

## Before you start

1. Read the original guideline once, about 10 minutes. Most rows use it. Changed guidelines are longer, so search them rather than read them.
2. Code the five examples above without looking at the answers, then compare. These are practice and are not counted.
3. Code the 50 rows in sheet order. Don't discuss items with Claude until the sheet is returned.
4. Return the file. Claude computes kappa with its 95% CI, and a table of where the two coders disagree, then reports both.
