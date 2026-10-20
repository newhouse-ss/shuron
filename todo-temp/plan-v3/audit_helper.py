"""Offline audit helper for plan v2 (no API calls, no keys, read-only on the repository).

Recomputes items in docs/RP/20261020_research_plan_v2.md that have no saved artifact or that the
S1 replacement needs:
    1  data identity: valid100 / train sizes, gold mention count, overlap between splits
    2  SD of the 8 strict valid100 F1 values and the detectable differences (with and without Holm)
    3  cancer-pattern S/D confusions (original vs top-4) with explicit regexes
    4  review curve at 1% steps: first share of checked entities reaching 0.875 (strict) and the
       one-type F1 path, for top-4 vs 7 other runs and for R4 vs its same-guideline rerun
    5  EN vs ZH plan v2: digits per line
    6  cost arithmetic per call

Run from anywhere:  python -I "<this file>"
Writes audit_helper_output.txt next to this file.
"""
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert (ROOT / "OVERVIEW.md").exists(), ROOT
OUT = []


def say(*p):
    s = " ".join(str(x) for x in p)
    OUT.append(s)
    print(s)


def load_dir(d):
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(d).glob("*.json"))}


def ents(doc):
    return [(d["span"]["begin"], d["span"]["end"], d["obj"]) for d in doc["denotations"]]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def score(gold, pred, typed=True):
    tp = fp = fn = 0
    key = (lambda e: e) if typed else (lambda e: e[:2])
    for n, g in gold.items():
        gc, pc = Counter(map(key, g)), Counter(map(key, pred.get(n, [])))
        c = sum((gc & pc).values())
        tp += c
        fp += sum(pc.values()) - c
        fn += sum(gc.values()) - c
    return prf(tp, fp, fn), tp, fp, fn


RUNS = {  # same paths as todo-temp/plan-v3/offline_direction_checks.py
    "original": "outputs/ncbi_disease/20260802_gpt54-high_valid-G",
    "R4": "outputs/ncbi_disease/20260802_gpt54-high_valid-M",
    "R4_rerun": "outputs/ncbi_disease/20260824_gpt54-high_valid-published-rerun",
    "topk4": "outputs/20261007_ncbi_gpt54-high_valid-topk4",
    "dev20": "outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev20",
    "dev30": "outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev30",
    "noTP": "outputs/ncbi_disease/20260824_gpt54-high_valid-noTP_run2",
    "abstraction": "outputs/ncbi_disease/20260824_gpt54-high_valid-abstraction_run1",
}
EXPECTED = {"original": 0.7792, "R4": 0.7878, "R4_rerun": 0.7789, "topk4": 0.8023,
            "dev20": 0.7745, "dev30": 0.8050, "noTP": 0.7716, "abstraction": 0.7844}

valid = load_dir(ROOT / "data/datasets/ncbi_disease/valid")
train = load_dir(ROOT / "data/datasets/ncbi_disease/train")
gold = {n: ents(d) for n, d in valid.items()}
runs = {}
for lab, rel in RUNS.items():
    docs = load_dir(ROOT / rel)
    assert set(docs) == set(valid), lab
    runs[lab] = {n: ents(d) for n, d in docs.items()}
    f = score(gold, runs[lab])[0]
    assert abs(round(f, 4) - EXPECTED[lab]) < 1e-4, (lab, f)

# ------------------------------------------------------------------ 1 data identity
say("== 1 data identity")
say("valid docs", len(valid), "gold mentions", sum(map(len, gold.values())), "| train docs", len(train))
vid = {d.get("sourceid", n) for n, d in valid.items()}
tid = {d.get("sourceid", n) for n, d in train.items()}
say("sourceid overlap valid & train:", len(vid & tid))
dev10 = json.loads((ROOT / "reproduction/dev_splits/ncbi_disease_dev10.json").read_text(encoding="utf-8"))
say("dev10 split seed", dev10["seed"], "docs in train:", sum(1 for x in dev10["documents"] if x in train), "of", len(dev10["documents"]))
say("first 5 valid sourceids:", sorted(vid)[:5], "| sourcedb values:", sorted({d.get("sourcedb") for d in valid.values()}))
for lab in ("original", "R4", "R4_rerun", "topk4", "dev30"):
    f1, tp, fp, fn = score(gold, runs[lab])
    f1u = score(gold, runs[lab], typed=False)
    say(f"  {lab:9s} strict {f1:.4f} P {tp/(tp+fp):.4f} R {tp/(tp+fn):.4f} TP {tp} | one-type (span only) {f1u[0]:.4f}")

