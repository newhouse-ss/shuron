"""Which validation mentions each changed guideline fixed or broke, and which guideline sections name them.

Offline, no API calls. Reads error_rows.csv (from error_table.py), the validation gold, each loop's final
guideline and round snapshots, and rounds.json (from rounds_table.py).

For each of the 11 changed guidelines (one validation run each):
- fixed: gold mentions it gets exactly right that at most 4 of the 19 original-guideline runs get right;
- broken: gold mentions it gets wrong that at least 15 of the 19 original runs get right;
- new extras: predictions overlapping no gold mention that at most 4 of the 19 original runs make;
- removed extras: such predictions made by at least 15 of the 19 original runs that it does not make.
Each fixed item takes the pattern of its most common error in the original runs; each broken item or new
extra takes the pattern of the changed run's error.

Chance level: the same four counts for each original run against the other 18, with the looser cut-offs
"at most 4 of 18" and "at least 14 of 18" (so chance is if anything overstated). Reported as mean and max.

Guideline links: the final guideline is split into sections at its headings. A section is "new" when its
text does not occur in the original guideline. For every flipped item, the sections that contain the gold
string (case-insensitive, whole words) are listed, and so is the round that first added the string.

Writes rule_links_output.txt and rule_links.json.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
OUT = ROOT / "outputs" / "ncbi_disease"
ORIGINAL = (ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt").read_text(encoding="utf-8").replace("\r\n", "\n")

from patterns_lib import FAMILIES, pattern  # noqa: E402

FAMILY_OF = {p: name for name, members in FAMILIES.items() for p in members}
SHORT_FAMILY = {
    "disease name used as a modifier, missed": "Modifier missed",
    "other missed mentions: symptoms, general words, tumors, deficiencies, the rest": "other missed",
    "span shorter or longer than the gold span": "span too short or long",
    "Modifier against disease or Composite label": "Modifier vs disease label",
    "Specific against DiseaseClass": "Specific vs DiseaseClass",
    "Composite label at the gold span, or one prediction over two gold mentions": "Composite or one over two",
    "extra mentions and other": "extras and other",
}

rows = list(csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")))
texts = {p.stem: json.loads(p.read_text(encoding="utf-8"))["text"] for p in VALID.glob("*.json")}
gold = {(d, x["span"]["begin"], x["span"]["end"], x["obj"])
        for d in texts for x in json.loads((VALID / f"{d}.json").read_text(encoding="utf-8"))["denotations"]}
runs = list(dict.fromkeys(r["run"] for r in rows))
info = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}
orig = [x for x in runs if info[x][2] == "original"]
changed = [x for x in runs if info[x][2] != "original"]
assert len(orig) == 19 and len(changed) == 11


def pat(r: dict) -> str:
    t = texts[r["doc"]]
    after_gold = t[int(r["gold_end"]):int(r["gold_end"]) + 40] if r["gold_end"] else ""
    after_pred = t[int(r["pred_end"]):int(r["pred_end"]) + 40] if r["pred_end"] else ""
    return pattern(r, after_gold, after_pred)


# status of every gold mention and every pure extra, per run
gold_err: dict[str, dict] = {x: {} for x in runs}    # gold key -> (pattern, row)
extras: dict[str, dict] = {x: {} for x in runs}      # prediction key -> (pattern, row)
true_miss = Counter()
miss_docs: dict[str, set] = {x: set() for x in runs}
for r in rows:
    if r["gold_text"]:
        k = (r["doc"], int(r["gold_start"]), int(r["gold_end"]), r["gold_label"])
        gold_err[r["run"]].setdefault(k, (pat(r), r))
        true_miss[r["run"]] += r["kind"] == "missed"
        if r["kind"] == "missed":
            miss_docs[r["run"]].add(r["doc"])
    elif r["kind"] in ("extra", "unpaired"):
        k = (r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"])
        extras[r["run"]].setdefault(k, (pat(r), r))


def flips(x: str, ref: list[str], lo: int, hi: int) -> dict:
    """Items run x fixed / broke and extras it added / removed, against the runs in ref."""
    right = Counter(k for y in ref for k in gold if k not in gold_err[y])
    made = Counter(k for y in ref for k in extras[y])
    res = {"fixed": [], "broken": [], "new_extra": [], "removed_extra": []}
    for k in sorted(gold):
        if k not in gold_err[x] and right[k] <= lo:
            p = Counter(gold_err[y][k][0] for y in ref if k in gold_err[y]).most_common(1)[0][0]
            res["fixed"].append((k, p, right[k]))
        elif k in gold_err[x] and right[k] >= hi:
            res["broken"].append((k, gold_err[x][k][0], right[k]))
    for k, (p, _) in extras[x].items():
        if made[k] <= lo:
            res["new_extra"].append((k, p, made[k]))
    for k, n in sorted(made.items()):
        if n >= hi and k not in extras[x]:
            p = Counter(extras[y][k][0] for y in ref if k in extras[y]).most_common(1)[0][0]
            res["removed_extra"].append((k, p, n))
    return res


def by_family(items: list) -> Counter:
    return Counter(SHORT_FAMILY[FAMILY_OF[p]] for _, p, _ in items)


# chance level: each original run against the other 18
chance = {kind: defaultdict(list) for kind in ("fixed", "broken", "new_extra", "removed_extra")}
chance_total = defaultdict(list)
chance_items = []
for x in orig:
    res = flips(x, [y for y in orig if y != x], 4, 14)
    chance_items.append({kind: [{"pattern": p, "doc": k[0], "span": [k[1], k[2]], "label": k[3]} for k, p, _ in res[kind]]
                         for kind in ("fixed", "broken")})
    for kind, items in res.items():
        chance_total[kind].append(len(items))
        fam = by_family(items)
        for f in SHORT_FAMILY.values():
            chance[kind][f].append(fam[f])


def heading_sections(text: str) -> list[dict]:
    lines = text.split("\n")
    starts = [i for i, s in enumerate(lines) if s.startswith("#")] + [len(lines)]
    secs = []
    if starts[0] > 0:
        starts = [0] + starts
    for a, b in zip(starts, starts[1:]):
        body = "\n".join(lines[a:b])
        secs.append({"heading": lines[a].strip() if lines[a].startswith("#") else "(top)", "first_line": a + 1,
                     "last_line": b, "text": body,
                     "new": re.sub(r"\s+", " ", body).strip() not in re.sub(r"\s+", " ", ORIGINAL)})
    return secs


def names(section_text: str, s: str) -> bool:
    s = s.strip()
    return bool(s) and re.search(r"(?<![\w-])" + re.escape(s) + r"(?![\w-])", section_text, re.I) is not None


rounds = json.loads((HERE / "rounds.json").read_text(encoding="utf-8"))
out = ["Chance level: one original-guideline run against the other 18 (cut-offs at most 4 / at least 14 of 18)",
       f"   fixed {statistics.mean(chance_total['fixed']):.1f} (max {max(chance_total['fixed'])}), "
       f"broken {statistics.mean(chance_total['broken']):.1f} (max {max(chance_total['broken'])}), "
       f"new extras {statistics.mean(chance_total['new_extra']):.1f} (max {max(chance_total['new_extra'])}), "
       f"removed extras {statistics.mean(chance_total['removed_extra']):.1f} (max {max(chance_total['removed_extra'])})",
       "   by group, mean (max) for fixed / broken / new extras:"]
for f in SHORT_FAMILY.values():
    out.append(f"   {f:<32} " + " / ".join(f"{statistics.mean(chance[k][f]):.1f} ({max(chance[k][f])})" for k in ("fixed", "broken", "new_extra")))
tm_orig = [true_miss[x] for x in orig]
md_orig = [len(miss_docs[x]) for x in orig]
out.append(f"\nTrue misses (gold mention overlapped by no prediction), original runs: mean {statistics.mean(tm_orig):.1f}, "
           f"SD {statistics.stdev(tm_orig):.1f}, range {min(tm_orig)}-{max(tm_orig)}; documents with at least one true miss: "
           f"mean {statistics.mean(md_orig):.1f}, range {min(md_orig)}-{max(md_orig)} of 100\n")

record = {"chance": {k: {f: [statistics.mean(v), max(v)] for f, v in d.items()} for k, d in chance.items()},
          "chance_total": {k: [statistics.mean(v), max(v)] for k, v in chance_total.items()},
          "chance_items": chance_items, "true_miss_original": tm_orig, "miss_docs_original": md_orig, "guidelines": {}}

for x in sorted(changed, key=lambda r: -json.loads((OUT / r / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]["f1"]):
    method, loop, _ = info[x]
    m = json.loads((OUT / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    guide = (OUT / x / "final" / "final_guidelines.txt").read_text(encoding="utf-8").replace("\r\n", "\n")
    secs = heading_sections(guide)
    res = flips(x, orig, 4, 15)
    out.append("=" * 100)
    out.append(f"{method} {loop}: validation F1 {m['f1']:.4f}, TP {m['true_positives']}, FP {m['false_positives']}, "
               f"FN {m['false_negatives']}, true misses {true_miss[x]} in {len(miss_docs[x])} documents; guideline {len(guide):,} chars, "
               f"{sum(s['new'] for s in secs)} of {len(secs)} sections new")
    out.append(f"   fixed {len(res['fixed'])}, broken {len(res['broken'])}, new extras {len(res['new_extra'])}, "
               f"removed extras {len(res['removed_extra'])}")
    out.append(f"   {'group':<32} {'fixed':>5} {'broken':>6} {'+extra':>6} {'-extra':>6}")
    fams = {k: by_family(v) for k, v in res.items()}
    for f in SHORT_FAMILY.values():
        if any(fams[k][f] for k in fams):
            out.append(f"   {f:<32} {fams['fixed'][f]:>5} {fams['broken'][f]:>6} {fams['new_extra'][f]:>6} {fams['removed_extra'][f]:>6}")
    # rounds of this loop that were kept, and the sections each one added
    kept = [r for r in rounds if r["method"] == method and r["loop"] == int(loop[-2:]) and r["kept"]]
    snaps = {s["iteration"]: s for s in (json.loads(p.read_text(encoding="utf-8")) for p in sorted((OUT / x / "rounds").glob("iteration_*/snapshot.json")))}
    added_in = {}
    for r in kept:
        s = snaps[r["round"]]
        before = {h["heading"] for h in heading_sections(s["guidelines_before"].replace("\r\n", "\n"))}
        new_heads = [h["heading"] for h in heading_sections(s["guidelines_candidate"].replace("\r\n", "\n")) if h["heading"] not in before]
        out.append(f"   kept round {r['round']}: dev F1 {r['f1_before']:.3f} -> {r['f1_candidate']:.3f}; targets "
                   + "; ".join(f"{t} {a}->{b}" for t, (a, b) in r["targets"].items()))
        for h in new_heads:
            out.append(f"      adds {h}")
            added_in.setdefault(h, r["round"])
    gl = {"f1": m["f1"], "tp": m["true_positives"], "fp": m["false_positives"], "fn": m["false_negatives"],
          "true_miss": true_miss[x], "miss_docs": len(miss_docs[x]), "families": {k: dict(v) for k, v in fams.items()}, "items": {}}
    for kind in ("fixed", "broken", "new_extra", "removed_extra"):
        out.append(f"   -- {kind}")
        for k, p, n in sorted(res[kind], key=lambda t: (t[1], t[0])):
            d, b, e, lab = k
            if kind in ("fixed", "broken"):
                r = gold_err[x][k][1] if kind == "broken" else next(gold_err[y][k][1] for y in orig if k in gold_err[y])
            else:
                r = (extras[x] if kind == "new_extra" else next(extras[y] for y in orig if k in extras[y]))[k][1]
            s = texts[d][b:e]
            hit = [f"{h['heading'][:60]} (L{h['first_line']}{', new' if h['new'] else ''}{', round ' + str(added_in[h['heading']]) if h['heading'] in added_in else ''})"
                   for h in secs if names(h["text"], s)]
            pred = f" -> {r['pred_text']!r} {r['pred_label']}" if kind == "broken" and r["pred_text"] else (" -> missed" if kind == "broken" else "")
            out.append(f"   {p:<3} {d} {s!r} {lab}{pred} [orig {n}/19]  named in: {'; '.join(hit) or '-'}")
            out.append(f"         ...{r['context'][:150]}...")
            gl["items"].setdefault(kind, []).append({"pattern": p, "doc": d, "span": [b, e], "label": lab, "text": s,
                                                     "orig_of19": n, "named_in": hit})
    record["guidelines"][f"{method} {loop}"] = gl

# 10/26: gold mentions by how many of the 19 original runs get them right. Mentions in the middle bin can
# never count as fixed or broken under the cut-offs above.
right19 = Counter(k for y in orig for k in gold if k not in gold_err[y])
bins = {"right in at most 4 of 19": sum(right19[k] <= 4 for k in gold),
        "right in 5 to 14 of 19": sum(5 <= right19[k] <= 14 for k in gold),
        "right in at least 15 of 19": sum(right19[k] >= 15 for k in gold)}
out.append("=" * 100)
out.append(f"Gold mentions ({len(gold)}) by how many of the 19 original runs get them exactly right "
           "(the middle bin can be neither fixed nor broken):")
for b, n in bins.items():
    out.append(f"   {b:<28} {n}")
record["original_correct_bins"] = bins

(HERE / "rule_links.json").write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
(HERE / "rule_links_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out[:20]))
