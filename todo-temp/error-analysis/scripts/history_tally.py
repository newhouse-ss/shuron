"""Offline check of where the family-history rule came from: did rounds whose prompts showed the gold label write
the rule differently from rounds that did not?

Offline, no API calls. For each of the 44 rounds of the 20 Haiku loops, the rewritten guideline (the round's
candidate) is coded by hand for what it says about a single named disease after "a family history of" (gold in
development document 10196379: SpecificDisease). HISTORY below holds the code, the line, and a phrase the script
checks is on that line. Codes were read from every candidate line that mentions "histor" plus the lines they point
to; a rule that covers the phrase without that word would be missed.

Exposure: the rewrite prompt never listed the label (0 of 44, rule_chain.py B), so the only channel that showed the
gold label is the analysis prompts' error examples (7 rounds). The direction before the round is the direction of
the guideline the loop held (the last kept candidate, or the original guideline, which has no such rule).

Writes history_tally_output.txt.
"""

from __future__ import annotations

import json
import re
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"

M, S, N, X = "Modifier", "Specific", "no rule", "other"
HISTORY = {  # (loop, round): (code, line in the candidate, phrase on that line)
    ("topk1_loop01", 1): (N, None, None),
    ("topk1_loop02", 1): (M, 53, '"family history of ovarian cancer" → **Modifier**'),
    ("topk1_loop03", 1): (M, 40, "It is annotated as **Modifier** (Section 3)"),
    ("topk1_loop04", 1): (M, 195, "“ovarian cancer” remains **Modifier**"),
    ("topk1_loop05", 1): (N, None, None),
    ("topk1_loop05", 2): (M, 63, "keeps its existing treatment (Modifier under Section 3)"),
    ("topk1_loop05", 3): (M, 63, "keeps its existing treatment (Modifier under Section 3)"),
    ("topk1_loop06", 1): (M, 191, "is a complement of the non-person noun “history”"),
    ("topk1_loop07", 1): (N, None, None),
    ("topk1_loop07", 2): (N, None, None),
    ("topk1_loop07", 3): (N, None, None),
    ("topk1_loop07", 4): (N, None, None),
    ("topk1_loop08", 1): (N, None, None),
    ("topk1_loop09", 1): (X, 31, "The existing label is kept."),
    ("topk1_loop10", 1): (M, 56, "or as a history or risk complement"),
    ("topk4_loop01", 1): (N, None, None),
    ("topk4_loop01", 2): (N, None, None),
    ("topk4_loop01", 3): (M, 243, '"…a family history of ovarian cancer…" → "ovarian cancer" as **Modifier**'),
    ("topk4_loop01", 4): (M, 296, '"…a family history of ovarian cancer…" → "ovarian cancer" as **Modifier**'),
    ("topk4_loop01", 5): (S, 334, '"…a family history of ovarian cancer…" → "ovarian cancer" as **Specific Disease**'),
    ("topk4_loop01", 6): (S, 383, '"…a family history of ovarian cancer…" → "ovarian cancer" as **Specific Disease**'),
    ("topk4_loop02", 1): (M, 91, "and are annotated as **Modifier**"),
    ("topk4_loop02", 2): (M, 161, "When they name a single disease, they are annotated as **Modifier**"),
    ("topk4_loop02", 3): (M, 209, "When they name a single qualified disease, they are annotated as **Modifier**"),
    ("topk4_loop02", 4): (S, 241, "is annotated as **Specific Disease**"),
    ("topk4_loop03", 1): (M, 217, "**Modifier**, even though “ovarian” fixes an anatomical site"),
    ("topk4_loop04", 1): (M, 249, "“ovarian cancer” = **Modifier** (rule 3)."),
    ("topk4_loop04", 2): (S, 118, '"ovarian cancer" is **Specific Disease**'),
    ("topk4_loop04", 3): (S, 165, '"ovarian cancer" is **Specific Disease**'),
    ("topk4_loop05", 1): (M, 161, "the named disease is a **Modifier**"),
    ("topk4_loop05", 2): (M, 226, "the named disease is a **Modifier**"),
    ("topk4_loop06", 1): (N, None, None),  # line 30 only keeps it out of the patient-anchored rule
    ("topk4_loop06", 2): (M, 340, "“ovarian cancer” is **Modifier**. It appears in a family-history construction"),
    ("topk4_loop06", 3): (M, 396, '"ovarian cancer" is **Modifier**. It appears in a family-history construction'),
    ("topk4_loop07", 1): (M, 66, "are annotated as **Modifier**"),
    ("topk4_loop07", 2): (M, 110, "while “a family history of ovarian cancer” annotates “ovarian cancer” as **Modifier**"),
    ("topk4_loop08", 1): (M, 237, "“ovarian cancer” = **Modifier** in both"),
    ("topk4_loop08", 2): (M, 300, "“ovarian cancer” in “a family history of ovarian cancer” = **Modifier**"),
    ("topk4_loop09", 1): (M, 276, "“ovarian cancer” = **Modifier** in both"),
    ("topk4_loop09", 2): (M, 132, "“a family history of ovarian cancer” → “ovarian cancer” = **Modifier**"),
    ("topk4_loop09", 3): (M, 38, "“a family history of ovarian cancer” → “ovarian cancer” = **Modifier**"),
    ("topk4_loop10", 1): (M, 99, "“a family history of ovarian cancer”: “ovarian cancer” is **Modifier**."),
    ("topk4_loop10", 2): (M, 148, "“a family history of ovarian cancer”: “ovarian cancer” is **Modifier**."),
    ("topk4_loop10", 3): (M, 179, "“a family history of ovarian cancer”: “ovarian cancer” is **Modifier**."),
}

