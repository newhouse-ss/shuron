"""Sort every validation error into a pattern and compare the changed guidelines with the original one.

Offline, no API calls. Reads error_rows.csv (from error_table.py). Patterns are fixed string and label
rules (patterns_lib.py), applied in order; each distinct error gets exactly one pattern.

Normal spread: the 19 runs whose guideline is the original one (E1 run01-10 plus the 9 loops whose
final guideline equals the original). A changed loop's count is marked when it lies outside the
19 runs' range.

Also counts validation gold spans that start or end with a space (only a prediction that includes the space matches).

Writes error_patterns_output.txt and error_items_patterns.csv.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"

from patterns_lib import FAMILIES, PATTERNS, key, pattern  # noqa: E402


rows = list(csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")))
texts = {p.stem: json.loads(p.read_text(encoding="utf-8"))["text"] for p in VALID.glob("*.json")}
runs = list(dict.fromkeys(r["run"] for r in rows))
run_info = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}
orig_runs = [x for x in runs if run_info[x][2] == "original"]
changed_runs = [x for x in runs if run_info[x][2] != "original"]
assert len(orig_runs) == 19 and len(changed_runs) == 11

item_pattern: dict[tuple, str] = {}
item_rows: dict[tuple, dict] = {}
item_runs: dict[tuple, list[str]] = defaultdict(list)
for r in rows:
    k = key(r)
    item_runs[k].append(r["run"])
    if k not in item_pattern:
        t = texts[r["doc"]]
        after_gold = t[int(r["gold_end"]):int(r["gold_end"]) + 40] if r["gold_end"] else ""
        after_pred = t[int(r["pred_end"]):int(r["pred_end"]) + 40] if r["pred_end"] else ""
        item_pattern[k] = pattern(r, after_gold, after_pred)
        item_rows[k] = r

out = []
out.append(f"runs with the original guideline: {len(orig_runs)}; with a changed guideline: {len(changed_runs)}")
out.append("")

# --- pattern table over the 19 original-guideline runs ---
per_run = {x: Counter() for x in runs}
for r in rows:
    per_run[r["run"]][item_pattern[key(r)]] += 1
tot_orig = sum(sum(per_run[x].values()) for x in orig_runs)


def f1_gain(*ps: str) -> float:
    gains = []
    for x in orig_runs:
        m = json.loads((ROOT / "outputs" / "ncbi_disease" / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
        tp, fp, fn = m["true_positives"], m["false_positives"], m["false_negatives"]
        base = 2 * tp / (2 * tp + fp + fn)
        dtp = dfp = dfn = 0
        for r in rows:
            if r["run"] != x or item_pattern[key(r)] not in ps:
                continue
            if r["kind"] in ("label", "boundary"):
                dtp, dfp, dfn = dtp + 1, dfp + 1, dfn + 1
            elif r["gold_text"]:  # missed, unpaired gold
                dtp, dfn = dtp + 1, dfn + 1
            else:  # extra, unpaired prediction
                dfp += 1
        tp2, fp2, fn2 = tp + dtp, fp - dfp, fn - dfn
        gains.append(2 * tp2 / (2 * tp2 + fp2 + fn2) - base)
    return statistics.mean(gains)


out.append("A. Patterns, original guideline (19 runs). Errors per run: mean (min-max); share of all errors;")
out.append("   F1 gain if the pattern were fixed (mean over runs); distinct errors; errors made in >=15 of 19 runs;")
out.append(f"{'':3} {'mean':>6} {'range':>9} {'share':>6} {'F1+':>7} {'items':>5} {'>=15':>4}  pattern")
for p, desc in PATTERNS.items():
    vals = [per_run[x][p] for x in orig_runs]
    items_p = [k for k in item_pattern if item_pattern[k] == p and any(run_info[x][2] == "original" for x in item_runs[k])]
    stable = [k for k in items_p if sum(1 for x in item_runs[k] if run_info[x][2] == "original") >= 15]
    share = sum(vals) / tot_orig
    out.append(f"{p:3} {statistics.mean(vals):6.1f} {min(vals):>4}-{max(vals):<4} {share:6.1%} {f1_gain(p):+7.4f} {len(items_p):5} {len(stable):4}  {desc}")
out.append(f"total errors per run: {tot_orig / len(orig_runs):.1f}\n")
out.append("Pattern groups: errors per run (mean, min-max), share, F1 gain if the whole group were fixed")
for name, members in FAMILIES.items():
    vals = [sum(per_run[x][p] for p in members) for x in orig_runs]
    out.append(f"   {statistics.mean(vals):5.1f} ({min(vals)}-{max(vals)})  {sum(vals) / tot_orig:5.1%}  {f1_gain(*members):+.4f}  {name} [{' '.join(members)}]")
stable_occ = sum(len([x for x in item_runs[k] if run_info[x][2] == "original"]) for k in item_pattern
                 if sum(1 for x in item_runs[k] if run_info[x][2] == "original") >= 15)
out.append(f"errors made in >=15 of the 19 runs: {stable_occ / tot_orig:.1%} of all original-guideline errors\n")

# --- gold spans that start or end with a space: matched only by a prediction that includes the space ---
out.append("B. Validation gold spans that start or end with whitespace, and the errors they cause in the 19 runs")
spaced, partners = [], []
for d, t in texts.items():
    g = json.loads((VALID / f"{d}.json").read_text(encoding="utf-8"))
    spans = [(x["span"]["begin"], x["span"]["end"]) for x in g.get("denotations", [])]
    for b, e in spans:
        if t[b:e] != t[b:e].strip():
            spaced.append((d, b, e))
            # a composite cut in two ("C6 or " + "C7 deficiency"): the gold mention that continues it
            partners += [(d, x, y) for x, y in spans if x == e or y == b]
for name, keys in (("those spans", set(spaced)), ("those spans and the gold mentions that continue them", set(spaced) | set(partners))):
    hit = sum(1 for r in rows if r["guideline"] == "original" and r["gold_text"]
              and (r["doc"], int(r["gold_start"]), int(r["gold_end"])) in keys)
    out.append(f"   {len(spaced)} gold spans with a stray space; errors per run on {name} ({len(keys)}): {hit / len(orig_runs):.1f}")
# the aligner (text_utils.align_annotations) keeps leading and trailing spaces, so a prediction that includes the
# stray space would match; count how often a run did (a stray-space span with no error row in that run)
orig_names = {r["run"] for r in rows if r["guideline"] == "original"}
with_error = {(r["run"], r["doc"], int(r["gold_start"]), int(r["gold_end"])) for r in rows if r["gold_text"]}
matched = sum(1 for run in orig_names for (d, b, e) in spaced if (run, d, b, e) not in with_error)
out.append(f"   stray-space spans matched exactly: {matched} of {len(spaced) * len(orig_names)} span x run cases "
           f"(the aligner keeps the space, so a prediction that includes it can match)")
out.append("")

# --- changed loops against the 19-run range ---
out.append("C. Changed guidelines: errors per pattern; * = outside the 19 original runs' range")
head = "   ".join(f"{run_info[x][0][-1]}{run_info[x][1][-2:]}" for x in changed_runs)
out.append(f"{'':3} {'range':>9}   {head}")
for p in PATTERNS:
    vals = [per_run[x][p] for x in orig_runs]
    lo, hi = min(vals), max(vals)
    cells = []
    for x in changed_runs:
        v = per_run[x][p]
        cells.append(f"{v:4}{'*' if v < lo or v > hi else ' '}")
    out.append(f"{p:3} {lo:>4}-{hi:<4}  " + " ".join(cells))
out.append("   column names: 1 = top-1 loop, 4 = top-4 loop, then the loop number")

(HERE / "error_patterns_output.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))

with (HERE / "error_items_patterns.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pattern", "doc", "kind", "gold_text", "gold_label", "pred_text", "pred_label", "original_of19", "changed_of11", "context"])
    for k, p in sorted(item_pattern.items(), key=lambda kv: (kv[1], -len(item_runs[kv[0]]))):
        r = item_rows[k]
        w.writerow([p, r["doc"], r["kind"], r["gold_text"], r["gold_label"], r["pred_text"], r["pred_label"],
                    sum(1 for x in item_runs[k] if run_info[x][2] == "original"),
                    sum(1 for x in item_runs[k] if run_info[x][2] != "original"),
                    r["context"]])

# numbers for the figures (make_figures.py)
f1s = {}
for x in runs:
    m = json.loads((ROOT / "outputs" / "ncbi_disease" / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    f1s[x] = 2 * m["true_positives"] / (2 * m["true_positives"] + m["false_positives"] + m["false_negatives"])
(HERE / "error_patterns.json").write_text(json.dumps({
    "patterns": PATTERNS,
    "families": FAMILIES,
    "family_f1_gain": {name: f1_gain(*members) for name, members in FAMILIES.items()},
    "runs": [{"run": x, "method": run_info[x][0], "loop": run_info[x][1], "guideline": run_info[x][2],
              "f1": f1s[x], "counts": {p: per_run[x][p] for p in PATTERNS}} for x in runs],
}, indent=1) + "\n", encoding="utf-8")
