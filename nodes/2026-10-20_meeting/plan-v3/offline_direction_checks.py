"""Offline checks used to rank research directions for the 2026-10-20 meeting (no API calls).

Question: which candidate directions have support in data that already exists, and how large is
the effect each could have on validation F1 (strict span + subtype, PubAnnotation multiset)?

Inputs (all saved earlier):
    data/datasets/ncbi_disease/{train,valid}/*.json      gold, PubAnnotation
    outputs/.../<run>/*.json                             saved valid100 predictions (8 guideline runs)
    reproduction/results/size_noise/repeat_0[1-5].json   5 repeated dev10 annotations, original guideline

Sections (each prints its own block):
    A  run-to-run noise on valid100 (the only guideline annotated twice: R4)
    B  majority vote over the 8 saved guideline runs (exploratory: the run set was not chosen in advance)
    C  human-review effort curve: F1 after an expert fixes the k least-agreed predicted entities
    D  gold subtype consistency (same string, different subtype) and train precedent for valid S/D confusions
    E  document-level propagation of predicted strings and within-document type harmonization
    F  dictionary baselines from gold (dev10 only; train minus dev10) and precedent relabeling
    G  abbreviation share of errors; boundary error direction

Outputs: offline_direction_checks.json and offline_direction_checks_output.txt next to this script.

    python nodes/2026-10-20_meeting/plan-v3/offline_direction_checks.py
"""
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GOLD_VALID = ROOT / "data/datasets/ncbi_disease/valid"
GOLD_TRAIN = ROOT / "data/datasets/ncbi_disease/train"
SIZE_NOISE = ROOT / "reproduction/results/size_noise"
RUNS = {
    "original": "outputs/ncbi_disease/20260802_gpt54-high_valid-G",
    "R4": "outputs/ncbi_disease/20260802_gpt54-high_valid-M",
    "R4_rerun": "outputs/ncbi_disease/20260824_gpt54-high_valid-published-rerun",
    "topk4": "outputs/20261007_ncbi_gpt54-high_valid-topk4",
    "dev20": "outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev20",
    "dev30": "outputs/ncbi_disease/20260813_gpt54-high_valid-M-dev30",
    "noTP": "outputs/ncbi_disease/20260824_gpt54-high_valid-noTP_run2",
    "abstraction": "outputs/ncbi_disease/20260824_gpt54-high_valid-abstraction_run1",
}
EXPECTED_F1 = {"original": 0.7792, "R4": 0.7878, "R4_rerun": 0.7789, "topk4": 0.8023,
               "dev20": 0.7745, "dev30": 0.8050, "noTP": 0.7716, "abstraction": 0.7844}
SD, DC = "SpecificDisease", "DiseaseClass"
OUT = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    OUT.append(line)
    print(line)


def load_dir(d):
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(d).glob("*.json"))}


def ents(doc):
    return [(d["span"]["begin"], d["span"]["end"], d["obj"]) for d in doc["denotations"]]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return round(2 * p * r / (p + r), 4) if p + r else 0.0


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


# ---------------------------------------------------------------- load
valid_docs = load_dir(GOLD_VALID)
train_docs = load_dir(GOLD_TRAIN)
gold_valid = {n: ents(d) for n, d in valid_docs.items()}
runs = {}
for label, rel in RUNS.items():
    docs = load_dir(ROOT / rel)
    assert set(docs) == set(valid_docs), label
    runs[label] = {n: ents(d) for n, d in docs.items()}
    got = score(gold_valid, runs[label])["f1"]
    assert abs(got - EXPECTED_F1[label]) < 1e-4, (label, got)
dev_repeats = [json.loads((SIZE_NOISE / f"repeat_0{i}.json").read_text(encoding="utf-8")) for i in range(1, 6)]
dev30_ids = sorted(dev_repeats[0])
assert all(sorted(r) == dev30_ids for r in dev_repeats)
sampled = json.loads((ROOT / "outputs/ncbi_disease/20260802_gpt54-high_moderation/inputs/sampled_train_documents.json")
                     .read_text(encoding="utf-8"))
