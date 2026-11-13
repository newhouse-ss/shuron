"""Locate the guideline text behind each prediction with Claude Haiku 5.5 (effort max, Message Batches). 2026-11-06.

Follows the locating rules of notes/20261106_codex_locate_spec.md (locating only: no merging, no aggregation). Reads
only the blinded inputs in outputs/bar_clause_pilot/codex_locate/inputs/ (no gold labels, no outcome differences).
One request per prediction; the reply is constrained to a JSON schema (structured outputs). The API key is loaded by
the project's own load_dotenv; this script never reads .env itself.

Usage:
  python -I haiku_locate.py run --prefix top4_loop01 --limit 10     # pilot: submit, wait, collect, check
  python -I haiku_locate.py run --prefix top4_loop01 --budget 4.5   # the rest, refused if the projected total exceeds the budget
  python -I haiku_locate.py collect --batch <id>                    # collect a batch submitted earlier

Pending predictions are those of <prefix>_predictions.jsonl not yet in <prefix>_locate.jsonl (Codex) nor in
<prefix>_locate_haiku.jsonl (this script). Results are appended to <prefix>_locate_haiku.jsonl; each batch also writes
haiku_runs/<batch_id>_summary.json (tokens, cost at batch prices, check results) and _thinking.jsonl (thinking summaries).
Cost: batch prices are half of $0.10 / $0.50 per million input / output tokens (Claude API skill, models table,
2026-10-06); all input tokens are priced at the input rate (no prompt caching is requested).
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))
from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402

BASE = ROOT / "nodes/2026-11-06_seminar/error-analysis/outputs" / "bar_clause_pilot" / "codex_locate"
INP, OUT = BASE / "inputs", BASE / "outputs"
RUNS = OUT / "haiku_runs"
MODEL, EFFORT, MAX_TOKENS = "claude-haiku-5-5", "max", 128000
PRICE_IN, PRICE_OUT = 0.10 / 2 / 1e6, 0.50 / 2 / 1e6

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["located", "cannot_locate"]},
        "quotes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "quote": {"type": "string"}, "line_start": {"type": "integer"}, "line_end": {"type": "integer"},
                "condition_words": {"type": "string"},
                "role": {"type": "string", "enum": ["basis", "ruled_out", "context"]},
                "cited_as": {"type": "string"}},
            "required": ["quote", "line_start", "line_end", "condition_words", "role", "cited_as"]}},
        "note": {"type": "string"}},
    "required": ["status", "quotes", "note"],
}

RULES = """You locate, in an annotation guideline, the text that an annotator model relied on for one prediction.
The annotator labelled disease mentions in a PubMed abstract following the guideline below, and for each prediction
wrote a citation (guideline_section) and a rationale. You get the prediction, its document context (the prediction is
marked [[...]]), the citation and the rationale. Find the guideline text the rationale relies on. You do not know
whether the prediction is correct; do not judge it and do not try to infer the gold label.

Return JSON with:
- quotes: one entry per guideline place the rationale relies on or cites. Each entry:
  - quote: the shortest contiguous span of the guideline, copied exactly (without the 4-digit line number and the tab),
    that states both the condition and the action (a label, "not annotated", or a span rule) the rationale relies on.
    It may cover consecutive lines; keep the text as in the guideline, including markup such as ** or quotation marks.
    If the rationale relies on a whole sentence or bullet, quote all of it.
  - line_start, line_end: the guideline line numbers of the quote.
  - condition_words: when the quoted rule lists several conditions (joined by "or", commas or a list) and the rationale
    invokes one of them, copy the words that name that condition (they must be a substring of the quote). Example:
    rationale "The disease name is the complement of the context noun risk in 'risk of breast cancer'" with the sentence
    "A disease name that premodifies, or is the complement of, a context or population noun ... is annotated Modifier"
    gives "is the complement of". If the rationale does not say which condition, use "".
  - role: "basis" if, according to the rationale, the label or span follows from this text (exceptions, precedence
    rules and examples the rationale relies on are basis too); "ruled_out" if the rationale cites this text to say it
    does not apply here (for example "What NOT 8 not applicable", or a rule cited only to explain why it is not used);
    "context" if it is cited or alluded to but not decisive, such as a definition named in passing.
  - cited_as: the fragment of guideline_section that points to this text, or "" if found only through the rationale.
