"""Stage 0 of the clause-ablation test (notes/20261103_clause_ablation_design_review.md): offline preparation, nothing sent.

The rule under test labels a disease name Modifier when it follows a relational noun plus "of" or "with" ("a family history
of ovarian cancer", "risk of", "patients with"). This script:
A. checks the hand inventory outputs/clause_ablation_stage0/rule_locations.csv: every listed line of every guideline that
   states the rule contains the quoted words, and the original guideline has no line of that kind;
B. writes the frozen edited guidelines and their unified diffs (top-4 loop07 with the rule removed; the original with
   loop07's lines 65 and 66 inserted; optionally top-1 loop05 with its two pointers removed), with SHA-256 hashes;
C. checks offline that the removal is clean: no line of an edited guideline still assigns Modifier to such a position, the
   inventory lines are all edited, the gene-noun and premodifier rules are unchanged word for word, and nothing else moved;
D. recounts documents and calls from text and gold only: validation documents with the 71 post-phrase non-Modifier gold
   mentions, and the larger set adding gene-noun and people/risk premodifier Modifier gold (definitions from
   modifier_subset.py); the unused training pool (train minus dev50, the 50 test documents and the 6 BioRED PMIDs, whose
   files are filtered by name before any is read) with the same definitions;
E. estimates cost from the saved replies: each validation call's batch price from its usage (run_haiku.cost_jpy, the
   function behind the recorded reproduction cost), per document for the guideline the arm uses; for training documents,
   which have no measured call, a per-guideline least-squares line of call cost on document length.
Writes outputs/clause_ablation_stage0/: the edited guidelines, *.diff, manifest.json, stage0_output.txt.
"""

from __future__ import annotations

import contextlib
import csv
import difflib
import hashlib
import io
import json
import re
import runpy
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parent / "outputs" / "clause_ablation_stage0"
RUNS = ROOT / "outputs" / "ncbi_disease"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
ORIGINAL = ROOT / "data" / "guidelines" / "ncbi_disease_guidelines.txt"
sys.path.insert(0, str(ROOT / "todo-temp" / "haiku-trial"))
import run_haiku as rh  # noqa: E402  (price table and cost_jpy only; nothing is sent)

with contextlib.redirect_stdout(io.StringIO()):
    m = runpy.run_path(str(HERE / "modifier_subset.py"))
texts, gold, member, groups, head_group, B1, B2, orig, mod, name, REL_GROUPS = (
    m[k] for k in ("texts", "gold", "member", "groups", "head_group", "B1", "B2", "orig", "mod", "name", "REL_GROUPS"))
by = {name[x]: x for x in mod}
FOLDER = {n: RUNS / x for n, x in by.items()}
REPEATS = 5
sha = lambda b: hashlib.sha256(b).hexdigest()
out, man = [], {"repeats_per_arm": REPEATS}


def guideline(n):
    return ORIGINAL.read_text(encoding="utf-8") if n == "original" else (FOLDER[n] / "final" / "final_guidelines.txt").read_text(encoding="utf-8")


# ---------- A ----------
inv = list(csv.DictReader((OUT / "rule_locations.csv").open(encoding="utf-8")))
out.append("A. Where each guideline states the rule (hand inventory rule_locations.csv; each line checked for its quoted words)")
bad = []
for n in dict.fromkeys(r["guideline"] for r in inv):
    ls = guideline(n).split("\n")
    rows = [r for r in inv if r["guideline"] == n]
    for r in rows:
        if r["words"] not in ls[int(r["line"]) - 1]:
            bad.append((n, r["line"]))
    out.append(f"   {n:<14} {len(rows)} lines: " + ", ".join(f"L{r['line']}" for r in rows))
assert not bad, bad
FRAME = re.compile(r"histor|relative|kindred|\brisk\b|incidence|complement of|patients? with|relational|famil", re.I)
MODW = re.compile(r"Modifier|§ ?3\b|Section 3", re.I)
o_lines = [i + 1 for i, l in enumerate(guideline("original").split("\n")) if FRAME.search(l) and MODW.search(l)]
out.append(f"   original: lines naming both a relational frame word and Modifier/Section 3: {o_lines or 'none'}; "
           f"lines containing 'of' or 'with' in Section 3 (L27-L35): "
           f"{[i for i in range(27, 36) if re.search(r'\\b(of|with)\\b', guideline('original').split(chr(10))[i - 1])]}")
assert not o_lines

