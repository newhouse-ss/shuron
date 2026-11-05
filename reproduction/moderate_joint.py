"""Analyse the top k discrepancy groups in one call, reconciling them before rewriting.

WHY
---
`moderate_topk.py` analyses each of the k groups on its own and lets the rewrite
merge the k principles. The rewrite cannot do that job: its template takes only
`{guidelines}`, `{new_principles}` and `{verified_examples}`, so it never sees a
single discrepancy. It is asked to reconcile rules whose evidence it cannot read.

Round 1 of 20260902_..._topk4_r3 shows what follows. Two of the four principles
covered the same surface form:

    principle 2  deficit construction + molecular product  -> DiseaseClass
                 evidence: "deficiency of norrin"
    principle 3  deficit nominalisation + biomolecule name  -> SpecificDisease
                 evidence: "deficient activity of fatty aldehyde dehydrogenase"

Each mention satisfies the other's trigger, and the rewrite had neither in front
of it. It resolved the clash by writing three numbered entries that quote the
development sentences verbatim, and it got one of them backwards: principle 3
asks for FALDH to be annotated, the guideline says not to. That group went from
2 discrepancies to 3.

The clash is not incidental. Over the nineteen rounds recorded so far, every one
has at least two of its top four groups sharing a content word, and 84 of the 85
colliding pairs share `deficien-`.

WHAT CHANGES
------------
One joint analysis call replaces the k separate ones. It sees every group's
discrepancies together with the shared true-positive control, and returns groups
of clusters: merged where one pattern explains several, independent where they
are genuinely separate, and explicitly UNRESOLVABLE where no stated criterion
separates them. Principle generation then runs per returned group, using the
published prompt unchanged, so the number of principles is at most k and they no
longer contradict each other.

The UNRESOLVABLE outlet matters. Told to reconcile, a model will always produce
something; a forced merge over an unresolvable pair is worse than moderating
neither, which is what those clusters get here.

SCOPE
-----
The `refine_guidelines` template is the same one `moderate_topk.py` uses, so a
run of this against a top-k run differs in the analysis stage alone.
`generate_moderation_principle` is untouched. Upstream source is untouched.

    python reproduction/moderate_joint.py --k 4 --azure-model-key 5_4
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_guideline_moderation import iterative  # noqa: E402
from llm_guideline_moderation.prompts import PROMPT_TEMPLATES, render_prompt  # noqa: E402
from moderate_topk import build_template  # noqa: E402

EXPERIMENT_ID = "ncbi_disease_joint_moderation"

JOINT_TEMPLATE = """
You are an expert Computational Linguist.
You are given **SEVERAL discrepancy clusters from the same annotation round** and must decide,
before any guideline is written, which of them are the same problem and which are not.

**ENTITY SCHEMA:**
{entity_schema}

**INPUT DATA:**
1. **Clusters (The Problems)**: numbered groups of the same (gold type, predicted type) error.
2. **True Positives (The Control)**: cases the model already gets right, shared by all clusters.

---
**1. CLUSTERS TO ANALYSE:**
{clusters}

**2. TRUE POSITIVE EXAMPLES (For Contrast):**
{true_positive_examples}
---

**TASK:**

Step 1: **Per cluster**, identify the linguistic trigger, exactly as you would in isolation:
contrast its discrepancies against the True Positives and name the feature that separates them.

Step 2: **Across clusters**, check every pair for these relations:
- **Same trigger, same verdict**: one pattern explains both. MERGE them.
- **Same trigger, opposite verdicts** (e.g. the same surface construction is gold-labelled one way
  in one cluster and another way in a second cluster): look for a further feature that separates
  the two sets of evidence. If you find one, MERGE them into a single pattern whose rule names
  that feature and covers both verdicts.
- **No shared trigger**: keep them INDEPENDENT.

Step 3: **Be honest about failure.** If two clusters share a trigger and you cannot find any
feature, statable from the evidence and the Entity Schema, that separates their verdicts, do NOT
invent one and do NOT pick a side. Report them as UNRESOLVABLE. A guideline rule that contradicts
one of the clusters is worse than no rule.

**OUTPUT FORMAT:**
Emit one block per resulting group, then exactly one UNRESOLVABLE block. Use these headings
literally, with the cluster numbers in brackets:

## GROUP 1 [clusters: 2, 3]
- **Pattern Name**: short descriptive title.
- **Confusion Trigger**: the linguistic feature causing the error.
- **Separating Feature**: for a merge across opposite verdicts, the feature that decides which
  verdict applies. Write "n/a" for a single-verdict group.
- **Contrastive Evidence**: how the True Positives avoid the trigger.
- **Linguistic Rule (Proposed)**: the precise logic, covering every cluster in this group.

## GROUP 2 [clusters: 1]
...

