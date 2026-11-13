"""Offline dry run, or explicitly authorized detached Message Batches execution."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
from common import (  # noqa: E402
    ARMS, ROOT, RUNS, TASK, TRAIN, hb, load_inputs, manifest, output_schema,
    parse_annotations, prompt, read_json, sha, type_candidates, write_json,
)
from llm_guideline_moderation.pubannotation import annotations_to_pubannotation  # noqa: E402


def arm_dir(root: Path, arm: str, run: int) -> Path:
    return root / {"S": "S", "S+": "Splus", "T": "T"}[arm] / f"run{run:02d}"


def freeze_inputs(root: Path) -> tuple:
    guideline, entities = load_inputs()
    frozen = {**manifest(), "guideline_sha256": sha(guideline),
              "entity_schema_sha256": sha(hb.ENTITY_SCHEMA.read_text(encoding="utf-8")),
              "schemas": {s: output_schema(s, entities) for s in ("S", "S+", "find", "type")},
              "prompt_sha256": {s: sha(prompt(s, "", guideline, entities, []))
                                for s in ("S", "S+", "find", "type")},
              "model": hb.rh.MODEL, "effort": "xhigh", "max_tokens": hb.MAX_OUTPUT_TOKENS,
              "max_attempts": hb.MAX_ATTEMPTS, "spending_cap": None}
    path = root / "manifest.json"
    if path.exists():
        if read_json(path) != frozen:
            raise ValueError("saved manifest differs from current inputs; use a new output directory")
    else:
        write_json(path, frozen)
    return frozen, guideline, entities


def queue_factory(queue, entities):
    def factory(arm, run, step, name):
        # Document identity also isolates repeated identical text within one arm/run/step.
        identity = f"{arm}-r{run:02d}-{step}-{Path(name).stem}"
        provider = hb.QueueProvider(queue, identity, "pilot")
        provider.template.json_schemas = {TASK: output_schema(step, entities)}
        return provider
    return factory


def call(workdir, name, step, arm, run, text, factory, entities):
    """Save parsed replies and usage alongside the queue's original API messages."""
    path = workdir / "raw_replies" / Path(name).stem / f"{step}.json"
    digest = sha(text)
    if path.exists():
        previous = read_json(path)
        if previous["prompt_sha256"] != digest:
            raise ValueError(f"saved prompt differs: {path}")
        if previous["status"] == "ok":
            return previous["reply"]
    provider = factory(arm, run, step, name)
    record = {"arm": arm, "run": run, "step": step, "document": name,
              "provider_name": provider.loop_id, "prompt_sha256": digest}
    try:
        response = provider.complete(TASK, text)
        raw = json.loads(response)
        # Structured outputs constrain these shapes in production. Check saved/fake replies as well.
        key = "decisions" if step == "type" else "annotations"
        if not isinstance(raw, dict) or not isinstance(raw.get(key), list):
            raise ValueError(f"reply must contain a {key} array")
        schema = output_schema(step, entities)["properties"][key]["items"]
        for row in raw[key]:
            if not isinstance(row, dict) or set(row) != set(schema["required"]):
                raise ValueError("reply fields differ from structured-output schema")
            for field, specification in schema["properties"].items():
                expected = int if specification["type"] == "integer" else str
                if type(row[field]) is not expected or ("enum" in specification and row[field] not in specification["enum"]):
                    raise ValueError(f"invalid reply field {field}")
        record.update(status="ok", response=response, reply=raw)
    except Exception as exc:
        record.update(status="unusable", error=f"{type(exc).__name__}: {exc}")
    finally:
        attempts = []
        if hasattr(provider, "queue"):
            params = provider.template.build_params(TASK, text)
            keyed = {**params, "max_tokens": hb.KEY_MAX_TOKENS}
            base = f"{provider.loop_id}|{TASK}|{sha(json.dumps(keyed, sort_keys=True, ensure_ascii=False))}"
            for attempt in range(provider.queue.max_attempts):
                cid = sha(f"{base}|0|{attempt}")[:48]
                reply_path = provider.queue.replies / f"{cid}.json"
                if reply_path.exists():
                    saved = read_json(reply_path)
                    usage = saved["message"].get("usage") or {}
                    attempts.append({"custom_id": saved["custom_id"], "attempt": saved["meta"]["attempt"],
                                     "usage": usage, "cost_jpy": hb.rh.cost_jpy(usage, True),
                                     "raw_message": str(reply_path.relative_to(workdir.parents[1]))})
        record["attempts"] = attempts
        record["cost_jpy"] = sum(a["cost_jpy"] for a in attempts)
        write_json(path, record)
    if record["status"] != "ok":
        raise RuntimeError(record["error"])
    return raw


def save_predictions(workdir, name, document, track1, track2):
    for track, annotations in (("track1_predictions", track1), ("track2_predictions", track2)):
        converted = annotations_to_pubannotation(
            text=document["text"], annotations=annotations, sourcedb=document.get("sourcedb", "unknown"),
            sourceid=document.get("sourceid", Path(name).stem), project=document.get("project"), target=document.get("target"))
        write_json(workdir / track / name, converted)


