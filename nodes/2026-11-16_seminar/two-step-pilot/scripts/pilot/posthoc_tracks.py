"""Post hoc, offline: every kind of expert correction for each arm's two outputs (not part of the frozen rule).

Track 2 is the list given to an expert (S: all annotations; S+: all, excluded ones included; T: all step-1
candidates). Track 1 is the directly used output (S+: excluded removed; T: candidates step 2 typed). For each,
reproduction/lib/discrepancy.py classifies every difference from gold:
  missed     gold with no overlapping prediction (expert must read the text to add it)
  extra      prediction overlapping no gold (expert deletes it)
  label      overlapping, wrong label (expert relabels)
  boundary   same label, wrong span (expert adjusts)
  unpaired   one prediction covering two gold (expert splits)
Mean of the 2 runs, summed over the 200 documents. Run from the repository root:
    python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/posthoc_tracks.py > nodes/2026-11-16_seminar/two-step-pilot/outputs/20261114_posthoc_tracks_output.txt
"""
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, RUNS, TRAIN, read_json  # noqa: E402
from lib.discrepancy import classify_document, to_spans  # noqa: E402
from llm_guideline_moderation.pubannotation import pubannotation_to_annotations  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20261114_haiku-xhigh_pilot_twostep"
names = read_json(RUN / "manifest.json")["pilot_documents"]
gold = {n: read_json(TRAIN / n) for n in names}
SHORT = {"false_negative": "missed", "false_positive": "extra", "label_mismatch": "label",
         "boundary_mismatch": "boundary", "unpaired_overlap": "unpaired"}
KINDS = ["missed", "extra", "label", "boundary", "unpaired"]


def counts(folder, track):
    per_run = []
    for r in RUNS:
        c = Counter()
        for n in names:
            pred = read_json(RUN / folder / f"run{r:02d}" / track / n)
            report = classify_document(n, gold[n]["text"], to_spans(pubannotation_to_annotations(gold[n])),
                                       to_spans(pubannotation_to_annotations(pred)))
            c.update(SHORT[d.category] for d in report.discrepancies)
            c["predictions"] += len(pred.get("denotations", []))
        per_run.append(c)
    return {k: statistics.mean(c[k] for c in per_run) for k in KINDS + ["predictions"]}


print("mean of 2 runs, 200 documents | predictions | " + " | ".join(KINDS) + " | corrections other than missed")
for folder, arm in (("S", "S"), ("Splus", "S+"), ("T", "T")):
    for track in ("track2_predictions", "track1_predictions"):
        if arm == "S" and track == "track1_predictions":
            continue
        c = counts(folder, track)
        other = c["extra"] + c["label"] + c["boundary"] + c["unpaired"]
        print(f"{arm:2s} {track[:6]} | {c['predictions']:7.1f} | " + " | ".join(f"{c[k]:6.1f}" for k in KINDS) + f" | {other:6.1f}")
