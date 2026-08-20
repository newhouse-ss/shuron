"""Ablation: remove verified examples from the guideline-refinement prompt. Then run refinement.

WHY
---
Section 3.4.4 describes verified examples (true positives) as "in-prompt
checks": the model is told not to introduce changes that would flip cases it
already handles correctly. In the released implementation that block occupies
46% of the refinement prompt (8,170 of 17,605 characters in round 1) and carries
18 true positives together with the *full text* of five development documents.

The model does not treat it as a constraint; it treats it as material. All seven
newly written guideline entries sampled from round 1 correspond to true
positives from that block, none to the discrepancy cluster the round was
moderating. Over four rounds the guideline grew from 7,367 to 19,940 characters,
15 of 43 development-set entity strings were written in verbatim, and
development-set F1 rose +0.11 while held-out F1 rose +0.01.

HYPOTHESIS
----------
Removing the block stops the guideline absorbing development-set content, so
inflation and leakage disappear together. Regression protection is not lost: the
loop already gates on `improved = F1_after > F1_before`, a net check backed by a
real re-annotation rather than a sentence in a prompt.

SCOPE
-----
Single variable. Only the CONSTRAINT block and the CONSTRAINT CHECK instruction
that refers to it are removed; everything else is verbatim and **no new
instruction is added** — a "do not add examples" directive would be a second
variable. True positives stay in `infer_discrepancy_patterns`, which Section
3.4.2 requires for contrastive analysis. Upstream source is untouched: the
template dict is overridden at runtime.

READING THE RESULT
------------------
Guideline size and verbatim-entity count are decisive — an order of magnitude
apart if the hypothesis holds. F1 and iteration count are not: a rerun differs
from the original even with no change, the same prompt at `high` effort having
consumed 9,214 and 23,375 reasoning tokens on two occasions.

    python reproduction/ablation_no_tp.py --azure-model-key 5_4
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

# The published template with the CONSTRAINT block and CONSTRAINT CHECK removed
# and the remaining instructions renumbered. Nothing else differs.
ABLATED_REFINE_GUIDELINES = """
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

EXPERIMENT_ID = "ncbi_ablation_noTP"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the no-verified-examples ablation.")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    parser.add_argument("--run-name", help="Output folder name, e.g. 20260805_ncbi_gpt54-high_moderation-noTP")
    parser.add_argument("--dev-split", help="Document list from reproduction/make_dev_splits.py")
    parser.add_argument("--n-examples", type=int,
                        help="Prompt evidence count. Scale it with the dev split, since the "
                             "published value of 5 was calibrated for 10 documents.")
    args = parser.parse_args()

    original = PROMPT_TEMPLATES["refine_guidelines"]
    assert "{verified_examples}" in original, "nothing to ablate"
    PROMPT_TEMPLATES["refine_guidelines"] = ABLATED_REFINE_GUIDELINES
    # str.format ignores surplus keyword arguments, so iterative.py can keep
    # passing verified_examples= without modification.
    assert set(re.findall(r"\{(\w+)\}", ABLATED_REFINE_GUIDELINES)) == {"guidelines", "new_principles"}
    print(f"refine_guidelines template: {len(original)} -> {len(ABLATED_REFINE_GUIDELINES)} chars")

    # Same published spec, only the experiment id changed so outputs stay separate.
    spec = json.loads((REPO_ROOT / "experiments/ncbi_disease_valid_round1.spec.json").read_text(encoding="utf-8"))
    spec["experiment_id"] = EXPERIMENT_ID
    spec["description"] = "Ablation of the verified-examples block; identical to the published spec otherwise."
    spec_path = Path(__file__).resolve().parent / "ablation_no_tp.spec.json"
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
