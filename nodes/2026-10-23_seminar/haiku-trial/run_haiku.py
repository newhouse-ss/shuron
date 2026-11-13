"""Claude Haiku 5.5 trial on dev10: does it annotate as well and as steadily as DeepSeek, and what does a call cost?

Same fixed inputs as the DeepSeek stability test (nodes/2026-10-23_seminar/deepseek-stability/run_stability.py): the 10 dev
documents of the 08/02 run, its original guideline, the annotate_with_guidelines template with rationale and
guideline section, one call per document, label mapping, loop set scoring. The prompts are byte-identical to the
ones DeepSeek received (dry-run checks the hashes). Model claude-haiku-5-5, adaptive thinking with summaries,
max_tokens 64000, no temperature (Haiku 5.5 rejects one), and structured outputs with a JSON Schema built from
the prompt's own field list, so every reply that ends normally is valid JSON of the shape the prompt asks for.
Only the effort differs (medium dropped by the user, 2026-10-22):

    H_high     output_config.effort "high"
    H_xhigh    output_config.effort "xhigh"
    H_max      output_config.effort "max" (added 2026-10-22 after the high/xhigh batch; sent as its own batch with
               --arms H_max, 200 requests, same prompts, schema and 64000 cap)

    submit   Message Batches API, dev10 x 20 repeats per arm (high and xhigh: 400 requests in one batch, 2026-10-22)
             -> batch_state.json
             --reps N sends repeats 1..N only; a later submit sends what is not ok yet
             --arms runs a subset; --yes is required to send
    collect  fetch the batch results once it has ended                             -> units/

There is no separate standard-API probe (dropped 2026-10-22 at the user's request): requests that fail
validation in a batch come back "errored" and are not billed, and the request shape was checked by the key-check
call (key_check_output.txt) and the offline checks.

Rules fixed before the batch (2026-10-22):
    effort   high, unless xhigh beats it: a higher mean dev10 F1 with Welch p < 0.05
    max      (fixed before its batch, 2026-10-22) taken over xhigh only if a higher mean dev10 F1 with Welch
             p < 0.05. Its SD, FN, cut-offs and cost per call are reported but do not decide: with 20 runs an
             F-test confirms an SD difference only below a ratio of 0.63 (effort_efficiency_output.txt).
    report   per arm F1 mean and SD, repeat-to-repeat stability, the followed cases, how each reply was read as
             JSON, cut-offs, refusals, tokens and cost per call, batch duration; Welch against DeepSeek's 20
             thinking-on repeats with p and 95% CI. Which model becomes the main one is the user's decision; no
             threshold is set here.
    money    submit prints the cost if each request used DeepSeek's measured token counts (x1, x2, x3) and the
             bound with every output at the cap. The Console spend limit is the hard stop.

Prices, USD per 1M tokens (platform.claude.com/docs/en/about-claude/pricing, read 2026-10-22): prompt up to
100,000 tokens input 0.10, 5-minute cache write 0.125, cache read 0.01, output 0.50; prompt over 100,000 tokens
0.50 / 0.625 / 0.05 / 2.50; the Batch API halves all of them. A request's prompt length counts all its input
tokens. Yen at the rate the DeepSeek runner uses (2026-10-16).

The API key is read from ANTHROPIC_API_KEY, which the project's load_dotenv takes from .env.

    python nodes/2026-10-23_seminar/haiku-trial/run_haiku.py dry-run          # request bodies and costs, no network
    python nodes/2026-10-23_seminar/haiku-trial/run_haiku.py submit --yes     # 400 batch requests, only with the user's approval
    python nodes/2026-10-23_seminar/haiku-trial/run_haiku.py collect --wait   # poll every 60 s until the batch ends
    python nodes/2026-10-23_seminar/haiku-trial/run_haiku.py report
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / "deepseek-stability"))

import run_stability as rs  # noqa: E402
import welch_on_off as wo  # noqa: E402

from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402
from llm_guideline_moderation.providers._shared import annotation_json_schema  # noqa: E402
from llm_guideline_moderation.providers.claude import ClaudeProvider  # noqa: E402

MODEL = "claude-haiku-5-5"
MAX_TOKENS = 64000
ARMS = {"H_high": {"effort": "high"}, "H_xhigh": {"effort": "xhigh"}, "H_max": {"effort": "max"}}
TASK = "annotate_with_guidelines"
SCHEMA = annotation_json_schema(rs.OUTPUT_CONFIGURATION)
RUN_REPS = 20
UNITS = OUT / "units"
STATE = OUT / "batch_state.json"
PROMPT_CARD_LIMIT = 100_000
USD_PER_M = {False: {"in": 0.10, "write": 0.125, "read": 0.01, "out": 0.50},
             True: {"in": 0.50, "write": 0.625, "read": 0.05, "out": 2.50}}  # keyed by "prompt over 100K"
BATCH_FACTOR = 0.5


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def cost_jpy(usage: dict, batch: bool) -> float:
    fresh = usage.get("input_tokens", 0) or 0
    write = usage.get("cache_creation_input_tokens", 0) or 0
    read = usage.get("cache_read_input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    price = USD_PER_M[fresh + write + read > PROMPT_CARD_LIMIT]
    usd = (fresh * price["in"] + write * price["write"] + read * price["read"] + out * price["out"]) / 1e6
    return usd * (BATCH_FACTOR if batch else 1) * rs.JPY_PER_USD


def worst_call_jpy(prompt_chars: int, batch: bool) -> float:
    # Every prompt character counted as an uncached token (an overestimate) and output at the cap.
    return cost_jpy({"input_tokens": prompt_chars, "output_tokens": MAX_TOKENS}, batch)


def money_lines(n_requests: int, prompts: dict[str, str], units: list[tuple[str, str, int]]) -> list[str]:
    """Cost of n batch requests if each used DeepSeek's measured thinking-on token counts (x1..x3), and the bound."""
    deepseek = [u["usage"] for u in rs.load_units(rs.UNIT_DIRS["run"]) if u["arm"] == "B_on"]
    lines = []
    for k in (1, 2, 3):
        per = statistics.mean(cost_jpy({"input_tokens": x["prompt_tokens"],
                                        "output_tokens": x["completion_tokens"] * k}, True) for x in deepseek)
        lines.append(f"  output x{k} of DeepSeek's: JPY {per * n_requests:,.0f}")
    worst = sum(worst_call_jpy(len(prompts[d]), True) for _, d, _ in units)
    lines.append(f"  bound, every output at the {MAX_TOKENS:,} cap: JPY {worst:,.0f}")
    return lines


