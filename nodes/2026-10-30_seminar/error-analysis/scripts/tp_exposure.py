"""Would listing every true positive in the rewrite prompt make hard-coding worse? What the Haiku loops show.

Offline, no API calls. For each of the 44 rounds of the 20 Haiku loops, every development gold mention string
(at least 4 characters, as in reproduction/measure_hardcoding.py) that the guideline before the round does not
contain is put in one class, by what the rewrite step's prompt (rounds/iteration_NN/refine_guidelines.txt) showed:

  listed      in the "do not break" block's MATCHED ANNOTATIONS, with its label (capped at 5 per document)
  principle   not listed, but quoted in the round's new moderation principles (which come from the error clusters)
  text only   not listed or quoted, but in the full text of a "do not break" document
  not shown   only in development documents the prompt does not show

A string is "copied" when the round's candidate guideline contains it. Copy rates per class answer the question:
removing the cap moves strings from "text only" to "listed".

Also, per changed final guideline: how many development strings it copied in total, against its development and
validation F1. And how much of the development gold the five shown documents hold, i.e. how much of the answer key
an uncapped list would put on screen for the same 10 documents the keep rule scores.

Writes tp_exposure_output.txt.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
MIN_LENGTH = 4

DEV = [d["filename"] for d in json.loads((OUT / "20261022_haiku-xhigh_topk4_loop08" / "inputs" / "sampled_train_documents.json").read_text(encoding="utf-8"))]
gold = {}
for f in DEV:
    d = json.loads((TRAIN / f).read_text(encoding="utf-8"))
    gold[f] = (d["text"], [(x["span"]["begin"], x["span"]["end"], x["obj"]) for x in d["denotations"]])
dev_strings = {gold[f][0][b:e] for f in gold for (b, e, _) in gold[f][1]}
dev_strings = {s for s in dev_strings if len(s) >= MIN_LENGTH}
n_mentions = sum(len(g) for _, g in gold.values())

# "text only" is split by the run before the rewrite: right but cut by the cap (removing the cap would list it),
# or wrong (removing the cap alone would not list it)
CLASSES = ("listed", "principle", "text only, right but cut by the cap", "text only, wrong before the rewrite", "not shown")
eligible, copied = Counter(), Counter()
docs_with_tp, docs_shown = [], []
not_shown_docs = Counter()
by_method = {m: (Counter(), Counter()) for m in ("top-1", "top-4")}
shown_mentions, listed_mentions = [], []
examples = defaultdict(list)
rounds = 0
for folder in sorted(OUT.glob("20261022_haiku-xhigh_topk*_loop*")):
    method = "top-1" if "topk1" in folder.name else "top-4"
    for it in sorted((folder / "rounds").glob("iteration_*")):
        rounds += 1
        snap = json.loads((it / "snapshot.json").read_text(encoding="utf-8"))
        before, cand = snap["guidelines_before"], snap["guidelines_candidate"]
        prompt = (it / "refine_guidelines.txt").read_text(encoding="utf-8")
        block = prompt.split("DO NOT BREAK")[-1]
        files = dict(re.findall(r"^FILE: (\S+)\n(.*?)(?=^FILE: |\Z)", block, re.M | re.S))
        listed = {t for body in files.values() for t in re.findall(r'^- \w+ \[\d+, \d+\] "([^"]*)"', body, re.M)}
        principles = snap["moderation_principle"]
        shown_text = " ".join(gold[f][0] for f in files if f in gold)
        right_before = {p["reference_text"] for fd in snap["diagnostics_before"]["files"] if fd["filename"] in files for p in fd["matched_pairs"]}
        with_tp = [fd["filename"] for fd in snap["diagnostics_before"]["files"] if fd["matched_pairs"]]
        docs_with_tp.append(len(with_tp))
        docs_shown.append(len(files))
        not_shown_docs.update(f for f in DEV if f not in files)
        shown_mentions.append(sum(len(gold[f][1]) for f in files if f in gold))
        listed_mentions.append(sum(len(re.findall(r"^- \w+ \[", body, re.M)) for body in files.values()))
        for s in dev_strings:
            if s in before:
                continue
            c = ("listed" if s in listed else "principle" if s in principles
                 else ("text only, right but cut by the cap" if s in right_before else "text only, wrong before the rewrite") if s in shown_text
                 else "not shown")
            hit = s in cand
            eligible[c] += 1
            copied[c] += hit
            by_method[method][0][c] += 1
            by_method[method][1][c] += hit
            if hit and len(examples[c]) < 12 and s not in examples[c]:
                examples[c].append(s)

out = [f"Development gold: {n_mentions} mentions in 10 documents, {len(dev_strings)} distinct strings of at least {MIN_LENGTH} characters",
       f"Rounds: {rounds}. The five 'do not break' documents hold {statistics.mean(shown_mentions):.1f} gold mentions per round "
       f"(range {min(shown_mentions)}-{max(shown_mentions)}, {statistics.mean(shown_mentions) / n_mentions:.0%} of the development gold); "
       f"the capped list shows {statistics.mean(listed_mentions):.1f} of them",
       "",
       "Copy rate by what the rewrite prompt showed (string x round pairs; strings already in the guideline before the round excluded)",
       f"   {'class':<37} {'eligible':>8} {'copied':>7} {'rate':>6}   {'top-1 rate':<12} {'top-4 rate':<12} examples of copied strings"]
for c in CLASSES:
    e, k = eligible[c], copied[c]
    rates = [f"{by_method[m][1][c] / by_method[m][0][c]:.0%} of {by_method[m][0][c]}" if by_method[m][0][c] else "-" for m in ("top-1", "top-4")]
    out.append(f"   {c:<37} {e:>8} {k:>7} {k / e if e else 0:>6.0%}   {rates[0]:<12} {rates[1]:<12} {', '.join(examples[c][:6])}")

# what removing the cap would change: strings that were right but cut would become listed
rate = {c: copied[c] / eligible[c] for c in CLASSES if eligible[c]}
cut = "text only, right but cut by the cap"
extra = (rate["listed"] - rate[cut]) * eligible[cut] / rounds
out.append("\nOne parameter, n_examples = 5, sets three limits (iterative.py): documents in the block (line 399), matched "
           "annotations listed per document (line 397), error examples per cluster in the analysis prompts (line 379)")
out.append(f"1. Per-document limit only: if every string that was right but cut were listed and copied at the 'listed' rate: "
           f"{extra:+.1f} copied strings per round ({eligible[cut] / rounds:.1f} such strings per round)")
shown_rate = (copied["listed"] + copied[cut]) / (eligible["listed"] + eligible[cut])
out.append(f"2. Document limit: documents with at least one correct mention before the rewrite {statistics.mean(docs_with_tp):.1f} per round "
           f"(range {min(docs_with_tp)}-{max(docs_with_tp)}), shown {statistics.mean(docs_shown):.1f}; never shown in any round: "
           f"{', '.join(f for f in DEV if not_shown_docs[f] == rounds)}")
out.append(f"   'not shown' strings per round {eligible['not shown'] / rounds:.1f}; if they were shown and copied at the rate of shown strings that "
           f"were right before the rewrite ({shown_rate:.0%}): about {shown_rate * eligible['not shown'] / rounds:+.1f} copied strings per round "
           f"(extrapolation), and the block would cover all {n_mentions} development gold mentions instead of {statistics.mean(shown_mentions):.1f}")
rj = json.loads((HERE / "rounds.json").read_text(encoding="utf-8"))
targets = [n for r in rj for (n, _) in r["targets"].values()]
over = [n for n in targets if n > 5]
out.append(f"3. Error-example limit: targeted clusters {len(targets)}, with more than 5 errors {len(over)} "
           f"(their sizes {sorted(over)}); error examples not shown to the analysis step: {sum(n - 5 for n in over)}")

# final guidelines: copied development strings, development and validation F1
out.append("\nChanged final guidelines: development strings copied (not in the original guideline), dev F1, validation F1")
orig = (OUT / "20261022_haiku-xhigh_topk4_loop08" / "inputs" / "initial_guidelines.txt").read_text(encoding="utf-8")
rows = []
for folder in sorted(OUT.glob("20261022_haiku-xhigh_topk*_loop*")):
    final = (folder / "final" / "final_guidelines.txt").read_text(encoding="utf-8")
    if final.replace("\r\n", "\n") == orig.replace("\r\n", "\n"):
        continue
    absorbed = sorted(s for s in dev_strings if s not in orig and s in final)
    run = json.loads((folder / "final" / "iterative_refinement_run.json").read_text(encoding="utf-8"))
    m = json.loads((folder / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    absorbable = sum(1 for s in dev_strings if s not in orig)
    rows.append((folder.name.split("_", 2)[2], len(absorbed), absorbable, run["final_summary"]["overall_f1"], m["f1"], len(final)))
    out.append(f"   {rows[-1][0]:<13} copied {len(absorbed):>3} of {absorbable} ({len(absorbed) / absorbable:.0%})   dev F1 {rows[-1][3]:.3f}   "
               f"validation F1 {m['f1']:.4f}   gap {rows[-1][3] - m['f1']:+.3f}   guideline {len(final):,} chars")


def ranks(xs: list) -> list:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[order[k]] = (i + j) / 2
        i = j + 1
    return rk


a, dev, val = [r[1] for r in rows], [r[3] for r in rows], [r[4] for r in rows]
out.append(f"   Spearman, copied strings against: dev F1 {statistics.correlation(ranks(a), ranks(dev)):+.2f}; validation F1 "
           f"{statistics.correlation(ranks(a), ranks(val)):+.2f}; dev minus validation gap {statistics.correlation(ranks(a), ranks([d - v for d, v in zip(dev, val)])):+.2f}"
           f" (n = {len(rows)})")

(HERE / "tp_exposure_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
