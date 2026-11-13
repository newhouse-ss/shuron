"""Offline, gold only: do dev10, dev20 and dev30 contain the general-terms cases where the rule and gold disagree?

Categories come from the step-2 removals in posthoc_rule4_cases_output.txt (chosen after looking at them):
  deficiency   gold mention containing "deficien" (the rule lists "deficiency" as a general term; gold annotates it)
  abnormality  gold mention ending in abnormality/abnormalities/anomaly/anomalies/defect/defects
  category+    gold mention of two or more words ending in disease(s)/disorder(s)/syndrome(s)/condition(s)
  bare noun    a bare disease/disorder/syndrome/condition word in the text that no gold mention covers (gold agrees
               with the rule here)
The 200 check documents are shown for comparison. Run from the repository root:
    python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/dev_rule4_coverage.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/20261114_dev_rule4_coverage_output.txt
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, TRAIN, read_json  # noqa: E402
from llm_guideline_moderation.pubannotation import pubannotation_to_annotations  # noqa: E402

ABN = {"abnormality", "abnormalities", "anomaly", "anomalies", "defect", "defects"}
CAT = {"disease", "diseases", "disorder", "disorders", "syndrome", "syndromes", "condition", "conditions"}
WORD = re.compile(r"\b(disease|diseases|disorder|disorders|syndrome|syndromes|condition|conditions)\b", re.I)


def count(names):
    c = {"documents": len(names), "gold": 0, "deficiency": 0, "abnormality": 0, "category+": 0, "bare noun": 0}
    docs_with = {"deficiency": 0, "abnormality": 0, "category+": 0}
    for n in names:
        doc = read_json(TRAIN / n)
        gold = pubannotation_to_annotations(doc)
        c["gold"] += len(gold)
        seen = set()
        for g in gold:
            words = g.text.lower().split()
            last = words[-1].strip(".,;:()") if words else ""
            for key, hit in (("deficiency", "deficien" in g.text.lower()), ("abnormality", last in ABN),
                             ("category+", len(words) > 1 and last in CAT)):
                if hit:
                    c[key] += 1
                    seen.add(key)
        for key in seen:
            docs_with[key] += 1
        for m in WORD.finditer(doc["text"]):
            if not any(g.start < m.end() and m.start() < g.end for g in gold):
                c["bare noun"] += 1
    return c, docs_with


splits = {k: read_json(ROOT / f"reproduction/dev_splits/ncbi_disease_{k}.json")["documents"] for k in ("dev10", "dev20", "dev30")}
splits["check 200"] = read_json(ROOT / "outputs/ncbi_disease/20261114_haiku-xhigh_pilot_twostep/manifest.json")["pilot_documents"]
print("set | documents | gold mentions | deficiency (docs) | abnormality (docs) | category+ (docs) | bare noun not annotated")
for k, names in splits.items():
    c, d = count(names)
    print(f"{k:9s} | {c['documents']:3d} | {c['gold']:4d} | {c['deficiency']:3d} ({d['deficiency']}) | "
          f"{c['abnormality']:3d} ({d['abnormality']}) | {c['category+']:3d} ({d['category+']}) | {c['bare noun']:3d}")
