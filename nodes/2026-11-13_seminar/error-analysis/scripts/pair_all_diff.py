"""top-4 loop04 against top-4 loop08 on the whole validation set: on how many gold mentions of each type the two runs
differ, and how many predictions without a gold mention appear in only one run (11/11). Answers whether the 42 gold
Modifiers that only one of the two gets right (pair_vs_original_output.txt section D) are all the differences.

Offline, no API calls. Inputs: validation gold and error_rows.csv. A gold mention is right in a run when the run has no
error row for it; otherwise its outcome is the set of its error rows (kind, predicted label, predicted span), so two
runs that are both wrong differ when they are wrong in different ways.
Run from the repository root. Writes outputs/overall_view/pair_all_diff_output.txt.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
RUN = {"loop04": "20261022_haiku-xhigh_topk4_loop04", "loop08": "20261022_haiku-xhigh_topk4_loop08"}
NAME = {"loop04": "top-4 loop04", "loop08": "top-4 loop08"}
LABELS = ["Modifier", "SpecificDisease", "DiseaseClass", "CompositeMention"]

gold: dict[tuple[str, int, int], str] = {}
texts: dict[str, str] = {}
for path in sorted(VALID.glob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    texts[doc["sourceid"]] = doc["text"]
    for a in doc["denotations"]:
        key = (doc["sourceid"], a["span"]["begin"], a["span"]["end"])
        assert key not in gold, key
        gold[key] = a["obj"]
assert set(gold.values()) == set(LABELS)

outcome: dict[str, dict] = {n: defaultdict(list) for n in RUN}
no_gold: dict[str, set] = {n: set() for n in RUN}
run_rows: dict[str, list] = {n: [] for n in RUN}
for r in csv.DictReader((ROOT / "nodes/shared/error-analysis/outputs" / "error_rows.csv").open(encoding="utf-8")):
    for n, run in RUN.items():
        if r["run"] != run:
            continue
        run_rows[n].append(r)
        pred = (r["kind"], r["pred_label"], r["pred_start"], r["pred_end"])
        if r["gold_start"]:
            g = (r["doc"], int(r["gold_start"]), int(r["gold_end"]))
            assert gold[g] == r["gold_label"], (g, r["gold_label"])
            outcome[n][g].append(pred)
        else:
            no_gold[n].add((r["doc"], r["pred_start"], r["pred_end"], r["pred_label"], r["kind"]))


def state(n, g):
    return tuple(sorted(outcome[n][g])) if g in outcome[n] else None


table = {lab: Counter() for lab in LABELS}
for g, lab in gold.items():
    s4, s8 = state("loop04", g), state("loop08", g)
    if s4 is None and s8 is None:
        table[lab]["both right"] += 1
    elif s4 is None:
        table[lab]["only loop04 right"] += 1
    elif s8 is None:
        table[lab]["only loop08 right"] += 1
    elif s4 == s8:
        table[lab]["both wrong, same way"] += 1
    else:
        table[lab]["both wrong, different ways"] += 1
assert table["Modifier"]["only loop08 right"] == 33 and table["Modifier"]["only loop04 right"] == 9

out: list[str] = []
w = out.append
w("top-4 loop04 与 top-4 loop08 在整个验证集上的全部差别（2026-11-11，离线）")
w("")
w("A. gold 提及：两份结果相同还是不同。都错时，错法（错误类型、标成的类型、标出的范围）不同也算不同")
cols = ["both right", "only loop08 right", "only loop04 right", "both wrong, different ways", "both wrong, same way"]
head = ["都标对", "只有 top-4 loop08 标对", "只有 top-4 loop04 标对", "都错但错法不同", "都错且错法相同"]
w("  gold 类型 | 提及数 | " + " | ".join(head) + " | 结果不同合计")
tot = Counter()
for lab in LABELS:
    c = table[lab]
    differ = c["only loop08 right"] + c["only loop04 right"] + c["both wrong, different ways"]
    tot.update(c)
    tot["differ"] += differ
    w(f"  {lab} | {sum(c[k] for k in cols)} | " + " | ".join(str(c[k]) for k in cols) + f" | {differ}")
w(f"  合计 | {sum(tot[k] for k in cols)} | " + " | ".join(str(tot[k]) for k in cols) + f" | {tot['differ']}")
mod = table["Modifier"]
in_table = mod["only loop08 right"] + mod["only loop04 right"]
w(f"  条文对应表里的是 gold Modifier 只有一份标对的 {in_table} 个；结果不同的 gold 提及在表外还有 {tot['differ'] - in_table} 个")
w(f"  gold 不是 Modifier 的提及：只有 top-4 loop08 标对 {tot['only loop08 right'] - mod['only loop08 right']} 个，"
  f"只有 top-4 loop04 标对 {tot['only loop04 right'] - mod['only loop04 right']} 个")
w("")
w("B. 不对应任何 gold 提及的预测（多标，按标成的类型）：只在一份里出现的个数")
shared = no_gold["loop04"] & no_gold["loop08"]
for n in RUN:
    only = no_gold[n] - shared
    by = Counter(x[3] for x in only)
    w(f"  只在 {NAME[n]} 里：{len(only)} 个（" + "，".join(f"{lab} {by[lab]}" for lab in LABELS if by[lab]) + "）")
w(f"  两份都有：{len(shared)} 个")
w("")


def ctx(d, s, e, width=45):
    t = texts[d]
    return (t[max(0, s - width):s] + "[[" + t[s:e] + "]]" + t[e:e + width]).replace("\n", " ")


def how(n, g):
    out = []
    for r in run_rows[n]:
        if r["gold_start"] and (r["doc"], int(r["gold_start"]), int(r["gold_end"])) == g:
            out.append("没标" if r["kind"] == "missed" else
                       f"{r['kind']}：标成 {r['pred_label']} '{r['pred_text']}'" if r["pred_start"] else r["kind"])
    return "；".join(out)


# Manual grouping of C1 and C2 by construction, keyed by (doc, gold text for C1 / predicted text for C2).
# The second field says whether the construction is one of the seven situations of the clause table for the 42
# (11/11 reply): brackets, undefined short form, disease short form used as or in a gene name, order of Modifier against
# Composite and DiseaseClass, -deficient, protein, and identical wording (male, bare tumor).
TABLE, NEW = "条文对应表里的场合", "条文对应表里没有的场合"
GROUP = {
    ("8640236", "tumour"): ("单独的 tumour 接名词（tumour types）", TABLE),
    ("8968716", "breast and 79 ovarian cancer"): ("Modifier 和 Composite、DiseaseClass 哪个先判", TABLE),
    ("8968760", "cancer"): ("Modifier 和 Composite、DiseaseClass 哪个先判", TABLE),
    ("8673132", "Dmpk deficient"): ("-deficient 修饰别的名词，这里 gold 不标", TABLE),
    ("8894695", "doubly-deficient"): ("-deficient 修饰别的名词，这里 gold 不标", TABLE),
    ("8808605", "enzyme-deficient"): ("-deficient 修饰别的名词，这里 gold 不标", TABLE),
    ("8673131", "DM"): ("病名缩写用在基因名里（DM-protein kinase），这里 gold 不标", TABLE),
    ("8968716", "breast , ovarian , or other cancers"): ("history of 后面的病名", NEW),
    ("9012404", "cancer"): ("history of 后面的病名", NEW),
    ("9145677", "breast cancer"): ("history of 后面的病名", NEW),
    ("9145677", "ovarian cancer"): ("history of 后面的病名", NEW),
    ("9195227", "cancer"): ("history of 后面的病名", NEW),
    ("8954016", "multiple endocrine neoplasia ( MEN ) types 1 and 2"): ("带括号缩写和型号的长病名怎么切", NEW),
    ("8954016", "MEN"): ("带括号缩写和型号的长病名怎么切", NEW),
    ("9271438", "von Hippel-Lindau tumor"): ("病名接 tumor suppressor gene 时 tumor 算不算进范围", NEW),
    ("9083764", "SJS"): ("病名缩写接 type 编号（SJS type 1A）", NEW),
    ("8644703", "early-onset"): ("early onset 这类发病年龄词", NEW),
    ("8968716", "early onset"): ("early onset 这类发病年龄词", NEW),
    ("8666397", "scurfy"): ("小鼠突变品系名 scurfy (sf)", NEW),
    ("8666397", "sf"): ("小鼠突变品系名 scurfy (sf)", NEW),
    ("8786135", "AT"): ("文中定义过的缩写接 region，这里 gold 不标", NEW),
}
grouped: list[tuple[str, str]] = []

w("C. 单看 Modifier，条文对应表（gold Modifier 只有一份标对的 42 个）以外的差别")
both_diff = [g for g, lab in gold.items() if lab == "Modifier" and state("loop04", g) and state("loop08", g)
             and state("loop04", g) != state("loop08", g)]
w(f"  C1. gold 是 Modifier、两份都错但错法不同：{len(both_diff)} 个")
for g in both_diff:
    grouped.append(GROUP[(g[0], texts[g[0]][g[1]:g[2]])])
    w(f"  - {g[0]} '{texts[g[0]][g[1]:g[2]]}'  top-4 loop04 {how('loop04', g)}；top-4 loop08 {how('loop08', g)}")
    w(f"      {ctx(*g)}")
wrong_mod: dict[str, dict] = {n: {} for n in RUN}
for n in RUN:
    on_gold_mod = {(r["doc"], r["pred_start"], r["pred_end"]) for r in run_rows[n] if r["gold_label"] == "Modifier"}
    for r in run_rows[n]:
        key = (r["doc"], r["pred_start"], r["pred_end"])
        if r["pred_label"] == "Modifier" and r["gold_label"] != "Modifier" and key not in on_gold_mod:
            wrong_mod[n][key] = r
w("  C2. 标成 Modifier、但 gold 不是 Modifier 的预测，只在一份里出现（落在别的类型的 gold 上，或不对应任何 gold）")
for n in RUN:
    other = "loop08" if n == "loop04" else "loop04"
    only = sorted(set(wrong_mod[n]) - set(wrong_mod[other]), key=lambda k: (k[0], int(k[1])))
    by = Counter(wrong_mod[n][k]["gold_label"] for k in only)
    w(f"  只在 {NAME[n]} 里：{len(only)} 个（" + "，".join(f"gold {lab} {c}" for lab, c in sorted(by.items())) + "）")
    for k in only:
        r = wrong_mod[n][k]
        grouped.append(GROUP[(k[0], r["pred_text"])])
        gold_part = f"gold {r['gold_label']} '{r['gold_text']}'" if r["gold_start"] else "不对应任何 gold"
        w(f"  - {k[0]} '{r['pred_text']}'  {gold_part}；{NAME[other]} {how(other, (r['doc'], int(r['gold_start']), int(r['gold_end']))) or '标对' if r['gold_start'] else '没有这个预测'}")
        w(f"      {ctx(k[0], int(k[1]), int(k[2]))}")
w(f"  两份都有：{len(set(wrong_mod['loop04']) & set(wrong_mod['loop08']))} 个")
w(f"  C3. C1、C2 共 {len(grouped)} 个，按写法人工分组")
for where in (TABLE, NEW):
    sel = Counter(name for name, wh in grouped if wh == where)
    w(f"  {where}：{sum(sel.values())} 个")
    for name, c in sel.most_common():
        w(f"    {name}：{c}")
w("")
w("PASS：gold Modifier 只有 top-4 loop08 标对 33 个、只有 top-4 loop04 标对 9 个，与 pair_vs_original_output.txt D 节一致。")

dest = HERE / "overall_view" / "pair_all_diff_output.txt"
with dest.open("w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