def make_provider(arm: str, api_key: str | None = None) -> ClaudeProvider:
    return ClaudeProvider(model=MODEL, max_output_tokens=MAX_TOKENS, json_schemas={TASK: SCHEMA},
                          api_key=api_key, **ARMS[arm])


def unit_id(arm: str, doc: str, rep: int) -> str:
    return f"{arm}__{doc.replace('.json', '')}__r{rep}"  # also the batch custom_id: [A-Za-z0-9_-], under 64


def plan(docs: list[str], arms: list[str] | None = None, reps: int = RUN_REPS) -> list[tuple[str, str, int]]:
    return [(arm, doc, rep) for rep in range(1, reps + 1) for doc in docs for arm in (arms or list(ARMS))]


def done() -> set[str]:
    return {u["unit"] for u in rs.load_units(UNITS) if u.get("status") == "ok"} if UNITS.exists() else set()


def load_key() -> bool:
    from llm_guideline_moderation.dotenv import load_dotenv

    load_dotenv()
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def message_fields(message: dict) -> dict:
    content = message.get("content") or []
    return {"response": {"id": message.get("id"), "model": message.get("model"),
                         "stop_reason": message.get("stop_reason"), "stop_details": message.get("stop_details")},
            "usage": message.get("usage") or {},
            "content": "\n".join(b.get("text", "") for b in content if b.get("type") == "text"),
            "thinking_summary": "\n".join(b.get("thinking", "") for b in content if b.get("type") == "thinking")}


def settings(provider: ClaudeProvider) -> dict:
    return {"model": MODEL, "effort": provider.effort, "max_tokens": MAX_TOKENS,
            "thinking": {"type": "adaptive", "display": provider.thinking_display},
            "output_format": "json_schema", "schema_sha256": rs.sha256(json.dumps(SCHEMA, sort_keys=True))}


