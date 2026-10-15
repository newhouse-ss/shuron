"""Follow-up condition c3_minus_faldh: R4 guideline minus the three passages that name FALDH.

Plan: section 5 of todo-temp/r4-isolation/20261014_r4_isolation_report.md.
Single variable relative to c3_R4: lines 54-58 (FALDH "Do not annotate" example and the blank
line after it), 167 and 263 of iteration_04/guidelines_after.txt are deleted; every other line
is kept byte for byte. Only FALDH's document (10577908) is annotated, 3 repetitions, with the
same model, template and output configuration as run_isolation.py. Units go to units_c3minus/
so the 36-unit results and their hashes stay untouched.

    python todo-temp/r4-isolation/run_c3_minus.py run --dry-run
    python todo-temp/r4-isolation/run_c3_minus.py run
    python todo-temp/r4-isolation/run_isolation.py score --units-dir todo-temp/r4-isolation/units_c3minus \
        --out todo-temp/r4-isolation/scores_c3minus.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_isolation as base  # noqa: E402

COND = "c3_minus_faldh"
DOC = "10577908.json"
REPS = 3
# 1-based line number -> fragment the line must contain (empty string: the line must be blank)
REMOVE = {
    54: "> Deficient activity of fatty aldehyde dehydrogenase",
    55: "",
    56: "- **Do not annotate**",
    57: "because in this context it refers to enzyme activity/biochemical abnormality",
    58: "",
    167: "such as “deficient activity of fatty aldehyde dehydrogenase”",
    263: "In “deficient activity of fatty aldehyde dehydrogenase,”",
}


def build_condition(snapshot: dict) -> str:
    lines = snapshot["guidelines_after"].split("\n")
    for n, fragment in REMOVE.items():
        line = lines[n - 1]
        assert (fragment in line) if fragment else not line.strip(), f"line {n} is not what was planned: {line!r}"
    kept = [line for i, line in enumerate(lines, 1) if i not in REMOVE]
    text = "\n".join(kept)
    assert "fatty aldehyde" not in text.lower() and "faldh" not in text.lower(), "a FALDH mention survived"
    assert len(kept) == len(lines) - len(REMOVE)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    snapshot = base.load_snapshot()
    text = build_condition(snapshot)
    (base.OUT / "conditions").mkdir(exist_ok=True)
    (base.OUT / "conditions" / f"{COND}.txt").write_text(text, encoding="utf-8")
    meta = {"condition": COND, "derived_from": "c3_R4", "removed_lines": sorted(REMOVE),
            "chars": len(text), "sha256": base.sha256(text),
            "c3_R4_sha256": base.sha256(snapshot["guidelines_after"]),
            "snapshot_sha256": base.hashlib.sha256(base.SNAPSHOT.read_bytes()).hexdigest()}
    (base.OUT / "manifest_c3minus.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    document = base.load_documents()[DOC]
    entities = base.load_entities()
    output_configuration = base.OutputConfiguration(include_rationale=True, include_guideline_section=True)

    if args.dry_run:
        cap = base.CaptureProvider()
        base.annotate_with_guidelines(document.text, text, entities, cap,
                                      instructions="", output_configuration=output_configuration)
        (base.OUT / "dry_run" / f"{COND}__10577908.txt").write_text(cap.prompt, encoding="utf-8")
        print(f"{COND}: guideline chars {len(text)} (c3_R4 {len(snapshot['guidelines_after'])}), "
              f"prompt chars {len(cap.prompt)}, {REPS} calls")
        return

    from llm_guideline_moderation.dotenv import load_dotenv
    from llm_guideline_moderation.providers.openai import OpenAIProvider

    load_dotenv()
    provider = OpenAIProvider.from_azure_env("5_4", reasoning_effort="high", max_output_tokens=64000)
    unit_dir = base.OUT / "units_c3minus"
    unit_dir.mkdir(exist_ok=True)
    errors = 0
    for rep in range(1, REPS + 1):
        uid = base.unit_id(COND, DOC, rep)
        path = unit_dir / f"{uid}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ok":
            continue
        record = {"unit": uid, "condition": COND, "doc": DOC, "rep": rep, "condition_sha256": meta["sha256"],
                  "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            result = base.annotate_with_guidelines(document.text, text, entities, provider,
                                                   instructions="", output_configuration=output_configuration)
            record.update(status="ok", annotations=[asdict(a) for a in result.annotations],
                          raw_response=result.raw_response, usage=provider.last_usage)
            errors = 0
        except Exception as exc:  # recorded and retried on the next invocation
            record.update(status="error", error=f"{type(exc).__name__}: {exc}", usage=provider.last_usage)
            errors += 1
        record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{record['finished']} {uid} {record['status']}", flush=True)
        if errors >= base.MAX_CONSECUTIVE_ERRORS:
            print(f"aborting after {errors} consecutive errors", flush=True)
            sys.exit(1)


if __name__ == "__main__":
    main()