# ------------------------------------------------------------------ 2 SD and detectable differences
say("\n== 2 SD of the 8 strict F1 values and detectable differences (normal approximation)")
vals = [round(score(gold, runs[l])[0], 4) for l in RUNS]
m = sum(vals) / len(vals)
sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
say("values", vals, f"mean {m:.4f} SD(ddof=1) {sd:.4f}")
Z = {0.05: 1.959964, 0.0125: 2.497705, 0.0167: 2.393980, 0.025: 2.241403}
Z80 = 0.841621
for n in (3, 4):
    for a in (0.05, 0.025, 0.0167, 0.0125):
        mult = Z[a] + Z80
        say(f"  n={n} loops per arm, two-sided alpha {a}: multiplier {mult:.2f}, detectable diff {mult * math.sqrt(2 * sd * sd / n):.4f}")
say("  (alpha 0.0125 = first Holm step for 4 primary comparisons; 0.05 = unadjusted, as in plan v2 6.3)")

# ------------------------------------------------------------------ 3 cancer patterns
say("\n== 3 cancer-pattern same-span S/D confusions (regexes stated here; report 3.2 did not save its query)")
SD_, DC_ = "SpecificDisease", "DiseaseClass"
PAT_HERED = re.compile(r"^(hereditary|sporadic)\b.*\b(cancers?|carcinomas?)$", re.I)
PAT_BARE_STRICT = re.compile(r"^(cancers?|tumou?rs?|lipomas?)$", re.I)
PAT_BARE_WIDE = re.compile(r"^(stage \w+ )?(cancers?|tumou?rs?|lipomas?)$", re.I)
for lab in RUNS:
    a = b_s = b_w = 0
    items = []
    for n, doc in valid.items():
        gs = {(x, y): t for x, y, t in gold[n]}
        for x, y, t in runs[lab][n]:
            g = gs.get((x, y))
            if not g or {g, t} != {SD_, DC_}:
                continue
            txt = doc["text"][x:y]
            if g == SD_ and t == DC_ and PAT_HERED.match(txt):
                a += 1
                items.append(f"{txt} (S->D)")
            if g == DC_ and t == SD_ and PAT_BARE_STRICT.match(txt):
                b_s += 1
            if g == DC_ and t == SD_ and PAT_BARE_WIDE.match(txt):
                b_w += 1
                items.append(f"{txt} (D->S)")
    say(f"  {lab:11s} hereditary/sporadic S->D {a}; bare D->S strict {b_s}, with 'stage X' {b_w}; "
        f"total {a + b_s} / {a + b_w}" + (f"  {sorted(items)}" if lab in ("original", "topk4") else ""))

# ------------------------------------------------------------------ 4 review curve at 1% steps
say("\n== 4 review curve at 1% steps (same method as offline_direction_checks.py curve(); 20 seeds)")


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def classify(g, p, typed):
    key = (lambda e: e) if typed else (lambda e: e[:2])
    left = Counter(map(key, g))
    st = []
    for e in p:
        if left[key(e)] > 0:
            left[key(e)] -= 1
            st.append("TP")
        else:
            st.append(None)
    unmatched = [x for x in g]
    # remove matched gold (by key) from unmatched
    used = Counter(key(e) for e, s in zip(p, st) if s == "TP")
    rest = []
    for x in unmatched:
        if used[key(x)] > 0:
            used[key(x)] -= 1
        else:
            rest.append(x)
    for i, e in enumerate(p):
        if st[i] is None:
            hit = next((x for x in rest if overlaps(x, e)), None)
            if hit is not None:
                rest.remove(hit)
                st[i] = "FIX"
            else:
                st[i] = "DEL"
    return list(zip(p, st))


def curve_fine(base, conf_from, typed, seeds=20, target=0.875):
    items = []
    for n in valid:
        for e, s in classify(gold[n], runs[base][n], typed):
            items.append((sum(1 for l in conf_from if e in set(runs[l][n])), s))
    total = sum(map(len, gold.values()))
    N = len(items)

    def f1_after(rev):
        tp = sum(1 for _, s in items if s == "TP") + sum(1 for _, s in rev if s == "FIX")
        fp = sum(1 for _, s in items if s != "TP") - sum(1 for _, s in rev if s != "TP")
        return prf(tp, fp, total - tp)

    orders_a, orders_r = [], []
    for sd_ in range(seeds):
        rng = random.Random(sd_)
        orders_a.append(sorted(items, key=lambda x: (x[0], rng.random())))
    for sd_ in range(seeds):
        rng = random.Random(1000 + sd_)
        sh = items[:]
        rng.shuffle(sh)
        orders_r.append(sh)
    oracle = sorted(items, key=lambda x: x[1] == "TP")
    rows = []
    for pct in range(0, 101):
        k = round(pct / 100 * N)
        a = sum(f1_after(o[:k]) for o in orders_a) / seeds
        r = sum(f1_after(o[:k]) for o in orders_r) / seeds
        rows.append((pct, k, a, r, f1_after(oracle[:k])))
    first = lambda col: next((row[0] for row in rows if row[col] >= target), None)
    return N, rows, first(2), first(3), first(4)


