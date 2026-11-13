"""Case sheets for the 10/28 classification pilot: outcome strata over all validation gold mentions and extras, and a seeded sample.

Offline, no API calls. Reads error_rows.csv (from error_table.py, whose counts match valid_metrics.json) and the
validation gold. A gold mention is "right" in a run when no error row names it (a strict match); otherwise its state
is the kind of the first error row that names it (label, boundary, missed, unpaired).

Outcome strata are defined on the 19 original-guideline runs (orig) and the 11 changed-guideline runs (mod). They are
sampling strata only, not categories of the classification:
  persistent   right in <=4 of 19 orig and in <=1 of 11 mod
  improved     right in <=4 of 19 orig and in >=2 of 11 mod
  regressed    right in >=15 of 19 orig and wrong in >=2 of 11 mod
  form_change  wrong in >=15 of 19 orig with one dominant error kind, and some mod run wrong with another kind
  middle       right in 5 to 14 of 19 orig
  extra_persistent  a prediction overlapping no gold, made in >=15 of 19 orig
  extra_new         such a prediction made in 0 of 19 orig and in >=2 of 11 mod
A mention may meet several strata; for sampling it is assigned to the first in this order: regressed, improved,
form_change, persistent, middle. The full stratum sizes are printed (a census, not an estimate).

Sample: seed 20261028, fixed quota per stratum (QUOTA), at least one top-1 case where a stratum involves mod runs.
Writes pilot_cases_output.txt and pilot_cases.json.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
SEED = 20261028
QUOTA = {"persistent": 5, "improved": 5, "regressed": 6, "form_change": 4, "middle": 3, "extra_persistent": 2, "extra_new": 3}

rows = list(csv.DictReader((ROOT / "nodes/shared/error-analysis/outputs" / "error_rows.csv").open(encoding="utf-8")))
texts = {p.stem: json.loads(p.read_text(encoding="utf-8"))["text"] for p in VALID.glob("*.json")}
gold = sorted((d, x["span"]["begin"], x["span"]["end"], x["obj"])
              for d in texts for x in json.loads((VALID / f"{d}.json").read_text(encoding="utf-8"))["denotations"])
runs = list(dict.fromkeys(r["run"] for r in rows))
info = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}
orig = [x for x in runs if info[x][2] == "original"]
mod = [x for x in runs if info[x][2] != "original"]
assert len(orig) == 19 and len(mod) == 11
name = {x: f"{info[x][0]} {info[x][1]}" for x in runs}

state: dict[str, dict] = {x: {} for x in runs}      # gold key -> (kind, pred_text, pred_label)
extra: dict[str, dict] = {x: {} for x in runs}      # pred key -> pred_text
for r in rows:
    if r["gold_text"]:
        k = (r["doc"], int(r["gold_start"]), int(r["gold_end"]), r["gold_label"])
        state[r["run"]].setdefault(k, (r["kind"], r["pred_text"], r["pred_label"]))
    elif r["kind"] == "extra":
        extra[r["run"]][(r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"])] = r["pred_text"]


def st(x: str, k: tuple) -> str:
    return state[x][k][0] if k in state[x] else "right"


strata: dict[str, list] = defaultdict(list)
for k in gold:
    o = Counter(st(x, k) for x in orig)
    m = Counter(st(x, k) for x in mod)
    ro, rm = o["right"], m["right"]
    wrong_o = {s: n for s, n in o.items() if s != "right"}
    dom = max(wrong_o, key=wrong_o.get) if wrong_o else None
    tags = []
    if ro >= 15 and 11 - rm >= 2:
        tags.append("regressed")
    if ro <= 4 and rm >= 2:
        tags.append("improved")
    if ro <= 4 and dom and o[dom] >= 15 and any(s not in ("right", dom) for s in m.elements()):
        tags.append("form_change")
    if ro <= 4 and rm <= 1:
        tags.append("persistent")
    if 5 <= ro <= 14:
        tags.append("middle")
    for t in tags:
        strata[t].append(k)
    if tags:
        strata["_first"].append((tags[0], k))

xo = Counter(k for x in orig for k in extra[x])
xm = Counter(k for x in mod for k in extra[x])
strata["extra_persistent"] = sorted(k for k, n in xo.items() if n >= 15)
strata["extra_new"] = sorted(k for k, n in xm.items() if n >= 2 and xo[k] == 0)

rng = random.Random(SEED)
first = defaultdict(list)
for t, k in strata["_first"]:
    first[t].append(k)
first["extra_persistent"] = strata["extra_persistent"]
first["extra_new"] = strata["extra_new"]


def involves_top1(t: str, k: tuple) -> bool:
    mods = [x for x in mod if info[x][0] == "top-1"]
    if t.startswith("extra"):
        return any(k in extra[x] for x in mods)
    return any(st(x, k) != st(mods[0], k) or (t == "improved" and st(x, k) == "right") or (t == "regressed" and st(x, k) != "right") for x in mods)


sample = []
for t, q in QUOTA.items():
    pool = sorted(first[t])
    pick = rng.sample(pool, min(q, len(pool)))
    if t in ("improved", "regressed", "form_change", "extra_new") and not any(involves_top1(t, k) for k in pick):
        cand = [k for k in pool if k not in pick and involves_top1(t, k)]
        if cand:
            pick[-1] = rng.choice(cand)
    sample += [(t, k) for k in pick]


def ctx(d: str, b: int, e: int, w: int = 160) -> str:
    t = texts[d]
    return (t[max(0, b - w):b] + "[[" + t[b:e] + "]]" + t[e:e + w]).replace("\n", " ")


out = ["Stratum sizes (census over 791 gold mentions and all extras; strata overlap):"]
for t in ("persistent", "improved", "regressed", "form_change", "middle", "extra_persistent", "extra_new"):
    out.append(f"   {t:<17} {len(strata[t]):4}   assigned first: {len(first[t]):4}")
union = set().union(*(set(strata[t]) for t in ("persistent", "improved", "regressed", "form_change", "middle")))
out.append(f"   in no stratum (right in >=15 of 19 orig, wrong in <=1 of 11 mod): {len(gold) - len(union)}")
out.append(f"   gold mentions wrong in at least one of the 30 runs: {len({k for x in runs for k in state[x]})}; "
           f"distinct extra predictions over the 30 runs: {len({k for x in runs for k in extra[x]})}")
# 10/28 v2 additions: what the strata do and do not mean, and counts the first version left out
out.append("   note: strata are sampling labels. 'improved' does not by definition mean a higher right-rate in mod than in orig;"
           f" improved mentions whose rate does not rise: {sum(sum(k not in state[x] for x in mod) / 11 <= sum(k not in state[x] for x in orig) / 19 for k in strata['improved'])};"
           f" regressed mentions whose rate does not fall: {sum(sum(k not in state[x] for x in mod) / 11 >= sum(k not in state[x] for x in orig) / 19 for k in strata['regressed'])}")
out.append(f"   right in all 30 runs: {sum(all(k not in state[x] for x in runs) for k in gold)}; right in all 19 orig runs: {sum(all(k not in state[x] for x in orig) for k in gold)}")
_up = {(r["doc"], r["pred_start"], r["pred_end"], r["pred_label"]) for r in rows if r["kind"] == "unpaired" and r["pred_text"]}
out.append(f"   prediction-side unpaired overlaps (not counted among the extras): {sum(1 for r in rows if r['kind'] == 'unpaired' and r['pred_text'])} rows, {len(_up)} distinct predictions")
out.append(f"Sample: seed {SEED}, quota {QUOTA}, {len(sample)} cases\n")
rec = []
for i, (t, k) in enumerate(sample, 1):
    d, b, e, lab = k
    out.append("=" * 110)
    if t.startswith("extra"):
        out.append(f"P{i:02d} [{t}] {d} {b}-{e} predicted {lab} {texts[d][b:e]!r} (no overlapping gold); orig {xo[k]}/19, mod {xm[k]}/11")
        out.append("   mod runs making it: " + ", ".join(name[x] for x in mod if k in extra[x]))
        per = {name[x]: k in extra[x] for x in runs}
    else:
        o = Counter(st(x, k) for x in orig)
        out.append(f"P{i:02d} [{t}] {d} {b}-{e} gold {lab} {texts[d][b:e]!r}; orig states {dict(o)}")
        per = {}
        for x in mod:
            s = state[x].get(k)
            per[name[x]] = "right" if not s else f"{s[0]} -> {s[1]!r} {s[2]}"
            out.append(f"   {name[x]:<14} {per[name[x]]}")
        po = Counter(f"{state[x][k][1]!r} {state[x][k][2]}" for x in orig if k in state[x] and state[x][k][1])
        if po:
            out.append(f"   orig predictions when wrong: {dict(po.most_common(3))}")
    out.append(f"   context: {ctx(d, b, e)}")
    rec.append({"id": f"P{i:02d}", "stratum": t, "doc": d, "span": [b, e], "label": lab, "text": texts[d][b:e], "per_run": per})

# Development side: rejected rounds. A gold mention strictly right before the rewrite and not strictly right with the
# rejected candidate guideline (diagnostics_before / diagnostics_candidate of the round snapshot). Two drawn, same seed.
OUT = ROOT / "outputs" / "ncbi_disease"
DEV = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
rounds = json.loads((HERE / "rounds.json").read_text(encoding="utf-8"))
dev_pool = []
for r in rounds:
    if r["kept"]:
        continue
    folder = OUT / f"20261022_haiku-xhigh_topk{r['method'][-1]}_loop{r['loop']:02d}" / "rounds" / f"iteration_{r['round']:02d}"
    s = json.loads((folder / "snapshot.json").read_text(encoding="utf-8"))
    before = {f["filename"]: f for f in s["diagnostics_before"]["files"]}
    for f in s["diagnostics_candidate"]["files"]:
        b = before[f["filename"]]
        sb = {(x["start"], x["end"], x["label"]) for x in b["study_denotations"]}
        sc = {(x["start"], x["end"], x["label"]) for x in f["study_denotations"]}
        for g in f["reference_denotations"]:
            k = (g["start"], g["end"], g["label"])
            if k in sb and k not in sc:
                cand = [x for x in f["study_denotations"] if x["start"] < g["end"] and g["start"] < x["end"]]
                dev_pool.append((f"{r['method']} loop{r['loop']:02d} round {r['round']}", f["filename"], g, cand))
out.append("=" * 110)
out.append(f"Development, rejected rounds: {len(dev_pool)} gold mentions right before the rewrite and wrong with the rejected candidate")
_by = Counter(x[0] for x in dev_pool)
out.append(f"   from all {sum(1 for r in rounds if not r['kept'])} rejected rounds (mention x round); the {sum(1 for r in rounds if not r['kept'] and r['round'] == 1)}"
           f" first-round rejections contribute {sum(n for k, n in _by.items() if k.endswith('round 1'))}; by round: {dict(_by)}")
for j, (rid, fn, g, cand) in enumerate(rng.sample(dev_pool, 2), len(sample) + 1):
    t = json.loads((DEV / fn).read_text(encoding="utf-8"))["text"]
    c = "; ".join(f"{x['text']!r} {x['label']}" for x in cand) or "missed"
    out.append(f"P{j:02d} [dev_rejected] {rid} {fn} {g['start']}-{g['end']} gold {g['label']} {g['text']!r} -> candidate: {c}")
    out.append(f"   context: {(t[max(0, g['start'] - 160):g['start']] + '[[' + t[g['start']:g['end']] + ']]' + t[g['end']:g['end'] + 160])}")
    rec.append({"id": f"P{j:02d}", "stratum": "dev_rejected", "round": rid, "doc": fn, "span": [g["start"], g["end"]],
                "label": g["label"], "text": g["text"], "candidate": c})

(HERE / "pilot_cases.json").write_bytes((json.dumps(rec, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
(HERE / "pilot_cases_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out[:10]))
