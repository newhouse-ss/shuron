"""Can the Round 3 guideline fix FALDH once its named FALDH exclusion is removed?

Design: nodes/2026-10-16_seminar/r4-attribution/isolation/20261016_r3_minus_faldh_design.md (10/16 meeting, professor's item 1).
Single variable relative to c1_R3: lines 41-45 (the FALDH "Do not annotate" example and the blank
line around it) and line 241 of iteration_04 guidelines_before are deleted; every other line is
kept byte for byte, including the general exception rule on line 12 and Example 4 on line 172.
Only FALDH's document (10577908) is annotated, with the model, template and output configuration
of run_isolation.py. Units go to units_r3minus/ so earlier results and their hashes stay untouched.

    c1_R3                   control, R3 as-is                                   3 reps
    c4_R3_minus_faldh       R3 minus the named FALDH exclusion                  5 reps
    c4b_minus_level         c4 minus "a molecular/substance entity or its       5 reps, follow-up only:
                            level/activity" on line 12                          run only if c4 annotates
                                                                                FALDH in <= 1/5 and the
                                                                                user approves
Order is rep-major (c1 r1, c4 r1, c1 r2, c4 r2, c1 r3, c4 r3, c4 r4, c4 r5), so a partial run
stays balanced. Every unit also stores the response's id, model and created_at, which the
provider itself does not keep. A spending guard stops the run before any call whose worst case
would take the recorded spending in units_r3minus/ over --budget-jpy (default 1000); the
follow-up therefore needs an explicitly raised budget.

    python nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py run --dry-run
    python nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py run                          # 8 calls
    python nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py run --conditions c4b_minus_level --budget-jpy N   # follow-up
    python nodes/2026-10-16_seminar/r4-attribution/isolation/run_r3_minus.py score
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

DOC = "10577908.json"
FALDH = (245, 295)
REPS = {"c1_R3": 3, "c4_R3_minus_faldh": 5, "c4b_minus_level": 5}
MAIN = ["c1_R3", "c4_R3_minus_faldh"]
# 1-based line number of guidelines_before -> exact line content
REMOVE = {
    41: "> Deficient activity of fatty aldehyde dehydrogenase",
    42: "",
    43: "- **Do not annotate**  ",
    44: "  because it refers to enzyme activity rather than a disease/pathological-state mention.",
    45: "",
    241: "    - In “deficient activity of fatty aldehyde dehydrogenase,” the phrase is **not** annotated "
         "because it refers to enzyme activity rather than a disease/pathological-state mention.",
}
LEVEL_OLD = "a mechanistic biological process, a molecular/substance entity or its level/activity, or an isolated"
LEVEL_NEW = "a mechanistic biological process, or an isolated"
UNIT_DIR = base.OUT / "units_r3minus"
# Spending guard. Before each call, everything already recorded in UNIT_DIR plus the worst case of the
# next call (64,000 output tokens) must stay within the budget, else the run stops. Prices are the higher
# of the two East US 2 rates listed by azurespeed.com (Data Zone Standard); FX from open.er-api.com,
# 2026-10-16 00:02 UTC. A unit without usage (an error) is counted at the worst case.
BUDGET_JPY = 1000
JPY_PER_USD = 158.086954
USD_PER_M = {"input": 2.75, "output": 16.50}
WORST_INPUT_TOKENS = 4500  # measured c1_R3 prompt on this document: 4,431


def cost_jpy(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * USD_PER_M["input"] + output_tokens * USD_PER_M["output"]) / 1e6 * JPY_PER_USD


WORST_CALL_JPY = cost_jpy(WORST_INPUT_TOKENS, 64000)


def spent_jpy() -> float:
    total = 0.0
    for path in UNIT_DIR.glob("*.json"):
        u = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(u, dict) or "unit" not in u:
            continue
        usage = u.get("usage") or {}
        if u.get("status") == "ok" and usage:
            total += cost_jpy(usage["input_tokens"], usage["output_tokens"])
        else:
            total += WORST_CALL_JPY
    return total


def build_conditions(snapshot: dict) -> dict[str, str]:
    r3 = snapshot["guidelines_before"]
    r3_file = (base.RUN / "rounds/iteration_03/guidelines_after.txt").read_text(encoding="utf-8")
    assert r3_file.strip() == r3.strip(), "R3 guideline file != snapshot"
    lines = r3.split("\n")
    assert len(lines) == 244, f"R3 has {len(lines)} lines, expected 244"
    for n, content in REMOVE.items():
        assert lines[n - 1] == content, f"line {n} is not what was planned: {lines[n - 1]!r}"
    kept = [line for i, line in enumerate(lines, 1) if i not in REMOVE]
    minus = "\n".join(kept)
    assert len(kept) == len(lines) - 6
    assert "fatty aldehyde" not in minus.lower() and "faldh" not in minus.lower(), "a FALDH mention survived"
    assert lines[11] in kept and lines[171] in kept, "line 12 or line 172 was touched"

    assert minus.count(LEVEL_OLD) == 1, "follow-up edit point not unique"
    level = minus.replace(LEVEL_OLD, LEVEL_NEW)
    assert "level/activity" not in level and "molecular/substance entity" not in level
    return {"c1_R3": r3, "c4_R3_minus_faldh": minus, "c4b_minus_level": level}


def plan(selected: list[str]) -> list[tuple[str, int]]:
    return [(c, r) for r in range(1, max(REPS[c] for c in selected) + 1) for c in selected if r <= REPS[c]]


def capture_response_meta(provider) -> dict:
    """Wrap the provider's JSON request so the last response's id/model/created_at are kept."""
    meta: dict = {}
    original = provider._request_json

    def wrapped(url, payload=None, method="POST"):
        response = original(url, payload=payload, method=method)
        if isinstance(response, dict):
            meta.clear()
            meta.update({k: response.get(k) for k in ("id", "model", "status", "created_at")})
        return response

    provider._request_json = wrapped
    return meta


def cmd_run(args: argparse.Namespace) -> None:
    selected = args.conditions or MAIN
    for cond in selected:
        assert cond in REPS, f"unknown condition {cond}"
    snapshot = base.load_snapshot()
    conditions = build_conditions(snapshot)
    document = base.load_documents()[DOC]
    entities = base.load_entities()
    output_configuration = base.OutputConfiguration(include_rationale=True, include_guideline_section=True)

    manifest = {"design": "nodes/2026-10-16_seminar/r4-attribution/isolation/20261016_r3_minus_faldh_design.md",
                "snapshot_sha256": base.hashlib.sha256(base.SNAPSHOT.read_bytes()).hexdigest(),
                "doc": DOC, "reps": REPS, "removed_lines": sorted(REMOVE),
                "follow_up_edit": {"old": LEVEL_OLD, "new": LEVEL_NEW}, "conditions": {}}
    for name, text in conditions.items():
        (base.OUT / "conditions" / f"{name}.txt").write_text(text, encoding="utf-8")
        manifest["conditions"][name] = {"chars": len(text), "lines": len(text.split("\n")),
                                        "sha256": base.sha256(text)}
    (base.OUT / "manifest_r3minus.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")

    if args.dry_run:
        for cond in conditions:
            cap = base.CaptureProvider()
            base.annotate_with_guidelines(document.text, conditions[cond], entities, cap,
                                          instructions="", output_configuration=output_configuration)
            (base.OUT / "dry_run" / f"{cond}__10577908__r3minus.txt").write_text(cap.prompt, encoding="utf-8")
            m = manifest["conditions"][cond]
            print(f"{cond:18s} lines {m['lines']}  guideline chars {m['chars']:6d}  prompt chars {len(cap.prompt):6d}  "
                  f"sha256 {m['sha256'][:12]}  guideline in prompt {conditions[cond] in cap.prompt}  "
                  f"doc in prompt {document.text in cap.prompt}")
        print("order:", ", ".join(f"{c} r{r}" for c, r in plan(selected)), f"({len(plan(selected))} calls)")
        return

    from llm_guideline_moderation.dotenv import load_dotenv
    from llm_guideline_moderation.providers.openai import OpenAIProvider

    load_dotenv()
    provider = OpenAIProvider.from_azure_env("5_4", reasoning_effort="high", max_output_tokens=64000)
    meta = capture_response_meta(provider)
    UNIT_DIR.mkdir(exist_ok=True)
    consecutive_errors = 0
    for cond, rep in plan(selected):
        uid = base.unit_id(cond, DOC, rep)
        path = UNIT_DIR / f"{uid}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ok":
            continue
        spent = spent_jpy()
        if args.budget_jpy and spent + WORST_CALL_JPY > args.budget_jpy:  # 0 turns the guard off
            print(f"budget stop before {uid}: spent about JPY {spent:,.0f}, worst case of next call "
                  f"JPY {WORST_CALL_JPY:,.0f}, budget JPY {args.budget_jpy:,}", flush=True)
            return
        record = {"unit": uid, "condition": cond, "doc": DOC, "rep": rep,
                  "condition_sha256": manifest["conditions"][cond]["sha256"],
                  "deployment": provider.model, "reasoning_effort": provider.reasoning_effort,
                  "max_output_tokens": provider.max_output_tokens,
                  "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
        print(f"{record['started']} {uid} start", flush=True)
        try:
            result = base.annotate_with_guidelines(document.text, conditions[cond], entities, provider,
                                                   instructions="", output_configuration=output_configuration)
            record.update(status="ok", annotations=[asdict(a) for a in result.annotations],
                          raw_response=result.raw_response, usage=provider.last_usage)
            consecutive_errors = 0
        except Exception as exc:  # recorded and retried on the next invocation
            record.update(status="error", error=f"{type(exc).__name__}: {exc}", usage=provider.last_usage)
            consecutive_errors += 1
        record["response"] = dict(meta)
        record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{record['finished']} {uid} {record['status']} model={meta.get('model')} "
              f"out={record['usage'].get('output_tokens')} spent about JPY {spent_jpy():,.0f}", flush=True)
        if consecutive_errors >= base.MAX_CONSECUTIVE_ERRORS:
            print(f"aborting after {consecutive_errors} consecutive errors", flush=True)
            sys.exit(1)


def faldh_state(preds: list[dict]) -> str:
    s, e = FALDH
    exact = [p for p in preds if p["start"] == s and p["end"] == e]
    if exact:
        return "fixed" if exact[0]["label"] == "SpecificDisease" else f"type_wrong:{exact[0]['label']}"
    overlap = [p for p in preds if p["start"] < e and p["end"] > s]
    if overlap:
        return ";".join(f"boundary:{p['label']}[{p['start']},{p['end']})" for p in overlap)
    return "O"


def cmd_score(args: argparse.Namespace) -> None:
    snapshot = base.load_snapshot()
    before = next(f for f in snapshot["diagnostics_before"]["files"] if f["filename"] == DOC)
    gold = base.keyset(before["reference_denotations"])
    assert (FALDH[0], FALDH[1], "SpecificDisease") in gold and len(gold) == 14

    rows = []
    for path in sorted(UNIT_DIR.glob("*.json")):
        u = json.loads(path.read_text(encoding="utf-8"))
        if u.get("status") != "ok":
            continue
        preds = [{"start": a["start"], "end": a["end"], "label": a["entity"]} for a in u["annotations"]]
        pred = base.keyset(preds)
        rows.append({"unit": u["unit"], "condition": u["condition"], "rep": u["rep"],
                     "faldh": faldh_state(preds), "tp": len(gold & pred), "fp": len(pred - gold),
                     "fn": len(gold - pred), "fn_items": sorted(gold - pred), "fp_items": sorted(pred - gold),
                     "model": (u.get("response") or {}).get("model"), "usage": u.get("usage", {})})

    table = {}
    for r in rows:
        cell = table.setdefault(r["condition"], {"n": 0, "faldh": [], "tp_fp_fn": [], "models": [],
                                                 "input_tokens": 0, "output_tokens": 0})
        cell["n"] += 1
        cell["faldh"].append(r["faldh"])
        cell["tp_fp_fn"].append((r["tp"], r["fp"], r["fn"]))
        cell["models"].append(r["model"])
        cell["input_tokens"] += r["usage"].get("input_tokens", 0)
        cell["output_tokens"] += r["usage"].get("output_tokens", 0)
    out = base.OUT / "scores_r3minus.json"
    out.write_text(json.dumps({"table": table, "units": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    for cond in REPS:
        c = table.get(cond)
        if c:
            print(f"{cond:18s} n={c['n']}  FALDH {c['faldh']}  TP/FP/FN {c['tp_fp_fn']}  "
                  f"tokens in {c['input_tokens']} out {c['output_tokens']}  models {sorted(set(map(str, c['models'])))}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--conditions", nargs="+")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--budget-jpy", type=int, default=BUDGET_JPY)
    sub.add_parser("score")
    args = ap.parse_args()
    {"run": cmd_run, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
