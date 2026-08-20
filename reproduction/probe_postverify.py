"""Feasibility probe: post-hoc verification instead of in-prompt verified examples.

THE PROBLEM
-----------
The verified-examples block does two jobs at once. It suppresses regressions,
which is why the published run climbs for four rounds while every ablated run
stalls within three. It also hands the model 18 answers and five full
development documents, which is where the hardcoding comes from - 15 of 43
development entity strings end up verbatim in the guideline.

THE IDEA
--------
Keep the function, drop the mechanism. Generate the guideline from the principle
alone, then *check by re-annotating* whether anything that used to be right just
broke, and hand the broken cases back as errors for a revision.

Regressions cannot be driven to zero - annotation varies run to run, and a rule
that fixes six cases legitimately breaks one or two. So this is a budget, not a
gate: try up to MAX_ATTEMPTS drafts and keep the best.

CONDITIONS
----------
Attempt 1 never receives feedback, so within every condition it is that
condition's own no-feedback control and no separate run is needed.

  A  feedback names the mention and its correct label
     Result on dev10: regressions 4 -> 0, F1 -0.0081 -> +0.0220, but 6 of 43
     development entity strings landed verbatim in the guideline against 0 for
     the unfed draft. The pair (string, label) is directly transcribable.

  B  feedback gives only the character span and the entity type
     Result on dev10: regressions 4, 5, 5, 6, 4 over five attempts and no draft
     ever reached the pre-refinement baseline. Withholding the mention removes
     the copyable unit and the model's ability to diagnose along with it.
     (Caveat: B started from a different baseline and a different dominant
     cluster than A, so the two are not a controlled pair.)

  C  A's feedback plus an abstraction constraint on the refinement prompt
     Step 3.4.3 already carries such a constraint and it holds: across nine
     rounds the generated principles contained 0 development entity strings in
     seven of them and 1 in the other two, while the guidelines those same
     rounds produced accumulated 10, 12, 13, 15... So the model does abstract
     when told to. Section 3.4.4 simply never tells it to. C adds the missing
     instruction and changes nothing else.

     Watch out for two things. The existing instruction "maintain the original
     formatting and structure" points the other way, since the original
     guideline is full of worked examples, so the constraint is scoped to
     additions. And the hardcoding measure only catches verbatim copies - a
     model told not to copy may simply paraphrase, which would read as success.
     Guideline growth and the shape of the additions have to be read alongside.

Cost is roughly MAX_ATTEMPTS x |dev| annotations plus that many generations.

    python reproduction/probe_postverify.py --condition C
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_guideline_moderation import iterative as it  # noqa: E402
from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402
from llm_guideline_moderation.prompts import PROMPT_TEMPLATES, render_prompt  # noqa: E402
from llm_guideline_moderation.providers.openai import OpenAIProvider  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402

MAX_ATTEMPTS = 5

# Same ablated template as reproduction/ablation_no_tp.py: no verified examples.
ABLATED = """
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

# Condition C only. Worded after the constraint in generate_moderation_principle,
# which measurably holds, and scoped to additions so it does not fight the
# existing "maintain the original formatting and structure" instruction.
ABSTRACTION_CONSTRAINT = """
3. **GENERALISATION — applies to everything you add**:
   - State each addition as an abstract rule, in terms of linguistic categories
     (syntactic role, semantic head type, discourse context) rather than the
     particular words you were shown.
   - Do NOT quote or paraphrase sentences from the discrepancy or regression
     material, and do NOT build new worked examples out of the mentions listed
     there. Those mentions are evidence for inferring a rule, not content.
   - If an illustration is genuinely required, invent a minimal phrase of your
     own; do not lift one from the material.
   - Examples already present in the Current Guidelines stay as they are. This
     constraint governs what you add, not what is already written.
"""

# Retry preamble. The regression list itself is produced by the condition's
# feedback function below.
REGRESSION_PREAMBLE = {
    # A and C name the mention and its correct label.
    "text": """**REGRESSIONS CAUSED BY YOUR PREVIOUS DRAFT:**
Your previous revision was tested by re-annotating the documents. The mentions
listed below were annotated correctly before the revision and are wrong after
it. Diagnose which of your new wordings caused each regression and revise so
that the new principles still apply while these cases return to being correct.
{regressions}

**INSTRUCTIONS:**""",
    # B gives position and type only.
    "position": """**REGRESSIONS CAUSED BY YOUR PREVIOUS DRAFT:**
Your previous revision was tested by re-annotating the documents. The annotations
listed below were correct before the revision and are wrong after it. Each is
given by document, character span and entity type; the mention text is withheld
on purpose. Work out which of your new wordings is over-applying or
under-applying to cases of that type, and revise so the new principles still hold
without disturbing them.
{regressions}

**INSTRUCTIONS:**""",
}


def build_templates(condition: str) -> tuple[str, str]:
    """Return (first-draft template, retry template) for a condition."""
    base = ABLATED
    if condition == "C":
        base = base.replace("\n3. Maintain the original formatting and structure.",
                            ABSTRACTION_CONSTRAINT.rstrip() + "\n4. Maintain the original formatting and structure.")
        for old, new in [("\n4. Return the FULL", "\n5. Return the FULL"),
                         ("\n5. **CRITICAL", "\n6. **CRITICAL"),
                         ("\n6. Output ONLY", "\n7. Output ONLY")]:
            base = base.replace(old, new)
    style = "position" if condition == "B" else "text"
    return base, base.replace("**INSTRUCTIONS:**", REGRESSION_PREAMBLE[style], 1)


def annotate(documents, guidelines, entities, provider):
    return it._annotate_documents(
        documents, guidelines, entities, provider, "",
        OutputConfiguration(include_rationale=True, include_guideline_section=True),
    )


