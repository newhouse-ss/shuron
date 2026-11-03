"""Mechanical error overview of the 30 validation runs (10/29), three comparisons kept apart.

Offline, no API calls. Reads error_rows.csv (error_table.py, whose TP/FP/FN match valid_metrics.json) and each run's
valid_metrics.json. Error kinds follow reproduction/lib/discrepancy.py: label, boundary, missed, extra, and unpaired
overlap, which is split here into its gold side (counts in FN) and prediction side (counts in FP). Identities checked
per run: FP = label + boundary + extra + unpaired_pred; FN = label + boundary + missed + unpaired_gold.

A. The 19 original-guideline runs: what the original guideline's errors look like (denominator: 19 runs).
B. Method endpoints: E1 run01-10, top-1 loop01-10, top-4 loop01-10, each loop's final guideline, including the loops
   that stopped at the original guideline (denominator: 10 runs per method).
C. The 11 changed guidelines against the 19 original runs: per guideline, its single run minus the original mean,
   with the original range (denominator: one run per guideline, reference 19 runs).
D. (10/29, after the independent review) The same 11 runs by gold label: strict TP change per label and the error state
   behind the largest part of it; rank correlation of F1 with each label's TP; counts outside the original range.
Writes error_overview_output.txt and error_overview.json.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
KINDS = ["label", "boundary", "missed", "unpaired_gold", "extra", "unpaired_pred"]

rows = list(csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")))
runs = list(dict.fromkeys(r["run"] for r in rows))
info = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}


def kind(r: dict) -> str:
    if r["kind"] != "unpaired":
        return r["kind"]
    return "unpaired_gold" if r["gold_text"] else "unpaired_pred"


cnt = {x: Counter() for x in runs}
lab_pair = {x: Counter() for x in runs}      # (gold label, pred label) for label mismatches
miss_lab = {x: Counter() for x in runs}      # gold label of missed and unpaired gold
extra_lab = {x: Counter() for x in runs}     # pred label of extra and unpaired pred
bnd_lab = {x: Counter() for x in runs}       # gold label of boundary mismatches
for r in rows:
    k = kind(r)
    cnt[r["run"]][k] += 1
    if k == "label":
        lab_pair[r["run"]][(r["gold_label"], r["pred_label"])] += 1
    elif k in ("missed", "unpaired_gold"):
        miss_lab[r["run"]][(k, r["gold_label"])] += 1
    elif k in ("extra", "unpaired_pred"):
        extra_lab[r["run"]][(k, r["pred_label"])] += 1
    elif k == "boundary":
        bnd_lab[r["run"]][r["gold_label"]] += 1

met = {}
for x in runs:
    m = json.loads((OUT / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    met[x] = {"tp": m["true_positives"], "fp": m["false_positives"], "fn": m["false_negatives"], "p": m["precision"], "r": m["recall"], "f1": m["f1"]}
    c = cnt[x]
    assert met[x]["fp"] == c["label"] + c["boundary"] + c["extra"] + c["unpaired_pred"], x
    assert met[x]["fn"] == c["label"] + c["boundary"] + c["missed"] + c["unpaired_gold"], x

orig = [x for x in runs if info[x][2] == "original"]
changed = [x for x in runs if info[x][2] != "original"]
name = {x: f"{info[x][0]} {info[x][1]}" for x in runs}


def ms(vals):
    return f"{statistics.mean(vals):7.1f} (SD {statistics.stdev(vals):5.1f}, {min(vals)}-{max(vals)})" if len(vals) > 1 else f"{vals[0]}"


out, rec = [], {}
out.append("A. The 19 original-guideline runs (10 E1 runs + 9 loops that stopped at the original guideline). Per run: mean (SD, min-max)")
for k in ("tp", "fp", "fn"):
    out.append(f"   {k.upper():<14} {ms([met[x][k] for x in orig])}")
out.append(f"   {'F1':<14} {statistics.mean(met[x]['f1'] for x in orig):.4f} ({min(met[x]['f1'] for x in orig):.4f}-{max(met[x]['f1'] for x in orig):.4f})")
for k in KINDS:
    out.append(f"   {k:<14} {ms([cnt[x][k] for x in orig])}")
out.append("   FN = label + boundary + missed + unpaired_gold; FP = label + boundary + extra + unpaired_pred (checked for all 30 runs)")
out.append("   label mismatches by gold -> predicted label, mean per run:")
pairs = Counter()
for x in orig:
    pairs.update(lab_pair[x])
for (gl, pl), n in pairs.most_common():
    out.append(f"      {gl:<17} -> {pl:<17} {n / 19:6.1f}")
out.append("   missed (no overlapping prediction) and unpaired gold, by gold label, mean per run:")
mm = Counter()
for x in orig:
    mm.update(miss_lab[x])
for (k, gl), n in sorted(mm.items()):
    out.append(f"      {k:<14} {gl:<17} {n / 19:6.1f}")
out.append("   extra (no overlapping gold) and unpaired prediction, by predicted label, mean per run:")
ee = Counter()
for x in orig:
    ee.update(extra_lab[x])
for (k, pl), n in sorted(ee.items()):
    out.append(f"      {k:<14} {pl:<17} {n / 19:6.1f}")
out.append("   boundary mismatches by gold label, mean per run:")
bb = Counter()
for x in orig:
    bb.update(bnd_lab[x])
for gl, n in bb.most_common():
    out.append(f"      {gl:<17} {n / 19:6.1f}")
rec["original"] = {"runs": orig, "metrics": {x: met[x] for x in orig}, "kinds": {x: dict(cnt[x]) for x in orig}}

out.append("\nB. Method endpoints, 10 runs per method; each loop is scored with its final guideline")
for meth in ("E1", "top-1", "top-4"):
    xs = [x for x in runs if info[x][0] == meth]
    n_orig = sum(info[x][2] == "original" for x in xs)
    out.append(f"   {meth}: {len(xs)} runs, {n_orig} of them with the original guideline")
    out.append(f"      F1 {statistics.mean(met[x]['f1'] for x in xs):.4f} (SD {statistics.stdev(met[x]['f1'] for x in xs):.4f}); "
               f"P {statistics.mean(met[x]['p'] for x in xs):.4f}; R {statistics.mean(met[x]['r'] for x in xs):.4f}")
    for k in ("tp", "fp", "fn"):
        out.append(f"      {k.upper():<14} {ms([met[x][k] for x in xs])}")
    for k in KINDS:
        out.append(f"      {k:<14} {ms([cnt[x][k] for x in xs])}")

out.append("\nC. The 11 changed guidelines, one run each, minus the mean of the 19 original runs (original range in brackets)")
om = {k: statistics.mean(met[x][k] for x in orig) for k in ("tp", "fp", "fn")}
okm = {k: statistics.mean(cnt[x][k] for x in orig) for k in KINDS}
orng = {k: (min(cnt[x][k] for x in orig), max(cnt[x][k] for x in orig)) for k in KINDS}
mrng = {k: (min(met[x][k] for x in orig), max(met[x][k] for x in orig)) for k in ("tp", "fp", "fn")}
hdr = f"   {'guideline':<14} {'F1':>6} " + " ".join(f"{k.upper():>8}" for k in ("tp", "fp", "fn")) + " " + " ".join(f"{k:>14}" for k in KINDS)
out.append(hdr)
out.append(f"   {'orig mean':<14} {statistics.mean(met[x]['f1'] for x in orig):6.3f} " + " ".join(f"{om[k]:8.1f}" for k in ("tp", "fp", "fn")) + " "
           + " ".join(f"{okm[k]:14.1f}" for k in KINDS))
out.append(f"   {'orig range':<14} {'':>6} " + " ".join(f"{mrng[k][0]:>4}-{mrng[k][1]:<3}" for k in ("tp", "fp", "fn")) + " "
           + " ".join(f"{orng[k][0]:>9}-{orng[k][1]:<4}" for k in KINDS))
rec["changed"] = {}
for x in sorted(changed, key=lambda x: -met[x]["f1"]):
    d = {k: met[x][k] - om[k] for k in ("tp", "fp", "fn")}
    dk = {k: cnt[x][k] - okm[k] for k in KINDS}
    flag = lambda k: "*" if not orng[k][0] <= cnt[x][k] <= orng[k][1] else " "
    out.append(f"   {name[x]:<14} {met[x]['f1']:6.3f} " + " ".join(f"{d[k]:+8.1f}" for k in ("tp", "fp", "fn")) + " "
               + " ".join(f"{dk[k]:+13.1f}{flag(k)}" for k in KINDS))
    rec["changed"][name[x]] = {"metrics": met[x], "delta": d, "kinds": dict(cnt[x]), "delta_kinds": dk}
out.append("   * outside the range of the 19 original runs. Delta FN = sum of the label, boundary, missed, unpaired_gold deltas;"
           " delta FP = sum of the label, boundary, extra, unpaired_pred deltas.")
out.append("   label-mismatch pairs, changed run minus original mean (pairs with |delta| >= 3 in some guideline):")
allpairs = set().union(*(lab_pair[x] for x in runs))
for pr in sorted(allpairs):
    o = sum(lab_pair[x][pr] for x in orig) / 19
    deltas = {name[x]: lab_pair[x][pr] - o for x in changed}
    if any(abs(v) >= 3 for v in deltas.values()):
        out.append(f"      {pr[0]:<16}->{pr[1]:<16} orig {o:5.1f}  " + " ".join(f"{k.split()[0][-1]}{k.split()[1][-2:]}:{v:+.0f}" for k, v in deltas.items()))
out.append("   missed by gold label, changed run minus original mean (|delta| >= 3 in some guideline):")
for gl in ("SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention"):
    o = sum(miss_lab[x][("missed", gl)] for x in orig) / 19
    deltas = {name[x]: miss_lab[x][("missed", gl)] - o for x in changed}
    out.append(f"      {gl:<17} orig {o:5.1f}  " + " ".join(f"{k.split()[0][-1]}{k.split()[1][-2:]}:{v:+.0f}" for k, v in deltas.items()))
out.append("   (column key: 105 = top-1 loop05, 408 = top-4 loop08, ...)")

# D. Strict TP per gold label = gold mentions of the label minus its FN rows (label, boundary, missed, unpaired gold).
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
LABELS = ["SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention"]
n_lab = Counter(x["obj"] for p in VALID.glob("*.json") for x in json.loads(p.read_text(encoding="utf-8"))["denotations"])
fn_state = {x: Counter() for x in runs}
for r in rows:
    k = kind(r)
    if k in ("label", "boundary", "missed", "unpaired_gold"):
        fn_state[r["run"]][(r["gold_label"], f"label->{r['pred_label']}" if k == "label" else k)] += 1
tp_lab = {x: {lab: n_lab[lab] - sum(v for (gl, _), v in fn_state[x].items() if gl == lab) for lab in LABELS} for x in runs}
for x in runs:
    assert sum(tp_lab[x].values()) == met[x]["tp"], x


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for t in range(i, j + 1):
            r[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((p - ma) * (q - mb) for p, q in zip(ra, rb))
    return num / (sum((p - ma) ** 2 for p in ra) * sum((q - mb) ** 2 for q in rb)) ** 0.5


out.append("\nD. Strict TP change per gold label, changed run minus the original mean (* outside the original range); in brackets the"
           " error state whose count changed most for that label (positive = more of that error)")
tpo = {lab: statistics.mean(tp_lab[x][lab] for x in orig) for lab in LABELS}
tpr = {lab: (min(tp_lab[x][lab] for x in orig), max(tp_lab[x][lab] for x in orig)) for lab in LABELS}
sto = {key: sum(fn_state[x][key] for x in orig) / len(orig) for key in set().union(*(fn_state[x] for x in runs))}
out.append("   original mean (range): " + "  ".join(f"{lab} {tpo[lab]:.1f} ({tpr[lab][0]}-{tpr[lab][1]})" for lab in LABELS))
rec["by_label"] = {}
for x in sorted(changed, key=lambda x: -met[x]["f1"]):
    cells = []
    for lab in LABELS:
        flag = "*" if not tpr[lab][0] <= tp_lab[x][lab] <= tpr[lab][1] else " "
        top = max(sorted(key for key in sto if key[0] == lab), key=lambda key: abs(fn_state[x][key] - sto[key]))
        cells.append(f"{lab[:4]} {tp_lab[x][lab] - tpo[lab]:+6.1f}{flag}({top[1]} {fn_state[x][top] - sto[top]:+.1f})")
    out.append(f"   {name[x]:<14} F1 {met[x]['f1']:.3f}  " + "  ".join(cells))
    rec["by_label"][name[x]] = {lab: tp_lab[x][lab] - tpo[lab] for lab in LABELS}
out.append("   rank correlation (Spearman, ties averaged) of F1 with each label's strict TP over the 11 changed runs: "
           + ", ".join(f"{lab} {spearman([met[x]['f1'] for x in changed], [tp_lab[x][lab] for x in changed]):+.2f}" for lab in LABELS))
for key, label in (("f1", "F1"), ("fn", "FN")):
    lo, hi = min(met[x][key] for x in orig), max(met[x][key] for x in orig)
    below = [name[x] for x in changed if met[x][key] < lo]
    above = [name[x] for x in changed if met[x][key] > hi]
    out.append(f"   {label}: below the original range {len(below)} {below}; above it {len(above)} {above}; inside {len(changed) - len(below) - len(above)}")
lo, hi = orng["missed"]
out.append(f"   missed: fewer than the original mean {sum(cnt[x]['missed'] < okm['missed'] for x in changed)};"
           f" below the original range {sum(cnt[x]['missed'] < lo for x in changed)}; above it {sum(cnt[x]['missed'] > hi for x in changed)}")

(HERE / "error_overview.json").write_bytes((json.dumps(rec, indent=1, default=str) + "\n").encode("utf-8"))
(HERE / "error_overview_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
