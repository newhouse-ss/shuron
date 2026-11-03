"""Set aside 50 unused NCBI Disease training documents as the test set for the next change.

Offline, no API calls, reads file names only (no gold). Pool: the 593 training documents minus the
50 development documents (dev10/20/30 all come from dev50) minus the training documents whose PMID
is also a BioRED document (BioRED outputs exist for two of them). The pool is shuffled once with a
fixed seed and the first 50 are the test set; the error analysis never reads their gold.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NCBI = ROOT / "data" / "datasets" / "ncbi_disease"
BIORED = ROOT / "data" / "datasets" / "biored"
OUT = ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json"
SEED = 20261024
SIZE = 50

train = {p.name for p in (NCBI / "train").glob("*.json")}
dev = set(json.loads((ROOT / "reproduction" / "dev_splits" / "ncbi_disease_dev50.json").read_text(encoding="utf-8"))["documents"])
biored = {p.name for split in ("train", "valid") for p in (BIORED / split).glob("*.json")}
assert dev <= train
pool = sorted(train - dev - biored)
order = random.Random(SEED).sample(pool, len(pool))
test = order[:SIZE]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "dataset": "ncbi_disease",
    "size": SIZE,
    "seed": SEED,
    "pool": "train minus dev50 minus BioRED PMIDs; shuffled with random.Random(seed).sample(sorted(pool), len(pool)); first `size` kept",
    "pool_size": len(pool),
    "excluded_biored": sorted((train - dev) & biored),
    "documents": sorted(test),
}, indent=2) + "\n", encoding="utf-8")
print(f"train {len(train)}, dev50 {len(dev)}, BioRED overlap outside dev {len((train - dev) & biored)}, pool {len(pool)}")
print(f"wrote {len(test)} documents to {OUT.relative_to(ROOT)}")
