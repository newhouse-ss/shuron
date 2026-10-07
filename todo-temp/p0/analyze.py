from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from llm_guideline_moderation.iterative import _build_discrepancy_clusters
from llm_guideline_moderation.types import Annotation
from llm_guideline_moderation.evaluation import DocumentPair


def read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def key(a):
    return (a["start"], a["end"], a["label"])


def keys(annotations):
    result = {key(a) for a in annotations}
    assert len(result) == len(annotations), "Duplicate annotations need explicit scorer reconciliation"
    return result


def ann(a):
    return Annotation(start=a["start"], end=a["end"], entity=a["label"], text=a["text"])


manifest = read(RUN / "inputs/sampled_train_documents.json")
docs = {d["filename"]: read(ROOT / d["path"]) for d in manifest}
snapshots = {i: read(RUN / f"rounds/iteration_{i:02d}/snapshot.json") for i in range(1, 5)}
states = {0: snapshots[1]["diagnostics_before"]}
states.update({i: snapshots[i]["diagnostics_after"] for i in range(1, 5)})
summaries = {0: snapshots[1]["summary_before"]}
summaries.update({i: snapshots[i]["summary_after"] for i in range(1, 5)})

for i, s in snapshots.items():
    assert s["improved"] and not s["reverted"]
    assert s["diagnostics_before"] == states[i - 1], f"State continuity mismatch before iteration {i}"
    if i > 1:
        assert s["guidelines_before"] == snapshots[i - 1]["guidelines_after"]
assert read(RUN / "final/iterative_refinement_run.json")["final_diagnostics"] == states[4]

stage_files = {i: {f["filename"]: f for f in diag["files"]} for i, diag in states.items()}
stage_metrics = {}
matrices = {}
per_doc = {}
axis = ["SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention", "O"]
for i, files in stage_files.items():
    assert set(files) == set(docs), "Document alignment mismatch"
    total_tp = total_fp = total_fn = 0
    pairs = []
    per_doc[i] = {}
    for name, f in files.items():
        raw = docs[name]
        g = f["reference_denotations"]
        p = f["study_denotations"]
        raw_gold = {(d["span"]["begin"], d["span"]["end"], d["obj"]) for d in raw["denotations"]}
        assert keys(g) == raw_gold, f"Gold changed: {name}"
        assert all(raw["text"][a["start"]:a["end"]] == a["text"] for a in g + p), f"Text/offset mismatch: {name}"
        gs, ps = keys(g), keys(p)
        tp, fp, fn = len(gs & ps), len(ps - gs), len(gs - ps)
        total_tp += tp
        total_fp += fp
        total_fn += fn
        per_doc[i][name] = {"tp": tp, "fp": fp, "fn": fn}
        pairs.append(DocumentPair(filename=name, text=raw["text"], gold_annotations=[ann(a) for a in g], llm_annotations=[ann(a) for a in p]))
    score = 2 * total_tp / (2 * total_tp + total_fp + total_fn)
    saved = summaries[i]
    assert [total_tp, total_fp, total_fn] == [saved["true_positives"], saved["false_positives"], saved["false_negatives"]]
    assert abs(score - saved["overall_f1"]) < 1e-12
    overall = states[i]["overall"]["overall"]
    assert [total_tp, total_fp, total_fn] == [overall["matched_study"], overall["false_positives"], overall["false_negatives"]]
    stage_metrics[i] = {"tp": total_tp, "fp": total_fp, "fn": total_fn, "pred": total_tp + total_fp, "gold": total_tp + total_fn, "f1": score}
    computed = _build_discrepancy_clusters(pairs)
    expected = Counter({c["key"]: c["count"] for c in saved["all_clusters"]})
    observed = Counter({c.key: c.count for c in computed})
    assert expected == observed, f"Saved vs current clustering mismatch at {i}: {expected} {observed}"
    matrix = {a: {b: 0 for b in axis} for a in axis}
    for c in saved["all_clusters"]:
        assert c["count"] == len(c["examples"]), "Incomplete stored examples"
        matrix[c["gold_label"]][c["llm_label"]] += c["count"]
    matrices[i] = matrix


def describe(name, g, stage):
    preds = stage_files[stage][name]["study_denotations"]
    exact = [p for p in preds if p["start"] == g["start"] and p["end"] == g["end"]]
    if exact:
        return "; ".join(p["label"] for p in exact)
    overlap = [p for p in preds if min(p["end"], g["end"]) > max(p["start"], g["start"])]
    if overlap:
        return "; ".join(f'{p["label"]}: {p["text"]} [{p["start"]},{p["end"]})' for p in overlap)
    return "O"


transitions = []
gold_changes = []
history = []
for name, raw in docs.items():
    g = stage_files[3][name]["reference_denotations"]
    for a in g:
        values = [describe(name, a, i) for i in range(5)]
        row = {"doc": name, **a, "labels_0_to_4": values, "context": raw["text"][max(0, a["start"]-80):a["end"]+80]}
        history.append(row)
        if values[3] != values[4]:
            gold_changes.append(row)
    before = keys(stage_files[3][name]["study_denotations"])
    after = keys(stage_files[4][name]["study_denotations"])
    for kind, changed in [("removed", before - after), ("added", after - before)]:
        for start, end, label in sorted(changed):
            transitions.append({"doc": name, "change": kind, "start": start, "end": end, "label": label, "text": raw["text"][start:end]})

gains = []
losses = []
for name in docs:
    gold = keys(stage_files[3][name]["reference_denotations"])
    before = keys(stage_files[3][name]["study_denotations"])
    after = keys(stage_files[4][name]["study_denotations"])
    for dest, changed in [(gains, (gold & after) - before), (losses, (gold & before) - after)]:
        dest.extend({"doc": name, "start": k[0], "end": k[1], "label": k[2], "text": docs[name]["text"][k[0]:k[1]]} for k in sorted(changed))

sources = [RUN / f"rounds/iteration_{i:02d}/snapshot.json" for i in range(1, 5)]
sources += [RUN / "inputs/sampled_train_documents.json", RUN / "inputs/resolved_run_config.json"]
sources += [ROOT / d["path"] for d in manifest]
result = {"stage_metrics": stage_metrics, "matrices_gold_rows": matrices, "per_document": per_doc, "gold_case_changes_r4": gold_changes, "prediction_changes_r4": transitions, "tp_gains": gains, "tp_losses": losses, "gold_case_history": history, "checks": "10 documents aligned; gold and text offsets identical; no duplicates; stage continuity exact; saved loop and PubAnnotation counts identical; saved discrepancy clusters reproduced", "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k not in ["gold_case_history", "source_sha256", "matrices_gold_rows", "per_document"]}, ensure_ascii=False, indent=2))
print("FOCUS CASE HISTORY")
focus = ["norrin", "fatty aldehyde", "spasticity", "abnormal retinal", "deficiency in G6PD", "deficiency of hepatic"]
print(json.dumps([r for r in history if any(x in r["text"] for x in focus)], ensure_ascii=False, indent=2))
print("MATRICES", json.dumps({i: matrices[i] for i in [2, 3, 4]}, ensure_ascii=False))
