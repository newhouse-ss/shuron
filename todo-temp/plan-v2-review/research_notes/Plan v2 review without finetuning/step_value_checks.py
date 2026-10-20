"""Offline value, noise and detectability checks for the remaining steps of plan v2 (no API calls).

Question: for each remaining step of docs/RP/20261020_research_plan_v2.md (S2a, S2b, S3, S4, S5, S6, S7,
voting, review-effort curve), how much can it plausibly gain on valid100, can the planned comparison
detect that gain, and how much human review (gold standing in for the expert) do the saved predictions
need to reach published reference points?

Everything is computed from saved artifacts. Nothing here loads credentials or calls a model.
Scoring, review-curve and bootstrap code are copied from todo-temp/direction-scan/offline_direction_checks.py
(not imported, because importing that module re-runs it and rewrites its output files). The copied scorer is
checked against reproduction/results/<label>/metrics.json (TP, FP, FN) for every run.

Inputs (read only):
    data/datasets/ncbi_disease/{train,valid}/*.json             gold, PubAnnotation
    outputs/.../<valid run>/*.json                                8 saved valid100 prediction sets
    reproduction/results/<label>/metrics.json                     saved strict counts
    reproduction/results/size_noise/repeat_0[1-5].json            5 dev30 repeats, original guideline
    outputs/ncbi_disease/<loop>/final/iterative_refinement_run.json   loop trajectories and guidelines

Outputs (next to this script): step_value_checks_output.txt, step_value_checks.json

    python -I step_value_checks.py
"""
import itertools
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
assert (ROOT / "reproduction/eval_valid.py").is_file(), ROOT
GOLD_VALID = ROOT / "data/datasets/ncbi_disease/valid"
GOLD_TRAIN = ROOT / "data/datasets/ncbi_disease/train"
SIZE_NOISE = ROOT / "reproduction/results/size_noise"
LOOPS = ROOT / "outputs/ncbi_disease"

# label -> (prediction dir, metrics label, guideline source loop or None, guideline note)
RUNS = {
    "original": ("outputs/ncbi_disease/20260802_gpt54-high_valid-G", "ncbi-g-gpt54", None, "original guideline"),
    "R4": ("outputs/ncbi_disease/20260802_gpt54-high_valid-M", "ncbi-m-gpt54", "20260802_gpt54-high_moderation", "top-1 dev10 final (R4)"),
    "R4_rerun": ("outputs/ncbi_disease/20260824_gpt54-high_valid-published-rerun", "ncbi-valid-published-0824", "20260802_gpt54-high_moderation", "same R4 guideline, second pass (per LOG; input identity with the first batch marked unverified)"),
    "topk4": ("outputs/20261007_ncbi_gpt54-high_valid-topk4", "ncbi-valid-topk4-gpt54", "20260901_gpt54-high_topk4_dev10", "top-4 dev10 final"),
    "dev20": ("outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev20", "ncbi-m-dev20", "20260813_gpt54-high_moderation-withTP_dev20", "top-1 dev20 final"),
    "dev30": ("outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev30", "ncbi-m-dev30", "20260812_gpt54-high_moderation-withTP_dev30", "top-1 dev30 final"),
    "noTP": ("outputs/ncbi_disease/20260824_gpt54-high_valid-noTP_run2", "ncbi-valid-noTP-0824", "20260806_gpt54-high_moderation-noTP_run2", "no-verified-example dev10 final"),
    "abstraction": ("outputs/ncbi_disease/20260824_gpt54-high_valid-abstraction_run1", "ncbi-valid-abstraction-0824", "20260814_gpt54-high_moderation-abstraction_run1", "abstraction dev10 final"),
}
SD_, DC_ = "SpecificDisease", "DiseaseClass"
TARGETS = {"human agreement 0.875": 0.875, "BioBERT 0.8971": 0.8971, "NEEDLE 0.9228": 0.9228}
PASS_JPY = (5539, 8837)  # one 100-document validation pass, plan_v2_cost_output.txt
OUT = []
RES = {}


def say(*parts):
    line = " ".join(str(p) for p in parts)
    OUT.append(line)
    print(line)


def h12(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


# ------------------------------------------------------------------ copied helpers (offline_direction_checks.py)
def load_dir(d):
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(d).glob("*.json"))}


def ents(doc):
    return [(d["span"]["begin"], d["span"]["end"], d["obj"]) for d in doc["denotations"]]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return round(2 * p * r / (p + r), 4) if p + r else 0.0