text = json.loads((TRAIN / "10196379.json").read_text(encoding="utf-8"))["text"]
b = re.search(r"history of ovarian cancer", text).start() + len("history of ")
e = b + len("ovarian cancer")
ctx = re.escape(text[max(0, b - 25):b].split("\n")[-1][-15:])
shown = re.compile(r'\(Doc: 10196379\.json\):\nSnippet: "[^"]*' + ctx + r'[^"]*"\nGold: \w+, LLM: \w+\nEntity Text: "' + re.escape(text[b:e]) + '"')

rows = []
right_before = {}  # 10/30: was the mention labelled right (Specific) in the development run before the rewrite?
for folder in sorted(OUT.glob("20261022_haiku-xhigh_topk*_loop*")):
    loop = folder.name.split("_", 2)[2]
    held = N  # the original guideline has no family-history rule
    for it in sorted((folder / "rounds").glob("iteration_*")):
        r = int(it.name.split("_")[1])
        snap = json.loads((it / "snapshot.json").read_text(encoding="utf-8"))
        code, line, phrase = HISTORY[(loop, r)]
        if line:
            cand = snap["guidelines_candidate"].replace("\r\n", "\n").split("\n")
            assert phrase in cand[line - 1], (loop, r, line)
        exposed = shown.search("".join(p.read_text(encoding="utf-8") for p in it.glob("infer_discrepancy_patterns_*.txt"))) is not None
        right_before[(loop, r)] = any(d["start"] == b and d["end"] == e and d["label"] == "SpecificDisease"
                                      for fd in snap["diagnostics_before"]["files"] if fd["filename"] == "10196379.json"
                                      for d in fd["study_denotations"])
        rows.append((loop, r, "kept" if snap["improved"] else "rejected", exposed, held, code, line))
        if snap["improved"]:
            held = code
assert len(rows) == len(HISTORY) == 44

out = ["Family-history rule in each round's rewritten guideline (candidate), by whether the analysis prompt showed the gold label",
       f"   {'loop':<13} {'round':>5} {'decision':<9} {'gold shown':<10} {'before':<9} {'candidate':<9} line"]
for loop, r, kept, exp, before, code, line in rows:
    out.append(f"   {loop:<13} {r:>5} {kept:<9} {'yes' if exp else 'no':<10} {before:<9} {code:<9} {line or '-'}")


def switched(rs):
    return sum(1 for x in rs if x[5] == S), len(rs)


had_mod = [x for x in rows if x[4] == M]
a, n1 = switched([x for x in had_mod if x[3]])
c, n2 = switched([x for x in had_mod if not x[3]])
# one-sided Fisher exact test: chance that all switches fall in the shown group at least this often
k, n = a + c, n1 + n2
p = sum(comb(n1, i) * comb(n2, k - i) for i in range(a, min(k, n1) + 1)) / comb(n, k)
out.append(f"\nRounds that started from a Modifier rule: switched to Specific when the gold label was shown {a} of {n1}; "
           f"when it was not {c} of {n2} (one-sided Fisher exact p = {p:.3f})")
first = [x for x in rows if x[4] == N and x[5] != N]
out.append(f"Rounds that wrote a family-history rule where the guideline had none: {len(first)}; Modifier {sum(1 for x in first if x[5] == M)}, "
           f"Specific {sum(1 for x in first if x[5] == S)}, other {sum(1 for x in first if x[5] == X)}; "
           f"gold label shown in {sum(1 for x in first if x[3])} of them")
out.append(f"Gold label shown and the rule kept as Modifier: {', '.join(f'{x[0]} r{x[1]}' for x in had_mod if x[3] and x[5] == M)}")

# 10/30: a mention that was labelled right before the rewrite is not a discrepancy case, so showing every discrepancy
# case would not have shown its gold in that round
out.append(f"Rounds that wrote a family-history rule where the guideline had none: the mention was labelled right (Specific) before the rewrite in "
           f"{sum(right_before[(x[0], x[1])] for x in first)} of {len(first)}")
wrong = [x for x in rows if not right_before[(x[0], x[1])]]
out.append(f"All 44 rounds: the mention was wrong before the rewrite in {len(wrong)}; shown with its gold in the analysis prompt in "
           f"{sum(1 for x in wrong if x[3])} of those")
(HERE / "history_tally_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
