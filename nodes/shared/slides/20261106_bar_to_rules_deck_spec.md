# Deck spec: from bars to guideline rules (seminar 2026-11-06)

Build a 10-slide English deck exactly from the text below. Do not add, remove or reword content, except to shorten a line that does not fit; never add slides (no backup, no appendix).

## Files

- Template: `H:/Git/research/修論/presentations/academic-serif-template/Academic_Serif_B.pptx` (same template and title-slide layout as `presentations/20261030_error_analysis_en.pptx`).
- Output: `H:/Git/research/修論/presentations/20261106_bar_to_rules_en.pptx`.
- Builder script: `nodes/shared/slides/build_bar_to_rules_slides.py` (project repo). Reuse helpers from `nodes/shared/slides/build_error_analysis_slides.py` (fonts, colors, chart styling) and the `r:id` fix in `nodes/shared/slides/build_faldh_slides.py` (around line 735: write every `<p:sldId>` with the literal `r:id`, otherwise ONLYOFFICE shows an empty deck). Write chart XML in conventional form (explicit boolean `val`).

## Style rules

- English; 6x6 (at most 6 lines of body text per slide, short lines). Titles are the claims below, verbatim.
- Quoted annotation text and guideline text are verbatim; mark the annotated span in brackets as given.
- Speaker notes: put the "Notes" text of each slide into the slide's notes.
- No codes or abbreviations beyond those defined on the slides; no pronouns without a clear referent.

## Slides

### 1. Title slide
- Title: From bars to guideline rules: tracing annotations back to the guideline
- Subtitle: Error analysis: method and first results
- Date: 2026-11-06. Other lines (name, affiliation) as on slide 1 of the 2026-10-30 deck.

### 2. Which guideline rules are behind each bar?
- Left: the bar chart of slide 5 of `presentations/20261030_error_analysis_en.pptx` (title "F1 follows SpecificDisease losses, not Modifier gains"). Rebuild it with the code in `build_error_analysis_slides.py` (same data and colors). Fallback: convert that deck to PDF with ONLYOFFICE (see Verification), crop the chart from page 5, insert it as a picture.
- Right, body:
  - One bar: one refined guideline, one entity type
  - Bar value: strict TP minus the baseline mean
  - Baseline: 19 runs with the original guideline
  - Goal: candidate rules for good guideline writing
- Notes: Strict TP means same span and same type as the gold annotation. A refined guideline is the final guideline of one refinement loop; a loop is a sequence of rounds, and in the top-4 method each round merges four principles. On 2026-10-30 the professor asked to connect each guideline's results to its rules. Today: the method, and first results for one guideline.

### 3. Four steps lead from a bar to candidate rules
- A left-to-right flow of five boxes drawn with native shapes and arrows; under each box a status label:
  1. Split each bar into the mentions behind it — Done
  2. Find the guideline sentence each annotation relied on — Done: 2,918 annotations
  3. Group the sentences into rules — Running
  4. Sum the differences rule by rule — Running: top-4 loop07 done
  5. Controlled re-annotation of candidate rules — Planned
- Draw box 5 visually apart (for example dashed outline), since it tests what boxes 1 to 4 propose.
- Notes: Steps 1 to 4 propose candidate rules from the saved annotations without new model calls. Step 5 re-annotates with a candidate rule removed or added, to test whether that rule changes the annotations.

### 4. Each mention's difference from the baseline adds up to the bar
- Body line: Difference = this run (1 right, 0 not) − share of baseline runs right
- Table (columns: Mention, Gold type, Baseline runs right, This run, Difference):
  - "ability to produce [metastatic tumors] in nude mice" | Disease Class | 19 of 19 | missed | −1
  - "Germline [VHL] gene mutations predispose" | Modifier | 0 of 19 | right | +1
- Body lines under the table:
  - All Modifier mentions add up to the Modifier bar: +40.7
  - Predictions without a gold mention: same rule, "predicted" instead of "right"
- Notes: Both mentions come from the run with the guideline of top-4 loop07, the seventh loop of the top-4 method. The bar is a difference of two counts, so it splits exactly into one difference per mention. One mention alone can be noise; differences are read only after summing them per rule.

### 5. For every annotation, the model wrote a citation and a rationale
- Table (columns: Text, Label, Citation, Rationale):
  - "an 80 % risk of [breast cancer]" | Modifier | "Section 3 - Context and population frames" | "The disease name is the complement of the context noun risk in 'risk of breast cancer', so it is a Modifier rather than a standalone disease."
  - "Germline [VHL] gene mutations" | Modifier | "§3 Disease premodifier within a gene or protein designation" | "Disease abbreviation premodifies the gene head 'gene' in 'VHL gene mutations', matching the DTD gene example."
- Body lines:
  - Citations are free text, often only a section
  - Rationales describe the reason; they rarely quote the guideline
- Notes: The annotation prompt asks for a rationale and the corresponding guideline section with every annotation. Both examples are from the run with the top-4 loop07 guideline.

### 6. Step 2 matches citation and rationale to one guideline sentence
- Four numbered rows, each with the example "an 80 % risk of [breast cancer]":
  1. Citation: where to look → "Section 3 - Context and population frames"
  2. Rationale: condition and label → complement of "risk", so Modifier
  3. The sentence there with that condition and label (guideline line 65): "A disease name that premodifies, or is the complement of, a context or population noun (such as cases, population, history, risk, or incidence) is annotated Modifier." Highlight "is the complement of" and "Modifier".
  4. Record: the sentence, the condition used ("is the complement of"), its use: reason for the label
