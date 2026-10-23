"""RP v4 step 1: how much does DeepSeek's dev10 annotation vary between identical calls?

Design: todo-temp/deepseek-stability/20261016_deepseek_stability_design.md.
Fixed: the 10 dev documents of outputs/ncbi_disease/20260802_gpt54-high_moderation (74 gold); its original
guideline (text sha256 e6232d944d68, the same text the GPT-5.4 size_noise reference annotated); the
annotate_with_guidelines template with empty instructions and rationale + guideline section in the output;
one call per document; model deepseek-flash; max_tokens 64000; loop set scoring. Only the arm differs:

    A_off   thinking disabled, temperature 0
    B_on    thinking enabled, temperature not sent ("has no effect in thinking mode", API reference)

    probe   10577908 x 2 per arm = 4 calls, order A_off r1, B_on r1, A_off r2, B_on r2   -> units_probe/
    run     dev10 x 5 per arm = 100 calls, rep-major, the two arms alternate per document -> units/
    run --arms B_on --reps 20   step 2 (approved 2026-10-21): thinking on only, repeats 6-20 = 150 calls

Label spelling: from 2026-10-21 the pipeline maps "Specific Disease" and similar to the schema name
(pipeline.normalize_entity_labels). Units saved before that are mapped the same way when a report loads
them; the files keep what the model wrote.

Each unit stores the request settings, the prompt sha256, UTC start and finish, the response's id, model,
created, system_fingerprint and finish_reason, the full usage block, the visible content and the
reasoning_content. Finished units are skipped on rerun; three consecutive failed units abort the run.

Spending guard: before each call, the spending recorded in the command's unit directory plus the worst case
of the next call (every prompt character counted as a cache-miss token, max_tokens of output), all at peak
price, must stay within --budget-jpy. No call starts inside the peak window unless --allow-peak.

    python todo-temp/deepseek-stability/run_stability.py probe --dry-run   # payloads only, no network
    python todo-temp/deepseek-stability/run_stability.py probe             # 4 calls
    python todo-temp/deepseek-stability/run_stability.py report probe
    python todo-temp/deepseek-stability/run_stability.py run               # 100 calls, only after the probe is approved
    python todo-temp/deepseek-stability/run_stability.py report run
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from llm_guideline_moderation import iterative as it  # noqa: E402
from llm_guideline_moderation.pipeline import annotate_with_guidelines, normalize_entity_labels  # noqa: E402
from llm_guideline_moderation.providers.deepseek import DeepSeekProvider  # noqa: E402
from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
from llm_guideline_moderation.types import Annotation, EntityDefinition, OutputConfiguration  # noqa: E402

RUN = ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation"
OUT = Path(__file__).resolve().parent
UNIT_DIRS = {"probe": OUT / "units_probe", "run": OUT / "units"}
MODEL = "deepseek-flash"
MAX_TOKENS = 64000
ARMS = {"A_off": {"thinking": False, "temperature": 0.0},
        "B_on": {"thinking": True, "temperature": None}}
PROBE_DOC = "10577908.json"
PROBE_REPS = 2
RUN_REPS = 5
GUIDELINE_SHA256_PREFIX = "e6232d944d68"
GOLD_TOTAL = 74
MAX_CONSECUTIVE_ERRORS = 3
# Gold spans followed across repeats (design §4.3); all five documents are in dev10.
CASES = {"FALDH": ("10577908.json", 245, 295), "norrin": ("10484772.json", 949, 969),
         "G6PD": ("1303173.json", 1559, 1577), "PAH": ("1671881.json", 138, 185),
         "Tay-Sachs disease": ("8326491.json", 193, 210), "TSD": ("8326491.json", 213, 216)}

# deepseek-flash, USD per 1M tokens, off-peak; peak is 2x on weekdays UTC 01:00-04:00 and 06:00-10:00.
# api-docs.deepseek.com/quick_start/pricing read 2026-10-16 (the figures in cost_estimate.py). The price
# table did not render when re-read on 2026-10-20, after the 10/17 switch to DeepSeek-V4.1-Flash-1017.
USD_PER_M = {"miss": 0.15, "hit": 0.003, "out": 0.60}
PEAK_FACTOR = 2
PEAK_HOURS_UTC = [(1, 4), (6, 10)]
JPY_PER_USD = 158.086954  # open.er-api.com, 2026-10-16 00:02 UTC
BUDGET_JPY = {"probe": 100, "run": 1000}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def in_peak(moment: datetime) -> bool:
    return moment.weekday() < 5 and any(a <= moment.hour < b for a, b in PEAK_HOURS_UTC)


def cost_jpy(usage: dict, peak: bool) -> float:
    prompt = usage.get("prompt_tokens", 0) or 0
    hit = usage.get("prompt_cache_hit_tokens", 0) or 0
    miss = usage.get("prompt_cache_miss_tokens", prompt - hit) or 0
    out = usage.get("completion_tokens", 0) or 0
    usd = (miss * USD_PER_M["miss"] + hit * USD_PER_M["hit"] + out * USD_PER_M["out"]) / 1e6
    return usd * (PEAK_FACTOR if peak else 1) * JPY_PER_USD


def worst_call_jpy(prompt_chars: int) -> float:
    return cost_jpy({"prompt_tokens": prompt_chars, "prompt_cache_hit_tokens": 0,
                     "prompt_cache_miss_tokens": prompt_chars, "completion_tokens": MAX_TOKENS}, peak=True)


def load_inputs():
    guideline = (RUN / "inputs/initial_guidelines.txt").read_text(encoding="utf-8")
    assert sha256(guideline).startswith(GUIDELINE_SHA256_PREFIX) and len(guideline) == 7367, "guideline changed"
    manifest = json.loads((RUN / "inputs/sampled_train_documents.json").read_text(encoding="utf-8"))
    split = json.loads((ROOT / "reproduction/dev_splits/ncbi_disease_dev10.json").read_text(encoding="utf-8"))
    assert [d["filename"] for d in manifest] == split["documents"], "dev10 split != documents of the 08/02 run"
    documents = {d["filename"]: load_sampled_document(ROOT / d["path"]) for d in manifest}
    assert sum(len(d.gold_annotations) for d in documents.values()) == GOLD_TOTAL
    entities = [EntityDefinition(name=n) for n in
                json.loads((RUN / "inputs/entity_schema.json").read_text(encoding="utf-8"))]
    return guideline, documents, entities


OUTPUT_CONFIGURATION = OutputConfiguration(include_rationale=True, include_guideline_section=True)


class CaptureProvider:
    """Offline stand-in: records the prompt and returns an empty annotation list."""

    def __init__(self) -> None:
        self.prompt = ""

    def complete(self, task: str, prompt: str) -> str:
        self.prompt = prompt
        return '{"annotations": []}'


def render_prompt(document, guideline, entities) -> str:
    capture = CaptureProvider()
    annotate_with_guidelines(document.text, guideline, entities, capture,
                             instructions="", output_configuration=OUTPUT_CONFIGURATION)
    return capture.prompt


def plan(command: str, docs: list[str], arms: list[str] | None = None,
         reps: int | None = None) -> list[tuple[str, str, int]]:
    arms = arms or list(ARMS)
    if command == "probe":
        return [(arm, PROBE_DOC, rep) for rep in range(1, PROBE_REPS + 1) for arm in arms]
    return [(arm, doc, rep) for rep in range(1, (reps or RUN_REPS) + 1) for doc in docs for arm in arms]


def unit_id(arm: str, doc: str, rep: int) -> str:
    return f"{arm}__{doc.replace('.json', '')}__r{rep}"


def make_provider(arm: str, api_key: str | None = None) -> DeepSeekProvider:
    return DeepSeekProvider(model=MODEL, api_key=api_key, max_output_tokens=MAX_TOKENS, **ARMS[arm])


def load_units(unit_dir: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(unit_dir.glob("*.json"))]


def fix_labels(units: list[dict], entities) -> list[dict]:
    """Apply the pipeline's label mapping to units saved before it existed (a no-op on later units)."""
    for u in units:
        if u.get("annotations"):
            fixed = normalize_entity_labels([Annotation(**a) for a in u["annotations"]], entities)
            u["annotations"] = [asdict(a) for a in fixed]
    return units