# ---------- B ----------
L07 = guideline("top-4 loop07")
EDITS = {
    "topk4_loop07_rule_removed": ("top-4 loop07", [
        (65, "A disease name that premodifies, or is the complement of, a context or population noun",
             "A disease name that premodifies a context or population noun"),
        (65, " This holds even when the context noun carries its own premodifier, as in *family history of*.", ""),
        (66, "“ovarian cancer population,” “family history of ovarian cancer,” and “ovarian cancer risk”",
             "“ovarian cancer population” and “ovarian cancer risk”"),
        (94, "(history, risk, incidence, cases, family, population). Such frames are **Modifier** under §3;",
             "(history, risk, incidence, cases, family, population);"),
        (112, " Cohort, history, risk, and population phrases are **Modifier**.", ""),
        (235, "; “a family history of ovarian cancer”", ""),
    ]),
    "topk1_loop05_rule_removed": ("top-1 loop05", [
        (63, " Such a term keeps its existing treatment (Modifier under Section 3).", " Such a term keeps its existing treatment."),
        (268, " and keeps its existing treatment (Section 3).", " and keeps its existing treatment."),
    ]),
}
edited = {}
for tag, (n, eds) in EDITS.items():
    ls = guideline(n).split("\n")
    for ln, old, new in eds:
        assert ls[ln - 1].count(old) == 1, (tag, ln, old)
        ls[ln - 1] = ls[ln - 1].replace(old, new)
    edited[tag] = (n, "\n".join(ls))
o_ls = guideline("original").split("\n")
assert o_ls[34] == "  - “HNPCC” as **Modifier**" and o_ls[35] == ""
L07s = L07.split("\n")
edited["original_plus_rule"] = ("original", "\n".join(o_ls[:35] + ["", L07s[64], L07s[65]] + o_ls[35:]))

out.append("\nB. Frozen guidelines (UTF-8, LF line ends, as the runner reads them) and diffs against their sources")
man["guidelines"] = {}
for tag, (n, text) in edited.items():
    src = guideline(n)
    (OUT / f"{tag}.txt").write_bytes(text.encode("utf-8"))
    diff = "".join(difflib.unified_diff(src.splitlines(True), text.splitlines(True),
                                        fromfile=f"{n} final guideline" if n != "original" else "original guideline",
                                        tofile=tag, n=1))
    (OUT / f"{tag}.diff").write_bytes(diff.encode("utf-8"))
    removed = sum(len(a) - len(b) for a, b in zip(src.split("\n"), text.split("\n")) if a != b) if n != "original" else 0
    man["guidelines"][tag] = {"source": n, "source_sha256": sha(src.encode("utf-8")), "sha256": sha(text.encode("utf-8")),
                              "diff_sha256": sha(diff.encode("utf-8")), "source_chars": len(src), "chars": len(text)}
    out.append(f"   {tag:<28} from {n:<13} source {sha(src.encode('utf-8'))[:16]}  edited {sha(text.encode('utf-8'))[:16]}"
               f"  diff {sha(diff.encode('utf-8'))[:16]}  characters {len(src):,} -> {len(text):,} ({len(text) - len(src):+,},"
               f" {100 * (len(text) - len(src)) / len(src):+.2f}%)")

# ---------- C ----------
out.append("\nC. Offline checks of the edits")
for tag, (n, text) in edited.items():
    src, ls = guideline(n).split("\n"), text.split("\n")
    if n == "original":
        inserted = [l for l in ls if l not in src]
        assert len(ls) == len(src) + 3 and inserted == [L07s[64], L07s[65]]
        out.append(f"   {tag}: three lines added after L35 (a blank line, loop07 L65, L66); every original line kept in order: "
                   f"{[l for l in ls if l not in (L07s[64], L07s[65])] == src[:35] + [''] + src[35:]}")
        continue
    assert len(ls) == len(src)
    changed = [i + 1 for i, (a, b) in enumerate(zip(src, ls)) if a != b]
    listed = sorted({int(r["line"]) for r in inv if r["guideline"] == n})
    left = [r for r in inv if r["guideline"] == n and r["words"] in ls[int(r["line"]) - 1]]
    still = [i + 1 for i, l in enumerate(ls) if MODW.search(l) and FRAME.search(l)]
    out.append(f"   {tag}: lines changed {changed}; inventory lines {listed}; inventory quotes still present: "
               f"{[(r['line'], r['words']) for r in left] or 'none'}")
    hist = [(i + 1, l.strip()[:150]) for i, l in enumerate(ls) if re.search(r"histor(y|ies) of|relatives with|complement of", l, re.I)]
    out.append(f"      lines still containing 'history of', 'relatives with' or 'complement of': {len(hist)}")
    for i, l in hist:
        out.append(f"         L{i}: {l}")
    out.append(f"      lines naming both a relational frame word and Modifier/Section 3 after the edit: {still}")
    for i in still:
        out.append(f"         L{i}: {ls[i - 1].strip()[:200]}")
    assert set(changed) <= set(listed) and not left
    if n == "top-4 loop07":
        keep = list(range(55, 64)) + list(range(69, 76))
        out.append(f"      Section 3 definition, example and gene-designation rule (L55-L63, L69-L75) unchanged: "
                   f"{all(src[i - 1] == ls[i - 1] for i in keep)}; premodifier sentence kept: "
                   f"{'A disease name that premodifies a context or population noun (such as *cases*, *population*, *history*, *risk*, or *incidence*) is annotated **Modifier**.' in ls[64]}")
        assert all(src[i - 1] == ls[i - 1] for i in keep)
        man["topk4_loop07_changed_lines"] = changed