## UNRESOLVABLE [clusters: ]
State "none", or list the cluster numbers and say what could not be separated.
""".strip()

HEADING = re.compile(r"^##\s+(GROUP\s+\d+|UNRESOLVABLE)\s*\[clusters:\s*([0-9,\s]*)\]\s*$",
                     re.M | re.I)


def render_clusters(clusters, n_examples: int) -> str:
    blocks = []
    for index, cluster in enumerate(clusters, 1):
        body = iterative._build_discrepant_examples_from_cluster(cluster, n_examples)
        blocks.append(f"### CLUSTER {index}: {cluster['key'] if isinstance(cluster, dict) else cluster.key}"
                      f" ({cluster.count} cases)\n{body}")
    return "\n\n".join(blocks)


def parse_groups(text: str, count: int):
    """[(cluster indices, pattern text)], and the indices reported unresolvable."""
    marks = list(HEADING.finditer(text))
    if not marks:
        return None, []
    groups, unresolvable = [], []
    for position, mark in enumerate(marks):
        end = marks[position + 1].start() if position + 1 < len(marks) else len(text)
        body = text[mark.end():end].strip()
        members = [int(n) for n in re.findall(r"\d+", mark.group(2))
                   if 1 <= int(n) <= count]
        if mark.group(1).upper().startswith("UNRESOLVABLE"):
            unresolvable = members
        elif members:
            groups.append((members, f"{mark.group(0).strip()}\n{body}"))
    return (groups or None), unresolvable


def joint_refine(sampled_documents, predictions, current_guidelines, entities, summary,
                 provider, n_examples, *, k: int):
    clusters = summary.all_clusters[:k] or [summary.dominant_cluster]
    entity_schema = iterative._entity_schema_text(entities)
    true_positive_examples = iterative._build_true_positive_examples(
        sampled_documents, predictions, n_examples)
    verified_examples = iterative._build_verified_examples(
        sampled_documents, predictions, n_examples)

    prompts = {"infer_discrepancy_patterns_joint": render_prompt(
        "infer_discrepancy_patterns_joint",
        entity_schema=entity_schema,
        clusters=render_clusters(clusters, n_examples),
        true_positive_examples=true_positive_examples,
    )}
    insight = provider.complete("infer_discrepancy_patterns_joint",
                                prompts["infer_discrepancy_patterns_joint"])

    groups, unresolvable = parse_groups(insight, len(clusters))
    if groups is None:
        # Nothing parsed: fall back to one principle over every cluster rather
        # than silently dropping the round's analysis.
        groups = [(list(range(1, len(clusters) + 1)), insight)]
        print("    joint analysis: no GROUP headings found, treating it as one group", flush=True)
    print(f"    joint analysis: {len(clusters)} clusters -> {len(groups)} group(s)"
          + (f", unresolvable {unresolvable}" if unresolvable else ""), flush=True)

    principles = []
    for rank, (members, pattern) in enumerate(groups, 1):
        evidence = "\n\n".join(
            iterative._build_discrepant_examples_from_cluster(clusters[m - 1], n_examples)
            for m in members)
        keys = "; ".join(clusters[m - 1].key for m in members)
        name = f"generate_moderation_principle_{rank}"
        prompts[name] = render_prompt(
            "generate_moderation_principle",
            entity_schema=entity_schema,
            discrepancy_pattern=f"{keys}\n\n**INFERRED PATTERNS:**\n{pattern}",
            discrepant_examples=evidence,
        )
        principles.append(f"### {rank}. {keys}\n{provider.complete(name, prompts[name])}")

    prompts["refine_guidelines"] = render_prompt(
        "refine_guidelines",
        guidelines=current_guidelines or "(no guidelines provided)",
        new_principles="\n\n".join(principles),
        verified_examples=verified_examples,
    )
    refined = provider.complete("refine_guidelines", prompts["refine_guidelines"])
    return refined, insight, "\n\n".join(principles), prompts


def main() -> None:
    parser = argparse.ArgumentParser(description="Joint analysis over the top k groups.")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--run-name")
    parser.add_argument("--dev-split")
    parser.add_argument("--n-examples", type=int)
    args = parser.parse_args()
    assert args.k >= 2, "--k below 2 leaves nothing to reconcile"

    PROMPT_TEMPLATES["infer_discrepancy_patterns_joint"] = JOINT_TEMPLATE
    published = PROMPT_TEMPLATES["refine_guidelines"]
    PROMPT_TEMPLATES["refine_guidelines"] = build_template(published)

    # The principle prompt must stay as published: this experiment differs from
    # moderate_topk.py in the analysis stage only.
    assert "ONE Core Moderation Principle" in PROMPT_TEMPLATES["generate_moderation_principle"]
    assert set(re.findall(r"\{(\w+)\}", JOINT_TEMPLATE)) == {
        "entity_schema", "clusters", "true_positive_examples"}

    iterative._refine_guidelines_from_pairs = functools.partial(joint_refine, k=args.k)
    print(f"joint moderation over the top {args.k} groups: 1 analysis call + at most {args.k} "
          f"principle calls + 1 rewrite per round")

    spec = json.loads(
        (REPO_ROOT / "experiments/ncbi_disease_valid_round1.spec.json").read_text(encoding="utf-8"))
    spec["experiment_id"] = EXPERIMENT_ID
    spec["description"] = f"Published spec, top {args.k} groups reconciled in one analysis call."
    spec_path = Path(__file__).resolve().parent / "moderate_joint.spec.json"
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
