"""Code review check: how many predicted mentions does span alignment drop? Offline, no API calls.

The annotation reply gives each mention's text and offsets; text_utils.align_annotations moves each one to the
nearest occurrence of its text and silently drops it when the text is not found or overlaps a mention already
placed. A dropped mention becomes a missed one in scoring. This replays the pilot's saved validation replies
(original guideline from the top-1 loop, final guideline from the top-4 loop) through the same call the runner
makes, with a provider that answers from the saved replies by prompt hash, and counts the drops.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "reproduction"))
import haiku_batch_loops as hb  # noqa: E402
from llm_guideline_moderation import iterative, pipeline  # noqa: E402
from llm_guideline_moderation.text_utils import align_annotations_with_stats  # noqa: E402

RUNS = ROOT / "outputs/ncbi_disease"
replies = {}
for p in (RUNS / "20261022_haiku-xhigh_batchqueue/replies").glob("*.json"):
    r = json.loads(p.read_text(encoding="utf-8"))
    if r["meta"]["task"] == "annotate_with_guidelines":
        replies.setdefault((r["meta"]["loop"], r["meta"]["prompt_sha256"]), []).append(r)

stats = Counter()


def counting_align(text, annotations):
    out = align_annotations_with_stats(text, annotations)
    stats["returned"] += len(annotations)
    stats["dropped"] += out["dropped"]
    stats["dropped_docs"] += out["dropped"] > 0
    return out["aligned"]


pipeline.align_annotations = counting_align


class SavedReplies:
    def __init__(self, loop):
        self.loop, self.reader = loop, hb.make_template()

    def complete(self, task, prompt):
        found = replies.get((self.loop, hashlib.sha256(prompt.encode("utf-8")).hexdigest()))
        assert found, "no saved reply for this prompt"
        usable = [r for r in found if r["message"].get("stop_reason") == "end_turn"]
        return self.reader.read_message(usable[-1]["message"], task)


_, _, entities, _ = hb.load_inputs()
for loop, run in (("topk1L01", "topk1_loop01"), ("topk4L01", "topk4_loop01")):
    stats.clear()
    folder = RUNS / f"20261022_haiku-xhigh_{run}"
    guidelines = (folder / "final/final_guidelines.txt").read_text(encoding="utf-8")
    provider = SavedReplies(loop)
    kept = 0
    for path in sorted(hb.VALID_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = iterative.annotate_with_guidelines(text=raw["text"], guidelines=guidelines, entities=entities,
                                                    provider=provider, instructions="",
                                                    output_configuration=hb.CONFIG)
        saved = json.loads((folder / "valid_predictions" / path.name).read_text(encoding="utf-8"))
        assert len(saved["denotations"]) == len(result.annotations), path.name
        kept += len(result.annotations)
    print(f"{run}: mentions returned {stats['returned']}, kept {kept}, dropped {stats['dropped']} "
          f"({stats['dropped'] / stats['returned']:.2%}) in {stats['dropped_docs']} of 100 documents; "
          f"replayed predictions match the saved valid_predictions")
