"""Outside the Modifier subset, and the full FP account (10/29).

Offline, no API calls. Reuses modifier_subset.py (membership, v2 word lists) and pilot_cases.py (run states from
error_rows.csv, whose TP/FP/FN match valid_metrics.json).

A. FN side, the 495 gold mentions outside the subset: state counts per run, original mean and each changed guideline's
   change, by gold label x state. Minus the sum of the error-state changes equals the outside share of delta TP.
B. FP side, every non-strict prediction counted once:
   label or boundary error -> attributed to the gold it was paired with (member or not);
   extra (no overlapping gold) -> unattributed;
   prediction-side unpaired overlap -> attributed to the gold it overlaps if all of them are members or all are not,
   otherwise "spans member and non-member gold". The buckets are checked to sum to FP for every run.
C. top-4 loop10 outside the subset: the mentions it gets wrong that the original runs get right at least 15 of 19 times,
   by gold label and state; then four complete local views (seed 20261029) with every gold and every prediction in a
   window, for loop10 and for E1 run01.
A to C keep the old 495-mention boundary and are a local record only. D and E (10/29) drop that boundary:
D. All 791 gold mentions: every FN goes to one error type, the types sum to FN in every run (checked); each type also
   shows the part of its change on the 78 retrieved non-Modifier gold that the old boundary left out.
E. top-4 loop10 on all 791 gold: how many of its new errors the 48-mention coding covers.
Writes outside_subset_output.txt and outside_subset.json.
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import runpy
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    m = runpy.run_path(str(HERE / "modifier_subset.py"))
texts, gold, state, runs, orig, mod, name, rows, member, st = (m[k] for k in ("texts", "gold", "state", "runs", "orig", "mod", "name", "rows", "member", "st"))
ROOT = HERE.parents[2]
OUTRUNS = ROOT / "outputs" / "ncbi_disease"
OUTDIR = HERE.parent / "outputs"
cols = sorted(mod, key=lambda x: name[x])
short = {x: name[x].replace("top-", "").replace(" loop", "-") for x in runs}
outside = [k for k in gold if k not in member]
out, rec = [], {}

# ---------- A ----------
out.append(f"A. FN side: the {len(outside)} gold mentions outside the subset. Cells: gold label x state; original mean per run, then"
           " each changed guideline minus it. Error-state rows with |delta| >= 3 in some guideline are shown; 'other' sums the rest.")
out.append("   " + " " * 44 + "orig  " + " ".join(f"{short[x]:>6}" for x in cols))
cells = sorted({(k[3], st(x, k)) for x in runs for k in outside})
shown = Counter()
right_o = statistics.mean(sum(st(x, k) == "right" for k in outside) for x in orig)
out.append(f"   {'right (strict TP share)':<44}{right_o:5.1f} " + " ".join(f"{sum(st(x, k) == 'right' for k in outside) - right_o:+6.1f}" for x in cols))
other = {x: 0.0 for x in cols}
rec["fn_cells"] = {}
for lab, sv in cells:
    if sv == "right":
        continue
    ks = [k for k in outside if k[3] == lab]
    o = statistics.mean(sum(st(x, k) == sv for k in ks) for x in orig)
    d = {x: sum(st(x, k) == sv for k in ks) - o for x in cols}
    rec["fn_cells"][f"{lab} {sv}"] = {"orig": o, "delta": {name[x]: v for x, v in d.items()}}
    if any(abs(v) >= 3 for v in d.values()):
        out.append(f"   {lab + ' ' + sv:<44}{o:5.1f} " + " ".join(f"{d[x]:+6.1f}" for x in cols))
    else:
        for x in cols:
            other[x] += d[x]
out.append(f"   {'other error cells (each |delta| < 3)':<44}{'':5} " + " ".join(f"{other[x]:+6.1f}" for x in cols))
out.append("   by state only (all gold labels):")
for sv in ("missed", "label->DiseaseClass", "label->SpecificDisease", "label->CompositeMention", "label->Modifier", "boundary", "unpaired"):
    o = statistics.mean(sum(st(x, k) == sv for k in outside) for x in orig)
    out.append(f"   {sv:<44}{o:5.1f} " + " ".join(f"{sum(st(x, k) == sv for k in outside) - o:+6.1f}" for x in cols))

# ---------- B ----------
gold_by_doc = defaultdict(list)
for k in gold:
    gold_by_doc[k[0]].append(k)
fp = {x: Counter() for x in runs}
for r in rows:
    x = r["run"]
    if r["kind"] in ("label", "boundary"):
        gk = (r["doc"], int(r["gold_start"]), int(r["gold_end"]), r["gold_label"])
        fp[x][f"{r['kind']} error, paired gold is a member" if gk in member else f"{r['kind']} error, paired gold outside"] += 1
    elif r["kind"] == "extra":
        fp[x]["extra (no gold overlap), unattributed"] += 1
    elif r["kind"] == "unpaired" and r["pred_text"]:
        b, e = int(r["pred_start"]), int(r["pred_end"])
        ov = [k for k in gold_by_doc[r["doc"]] if k[1] < e and b < k[2]]
        mem = {k in member for k in ov}
        fp[x]["unpaired prediction, overlaps members only" if mem == {True} else
              "unpaired prediction, overlaps outside gold only" if mem == {False} else "unpaired prediction, spans member and outside gold"] += 1
for x in runs:
    v = json.loads((OUTRUNS / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]["false_positives"]
    assert sum(fp[x].values()) == v, x
out.append("\nB. FP account: every non-strict prediction once; buckets sum to FP for every run (checked). Original mean, then each changed guideline minus it")
buckets = sorted({b for c in fp.values() for b in c})
for b in buckets:
    o = statistics.mean(fp[x][b] for x in orig)
    out.append(f"   {b:<52}{o:5.1f} " + " ".join(f"{fp[x][b] - o:+6.1f}" for x in cols))
fo = statistics.mean(sum(fp[x].values()) for x in orig)
out.append(f"   {'FP total':<52}{fo:5.1f} " + " ".join(f"{sum(fp[x].values()) - fo:+6.1f}" for x in cols))
out.append("   (a label or boundary error is one FN and one FP; the FP is attributed to the paired gold)")
rec["fp"] = {name[x]: dict(fp[x]) for x in runs}

# ---------- C ----------
L10 = next(x for x in mod if name[x] == "top-4 loop10")
broken = [k for k in outside if sum(st(x, k) == "right" for x in orig) >= 15 and st(L10, k) != "right"]
fixed = [k for k in outside if sum(st(x, k) == "right" for x in orig) <= 4 and st(L10, k) == "right"]
out.append(f"\nC. top-4 loop10 outside the subset: wrong in loop10 but right in >=15 of 19 orig: {len(broken)}; right in loop10 but in <=4 of 19 orig: {len(fixed)}")
out.append("   the broken ones by gold label and loop10 state: " + str(dict(Counter((k[3], st(L10, k)) for k in broken).most_common())))
words = Counter(texts[k[0]][k[1]:k[2]].lower() for k in broken)
out.append("   their strings, most frequent: " + str(dict(words.most_common(25))))


def view(run, d, lo, hi):
    pr = json.loads((OUTRUNS / run / "valid_predictions" / f"{d}.json").read_text(encoding="utf-8"))
    t = texts[d]
    return [(x["span"]["begin"], x["span"]["end"], t[x["span"]["begin"]:x["span"]["end"]], x["obj"]) for x in pr.get("denotations", [])
            if x["span"]["begin"] < hi and lo < x["span"]["end"]]


E1 = next(x for x in orig if name[x] == "E1 run01")
rng = random.Random(20261029)
for k in rng.sample(sorted(broken), 4):
    d = k[0]
    t = texts[d]
    s = t.rfind(".", 0, k[1]) + 1
    e = t.find(".", k[2])
    e = len(t) if e < 0 else e + 1
    out.append(f"   -- {d} {k[1]}-{k[2]} gold {k[3]} {t[k[1]:k[2]]!r}; right in {sum(st(x, k) == 'right' for x in orig)}/19 orig; loop10: {st(L10, k)}")
    out.append(f"      sentence: {t[s:e].strip()}")
    out.append(f"      gold in sentence: {[(b, e2, t[b:e2], lab) for (dd, b, e2, lab) in gold_by_doc[d] if s <= b < e]}")
    out.append(f"      loop10 predictions: {view(L10, d, s, e)}")
    out.append(f"      E1 run01 predictions: {view(E1, d, s, e)}")


# ---------- D (10/29) ----------
# All 791 gold mentions, no retrieval boundary. Every FN (one per gold mention not strictly right) goes to exactly one
# error type; the types sum to FN for every run (checked). Gold Modifier errors and other gold labelled Modifier are
# report section 4; the other types are report section 5. Each type also shows how much of its change falls on the 78
# non-Modifier gold that the old word lists retrieved, i.e. what the old 495-mention table left out.
def etype(k, s_):
    if k[3] == "Modifier":
        return "gold Modifier, any error (section 4)"
    if s_ == "label->Modifier":
        return "other gold labelled Modifier (section 4)"
    if k[3] == "SpecificDisease" and s_ == "label->DiseaseClass":
        return "Specific labelled DiseaseClass"
    if k[3] == "DiseaseClass" and s_ == "label->SpecificDisease":
        return "DiseaseClass labelled Specific"
    if k[3] in ("SpecificDisease", "DiseaseClass") and s_ == "label->CompositeMention":
        return "Specific or DiseaseClass labelled Composite"
    if s_ == "missed" and k[3] in ("SpecificDisease", "DiseaseClass"):
        return f"{k[3]} missed"
    if s_ == "boundary":
        return "boundary (non-Modifier gold)"
    if s_ == "unpaired":
        return "unpaired gold side (non-Modifier gold)"
    return "rest (Composite gold label errors and misses)"


ETYPES = ["gold Modifier, any error (section 4)", "other gold labelled Modifier (section 4)", "Specific labelled DiseaseClass",
          "DiseaseClass labelled Specific", "Specific or DiseaseClass labelled Composite", "DiseaseClass missed",
          "SpecificDisease missed", "boundary (non-Modifier gold)", "unpaired gold side (non-Modifier gold)",
          "rest (Composite gold label errors and misses)"]
retrieved78 = [k for k in member if k[3] != "Modifier"]
assert len(retrieved78) == 78 and len(outside) == 495
ec = {x: Counter() for x in runs}
ec78 = {x: Counter() for x in runs}
for x in runs:
    for k in gold:
        s_ = st(x, k)
        if s_ != "right":
            ec[x][etype(k, s_)] += 1
            if k in member and k[3] != "Modifier":
                ec78[x][etype(k, s_)] += 1
    fn = json.loads((OUTRUNS / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]["false_negatives"]
    assert sum(ec[x].values()) == fn, x
out.append("\nD. All 791 gold mentions by error type (FN side; the types sum to FN in every run, checked). Original mean (min-max),"
           " then each changed guideline minus the mean (* outside the original range); second line: the part of that change"
           " on the 78 retrieved non-Modifier gold")
out.append("   " + " " * 48 + "orig".rjust(16) + "".join(f"{short[x]:>8}" for x in cols))
rec["all_gold_types"] = {}
for t_ in ETYPES:
    vals = [ec[x][t_] for x in orig]
    o = statistics.mean(vals)
    o78 = statistics.mean(ec78[x][t_] for x in orig)
    cells = "".join(f"{ec[x][t_] - o:+7.1f}{'*' if not min(vals) <= ec[x][t_] <= max(vals) else ' '}" for x in cols)
    out.append(f"   {t_:<48}{o:7.1f} ({min(vals)}-{max(vals)})".ljust(67) + cells)
    out.append(f"   {'   of which on the 78':<48}{o78:7.1f}".ljust(67) + "".join(f"{ec78[x][t_] - o78:+7.1f} " for x in cols))
    rec["all_gold_types"][t_] = {"orig_mean": o, "orig_range": [min(vals), max(vals)], "delta": {name[x]: ec[x][t_] - o for x in cols}}
ex = {x: sum(1 for r in rows if r["run"] == x and r["kind"] == "extra") for x in runs}
eo = statistics.mean(ex[x] for x in orig)
out.append(f"   {'extra predictions (FP side, no gold overlap)':<48}{eo:7.1f} ({min(ex[x] for x in orig)}-{max(ex[x] for x in orig)})".ljust(67)
           + "".join(f"{ex[x] - eo:+7.1f} " for x in cols))
dc = "DiseaseClass missed"
out.append("   DiseaseClass missed, changed run's count: " + ", ".join(f"{name[x]} {ec[x][dc]}" for x in cols))

# ---------- E (10/29) ----------
# Coverage of the loop10 per-mention coding: it covered only the 495 mentions outside the old word lists.
b_all = [k for k in gold if sum(st(x, k) == "right" for x in orig) >= 15 and st(L10, k) != "right"]
out.append(f"\nE. top-4 loop10, all 791 gold: wrong in loop10 but right in >=15 of 19 orig: {len(b_all)};"
           f" among the 495 (coded): {sum(k in outside for k in b_all)}; among the 78 retrieved non-Modifier gold: "
           f"{sum(k in member and k[3] != 'Modifier' for k in b_all)}; gold Modifier: {sum(k[3] == 'Modifier' for k in b_all)}")
out.append("   the 78-side ones, loop10 state: " + str(dict(Counter(st(L10, k) for k in b_all if k in member and k[3] != "Modifier"))))

(OUTDIR / "outside_subset.json").write_bytes((json.dumps(rec, indent=1) + "\n").encode("utf-8"))
(OUTDIR / "outside_subset_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