def prf_raw(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def score(gold_by_doc, pred_by_doc, typed=True):
    tp = fp = fn = 0
    for name, g in gold_by_doc.items():
        p = pred_by_doc.get(name, [])
        key = (lambda e: e) if typed else (lambda e: e[:2])
        gc, pc = Counter(map(key, g)), Counter(map(key, p))
        c = sum((gc & pc).values())
        tp += c
        fp += sum(pc.values()) - c
        fn += sum(gc.values()) - c
    return {"f1": prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn}


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def classify_preds(gold, pred, typed=True):
    """Per document: label each predicted entity TP, FIX (overlaps an unmatched gold entity) or DEL.
    typed=False: span-only (single type) version of the same rule."""
    key = (lambda e: e) if typed else (lambda e: e[:2])
    g_left = Counter(map(key, gold))
    status = []
    for e in pred:
        if g_left[key(e)] > 0:
            g_left[key(e)] -= 1
            status.append("TP")
        else:
            status.append(None)
    unmatched = [g for g, c in g_left.items() for _ in range(c)]
    for i, e in enumerate(pred):
        if status[i] is None:
            hit = next((g for g in unmatched if overlaps(g, e)), None)
            if hit is not None:
                unmatched.remove(hit)
                status[i] = "FIX"
            else:
                status[i] = "DEL"
    return list(zip(pred, status)), len(unmatched)


def per_doc_counts(pred, docs_sorted, gold):
    rows = []
    for n in docs_sorted:
        gc, pc = Counter(gold[n]), Counter(pred[n])
        c = sum((gc & pc).values())
        rows.append((c, sum(pc.values()) - c, sum(gc.values()) - c))
    return rows


def boot(pa, pb, docs_sorted, gold, reps=10000, seed=42):
    A, B = per_doc_counts(pa, docs_sorted, gold), per_doc_counts(pb, docs_sorted, gold)
    rng = random.Random(seed)
    n = len(A)
    diffs = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        fa_ = prf(*[sum(A[i][j] for i in idx) for j in range(3)])
        fb_ = prf(*[sum(B[i][j] for i in idx) for j in range(3)])
        diffs.append(fa_ - fb_)
    diffs.sort()
    point = prf(*[sum(r[j] for r in A) for j in range(3)]) - prf(*[sum(r[j] for r in B) for j in range(3)])
    return {"diff": round(point, 4), "ci95": [round(diffs[int(0.025 * reps)], 4), round(diffs[int(0.975 * reps)], 4)],
            "p_gt0": round(sum(1 for d in diffs if d > 0) / reps, 4)}


def boot_single(pa, docs_sorted, gold, reps=10000, seed=42):
    A = per_doc_counts(pa, docs_sorted, gold)
    rng = random.Random(seed)
    n = len(A)
    vals = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        vals.append(prf(*[sum(A[i][j] for i in idx) for j in range(3)]))
    vals.sort()
    return {"f1": prf(*[sum(r[j] for r in A) for j in range(3)]),
            "ci95": [vals[int(0.025 * reps)], vals[int(0.975 * reps)]]}


# ------------------------------------------------------------------ statistics helpers (no scipy available)
def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(q):
    lo, hi = -12.0, 12.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c
        c = c if abs(c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c
        c = c if abs(c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1) < 1e-14:
            break
    return h


def betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    p = 0.5 * betai(df / 2, 0.5, x)
    return 1 - p if t > 0 else p


def t_ppf(q, df):
    lo, hi = -200.0, 200.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_power(delta_over_se, df, alpha):
    """Exact power of a two-sided pooled two-sample t test: integrate the normal over the chi-square of the SD."""
    tc = t_ppf(1 - alpha / 2, df)
    vmax = df + 40 * math.sqrt(2 * df) + 60
    steps = 6000
    hstep = vmax / steps
    tot = 0.0
    for i in range(steps + 1):
        v = i * hstep
        if v == 0:
            f = 0.0
        else:
            f = math.exp((df / 2 - 1) * math.log(v) - v / 2 - (df / 2) * math.log(2) - math.lgamma(df / 2))
        s = math.sqrt(v / df)
        g = norm_cdf(-tc * s + delta_over_se) + norm_cdf(-tc * s - delta_over_se)
        w = 1 if i in (0, steps) else (4 if i % 2 else 2)
        tot += w * f * g
    return tot * hstep / 3


def mde(sd, n1, n2, alpha=0.05, power=0.8):
    se = sd * math.sqrt(1 / n1 + 1 / n2)
    normal = (norm_ppf(1 - alpha / 2) + norm_ppf(power)) * se
    df = n1 + n2 - 2
    lo, hi = 0.0, 30.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if t_power(mid, df, alpha) < power:
            lo = mid
        else:
            hi = mid
    return round(normal, 4), round(hi * se, 4)


# ------------------------------------------------------------------ load and verify
valid_docs = load_dir(GOLD_VALID)
train_docs = load_dir(GOLD_TRAIN)
DOCS = sorted(valid_docs)
gold_valid = {n: ents(d) for n, d in valid_docs.items()}
total_gold = sum(map(len, gold_valid.values()))
runs = {}
say("== 0  inputs, scorer check, guideline identity")
for label, (rel, mlabel, loop, note) in RUNS.items():
    docs = load_dir(ROOT / rel)
    assert set(docs) == set(valid_docs), label
    runs[label] = {n: ents(d) for n, d in docs.items()}
    s = score(gold_valid, runs[label])
    m = json.loads((ROOT / "reproduction/results" / mlabel / "metrics.json").read_text(encoding="utf-8"))
    saved = m["strict_match"]["pubannotation"]
    assert (s["tp"], s["fp"], s["fn"]) == (saved["true_positives"], saved["false_positives"], saved["false_negatives"]), label
    s1 = score(gold_valid, runs[label], typed=False)
    ghash = "e6232d944d68 (original)" if loop is None else h12(json.loads(
        (LOOPS / loop / "final/iterative_refinement_run.json").read_text(encoding="utf-8"))["final_guidelines"])
    RES.setdefault("runs", {})[label] = {"strict": s, "single_type": s1, "guideline_hash": ghash, "note": note,
                                         "pred_dir": rel, "metrics": mlabel}
    say(f"  {label:12s} strict F1 {s['f1']:.4f} (TP {s['tp']} FP {s['fp']} FN {s['fn']}; matches {mlabel}/metrics.json)  "
        f"single-type F1 {s1['f1']:.4f}  guideline {ghash}  [{note}]")
f1s8 = [RES["runs"][k]["strict"]["f1"] for k in RUNS]
sd8 = statistics.stdev(f1s8)
say(f"  gold mentions {total_gold}; 8 strict F1 values mean {statistics.mean(f1s8):.4f}, sample SD {sd8:.4f}")
labels = list(RUNS)
distinct = [l for l in labels if l != "R4_rerun"]
say("  distinct guidelines among the 8 runs: 7 (R4 and R4_rerun share one guideline file; all other hashes differ)")
hashes = Counter(RES["runs"][k]["guideline_hash"] for k in labels)
assert sum(1 for v in hashes.values() if v > 1) == 1 and hashes[RES["runs"]["R4"]["guideline_hash"]] == 2
loop_rows = {}
for loop in ["20260802_gpt54-high_moderation", "20260902_gpt54-high_topk1_run1", "20260902_gpt54-high_topk1_run2",
             "20260902_gpt54-high_topk1_run3", "20260901_gpt54-high_topk4_dev10", "20260902_gpt54-high_topk4_run1",
             "20260902_gpt54-high_topk4_run2", "20260902_gpt54-high_topk4_run3", "20260806_gpt54-high_moderation-noTP_run2",
             "20260806_gpt54-high_moderation-noTP_run4", "20260806_gpt54-high_moderation-noTP_run5",
             "20260814_gpt54-high_moderation-abstraction_run1", "20260814_gpt54-high_moderation-abstraction_run2"]:
    d = json.loads((LOOPS / loop / "final/iterative_refinement_run.json").read_text(encoding="utf-8"))
    rounds = []
    for it in d["iterations"]:
        before = it["summary_before"]["overall_f1"]
        cand = (it.get("summary_candidate") or it["summary_after"])["overall_f1"]
        rounds.append({"round": it["iteration"], "before": round(before, 4),
                       "candidate": round(cand, 4) if (it.get("summary_candidate") or it["improved"]) else None,
                       "kept": bool(it["improved"])})
    loop_rows[loop] = {"init_hash": h12(d["initial_guidelines"]), "final_hash": h12(d["final_guidelines"]),
                       "dev_initial": round(d["initial_summary"]["overall_f1"], 4),
                       "dev_final": round(d["final_summary"]["overall_f1"], 4), "rounds": rounds,
                       "stop": d.get("stop_reason")}
    say(f"  loop {loop:52s} init {loop_rows[loop]['init_hash']} final {loop_rows[loop]['final_hash']}  "
        f"dev F1 (loop set scoring) {loop_rows[loop]['dev_initial']} -> {loop_rows[loop]['dev_final']}")
RES["loops"] = loop_rows

# ------------------------------------------------------------------ S4 subtype proxy
say("\n== S4  same-span S/D confusions of top-4 and what the original-guideline run did on the same span")


def sd_confusions(pred_by_doc):
    out = []
    for n in DOCS:
        g_spans = {(b, e): t for b, e, t in gold_valid[n]}
        for b, e, t in pred_by_doc[n]:
            gt = g_spans.get((b, e))
            if gt and gt != t and {gt, t} == {SD_, DC_}:
                out.append((n, b, e, gt, t))
    return out


conf4 = sd_confusions(runs["topk4"])
others = [l for l in labels if l != "topk4"]
cats = Counter()
rows = []
for n, b, e, gt, t in conf4:
    orig_types = [tt for bb, ee, tt in runs["original"][n] if (bb, ee) == (b, e)]
    if gt in orig_types:
        c = "original has gold subtype on the same span"
    elif t in orig_types:
        c = "original has the same wrong subtype"
    elif orig_types:
        c = "original has another subtype on the same span"
    else:
        c = "original has no prediction with this exact span"
    cats[c] += 1
    n_right = sum(1 for lab in others if (b, e, gt) in set(runs[lab][n]))
    rows.append({"doc": n, "text": valid_docs[n]["text"][b:e], "gold": gt, "topk4": t, "original": orig_types,
                 "category": c, "other_runs_with_gold_subtype": n_right})
base = RES["runs"]["topk4"]["strict"]
k_orig = cats["original has gold subtype on the same span"]
f1_k = prf(base["tp"] + k_orig, base["fp"] - k_orig, base["fn"] - k_orig)
f1_all = prf(base["tp"] + len(conf4), base["fp"] - len(conf4), base["fn"] - len(conf4))
say(f"top-4 same-span S/D confusions: {len(conf4)}; categories: {dict(cats)}")
say(f"F1 if only the {k_orig} confusions the original run types correctly were fixed: {f1_k:.4f} (+{f1_k - base['f1']:.4f}); "
    f"if all {len(conf4)} were fixed: {f1_all:.4f} (+{f1_all - base['f1']:.4f}); all-label-mismatch ceiling from "
    f"error_breakdown_output.txt: 0.8750 (+0.0727)")
dist = Counter(r["other_runs_with_gold_subtype"] for r in rows)
say("number of the 7 other runs that give the gold subtype on the same span, per confusion:", dict(sorted(dist.items())))
for r in rows:
    say(f"   {r['text'][:45]:45s} gold {r['gold'][:4]} top4 {r['topk4'][:4]} original {[x[:4] for x in r['original']]} "
        f"other runs right {r['other_runs_with_gold_subtype']}/7")

# net projection: replace top-4's S/D type with the original run's S/D type on the same span (fixes and breaks)
fixes = breaks = changed = 0
newpred = {}
for n in DOCS:
    g = set(gold_valid[n])
    o_map = defaultdict(set)
    for bb, ee, tt in runs["original"][n]:
        if tt in (SD_, DC_):
            o_map[(bb, ee)].add(tt)
    out = []
    for b, e, t in runs["topk4"][n]:
        nt = t
        if t in (SD_, DC_) and len(o_map.get((b, e), ())) == 1:
            ot = next(iter(o_map[(b, e)]))
            if ot != t:
                nt = ot
                changed += 1
                if (b, e, nt) in g and (b, e, t) not in g:
                    fixes += 1
                elif (b, e, t) in g and (b, e, nt) not in g:
                    breaks += 1
        out.append((b, e, nt))
    newpred[n] = out
s_proxyA = score(gold_valid, newpred)
bs_proxyA = boot(newpred, runs["topk4"], DOCS, gold_valid)
say(f"projection 'variant A types like the original run' (top-4 spans, S/D type copied from the original run where it "
    f"has the same span as S or D): {changed} changed, {fixes} fixes, {breaks} breaks; strict F1 {s_proxyA['f1']:.4f} "
    f"(base {base['f1']:.4f}); bootstrap vs top-4 {bs_proxyA}")

# subtype vote across the 8 runs (exploratory, run set not fixed in advance)
fixes_v = breaks_v = changed_v = 0
newpred_v = {}
for n in DOCS:
    g = set(gold_valid[n])
    out = []
    for b, e, t in runs["topk4"][n]:
        nt = t
        if t in (SD_, DC_):
            c = Counter(tt for lab in labels for bb, ee, tt in set(runs[lab][n]) if (bb, ee) == (b, e) and tt in (SD_, DC_))
            top = c.most_common()
            if top and (len(top) == 1 or top[0][1] > top[1][1]) and top[0][0] != t:
                nt = top[0][0]
                changed_v += 1
                if (b, e, nt) in g:
                    fixes_v += 1
                elif (b, e, t) in g:
                    breaks_v += 1
        out.append((b, e, nt))
    newpred_v[n] = out
s_vote_sd = score(gold_valid, newpred_v)
bs_vote_sd = boot(newpred_v, runs["topk4"], DOCS, gold_valid)
say(f"exploratory: S/D type of top-4 replaced by the majority S/D type of the 8 runs on the same span: {changed_v} changed, "
    f"{fixes_v} fixes, {breaks_v} breaks; strict F1 {s_vote_sd['f1']:.4f}; bootstrap vs top-4 {bs_vote_sd}")
# detectability of an S4 result that fixes exactly the 19 original-correct confusions and breaks nothing
fix_set = {(r["doc"], c4[1], c4[2]) for r, c4 in zip(rows, conf4) if r["category"] == "original has gold subtype on the same span"}
pred_fixonly = {n: [(b, e, ({t2 for b2, e2, t2 in gold_valid[n] if (b2, e2) == (b, e)} - {t}).pop()
                     if (n, b, e) in fix_set else t) for b, e, t in runs["topk4"][n]] for n in DOCS}
s_fixonly = score(gold_valid, pred_fixonly)
bs_fixonly = boot(pred_fixonly, runs["topk4"], DOCS, gold_valid)
half_k = len(conf4) // 2
f1_half = prf(base["tp"] + half_k, base["fp"] - half_k, base["fn"] - half_k)
say(f"check: fixing exactly those {k_orig} with no breaks gives strict F1 {s_fixonly['f1']:.4f}; bootstrap vs top-4 {bs_fixonly}")
say(f"gate-B-sized effect on valid (S/D confusions halved, {half_k} fixes, no breaks): strict F1 {f1_half:.4f} (+{f1_half - base['f1']:.4f})")
RES["S4_extra"] = {"fix_only_19": {"strict": s_fixonly, "boot": bs_fixonly}, "halved": {"fixes": half_k, "f1": f1_half}}
RES["S4"] = {"topk4_SD_confusions": len(conf4), "categories": dict(cats), "f1_fix_original_correct": f1_k,
             "f1_fix_all_SD": f1_all, "other_runs_right_hist": dict(dist), "rows": rows,
             "proxyA": {"changed": changed, "fixes": fixes, "breaks": breaks, "strict": s_proxyA, "boot": bs_proxyA},
             "subtype_vote8": {"changed": changed_v, "fixes": fixes_v, "breaks": breaks_v, "strict": s_vote_sd,
                               "boot": bs_vote_sd}}

# dev30 pilot noise: S/D confusions per saved repeat of the original guideline
dev_repeats = [json.loads((SIZE_NOISE / f"repeat_0{i}.json").read_text(encoding="utf-8")) for i in range(1, 6)]
dev30_ids = sorted(dev_repeats[0])
gold_dev = {n: ents(train_docs[n]) for n in dev30_ids}
counts = []
for r in dev_repeats:
    c = 0
    tot_sd = 0
    for n in dev30_ids:
        g_spans = {(b, e): t for b, e, t in gold_dev[n]}
        for x in r[n]:
            gt = g_spans.get((x["start"], x["end"]))
            if gt and gt != x["entity"] and {gt, x["entity"]} == {SD_, DC_}:
                c += 1
        tot_sd += sum(1 for _, _, t in gold_dev[n] if t in (SD_, DC_))
    counts.append(c)
pairs = [(a, b) for i, a in enumerate(counts) for j, b in enumerate(counts) if i != j]
halved = sum(1 for a, b in pairs if b <= a / 2)
say(f"dev30 (size_noise, original guideline, 5 repeats): same-span S/D confusions per repeat {counts}; gold S+D mentions {tot_sd}; "
    f"ordered repeat pairs where the second has at most half the first: {halved}/{len(pairs)}")
RES["S4"]["dev30_SD_confusions_per_repeat"] = counts
RES["S4"]["dev30_gold_SD_mentions"] = tot_sd
RES["S4"]["dev30_halving_by_chance_pairs"] = [halved, len(pairs)]

# ------------------------------------------------------------------ S3 footprint
say("\n== S3  validation footprint of the strings named by gold-contradicting rules")
EXCLUSION_HINT = re.compile(r"do \*\*not\*\*|do not|not annotate|not annotated|not treated? as|are \*\*not\*\*", re.I)
QUOTE = re.compile(r"[“\"]([^”\"]{3,})[”\"]")
g4 = json.loads((LOOPS / "20260901_gpt54-high_topk4_dev10/final/iterative_refinement_run.json").read_text(encoding="utf-8"))["final_guidelines"]
excl_quotes = []
for line in g4.splitlines():
    if EXCLUSION_HINT.search(line):
        excl_quotes += QUOTE.findall(line)
excl_quotes = sorted(set(q.strip() for q in excl_quotes))


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def footprint(q):
    pat = re.compile(r"(?<![a-z0-9])" + re.escape(norm(q)) + r"(?![a-z0-9])")
    texts = sum(1 for d in valid_docs.values() if pat.search(norm(d["text"])))
    g_exact = g_contain = p_exact = 0
    for n, d in valid_docs.items():
        for b, e, t in gold_valid[n]:
            s = norm(d["text"][b:e])
            g_exact += s == norm(q)
            g_contain += bool(pat.search(s))
        for b, e, t in runs["topk4"][n]:
            p_exact += norm(d["text"][b:e]) == norm(q)
    return {"valid_texts": texts, "gold_exact": g_exact, "gold_containing": g_contain, "topk4_pred_exact": p_exact}


flagged = ["abnormal retinal vascular development", "deficient activity of fatty aldehyde dehydrogenase"]
probes = flagged + ["fatty aldehyde dehydrogenase", "FALDH", "retinal vascular", "deficiency of norrin", "norrin",
                    "autosomal recessive disorder", "Sjogren-Larsson syndrome"]
fp_rows = {q: footprint(q) for q in probes}
for q, r in fp_rows.items():
    say(f"  {q[:55]:55s} {r}")
allx = {q: footprint(q) for q in excl_quotes}
hit = {q: r for q, r in allx.items() if r["valid_texts"] or r["gold_containing"]}
say(f"quoted strings in exclusion lines of the top-4 final guideline: {len(excl_quotes)}; with any valid100 occurrence: "
    f"{len(hit)}; gold entities whose text equals one of them: {sum(r['gold_exact'] for r in allx.values())}")
for q, r in sorted(hit.items(), key=lambda x: -x[1]["valid_texts"]):
    say(f"   {q[:60]:60s} {r}")
g_flag = sum(fp_rows[q]["gold_containing"] for q in flagged)
f_up = prf(base["tp"] + g_flag, base["fp"], base["fn"] - g_flag)
say(f"largest direct F1 change on valid100 from the two flagged rules: gold entities containing their strings {g_flag}; "
    f"strict F1 {base['f1']:.4f} -> at most {f_up:.4f}")
RES["S3"] = {"probes": fp_rows, "exclusion_quotes": len(excl_quotes), "exclusion_quotes_with_valid_hits": hit,
             "flagged_gold_entities": g_flag, "max_direct_f1": f_up}

# ------------------------------------------------------------------ S2a / S5 detectability
say("\n== S2a / S5  detectable differences between loop means (alpha two-sided, power 0.8)")
sd_pair = abs(RES["runs"]["R4"]["strict"]["f1"] - RES["runs"]["R4_rerun"]["strict"]["f1"]) / math.sqrt(2)
RES["power"] = {"sd8": round(sd8, 4), "sd_same_guideline_pair": round(sd_pair, 4), "rows": []}
for sd in (round(sd8, 4), round(sd_pair, 4)):
    for n1, n2 in ((4, 4), (3, 4), (3, 3), (2, 2)):
        for alpha in (0.05, 0.0125):
            nm, tm = mde(sd, n1, n2, alpha)
            RES["power"]["rows"].append({"sd": sd, "n1": n1, "n2": n2, "alpha": alpha, "normal": nm, "t_exact": tm})
            say(f"  SD {sd:.4f}  loops {n1} vs {n2}  alpha {alpha:<6}  normal approx {nm:.4f}  exact t test {tm:.4f}")
known_top1 = [(RES["runs"]["R4"]["strict"]["f1"] + RES["runs"]["R4_rerun"]["strict"]["f1"]) / 2,
              RES["runs"]["original"]["strict"]["f1"], RES["runs"]["original"]["strict"]["f1"]]
say(f"top-1 loops with valid scores: R4 (two-pass mean {known_top1[0]:.4f}), runs 1 and 2 ended at the original guideline "
    f"(hash {loop_rows['20260902_gpt54-high_topk1_run1']['final_hash']}, {loop_rows['20260902_gpt54-high_topk1_run2']['final_hash']}; "
    f"valid {known_top1[1]:.4f}); SD of these 3 loop values {statistics.stdev(known_top1):.4f}")
lo8, hi8, mean8 = min(f1s8), max(f1s8), statistics.mean(f1s8)
scen = []
for name, x4, x1 in (("unscored finals score like the 8-run mean", mean8, mean8),
                     ("unscored top-4 finals score like top-4 (0.8023), top-1 run 3 like the 8-run mean", 0.8023, mean8),
                     ("unscored top-4 finals at the 8-run maximum, top-1 run 3 at the 8-run minimum", hi8, lo8),
                     ("unscored top-4 finals at the 8-run minimum, top-1 run 3 at the 8-run maximum", lo8, hi8)):
    m4 = (0.8023 + 3 * x4) / 4
    m1 = (sum(known_top1) + x1) / 4
    scen.append({"scenario": name, "top4_mean": round(m4, 4), "top1_mean": round(m1, 4), "diff": round(m4 - m1, 4)})
    say(f"  projection: {name}: top-4 mean {m4:.4f}, top-1 mean {m1:.4f}, difference {m4 - m1:+.4f}")
need = []
for x1 in (lo8, mean8, hi8):
    for target in (0.0244, 0.0292):
        m1 = (sum(known_top1) + x1) / 4
        x4 = (4 * (m1 + target) - 0.8023) / 3
        need.append({"top1_run3": x1, "target_diff": target, "needed_mean_of_3_unscored_top4": round(x4, 4)})
        say(f"  needed mean valid F1 of the 3 unscored top-4 finals for a difference of {target} if top-1 run 3 scores {x1:.4f}: {x4:.4f}")
RES["S2a"] = {"known_top1_loops": known_top1, "scenarios": scen, "needed": need}

# S5: rounds kept within dev10 noise
say("\n== S5  dev10 round decisions (loop set scoring) against dev10 annotation noise")
sn = json.loads((SIZE_NOISE / "summary.json").read_text(encoding="utf-8"))
say("size_noise summary keys:", list(sn)[:10])
sd_dev10 = 0.01502
band = 1.96 * sd_dev10 * math.sqrt(2)
kept = [(l, r["round"], round(r["candidate"] - r["before"], 4)) for l, v in loop_rows.items() for r in v["rounds"]
        if r["kept"] and r["candidate"] is not None]
rej = [(l, r["round"]) for l, v in loop_rows.items() for r in v["rounds"] if not r["kept"]]
inside = [k for k in kept if k[2] < band]
say(f"dev10 SD of one annotation 0.01502 (LOG, size_noise); SD of a difference of two annotations {sd_dev10 * math.sqrt(2):.4f}; "
    f"1.96 x that = {band:.4f}")
say(f"kept rounds in the 13 loops: {len(kept)}; kept with a dev gain below {band:.4f}: {len(inside)}; rejected rounds: {len(rej)}")
for k in kept:
    say(f"   kept {k[0]:52s} round {k[1]} gain {k[2]:+.4f}{'  (inside noise band)' if k[2] < band else ''}")
init_vals = [v["dev_initial"] for l, v in loop_rows.items() if v["init_hash"] == "e6232d944d68"]
say(f"dev10 initial F1 of the original guideline across the 13 loops (repeated annotations unless cached): {init_vals}; "
    f"SD {statistics.stdev(init_vals):.4f}; without the lowest value ({min(init_vals)}) SD "
    f"{statistics.stdev(sorted(init_vals)[1:]):.4f}")
reps10 = [0.8028, 0.8085, 0.8252, 0.7832, 0.8028]  # loop set scoring of the 5 dev10 repeats (offline_direction_checks_output.txt)
pairs10 = [(a, b) for i, a in enumerate(reps10) for j, b in enumerate(reps10) if i != j]
say(f"same guideline annotated twice on dev10 (5 saved repeats, 20 ordered pairs): second strictly higher in "
    f"{sum(1 for a, b in pairs10 if b > a)}/20 pairs, so a no-change candidate would pass 'F1 rises' about that often")
RES["S5"] = {"kept": kept, "inside_band": inside, "band": round(band, 4), "rejected": len(rej), "dev10_initial_values": init_vals,
             "no_change_pass_rate_pairs": [sum(1 for a, b in pairs10 if b > a), 20]}

# ------------------------------------------------------------------ vote vs number of runs
say("\n== V  vote over saved runs: F1 against the number of runs voted (all subsets)")


def vote(sub, k):
    out = {}
    for n in DOCS:
        c = Counter()
        for lab in sub:
            for e in set(runs[lab][n]):
                c[e] += 1
        out[n] = [e for e, v in c.items() if v >= k]
    return out


RES["vote"] = {}
for m in range(1, 9):
    rowsm = []
    for sub in itertools.combinations(labels, m):
        r = {"runs": sub}
        for k in range(1, m + 1):
            r[k] = score(gold_valid, vote(sub, k))["f1"]
        rowsm.append(r)
    half = math.ceil(m / 2)
    strict_major = m // 2 + 1
    best = [max(r[k] for k in range(1, m + 1)) for r in rowsm]
    a = [r[half] for r in rowsm]
    b_ = [r[strict_major] for r in rowsm] if strict_major <= m else a
    dist_only = [r for r in rowsm if not ("R4" in r["runs"] and "R4_rerun" in r["runs"])]
    a_d = [r[half] for r in dist_only]
    RES["vote"][m] = {"subsets": len(rowsm), "at_least_half": [round(statistics.mean(a), 4), min(a), max(a)],
                      "strict_majority": [round(statistics.mean(b_), 4), min(b_), max(b_)],
                      "best_k_posthoc": [round(statistics.mean(best), 4), min(best), max(best)],
                      "distinct_guidelines_only_at_least_half": [round(statistics.mean(a_d), 4), min(a_d), max(a_d), len(a_d)]
                      if a_d else None}
    say(f"  m={m} ({len(rowsm)} subsets): keep if >= {half} runs: mean {statistics.mean(a):.4f} [min {min(a):.4f}, max {max(a):.4f}]"
        f" | strict majority (>= {strict_major}): mean {statistics.mean(b_):.4f} [{min(b_):.4f}, {max(b_):.4f}]"
        f" | best k chosen after the fact: mean {statistics.mean(best):.4f} [{min(best):.4f}, {max(best):.4f}]"
        + (f" | distinct-guideline subsets only, >= {half}: mean {statistics.mean(a_d):.4f} (n={len(a_d)})" if a_d else ""))
same_union = vote(["R4", "R4_rerun"], 1)
same_inter = vote(["R4", "R4_rerun"], 2)
su, si = score(gold_valid, same_union), score(gold_valid, same_inter)
say(f"same guideline, two passes (R4 + R4_rerun): union F1 {su['f1']:.4f} (TP {su['tp']} FP {su['fp']} FN {su['fn']}); "
    f"intersection F1 {si['f1']:.4f} (TP {si['tp']} FP {si['fp']} FN {si['fn']}); single passes 0.7878 / 0.7789")
v7 = vote(distinct, 4)
s7 = score(gold_valid, v7)
comps = {"union(R4,R4_rerun) - R4": (same_union, runs["R4"]),
         "union(R4,R4_rerun) - R4_rerun": (same_union, runs["R4_rerun"]),
         "intersection(R4,R4_rerun) - R4": (same_inter, runs["R4"]),
         "intersection(R4,R4_rerun) - R4_rerun": (same_inter, runs["R4_rerun"]),
         "vote>=4 of 7 distinct guidelines - topk4": (v7, runs["topk4"]),
         "vote>=4 of 7 distinct guidelines - original": (v7, runs["original"])}
RES["vote"]["same_guideline"] = {"union": su, "intersection": si}
RES["vote"]["distinct7_k4"] = s7
RES["vote"]["boot"] = {k: boot(*v, DOCS, gold_valid) for k, v in comps.items()}
say(f"vote >= 4 of the 7 distinct-guideline runs: F1 {s7['f1']:.4f}")
for k, v in RES["vote"]["boot"].items():
    say(f"  bootstrap {k:45s} diff {v['diff']:+.4f} 95% CI [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] P(diff>0) {v['p_gt0']:.3f}")

# ------------------------------------------------------------------ review-effort curve: share needed to reach targets
say("\n== R  review-effort curve: smallest share of predicted entities to check to reach each target")


def curve_full(base_label, conf_labels, typed=True, seeds=20):
    items = []
    gold_left_total = 0
    for n in DOCS:
        cls, missed = classify_preds(gold_valid[n], runs[base_label][n], typed=typed)
        gold_left_total += missed
        for e, s in cls:
            conf = sum(1 for lab in conf_labels if e in set(runs[lab][n]))
            items.append((conf, s))
    n_items = len(items)
    tp0 = sum(1 for _, s in items if s == "TP")
    wrong = n_items - tp0

    def f1_series(order):
        fix = nontp = 0
        out = [prf_raw(tp0, wrong, total_gold - tp0)]
        for _, s in order:
            if s == "FIX":
                fix += 1
            if s != "TP":
                nontp += 1
            tp = tp0 + fix
            out.append(prf_raw(tp, wrong - nontp, total_gold - tp))
        return out

    agree = []
    for seed in range(seeds):
        rng = random.Random(seed)
        agree.append(f1_series(sorted(items, key=lambda x: (x[0], rng.random()))))
    rnd = []
    for seed in range(seeds):
        rng = random.Random(1000 + seed)
        sh = items[:]
        rng.shuffle(sh)
        rnd.append(f1_series(sh))
    oracle = f1_series(sorted(items, key=lambda x: x[1] == "TP"))
    mean_a = [sum(s[k] for s in agree) / seeds for k in range(n_items + 1)]
    mean_r = [sum(s[k] for s in rnd) / seeds for k in range(n_items + 1)]
    return {"n": n_items, "wrong": wrong, "tp0": tp0, "gold_never_proposed": gold_left_total,
            "agree": mean_a, "agree_seeds": agree, "random": mean_r, "oracle": oracle}


def first_k(series, target):
    for k, v in enumerate(series):
        if v >= target - 1e-12:
            return k
    return None


def report_curve(name, c, check_known=None):
    n = c["n"]
    say(f"-- {name}: {n} predicted entities, {c['wrong']} wrong, start F1 {c['agree'][0]:.4f}, ceiling after checking all "
        f"{c['oracle'][-1]:.4f}; gold entities with no overlapping prediction {c['gold_never_proposed']}")
    if check_known:
        for frac, val in check_known.items():
            got = round(c["agree"][round(frac * n)], 4)
            assert abs(got - val) < 1e-4, (name, frac, got, val)
        say("   reproduces offline_direction_checks_output.txt section C at", list(check_known))
    out = {"n": n, "wrong": c["wrong"], "start": round(c["agree"][0], 4), "ceiling": round(c["oracle"][-1], 4), "targets": {},
           "fractions": {}}
    for frac in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5):
        k = round(frac * n)
        out["fractions"][frac] = {"agree": round(c["agree"][k], 4), "random": round(c["random"][k], 4),
                                  "oracle": round(c["oracle"][k], 4)}
    say("   fixed shares (agreement / random / wrong-first bound): " + "; ".join(
        f"{int(f * 100)}% {v['agree']:.4f}/{v['random']:.4f}/{v['oracle']:.4f}" for f, v in out["fractions"].items()))
    for tname, t in TARGETS.items():
        ka = first_k(c["agree"], t)
        kr = first_k(c["random"], t)
        ko = first_k(c["oracle"], t)
        seeds_k = [first_k(s, t) for s in c["agree_seeds"]]
        row = {"agree_k": ka, "agree_share": round(ka / n, 4) if ka is not None else None,
               "agree_seed_range": [min(seeds_k), max(seeds_k)] if None not in seeds_k else None,
               "random_k": kr, "random_share": round(kr / n, 4) if kr is not None else None,
               "oracle_k": ko, "oracle_share": round(ko / n, 4) if ko is not None else None}
        if ka is not None:
            row["random_at_agree_k"] = round(c["random"][ka], 4)
            row["oracle_at_agree_k"] = round(c["oracle"][ka], 4)
        out["targets"][tname] = row
        if ka is None:
            say(f"   {tname}: not reachable by checking predicted entities (ceiling {c['oracle'][-1]:.4f})")
        else:
            say(f"   {tname}: agreement order {ka} entities ({ka / n:.1%}; seed range {row['agree_seed_range']}) | "
                f"random order {kr} ({(kr / n) if kr is not None else float('nan'):.1%}) | wrong-first bound {ko} ({ko / n:.1%}) | "
                f"at {ka / n:.1%} checked: random {row['random_at_agree_k']:.4f}, bound {row['oracle_at_agree_k']:.4f}")
    return out


RES["review"] = {}
known = {0.1: 0.8432, 0.2: 0.8868, 0.3: 0.9109}
c = curve_full("topk4", others, typed=True)
RES["review"]["strict topk4 | 7 other runs"] = report_curve("strict four-subtype, base top-4, agreement from the 7 other runs", c, known)
c = curve_full("topk4", others, typed=False)
RES["review"]["single-type topk4 | 7 other runs"] = report_curve("single type (exact span), base top-4, same typed agreement ordering", c)
c = curve_full("R4", ["R4_rerun"], typed=True)
RES["review"]["strict R4 | R4_rerun"] = report_curve("strict four-subtype, base R4, agreement from its own second pass", c,
                                                     {0.1: 0.8343, 0.2: 0.8507, 0.3: 0.8634})
c = curve_full("R4", ["R4_rerun"], typed=False)
RES["review"]["single-type R4 | R4_rerun"] = report_curve("single type (exact span), base R4, agreement from its own second pass", c)
c = curve_full("R4_rerun", ["R4"], typed=True)
RES["review"]["strict R4_rerun | R4"] = report_curve("strict four-subtype, base R4_rerun, agreement from R4 (roles swapped)", c)
# one other run of a different guideline: every single choice
single = {}
for lab in others:
    cc = curve_full("topk4", [lab], typed=True, seeds=10)
    single[lab] = {t: first_k(cc["agree"], v) for t, v in TARGETS.items()}
    single[lab]["n"] = cc["n"]
    single[lab]["at20"] = round(cc["agree"][round(0.2 * cc["n"])], 4)
RES["review"]["strict topk4 | one other run"] = single
say("-- strict, base top-4, agreement from ONE other run (each choice): entities to check for each target, and F1 at 20%")
for lab, r in single.items():
    say(f"   {lab:12s} " + "; ".join(f"{t}: {r[t]} ({r[t] / r['n']:.1%})" if r[t] is not None else f"{t}: n/a"
                                    for t in TARGETS) + f"; F1 at 20% {r['at20']:.4f}")

# consistent errors: wrong entities agreed by all 7 other runs (the part agreement routing reaches last)
cons_fix = cons_del = 0
for n in DOCS:
    cls, _ = classify_preds(gold_valid[n], runs["topk4"][n])
    for e, s in cls:
        if s != "TP" and all(e in set(runs[lab][n]) for lab in others):
            if s == "FIX":
                cons_fix += 1
            else:
                cons_del += 1
f_cons = prf(base["tp"] + cons_fix, base["fp"] - cons_fix - cons_del, base["fn"] - cons_fix)
say(f"S7 headroom: wrong top-4 entities present in all 7 other runs: {cons_fix + cons_del} ({cons_fix} fixable, {cons_del} delete); "
    f"F1 if only these were corrected: {f_cons:.4f} (+{f_cons - base['f1']:.4f})")
RES["S7"] = {"consistent_wrong": cons_fix + cons_del, "fixable": cons_fix, "delete": cons_del, "f1_if_fixed": f_cons}

# ------------------------------------------------------------------ S6 / single-run precision
say("\n== S6  precision of one 100-document score (document bootstrap, 10,000 resamples)")
RES["S6"] = {}
for lab in ("original", "topk4", "R4"):
    b1 = boot_single(runs[lab], DOCS, gold_valid)
    RES["S6"][lab] = b1
    say(f"  {lab:10s} strict F1 {b1['f1']:.4f} 95% CI [{b1['ci95'][0]:.4f}, {b1['ci95'][1]:.4f}]")

(HERE / "step_value_checks.json").write_text(json.dumps(RES, indent=1, default=str), encoding="utf-8")
(HERE / "step_value_checks_output.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
