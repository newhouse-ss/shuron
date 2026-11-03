"""Per-loop and per-label tables for the 10/30 seminar feedback (10/31).

Offline, no API calls. Reads each loop's status.json, rounds/iteration_NN/snapshot.json and valid_metrics.json, the
error rows of error_table.py and the validation gold.

A. The 20 loops, one row each: rounds tried and kept, development F1 from the loop's own start (its round 1 annotated
   the development set with the original guideline) to its final guideline, and the final guideline's validation F1
   against the range of the 19 original-guideline runs.
B. The 44 rounds, one row each. A round compares two single development runs (current guideline, candidate). The SD of
   one run is taken from the 20 round-1 runs of the original guideline (same pipeline and scoring as the loops); two
   independent runs then differ with SD sqrt(2) times that. For each kept round: the chance that an unchanged
   guideline gains at least this much by run-to-run variation alone (normal approximation). The Haiku trial's SD
   0.015 (todo-temp/haiku-trial/report_output.txt, 20 runs) is used as a consistency check.
C. Starting point per gold label: gold mentions on validation, strict TP of the 19 original runs, what is left.
D. The 11 changed guidelines by label: strict TP change per gold label and wrong-prediction change per predicted
   label (FP split by the label the model predicted), each against the mean and range of the 19 original runs; per
   cell the error state that changed most.
Writes loop_label_tables_output.txt and loop_label_tables.json.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
LABELS = ["SpecificDisease", "DiseaseClass", "Modifier", "CompositeMention"]
TRIAL_SD = 0.0150  # Haiku trial, xhigh, 20 runs of the original guideline on the development set

rows = list(csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")))
runs = list(dict.fromkeys(r["run"] for r in rows))
info = {r["run"]: (r["method"], r["loop"], r["guideline"]) for r in rows}
orig = [x for x in runs if info[x][2] == "original"]
changed = [x for x in runs if info[x][2] != "original"]
assert len(orig) == 19 and len(changed) == 11
name = {x: f"{info[x][0]} {info[x][1]}" for x in runs}


def kind(r: dict) -> str:
    if r["kind"] != "unpaired":
        return r["kind"]
    return "unpaired_gold" if r["gold_text"] else "unpaired_pred"


met = {}
for x in runs:
    m = json.loads((OUT / x / "valid_metrics.json").read_text(encoding="utf-8"))["strict_match"]["pubannotation"]
    met[x] = {"tp": m["true_positives"], "fp": m["false_positives"], "fn": m["false_negatives"], "f1": m["f1"]}
f1_lo, f1_hi = min(met[x]["f1"] for x in orig), max(met[x]["f1"] for x in orig)
out, rec = [], {}

# A and B: loops and rounds
loops, rounds = [], []
for method, k in (("top-1", "topk1"), ("top-4", "topk4")):
    for i in range(1, 11):
        folder = OUT / f"20261022_haiku-xhigh_{k}_loop{i:02d}"
        st = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        rs = []
        for snap in sorted((folder / "rounds").glob("iteration_*/snapshot.json")):
            s = json.loads(snap.read_text(encoding="utf-8"))
            rs.append({"method": method, "loop": i, "round": s["iteration"], "kept": s["improved"],
                       "before": s["summary_before"]["overall_f1"], "candidate": s["summary_candidate"]["overall_f1"]})
        kept = [r for r in rs if r["kept"]]
        end = kept[-1]["candidate"] if kept else rs[0]["before"]
        assert abs(st["initial_f1"] - rs[0]["before"]) < 1e-9 and abs(st["final_f1"] - end) < 1e-9, folder.name
        run = folder.name
        assert abs(met[run]["f1"] - st["valid_strict_f1"]) < 1e-4, run
        loops.append({"method": method, "loop": i, "tried": len(rs), "kept": len(kept), "dev_start": rs[0]["before"],
                      "dev_end": end, "valid_f1": met[run]["f1"], "guideline": info[run][2]})
        rounds += rs
assert len(loops) == 20 and len(rounds) == 44

out.append("A. The 20 loops. Development F1: the loop's own start (round 1, original guideline) -> its final guideline."
           f" Validation F1 of the final guideline; * outside the range of the 19 original runs ({f1_lo:.4f}-{f1_hi:.4f})")
out.append(f"   {'loop':<14} {'rounds':>6} {'kept':>4}  {'dev F1':<15}  {'valid F1':<9} final guideline")
for L in loops:
    flag = "*" if not f1_lo <= L["valid_f1"] <= f1_hi else " "
    out.append(f"   {L['method']} loop{L['loop']:02d}  {L['tried']:>6} {L['kept']:>4}  {L['dev_start']:.3f} -> {L['dev_end']:.3f}  "
               f"{L['valid_f1']:.4f}{flag}  {'original (stopped at round 1)' if L['guideline'] == 'original' else 'changed'}")
n_changed = sum(L["guideline"] != "original" for L in loops)
n_out = sum(1 for L in loops if L["guideline"] != "original" and not f1_lo <= L["valid_f1"] <= f1_hi)
out.append(f"   loops ending with a changed guideline {n_changed}; with the original guideline {20 - n_changed};"
           f" changed guidelines outside the original range {n_out}")
out.append(f"   original-guideline runs: 10 E1 runs + {20 - n_changed} loops = {10 + 20 - n_changed}")
assert 10 + 20 - n_changed == len(orig)
rec["loops"] = loops

starts = [L["dev_start"] for L in loops]
sd1 = statistics.stdev(starts)
lo_sd, hi_sd = sd1 * math.sqrt(19 / 32.852), sd1 * math.sqrt(19 / 8.907)   # chi-square 2.5% and 97.5% points, 19 df
diff_sd = sd1 * math.sqrt(2)
nd = statistics.NormalDist(0, diff_sd)
out.append(f"\nB. The 44 rounds. One development run of the original guideline: SD {sd1:.4f} over the 20 round-1 runs"
           f" (95% range of the true SD {lo_sd:.4f}-{hi_sd:.4f}; Haiku trial {TRIAL_SD:.4f}, inside it)."
           f" Two runs differ with SD {diff_sd:.4f}. 'chance': for a kept round, the chance that an unchanged guideline"
           " gains at least this much (normal); + marks a chance of 5% or more")
for r in rounds:
    g = r["candidate"] - r["before"]
    tail = ""
    if r["kept"]:
        p = 1 - nd.cdf(g)
        r["chance"] = p
        tail = f"  chance {p:5.1%}{' +' if p >= 0.05 else ''}"
    out.append(f"   {r['method']} loop{r['loop']:02d} round {r['round']}  {'kept    ' if r['kept'] else 'rejected'}  "
               f"{r['before']:.3f} -> {r['candidate']:.3f} ({g:+.3f}){tail}")
kept_r = [r for r in rounds if r["kept"]]
n_noise = sum(r["chance"] >= 0.05 for r in kept_r)
nd_trial = statistics.NormalDist(0, TRIAL_SD * math.sqrt(2))
n_noise_trial = sum(1 - nd_trial.cdf(r["candidate"] - r["before"]) >= 0.05 for r in kept_r)
out.append(f"   kept rounds {len(kept_r)}; chance of 5% or more: {n_noise} (with the trial SD {TRIAL_SD}: {n_noise_trial});"
           f" gain at which the chance is 5%: {1.6449 * diff_sd:.3f}")
rec["rounds"] = rounds
rec["noise"] = {"sd_one_run": sd1, "sd_range": [lo_sd, hi_sd], "sd_diff": diff_sd, "kept": len(kept_r),
                "chance_ge_5pct": n_noise, "chance_ge_5pct_trial_sd": n_noise_trial}

# C and D: by label
n_lab = Counter(x["obj"] for p in VALID.glob("*.json") for x in json.loads(p.read_text(encoding="utf-8"))["denotations"])
assert sum(n_lab.values()) == 791
fn_state = {x: Counter() for x in runs}   # (gold label, state) for gold mentions not strictly correct
fp_state = {x: Counter() for x in runs}   # (predicted label, state) for predictions not strictly correct
for r in rows:
    k = kind(r)
    if k in ("label", "boundary", "missed", "unpaired_gold"):
        fn_state[r["run"]][(r["gold_label"], f"as {r['pred_label']}" if k == "label" else k)] += 1
    if k in ("label", "boundary", "extra", "unpaired_pred"):
        fp_state[r["run"]][(r["pred_label"], f"gold {r['gold_label']}" if k == "label" else k)] += 1
tp = {x: {lab: n_lab[lab] - sum(v for (gl, _), v in fn_state[x].items() if gl == lab) for lab in LABELS} for x in runs}
fp = {x: {lab: sum(v for (pl, _), v in fp_state[x].items() if pl == lab) for lab in LABELS} for x in runs}
for x in runs:
    assert sum(tp[x].values()) == met[x]["tp"] and sum(fp[x].values()) == met[x]["fp"], x
ov = json.loads((HERE / "error_overview.json").read_text(encoding="utf-8"))["by_label"]

mean = lambda d, lab: statistics.mean(d[x][lab] for x in orig)
rng = lambda d, lab: (min(d[x][lab] for x in orig), max(d[x][lab] for x in orig))
out.append("\nC. Starting point per gold label on validation (19 original runs)")
out.append(f"   {'label':<17} {'gold':>5} {'strict TP mean':>15} {'share':>6} {'left':>6}")
rec["start"] = {}
for lab in LABELS:
    m = mean(tp, lab)
    out.append(f"   {lab:<17} {n_lab[lab]:>5} {m:>15.1f} {m / n_lab[lab]:>6.0%} {n_lab[lab] - m:>6.1f}")
    rec["start"][lab] = {"gold": n_lab[lab], "tp_mean": m, "left": n_lab[lab] - m}

out.append("\nD. The 11 changed guidelines, one run each, minus the mean of the 19 original runs; * outside the original range."
           " TP by gold label; FP by predicted label (a prediction with that label whose span or label differs from gold)."
           " In brackets the state that changed most: for TP, where the label's gold mentions went instead"
           " (as <label> = labeled so, boundary, missed, unpaired_gold); for FP, what the wrong predictions were"
           " (gold <label> = a gold mention of that label, boundary, extra, unpaired_pred)")
out.append("   original mean (range): TP " + "  ".join(f"{lab[:4]} {mean(tp, lab):.1f} ({rng(tp, lab)[0]}-{rng(tp, lab)[1]})" for lab in LABELS)
           + " | FP " + "  ".join(f"{lab[:4]} {mean(fp, lab):.1f} ({rng(fp, lab)[0]}-{rng(fp, lab)[1]})" for lab in LABELS))
fn_o = {key: sum(fn_state[x][key] for x in orig) / 19 for key in set().union(*(fn_state[x] for x in runs))}
fp_o = {key: sum(fp_state[x][key] for x in orig) / 19 for key in set().union(*(fp_state[x] for x in runs))}
rec["by_label"] = {}
for x in sorted(changed, key=lambda x: -met[x]["f1"]):
    cells, R = [], {}
    for lab in LABELS:
        dt, df = tp[x][lab] - mean(tp, lab), fp[x][lab] - mean(fp, lab)
        assert abs(dt - ov[name[x]][lab]) < 1e-9, (x, lab)
        ft = "*" if not rng(tp, lab)[0] <= tp[x][lab] <= rng(tp, lab)[1] else " "
        ff = "*" if not rng(fp, lab)[0] <= fp[x][lab] <= rng(fp, lab)[1] else " "
        top_n = max(sorted(k for k in fn_o if k[0] == lab), key=lambda k: abs(fn_state[x][k] - fn_o[k]))
        top_p = max(sorted(k for k in fp_o if k[0] == lab), key=lambda k: abs(fp_state[x][k] - fp_o[k]))
        cells.append(f"{lab[:4]} TP {dt:+6.1f}{ft}({top_n[1]} {fn_state[x][top_n] - fn_o[top_n]:+.1f}) "
                     f"FP {df:+6.1f}{ff}({top_p[1]} {fp_state[x][top_p] - fp_o[top_p]:+.1f})")
        R[lab] = {"tp": dt, "tp_out": ft == "*", "fp": df, "fp_out": ff == "*",
                  "tp_top": [top_n[1], fn_state[x][top_n] - fn_o[top_n]], "fp_top": [top_p[1], fp_state[x][top_p] - fp_o[top_p]]}
    out.append(f"   {name[x]:<14} F1 {met[x]['f1']:.3f}")
    out += [f"      {c}" for c in cells]
    rec["by_label"][name[x]] = {"f1": met[x]["f1"], **R}
comp = [rec["by_label"][g]["CompositeMention"] for g in rec["by_label"]]
out.append(f"   CompositeMention over the 11: TP change {min(c['tp'] for c in comp):+.1f} to {max(c['tp'] for c in comp):+.1f},"
           f" FP change {min(c['fp'] for c in comp):+.1f} to {max(c['fp'] for c in comp):+.1f};"
           f" outside the range: TP {sum(c['tp_out'] for c in comp)}, FP {sum(c['fp_out'] for c in comp)}")
out.append("   checked: per run, TP over the labels = strict TP and FP over the labels = strict FP (valid_metrics.json);"
           " TP changes equal error_overview.json by_label")

(HERE / "loop_label_tables.json").write_bytes((json.dumps(rec, indent=1) + "\n").encode("utf-8"))
(HERE / "loop_label_tables_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