class ReplayProvider:
    """Hands a saved Claude message to the pipeline, so batch results are parsed, aligned and label-mapped by
    the same code as live calls. It also checks that the prompt the pipeline renders now is the one sent."""

    def __init__(self, claude: ClaudeProvider, message: dict, prompt_sha256: str) -> None:
        self.claude, self.message, self.prompt_sha256 = claude, message, prompt_sha256

    def complete(self, task: str, prompt: str) -> str:
        if rs.sha256(prompt) != self.prompt_sha256:
            raise RuntimeError("rendered prompt differs from the one submitted")
        return self.claude.read_message(self.message, task)


def cmd_dry_run(args: argparse.Namespace) -> None:
    guideline, documents, entities = rs.load_inputs()
    prompts = {doc: rs.render_prompt(documents[doc], guideline, entities) for doc in documents}
    dry = OUT / "dry_run"
    dry.mkdir(exist_ok=True)
    for doc, prompt in sorted(prompts.items()):
        (dry / f"prompt_{doc.replace('.json', '')}.txt").write_text(prompt, encoding="utf-8")
    for arm in ARMS:
        params = make_provider(arm).build_params(TASK, prompts[rs.PROBE_DOC])
        for message in params["messages"]:
            message["content"] = f"<{len(message['content'])} chars, sha256 {rs.sha256(message['content'])[:12]}>"
        if arm != next(iter(ARMS)):
            params["output_config"]["format"] = f"<same schema as {next(iter(ARMS))}>"
        print(f"{arm} request params for {rs.PROBE_DOC}:\n{json.dumps(params, indent=2)}\n")
    deepseek = {u["doc"]: u["prompt_sha256"] for u in rs.load_units(rs.UNIT_DIRS["run"]) if u["arm"] == "B_on"}
    same = sorted(deepseek) == sorted(prompts) and all(rs.sha256(prompts[d]) == s for d, s in deepseek.items())
    print(f"prompts identical to those sent to DeepSeek (prompt_sha256 of its saved units): {same}; "
          f"prompt chars {min(map(len, prompts.values()))} to {max(map(len, prompts.values()))}")
    fields = list(SCHEMA["properties"]["annotations"]["items"]["properties"])
    shown = all(f'"{f}"' in prompts[rs.PROBE_DOC] for f in fields)
    print(f"schema fields {fields}, all required; each named in the prompt's JSON schema block: {shown}")
    units = plan(list(documents))
    print(f"{len(units)} batch requests; cost if each used DeepSeek's measured token counts:")
    print("\n".join(money_lines(len(units), prompts, units)))
    import anthropic

    print(f"anthropic SDK {anthropic.__version__}; ANTHROPIC_API_KEY present: {load_key()}")


def cmd_submit(args: argparse.Namespace) -> None:
    guideline, documents, entities = rs.load_inputs()
    if STATE.exists():
        sys.exit(f"{STATE.name} exists (batch {json.loads(STATE.read_text())['batch_id']}); run collect first")
    arms = args.arms or list(ARMS)
    prompts = {doc: rs.render_prompt(documents[doc], guideline, entities) for doc in documents}
    finished = done()
    units = [u for u in plan(list(documents), arms, args.reps) if unit_id(*u) not in finished]
    print(f"{len(units)} requests ({', '.join(f'{a} {sum(x == a for x, _, _ in units)}' for a in arms)}); "
          f"cost if each used DeepSeek's measured token counts:")
    print("\n".join(money_lines(len(units), prompts, units)))
    if not units:
        sys.exit("nothing to submit")
    if not args.yes:
        sys.exit("not sent: add --yes to submit")
    if not load_key():
        sys.exit("ANTHROPIC_API_KEY is not set (add it to .env)")
    from anthropic.types.messages.batch_create_params import Request

    providers = {arm: make_provider(arm) for arm in arms}
    requests = [Request(custom_id=unit_id(arm, doc, rep), params=providers[arm].build_params(TASK, prompts[doc]))
                for arm, doc, rep in units]
    batch = providers[arms[0]]._client().messages.batches.create(requests=requests)
    state = {"batch_id": batch.id, "created_utc": now_utc().isoformat(timespec="seconds"),
             "model": MODEL, "arms": {arm: ARMS[arm] for arm in arms}, "max_tokens": MAX_TOKENS, "schema": SCHEMA,
             "units": {unit_id(a, d, r): {"arm": a, "doc": d, "rep": r, "prompt_chars": len(prompts[d]),
                                          "prompt_sha256": rs.sha256(prompts[d])} for a, d, r in units}}
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    print(f"submitted batch {batch.id} ({batch.processing_status}); state in {STATE.name}")


