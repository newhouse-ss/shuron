"""Guideline refinement with post-hoc verification in place of in-prompt examples.

WHY
---
The published `refine_guidelines` prompt carries a CONSTRAINT block holding true
positives and the full text of five development documents. It does two jobs:

  * it suppresses regressions, which is why the published run climbs for four
    rounds while all five ablated runs stall within three and none passes 0.87;
  * it hands over transcribable answers, which is where the hardcoding comes
    from - 15 of 43 development entity strings end up verbatim in the guideline,
    12% of everything the four rounds added.

Removing the block cleanly removes the second and destroys the first. They are
the same mechanism: the guideline climbs on the development set by restating
answers already in its own prompt.

APPROACH
--------
Keep the function, move it out of the prompt. Generate from the principle alone,
then *test the draft by re-annotating* and see which previously-correct
annotations it broke. Feed those back as errors and ask for a revision. True
positives are still what protects against regression, but they are consulted by
running the annotator, not by pasting them into the text the model is writing.

WHAT WE ALREADY KNOW ABOUT THE PIECES
-------------------------------------
Feedback naming the mention and its label drove regressions 4 -> 0 in one round
and lifted F1 from -0.0081 to +0.0220, at the cost of 6 of 43 entity strings
appearing in the guideline. Feedback giving only the character span and entity
type left regressions at 4, 5, 5, 6, 4 across five attempts with no draft ever
reaching the pre-refinement baseline: withholding the mention removes the
copyable unit and the ability to diagnose along with it. So the mention text
stays, and hardcoding is attacked separately.

That separate attack is an abstraction constraint, which is not speculative -
`generate_moderation_principle` already carries one and it holds. Across nine
rounds the principles it produced contained 0 development entity strings in
seven and 1 in the other two, while the guidelines written in those same rounds
accumulated 10, 12, 13, 15. Same model, same evidence, opposite behaviour. The
only difference is that Section 3.4.4 never asks for abstraction. This adds it.

DESIGN DECISIONS THAT MATTER FOR READING THE NUMBERS
----------------------------------------------------
Drafts are accepted on fewest regressions, ties broken by development F1. The
loop's job is regression suppression, so it selects on regressions; F1 is the
outcome being measured and selecting on it would bias the result upward - with
annotation as variable as it is here, the best of N noisy draws beats the first
draw about (N-1)/N of the time for no reason at all.

The accepted draft is then re-annotated by the outer loop before the round's
improvement is judged. That evaluation is an independent sample, not the one
used to choose the draft, so the accept/revert decision is not made on the same
draw that selected it.

Regression feedback never claims the model can see its previous draft, because
it cannot - the retry prompt carries the current guideline, not the rejected
one. It states what breaks when the principles are written in, and nothing about
authorship or history.

Zero regressions is not the target and is not reachable: annotation varies run
to run, and a rule that genuinely fixes six cases will break one or two. The
budget bounds the attempts and the best draft is kept regardless.

    python reproduction/verified_refinement.py --dev-split reproduction/dev_splits/ncbi_disease_dev10.json \
        --run-name 20260814_ncbi_gpt54-high_verified_dev10
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from llm_guideline_moderation import iterative as it  # noqa: E402
from llm_guideline_moderation.prompts import PROMPT_TEMPLATES, render_prompt  # noqa: E402
from llm_guideline_moderation.types import OutputConfiguration  # noqa: E402

# ---------------------------------------------------------------- prompts ----

# The published template minus the CONSTRAINT block and the CONSTRAINT CHECK
# instruction that refers to it. Nothing else is altered.
GENERATE = """
You are an expert AI Moderator.

**GOAL:**
Update the official Annotation Guidelines to incorporate new "Moderation Principles" discovered from error analysis.

**CURRENT GUIDELINES:**
{guidelines}

**NEW MODERATION PRINCIPLES:**
{new_principles}

**INSTRUCTIONS:**
1. Read the Current Guidelines and the New Principles.
2. Integrate the New Principles into the Guidelines naturally.
   - Do NOT just append them at the end unless it makes sense.
   - If an existing rule contradicts the new principle, update it.
   - **Conflict Resolution**: If the new principle necessitates changing an existing rule, explicitly justify (in your internal thought process) why the new rule is superior (e.g., more specific, resolves an ambiguity).
   - If the new principle clarifies a specific section, add it there.
