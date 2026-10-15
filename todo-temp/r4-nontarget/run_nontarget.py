"""Attribution of the Round 4 non-target change in 8326491 (Tay-Sachs disease / TSD, M -> S).

Question: did the R4 guideline cause the M -> S change of the two mentions in
"a Tay-Sachs disease ( TSD ) causing mutation" (gold SpecificDisease), or was it run-to-run noise?
Run:  outputs/ncbi_disease/20260802_gpt54-high_moderation (Azure 5_4, reasoning high).

Same setup as todo-temp/r4-isolation/run_isolation.py: only the guideline text changes between
conditions; model, prompt template, output configuration and document are the original run's.
The annotator never sees gold; gold is used only by the ``score`` command.

    c1_R3          R3-after guideline (iteration_04 guidelines_before)              E1
    c3_R4          R4-after guideline (iteration_04 guidelines_after)               E1
    c3_nocause     c3_R4 with "causation" and "responsibility-for-condition"        E2, run only
                   removed from the deficiency bullet (the only place either word   if E1 shows
                   occurs in the R4 guideline)                                      the change

Each (condition, repetition) is one unit written to units/<id>.json as soon as it finishes;
rerunning skips finished units, so the job is resumable. Three consecutive failed units abort.

    python todo-temp/r4-nontarget/run_nontarget.py run --conditions c1_R3 c3_R4 --dry-run
    python todo-temp/r4-nontarget/run_nontarget.py run --conditions c1_R3 c3_R4     # E1, 10 calls
    python todo-temp/r4-nontarget/run_nontarget.py run --conditions c3_nocause      # E2, 5 calls
    python todo-temp/r4-nontarget/run_nontarget.py score
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
SNAPSHOT = RUN / "rounds/iteration_04/snapshot.json"
OUT = Path(__file__).resolve().parent
DOC = "8326491.json"
CONDITIONS = ["c1_R3", "c3_R4", "c3_nocause"]
REPS = 5
# E2 edit: the deficiency bullet (R4 line 12) is the only place "causation" or "responsibility" occurs.
CAUSE_OLD = "often signaled by disease-definition, causation, characterization, or responsibility-for-condition context"
CAUSE_NEW = "often signaled by disease-definition or characterization context"
# Gold spans of 8326491; the first two are the R4 non-target change.
SPANS = {
    (193, 210): "Tay-Sachs disease (causing mutation)",
    (213, 216): "TSD (causing mutation)",
    (106, 123): "Tay-Sachs disease patients",
    (567, 570): "TSD carriers",
    (839, 842): "TSD carriers (2)",
    (966, 969): "TSD families",
}
FOCUS = [(193, 210), (213, 216)]
MAX_CONSECUTIVE_ERRORS = 3


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def build_conditions(snapshot: dict) -> dict[str, str]:
    r4_file = (RUN / "rounds/iteration_04/guidelines_after.txt").read_text(encoding="utf-8")
    assert r4_file.strip() == snapshot["guidelines_after"].strip(), "R4 guideline file != snapshot"
    r3_file = (RUN / "rounds/iteration_03/guidelines_after.txt").read_text(encoding="utf-8")
    assert r3_file.strip() == snapshot["guidelines_before"].strip(), "R3 guideline file != snapshot"

    r4 = snapshot["guidelines_after"]
    assert r4.count(CAUSE_OLD) == 1, "E2 edit point not unique in R4 guideline"
    nocause = r4.replace(CAUSE_OLD, CAUSE_NEW)
    for word in ("causation", "responsib"):
        assert word not in nocause.lower(), f"{word} still present after E2 edit"

    return {"c1_R3": snapshot["guidelines_before"], "c3_R4": r4, "c3_nocause": nocause}


def load_document():
    manifest = json.loads((RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))
    by_name = {d["filename"]: d for d in manifest}
    return load_sampled_document(ROOT / by_name[DOC]["path"])


def load_entities() -> list[EntityDefinition]:
    names = json.loads((RUN / "inputs/entity_schema.json").read_text(encoding="utf-8"))
    return [EntityDefinition(name=n) for n in names]


def unit_id(cond: str, rep: int) -> str:
    return f"{cond}__{DOC.replace('.json', '')}__r{rep}"


class CaptureProvider:
    """Offline stand-in: records the prompt and returns an empty annotation list."""

    def __init__(self) -> None:
        self.prompt = ""
        self.last_usage: dict = {}

    def complete(self, task: str, prompt: str) -> str:
        self.prompt = prompt
        return '{"annotations": []}'


def cmd_run(args: argparse.Namespace) -> None:
    selected = args.conditions
    for cond in selected:
        assert cond in CONDITIONS, f"unknown condition {cond}"
    snapshot = load_snapshot()
    conditions = build_conditions(snapshot)
    document = load_document()
    entities = load_entities()
    output_configuration = OutputConfiguration(include_rationale=True, include_guideline_section=True)

    cond_dir = OUT / "conditions"
    cond_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"run": str(RUN.relative_to(ROOT)),
                "snapshot_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
                "conditions": {}, "doc": DOC, "reps": REPS,
                "e2_edit": {"old": CAUSE_OLD, "new": CAUSE_NEW}}
    for name, text in conditions.items():
        (cond_dir / f"{name}.txt").write_text(text, encoding="utf-8")
        manifest["conditions"][name] = {"chars": len(text), "sha256": sha256(text)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run:
        dry = OUT / "dry_run"
        dry.mkdir(exist_ok=True)
        for cond in selected:
            cap = CaptureProvider()
            annotate_with_guidelines(document.text, conditions[cond], entities, cap,
                                     instructions="", output_configuration=output_configuration)
            (dry / f"{cond}__{DOC.replace('.json', '')}.txt").write_text(cap.prompt, encoding="utf-8")
            print(f"{cond:12s} prompt chars {len(cap.prompt):6d}  guideline sha256 {manifest['conditions'][cond]['sha256']}")
        print(f"{len(selected) * REPS} calls planned")
        return

    from llm_guideline_moderation.dotenv import load_dotenv
    from llm_guideline_moderation.providers.openai import OpenAIProvider

    load_dotenv()
    provider = OpenAIProvider.from_azure_env("5_4", reasoning_effort="high", max_output_tokens=64000)
    unit_dir = OUT / "units"
    unit_dir.mkdir(exist_ok=True)
    consecutive_errors = 0
    # rep-major order keeps a partial run balanced across conditions
    for rep in range(1, REPS + 1):
        for cond in selected:
            uid = unit_id(cond, rep)
            path = unit_dir / f"{uid}.json"
            if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ok":
                continue
            record = {"unit": uid, "condition": cond, "doc": DOC, "rep": rep,
                      "condition_sha256": manifest["conditions"][cond]["sha256"],
                      "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
            print(f"{record['started']} {uid} start", flush=True)
            try:
                result = annotate_with_guidelines(document.text, conditions[cond], entities, provider,
                                                  instructions="", output_configuration=output_configuration)
                record.update(status="ok",
                              annotations=[asdict(a) for a in result.annotations],
                              raw_response=result.raw_response,
                              usage=provider.last_usage)
                consecutive_errors = 0
            except Exception as exc:  # recorded and retried on the next invocation
                record.update(status="error", error=f"{type(exc).__name__}: {exc}", usage=provider.last_usage)
                consecutive_errors += 1
            record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{record['finished']} {uid} {record['status']}", flush=True)
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print(f"aborting after {consecutive_errors} consecutive errors", flush=True)
                sys.exit(1)


def span_status(preds: list[dict], start: int, end: int) -> str:
    exact = [p["label"] for p in preds if p["start"] == start and p["end"] == end]
    if exact:
        return exact[0]
    overlap = [f'overlap:{p["label"]}[{p["start"]},{p["end"]})' for p in preds
               if p["start"] < end and p["end"] > start]
    return ";".join(overlap) if overlap else "O"


def keyset(denotations: list[dict]) -> set[tuple[int, int, str]]:
    return {(d["start"], d["end"], d["label"]) for d in denotations}


def cmd_score(args: argparse.Namespace) -> None:
    snapshot = load_snapshot()
    before = next(f for f in snapshot["diagnostics_before"]["files"] if f["filename"] == DOC)
    after = next(f for f in snapshot["diagnostics_after"]["files"] if f["filename"] == DOC)
    gold = keyset(before["reference_denotations"])
    gold_label = {(s, e): lab for s, e, lab in gold}
    assert set(gold_label) == set(SPANS), "gold spans of 8326491 differ from SPANS"

    rows = []
    for path in sorted((OUT / "units").glob("*.json")):
        u = json.loads(path.read_text(encoding="utf-8"))
        if u.get("status") != "ok":
            continue
        preds = [{"start": a["start"], "end": a["end"], "label": a["entity"]} for a in u["annotations"]]
        pred = keyset(preds)
        focus_detail = {}
        for s, e in FOCUS:
            hit = [a for a in u["annotations"] if a["start"] < e and a["end"] > s]
            focus_detail[f"{s}-{e}"] = [{k: a.get(k) for k in ("start", "end", "text", "entity", "rationale",
                                                               "guideline_section", "uncertain")} for a in hit]
        rows.append({
            "unit": u["unit"], "condition": u["condition"], "rep": u["rep"],
            "spans": {f"{s}-{e}": span_status(preds, s, e) for s, e in SPANS},
            "focus_correct": sum((s, e, gold_label[(s, e)]) in pred for s, e in FOCUS),
            "tp": len(gold & pred), "fp": len(pred - gold), "fn": len(gold - pred),
            "fp_items": sorted(pred - gold),
            "focus_detail": focus_detail,
            "usage": u.get("usage", {}),
        })

    baseline = {name: {f"{s}-{e}": span_status(f["study_denotations"], s, e) for s, e in SPANS}
                for name, f in (("R3_after_saved", before), ("R4_after_saved", after))}
    table = {}
    for r in rows:
        cell = table.setdefault(r["condition"], {"n": 0, "focus_correct": 0, "spans": {}, "tp_fp_fn": [],
                                                 "input_tokens": 0, "output_tokens": 0})
        cell["n"] += 1
        cell["focus_correct"] += r["focus_correct"]
        for k, v in r["spans"].items():
            cell["spans"].setdefault(k, []).append(v)
        cell["tp_fp_fn"].append((r["tp"], r["fp"], r["fn"]))
        cell["input_tokens"] += r["usage"].get("input_tokens", 0)
        cell["output_tokens"] += r["usage"].get("output_tokens", 0)

    result = {"gold": {f"{s}-{e}": gold_label[(s, e)] for s, e in SPANS}, "baseline_saved": baseline,
              "table": table, "units": rows}
    out = OUT / "scores.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("gold:", result["gold"])
    for name, spans in baseline.items():
        print(f"{name}: {spans}")
    for cond in CONDITIONS:
        c = table.get(cond)
        if not c:
            continue
        print(f"\n{cond}: n={c['n']}  focus spans correct {c['focus_correct']}/{2 * c['n']}  "
              f"tokens in {c['input_tokens']} out {c['output_tokens']}")
        for k, v in c["spans"].items():
            print(f"   {k:8s} {SPANS[tuple(map(int, k.split('-')))]:38s} {v}")
        print(f"   TP/FP/FN per rep: {c['tp_fp_fn']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--conditions", nargs="+", required=True)
    p_run.add_argument("--dry-run", action="store_true")
    sub.add_parser("score")
    args = ap.parse_args()
    {"run": cmd_run, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