def true_positive_keys(documents, predictions):
    keys = set()
    for document in documents:
        gold = {(a.start, a.end, a.entity) for a in document.gold_annotations}
        pred = {(a.start, a.end, a.entity) for a in predictions.get(document.filename, [])}
        keys |= {(document.filename, *k) for k in gold & pred}
    return keys


def describe_with_text(documents, lost):
    """Conditions A and C: the mention, its correct label, +-60 characters of context."""
    by_doc = {}
    for filename, start, end, label in sorted(lost):
        by_doc.setdefault(filename, []).append((start, end, label))
    index = {d.filename: d for d in documents}
    lines = []
    for filename, spans in by_doc.items():
        text = index[filename].text
        lines.append(f"FILE: {filename}")
        for start, end, label in spans:
            window = text[max(0, start - 60):end + 60].replace("\n", " ")
            lines.append(f'- "{text[start:end]}" should be {label}   context: ...{window}...')
    return "\n".join(lines)


def describe_position_only(documents, lost):
    """Condition B: character span and entity type, mention withheld."""
    by_doc = {}
    for filename, start, end, label in sorted(lost):
        by_doc.setdefault(filename, []).append((start, end, label))
    lines = []
    for filename, spans in by_doc.items():
        lines.append(f"FILE: {filename}")
        for start, end, label in spans:
            lines.append(
                f"- a {label} annotation at characters [{start}, {end}] was correct "
                f"before your revision and is wrong after it"
            )
    return "\n".join(lines)


FEEDBACK = {"A": describe_with_text, "B": describe_position_only, "C": describe_with_text}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--condition", choices=["A", "B", "C"], default="C",
                        help="A: mention+label feedback. B: position+label only. "
                             "C: A plus an abstraction constraint on the refinement prompt.")
    parser.add_argument("--dev-split", default="reproduction/dev_splits/ncbi_disease_dev10.json")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--out")
    args = parser.parse_args()
    out_path = Path(args.out or f"reproduction/results/postverify_probe_cond{args.condition}.json")

    load_dotenv()
    first_draft_template, retry_template = build_templates(args.condition)
    describe = FEEDBACK[args.condition]
    PROMPT_TEMPLATES["refine_guidelines"] = first_draft_template
    print(f"condition {args.condition}   first-draft template {len(first_draft_template)} chars, "
          f"retry {len(retry_template)} chars")

    names = json.loads(Path(args.dev_split).read_text(encoding="utf-8"))["documents"]
    documents = [load_sampled_document(REPO_ROOT / "data/datasets/ncbi_disease/train" / n) for n in names]
    guidelines = (REPO_ROOT / "data/guidelines/ncbi_disease_guidelines.txt").read_text(encoding="utf-8")
    entities = [EntityDefinition(name=r) for r in json.loads(
        (REPO_ROOT / "data/schemas/ncbi_entities.schema.json").read_text(encoding="utf-8"))]
    provider = OpenAIProvider.from_azure_env(args.azure_model_key, reasoning_effort=args.reasoning_effort)

    print(f"{len(documents)} documents, {sum(len(d.gold_annotations) for d in documents)} gold annotations\n")

    baseline_predictions = annotate(documents, guidelines, entities, provider)
    baseline = it._summarize_moderation_pairs(it._build_pairs(documents, baseline_predictions), 0.9) # what is it?
    baseline_tps = true_positive_keys(documents, baseline_predictions)
    print(f"baseline   F1={baseline.overall_f1:.4f}  TP={baseline.true_positives}  "
          f"target={baseline.dominant_cluster.key} (n={baseline.dominant_cluster.count})\n")

    refined, insight, principle, _ = it._refine_guidelines_from_pairs(
        sampled_documents=documents, predictions=baseline_predictions,
        current_guidelines=guidelines, entities=entities, summary=baseline,
        provider=provider, n_examples=5,
    )

    attempts, best = [], None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        predictions = annotate(documents, refined, entities, provider)
        summary = it._summarize_moderation_pairs(it._build_pairs(documents, predictions), 0.9)
        lost = baseline_tps - true_positive_keys(documents, predictions)
        delta = summary.overall_f1 - baseline.overall_f1
        label = "no-verification baseline" if attempt == 1 else f"after regression feedback #{attempt - 1}"
        print(f"attempt {attempt} ({label})")
        print(f"   F1={summary.overall_f1:.4f} ({delta:+.4f})  TP={summary.true_positives}  "
              f"regressions={len(lost)}  guideline={len(refined)} chars")

        attempts.append({"attempt": attempt, "f1": summary.overall_f1, "delta": delta,
                         "regressions": len(lost), "guideline_chars": len(refined),
                         "guideline": refined})
        if best is None or summary.overall_f1 > best["f1"]:
            best = attempts[-1]

        if not lost or attempt == MAX_ATTEMPTS:
            if not lost:
                print("   no regressions left, stopping")
            break

        PROMPT_TEMPLATES["refine_guidelines"] = retry_template
        refined = provider.complete("refine_guidelines", render_prompt(
            "refine_guidelines", guidelines=guidelines, new_principles=principle,
            regressions=describe(documents, lost),
        ))

    print(f"\nbest = attempt {best['attempt']}  F1={best['f1']:.4f} ({best['delta']:+.4f})")
    print("verification helped" if best["attempt"] > 1 else
          "verification did not beat its own first draft")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "condition": args.condition, "dev_split": args.dev_split,
        "baseline_f1": baseline.overall_f1,
        "target": baseline.dominant_cluster.key, "principle": principle,
        "attempts": attempts, "best_attempt": best["attempt"],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"written to {out_path}")


if __name__ == "__main__":
    main()