3. Maintain the original formatting and structure.
4. Return the FULL updated Guidelines text.
5. **CRITICAL INSTRUCTION**: Models often try to summarize or use placeholders like "(...)" to save tokens. **DO NOT DO THIS.** YOU MUST OUTPUT THE COMPLETED DOCUMENT IN FULL. If you leave out any section, the file will be corrupted.
6. Output ONLY the guideline text. Do not start with "Here are the updated guidelines:".
""".strip()

# Scoped to additions so it does not contradict "maintain the original
# formatting and structure" - the existing guideline is full of worked examples
# and the instruction to preserve its style would otherwise license more.
ABSTRACTION = """3. **GENERALISATION — governs everything you add**:
   - State each addition as an abstract rule, in terms of linguistic categories
     (syntactic role, semantic head type, discourse context) rather than the
     particular words you were shown.
   - Do NOT quote or paraphrase sentences from the evidence, and do NOT build
     worked examples out of the mentions listed in it. Those mentions are
     evidence for inferring a rule, not content to be written down.
   - If an illustration is genuinely needed, invent a minimal phrase of your
     own rather than lifting one from the evidence.
   - Examples already in the Current Guidelines stay as they are. This governs
     what you add, not what is already written.
"""

# Stated as a property of the principles, not as a history of drafts: the retry
# prompt carries the current guideline, so there is no previous draft in it to
# refer to.
REGRESSION_BLOCK = """**ANNOTATIONS THAT BREAK UNDER THESE PRINCIPLES:**
Writing the principles above into the guideline was tested by re-annotating the
documents. The mentions below are annotated correctly under the current
guideline and incorrectly once the principles are written in. Work out what
phrasing would over-apply or under-apply to them, and write the revision so the
principles hold without disturbing these cases.
{regressions}

