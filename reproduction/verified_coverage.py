"""What the CONSTRAINT block protects: all of it, or only what is still correct.

WHAT THIS TESTS
---------------
`refine_guidelines` receives a block headed DO NOT BREAK THESE EXAMPLES holding
annotations the current guideline already gets right. It is the loop's only
mechanism against regression.

In the published run on ten development documents the block never held more than
18 of the 57 correct mentions, because `n_examples` (5) is applied twice inside
`_build_true_positive_examples`: at most 5 annotations per document, and at most
5 documents. The last five development documents contributed nothing at all.

Across the four rounds the rewrite broke six mentions that had been annotated
correctly before it. Not one of them appears in the block. So the observed
regression is not the instruction failing on cases it was given; it is regression
on cases it was never given.

Two conditions, one variable each.

  --mode full
      Every currently correct mention, every document. Same rendering, both caps
      removed. Tests whether the instruction holds once it covers the cases.

  --mode cumulative
      Everything --mode full protects, plus every mention that was correct in any
      earlier round of this run. The block is rebuilt from the current round's
      predictions, so a mention drops out of it the moment it breaks and nothing
      can pull it back: "unilateral retinal telangiectasis" broke in round 2 and
      was still broken at the end. This restores those.

`--mode cumulative` is a superset of `--mode full`, so read it against that run
rather than against the published one, or the comparison carries two changes.

SCOPE
-----
Only `_build_verified_examples` is replaced. `_build_true_positive_examples` is
left alone even though the published code has the former delegate to the latter,
because it also feeds `infer_discrepancy_patterns` as the contrastive control;
changing it would move a second variable. The prompt templates, the analysis
calls, the accept/revert test and the stopping rule are untouched.

WHAT TO EXPECT
--------------
The block gets longer, so copied share should rise: the same text is what the
rewrite transcribes into the guideline. Run `measure_hardcoding.py` on the result
and read the regression count against it. Falling regression bought with a higher
copied share is the outcome that says the two are the same mechanism, which is
worth knowing either way.

    python reproduction/verified_coverage.py --mode full --azure-model-key 5_4
    python reproduction/verified_coverage.py --mode cumulative --azure-model-key 5_4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from llm_guideline_moderation import iterative  # noqa: E402

EXPERIMENT_ID = "ncbi_disease_verified_coverage"

# doc filename -> {(start, end, label): Annotation} for everything ever matched.
_ever_correct: dict[str, dict[tuple[int, int, str], object]] = {}


def build_block(sampled_documents, predictions, n_examples, *, cumulative: bool) -> str:
    """The published rendering, with both of n_examples' caps removed."""
    blocks: list[str] = []
    for document in sampled_documents:
        gold = {iterative._annotation_to_key(a): a for a in document.gold_annotations}
        pred = {iterative._annotation_to_key(a): a
                for a in predictions.get(document.filename, [])}
        matched = {key: gold[key] for key in gold.keys() & pred.keys()}

        history = _ever_correct.setdefault(document.filename, {})
        history.update(matched)
        selected = history if cumulative else matched
        if not selected:
            continue

        # Sorted by position: the published order comes from a set intersection,
        # which makes the block's contents depend on hash order.
        annotations = [selected[key] for key in sorted(selected)]
        lines = [f"FILE: {document.filename}", f"TEXT: {document.text}", "MATCHED ANNOTATIONS:"]
        lines.extend(f"- {iterative._annotation_summary(a)}" for a in annotations)
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks) or "(no true positive examples found)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Widen the CONSTRAINT block.")
    parser.add_argument("--mode", choices=("full", "cumulative"), required=True)
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--run-name", help="Output folder name")
    parser.add_argument("--dev-split", help="Document list from reproduction/make_dev_splits.py")
    parser.add_argument("--n-examples", type=int,
                        help="Still passed through: it caps the discrepancy examples and the "
                             "contrastive true positives, which this experiment does not change.")
    args = parser.parse_args()

    cumulative = args.mode == "cumulative"

    published = iterative._build_verified_examples
    seen: dict[str, int] = {}

    def patched(sampled_documents, predictions, n_examples):
        block = build_block(sampled_documents, predictions, n_examples, cumulative=cumulative)
        was = published(sampled_documents, predictions, n_examples)
        round_number = seen["n"] = seen.get("n", 0) + 1
        print(f"  round {round_number}: CONSTRAINT block {len(was)} -> {len(block)} chars, "
              f"{was.count(chr(10) + '- ')} -> {block.count(chr(10) + '- ')} annotations",
              flush=True)
        return block

    iterative._build_verified_examples = patched

    spec = json.loads(
        (REPO_ROOT / "experiments/ncbi_disease_valid_round1.spec.json").read_text(encoding="utf-8"))
    spec["experiment_id"] = EXPERIMENT_ID
    spec["description"] = (f"Published spec, CONSTRAINT block covering "
                           f"{'every mention ever correct' if cumulative else 'every correct mention'}.")
    spec_path = Path(__file__).resolve().parent / f"verified_coverage_{args.mode}.spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    import run_iterative_refinement as runner

    sys.argv = [
        "run_iterative_refinement.py",
        "--spec", str(spec_path),
        "--azure-model-key", args.azure_model_key,
        "--reasoning-effort", args.reasoning_effort,
        "--max-output-tokens", str(args.max_output_tokens),
        *(["--run-name", args.run_name] if args.run_name else []),
        *(["--dev-split", args.dev_split] if args.dev_split else []),
        *(["--n-examples", str(args.n_examples)] if args.n_examples else []),
    ]
    runner.main()


if __name__ == "__main__":
    main()
