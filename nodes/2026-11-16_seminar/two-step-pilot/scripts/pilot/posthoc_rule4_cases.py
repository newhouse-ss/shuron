"""Post hoc, offline: the candidates T's step 2 dropped while citing the general-terms rule (What NOT to Annotate 4).

Splits them into dropped gold mentions (wrong removals) and dropped non-gold candidates (right removals), and
prints the candidate texts and their last word, summed over the 2 runs. Exploration on the check's 200
training documents, which from now on count as development data. Run from the repository root:
    python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/posthoc_rule4_cases.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/20261114_posthoc_rule4_cases_output.txt
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

wrong, right, wrong_head, right_head, wrong_gold_label = Counter(), Counter(), Counter(), Counter(), Counter()
for r in RUNS:
    for n in names:
        doc = read_json(TRAIN / n)
        gold = pubannotation_to_annotations(doc)
        folder = RUN / "T" / f"run{r:02d}" / "raw_replies" / Path(n).stem
        candidates = parse_annotations("find", read_json(folder / "find.json")["reply"], doc["text"], entities)[1]
        if not candidates or not (folder / "type.json").exists():
            continue
        decisions = {}
        for d in read_json(folder / "type.json")["reply"]["decisions"]:
            if type(d["id"]) is int and 1 <= d["id"] <= len(candidates):
                decisions.setdefault(d["id"], d)
        for i, c in enumerate(candidates, 1):
            d = decisions.get(i)
            if d is None or d["entity"] in labels or "general" not in d["guideline_section"].lower():
                continue
            text = c.text.lower()
            head = text.split()[-1].strip(".,;:()")
            overlaps = [g for g in gold if g.start < c.end and c.start < g.end]
            if overlaps:
                wrong[text] += 1
                wrong_head[head] += 1
                wrong_gold_label[overlaps[0].entity] += 1
            else:
                right[text] += 1
                right_head[head] += 1

print(f"dropped citing the general-terms rule, summed over 2 runs: overlaps gold {sum(wrong.values())}, overlaps no gold {sum(right.values())}")
print("gold label of the dropped gold mentions:", dict(wrong_gold_label.most_common()))
print("\nlast word | dropped, overlaps gold | dropped, overlaps no gold")
for head in sorted(set(wrong_head) | set(right_head), key=lambda h: -(wrong_head[h] + right_head[h]))[:25]:
    print(f"  {head:18s} | {wrong_head[head]:4d} | {right_head[head]:4d}")
multi_wrong = sum(v for t, v in wrong.items() if len(t.split()) > 1)
multi_right = sum(v for t, v in right.items() if len(t.split()) > 1)
print(f"\nmore than one word: overlaps gold {multi_wrong} of {sum(wrong.values())}; overlaps no gold {multi_right} of {sum(right.values())}")
print("\nmost frequent dropped gold mentions:")
for t, v in wrong.most_common(25):
    print(f"  {v:3d}  {t}")
print("\nmost frequent dropped non-gold candidates:")
for t, v in right.most_common(25):
    print(f"  {v:3d}  {t}")