def spent_jpy(unit_dir: Path) -> float:
    """Recorded spending at peak price; a unit without usage counts as the worst case."""
    total = 0.0
    for u in load_units(unit_dir):
        total += cost_jpy(u["usage"], peak=True) if u.get("usage") else worst_call_jpy(u["prompt_chars"])
    return total


def cmd_execute(args: argparse.Namespace) -> None:
    guideline, documents, entities = load_inputs()
    units = plan(args.cmd, list(documents), args.arms, args.reps)
    prompts = {doc: render_prompt(documents[doc], guideline, entities) for doc in {d for _, d, _ in units}}
    unit_dir = UNIT_DIRS[args.cmd]
    budget = BUDGET_JPY[args.cmd] if args.budget_jpy is None else args.budget_jpy

    if args.dry_run:
        dry = OUT / "dry_run"
        dry.mkdir(exist_ok=True)
        for doc, prompt in sorted(prompts.items()):
            (dry / f"prompt_{doc.replace('.json', '')}.txt").write_text(prompt, encoding="utf-8")
        for arm in ARMS:
            payload = make_provider(arm, api_key="dry-run").build_payload("annotate_with_guidelines",
                                                                          prompts[units[0][1]])
            for message in payload["messages"]:
                message["content"] = (f"<{len(message['content'])} chars, "
                                      f"sha256 {sha256(message['content'])[:12]}>")
            print(f"{arm} request body for {units[0][1]}:\n{json.dumps(payload, indent=2)}\n")
        chars = [len(p) for p in prompts.values()]
        worst = sum(worst_call_jpy(len(prompts[d])) for _, d, _ in units)
        print(f"guideline {len(guideline)} chars, sha256 {sha256(guideline)[:12]}; "
              f"prompt chars {min(chars)} to {max(chars)} over {len(prompts)} document(s); "
              f"{PROBE_DOC} prompt sha256 {sha256(prompts[PROBE_DOC])[:12] if PROBE_DOC in prompts else '-'}")
        print(f"order: {', '.join(f'{a} {d[:-5]} r{r}' for a, d, r in units[:6])}"
              f"{' ...' if len(units) > 6 else ''} ({len(units)} calls)")
        print(f"worst case, every call at the {MAX_TOKENS} cap and peak price: JPY {worst:,.0f}; "
              f"budget JPY {budget:,}")
        now = datetime.now(timezone.utc)
        print(f"now {now:%Y-%m-%d %H:%M} UTC, peak window: {in_peak(now)}")
        from llm_guideline_moderation.dotenv import load_dotenv
        load_dotenv()
        import os
        print(f"DEEPSEEK_API_KEY present: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")
        return

    from llm_guideline_moderation.dotenv import load_dotenv
    load_dotenv()
    providers = {arm: make_provider(arm) for arm in ARMS}
    unit_dir.mkdir(exist_ok=True)
    consecutive_errors = 0
    for arm, doc, rep in units:
        uid = unit_id(arm, doc, rep)
        path = unit_dir / f"{uid}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ok":
            continue
        prompt = prompts[doc]
        spent = spent_jpy(unit_dir)
        if budget and spent + worst_call_jpy(len(prompt)) > budget:  # 0 turns the guard off
            print(f"budget stop before {uid}: recorded about JPY {spent:,.0f} at peak price, worst case of "
                  f"next call JPY {worst_call_jpy(len(prompt)):,.0f}, budget JPY {budget:,}", flush=True)
            return
        started = datetime.now(timezone.utc)
        if in_peak(started) and not args.allow_peak:
            print(f"peak-window stop before {uid} at {started:%H:%M} UTC; rerun off-peak or pass --allow-peak",
                  flush=True)
            return
        provider = providers[arm]
        record = {"unit": uid, "arm": arm, "doc": doc, "rep": rep,
                  "settings": {"model": provider.model, "thinking": provider.thinking,
                               "temperature": provider.temperature, "max_tokens": provider.max_output_tokens,
                               "base_url": provider.base_url},
                  "prompt_chars": len(prompt), "prompt_sha256": sha256(prompt),
                  "started_utc": started.isoformat(timespec="seconds"), "peak": in_peak(started)}
        print(f"{record['started_utc']} {uid} start", flush=True)
        began = time.monotonic()
        try:
            result = annotate_with_guidelines(documents[doc].text, guideline, entities, provider,
                                              instructions="", output_configuration=OUTPUT_CONFIGURATION)
            record.update(status="ok", annotations=[asdict(a) for a in result.annotations])
            consecutive_errors = 0
        except Exception as exc:  # recorded, and retried on the next invocation
            record.update(status="error", error=f"{type(exc).__name__}: {exc}")
            consecutive_errors += 1
        response = provider.last_response
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        record.update(
            seconds=round(time.monotonic() - began, 1),
            finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            response={"id": response.get("id"), "model": response.get("model"),
                      "created": response.get("created"), "system_fingerprint": response.get("system_fingerprint"),
                      "finish_reason": choice.get("finish_reason")},
            usage=provider.last_usage, content=message.get("content"),
            reasoning_content=message.get("reasoning_content"))
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        reasoning = ((record["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens"))
        print(f"{record['finished_utc']} {uid} {record['status']} {record['seconds']}s "
              f"model={record['response']['model']} finish={record['response']['finish_reason']} "
              f"out={record['usage'].get('completion_tokens')} reasoning={reasoning} "
              f"recorded about JPY {spent_jpy(unit_dir):,.1f} at peak price", flush=True)
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            print(f"aborting after {consecutive_errors} consecutive errors", flush=True)
            sys.exit(1)


def keyset(annotations: list[dict]) -> set[tuple[int, int, str]]:
    return {(a["start"], a["end"], a["entity"]) for a in annotations}


def case_state(annotations: list[dict], start: int, end: int) -> str:
    exact = [a for a in annotations if a["start"] == start and a["end"] == end]
    if exact:
        return exact[0]["entity"]
    overlap = [a for a in annotations if a["start"] < end and a["end"] > start]
    if overlap:
        return ";".join(f"boundary:{a['entity']}[{a['start']},{a['end']})" for a in overlap)
    return "O"


def summarize(values: list[float]) -> str:
    if not values:
        return "-"
    return f"mean {statistics.mean(values):,.0f}, min {min(values):,.0f}, max {max(values):,.0f}"


def cmd_report(args: argparse.Namespace) -> None:
    _, documents, entities = load_inputs()
    units = fix_labels(load_units(UNIT_DIRS[args.units]), entities)
    report: dict = {"units": args.units, "n_units": len(units), "arms": {}}
    print(f"== {args.units}: {len(units)} unit(s) in {UNIT_DIRS[args.units].name}/ ==")

    rows = []
    for u in units:
        usage = u.get("usage") or {}
        gold = {(a.start, a.end, a.entity) for a in documents[u["doc"]].gold_annotations}
        pred = keyset(u.get("annotations") or [])
        rows.append({
            "unit": u["unit"], "arm": u["arm"], "doc": u["doc"], "rep": u["rep"], "status": u["status"],
            "model": u["response"]["model"], "fingerprint": u["response"].get("system_fingerprint"),
            "finish_reason": u["response"]["finish_reason"],
            "seconds": u["seconds"], "prompt_tokens": usage.get("prompt_tokens"),
            "cache_hit": usage.get("prompt_cache_hit_tokens"), "cache_miss": usage.get("prompt_cache_miss_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "content_chars": len(u.get("content") or ""), "reasoning_chars": len(u.get("reasoning_content") or ""),
            "predictions": len(pred), "tp": len(gold & pred), "fp": len(pred - gold), "fn": len(gold - pred),
            "jpy_offpeak": cost_jpy(usage, peak=False), "jpy_peak": cost_jpy(usage, peak=True),
            "faldh": case_state(u.get("annotations") or [], 245, 295) if u["doc"] == "10577908.json" else None,
            "error": u.get("error")})
    report["rows"] = rows

    if args.units == "probe":
        print(f"{'unit':26s}{'status':7s}{'model':24s}{'finish':8s}{'sec':>7s}{'in':>7s}{'hit':>7s}"
              f"{'out':>8s}{'reason':>8s}{'r.chars':>9s}{'pred':>5s}{'TP/FP/FN':>10s}  FALDH")
        for r in rows:
            print(f"{r['unit']:26s}{r['status']:7s}{str(r['model']):24s}{str(r['finish_reason']):8s}"
                  f"{r['seconds']:7.1f}{str(r['prompt_tokens']):>7s}{str(r['cache_hit']):>7s}"
                  f"{str(r['completion_tokens']):>8s}{str(r['reasoning_tokens']):>8s}{r['reasoning_chars']:9d}"
                  f"{r['predictions']:5d}{r['tp']:>4d}/{r['fp']}/{r['fn']:<4d}  {r['faldh']}")
            if r["error"]:
                print(f"    error: {r['error'][:300]}")

    print("\nper arm:")
    for arm in ARMS:
        arm_rows = [r for r in rows if r["arm"] == arm]
        ok = [r for r in arm_rows if r["status"] == "ok"]
        cell = {
            "calls": len(arm_rows), "ok": len(ok),
            "models": sorted({str(r["model"]) for r in arm_rows}),
            # The model field only echoes the alias, so the fingerprint is the one sign of a backend change.
            "fingerprints": sorted({str(r["fingerprint"]) for r in arm_rows}),
            "finish_reasons": {k: sum(r["finish_reason"] == k for r in arm_rows)
                               for k in sorted({str(r["finish_reason"]) for r in arm_rows})},
            "reasoning_tokens": [r["reasoning_tokens"] for r in arm_rows],
            "completion_tokens": [r["completion_tokens"] for r in arm_rows],
            "seconds": [r["seconds"] for r in arm_rows],
            "jpy_offpeak": sum(r["jpy_offpeak"] for r in arm_rows),
            "jpy_peak": sum(r["jpy_peak"] for r in arm_rows)}
        report["arms"][arm] = cell
        out = [r["completion_tokens"] or 0 for r in arm_rows]
        print(f"  {arm}: {len(ok)}/{len(arm_rows)} ok; models {cell['models']}; finish {cell['finish_reasons']}")
        print(f"    system_fingerprint {cell['fingerprints']}")
        print(f"    output tokens {summarize(out)}; reasoning tokens "
              f"{summarize([r['reasoning_tokens'] or 0 for r in arm_rows])}")
        print(f"    seconds {summarize([r['seconds'] for r in arm_rows])}; "
              f"cost JPY {cell['jpy_offpeak']:.2f} off-peak / {cell['jpy_peak']:.2f} peak")

    a_reason = [r["reasoning_tokens"] or 0 for r in rows if r["arm"] == "A_off"]
    b_reason = [r["reasoning_tokens"] or 0 for r in rows if r["arm"] == "B_on"]
    switch_ok = bool(a_reason) and bool(b_reason) and max(a_reason) == 0 and min(b_reason) > 0 and \
        all(r["reasoning_chars"] == 0 for r in rows if r["arm"] == "A_off")
    report["thinking_switch_effective"] = switch_ok
    print(f"\nthinking switch effective (A_off reasoning 0 and no reasoning text, B_on reasoning > 0): {switch_ok}")

    if args.units == "probe":
        calls_per_arm = len(documents) * RUN_REPS
        prompts_note = f"probe document {PROBE_DOC}: {len(documents[PROBE_DOC].gold_annotations)} gold, " \
                       f"dev10 mean {GOLD_TOTAL / len(documents):.1f}"
        print(f"\nextrapolation to the main run ({calls_per_arm} calls per arm; {prompts_note}):")
        report["extrapolation"] = {}
        for arm in ARMS:
            arm_rows = [r for r in rows if r["arm"] == arm and r["status"] == "ok"]
            if not arm_rows:
                print(f"  {arm}: no successful probe call")
                continue
            mean_off = statistics.mean(r["jpy_offpeak"] for r in arm_rows) * calls_per_arm
            max_off = max(r["jpy_offpeak"] for r in arm_rows) * calls_per_arm
            secs = statistics.mean(r["seconds"] for r in arm_rows) * calls_per_arm / 60
            report["extrapolation"][arm] = {"jpy_offpeak_mean": mean_off, "jpy_offpeak_max": max_off,
                                            "serial_minutes_mean": secs}
            print(f"  {arm}: JPY {mean_off:.1f} (probe mean) to {max_off:.1f} (probe max) off-peak, "
                  f"x{PEAK_FACTOR} at peak; about {secs:.0f} min serial")
        cap = worst_call_jpy(0) / PEAK_FACTOR * calls_per_arm * len(ARMS)
        print(f"  hard bound, every call at the {MAX_TOKENS} cap: JPY {cap:,.0f} off-peak (input excluded)")
    else:
        report.update(score_run(units, documents))

    out = OUT / f"report_{args.units}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwritten to {out.name}")


def score_run(units: list[dict], documents: dict, arms=None) -> dict:
    """dev10 F1 per complete repeat, its SD, prediction-level stability and the followed cases, per arm.

    ``arms`` defaults to this runner's arms; the Haiku trial passes its own (todo-temp/haiku-trial)."""
    result: dict = {}
    for arm in arms or ARMS:
        by_rep: dict[int, dict[str, list[dict]]] = {}
        for u in units:
            if u["arm"] == arm and u["status"] == "ok":
                by_rep.setdefault(u["rep"], {})[u["doc"]] = u["annotations"]
        complete = {rep: preds for rep, preds in sorted(by_rep.items()) if set(preds) == set(documents)}
        f1s, repeat_keys, cases = [], [], {name: [] for name in CASES}
        for rep, preds in complete.items():
            predictions = {doc: [Annotation(start=a["start"], end=a["end"], entity=a["entity"], text=a["text"])
                                 for a in anns] for doc, anns in preds.items()}
            summary = it._summarize_moderation_pairs(it._build_pairs(list(documents.values()), predictions), 1.0)
            f1s.append(summary.overall_f1)
            repeat_keys.append({(doc, *k) for doc, anns in preds.items() for k in keyset(anns)})
            for name, (doc, start, end) in CASES.items():
                cases[name].append(case_state(preds[doc], start, end))
        cell = {"complete_repeats": list(complete), "f1": f1s, "cases": cases}
        print(f"\n{arm}: complete repeats {list(complete)} (incomplete: {sorted(set(by_rep) - set(complete))})")
        if f1s:
            print(f"  dev10 F1 {[round(f, 4) for f in f1s]} mean {statistics.mean(f1s):.4f}"
                  + (f" sample SD {statistics.stdev(f1s):.4f}" if len(f1s) > 1 else ""))
            cell["f1_mean"] = statistics.mean(f1s)
            cell["f1_sd"] = statistics.stdev(f1s) if len(f1s) > 1 else None
        if len(repeat_keys) > 1:
            union, common = set().union(*repeat_keys), set.intersection(*repeat_keys)
            diffs = [len(a ^ b) for a, b in itertools.combinations(repeat_keys, 2)]
            cell.update(distinct=len(union), in_all=len(common), pair_diffs=diffs)
            print(f"  distinct predictions {len(union)}; in all {len(repeat_keys)} repeats {len(common)} "
                  f"({len(common) / len(union):.1%}); differing per repeat pair mean {statistics.mean(diffs):.1f} "
                  f"{diffs}")
        for name, states in cases.items():
            doc, start, end = CASES[name]
            gold = next(a.entity for a in documents[doc].gold_annotations if (a.start, a.end) == (start, end))
            print(f"  {name:18s} gold {gold:16s} {states}")
        result[arm] = cell
    return {"scores": result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("probe", "run"):
        p = sub.add_parser(name)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--budget-jpy", type=int, default=None, help=f"defaults: {BUDGET_JPY}")
        p.add_argument("--allow-peak", action="store_true")
        p.add_argument("--arms", nargs="+", choices=list(ARMS), default=None, help="default: both arms")
        p.add_argument("--reps", type=int, default=None, help=f"run only; default {RUN_REPS}")
    p_report = sub.add_parser("report")
    p_report.add_argument("units", choices=list(UNIT_DIRS))
    args = parser.parse_args()
    cmd_report(args) if args.cmd == "report" else cmd_execute(args)


if __name__ == "__main__":
    main()