dev_ids = sorted(x["filename"] for x in sampled)  # the dev10 of every run since 08/02
assert set(dev_ids) <= set(dev30_ids)
gold_dev = {n: ents(train_docs[n]) for n in dev30_ids}
dev_pred = [{n: [(e["start"], e["end"], e["entity"]) for e in r[n]] for n in dev30_ids} for r in dev_repeats]
train_rest = {n: d for n, d in train_docs.items() if n not in set(dev30_ids)}  # excludes every development document
results = {"runs_f1": {k: score(gold_valid, v) for k, v in runs.items()}}
say("== inputs")
say("valid docs", len(valid_docs), "gold mentions", sum(map(len, gold_valid.values())),
    "| train docs", len(train_docs), "dev10", len(dev_ids), "dev30 (size_noise sample)", len(dev30_ids),
    "train minus dev30", len(train_rest))
for k, v in results["runs_f1"].items():
    say(f"  {k:12s} strict F1 {v['f1']:.4f}  TP {v['tp']} FP {v['fp']} FN {v['fn']}")
g10 = {n: gold_dev[n] for n in dev_ids}
dev_f1 = [score(g10, {n: p[n] for n in dev_ids})["f1"] for p in dev_pred]
say("dev10 repeats (original guideline, strict multiset; loop's set scoring gave 0.8028 0.8085 0.8252 0.7832 0.8028):", dev_f1)

# ---------------------------------------------------------------- A noise
say("\n== A  run-to-run noise on valid100: R4 guideline annotated twice")
a, b = runs["R4"], runs["R4_rerun"]
same = sum(sum((Counter(a[n]) & Counter(b[n])).values()) for n in valid_docs)
na, nb = sum(map(len, a.values())), sum(map(len, b.values()))
docs_identical = sum(1 for n in valid_docs if Counter(a[n]) == Counter(b[n]))
fa, fb = results["runs_f1"]["R4"]["f1"], results["runs_f1"]["R4_rerun"]["f1"]
results["A"] = {"f1": [fa, fb], "abs_diff": round(abs(fa - fb), 4), "sd_estimate_from_pair": round(abs(fa - fb) / 2 ** 0.5, 4),
                "pred_entities": [na, nb], "identical_entities": same,
                "share_identical_of_union": round(same / (na + nb - same), 4), "docs_identical": docs_identical}
say(f"F1 {fa} vs {fb}; |diff| {abs(fa-fb):.4f}; SD estimate from one pair {abs(fa-fb)/2**0.5:.4f} (2 runs only, very rough)")
say(f"predicted entities {na} / {nb}; identical {same}; identical share of union {same/(na+nb-same):.3f}; documents with identical output {docs_identical}/100")

# ---------------------------------------------------------------- B vote
say("\n== B  vote over the 8 saved guideline runs (typed entity must appear in >= k runs)")
labels = list(RUNS)
votes = {n: Counter() for n in valid_docs}
for lab in labels:
    for n, es in runs[lab].items():
        for e in set(es):
            votes[n][e] += 1
results["B"] = {}
for k in range(1, len(labels) + 1):
    pred = {n: [e for e, c in votes[n].items() if c >= k] for n in valid_docs}
    s = score(gold_valid, pred)
    results["B"][k] = s
    say(f"  k>={k}: F1 {s['f1']:.4f}  TP {s['tp']} FP {s['fp']} FN {s['fn']}")
# same with the 4 runs that are refined guidelines from dev10 only would be a post-hoc choice; not reported.
best_single = max(EXPECTED_F1.values())
say(f"best single run {best_single}; mean of the 8 single runs {sum(EXPECTED_F1.values())/8:.4f}")

# ---------------------------------------------------------------- C review curve
say("\n== C  human-review effort curve (expert = gold; reviewing an entity fixes its span/type or deletes it)")


def classify_preds(gold, pred):
    """Per document: label each predicted entity TP, FIX (overlaps an unmatched gold entity) or DEL."""
    out = []
    g_left = Counter(gold)
    status = []
    for e in pred:
        if g_left[e] > 0:
            g_left[e] -= 1
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
    for e, s in zip(pred, status):
        out.append((e, s))
    return out, len(unmatched)


