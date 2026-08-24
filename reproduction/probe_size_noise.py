"""Experiment A: how much of the annotation noise is explained by development-set size?

THE QUESTION
------------
Annotating dev10 with the shipped guideline gives 51 to 61 true positives across
eleven runs, an F1 range of 0.7391 to 0.8592 and a standard deviation of 0.0302.
That is larger than most of the effects the refinement loop is asked to detect,
so every accept/revert decision it makes is partly a coin flip.

If the instability is independent per annotation decision, the F1 deviation
should shrink as 1/sqrt(N) with the number of gold annotations: 0.0302 at dev10
(74 gold) predicts 0.0157 at dev30 (273 gold). If instead a pass drifts as a
whole, one annotation run being systematically more aggressive about a category,
the deviation stays flat and a larger development set does not help.

The three dev30 baselines already on disk suggest 0.0042, well under the
1/sqrt(N) prediction, but three points pin a standard deviation only to within a
factor of six, so they settle nothing.

THE DESIGN
----------
The splits are nested, dev10 inside dev20 inside dev30, so annotating dev30 k
times yields k annotations of every smaller size at once, free and perfectly
paired: the dev10 numbers come from the same passes as the dev30 numbers, which
removes the run-to-run confound that comparing separate experiments would carry.

    k annotations of dev30  ->  k F1 values at each of dev10, dev20, dev30
                            ->  one standard deviation per size, same passes

RESUMING
--------
Predictions are cached per (repeat, document) as they are produced. The machine
running this has lost three multi-hour jobs to power failure, so a rerun with the
same --out-dir skips what is already on disk and continues. Nothing is recomputed
and nothing is lost beyond the document in flight.

    python reproduction/probe_size_noise.py --repeats 5
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from math import sqrt
from pathlib import Path
from time import monotonic

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_guideline_moderation import iterative as it  # noqa: E402
from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402
from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402
from llm_guideline_moderation.providers.openai import OpenAIProvider  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import Annotation, EntityDefinition, OutputConfiguration  # noqa: E402


def annotation_to_dict(a: Annotation) -> dict:
    return {"start": a.start, "end": a.end, "entity": a.entity, "text": a.text}


def dict_to_annotation(d: dict) -> Annotation:
    return Annotation(start=d["start"], end=d["end"], entity=d["entity"], text=d["text"])


def score(documents, predictions) -> tuple[float, int]:
    """Strict-match F1 and true-positive count over the given documents."""
    summary = it._summarize_moderation_pairs(it._build_pairs(documents, predictions), 1.0)
    true_positives = 0
    for document in documents:
        gold = {(a.start, a.end, a.entity) for a in document.gold_annotations}
        pred = {(a.start, a.end, a.entity) for a in predictions.get(document.filename, [])}
        true_positives += len(gold & pred)
    return summary.overall_f1, true_positives


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--sizes", default="10,20,30", help="nested split sizes to score")
    parser.add_argument("--guidelines", default="data/guidelines/ncbi_disease_guidelines.txt")
    parser.add_argument("--provider", choices=["azure", "deepseek"], default="azure")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--model", default="deepseek-v4-flash",
                        help="model id when --provider deepseek")
    parser.add_argument("--reasoning-effort", default="high",
                        help='"none" for models that do not take it, such as GPT-4o. '
                             'An empty string is unreliable to pass through a shell, so the '
                             'literal "none" is accepted as the off switch.')
    parser.add_argument("--token-param", default=None,
                        help="max_tokens or max_completion_tokens; the GPT-5.x "
                             "deployments reject the former, GPT-4o and DeepSeek take it")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--temperature", type=float, default=None,
                        help="omit for the API default. Reasoning models accept it but "
                             "are not made deterministic by it, since the reasoning trace "
                             "is sampled independently; see probe_deepseek.py")
    parser.add_argument("--out-dir", default="reproduction/results/size_noise")
    args = parser.parse_args()

    load_dotenv()
    sizes = [int(s) for s in args.sizes.split(",")]
    largest = max(sizes)
    splits = {
        n: json.loads((REPO_ROOT / f"reproduction/dev_splits/ncbi_disease_dev{n}.json")
                      .read_text(encoding="utf-8"))["documents"]
        for n in sizes
    }
    for smaller, larger in zip(sizes, sizes[1:]):
        assert set(splits[smaller]) <= set(splits[larger]), f"dev{smaller} is not inside dev{larger}"

    source = REPO_ROOT / "data/datasets/ncbi_disease/train"
    documents = {n: [load_sampled_document(source / f) for f in splits[n]] for n in sizes}
    guidelines = (REPO_ROOT / args.guidelines).read_text(encoding="utf-8")
    entities = [EntityDefinition(name=r) for r in json.loads(
        (REPO_ROOT / "data/schemas/ncbi_entities.schema.json").read_text(encoding="utf-8"))]
    configuration = OutputConfiguration(include_rationale=True, include_guideline_section=True)

    out_dir = REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    shared = {"max_output_tokens": args.max_output_tokens}
    if args.temperature is not None:
        shared["temperature"] = args.temperature
    if args.reasoning_effort and args.reasoning_effort.lower() != "none":
        shared["reasoning_effort"] = args.reasoning_effort
    if args.token_param:
        shared["token_param"] = args.token_param

    if args.provider == "deepseek":
        import os
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            sys.exit("DEEPSEEK_API_KEY is not set")
        shared.setdefault("token_param", "max_tokens")
        # DeepSeek is OpenAI-compatible on chat/completions; background mode is
        # an Azure Responses feature and does not apply.
        provider = OpenAIProvider(model=args.model, api_key=key, use_background=False,
                                  base_url="https://api.deepseek.com/chat/completions",
                                  **shared)
        label = args.model
    else:
        provider = OpenAIProvider.from_azure_env(args.azure_model_key, **shared)
        label = f"azure:{args.azure_model_key}"

    gold_counts = {n: sum(len(d.gold_annotations) for d in documents[n]) for n in sizes}
    print(f"model {label}, guideline {len(guidelines)} chars, {args.repeats} repeats, "
          f"temperature={args.temperature}, effort={shared.get('reasoning_effort', 'none')}")
    for n in sizes:
        print(f"  dev{n}: {len(documents[n])} docs, {gold_counts[n]} gold annotations")
    print(f"cache: {out_dir}\n", flush=True)

    started = monotonic()
    for repeat in range(1, args.repeats + 1):
        cache = out_dir / f"repeat_{repeat:02d}.json"
        stored = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
        pending = [d for d in documents[largest] if d.filename not in stored]
        print(f"repeat {repeat}: {len(stored)} cached, {len(pending)} to annotate", flush=True)
        for document in pending:
            began = monotonic()
            result = annotate_with_guidelines(
                text=document.text, guidelines=guidelines, entities=entities,
                provider=provider, instructions="", output_configuration=configuration,
            )
            stored[document.filename] = [annotation_to_dict(a) for a in result.annotations]
            # Written after every document: a power cut costs one call, not the run.
            cache.write_text(json.dumps(stored, indent=1), encoding="utf-8")
            print(f"    r{repeat} {document.filename:<16} {monotonic() - began:6.1f}s  "
                  f"{len(stored)}/{len(documents[largest])}  "
                  f"(elapsed {(monotonic() - started) / 60:.1f} min)", flush=True)

        predictions = {k: [dict_to_annotation(a) for a in v] for k, v in stored.items()}
        line = "  ".join(f"dev{n} F1={score(documents[n], predictions)[0]:.4f}" for n in sizes)
        print(f"repeat {repeat} done: {line}\n", flush=True)

    results: dict[int, list[tuple[float, int]]] = {n: [] for n in sizes}
    for repeat in range(1, args.repeats + 1):
        stored = json.loads((out_dir / f"repeat_{repeat:02d}.json").read_text(encoding="utf-8"))
        predictions = {k: [dict_to_annotation(a) for a in v] for k, v in stored.items()}
        for n in sizes:
            results[n].append(score(documents[n], predictions))

    print(f"\n{'size':<7}{'gold':>6}{'F1 per repeat':>46}{'range':>9}{'SD':>9}{'1/sqrt(N) pred':>16}")
    print("-" * 94)
    reference = None
    for n in sizes:
        f1s = [f for f, _ in results[n]]
        sd = statistics.stdev(f1s) if len(f1s) > 1 else float("nan")
        if reference is None:
            reference = (sd, gold_counts[n])
            predicted = "  (reference)"
        else:
            predicted = f"{reference[0] * sqrt(reference[1] / gold_counts[n]):>16.4f}"
        values = " ".join(f"{f:.4f}" for f in f1s)
        print(f"dev{n:<4}{gold_counts[n]:>6}{values:>46}{max(f1s) - min(f1s):>9.4f}{sd:>9.4f}{predicted}")

    print(f"\n{'size':<7}{'true positives per repeat':>40}{'range':>9}{'SD':>9}")
    print("-" * 65)
    for n in sizes:
        tps = [t for _, t in results[n]]
        sd = statistics.stdev(tps) if len(tps) > 1 else float("nan")
        print(f"dev{n:<4}{' '.join(str(t) for t in tps):>40}{max(tps) - min(tps):>9}{sd:>9.2f}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps({
        "repeats": args.repeats, "temperature": args.temperature,
        "reasoning_effort": args.reasoning_effort,
        "model": label,
        "sizes": {str(n): {"gold": gold_counts[n],
                           "f1": [f for f, _ in results[n]],
                           "true_positives": [t for _, t in results[n]]} for n in sizes},
    }, indent=2), encoding="utf-8")
    print(f"\nwritten to {summary_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
