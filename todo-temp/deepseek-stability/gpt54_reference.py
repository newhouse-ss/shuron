"""Offline reference for the DeepSeek stability test: how stable is GPT-5.4 high on dev10?

Source: reproduction/results/size_noise/repeat_01..05.json, the original guideline annotated
5 times on dev30 with Azure 5_4, reasoning high (dev10 is a subset). No API calls.

Reports, for dev10 only:
  - F1 per repeat (taken from summary.json) and its sample SD
  - prediction-level stability: of all distinct (doc, start, end, label) predictions made in any
    repeat, the share made in all 5 repeats
  - mean number of differing predictions between two repeats, over the 10 repeat pairs
"""
import itertools
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOISE = ROOT / "reproduction/results/size_noise"
dev10 = json.loads((ROOT / "reproduction/dev_splits/ncbi_disease_dev10.json").read_text(encoding="utf-8"))["documents"]
run_docs = [d["filename"] for d in json.loads(
    (ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation/inputs/sampled_train_documents.json")
    .read_text(encoding="utf-8"))]
print("dev10 split == documents of the 08/02 run:", sorted(dev10) == sorted(run_docs))

summary = json.loads((NOISE / "summary.json").read_text(encoding="utf-8"))
f1 = summary["sizes"]["10"]["f1"]
print("settings:", {k: summary[k] for k in ("repeats", "temperature", "reasoning_effort")})
print("dev10 F1 per repeat:", [round(x, 4) for x in f1],
      " mean", round(statistics.mean(f1), 4), " sample SD", round(statistics.stdev(f1), 4))

repeats = []
for i in range(1, 6):
    stored = json.loads((NOISE / f"repeat_{i:02d}.json").read_text(encoding="utf-8"))
    repeats.append({(doc, a["start"], a["end"], a["entity"]) for doc in dev10 for a in stored[doc]})

union = set().union(*repeats)
in_all = set.intersection(*repeats)
print(f"distinct predictions over 5 repeats: {len(union)}; made in all 5: {len(in_all)} "
      f"({len(in_all) / len(union):.1%})")
pair_diffs = [len(a ^ b) for a, b in itertools.combinations(repeats, 2)]
print("differing predictions per repeat pair:", pair_diffs, " mean", statistics.mean(pair_diffs))
print("predictions per repeat:", [len(r) for r in repeats])