def curve(base_label, conf_labels, seeds=20):
    base = runs[base_label]
    items = []  # (confidence, status)
    fn_unreachable = 0
    for n in valid_docs:
        cls, missed = classify_preds(gold_valid[n], base[n])
        fn_unreachable += missed
        for e, s in cls:
            conf = sum(1 for lab in conf_labels if e in set(runs[lab][n]))
            items.append((conf, s))
    total_gold = sum(map(len, gold_valid.values()))
    n_items = len(items)

    def f1_after(reviewed):
        tp = sum(1 for _, s in items if s == "TP") + sum(1 for _, s in reviewed if s == "FIX")
        fp = sum(1 for _, s in items if s != "TP") - sum(1 for _, s in reviewed if s != "TP")
        return prf(tp, fp, total_gold - tp)

    rows = {}
    for frac in (0.0, 0.1, 0.2, 0.3, 0.5, 1.0):
        k = round(frac * n_items)
        accs = []
        for seed in range(seeds):
            rng = random.Random(seed)
            order = sorted(items, key=lambda x: (x[0], rng.random()))
            accs.append(f1_after(order[:k]))
        rnd = []
        for seed in range(seeds):
            rng = random.Random(1000 + seed)
            sh = items[:]
            rng.shuffle(sh)
            rnd.append(f1_after(sh[:k]))
        oracle = f1_after(sorted(items, key=lambda x: x[1] == "TP")[:k])
        rows[frac] = {"entities_reviewed": k, "agreement_order": round(sum(accs) / seeds, 4),
                      "random_order": round(sum(rnd) / seeds, 4), "oracle_order": oracle}
    conf_hist = Counter(c for c, _ in items)
    wrong_by_conf = {c: sum(1 for cc, s in items if cc == c and s != "TP") for c in sorted(conf_hist)}
    return {"base": base_label, "confidence_from": conf_labels, "predicted_entities": n_items,
            "wrong_entities": sum(1 for _, s in items if s != "TP"),
            "gold_never_proposed": fn_unreachable, "curve": rows,
            "agreement_histogram": dict(sorted(conf_hist.items())), "wrong_by_agreement": wrong_by_conf}


others = [l for l in labels if l != "topk4"]
results["C"] = {"topk4_vs_7_other_runs": curve("topk4", others),
                "R4_vs_rerun": curve("R4", ["R4_rerun"])}
for key, r in results["C"].items():
    say(f"-- {key}: base {r['base']}, {r['predicted_entities']} predicted entities, {r['wrong_entities']} wrong, "
        f"{r['gold_never_proposed']} gold entities never proposed by the base run")
    say("   agreement histogram (number of other runs with the identical entity):", r["agreement_histogram"])
    say("   wrong entities per agreement level:", r["wrong_by_agreement"])
    for frac, row in r["curve"].items():
        say(f"   review {frac:>4.0%} ({row['entities_reviewed']:3d} entities): agreement order F1 {row['agreement_order']:.4f} | "
            f"random {row['random_order']:.4f} | oracle {row['oracle_order']:.4f}")

# recall candidates: entities proposed by other runs that overlap no topk4 prediction
cand = cand_gold_exact = cand_gold_overlap = 0
for n in valid_docs:
    base = runs["topk4"][n]
    pool = set()
    for lab in others:
        for e in runs[lab][n]:
            if not any(overlaps(e, b2) for b2 in base):
                pool.add(e)
    # collapse candidates with the same span
    spans_seen = {}
    for e in pool:
        spans_seen.setdefault(e[:2], e)
    for e in spans_seen.values():
        cand += 1
        if e in set(gold_valid[n]):
            cand_gold_exact += 1
        elif any(overlaps(e, g) for g in gold_valid[n]):
            cand_gold_overlap += 1
results["C"]["recall_candidates_from_other_runs"] = {"candidates": cand, "exact_gold": cand_gold_exact,
                                                     "overlap_gold_only": cand_gold_overlap}
say(f"-- missed-entity candidates: spans proposed by the 7 other runs that overlap no topk4 prediction: {cand}; "
    f"exactly gold {cand_gold_exact}; overlapping a gold span {cand_gold_overlap}")

# ---------------------------------------------------------------- D subtype consistency
say("\n== D  gold subtype consistency")


def label_table(docs):
    t = defaultdict(Counter)
    for d in docs.values():
        for b2, e, ty in ents(d):
            t[d["text"][b2:e].lower()][ty] += 1
    return t


