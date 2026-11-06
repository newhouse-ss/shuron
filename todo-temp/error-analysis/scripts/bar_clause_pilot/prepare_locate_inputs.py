"""Blinded inputs for the Codex locating task (2026-11-06). Offline, no API calls.

For each of the 11 changed guidelines, writes one JSON line per distinct prediction that the bar analysis needs located
(a prediction linked to an instance with a non-zero difference in <prefix>_instances.csv). Each line carries only what a
reader needs to locate the guideline text behind the prediction: document, predicted span, text and label, about 250
characters of document context each side, the model's guideline_section citation and its rationale. Gold labels,
outcome categories and difference values are left out on purpose, so locating cannot be steered by results.

Also writes, for the positions where a changed guideline has no prediction (gold left unlabelled, or a no-gold prediction
the original runs made and the changed guideline dropped), the original-run predictions at that exact position: up to 3
per position, one per distinct citation string (most frequent first), each with its rationale.

Guidelines are copied with line endings normalised to LF, as plain text and as a numbered view, so that line numbers and
verbatim quotes are unambiguous.

Inputs: outputs/bar_clause_pilot/<prefix>_instances.csv and <prefix>_noprediction_lookup.csv (build_instances.py),
outputs/20261030_rationale_audit/{documents/, prediction_index.jsonl, run_manifest.json}, the final guidelines under
outputs/ncbi_disease/, data/guidelines/ncbi_disease_guidelines.txt.
Outputs: outputs/bar_clause_pilot/codex_locate/inputs/ (see the spec note 20261106_codex_locate_spec.md).
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EA = ROOT / "todo-temp" / "error-analysis" / "outputs"
PILOT = EA / "bar_clause_pilot"
AUDIT = EA / "20261030_rationale_audit"
OUT = PILOT / "codex_locate" / "inputs"
CTX = 250

PREFIXES = {
    "top1_loop05": "topk1_loop05", "top1_loop07": "topk1_loop07",
    "top4_loop01": "topk4_loop01", "top4_loop02": "topk4_loop02", "top4_loop04": "topk4_loop04",
    "top4_loop05": "topk4_loop05", "top4_loop06": "topk4_loop06", "top4_loop07": "topk4_loop07",
    "top4_loop08": "topk4_loop08", "top4_loop09": "topk4_loop09", "top4_loop10": "topk4_loop10",
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lf(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


docs = {}


def doc_text(doc):
    if doc not in docs:
        docs[doc] = lf((AUDIT / "documents" / f"{doc}.txt").read_text(encoding="utf-8"))
    return docs[doc]


def context(doc, s, e):
    t = doc_text(doc)
    return t[max(0, s - CTX):s] + "[[" + t[s:e] + "]]" + t[e:e + CTX]


def write_guideline(name, src):
    text = lf(Path(src).read_text(encoding="utf-8"))
    (OUT / "guidelines").mkdir(parents=True, exist_ok=True)
    plain = OUT / "guidelines" / f"{name}.txt"
    plain.write_text(text, encoding="utf-8", newline="\n")
    numbered = "".join(f"{i:04d}\t{line}\n" for i, line in enumerate(text.split("\n"), 1))
    (OUT / "guidelines" / f"{name}_numbered.txt").write_text(numbered, encoding="utf-8", newline="\n")
    return plain


OUT.mkdir(parents=True, exist_ok=True)
manifest = {"inputs": {}, "outputs": {}, "counts": {}}
offset_mismatch = []

# ---- Part A: predictions of the 11 changed guidelines
for prefix, folder in PREFIXES.items():
    gpath = ROOT / "outputs" / "ncbi_disease" / f"20261022_haiku-xhigh_{folder}" / "final" / "final_guidelines.txt"
    write_guideline(prefix, gpath)
    ipath = PILOT / f"{prefix}_instances.csv"
    manifest["inputs"][str(ipath.relative_to(ROOT))] = sha(ipath)
    manifest["inputs"][str(gpath.relative_to(ROOT))] = sha(gpath)
    rows = list(csv.DictReader(open(ipath, encoding="utf-8")))
    seen, lines = set(), []
    n_with_pred = 0
    for r in rows:
        if not r["target_pred_label"]:
            continue
        n_with_pred += 1
        doc, s, e, lab = r["doc"], int(r["target_pred_start"]), int(r["target_pred_end"]), r["target_pred_label"]
        key = (doc, s, e, lab)
        if key in seen:
            continue
        seen.add(key)
        if doc_text(doc)[s:e] != r["target_pred_text"]:
            offset_mismatch.append((prefix, key, r["target_pred_text"]))
        lines.append({
            "pred_id": f"{prefix}|{doc}|{s}|{e}|{lab}", "guideline": prefix, "doc": doc,
            "pred_start": s, "pred_end": e, "pred_text": r["target_pred_text"], "pred_label": lab,
            "context": context(doc, s, e), "guideline_section": r["cited_section_raw"],
            "rationale": r["raw_rationale"],
        })
    lines.sort(key=lambda x: (x["doc"], x["pred_start"], x["pred_end"], x["pred_label"]))
    opath = OUT / f"{prefix}_predictions.jsonl"
    with open(opath, "w", encoding="utf-8", newline="\n") as f:
        for x in lines:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    manifest["counts"][prefix] = {"instances_with_prediction": n_with_pred, "distinct_predictions": len(lines)}

# ---- Part B: original-run predictions at positions with no prediction in a changed guideline
write_guideline("original", ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt")
runs = json.loads((AUDIT / "run_manifest.json").read_text(encoding="utf-8"))
orig_runs = sorted(r["run"] for r in runs if r["guideline_group"] == "original")
assert len(orig_runs) == 19, len(orig_runs)
positions = {}
for prefix in PREFIXES:
    lpath = PILOT / f"{prefix}_noprediction_lookup.csv"
    manifest["inputs"][str(lpath.relative_to(ROOT))] = sha(lpath)
    for r in csv.DictReader(open(lpath, encoding="utf-8")):
        lab = r["gold_label"] or r["nogold_label"]
        positions[(r["doc"], int(r["start"]), int(r["end"]), lab)] = r["text"]
by_pos = {k: [] for k in positions}
with open(AUDIT / "prediction_index.jsonl", encoding="utf-8") as f:
    for line in f:
        p = json.loads(line)
        if p["run"] not in orig_runs:
            continue
        k = (p["doc"], int(p["start"]), int(p["end"]), p["pred_label"])
        if k in by_pos:
            by_pos[k].append(p)
b_lines, missing = [], []
for k in sorted(positions):
    preds = by_pos[k]
    if not preds:
        missing.append(k)
        continue
    groups = {}
    for p in sorted(preds, key=lambda p: p["run"]):
        groups.setdefault(p["cited_section"] or "", []).append(p)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:3]
    for cite, ps in ordered:
        p = ps[0]
        doc, s, e, lab = k
        b_lines.append({
            "lookup_id": f"original|{doc}|{s}|{e}|{lab}|{p['run']}", "guideline": "original", "doc": doc,
            "pred_start": s, "pred_end": e, "pred_text": p["pred_text"], "pred_label": lab,
            "context": context(doc, s, e), "guideline_section": cite, "rationale": p["raw_rationale"],
            "n_original_runs_with_this_citation": len(ps),
        })
bpath = OUT / "original_lookup_predictions.jsonl"
with open(bpath, "w", encoding="utf-8", newline="\n") as f:
    for x in b_lines:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
manifest["counts"]["original_lookup"] = {"positions": len(positions), "positions_without_original_prediction": len(missing),
                                         "lines": len(b_lines)}
manifest["offset_mismatch"] = [list(map(str, m)) for m in offset_mismatch]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name != "manifest.json":
        manifest["outputs"][str(p.relative_to(ROOT))] = sha(p)
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(manifest["counts"], indent=1))
print("total distinct predictions:", sum(v["distinct_predictions"] for k, v in manifest["counts"].items() if k != "original_lookup"))
print("offset mismatches:", len(offset_mismatch), "| positions without original prediction:", len(missing))