# ---------- D ----------
post = [k for k in gold if k[3] != "Modifier" and k in member and "B2" in member[k]]
b1m = groups["Modifier gold, B1 context"]
gene = [k for k in b1m if head_group(k).startswith("molecular")]
people = [k for k in b1m if head_group(k).startswith(("people", "risk"))]
d_post = sorted({k[0] for k in post})
d_big = sorted({k[0] for k in post + gene + people})
out.append("\nD. Documents and calls, chosen from text and gold only")
out.append(f"   validation: post-phrase non-Modifier gold {len(post)} mentions in {len(d_post)} documents; gene-noun Modifier gold "
           f"{len(gene)} in {len({k[0] for k in gene})}; people/risk premodifier Modifier gold {len(people)} in {len({k[0] for k in people})};"
           f" union {len(d_big)} documents")
assert len(post) == 71 and len(gene) == 99
calls_valid = {"unchanged": len(d_big) * REPEATS, "rule removed": len(d_big) * REPEATS,
               "original": len(d_post) * REPEATS, "original plus rule": len(d_post) * REPEATS}
out.append(f"   validation design, {REPEATS} repeats: " + ", ".join(f"{a} {c}" for a, c in calls_valid.items())
           + f"; total {sum(calls_valid.values())}")
heldout = json.loads((ROOT / "reproduction" / "test_splits" / "ncbi_disease_heldout50.json").read_text(encoding="utf-8"))
dev50 = set(json.loads((ROOT / "reproduction" / "dev_splits" / "ncbi_disease_dev50.json").read_text(encoding="utf-8"))["documents"])
skip = set(heldout["documents"]) | dev50 | set(heldout["excluded_biored"])
pool = [p for p in sorted(TRAIN.glob("*.json")) if p.name not in skip]
assert len(pool) == heldout["pool_size"] - heldout["size"]
tr = {}
for p in pool:
    d = json.loads(p.read_text(encoding="utf-8"))
    t = d["text"]
    ps = gs = pp = 0
    rg = {}
    for a in d.get("denotations", []):
        b, e, lab = a["span"]["begin"], a["span"]["end"], a["obj"]
        mb = B2.search(t[max(0, b - 80):b])
        if lab != "Modifier" and mb:
            ps += 1
            gname = next(gn for gn, pat in REL_GROUPS if re.fullmatch(pat, mb.group(1).lower()))
            rg[gname] = rg.get(gname, 0) + 1
        mt = B1.match(t[e:e + 50])
        if lab == "Modifier" and mt:
            w = (mt.group(3) or "").strip()
            g_ = next(gn for gn, pat in m["HEAD_GROUPS"] if re.fullmatch(pat, w, re.I))
            gs += g_.startswith("molecular")
            pp += g_.startswith(("people", "risk"))
    tr[p.stem] = {"post": ps, "gene": gs, "people": pp, "chars": len(t), "rel": rg}
t_post = sorted(d for d, v in tr.items() if v["post"])
out.append(f"   unused training pool: {len(pool)} documents (train {len(list(TRAIN.glob('*.json')))} minus dev50, the 50 test documents"
           f" and {len(heldout['excluded_biored'])} BioRED PMIDs); with post-phrase non-Modifier gold: {len(t_post)} documents,"
           f" {sum(tr[d]['post'] for d in t_post)} mentions; in those documents gene-noun Modifier gold {sum(tr[d]['gene'] for d in t_post)},"
           f" people/risk premodifier Modifier gold {sum(tr[d]['people'] for d in t_post)}")
for gname, _ in REL_GROUPS:
    nv = sum(m["rel_group"](k) == gname for k in post)
    nt = sum(tr[d]["rel"].get(gname, 0) for d in t_post)
    if nv or nt:
        out.append(f"      by relational noun, {gname:<40} validation {nv:3}   training pool {nt:3}")