lt_train = label_table(train_rest)
lt_valid = label_table(valid_docs)
for name, lt in (("train minus dev30", lt_train), ("valid", lt_valid)):
    multi = {s: c for s, c in lt.items() if sum(c.values()) >= 2}
    mixed = {s: c for s, c in multi.items() if len(c) > 1}
    mixed_sd = {s: c for s, c in multi.items() if c[SD] and c[DC]}
    mentions_multi = sum(sum(c.values()) for c in multi.values())
    mentions_mixed = sum(sum(c.values()) for c in mixed.values())
    say(f"{name}: strings seen >=2 times {len(multi)} ({mentions_multi} mentions); with >1 subtype {len(mixed)} "
        f"({mentions_mixed} mentions, {mentions_mixed/mentions_multi:.1%}); with both S and D {len(mixed_sd)}")
    results.setdefault("D", {})[name] = {"strings_multi": len(multi), "mentions_multi": mentions_multi,
                                         "strings_mixed": len(mixed), "mentions_mixed": mentions_mixed,
                                         "strings_mixed_SD": len(mixed_sd),
                                         "top_mixed": sorted(((s, dict(c)) for s, c in mixed.items()),
                                                             key=lambda x: -sum(x[1].values()))[:15]}
say("most frequent mixed strings in train minus dev30:", results["D"]["train minus dev30"]["top_mixed"][:10])

# valid S<->D confusions of topk4 (same span, type differs), judged by train precedent
conf_rows = Counter()
examples = defaultdict(list)
for n, doc in valid_docs.items():
    g_spans = {(b2, e): ty for b2, e, ty in gold_valid[n]}
    for b2, e, ty in runs["topk4"][n]:
        gt = g_spans.get((b2, e))
        if gt and gt != ty and {gt, ty} == {SD, DC}:
            s = doc["text"][b2:e].lower()
            c = lt_train.get(s, Counter())
            tot = c[SD] + c[DC]
            if tot == 0:
                cat = "string unseen in train gold (as S or D)"
            elif c[gt] / tot >= 0.75:
                cat = "train precedent agrees with valid gold (>=75%)"
            elif c[ty] / tot >= 0.75:
                cat = "train precedent agrees with the prediction (>=75%)"
            else:
                cat = "train precedent mixed"
            conf_rows[cat] += 1
            examples[cat].append(f"{s} [gold {gt[:4]}, pred {ty[:4]}, train S{c[SD]}/D{c[DC]}]")
results["D"]["topk4_SD_confusions_by_train_precedent"] = dict(conf_rows)
results["D"]["examples"] = {k: v[:12] for k, v in examples.items()}
say("topk4 same-span S<->D confusions on valid, by train-gold precedent:", dict(conf_rows))
for k, v in examples.items():
    say(f"   {k}: {v[:8]}")

# ---------------------------------------------------------------- E propagation
say("\n== E  document-level propagation and type harmonization")
WORD = r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])"


def occurrences(text, s):
    return [(m.start(), m.end()) for m in re.finditer(WORD.format(re.escape(s)), text)]


def gold_consistency(docs):
    occ_total = occ_annot = occ_same_type = 0
    for d in docs.values():
        text = d["text"]
        es = ents(d)
        by_span = {(b2, e): ty for b2, e, ty in es}
        strings = Counter()
        for b2, e, ty in es:
            strings[(text[b2:e], ty)] += 1
        done = set()
        for (s, ty) in strings:
            if s in done:
                continue
            done.add(s)
            for o in occurrences(text, s):
                if any(overlaps(o, (b2, e)) and (b2, e) != o for b2, e, _ in es):
                    continue  # occurrence is inside a longer annotated span
                occ_total += 1
                if o in by_span:
                    occ_annot += 1
                    types = [t for (ss, t) in strings if ss == s]
                    if by_span[o] == Counter(types).most_common(1)[0][0]:
                        occ_same_type += 1
    return occ_total, occ_annot, occ_same_type


for name, docs in (("train", train_docs), ("valid", valid_docs)):
    t, a_, s_ = gold_consistency(docs)
    say(f"gold {name}: free occurrences of annotated strings {t}; annotated {a_} ({a_/t:.1%}); "
        f"annotated with the string's majority type in that document {s_} ({s_/t:.1%})")
    results.setdefault("E", {})[f"gold_consistency_{name}"] = {"occurrences": t, "annotated": a_, "same_type": s_}


def propagate(text, pred, harmonize=True, add=True):
    pred = list(pred)
    if harmonize:
        major = {}
        for s in set(text[b2:e] for b2, e, _ in pred):
            c = Counter(ty for b2, e, ty in pred if text[b2:e] == s)
            top = c.most_common()
            if len(top) == 1 or top[0][1] > top[1][1]:
                major[s] = top[0][0]
        pred = [(b2, e, major.get(text[b2:e], ty)) for b2, e, ty in pred]
    if add:
        typed = {}
        for b2, e, ty in pred:
            typed.setdefault(text[b2:e], Counter())[ty] += 1
        extra = []
        for s, c in typed.items():
            if len(s) < 3:
                continue
            ty = c.most_common(1)[0][0]
            for o in occurrences(text, s):
                if not any(overlaps(o, p[:2]) for p in pred + extra):
                    extra.append((o[0], o[1], ty))
        pred = pred + extra
    return pred


