"""Moderate the top k discrepancy groups in one rewrite instead of one per round.

WHAT THIS TESTS
---------------
The published loop repairs one (gold type, predicted type) group per round. It
picks the largest group, explains it, condenses it to one principle, and rewrites
the whole guideline around that principle. The rewrite is accepted if development
F1 rises.

Over the published run's three scored rounds the targeted group shrinks every
time and the total does not follow: 18 discrepancies to 11, while the four
targets themselves account for 12. Each round repairs its own group and adds
errors elsewhere, including in groups an earlier round had already repaired.

The suspicion is that this is structural rather than incidental. A rewrite that
sees one group has one thing to optimise and no term for what it costs the rest,
and the accept test (F1 up or down) cannot separate "repaired the target" from
"broke something else by less". Showing the rewrite the k largest groups at once
gives it the trade-off inside a single call.

WHAT CHANGES
------------
One function. `_refine_guidelines_from_pairs` reads `summary.dominant_cluster`;
this reads `summary.all_clusters[:k]`, which is already sorted by count
(iterative.py builds it with `sorted(..., reverse=True)`).

Per cluster the two analysis calls run exactly as published, each still seeing a
single cluster, so `infer_discrepancy_patterns` and `generate_moderation_principle`
are used unmodified: their "ONE Dominant Discrepancy Case" framing still holds
for each call. The k principles then go into ONE `refine_guidelines` call.

`refine_guidelines` already speaks in the plural ("NEW MODERATION PRINCIPLES",
"Integrate the New Principles"). The only thing it never had to handle is two new
principles contradicting each other, so one instruction is added for that. Every
other instruction, the CONSTRAINT block and the CONSTRAINT CHECK are byte
identical to the published template.

Annotation, scoring, the accept/revert test and the stopping rule are untouched,
so runs are comparable with the published condition and with the two verified-
example ablations.

WHAT IT COSTS
-------------
Refinement calls per round go from 3 to 2k+1. Annotation still dominates (one
call per development document per round), so k=3 on ten documents is 17 calls a
round against 13.

WHAT TO LOOK AT AFTERWARDS
--------------------------
Not the F1 curve. Two counts read off the per-round snapshots:

  * REGRESSION: a group whose count fell in an earlier round and rose again
    later. If merging works, these should be rarer, because a group repaired in
    round n is likely still in the top k at round n+1 and so is defended rather
    than ignored.

  * NEW GROUPS: keys absent from every earlier round. Merging has no mechanism
    against these. The k principles are generated independently and only meet
    inside the rewrite, and no group outside the top k is represented at all. If
    the new-group count does not fall, that is the expected result, not a
    failure of the run.

Both counts come from `all_clusters` in each round's snapshot, so no extra
annotation is needed to score this.

    python reproduction/moderate_topk.py --k 3 --azure-model-key 5_4
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from llm_guideline_moderation import iterative  # noqa: E402
from llm_guideline_moderation.prompts import PROMPT_TEMPLATES, render_prompt  # noqa: E402

EXPERIMENT_ID = "ncbi_disease_topk_moderation"

# The published template tells the rewrite how to resolve a new principle against
# an existing rule. With k principles arriving together it also needs a rule for
# resolving them against each other, which is the case this experiment creates.
CONFLICT = (
    "   - **Between New Principles**: The principles below were derived independently and may\n"
    "     overlap or conflict. Where two of them would label the same span differently, state the\n"
    "     narrower condition first and make the broader principle explicitly exclude it. Do not\n"
    "     silently drop either one.\n"
)


def build_template(published: str) -> str:
    """Published refine_guidelines plus one conflict-resolution instruction."""
    anchor = "   - If the new principle clarifies a specific section, add it there.\n"
    assert anchor in published, "instruction 2 changed upstream"
    return published.replace(anchor, anchor + CONFLICT)


def topk_refine(
    sampled_documents,
    predictions,
    current_guidelines,
    entities,
    summary,
    provider,
    n_examples,
    *,
    k: int,
):
    """Published refinement, over the k largest discrepancy groups instead of one."""
    clusters = summary.all_clusters[:k] or [summary.dominant_cluster]
    entity_schema = iterative._entity_schema_text(entities)
    true_positive_examples = iterative._build_true_positive_examples(
        sampled_documents, predictions, n_examples)
    verified_examples = iterative._build_verified_examples(
        sampled_documents, predictions, n_examples)

    prompts: dict[str, str] = {}
    insights: list[str] = []
    principles: list[str] = []

    for rank, cluster in enumerate(clusters, 1):
        discrepancy_examples = iterative._build_discrepant_examples_from_cluster(
            cluster, n_examples)
        header = f"### {rank}. {cluster.key} ({cluster.count} cases)"

        name = f"infer_discrepancy_patterns_{rank}"
        prompts[name] = render_prompt(
            "infer_discrepancy_patterns",
            entity_schema=entity_schema,
            discrepant_examples=discrepancy_examples,
            true_positive_examples=true_positive_examples,
        )
        insight = provider.complete(name, prompts[name])
        insights.append(f"{header}\n{insight}")

        discrepancy_pattern = cluster.key
        if insight.strip():
            discrepancy_pattern += f"\n\n**INFERRED PATTERNS:**\n{insight}"

        name = f"generate_moderation_principle_{rank}"
        prompts[name] = render_prompt(
            "generate_moderation_principle",
            entity_schema=entity_schema,
            discrepancy_pattern=discrepancy_pattern,
            discrepant_examples=discrepancy_examples,
        )
        principle = provider.complete(name, prompts[name])
        principles.append(f"{header}\n{principle}")

    prompts["refine_guidelines"] = render_prompt(
        "refine_guidelines",
        guidelines=current_guidelines or "(no guidelines provided)",
        new_principles="\n\n".join(principles),
        verified_examples=verified_examples,
    )
    refined_guidelines = provider.complete("refine_guidelines", prompts["refine_guidelines"])
    return refined_guidelines, "\n\n".join(insights), "\n\n".join(principles), prompts


def main() -> None:
    parser = argparse.ArgumentParser(description="Moderate the top k discrepancy groups per round.")
    parser.add_argument("--k", type=int, default=3, help="Groups moderated in one rewrite")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--run-name", help="Output folder name")
    parser.add_argument("--dev-split", help="Document list from reproduction/make_dev_splits.py")
    parser.add_argument("--n-examples", type=int,
                        help="Prompt evidence count. Scale it with the dev split, since the "
                             "published value of 5 was calibrated for 10 documents.")
    args = parser.parse_args()
    assert args.k >= 1, "--k must be at least 1"

    published = PROMPT_TEMPLATES["refine_guidelines"]
    template = build_template(published)

    # One added instruction, nothing removed: the block that limits regression and
    # the check that enforces it must both survive, or this stops being comparable
    # with the published run.
    assert "{verified_examples}" in template, "the CONSTRAINT block must stay"
    assert "CONSTRAINT CHECK" in template, "the CONSTRAINT CHECK must stay"
    assert set(re.findall(r"\{(\w+)\}", template)) == {
        "guidelines", "new_principles", "verified_examples"}
    PROMPT_TEMPLATES["refine_guidelines"] = template

    # The two analysis prompts each still see exactly one cluster, so they are used
    # as published; assert that, so a later upstream edit cannot pass silently.
    assert "ONE Dominant Discrepancy Case" in PROMPT_TEMPLATES["infer_discrepancy_patterns"]
    assert "ONE Core Moderation Principle" in PROMPT_TEMPLATES["generate_moderation_principle"]

    iterative._refine_guidelines_from_pairs = functools.partial(topk_refine, k=args.k)

    print(f"top-{args.k} moderation: {2 * args.k + 1} refinement calls per round "
          f"(published: 3); refine_guidelines {len(published)} -> {len(template)} chars")

    spec = json.loads(
        (REPO_ROOT / "experiments/ncbi_disease_valid_round1.spec.json").read_text(encoding="utf-8"))
    spec["experiment_id"] = EXPERIMENT_ID
    spec["description"] = f"Published spec, moderating the top {args.k} discrepancy groups per round."
    spec_path = Path(__file__).resolve().parent / "moderate_topk.spec.json"
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
