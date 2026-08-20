"""How many true positives move between two annotations of the same documents?

The verification loop counts a regression whenever a true positive present in
the round's baseline annotation is missing from the annotation of a candidate
guideline. Both are independent samples, so that count is

    regressions = (true positives the guideline actually broke)
                + (true positives that moved because annotation is not
                   deterministic)

and the second term has never been measured. Without it a count of 4 could mean
the draft broke four cases, or that it broke none and the annotator simply drew
differently. It also sets the floor the loop should stop at: driving regressions
below the noise level is not achievable, so a budget aimed at zero is aimed at
the wrong number.

This annotates the same documents with the *unchanged* guideline several times.
Every difference between two runs is noise by construction.

Reported per pair:
  lost      true positives in the earlier run, missing from the later one
            - directly comparable to the regression counts in the loop
  gained    the reverse, for symmetry
  jaccard   overlap of the two true-positive sets

    python reproduction/probe_annotation_noise.py --repeats 3
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from time import monotonic

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_guideline_moderation import iterative as it  # noqa: E402
from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402
from llm_guideline_moderation.providers.openai import OpenAIProvider  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402


def true_positives(documents, predictions) -> set[tuple]:
    keys = set()
    for document in documents:
        gold = {(a.start, a.end, a.entity) for a in document.gold_annotations}
        pred = {(a.start, a.end, a.entity) for a in predictions.get(document.filename, [])}
        keys |= {(document.filename, *k) for k in gold & pred}
    return keys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dev-split", default="reproduction/dev_splits/ncbi_disease_dev10.json")
    parser.add_argument("--guidelines", default="data/guidelines/ncbi_disease_guidelines.txt")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--out", default="reproduction/results/annotation_noise.json")
    args = parser.parse_args()

    load_dotenv()
    names = json.loads(Path(args.dev_split).read_text(encoding="utf-8"))["documents"]
    documents = [load_sampled_document(REPO_ROOT / "data/datasets/ncbi_disease/train" / n) for n in names]
    guidelines = Path(args.guidelines).read_text(encoding="utf-8")
    entities = [EntityDefinition(name=r) for r in json.loads(
        (REPO_ROOT / "data/schemas/ncbi_entities.schema.json").read_text(encoding="utf-8"))]
    provider = OpenAIProvider.from_azure_env(args.azure_model_key, reasoning_effort=args.reasoning_effort)
    configuration = OutputConfiguration(include_rationale=True, include_guideline_section=True)

    gold_total = sum(len(d.gold_annotations) for d in documents)
    print(f"{len(documents)} documents, {gold_total} gold annotations, "
          f"guideline {len(guidelines)} chars, {args.repeats} repeats\n")

    # Each annotation is a multi-minute reasoning call, so a silent run gives no
    # way to tell "slow" from "wedged on a socket that never times out" until
    # the whole repeat is done. Tick once per call instead.
    original_complete = provider.complete
    state = {"call": 0, "started": monotonic()}

    def complete_with_progress(task, prompt, **kwargs):
        state["call"] += 1
        began = monotonic()
        result = original_complete(task, prompt, **kwargs)
        print(f"    call {state['call']:>3}  {monotonic() - began:6.1f}s  "
              f"(elapsed {(monotonic() - state['started']) / 60:.1f} min)", flush=True)
        return result

    provider.complete = complete_with_progress

    runs = []
    for index in range(1, args.repeats + 1):
        predictions = it._annotate_documents(documents, guidelines, entities, provider, "", configuration)
        summary = it._summarize_moderation_pairs(it._build_pairs(documents, predictions), 1.0)
        tps = true_positives(documents, predictions)
        runs.append(tps)
        print(f"run {index}: F1={summary.overall_f1:.4f}  TP={len(tps)}", flush=True)

    print()
    print(f"{'pair':<8}{'lost':>6}{'gained':>8}{'jaccard':>10}")
    pairs = []
    for a, b in combinations(range(len(runs)), 2):
        lost, gained = runs[a] - runs[b], runs[b] - runs[a]
        union = runs[a] | runs[b]
        jaccard = len(runs[a] & runs[b]) / len(union) if union else 1.0
        pairs.append({"pair": f"{a + 1}->{b + 1}", "lost": len(lost),
                      "gained": len(gained), "jaccard": jaccard})
        print(f"{a + 1}->{b + 1:<5}{len(lost):>6}{len(gained):>8}{jaccard:>10.3f}")

    losses = [p["lost"] for p in pairs]
    print()
    print(f"noise floor: {min(losses)} to {max(losses)} true positives lost between "
          f"two runs of the identical guideline")
    print(f"for reference, the verification loop saw 4, 2 and 2 regressions on its "
          f"first drafts and treated 0 as the target")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "dev_split": args.dev_split, "repeats": args.repeats,
        "gold_total": gold_total, "true_positive_counts": [len(r) for r in runs],
        "pairs": pairs,
    }, indent=2), encoding="utf-8")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