def apply_all(pred_by_doc, docs, **kw):
    return {n: propagate(docs[n]["text"], p, **kw) for n, p in pred_by_doc.items()}


dev_rows = []
for i, p in enumerate(dev_pred):
    base = score(gold_dev, p)["f1"]
    h = score(gold_dev, apply_all(p, train_docs, add=False))["f1"]
    ad = score(gold_dev, apply_all(p, train_docs, harmonize=False))["f1"]
    both = score(gold_dev, apply_all(p, train_docs))["f1"]
    dev_rows.append((base, h, ad, both))
results["E"]["dev30_repeats"] = dev_rows
say("dev30 documents, 5 repeats, original guideline (base, harmonize only, add only, both):", dev_rows)
say(f"   mean delta harmonize {sum(r[1]-r[0] for r in dev_rows)/5:+.4f}; add only {sum(r[2]-r[0] for r in dev_rows)/5:+.4f}; "
    f"both {sum(r[3]-r[0] for r in dev_rows)/5:+.4f}")
valid_rows = {}
for lab in labels:
    base = results["runs_f1"][lab]
    h = score(gold_valid, apply_all(runs[lab], valid_docs, add=False))
    ad = score(gold_valid, apply_all(runs[lab], valid_docs, harmonize=False))
    both = score(gold_valid, apply_all(runs[lab], valid_docs))
    valid_rows[lab] = {"base": base["f1"], "harmonize": h["f1"], "add_only": ad["f1"], "harmonize_add": both["f1"],
                       "add_only_tp": ad["tp"] - base["tp"], "add_only_fp": ad["fp"] - base["fp"]}
    say(f"   valid {lab:12s} base {base['f1']:.4f}  harmonize {h['f1']:.4f}  add only {ad['f1']:.4f} "
        f"(TP {ad['tp']-base['tp']:+d}, FP {ad['fp']-base['fp']:+d})  both {both['f1']:.4f}")
results["E"]["valid"] = valid_rows
say(f"   mean delta over 8 valid runs: harmonize {sum(v['harmonize']-v['base'] for v in valid_rows.values())/8:+.4f}; "
    f"add only {sum(v['add_only']-v['base'] for v in valid_rows.values())/8:+.4f}; "
    f"both {sum(v['harmonize_add']-v['base'] for v in valid_rows.values())/8:+.4f}")

# ---------------------------------------------------------------- F dictionary baselines
say("\n== F  dictionary baselines and precedent relabeling (reference points, not candidate methods)")


def build_dict(docs, min_len=3):
    t = label_table(docs)
    return {s: c.most_common(1)[0][0] for s, c in t.items() if len(s) >= min_len}


def dict_annotate(text, dic):
    low = text.lower()
    cands = []
    for s, ty in dic.items():
        for m in re.finditer(WORD.format(re.escape(s)), low):
            cands.append((m.start(), m.end(), ty))
    cands.sort(key=lambda x: (-(x[1] - x[0]), x[0]))
    chosen = []
    for c in cands:
        if not any(overlaps(c, d) for d in chosen):
            chosen.append(c)
    return chosen


for name, src in (("dev10 gold only", {n: train_docs[n] for n in dev_ids}), ("train minus dev30 gold", train_rest)):
    dic = build_dict(src)
    pred = {n: dict_annotate(d["text"], dic) for n, d in valid_docs.items()}
    s, s_span = score(gold_valid, pred), score(gold_valid, pred, typed=False)
    results.setdefault("F", {})[name] = {"dictionary_entries": len(dic), "strict": s, "span_only": s_span}
    say(f"dictionary from {name}: {len(dic)} strings; valid strict F1 {s['f1']:.4f} (TP {s['tp']} FP {s['fp']} FN {s['fn']}); span-only F1 {s_span['f1']:.4f}")