calls_train = {"unchanged": len(t_post) * REPEATS, "rule removed": len(t_post) * REPEATS}
out.append(f"   training design (two arms on these documents), {REPEATS} repeats: " + ", ".join(f"{a} {c}" for a, c in calls_train.items())
           + f"; total {sum(calls_train.values())}")
man["documents"] = {"validation_post": d_post, "validation_big": d_big, "training_post": t_post,
                    "calls_validation": calls_valid, "calls_training": calls_train}

# ---------- E ----------
prov = [json.loads(l) for l in (HERE.parent / "outputs" / "20261030_rationale_audit" / "provenance_documents.jsonl").open(encoding="utf-8")]
cost = {}
for r in prov:
    rep = json.loads((ROOT / r["candidate_replies"][0]["reply_file"]).read_text(encoding="utf-8"))
    cost[(r["run"], r["doc"])] = (rh.cost_jpy(rep["message"]["usage"], True), rep["message"]["usage"], int(r["prompt_chars"]))
x07 = by["top-4 loop07"]
per07 = {d: cost[(x07, d)][0] for d in texts}
per0 = {d: statistics.mean(cost[(x, d)][0] for x in orig) for d in texts}
out.append(f"\nE. Cost at the saved batch prices (run_haiku.cost_jpy; JPY per USD {rh.rs.JPY_PER_USD})")
out.append(f"   per validation call: top-4 loop07 mean {statistics.mean(per07.values()):.3f} (min {min(per07.values()):.3f}, max"
           f" {max(per07.values()):.3f}); original, mean of 19 runs per document, {statistics.mean(per0.values()):.3f}")
chars_tok = statistics.mean(c[2] / c[1]["input_tokens"] for c in cost.values())
extra_chars = len(L07s[64]) + len(L07s[65]) + 2
extra_jpy = extra_chars / chars_tok * rh.USD_PER_M[False]["in"] / 1e6 * rh.BATCH_FACTOR * rh.rs.JPY_PER_USD
out.append(f"   original plus rule: {extra_chars} more prompt characters, about {extra_chars / chars_tok:.0f} input tokens"
           f" ({chars_tok:.2f} characters per token in the saved calls), at most JPY {extra_jpy:.4f} more per call before any"
           " change in output length; priced with the original's per-document cost")
v = {"unchanged": sum(per07[d] for d in d_big) * REPEATS, "rule removed": sum(per07[d] for d in d_big) * REPEATS,
     "original": sum(per0[d] for d in d_post) * REPEATS, "original plus rule": sum(per0[d] for d in d_post) * REPEATS}
out.append("   validation design: " + ", ".join(f"{a} JPY {c:,.0f}" for a, c in v.items()) + f"; total JPY {sum(v.values()):,.0f}"
           f" (USD {sum(v.values()) / rh.rs.JPY_PER_USD:.2f})")


def fit(run_list):
    xs = [len(texts[d]) for x in run_list for d in texts]
    ys = [cost[(x, d)][0] for x in run_list for d in texts]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    r = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / (sum((a - mx) ** 2 for a in xs) * sum((c - my) ** 2 for c in ys)) ** 0.5
    return my - b * mx, b, r


a7, b7, r7 = fit([x07])
t_len = [tr[d]["chars"] for d in t_post]
tc = sum(a7 + b7 * c for c in t_len) * REPEATS * 2
tm = statistics.mean(per07.values()) * len(t_post) * REPEATS * 2
out.append(f"   training design: per-call cost of top-4 loop07 on document length, intercept {a7:.3f}, slope {b7 * 1000:.4f} per 1,000"
           f" characters (r = {r7:.2f}); training documents mean {statistics.mean(t_len):,.0f} characters, validation"
           f" {statistics.mean(len(t) for t in texts.values()):,.0f}; estimate JPY {tc:,.0f} (at the validation mean per call JPY {tm:,.0f})")
per_doc = (a7 + b7 * statistics.mean(t_len)) * REPEATS * 2
out.append(f"   per training document in both arms ({REPEATS} repeats each), at the fitted cost of the pool's mean length: JPY {per_doc:.2f};"
           f" e.g. 40 documents, {40 * REPEATS * 2} calls: JPY {40 * per_doc:,.0f}")
man["cost_jpy"] = {"validation": v, "validation_total": sum(v.values()), "training_fit": tc, "training_mean": tm,
                   "per_call_loop07_mean": statistics.mean(per07.values()), "per_call_original_mean": statistics.mean(per0.values())}
(OUT / "manifest.json").write_bytes((json.dumps(man, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
(OUT / "stage0_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
