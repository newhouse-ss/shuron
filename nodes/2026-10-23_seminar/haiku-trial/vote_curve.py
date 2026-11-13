"""Track 2 illustration: voting across repeated runs, from the Haiku xhigh dev10 trial. Offline, no API calls.

The trial annotated the 10 development documents 20 times with the original guideline (same prompt each time).
Voting keeps a mention (exact span and subtype) if at least k of the 20 runs predicted it; k = 1 is the union of
all runs, k = 20 the mentions every run found. For each k: kept mentions, TP, FP (extra), FN (missed), precision,
recall, F1, scored with the loop's set scoring (iterative._summarize_moderation_pairs), as fn_noise.py does for
single runs. Development documents, so this only shows how the threshold trades FP for FN; the thesis curve
would use repeated validation runs.
"""
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from fn_noise import per_repeat  # noqa: E402
from run_haiku import rs  # noqa: E402

it = rs.it
ARM = "H_xhigh"


def main() -> None:
    _, documents, entities = rs.load_inputs()
    units = [u for u in rs.fix_labels(rs.load_units(rh.UNITS), entities) if u["arm"] == ARM and u["status"] == "ok"]
    reps = {u["rep"] for u in units}
    complete = sorted(r for r in reps if {u["doc"] for u in units if u["rep"] == r} == set(documents))
    n = len(complete)
    votes = {doc: Counter() for doc in documents}
    for u in units:
        if u["rep"] in complete:
            votes[u["doc"]].update({(a["start"], a["end"], a["entity"]) for a in u["annotations"]})
    gold = {doc: {it._annotation_to_key(a) for a in d.gold_annotations} for doc, d in documents.items()}
    assert all(len(next(iter(g))) == 3 for g in gold.values() if g)
    print(f"{ARM}: {n} complete repeats x {len(documents)} documents; gold mentions {sum(map(len, gold.values()))}")

    single = per_repeat(units, ARM, documents)
    print(f"single run, mean of {len(single)}: kept {statistics.mean(r['predictions'] for r in single):.1f}, "
          f"FP {statistics.mean(r['fp'] for r in single):.2f}, FN {statistics.mean(r['fn'] for r in single):.2f}, "
          f"precision {statistics.mean(r['precision'] for r in single):.4f}, "
          f"recall {statistics.mean(r['recall'] for r in single):.4f}, F1 {statistics.mean(r['f1'] for r in single):.4f}")
    print("k (at least k of n runs) | kept | TP | FP | FN | precision | recall | F1")
    for k in range(1, n + 1):
        tp = fp = fn = 0
        for doc, counter in votes.items():
            kept = {key for key, c in counter.items() if c >= k}
            tp += len(kept & gold[doc])
            fp += len(kept - gold[doc])
            fn += len(gold[doc] - kept)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn)
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        print(f"{k:2d} | {tp + fp} | {tp} | {fp} | {fn} | {p:.4f} | {r:.4f} | {f1:.4f}")
    # Rules that need no gold to pick k; a k chosen by its score here would use gold (development only).
    print(f"rules fixed in advance: union k = 1; majority (more than half) k = {n // 2 + 1}; unanimous k = {n}")


if __name__ == "__main__":
    main()