def cmd_collect(args: argparse.Namespace) -> None:
    guideline, documents, entities = rs.load_inputs()
    if not STATE.exists():
        sys.exit(f"no {STATE.name}; submit first")
    if not load_key():
        sys.exit("ANTHROPIC_API_KEY is not set (add it to .env)")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    client = make_provider(next(iter(state["arms"])))._client()
    while True:
        batch = client.messages.batches.retrieve(state["batch_id"])
        print(f"{now_utc():%H:%M:%S} batch {batch.id}: {batch.processing_status} {batch.request_counts.to_dict()}",
              flush=True)
        if batch.processing_status == "ended" or not args.wait:
            break
        time.sleep(60)
    if batch.processing_status != "ended":
        return
    UNITS.mkdir(exist_ok=True)
    counts: dict[str, int] = {}
    for result in client.messages.batches.results(state["batch_id"]):
        meta = state["units"][result.custom_id]
        provider = make_provider(meta["arm"])
        record = {"unit": result.custom_id, **{k: meta[k] for k in ("arm", "doc", "rep", "prompt_chars",
                                                                     "prompt_sha256")},
                  "mode": "batch", "batch_id": state["batch_id"], "batch_created_utc": state["created_utc"],
                  "batch_ended_utc": batch.ended_at.isoformat() if batch.ended_at else None,
                  "settings": settings(provider), "result_type": result.result.type}
        if result.result.type == "succeeded":
            message = result.result.message.to_dict()
            record.update(message_fields(message))
            try:
                annotated = annotate_with_guidelines(
                    documents[meta["doc"]].text, guideline, entities,
                    ReplayProvider(provider, message, meta["prompt_sha256"]),
                    instructions="", output_configuration=rs.OUTPUT_CONFIGURATION)
                record.update(status="ok", annotations=[asdict(a) for a in annotated.annotations])
            except Exception as exc:
                record.update(status="error", error=f"{type(exc).__name__}: {exc}")
            record["json_extraction"] = provider.last_extraction
        else:  # errored, canceled or expired requests are not billed; a later submit sends them again
            record.update(status="error", usage={}, response={},
                          error=json.dumps(result.result.to_dict(), ensure_ascii=False)[:2000])
        counts[record["status"]] = counts.get(record["status"], 0) + 1
        path = UNITS / f"{result.custom_id}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ok":
            continue  # an earlier batch already produced this unit
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"written to {UNITS.name}/: {counts}")
    STATE.rename(OUT / f"batch_state_{state['batch_id']}.json")


def tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return out


def arm_summary(units: list[dict]) -> None:
    for arm in [a for a in ARMS if any(u["arm"] == a for u in units)]:
        rows = [u for u in units if u["arm"] == arm]
        ok = [u for u in rows if u["status"] == "ok"]
        usage = [u.get("usage") or {} for u in rows]
        out = [x.get("output_tokens") or 0 for x in usage]
        think = [(x.get("output_tokens_details") or {}).get("thinking_tokens") or 0 for x in usage]
        fresh = [x.get("input_tokens") or 0 for x in usage]
        jpy = [cost_jpy(x, True) for x in usage]
        print(f"  {arm}: {len(ok)}/{len(rows)} ok; stop reasons "
              f"{tally((u.get('response') or {}).get('stop_reason') or u.get('result_type') for u in rows)}; "
              f"JSON read as {tally(u.get('json_extraction') for u in rows)}")
        print(f"    input tokens {rs.summarize(fresh)}; output tokens {rs.summarize(out)}; thinking {rs.summarize(think)}")
        if jpy:
            print(f"    cost JPY {sum(jpy):.2f} at batch price, per call mean {statistics.mean(jpy):.3f}, "
                  f"max {max(jpy):.3f}")
        for u in rows:
            if u["status"] != "ok":
                print(f"    {u['unit']}: {u.get('error', '')[:300]}")


