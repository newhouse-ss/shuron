"""Check a finished locate output and summarise it. Offline, no API calls. 2026-11-06.

Usage: python -I check_locate.py <prefix> [<prefix> ...]   (prefix "original" = the original-guideline lookup)
For each prefix: every input id present exactly once; every record passes the same checks as append_locate_batch.py;
counts by status and role; basis quotes per prediction; share of basis quotes with an empty cited_as.
Reads <prefix>_locate.jsonl; for top4_loop01 also <prefix>_locate_haiku.jsonl (rows located by Claude Haiku 5.5).
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from append_locate_batch import paths, validate  # noqa: E402


def main():
    ok_all = True
    for prefix in sys.argv[1:]:
        inp, gpath, out, key = paths(prefix)
        ids = [json.loads(l)[key] for l in inp.read_text(encoding="utf-8").splitlines() if l.strip()]
        recs = []
        for f in (out, out.with_name(out.stem + "_haiku.jsonl")):
            if f.exists():
                recs += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        lines = gpath.read_text(encoding="utf-8").split("\n")
        got = collections.Counter(r[key] for r in recs)
        missing = [i for i in ids if i not in got]
        dup = [i for i, c in got.items() if c > 1]
        extra = [i for i in got if i not in set(ids)]
        bad = {}
        for r in recs:
            core = {k: r[k] for k in (key, "status", "quotes", "note")}
            p = validate(core, key, lines)
            if p:
                bad[r[key]] = p
        nb = [sum(q["role"] == "basis" for q in r["quotes"]) for r in recs]
        basis = [q for r in recs for q in r["quotes"] if q["role"] == "basis"]
        ok = not (missing or dup or extra or bad)
        ok_all &= ok
        print(f"{prefix}: {'PASS' if ok else 'FAIL'} | inputs {len(ids)} records {len(recs)} missing {len(missing)} "
              f"duplicates {len(dup)} unknown {len(extra)} failing checks {len(bad)}")
        print(f"   status {dict(collections.Counter(r['status'] for r in recs))} | roles "
              f"{dict(collections.Counter(q['role'] for r in recs for q in r['quotes']))}")
        print(f"   basis per prediction mean {sum(nb) / max(1, len(nb)):.2f}; basis with empty cited_as "
              f"{sum(q['cited_as'] == '' for q in basis)} of {len(basis)}")
        for rid, p in list(bad.items())[:10]:
            print(f"   check failed {rid}: {'; '.join(p)}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
