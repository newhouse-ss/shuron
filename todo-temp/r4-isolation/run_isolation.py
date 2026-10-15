"""RP step 2: isolation replay of the Round 4 target cases.

Plan: docs/RP/20261014_r4_failure_attribution_plan.md (step 2).
Run:  outputs/ncbi_disease/20260802_gpt54-high_moderation (Azure 5_4, reasoning high).

Only the guideline text changes between conditions; model, prompt template,
output configuration, instructions and documents are the original run's.
The annotator never sees gold; gold is used only by the ``score`` command.

    c1_R3             R3-after guideline (iteration_04 guidelines_before)
    c2_principle      label definitions + full R4 principle
    c2b_no_exception  label definitions + R4 principle without its DO NOT clause
    c3_R4             R4-after guideline (iteration_04 guidelines_after)

Each (condition, document, repetition) is one unit written to units/<id>.json as
soon as it finishes; rerunning skips finished units, so the job is resumable.
Three consecutive failed units abort the run.

    python todo-temp/r4-isolation/run_isolation.py run --dry-run   # render prompts, no network
    python todo-temp/r4-isolation/run_isolation.py run             # 36 model calls
    python todo-temp/r4-isolation/run_isolation.py score

Start the real run detached so it survives the CLI exiting, e.g. from PowerShell:
    Start-Process python -ArgumentList 'todo-temp/r4-isolation/run_isolation.py','run' `
        -RedirectStandardOutput todo-temp/r4-isolation/run.log `
        -RedirectStandardError todo-temp/r4-isolation/run.err -WindowStyle Hidden
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
OUT = Path(__file__).resolve().parent
DOCS = ["10577908.json", "1303173.json", "1671881.json"]
CONDITIONS = ["c1_R3", "c2_principle", "c2b_no_exception", "c3_R4"]
REPS = 3
CLAUSE = "; **DO NOT** apply this rule when"
# Label-definition sentences of the original guideline (1-based lines 6-8, 20, 28).
DEFINITION_LINES = [6, 7, 8, 20, 28]
TARGETS = {
    ("10577908.json", 245, 295): "FALDH",
    ("1303173.json", 1559, 1577): "G6PD",
    ("1671881.json", 138, 185): "PAH",
}
MAX_CONSECUTIVE_ERRORS = 3


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SNAPSHOT = RUN / "rounds/iteration_04/snapshot.json"


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def build_conditions(snapshot: dict) -> dict[str, str]:
    lines = (RUN / "inputs/initial_guidelines.txt").read_text(encoding="utf-8").splitlines()
    definitions = "\n".join(lines[n - 1] for n in DEFINITION_LINES)
    for label in ("Disease Class", "Specific Disease", "Composite Mention", "Modifier"):
        assert f"**{label}**" in definitions, f"definition of {label} missing"

    principle = snapshot["moderation_principle"]
    assert principle.count(CLAUSE) == 1, "exception-rule cut point not unique in R4 principle"
    principle_cut = principle.split(CLAUSE)[0] + "."

    r4_file = (RUN / "rounds/iteration_04/guidelines_after.txt").read_text(encoding="utf-8")
    assert r4_file.strip() == snapshot["guidelines_after"].strip(), "R4 guideline file != snapshot"
    r3_file = (RUN / "rounds/iteration_03/guidelines_after.txt").read_text(encoding="utf-8")
    assert r3_file.strip() == snapshot["guidelines_before"].strip(), "R3 guideline file != snapshot"

    return {
        "c1_R3": snapshot["guidelines_before"],
        "c2_principle": definitions + "\n\n" + principle,
        "c2b_no_exception": definitions + "\n\n" + principle_cut,
        "c3_R4": snapshot["guidelines_after"],
    }


def load_documents() -> dict:
    manifest = json.loads((RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))
    by_name = {d["filename"]: d for d in manifest}
    return {name: load_sampled_document(ROOT / by_name[name]["path"]) for name in DOCS}


def load_entities() -> list[EntityDefinition]:
    names = json.loads((RUN / "inputs/entity_schema.json").read_text(encoding="utf-8"))
    return [EntityDefinition(name=n) for n in names]


def units() -> list[tuple[str, str, int]]:
    # rep-major order keeps a partial run balanced across conditions
    return [(c, d, r) for r in range(1, REPS + 1) for d in DOCS for c in CONDITIONS]


def unit_id(cond: str, doc: str, rep: int) -> str:
    return f"{cond}__{doc.replace('.json', '')}__r{rep}"


class CaptureProvider:
    """Offline stand-in: records the prompt and returns an empty annotation list."""

    def __init__(self) -> None:
        self.prompt = ""
        self.last_usage: dict = {}

    def complete(self, task: str, prompt: str) -> str:
        self.prompt = prompt
        return '{"annotations": []}'


def cmd_run(args: argparse.Namespace) -> None:
    snapshot = load_snapshot()
    conditions = build_conditions(snapshot)
    documents = load_documents()
    entities = load_entities()
    output_configuration = OutputConfiguration(include_rationale=True, include_guideline_section=True)

    cond_dir = OUT / "conditions"
    cond_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"run": str(RUN.relative_to(ROOT)),
                "snapshot_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
                "conditions": {}, "docs": DOCS, "reps": REPS}
    for name, text in conditions.items():
        (cond_dir / f"{name}.txt").write_text(text, encoding="utf-8")
        manifest["conditions"][name] = {"chars": len(text), "sha256": sha256(text)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run:
        dry = OUT / "dry_run"
        dry.mkdir(exist_ok=True)
        total = 0
        for cond in CONDITIONS:
            for doc in DOCS:
                cap = CaptureProvider()
                annotate_with_guidelines(documents[doc].text, conditions[cond], entities, cap,
                                         instructions="", output_configuration=output_configuration)
                (dry / f"{cond}__{doc.replace('.json', '')}.txt").write_text(cap.prompt, encoding="utf-8")
                total += REPS * len(cap.prompt)
                print(f"{cond:18s} {doc:15s} prompt chars {len(cap.prompt):6d}")
        print(f"{len(units())} calls, total prompt chars {total}")
        return

    from llm_guideline_moderation.dotenv import load_dotenv
    from llm_guideline_moderation.providers.openai import OpenAIProvider

    load_dotenv()
    provider = OpenAIProvider.from_azure_env("5_4", reasoning_effort="high", max_output_tokens=64000)
    unit_dir = OUT / "units"
    unit_dir.mkdir(exist_ok=True)
    consecutive_errors = 0
    for cond, doc, rep in units():
        uid = unit_id(cond, doc, rep)
        path = unit_dir / f"{uid}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ok":
            continue
        record = {"unit": uid, "condition": cond, "doc": doc, "rep": rep,
                  "condition_sha256": manifest["conditions"][cond]["sha256"],
                  "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            result = annotate_with_guidelines(documents[doc].text, conditions[cond], entities, provider,
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
    unit_dir = Path(args.units_dir) if args.units_dir else OUT / "units"
    by_doc = {f["filename"]: f for f in snapshot["diagnostics_before"]["files"]}
    after = {f["filename"]: f for f in snapshot["diagnostics_after"]["files"]}

    rows = []
    for path in sorted(unit_dir.glob("*.json")):
        u = json.loads(path.read_text(encoding="utf-8"))
        if u.get("status") != "ok":
            continue
        doc = u["doc"]
        preds = [{"start": a["start"], "end": a["end"], "label": a["entity"]} for a in u["annotations"]]
        gold = keyset(by_doc[doc]["reference_denotations"])
        pred = keyset(preds)
        r3_tp = gold & keyset(by_doc[doc]["study_denotations"])
        [(name, start, end)] = [(n, s, e) for (d, s, e), n in TARGETS.items() if d == doc]
        gold_label = next(g[2] for g in gold if g[0] == start and g[1] == end)
        target_key = (start, end, gold_label)
        rows.append({
            "unit": u["unit"], "condition": u["condition"], "doc": doc, "rep": u["rep"],
            "target": name, "gold_label": gold_label,
            "target_status": span_status(preds, start, end),
            "target_correct": target_key in pred,
            "tp": len(gold & pred), "fp": len(pred - gold), "fn": len(gold - pred),
            "lost_vs_R3_after": sorted(r3_tp - pred - {target_key}),
            "gained_vs_R3_after": sorted((gold & pred) - r3_tp - {target_key}),
            "usage": u.get("usage", {}),
        })

    baseline = {}
    for (doc, s, e), name in TARGETS.items():
        baseline[name] = {
            "R3_after_saved": span_status(by_doc[doc]["study_denotations"], s, e),
            "R4_after_saved": span_status(after[doc]["study_denotations"], s, e),
        }
    table = {}
    for r in rows:
        cell = table.setdefault(r["target"], {}).setdefault(r["condition"], {"statuses": [], "correct": 0, "n": 0})
        cell["statuses"].append(r["target_status"])
        cell["correct"] += int(r["target_correct"])
        cell["n"] += 1
    result = {"baseline_saved": baseline, "table": table, "units": rows}
    out = Path(args.out) if args.out else OUT / "scores.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("FALDH", "G6PD", "PAH"):
        print(f"{name}: saved R3-after={baseline[name]['R3_after_saved']} R4-after={baseline[name]['R4_after_saved']}")
        for cond in CONDITIONS:
            c = table.get(name, {}).get(cond)
            if c:
                print(f"   {cond:18s} correct {c['correct']}/{c['n']}  {c['statuses']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--dry-run", action="store_true")
    p_score = sub.add_parser("score")
    p_score.add_argument("--units-dir")
    p_score.add_argument("--out")
    args = ap.parse_args()
    {"run": cmd_run, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