# precedent relabeling of topk4 predictions with train-minus-dev10 gold (exact string, n>=2, >=75% majority)
for min_n in (2, 3):
    relabeled = changed = 0
    newpred = {}
    for n, doc in valid_docs.items():
        out = []
        for b2, e, ty in runs["topk4"][n]:
            c = lt_train.get(doc["text"][b2:e].lower())
            if c and sum(c.values()) >= min_n:
                top, cnt = c.most_common(1)[0]
                if cnt / sum(c.values()) >= 0.75 and top != ty:
                    changed += 1
                    ty = top
            out.append((b2, e, ty))
        newpred[n] = out
    s = score(gold_valid, newpred)
    results["F"][f"precedent_relabel_topk4_min{min_n}"] = {"changed": changed, "strict": s}
    say(f"topk4 relabeled by train precedent (n>={min_n}, >=75%): {changed} entities changed; strict F1 {s['f1']:.4f} "
        f"(base {results['runs_f1']['topk4']['f1']:.4f})")

# precedent relabeling restricted to S<->D: only a predicted S or D is switched, and only toward the other of the two
for min_n in (2, 3):
    changed = 0
    newpred = {}
    for n, doc in valid_docs.items():
        out = []
        for b2, e, ty in runs["topk4"][n]:
            if ty in (SD, DC):
                c = lt_train.get(doc["text"][b2:e].lower(), Counter())
                other = DC if ty == SD else SD
                tot = c[SD] + c[DC]
                if tot >= min_n and c[other] / tot >= 0.75:
                    changed += 1
                    ty = other
            out.append((b2, e, ty))
        newpred[n] = out
    s = score(gold_valid, newpred)
    results["F"][f"precedent_relabel_SD_only_topk4_min{min_n}"] = {"changed": changed, "strict": s}
    say(f"topk4 S<->D relabeled by train precedent (n>={min_n}, >=75% of S+D): {changed} entities changed; "
        f"strict F1 {s['f1']:.4f} (base {results['runs_f1']['topk4']['f1']:.4f})")

# the same S<->D relabeling with precedent pools of growing size (how much does each extra annotated document buy?)
say("S<->D relabeling of topk4 by precedent pools of growing size (random documents from train minus dev30; 5 draws):")
results["F"]["precedent_pool_curve"] = {}
pool_names = sorted(train_rest)
for size in (10, 30, 100, 300, 563):
    f1s = []
    for draw in range(5 if size < 563 else 1):
        rng = random.Random(100 + draw)
        pool = {n: train_rest[n] for n in rng.sample(pool_names, size)}
        lt_pool = label_table(pool)
        newpred = {}
        for n, doc in valid_docs.items():
            out = []
            for b2, e, ty in runs["topk4"][n]:
                if ty in (SD, DC):
                    c = lt_pool.get(doc["text"][b2:e].lower(), Counter())
                    other = DC if ty == SD else SD
                    tot = c[SD] + c[DC]
                    if tot >= 2 and c[other] / tot >= 0.75:
                        ty = other
                out.append((b2, e, ty))
            newpred[n] = out
        f1s.append(score(gold_valid, newpred)["f1"])
    results["F"]["precedent_pool_curve"][size] = {"mean_f1": round(sum(f1s) / len(f1s), 4), "f1s": f1s}
    say(f"   pool {size:3d} documents: strict F1 mean {sum(f1s)/len(f1s):.4f}  draws {f1s}")

# ---------------------------------------------------------------- H bootstrap and S/D confusion listing
say("\n== H  paired document bootstrap (10,000 resamples, seed 42) and S/D confusions per run")


def per_doc_counts(pred):
    rows = []
    for n in sorted(valid_docs):
        gc, pc = Counter(gold_valid[n]), Counter(pred[n])
        c = sum((gc & pc).values())
        rows.append((c, sum(pc.values()) - c, sum(gc.values()) - c))
    return rows


def boot(pa, pb, reps=10000, seed=42):
    A, B = per_doc_counts(pa), per_doc_counts(pb)
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


vote4 = {n: [e for e, c in votes[n].items() if c >= 4] for n in valid_docs}
comparisons = {"topk4 - original": (runs["topk4"], runs["original"]),
               "topk4 - R4": (runs["topk4"], runs["R4"]),
               "R4 - R4_rerun (same guideline)": (runs["R4"], runs["R4_rerun"]),
               "vote>=4of8 - topk4": (vote4, runs["topk4"]),
               "vote>=4of8 - dev30": (vote4, runs["dev30"]),
               "vote>=4of8 - original": (vote4, runs["original"])}