def run_document(root, arm, run, name, document, guideline, entities, factory):
    workdir = arm_dir(root, arm, run)
    status_path = workdir / "documents" / name
    status = {"arm": arm, "run": run, "document": name, "undecided": 0}
    try:
        step = "find" if arm == "T" else arm
        raw = call(workdir, name, step, arm, run, prompt(step, document["text"], guideline, entities), factory, entities)
        track1, track2 = parse_annotations(step, raw, document["text"], entities)
        if arm == "T":
            if track2:
                # First-step candidates are usable even when the typing call fails.
                try:
                    typed = call(workdir, name, "type", arm, run,
                                 prompt("type", document["text"], guideline, entities, track2), factory, entities)
                except RuntimeError as exc:
                    typed = {"decisions": []}
                    status["typing_error"] = str(exc)
                track1, track2, status["undecided"] = type_candidates(track2, typed, entities)
            else:
                track1 = []
                status["typing_skipped"] = "no candidates"
        save_predictions(workdir, name, document, track1, track2)
        status.update(status="completed", track1_count=len(track1), track2_count=len(track2))
    except Exception as exc:
        status.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    write_json(status_path, status)
    return status


def usage_report(workdir: Path) -> dict:
    calls = [read_json(p) for p in sorted((workdir / "raw_replies").glob("*/*.json"))]
    unusable = [{k: c[k] for k in ("document", "step", "provider_name", "error")}
                for c in calls if c["status"] != "ok"]
    return {"logical_calls": len(calls), "unusable_calls": unusable,
            "cost_jpy": sum(c["cost_jpy"] for c in calls),
            "calls": [{k: c[k] for k in ("document", "step", "provider_name", "status", "cost_jpy", "attempts")}
                      for c in calls]}


def run_all(root: Path, client, *, quiet=hb.QUIET, poll=hb.POLL):
    frozen, guideline, entities = freeze_inputs(root)
    names = frozen["pilot_documents"]
    # Open only pilot documents, never reserved or excluded documents.
    documents = {name: read_json(TRAIN / name) for name in names}
    queue = hb.BatchQueue(root / "_batchqueue", client, cap_jpy=float("inf"), quiet=quiet,
                          poll=poll, max_attempts=hb.MAX_ATTEMPTS)
    factory = queue_factory(queue, entities)
    for arm in ARMS:
        for run in RUNS:
            write_json(arm_dir(root, arm, run) / "documents.json", names)
    queue.start()
    units = [(arm, run, name) for run in RUNS for name in names for arm in ARMS]
    with cf.ThreadPoolExecutor(max_workers=128) as pool:
        futures = [pool.submit(run_document, root, arm, run, name, documents[name], guideline, entities, factory)
                   for arm, run, name in units]
        statuses = [future.result() for future in futures]
    usages = []
    for arm in ARMS:
        for run in RUNS:
            directory = arm_dir(root, arm, run)
            usage = usage_report(directory)
            write_json(directory / "usage.json", usage)
            usages.append(usage)
            own = [s for s in statuses if s["arm"] == arm and s["run"] == run]
            write_json(directory / "status.json", {"documents": len(own), "failed": [s for s in own if s["status"] != "completed"],
                                                  "undecided": sum(s["undecided"] for s in own)})
    unusable = [c for usage in usages for c in usage["unusable_calls"]]
    count = sum(u["logical_calls"] for u in usages)
    summary = {"status": "completed" if not unusable else "unusable_calls", "logical_calls": count,
               "unusable_calls": unusable, "unusable_fraction": len(unusable) / count if count else 1,
               "cost_jpy": queue.spent_jpy(), "batches_sent_this_session": queue.sent}
    write_json(root / "status.json", summary)
    return summary


def dry_run() -> str:
    selected = manifest()
    load_inputs()  # Assert the original guideline hash without reading any document or credentials.
    calls = len(selected["pilot_documents"]) * len(RUNS) * 4
    assert calls <= 1600
    return (f"DRY RUN: pool={selected['pool_size']}; reserved=100; pilot=200; runs=2; "
            f"calls <= {calls} before retries (S=400, S+=400, T<=800); "
            f"JPY {calls * 0.634:.2f} at JPY 0.634/call; no spending cap; no calls executed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("dry-run")
    run = commands.add_parser("run")
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d")
    run.add_argument("--output-root", type=Path, default=ROOT / f"outputs/ncbi_disease/{today}_haiku-xhigh_pilot_twostep")
    run.add_argument("--yes", action="store_true")
    run.add_argument("--administrator-notified", action="store_true")
    run.add_argument("--detach", action="store_true")
    args = parser.parse_args()
    if args.command == "dry-run":
        print(dry_run())
        return
    if not args.yes or not args.administrator_notified:
        parser.error("paid run requires --yes and --administrator-notified after approval and notification")
    # Require an environment key. Never open .env or any credential file, even in the paid entry point.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        parser.error("ANTHROPIC_API_KEY must already be set in the environment")
    root = args.output_root.resolve()
    freeze_inputs(root)  # Persist both document lists and hashes before any client is created.
    if args.detach:
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "run", "--yes", "--administrator-notified",
                   "--output-root", str(root)]
        options = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        with (root / "runner.log").open("ab") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, **options)
        write_json(root / "process.json", {"pid": process.pid, "command": command})
        print(f"Detached pilot PID {process.pid}; log: {root / 'runner.log'}")
        return
    import anthropic
    summary = run_all(root, anthropic.Anthropic(max_retries=4))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