**INSTRUCTIONS:**"""


def build_prompts(abstraction: bool) -> tuple[str, str]:
    """Return (first draft template, retry template)."""
    generate = GENERATE
    if abstraction:
        generate = generate.replace(
            "3. Maintain the original formatting and structure.",
            ABSTRACTION + "4. Maintain the original formatting and structure.",
        )
        for old, new in (("\n4. Return the FULL", "\n5. Return the FULL"),
                         ("\n5. **CRITICAL", "\n6. **CRITICAL"),
                         ("\n6. Output ONLY", "\n7. Output ONLY")):
            generate = generate.replace(old, new)
    return generate, generate.replace("**INSTRUCTIONS:**", REGRESSION_BLOCK, 1)


# ------------------------------------------------------------ verification ---


def true_positives(documents, predictions) -> set[tuple]:
    """Annotations the model got exactly right: same span, same type."""
    keys = set()
    for document in documents:
        gold = {(a.start, a.end, a.entity) for a in document.gold_annotations}
        pred = {(a.start, a.end, a.entity) for a in predictions.get(document.filename, [])}
        keys |= {(document.filename, *k) for k in gold & pred}
    return keys


def render_regressions(documents, lost, context: int = 60) -> str:
    """The mention, its correct type, and a narrow window - never the whole document.

    The document body is what the CONSTRAINT block supplied and what the model
    quoted from; a window wide enough to place the mention is not.
    """
    index = {d.filename: d for d in documents}
    by_document: dict[str, list] = {}
    for filename, start, end, label in sorted(lost):
        by_document.setdefault(filename, []).append((start, end, label))

    lines = []
    for filename, spans in by_document.items():
        text = index[filename].text
        lines.append(f"FILE: {filename}")
        for start, end, label in spans:
            window = text[max(0, start - context):end + context].replace("\n", " ")
            lines.append(f'- "{text[start:end]}" is {label}   context: ...{window}...')
    return "\n".join(lines)


@dataclass(slots=True)
class Draft:
    attempt: int
    guidelines: str
    f1: float
    regressions: int

    def better_than(self, other: "Draft | None") -> bool:
        """Fewest regressions wins; development F1 breaks ties.

        Selecting on F1 would bias the reported outcome upward, since the best
        of several noisy drafts beats the first for no reason at all. Regression
        count is what this loop exists to reduce, so it is what it selects on.
        """
        if other is None:
            return True
        return (self.regressions, -self.f1) < (other.regressions, -other.f1)


class VerifyingRefiner:
    """Drop-in replacement for iterative._refine_guidelines_from_pairs."""

    def __init__(self, max_attempts: int, abstraction: bool, output_configuration):
        self.max_attempts = max_attempts
        self.generate_template, self.retry_template = build_prompts(abstraction)
        self.output_configuration = output_configuration
        self.log: list[dict] = []

    def __call__(self, *, sampled_documents, predictions, current_guidelines,
                 entities, summary, provider, n_examples):
        protected = true_positives(sampled_documents, predictions)

        # The discrepancy analysis, pattern explanation and principle generation
        # are the published ones; only the guideline-writing step is replaced.
        PROMPT_TEMPLATES["refine_guidelines"] = self.generate_template
        guidelines, insight, principle, prompts = self._original(
            sampled_documents=sampled_documents, predictions=predictions,
            current_guidelines=current_guidelines, entities=entities,
            summary=summary, provider=provider, n_examples=n_examples,
        )

        best: Draft | None = None
        round_log = []
        for attempt in range(1, self.max_attempts + 1):
            trial = it._annotate_documents(
                sampled_documents, guidelines, entities, provider, "",
                self.output_configuration,
            )
            lost = protected - true_positives(sampled_documents, trial)
            score = it._summarize_moderation_pairs(
                it._build_pairs(sampled_documents, trial), 1.0
            ).overall_f1
            draft = Draft(attempt, guidelines, score, len(lost))
            round_log.append({"attempt": attempt, "f1": score, "regressions": len(lost),
                              "guideline_chars": len(guidelines)})
            print(f"    attempt {attempt}: F1={score:.4f}  regressions={len(lost)}  "
                  f"guideline={len(guidelines)} chars", flush=True)

            if draft.better_than(best):
                best = draft
            if not lost or attempt == self.max_attempts:
                break

            PROMPT_TEMPLATES["refine_guidelines"] = self.retry_template
            guidelines = provider.complete("refine_guidelines", render_prompt(
                "refine_guidelines", guidelines=current_guidelines,
                new_principles=principle,
                regressions=render_regressions(sampled_documents, lost),
            ))

        print(f"    accepted attempt {best.attempt} "
              f"(regressions={best.regressions}, F1={best.f1:.4f})", flush=True)
        self.log.append({"attempts": round_log, "accepted": best.attempt})
        prompts["verification"] = json.dumps(
            {"attempts": round_log, "accepted": best.attempt}, indent=2)
        return best.guidelines, insight, principle, prompts

    _original = staticmethod(it._refine_guidelines_from_pairs)


# ----------------------------------------------------------------- driver ----


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dev-split", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Drafts per round, including the unfed first one")
    parser.add_argument("--no-abstraction", action="store_true",
                        help="Drop the generalisation constraint, isolating its effect")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--spec", default="experiments/ncbi_disease_valid_round1.spec.json")
    args = parser.parse_args()

    refiner = VerifyingRefiner(
        max_attempts=args.max_attempts,
        abstraction=not args.no_abstraction,
        output_configuration=OutputConfiguration(include_rationale=True,
                                                 include_guideline_section=True),
    )
    it._refine_guidelines_from_pairs = refiner

    print(f"verification on, {args.max_attempts} drafts per round, "
          f"abstraction constraint {'off' if args.no_abstraction else 'on'}")

    import run_iterative_refinement as runner

    sys.argv = [
        "run_iterative_refinement.py",
        "--spec", args.spec,
        "--dev-split", args.dev_split,
        "--run-name", args.run_name,
        "--azure-model-key", args.azure_model_key,
        "--reasoning-effort", args.reasoning_effort,
        "--max-output-tokens", str(args.max_output_tokens),
    ]
    runner.main()


if __name__ == "__main__":
    main()