results["H"] = {"bootstrap": {k: boot(*v) for k, v in comparisons.items()}}
for k, v in results["H"]["bootstrap"].items():
    say(f"  {k:32s} diff {v['diff']:+.4f}  95% CI [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]  P(diff>0) {v['p_gt0']:.3f}")

sd_counts = {}
for lab in labels:
    c = Counter()
    for n in valid_docs:
        g_spans = {(b2, e): ty for b2, e, ty in gold_valid[n]}
        for b2, e, ty in runs[lab][n]:
            gt = g_spans.get((b2, e))
            if gt and gt != ty:
                c[f"{gt[:4]}->{ty[:4]}"] += 1
    sd_counts[lab] = {k: c[k] for k in ("Spec->Dise", "Dise->Spec")}
results["H"]["same_span_SD_confusions_per_run"] = sd_counts
say("same-span S->D and D->S confusions per run:", sd_counts)
lst = []
for n, doc in valid_docs.items():
    g_spans = {(b2, e): ty for b2, e, ty in gold_valid[n]}
    for b2, e, ty in runs["topk4"][n]:
        gt = g_spans.get((b2, e))
        if gt and {gt, ty} == {SD, DC}:
            lst.append(f"{doc['text'][b2:e]} ({gt[:4]}->{ty[:4]})")
results["H"]["topk4_SD_confusions"] = sorted(lst)
say("topk4 S<->D same-span confusions:", sorted(lst))

# review curve as a function of how many other runs supply the agreement signal
say("\n== C2  review curve vs number of runs giving the agreement signal (base topk4; mean over random subsets)")
rng0 = random.Random(7)
results["C2"] = {}
for m in (1, 2, 3, 7):
    subsets = [rng0.sample(others, m) for _ in range(10)] if m < 7 else [others]
    agg = defaultdict(list)
    for sub in subsets:
        r = curve("topk4", sub, seeds=5)
        for frac in (0.1, 0.2, 0.3):
            agg[frac].append(r["curve"][frac]["agreement_order"])
    results["C2"][m] = {f: round(sum(v) / len(v), 4) for f, v in agg.items()}
    say(f"  m={m} other runs: review 10% -> {results['C2'][m][0.1]:.4f}, 20% -> {results['C2'][m][0.2]:.4f}, "
        f"30% -> {results['C2'][m][0.3]:.4f}")

# ---------------------------------------------------------------- G abbreviations, boundaries
say("\n== G  abbreviations and boundary direction (topk4 on valid)")
ABBR = re.compile(r"^(?=(?:.*[A-Z]){2})[A-Za-z0-9\-]{2,10}s?$")
disc = json.loads((ROOT / "reproduction/results/ncbi-valid-topk4-gpt54/discrepancies.json").read_text(encoding="utf-8"))
abbr = Counter()
tot = Counter()
for d in disc:
    txt = (d.get("gold") or d.get("pred") or {}).get("text", "")
    tot[d["category"]] += 1
    if ABBR.match(txt.strip()):
        abbr[d["category"]] += 1
results["G"] = {"discrepancies_by_category": dict(tot), "abbreviation_like": dict(abbr)}
say("discrepancies by category:", dict(tot))
say("of which the text is abbreviation-like:", dict(abbr), f"total {sum(abbr.values())}/{sum(tot.values())}")
longer = shorter = shifted = 0
extra_words = Counter()
for d in disc:
    if d["category"] != "boundary_mismatch":
        continue
    g, p = d["gold"], d["pred"]
    if p["start"] <= g["start"] and p["end"] >= g["end"]:
        longer += 1
        doc = valid_docs.get(d["doc_id"] + ".json")
        if doc:
            extra = doc["text"][p["start"]:g["start"]] + " " + doc["text"][g["end"]:p["end"]]
            for w in re.findall(r"[A-Za-z]+", extra.lower()):
                extra_words[w] += 1
    elif p["start"] >= g["start"] and p["end"] <= g["end"]:
        shorter += 1
    else:
        shifted += 1
results["G"]["boundary"] = {"pred_longer": longer, "pred_shorter": shorter, "shifted": shifted,
                            "extra_words_when_longer": extra_words.most_common(15)}
say(f"boundary mismatches: prediction longer {longer}, shorter {shorter}, shifted {shifted}")
say("words the prediction adds when longer:", extra_words.most_common(12))

(HERE / "offline_direction_checks.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
(HERE / "offline_direction_checks_output.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
