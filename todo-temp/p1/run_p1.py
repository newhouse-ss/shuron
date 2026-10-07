"""P1: ablate the scope-limiting second clause of the Round 3 moderation principle.

Run outputs/ncbi_disease/20260802_gpt54-high_moderation Round 3 generated a
two-part principle. Its second half ("do not apply this rule when the phrase
refers only to a normal biological process, a molecular/substance entity or
level, or an isolated descriptive finding ...") became guideline line 12 plus
the FALDH do-not-annotate example (iteration_03/guidelines_after.txt lines
41-44) that contradicts gold (SpecificDisease).

This replay changes exactly one variable: the saved refine_guidelines prompt of
Round 3 is reused verbatim except the principle is truncated before the
do-not-apply clause. Same guidelines_before (iteration_02 state), same
CONSTRAINT/verified-examples block, same 10 dev documents, same model
(Azure eastus2-gpt-5.4, reasoning high), same loop scorer.

    python todo-temp/p1_clause_ablation/run_p1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from llm_guideline_moderation import iterative as it
from llm_guideline_moderation.dotenv import load_dotenv
from llm_guideline_moderation.providers.openai import OpenAIProvider
from llm_guideline_moderation.sampling import load_sampled_document
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration

RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
OUT = Path(__file__).resolve().parent

CLAUSE = "; **do not apply this rule** when the phrase refers only to"

FOCUS = ["deficiency of norrin", "fatty aldehyde dehydrogenase", "spasticity",
         "abnormal retinal vascular development"]


def key(a):
    return (a["start"], a["end"], a["label"])


def keys(annotations):
    result = {key(a) for a in annotations}
    if len(result) != len(annotations):
        print(f"WARNING: {len(annotations) - len(result)} duplicate annotations")
    return result


def main() -> None:
    load_dotenv()
    OUT.mkdir(parents=True, exist_ok=True)

    snapshot = json.loads((RUN / "rounds/iteration_03/snapshot.json").read_text(encoding="utf-8"))
    principle = snapshot["moderation_principle"]
    prompt_original = snapshot["prompts"]["refine_guidelines"]

    assert CLAUSE in principle, "truncation point not found in saved principle"
    truncated = principle.split(CLAUSE)[0] + "."
    assert prompt_original.count(principle) == 1, "principle not unique in prompt"
    prompt_truncated = prompt_original.replace(principle, truncated)
    (OUT / "principle_original.txt").write_text(principle + "\n", encoding="utf-8")
    (OUT / "principle_truncated.txt").write_text(truncated + "\n", encoding="utf-8")
    (OUT / "prompt_truncated.txt").write_text(prompt_truncated, encoding="utf-8")
    print(f"principle: {len(principle)} -> {len(truncated)} chars; prompt diff is the clause only")

    provider = OpenAIProvider.from_azure_env("5_4", reasoning_effort="high", max_output_tokens=64000)

    candidate = provider.complete("refine_guidelines", prompt_truncated)
    (OUT / "guidelines_candidate_truncated.txt").write_text(candidate, encoding="utf-8")
    print(f"candidate guideline: {len(candidate)} chars "
          f"(original R3 result: {len(snapshot['guidelines_after'])} chars)")

    manifest = json.loads((RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))
    documents = [load_sampled_document(ROOT / d["path"]) for d in manifest]
    entity_rows = json.loads((ROOT / "data/schemas/ncbi_entities.schema.json").read_text(encoding="utf-8"))
    entities = [EntityDefinition(name=row) if isinstance(row, str) else EntityDefinition(**row)
                for row in entity_rows]

    trial = it._annotate_documents(
        documents, candidate, entities, provider, "",
        OutputConfiguration(include_rationale=True, include_guideline_section=True),
    )
    pairs = it._build_pairs(documents, trial)
    summary = it._summarize_moderation_pairs(pairs, 1.0)
    clusters = it._build_discrepancy_clusters(pairs)

    # Per-entity strict comparison across three states on the same 10 documents:
    # R2-after (= R3-before), R3-after original principle, R3 truncated candidate.
    stage_files = {
        "R2_after": {f["filename"]: f for f in snapshot["diagnostics_before"]["files"]},
        "R3_original": {f["filename"]: f for f in snapshot["diagnostics_after"]["files"]},
    }
    trial_files = {}
    for doc in documents:
        trial_files[doc.filename] = [
            {"start": a.start, "end": a.end, "label": a.entity, "text": a.text}
            for a in trial.get(doc.filename, [])
        ]

    per_doc = {}
    focus_history = []
    for doc in documents:
        name = doc.filename
        gold = keys(stage_files["R2_after"][name]["reference_denotations"])
        states = {
            "R2_after": keys(stage_files["R2_after"][name]["study_denotations"]),
            "R3_original": keys(stage_files["R3_original"][name]["study_denotations"]),
            "R3_truncated": keys(trial_files[name]),
        }
        counts = {s: {"tp": len(gold & p), "fp": len(p - gold), "fn": len(gold - p)}
                  for s, p in states.items()}
        per_doc[name] = counts
        for g in sorted(gold):
            text = doc.text[g[0]:g[1]]
            row = {"doc": name, "start": g[0], "end": g[1], "gold": g[2], "text": text}
            row.update({s: ("TP" if g in p else "miss") for s, p in states.items()})
            if any(x in text for x in FOCUS):
                focus_history.append(row)

    def totals(state):
        tp = sum(d[state]["tp"] for d in per_doc.values())
        fp = sum(d[state]["fp"] for d in per_doc.values())
        fn = sum(d[state]["fn"] for d in per_doc.values())
        return {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn)}

    gold_all = set()
    for doc in documents:
        gold_all |= {(doc.filename, *k) for k in keys(stage_files["R2_after"][doc.filename]["reference_denotations"])}
    pred_orig = set()
    pred_trunc = set()
    for doc in documents:
        pred_orig |= {(doc.filename, *k) for k in keys(stage_files["R3_original"][doc.filename]["study_denotations"])}
        pred_trunc |= {(doc.filename, *k) for k in keys(trial_files[doc.filename])}

    def rows(changed):
        return [{"doc": d, "start": s, "end": e, "label": l,
                 "text": next(x.text for x in documents if x.filename == d)[s:e]}
                for d, s, e, l in sorted(changed)]

    cand_lower = candidate.lower()
    exclusions = [line for line in candidate.splitlines()
                  if "do not annotate" in line.lower() or "not disease mention" in line.lower()]
    result = {
        "principle_original": principle,
        "principle_truncated": truncated,
        "candidate_chars": len(candidate),
        "guideline_still_excludes_faldh": "fatty aldehyde dehydrogenase" in cand_lower,
        "candidate_exclusion_lines": exclusions,
        "f1": {"R2_after": totals("R2_after"), "R3_original": totals("R3_original"),
               "R3_truncated": totals("R3_truncated"),
               "loop_summary_overall_f1": summary.overall_f1},
        "saved_R3_summary_f1": snapshot["summary_after"]["overall_f1"],
        "per_document": per_doc,
        "focus_cases": focus_history,
        "tp_gained_trunc_vs_original": rows((gold_all & pred_trunc) - pred_orig),
        "tp_lost_trunc_vs_original": rows((gold_all & pred_orig) - pred_trunc),
        "new_fp_trunc_vs_original": rows(pred_trunc - pred_orig - gold_all),
        "clusters_truncated": [{"key": c.key, "count": c.count} for c in clusters],
    }
    (OUT / "annotations_truncated.json").write_text(
        json.dumps(trial_files, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_document"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