others = [l for l in RUNS if l != "topk4"]
for typed in (True, False):
    tag = "strict" if typed else "one-type (span only)"
    for base, conf in (("topk4", others), ("R4", ["R4_rerun"])):
        for target in ((0.875,) if typed else (0.875, 0.897, 0.909, 0.9228)):
            N, rows, fa, fr, fo = curve_fine(base, conf, typed, target=target)
            say(f"  {tag:20s} base {base:6s} vs {len(conf)} run(s): first share reaching {target}: "
                f"agreement {fa}% | random {fr}% | wrong-first {fo}%")
        sel = [r for r in rows if r[0] in (0, 10, 20, 30, 50, 100)]
        say("     check rows (pct, k, agreement, random, wrong-first):",
            [(r[0], r[1], round(r[2], 4), round(r[3], 4), round(r[4], 4)) for r in sel])

# ------------------------------------------------------------------ 5 EN vs ZH digits
say("\n== 5 EN vs ZH plan v2: numbers per line (line-aligned files)")
EN, ZH = ROOT / "docs/RP/20261020_research_plan_v2.md", ROOT / "docs/RP/20261020_research_plan_v2_zh.md"
if not (EN.exists() and ZH.exists()):
    # plan v2 was superseded by plan v3 and deleted on 2026-10-20; the 10/19 output of this section is in commit d86ea17
    say("skipped: plan v2 files deleted on 2026-10-20 (10/19 result in commit d86ea17)")
else:
    en, zh = EN.read_text(encoding="utf-8").splitlines(), ZH.read_text(encoding="utf-8").splitlines()
    NUM = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
    say("lines EN", len(en), "ZH", len(zh))
    diff_lines = 0
    for i in range(max(len(en), len(zh))):
        a = Counter(NUM.findall(en[i])) if i < len(en) else Counter()
        b = Counter(NUM.findall(zh[i])) if i < len(zh) else Counter()
        if a != b:
            diff_lines += 1
            say(f"  line {i + 1}: EN-only {dict(a - b)} ZH-only {dict(b - a)}")
    say("lines whose digit multisets differ:", diff_lines)
    ae = Counter(x for l in en for x in NUM.findall(l))
    az = Counter(x for l in zh for x in NUM.findall(l))
    say("whole-file EN-only:", dict(ae - az), "| ZH-only:", dict(az - ae))

# ------------------------------------------------------------------ 6 cost arithmetic
say("\n== 6 cost per call (plan_v2_cost.py constants)")
usd = lambda out: (4834 * 2.50 + out * 15.00) / 1e6
for out in (22551, 36459):
    say(f"  output {out}: USD {usd(out):.5f}  JPY {usd(out) * 158.086954:.2f}")
say("  S4 as described (2 variants x 30 dev30 calls + 200 validation calls) = 260 calls:",
    f"JPY {260 * usd(22551) * 158.086954:,.0f} to {260 * usd(36459) * 158.086954:,.0f}")

# ------------------------------------------------------------------ 7 S4 gate B baseline on dev30
say("\n== 7 S4 pilot baseline: same-span S/D confusions in the 5 saved dev30 passes (original guideline)")
SN = ROOT / "reproduction/results/size_noise"
reps = [json.loads((SN / f"repeat_0{i}.json").read_text(encoding="utf-8")) for i in range(1, 6)]
dev30_ids = sorted(reps[0])
split30 = json.loads((ROOT / "reproduction/dev_splits/ncbi_disease_dev30.json").read_text(encoding="utf-8"))["documents"]
say("size_noise doc set == dev_splits/ncbi_disease_dev30.json:", sorted(split30) == dev30_ids, "| n =", len(dev30_ids))
gdev = {n: ents(train[n]) for n in dev30_ids}
for i, r in enumerate(reps, 1):
    c = Counter()
    for n in dev30_ids:
        gs = {(x, y): t for x, y, t in gdev[n]}
        for e in r[n]:
            g = gs.get((e["start"], e["end"]))
            if g and {g, e["entity"]} == {SD_, DC_}:
                c[f"{g[:4]}->{e['entity'][:4]}"] += 1
    say(f"  repeat {i}: S->D {c['Spec->Dise']} D->S {c['Dise->Spec']} total {sum(c.values())}")
d10 = set(dev10["documents"])
for name, ids in (("dev10", sorted(d10)), ("dev30", dev30_ids)):
    her = bare = 0
    for n in ids:
        t = train[n]["text"]
        for x, y, ty in ents(train[n]):
            s = t[x:y]
            if ty == SD_ and PAT_HERED.match(s):
                her += 1
            if ty == DC_ and PAT_BARE_WIDE.match(s):
                bare += 1
    say(f"  {name} gold: hereditary/sporadic ... cancer as SpecificDisease {her}; bare cancer/tumour/lipoma as DiseaseClass {bare}")

(HERE / "audit_helper_output.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
