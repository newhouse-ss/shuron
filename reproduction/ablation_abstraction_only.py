"""Experiment 2: keep the verified-examples block, forbid verbatim copying.

WHAT THIS TESTS
---------------
The CONSTRAINT block of verified examples does two jobs at once. It tells the
model not to break cases that already pass, and it says what those cases are.
Removing it (`ablation_no_tp.py`) killed the copying, 0/37 in every run, and
killed the loop's ability to keep improving along with it: all five ablation
runs stalled within one to three rounds and none reached the threshold the
published run reaches.

So the block cannot go. This asks whether it can stay while the copying stops,
by adding one instruction to the same prompt: state each addition as a rule, do
not transcribe the mentions you were shown.

WHY IT MIGHT WORK
-----------------
The pipeline already contains a control for this. Every round writes two things:
a *principle* at Section 3.4.3 and the *guideline* at Section 3.4.4. Both run in
the same round with the same true positives available, since the pattern
explanation feeding 3.4.3 quotes them as "Contrastive Evidence" and 11 of the 37
development mention strings appear verbatim in the principle prompt. The
difference is that 3.4.3 is told to state a general rule and 3.4.4 is not.

Across the four rounds of the published run the principles contain 0 development
mention strings; the guidelines accumulate 10, 12, 13, 15.

WHY THAT IS NOT ENOUGH TO SKIP THE RUN
--------------------------------------
The four principles total 2,430 characters against 12,573 characters of new
guideline text. At the guideline's rate of 1.19 strings per 1,000 characters,
2.9 would be expected in the principles, so observing 0 has p ~ 0.06. Consistent
with the instruction working, equally consistent with a short output having less
room to hold anything.

SCOPE
-----
Single variable against the published configuration: the GENERALISATION block is
inserted and the following instructions are renumbered. The CONSTRAINT block,
the CONSTRAINT CHECK, and every other instruction are byte-identical to the
published template. Upstream source is untouched; the template dict is
overridden at runtime.

READING THE RESULT
------------------
Three numbers against the two runs that bracket this one:

                         absorption   dev F1        rounds
    withTP  (published)  15/37 = 41%  0.7972->0.9091   4
    noTP    (ablation)   0/37 = 0%    stalls           1-3
    this run             ?            ?                ?

Absorption near 0 with the loop still climbing is the outcome that would make
the block salvageable. Absorption near 0 with an early stall means the
instruction did what deletion did. Absorption still high means the model
ignores the instruction when the material is in front of it.

One caveat carries over: the measure catches verbatim copies only. A model told
not to copy may paraphrase instead, which would read as success, so guideline
growth has to be read alongside the count.

    python reproduction/ablation_abstraction_only.py --azure-model-key 5_4
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from llm_guideline_moderation.prompts import PROMPT_TEMPLATES  # noqa: E402

# Scoped to additions so it does not contradict "maintain the original
# formatting and structure": the shipped guideline is full of worked examples
# and an instruction to preserve its style would otherwise license more.
GENERALISATION = """4. **GENERALISATION - governs everything you add**:
   - State each addition as an abstract rule, in terms of linguistic categories
     (syntactic role, semantic head type, discourse context) rather than the
     particular words you were shown.
   - Do NOT quote or paraphrase sentences from the CONSTRAINT examples, and do
     NOT build worked examples out of the mentions listed there. Those mentions
     are evidence for inferring a rule, not content to be written down.
   - If an illustration is genuinely needed, invent a minimal phrase of your own
     rather than lifting one from the evidence.
   - Examples already in the Current Guidelines stay as they are. This governs
     what you add, not what is already written.
"""

EXPERIMENT_ID = "ncbi_ablation_abstraction"


def build_template(published: str) -> str:
    """Published template with GENERALISATION inserted as instruction 4."""
    anchor = "4. Maintain the original formatting and structure."
    assert anchor in published, "instruction numbering changed upstream"
    out = published.replace(anchor, GENERALISATION + "5. Maintain the original formatting and structure.")
    for old, new in (("\n5. Return the FULL", "\n6. Return the FULL"),
                     ("\n6. **CRITICAL", "\n7. **CRITICAL"),
                     ("\n7. Output ONLY", "\n8. Output ONLY")):
        assert old in out, f"missing instruction {old!r}"
        out = out.replace(old, new)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the abstraction-constraint experiment.")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--run-name", help="Output folder name")
    parser.add_argument("--dev-split", help="Document list from reproduction/make_dev_splits.py")
    parser.add_argument("--n-examples", type=int,
                        help="Prompt evidence count. Scale it with the dev split, since the "
                             "published value of 5 was calibrated for 10 documents.")
    args = parser.parse_args()

    published = PROMPT_TEMPLATES["refine_guidelines"]
    template = build_template(published)

    # The block and its check must survive: this experiment differs from the
    # published run by one added instruction, not by a removal.
    assert "{verified_examples}" in template, "the CONSTRAINT block must stay"
    assert "CONSTRAINT CHECK" in template, "the CONSTRAINT CHECK must stay"
    assert set(re.findall(r"\{(\w+)\}", template)) == {"guidelines", "new_principles", "verified_examples"}
    PROMPT_TEMPLATES["refine_guidelines"] = template
    print(f"refine_guidelines template: {len(published)} -> {len(template)} chars "
          f"(+{len(template) - len(published)}, one added instruction)")

    spec = json.loads((REPO_ROOT / "experiments/ncbi_disease_valid_round1.spec.json").read_text(encoding="utf-8"))
    spec["experiment_id"] = EXPERIMENT_ID
    spec["description"] = "Published spec plus a generalisation constraint on guideline additions."
    spec_path = Path(__file__).resolve().parent / "ablation_abstraction_only.spec.json"
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
