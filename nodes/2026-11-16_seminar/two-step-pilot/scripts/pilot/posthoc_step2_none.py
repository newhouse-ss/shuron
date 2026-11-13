"""Post hoc, offline: when T's step 2 says NONE, is it dropping gold mentions or extras, and which sections does it cite?

For each step-1 candidate (rebuilt exactly as the run did), the step-2 decision is a type, NONE, or missing.
A candidate "overlaps gold" if any gold mention of the document overlaps it. Counts are means of the 2 runs over
the 200 documents. The cited section is the model's own guideline_section text, cut at 70 characters.
Run from the repository root:
    python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/posthoc_step2_none.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/20261114_posthoc_step2_none_output.txt
"""
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, RUNS, TRAIN, load_inputs, parse_annotations, read_json  # noqa: E402
from llm_guideline_moderation.pubannotation import pubannotation_to_annotations  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20261114_haiku-xhigh_pilot_twostep"
names = read_json(RUN / "manifest.json")["pilot_documents"]
_, entities = load_inputs()
labels = {e.name for e in entities}

kept = Counter()
dropped_gold_section, dropped_gold_label, dropped_extra_section = Counter(), Counter(), Counter()
for r in RUNS:
    for n in names:
        doc = read_json(TRAIN / n)
        gold = pubannotation_to_annotations(doc)
        folder = RUN / "T" / f"run{r:02d}" / "raw_replies" / Path(n).stem
        find = read_json(folder / "find.json")["reply"]
        candidates = parse_annotations("find", find, doc["text"], entities)[1]
        decisions = {}
        if candidates and (folder / "type.json").exists():
            for d in read_json(folder / "type.json")["reply"]["decisions"]:
                if type(d["id"]) is int and 1 <= d["id"] <= len(candidates):
                    decisions.setdefault(d["id"], d)
        for i, c in enumerate(candidates, 1):
            d = decisions.get(i)
            overlaps = [g for g in gold if g.start < c.end and c.start < g.end]
            typed = d is not None and d["entity"] in labels
            kept[("typed" if typed else "dropped", "gold" if overlaps else "no gold")] += 1
            if not typed:
                section = (d["guideline_section"] if d else "(no decision)").strip()[:70]
                if overlaps:
                    dropped_gold_section[section] += 1
                    dropped_gold_label.update(g.entity for g in overlaps[:1])
                else:
                    dropped_extra_section[section] += 1

k = len(RUNS)
print("step-1 candidates by step-2 decision (mean of 2 runs, 200 documents):")
for key in (("typed", "gold"), ("typed", "no gold"), ("dropped", "gold"), ("dropped", "no gold")):
    print(f"  {key[0]:7s} / overlaps {key[1]:7s}: {kept[key] / k:7.1f}")
print("\ndropped candidates that overlap gold, by gold label of the first overlapping mention:")
for label, v in dropped_gold_label.most_common():
    print(f"  {label}: {v / k:.1f}")
print("\ndropped candidates that overlap gold, top cited sections:")
for s, v in dropped_gold_section.most_common(8):
    print(f"  {v / k:6.1f}  {s}")
print("\ndropped candidates that overlap no gold, top cited sections:")
for s, v in dropped_extra_section.most_common(8):
    print(f"  {v / k:6.1f}  {s}")


def general(section):
    return "general" in section.lower()


print("\ncited section mentions 'general' (What NOT to Annotate 4, general terms):")
print(f"  dropped, overlaps gold:    {sum(v for s, v in dropped_gold_section.items() if general(s)) / k:6.1f} "
      f"of {sum(dropped_gold_section.values()) / k:.1f}")
print(f"  dropped, overlaps no gold: {sum(v for s, v in dropped_extra_section.items() if general(s)) / k:6.1f} "
      f"of {sum(dropped_extra_section.values()) / k:.1f}")
