"""Is the max result real, or an effect of which repeats survived the 64,000-token cap? Offline, no API calls.

In the max batch 10 of 200 replies were cut off at max_tokens, all on two documents, so only 10 of 20 repeats
are complete and the report's max F1 is scored on those 10. They are the repeats in which max happened to think
less on the two long documents, which may not be typical. This script avoids that selection:

1. Every arm on the 8 documents with no cut-off, all 20 repeats: loop set F1, recall, FN per repeat; Welch tests
   max vs xhigh, max vs high, max vs DeepSeek.
2. On each of the two affected documents, per arm: finished replies, output tokens, and the document's F1 and FN
   among finished replies; for max, finished replies' F1 against their output length (do longer replies score
   worse or better, i.e. which way would dropping the cut-off ones bias the result?).
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from run_haiku import rs, wo  # noqa: E402

from llm_guideline_moderation.types import Annotation  # noqa: E402

it = rs.it


def score(documents: dict, preds: dict) -> object:
    predictions = {doc: [Annotation(start=a["start"], end=a["end"], entity=a["entity"], text=a["text"])
                         for a in anns] for doc, anns in preds.items()}
    return it._summarize_moderation_pairs(it._build_pairs([documents[d] for d in preds], predictions), 1.0)


def main() -> None:
    _, documents, entities = rs.load_inputs()
    haiku = rs.fix_labels(rs.load_units(rh.UNITS), entities)
    deepseek = [u for u in rs.fix_labels(rs.load_units(rs.UNIT_DIRS["run"]), entities) if u["arm"] == "B_on"]
    units = deepseek + haiku
    arms = ["B_on", *rh.ARMS]
    cut = sorted({u["doc"] for u in haiku if u["arm"] == "H_max" and u["status"] != "ok"})
    clean = sorted(set(documents) - set(cut))
    print(f"documents with a max cut-off: {cut}; clean documents: {len(clean)}")

    print(f"\n1. the {len(clean)} clean documents, every repeat")
    per_arm = {}
    for arm in arms:
        by_rep: dict[int, dict] = {}
        for u in units:
            if u["arm"] == arm and u["status"] == "ok" and u["doc"] in clean:
                by_rep.setdefault(u["rep"], {})[u["doc"]] = u["annotations"]
        rows = [score(documents, preds) for rep, preds in sorted(by_rep.items()) if set(preds) == set(clean)]
        per_arm[arm] = {"f1": [s.overall_f1 for s in rows], "fn": [s.false_negatives for s in rows]}
        print(f"   {arm}: {len(rows)} repeats; F1 mean {statistics.mean(per_arm[arm]['f1']):.4f} "
              f"SD {statistics.stdev(per_arm[arm]['f1']):.4f}; recall mean "
              f"{statistics.mean(s.recall for s in rows):.4f}; precision mean "
              f"{statistics.mean(s.precision for s in rows):.4f}; FN mean {statistics.mean(per_arm[arm]['fn']):.2f} "
              f"SD {statistics.stdev(per_arm[arm]['fn']):.2f}")
    for a, b in (("H_xhigh", "H_max"), ("H_high", "H_max"), ("H_high", "H_xhigh"), ("B_on", "H_max")):
        for key in ("f1", "fn"):
            w = wo.welch(per_arm[a][key], per_arm[b][key])
            print(f"   {b} minus {a}, {key.upper()}: {w['diff']:+.4f}, t {w['t']:.3f}, df {w['df']:.1f}, "
                  f"p {w['p']:.4f}, 95% CI [{w['ci'][0]:+.4f}, {w['ci'][1]:+.4f}]")

    print("\n2. the documents with cut-offs, finished replies only")
    for doc in cut:
        gold = len(documents[doc].gold_annotations)
        print(f"   {doc} ({gold} gold annotations, {len(documents[doc].text):,} characters)")
        for arm in arms:
            rows = [u for u in units if u["arm"] == arm and u["doc"] == doc]
            ok = [u for u in rows if u["status"] == "ok"]
            out = [(u.get("usage") or {}).get("output_tokens") or (u.get("usage") or {}).get("completion_tokens")
                   or 0 for u in rows]
            scored = [(score(documents, {doc: u["annotations"]}), u) for u in ok]
            print(f"     {arm}: {len(ok)}/{len(rows)} finished; output tokens {rs.summarize(out)}; doc F1 mean "
                  f"{statistics.mean(s.overall_f1 for s, _ in scored):.4f}; FN mean "
                  f"{statistics.mean(s.false_negatives for s, _ in scored):.2f}")
            if arm == "H_max" and len(scored) > 2:
                pairs = sorted(((u["usage"]["output_tokens"], s.overall_f1) for s, u in scored))
                tokens, f1 = zip(*pairs)
                r = statistics.correlation(tokens, f1)
                print(f"       finished max replies, output tokens -> doc F1: "
                      f"{[(t, round(f, 3)) for t, f in pairs]}; Pearson r {r:+.2f}")


if __name__ == "__main__":
    main()