def effort_rule(scores: dict) -> None:
    levels = [a for a in ARMS if len(scores.get(a, {}).get("f1", [])) > 1]
    beats = {}
    for i, low in enumerate(levels):
        for high in levels[i + 1:]:
            w = wo.welch(scores[low]["f1"], scores[high]["f1"])
            beats[(high, low)] = w["diff"] > 0 and w["p"] < 0.05
            # Two-sided test, so either level can come out significantly better.
            verdict = (f"{high} significantly better" if beats[(high, low)] else
                       f"{low} significantly better" if w["diff"] < 0 and w["p"] < 0.05 else
                       "no significant difference")
            print(f"  {low} mean {w['mean_a']:.4f} SD {w['sd_a']:.4f}; {high} mean {w['mean_b']:.4f} "
                  f"SD {w['sd_b']:.4f}")
            print(f"  {high} minus {low}: {w['diff']:+.4f}, t {w['t']:.3f}, df {w['df']:.1f}, p {w['p']:.4f}, "
                  f"95% CI [{w['ci'][0]:+.4f}, {w['ci'][1]:+.4f}] -> {verdict}")
    if "H_max" in levels and "H_xhigh" in levels:
        print(f"max rule (max only if it beats xhigh): {'H_max' if beats[('H_max', 'H_xhigh')] else 'H_xhigh'}")
    first = [a for a in ("H_high", "H_xhigh") if a in levels]
    pick = next(low for i, low in enumerate(first) if not any(beats[(h, low)] for h in first[i + 1:]))
    print(f"effort rule of the high/xhigh batch (lowest level that no higher level beats): {pick}")


def cmd_report(args: argparse.Namespace) -> None:
    _, documents, entities = rs.load_inputs()
    units = rs.fix_labels(rs.load_units(UNITS), entities)
    print(f"== {len(units)} unit(s) in {UNITS.name}/ ==")
    arm_summary(units)
    for batch_id in sorted({u["batch_id"] for u in units if u.get("batch_id")}):
        first = next(u for u in units if u.get("batch_id") == batch_id)
        start = datetime.fromisoformat(first["batch_created_utc"])
        end = datetime.fromisoformat(first["batch_ended_utc"]) if first.get("batch_ended_utc") else None
        print(f"  batch {batch_id}: submitted {start:%Y-%m-%d %H:%M} UTC, "
              f"{f'ended after {(end - start).total_seconds() / 60:.0f} min' if end else 'end time unknown'}")
    present = {a: None for a in ARMS if any(u["arm"] == a for u in units)}
    scores = rs.score_run(units, documents, arms=present)["scores"]
    with contextlib.redirect_stdout(io.StringIO()):
        deepseek = rs.score_run(rs.fix_labels(rs.load_units(rs.UNIT_DIRS["run"]), entities), documents)["scores"]
    ds = deepseek["B_on"]["f1"]
    print(f"\nDeepSeek thinking on, {len(ds)} repeats: mean {statistics.mean(ds):.4f} SD {statistics.stdev(ds):.4f}")
    for arm in present:
        f1 = scores[arm]["f1"]
        if len(f1) > 1:
            w = wo.welch(ds, f1)
            print(f"  {arm} minus DeepSeek: {w['diff']:+.4f}, t {w['t']:.3f}, df {w['df']:.1f}, p {w['p']:.4f}, "
                  f"95% CI [{w['ci'][0]:+.4f}, {w['ci'][1]:+.4f}]")
    print()
    effort_rule(scores)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dry-run")
    p = sub.add_parser("submit")
    p.add_argument("--arms", nargs="+", choices=list(ARMS), default=None, help="default: all arms")
    p.add_argument("--reps", type=int, default=RUN_REPS, help=f"repeats 1..N (default {RUN_REPS})")
    p.add_argument("--yes", action="store_true", help="actually send the batch")
    p = sub.add_parser("collect")
    p.add_argument("--wait", action="store_true", help="poll every 60 s until the batch has ended")
    sub.add_parser("report")
    args = parser.parse_args()
    {"dry-run": cmd_dry_run, "submit": cmd_submit, "collect": cmd_collect, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