- Footer line: Uses: reason for the label · cited as not applicable · mentioned only
- Notes: The matching sees the text, the label, the citation and the rationale, but not whether the annotation is correct. If the cited place does not state the condition and label in the rationale, the sentence is searched in the whole guideline (next slide). Every recorded sentence is checked word for word against the guideline.

### 7. When the citation is imprecise, the rationale decides
- Table (columns: Citation, Rationale says, Sentence recorded as the reason):
  - "Section 1.6(iii)" (no item 1.6(iii); top-4 loop01) | "fixed site-plus-category compound" for "[breast carcinoma]" | "... through (i) an eponym, (ii) an acronym of a named disease, (iii) a fixed nomenclature compound in which the modifier is attached directly to the head ..."
  - "§3 gene designation not applied (position)" (top-4 loop07) | "DCC (deleted in [colorectal cancer]) gene": not the leading premodifier, so the gene rule does not apply | "Not applied: (c) The span is not in the leading premodifying position."
  - "Rule 1b(d) unanchored generic frame; Rule 1b(b) negative constraints" (top-4 loop04) | "the [tumours] they develop": a generic statement, a class | "(d) Unanchored, generic frame → Disease Class. An unanchored head noun in a generic frame is a Disease Class." (the cited negative constraint, about items in a list of findings, does not cover this case)
- Body line: All 2,918 annotations that differ from the baseline were matched
- Notes: Row 1: the citation names a sub-item that exists only inside a sentence. Row 2: the reason is the exception, not the gene rule itself. Row 3: one cited part does not describe the case, so it is not recorded as the reason.

### 8. Step 3 groups sentences into rules and counts each condition
- Body lines:
  - A rule: one sentence or list item, condition → action
  - Quotes of the same sentence form one rule
  - Conditions joined by "or" are counted separately
  - Grouping rules were fixed before seeing any difference
- Table (title: "Guideline line 65 of top-4 loop07"; columns: Condition named in the rationale, Annotations):
  - is the complement of | 27
  - premodifies | 15
  - not stated | 3
- Notes: The same sentence is often quoted at different lengths; all such quotes count for one rule. A rule written again elsewhere in the guideline is kept as a separate rule here; the places of a candidate rule are collected before step 5.

### 9. Step 4 sums the differences rule by rule
- Body lines:
  - Gains: mentions this run gets right more often
  - Losses: mentions this run gets wrong more often
  - Extra predictions without gold: counted separately
  - Annotation relying on two rules: counted under both
  - Mentions not annotated: no rationale, listed separately
  - Check: sums equal the bars (top-4 loop07: all three)
- Notes: Gains and losses are sums of the per-mention differences of slide 4, so they are in strict-TP units. A mention the run did not annotate has no citation and no rationale, so it cannot be matched to a rule; for top-4 loop07 these are 25 gold mentions (−8.2) and 37 positions the baseline runs predicted without a gold mention (−8.3).

### 10. top-4 loop07: candidate rules behind its bars
- Table (columns: Rule in the top-4 loop07 guideline, Annotations, Gains, Losses, Extra predictions):
  - Disease premodifier of a gene or protein name → Modifier (line 69) | 60 | +36.0 | −0.1 | 4
  - Context or population noun, "is the complement of" → Modifier (line 65) | 27 | 0 | −26.5 | 0
  - Context or population noun, "premodifies" → Modifier (line 65) | 15 | +6.3 | 0 | 0
  - Composite Mention rule, same as the original guideline (line 48) | 37 | +2.1 | −9.3 | 0
- Body lines:
  - VHL alone: +16.0, from 2 documents
  - These rules are candidates; re-annotation tests them
  - Next: all 11 refined guidelines, then re-annotation
- Notes: Gains and losses are in strict-TP units against the baseline mean. Line 65 helps when the disease name premodifies the noun and hurts when it is the complement: 27 annotations, mostly gold Specific Disease labelled Modifier. Line 69's gain is concentrated: 16.0 of it comes from VHL in two documents. Re-annotation: remove the rule from the refined guideline, or add it to the original guideline, and run with the unchanged guideline in the same batch.

## Verification (must pass before finishing)

1. Convert the deck with ONLYOFFICE: `C:\Program Files\ONLYOFFICE\DesktopEditors\converter\x2t.exe params.xml`, where params.xml is
   `<?xml version="1.0" encoding="utf-8"?><TaskQueueDataConvert><m_sFileFrom>DECK.pptx</m_sFileFrom><m_sFileTo>DECK.pdf</m_sFileTo><m_nFormatTo>513</m_nFormatTo><m_sAllFontsPath>%LOCALAPPDATA%\ONLYOFFICE\DesktopEditors\data\fonts\AllFonts.js</m_sAllFontsPath></TaskQueueDataConvert>` (expand %LOCALAPPDATA%).
2. The PDF must have exactly 10 pages. Rasterize every page (pymupdf; install it into a temporary folder with `pip --target` if missing) and check that no text overflows its box, no table is cut off, and the chart and flow shapes render.
3. Check every slide against the style rules: at most 6 body lines, titles verbatim, no undefined abbreviation.
4. Report: output path, page count, and any line you had to shorten.
