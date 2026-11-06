"""Validate one batch of located predictions and append it to the locate output. Offline, no API calls. 2026-11-06.

Used by the agents that locate guideline text (notes/20261106_codex_locate_spec.md). The script never locates anything;
it only checks a batch written by a reader and appends it.

Usage:
  python -I append_locate_batch.py <prefix> <batch.json> [--out <file>]
<prefix> is a guideline prefix such as top4_loop08, or "original" for the original-guideline lookup.
<batch.json> is a JSON list of records:
  {"pred_id": ..., "status": "located"|"cannot_locate",
   "quotes": [{"quote", "line_start", "line_end", "condition_words", "role": "basis"|"ruled_out"|"context", "cited_as"}],
   "note": ...}
For "original" the id key is "lookup_id" instead of "pred_id".
Checks (all must pass, otherwise nothing is appended and the problems are printed, exit 1):
  ids belong to the input file and are not yet in the output, and appear once in the batch; every field present with the
  right type; enum values; located has quotes and cannot_locate has none and a note; every quote occurs in lines
  line_start..line_end of the guideline after removing * and _ and collapsing whitespace; condition_words is a substring
  of its quote (same normalisation).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "todo-temp" / "error-analysis" / "outputs" / "bar_clause_pilot" / "codex_locate"
ROLES, STATUS = {"basis", "ruled_out", "context"}, {"located", "cannot_locate"}
QFIELDS = {"quote": str, "line_start": int, "line_end": int, "condition_words": str, "role": str, "cited_as": str}


def norm(s):
    return re.sub(r"\s+", " ", s.replace("*", "").replace("_", "")).strip()


def paths(prefix):
    if prefix == "original":
        return (BASE / "inputs" / "original_lookup_predictions.jsonl", BASE / "inputs" / "guidelines" / "original.txt",
                BASE / "outputs" / "original_lookup_locate.jsonl", "lookup_id")
    return (BASE / "inputs" / f"{prefix}_predictions.jsonl", BASE / "inputs" / "guidelines" / f"{prefix}.txt",
            BASE / "outputs" / f"{prefix}_locate.jsonl", "pred_id")


def validate(rec, key, lines):
    p = []
    if set(rec) != {key, "status", "quotes", "note"}:
        p.append(f"fields must be exactly {key}, status, quotes, note (got {sorted(rec)})")
        return p
    if rec["status"] not in STATUS:
        p.append(f"bad status {rec['status']!r}")
    if not isinstance(rec["note"], str) or not isinstance(rec["quotes"], list):
        p.append("note must be a string and quotes a list")
        return p
    if rec["status"] == "located" and not rec["quotes"]:
        p.append("located without quotes")
    if rec["status"] == "cannot_locate" and (rec["quotes"] or not rec["note"].strip()):
        p.append("cannot_locate needs no quotes and a note")
    for i, q in enumerate(rec["quotes"]):
        if not isinstance(q, dict) or set(q) != set(QFIELDS):
            p.append(f"quote {i}: fields must be exactly {sorted(QFIELDS)}")
            continue
        bad = [k for k, t in QFIELDS.items() if not isinstance(q[k], t) or (t is int and isinstance(q[k], bool))]
        if bad:
            p.append(f"quote {i}: wrong type for {bad}")
            continue
        if q["role"] not in ROLES:
            p.append(f"quote {i}: bad role {q['role']!r}")
        if not (1 <= q["line_start"] <= q["line_end"] <= len(lines)):
            p.append(f"quote {i}: line range {q['line_start']}-{q['line_end']} outside 1-{len(lines)}")
            continue
        span = norm("\n".join(lines[q["line_start"] - 1:q["line_end"]]))
        if not norm(q["quote"]) or norm(q["quote"]) not in span:
            p.append(f"quote {i}: not verbatim in lines {q['line_start']}-{q['line_end']}")
        if q["condition_words"] and norm(q["condition_words"]) not in norm(q["quote"]):
            p.append(f"quote {i}: condition_words not inside the quote")
    return p


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    prefix, batch_path = sys.argv[1], Path(sys.argv[2])
    inp, gpath, out, key = paths(prefix)
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    ids = {json.loads(l)[key] for l in inp.read_text(encoding="utf-8").splitlines() if l.strip()}
    done = set()
    if out.exists():
        done = {json.loads(l)[key] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    lines = gpath.read_text(encoding="utf-8").split("\n")
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if not isinstance(batch, list) or not batch:
        sys.exit("batch must be a non-empty JSON list")
    problems, seen = {}, set()
    for n, rec in enumerate(batch):
        rid = rec.get(key, f"<record {n} without {key}>") if isinstance(rec, dict) else f"<record {n}>"
        p = [] if isinstance(rec, dict) else ["record is not an object"]
        if not p:
            if rid not in ids:
                p.append("id not in the input file")
            if rid in done:
                p.append("id already in the output")
            if rid in seen:
                p.append("id twice in this batch")
            seen.add(rid)
            p += validate(rec, key, lines)
        if p:
            problems[rid] = p
    if problems:
        print(f"REJECTED: {len(problems)} of {len(batch)} records have problems; nothing appended")
        for rid, p in problems.items():
            print(f"  {rid}: {'; '.join(p)}")
        sys.exit(1)
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for rec in batch:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"APPENDED {len(batch)} records to {out.name}; {len(done) + len(batch)} of {len(ids)} done")


if __name__ == "__main__":
    main()