- Split guideline_section at semicolons; every fragment must appear in some quote's cited_as or be explained in note
  (for example: the cited section does not exist in this guideline). If the citation names an item that does not
  exist but the rationale clearly relies on another existing text, quote that text and say so in note.
- status: "located", or "cannot_locate" if neither the citation nor the rationale leads to supporting text (then
  quotes is empty and note says why).
- note: at most 20 words; "" unless something is unusual.
Locate by reading the guideline; never guess a line from a section number alone.

GUIDELINE (each line starts with its 4-digit line number and a tab; these are not part of the text):
"""


def norm(s):
    return re.sub(r"\s+", " ", s.replace("*", "").replace("_", "")).strip()


def load(prefix):
    inputs = [json.loads(l) for l in (INP / f"{prefix}_predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    done = set()
    for f in (OUT / f"{prefix}_locate.jsonl", OUT / f"{prefix}_locate_haiku.jsonl"):
        if f.exists():
            done |= {json.loads(l)["pred_id"] for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
    return inputs, done


def system_prompt(prefix):
    return RULES + (INP / "guidelines" / f"{prefix}_numbered.txt").read_text(encoding="utf-8")


def user_text(p):
    keys = ["doc", "pred_text", "pred_label", "context", "guideline_section", "rationale"]
    return json.dumps({k: p[k] for k in keys}, ensure_ascii=False, indent=1)


def check(rec, lines):
    problems = []
    for q in rec["quotes"]:
        if not (1 <= q["line_start"] <= q["line_end"] <= len(lines)):
            problems.append("line range")
            continue
        span = norm("\n".join(lines[q["line_start"] - 1:q["line_end"]]))
        if norm(q["quote"]) not in span:
            problems.append(f"not verbatim at L{q['line_start']}-{q['line_end']}")
        if q["condition_words"] and norm(q["condition_words"]) not in norm(q["quote"]):
            problems.append("condition_words not in quote")
    if rec["status"] == "cannot_locate" and rec["quotes"]:
        problems.append("cannot_locate with quotes")
    if rec["status"] == "located" and not rec["quotes"]:
        problems.append("located without quotes")
    return problems


def collect(client, batch_id, prefix):
    meta = json.loads((RUNS / f"{batch_id}_request.json").read_text(encoding="utf-8"))
    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        print(f"  {time.strftime('%H:%M:%S')} {b.processing_status} processing={b.request_counts.processing}", flush=True)
        time.sleep(60)
    lines = (INP / "guidelines" / f"{prefix}.txt").read_text(encoding="utf-8").split("\n")
    tok_in = tok_out = 0
    stops, errors, problems_all, recs = {}, [], {}, []
    think = open(RUNS / f"{batch_id}_thinking.jsonl", "w", encoding="utf-8", newline="\n")
    for r in client.messages.batches.results(batch_id):
        pid = meta["custom_ids"][r.custom_id]
        if r.result.type != "succeeded":
            errors.append({"pred_id": pid, "type": r.result.type})
            continue
        m = r.result.message
        u = m.usage
        tin = (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
        tok_in += tin
        tok_out += u.output_tokens or 0
        stops[m.stop_reason] = stops.get(m.stop_reason, 0) + 1
        think.write(json.dumps({"pred_id": pid, "thinking": "\n".join(getattr(x, "thinking", "") or "" for x in m.content
                                                                      if x.type == "thinking")}, ensure_ascii=False) + "\n")
        if m.stop_reason != "end_turn":
            errors.append({"pred_id": pid, "type": f"stop_reason {m.stop_reason}"})
            continue
        text = "".join(x.text for x in m.content if x.type == "text")
        rec = json.loads(text)
        probs = check(rec, lines)
        if probs:
            problems_all[pid] = probs
        recs.append({"pred_id": pid, **rec, "locator": {"model": MODEL, "effort": EFFORT, "batch_id": batch_id},
                     "usage": {"input_tokens": tin, "output_tokens": u.output_tokens}, "check_problems": probs})
    think.close()
    order = {p: i for i, p in enumerate(meta["order"])}
    recs.sort(key=lambda x: order[x["pred_id"]])
    with open(OUT / f"{prefix}_locate_haiku.jsonl", "a", encoding="utf-8", newline="\n") as f:
        for x in recs:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    roles = {}
    for x in recs:
        for q in x["quotes"]:
            roles[q["role"]] = roles.get(q["role"], 0) + 1
    cost = tok_in * PRICE_IN + tok_out * PRICE_OUT
    summary = {
        "batch_id": batch_id, "prefix": prefix, "requests": len(meta["order"]), "written": len(recs),
        "errors": errors, "stop_reasons": stops, "status_counts": {s: sum(1 for x in recs if x["status"] == s)
                                                                   for s in ("located", "cannot_locate")},
        "roles": roles, "records_with_check_problems": len(problems_all), "check_problems": problems_all,
        "input_tokens": tok_in, "output_tokens": tok_out,
        "output_tokens_per_request": round(tok_out / max(1, len(recs))), "cost_usd_batch": round(cost, 4),
        "cost_usd_per_request": round(cost / max(1, len(recs) + len([e for e in errors if "stop_reason" in e["type"]])), 5),
        "output_sha256": hashlib.sha256((OUT / f"{prefix}_locate_haiku.jsonl").read_bytes()).hexdigest(),
    }
    (RUNS / f"{batch_id}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "check_problems"}, ensure_ascii=False, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "collect"])
    ap.add_argument("--prefix", default="top4_loop01")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--budget", type=float, default=4.5)
    ap.add_argument("--batch", default="")
    a = ap.parse_args()
    load_dotenv(ROOT / ".env")
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    client = anthropic.Anthropic()
    RUNS.mkdir(parents=True, exist_ok=True)
    if a.cmd == "collect":
        prefix = json.loads((RUNS / f"{a.batch}_request.json").read_text(encoding="utf-8"))["prefix"]
        collect(client, a.batch, prefix)
        return
    inputs, done = load(a.prefix)
    pending = [p for p in inputs if p["pred_id"] not in done]
    if a.limit:
        pending = pending[:a.limit]
    spent = sum(json.loads(f.read_text(encoding="utf-8"))["cost_usd_batch"] for f in RUNS.glob("*_summary.json"))
    per = [json.loads(f.read_text(encoding="utf-8"))["cost_usd_per_request"] for f in RUNS.glob("*_summary.json")]
    if per and not a.limit:
        projected = spent + max(per) * len(pending)
        print(f"spent ${spent:.3f}; projected total ${projected:.3f} for {len(pending)} more requests (budget ${a.budget})")
        if projected > a.budget:
            sys.exit("projected total exceeds the budget; not submitted")
    if not pending:
        sys.exit("nothing pending")
    system = system_prompt(a.prefix)
    custom = {f"r{i:04d}": p["pred_id"] for i, p in enumerate(pending)}
    reqs = [Request(custom_id=cid, params=MessageCreateParamsNonStreaming(
        model=MODEL, max_tokens=MAX_TOKENS, system=system,
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user_text(next(p for p in pending if p["pred_id"] == pid))}]))
        for cid, pid in custom.items()]
    batch = client.messages.batches.create(requests=reqs)
    (RUNS / f"{batch.id}_request.json").write_text(json.dumps(
        {"batch_id": batch.id, "prefix": a.prefix, "model": MODEL, "effort": EFFORT, "max_tokens": MAX_TOKENS,
         "custom_ids": custom, "order": [p["pred_id"] for p in pending],
         "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest()}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"submitted batch {batch.id} with {len(reqs)} requests", flush=True)
    collect(client, batch.id, a.prefix)


if __name__ == "__main__":
    main()
