"""P2: rewrite the scope of the Round 3 principle's limiting clause, not delete it.

P1 showed that deleting the clause outright does not work: the refiner
regenerates equivalent restrictions, the three focus misses stay missed, dev F1
only reaches 0.8671 (vs 0.8873 with the clause), and SpecificDisease ->
DiseaseClass type errors double. P2 keeps a restriction but narrows its scope:

  original: "do not apply this rule when the phrase refers only to a normal
    biological process, a molecular/substance entity or level, or an isolated
    descriptive finding that is not presented as a pathological condition of
    the patient/disorder."
    -> the pathology qualifier binds only the LAST alternative, so
    "molecular/substance entity or level" sweeps up every "deficiency of X".

  scoped:   the pathology qualifier governs ALL alternatives, and a
    deficient/reduced/absent state presented as a pathological condition of the
    patient is explicitly carved back into the rule (without naming the
    specific gold entities, to avoid hard-coding answers).

Single variable: the first half of the principle is kept byte-identical; the
saved Round 3 refine prompt is reused verbatim apart from the clause swap.
Same 10 dev documents, model (Azure eastus2-gpt-5.4, high) and loop scorer.

The refine candidate and per-document annotations are checkpointed to disk so
an interrupted run can be resumed without redoing paid API calls.

    python todo-temp/p2_scoped_clause/run_p2.py
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
from llm_guideline_moderation.types import Annotation, EntityDefinition, OutputConfiguration

RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
P1 = ROOT / "todo-temp/p1/annotations_truncated.json"
OUT = Path(__file__).resolve().parent
CANDIDATE_PATH = OUT / "guidelines_candidate_scoped.txt"
ANNOTATIONS_PATH = OUT / "annotations_scoped.json"

CLAUSE = "; **do not apply this rule** when the phrase refers only to"

SCOPED_TAIL = (
    ". **Scope the exclusion narrowly**: do **not** apply this rule to a phrase "
    "that merely names or measures a normal biological process, a "
    "molecular/substance entity, level, or activity as such, or that states an "
    "isolated descriptive finding—**and only when** that phrase is **not** "
    "presented as a pathological condition of the patient/disorder. A phrase "
    "that presents a deficient, reduced, absent, or otherwise abnormal state "
    "of such an entity **as** a pathological condition of the patient/disorder "
    "**remains covered** by this rule, even when its head names a molecule or "
    "a process."
)

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

    assert CLAUSE in principle, "split point not found in saved principle"
    head = principle.split(CLAUSE)[0]
    scoped = head + SCOPED_TAIL
    assert prompt_original.count(principle) == 1, "principle not unique in prompt"
    prompt_scoped = prompt_original.replace(principle, scoped)
    (OUT / "principle_original.txt").write_text(principle + "\n", encoding="utf-8")
    (OUT / "principle_scoped.txt").write_text(scoped + "\n", encoding="utf-8")
    (OUT / "prompt_scoped.txt").write_text(prompt_scoped, encoding="utf-8")
    print(f"principle: {len(principle)} -> {len(scoped)} chars; first half byte-identical", flush=True)

    provider = OpenAIProvider.from_azure_env("5_4", reasoning_effort="high", max_output_tokens=64000)

    if CANDIDATE_PATH.exists():
        candidate = CANDIDATE_PATH.read_text(encoding="utf-8")
        print(f"reusing checkpointed candidate guideline: {len(candidate)} chars", flush=True)
    else:
        candidate = provider.complete("refine_guidelines", prompt_scoped)
        CANDIDATE_PATH.write_text(candidate, encoding="utf-8")
        print(f"candidate guideline: {len(candidate)} chars "
              f"(original R3 result: {len(snapshot['guidelines_after'])} chars)", flush=True)

    manifest = json.loads((RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))
    documents = [load_sampled_document(ROOT / d["path"]) for d in manifest]
    entity_rows = json.loads((ROOT / "data/schemas/ncbi_entities.schema.json").read_text(encoding="utf-8"))
    entities = [EntityDefinition(name=row) if isinstance(row, str) else EntityDefinition(**row)
                for row in entity_rows]
    output_configuration = OutputConfiguration(include_rationale=True, include_guideline_section=True)

    done = {}
    if ANNOTATIONS_PATH.exists():
        done = json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))
        print(f"resuming: {len(done)} documents already annotated", flush=True)
    for doc in documents:
        if doc.filename in done:
            continue
        result = it._annotate_documents([doc], candidate, entities, provider, "", output_configuration)
        done[doc.filename] = [{"start": a.start, "end": a.end, "label": a.entity, "text": a.text}
                              for a in result.get(doc.filename, [])]
        ANNOTATIONS_PATH.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"annotated {doc.filename} ({len(done)}/{len(documents)})", flush=True)

    trial = {name: [Annotation(start=a["start"], end=a["end"], entity=a["label"], text=a["text"])
                    for a in anns] for name, anns in done.items()}
    pairs = it._build_pairs(documents, trial)
    summary = it._summarize_moderation_pairs(pairs, 1.0)
    clusters = it._build_discrepancy_clusters(pairs)

    p1_annotations = json.loads(P1.read_text(encoding="utf-8"))
    stage_files = {
        "R2_after": {f["filename"]: f for f in snapshot["diagnostics_before"]["files"]},
        "R3_original": {f["filename"]: f for f in snapshot["diagnostics_after"]["files"]},
        "P1_truncated": p1_annotations,
        "P2_scoped": done,
    }
    def study_list(record):
        # snapshot file entries are dicts; saved annotation files are plain lists
        return record["study_denotations"] if isinstance(record, dict) else record

    states = {s: {name: keys(study_list(files[name])) for name in files}
              for s, files in stage_files.items()}

    per_doc = {}
    focus_history = []
    for doc in documents:
        name = doc.filename
        gold = keys(stage_files["R2_after"][name]["reference_denotations"])
        per_doc[name] = {s: {"tp": len(gold & p[name]), "fp": len(p[name] - gold),
                             "fn": len(gold - p[name])} for s, p in states.items()}
        for g in sorted(gold):
            text = doc.text[g[0]:g[1]]
            row = {"doc": name, "start": g[0], "end": g[1], "gold": g[2], "text": text}
            row.update({s: ("TP" if g in p[name] else "miss") for s, p in states.items()})
            if any(x in text for x in FOCUS):
                focus_history.append(row)

    def totals(state):
        tp = sum(d[state]["tp"] for d in per_doc.values())
        fp = sum(d[state]["fp"] for d in per_doc.values())
        fn = sum(d[state]["fn"] for d in per_doc.values())
        return {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn)}

    gold_all = set()
    for doc in documents:
        name = doc.filename
        gold_all |= {(name, *k) for k in keys(stage_files["R2_after"][name]["reference_denotations"])}
    pred = {}
    for s in ("R3_original", "P1_truncated", "P2_scoped"):
        pred[s] = set()
        for doc in documents:
            pred[s] |= {(doc.filename, *k) for k in states[s][doc.filename]}

    def rows(changed):
        return [{"doc": d, "start": s, "end": e, "label": l,
                 "text": next(x.text for x in documents if x.filename == d)[s:e]}
                for d, s, e, l in sorted(changed)]

    cand_lower = candidate.lower()
    exclusions = [line for line in candidate.splitlines()
                  if "do not annotate" in line.lower() or "not disease mention" in line.lower()
                  or "do **not** apply" in line.lower()]
    result = {
        "principle_original": principle,
        "principle_scoped": scoped,
        "candidate_chars": len(candidate),
        "guideline_mentions_faldh": "fatty aldehyde dehydrogenase" in cand_lower,
        "guideline_mentions_norrin": "norrin" in cand_lower,
        "candidate_exclusion_lines": exclusions,
        "f1": {s: totals(s) for s in ("R2_after", "R3_original", "P1_truncated", "P2_scoped")},
        "loop_summary_overall_f1": summary.overall_f1,
        "saved_R3_summary_f1": snapshot["summary_after"]["overall_f1"],
        "per_document": per_doc,
        "focus_cases": focus_history,
        "tp_gained_P2_vs_original": rows((gold_all & pred["P2_scoped"]) - pred["R3_original"]),
        "tp_lost_P2_vs_original": rows((gold_all & pred["R3_original"]) - pred["P2_scoped"]),
        "new_fp_P2_vs_original": rows(pred["P2_scoped"] - pred["R3_original"] - gold_all),
        "tp_gained_P2_vs_P1": rows((gold_all & pred["P2_scoped"]) - pred["P1_truncated"]),
        "tp_lost_P2_vs_P1": rows((gold_all & pred["P1_truncated"]) - pred["P2_scoped"]),
        "clusters_P2": [{"key": c.key, "count": c.count} for c in clusters],
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_document"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
