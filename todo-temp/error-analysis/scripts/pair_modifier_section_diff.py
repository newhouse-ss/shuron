"""top-4 loop08 against top-4 loop04, Modifier only (11/11): do the guideline lines behind the Modifier annotation
differences fall in the part of the Modifier section where the two guideline texts differ?

Steps as the user set them:
1. The 69 Modifier annotation differences of pair_all_diff.py: a gold Modifier that one run labels right and the other
   does not (42); a gold Modifier both runs get wrong in different ways (5); a prediction labelled Modifier whose
   gold is not Modifier and that appears in only one run (22).
2. Diff the Modifier section of the two guidelines line by line. The Modifier section is section 3, "Annotate disease
   mentions that are used as Modifiers", up to section 4. Curly quotes become straight quotes and trailing spaces are
   dropped before the diff (typography only).
3. For each difference, the guideline lines that the reasons of the predictions involved rely on (codex_locate, role
   basis). A run that did not predict anything there has no reason; codex_locate covers only predictions that differ
   from the original guideline, so some predictions have no located lines.
4. Whether each cited line is a changed line of the Modifier section, an unchanged line of it, or outside it.
Offline, no API calls. Run from the repository root. Writes outputs/overall_view/pair_modifier_section_diff_output.txt.
"""

from __future__ import annotations

import csv
import difflib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
LOC = HERE / "bar_clause_pilot" / "codex_locate"
RUN = {"loop08": "20261022_haiku-xhigh_topk4_loop08", "loop04": "20261022_haiku-xhigh_topk4_loop04"}
NAME = {"loop08": "top-4 loop08", "loop04": "top-4 loop04"}

# 1. the 69 differences
gold: dict[tuple[str, int, int], str] = {}
texts: dict[str, str] = {}
for path in sorted(VALID.glob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    texts[doc["sourceid"]] = doc["text"]
    for a in doc["denotations"]:
        gold[(doc["sourceid"], a["span"]["begin"], a["span"]["end"])] = a["obj"]
rows = {n: [r for r in csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")) if r["run"] == run]
        for n, run in RUN.items()}
err = {n: defaultdict(list) for n in RUN}
for n in RUN:
    for r in rows[n]:
        if r["gold_start"]:
            err[n][(r["doc"], int(r["gold_start"]), int(r["gold_end"]))].append(r)


def state(n, g):
    return tuple(sorted((r["kind"], r["pred_label"], r["pred_start"], r["pred_end"]) for r in err[n][g])) if g in err[n] else None


def preds_on_gold(n, g):
    """Prediction keys (doc, start, end, label) that run n made on gold mention g."""
    if g not in err[n]:
        return [(g[0], g[1], g[2], gold[g])]
    return [(r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"]) for r in err[n][g] if r["pred_start"]]


diffs = []  # (kind, who is right, description, {run: [prediction keys]})
for g, lab in gold.items():
    if lab != "Modifier":
        continue
    s8, s4 = state("loop08", g), state("loop04", g)
    if s8 == s4:
        continue
    right = "loop08" if s8 is None else "loop04" if s4 is None else "neither"
    kind = "一份标对" if right != "neither" else "都错但错法不同"
    diffs.append((kind, right, f"{g[0]} gold Modifier '{texts[g[0]][g[1]:g[2]]}'", {n: preds_on_gold(n, g) for n in RUN}))
wrong_mod = {n: {} for n in RUN}
for n in RUN:
    on_gold_mod = {(r["doc"], r["pred_start"], r["pred_end"]) for r in rows[n] if r["gold_label"] == "Modifier"}
    for r in rows[n]:
        key = (r["doc"], r["pred_start"], r["pred_end"])
        if r["pred_label"] == "Modifier" and r["gold_label"] != "Modifier" and key not in on_gold_mod:
            wrong_mod[n][key] = r
for n, other in (("loop08", "loop04"), ("loop04", "loop08")):
    for key in sorted(set(wrong_mod[n]) - set(wrong_mod[other])):
        r = wrong_mod[n][key]
        keys = {n: [(r["doc"], int(r["pred_start"]), int(r["pred_end"]), "Modifier")]}
        if r["gold_start"]:
            g = (r["doc"], int(r["gold_start"]), int(r["gold_end"]))
            keys[other] = preds_on_gold(other, g)
            where = f"gold {r['gold_label']} '{r['gold_text']}'"
        else:
            keys[other] = []
            where = "不对应任何 gold"
        diffs.append(("只有一份标成 Modifier 的错标", other, f"{r['doc']} {NAME[n]} 标成 Modifier '{r['pred_text']}'（{where}）", keys))
assert Counter(d[0] for d in diffs) == {"一份标对": 42, "都错但错法不同": 5, "只有一份标成 Modifier 的错标": 22}

# 2. diff of the Modifier section
GL = LOC / "inputs" / "guidelines"
lines = {n: (GL / f"top4_{n}.txt").read_text(encoding="utf-8").split("\n") for n in RUN}


def section3(n):
    ls = lines[n]
    start = next(i for i, x in enumerate(ls) if x.startswith("### 3."))
    end = next(i for i, x in enumerate(ls) if x.startswith("### 4."))
    return start + 1, end  # 1-based first line, last line


def norm(x):
    return x.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").rstrip()


sec = {n: section3(n) for n in RUN}
a = [norm(x) for x in lines["loop04"][sec["loop04"][0] - 1:sec["loop04"][1]]]
b = [norm(x) for x in lines["loop08"][sec["loop08"][0] - 1:sec["loop08"][1]]]
changed = {"loop04": set(), "loop08": set()}
diff_text = []
for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
    if op == "equal":
        for i, j in zip(range(i1, i2), range(j1, j2)):
            diff_text.append(f"  [两份相同] top-4 loop04 第 {sec['loop04'][0] + i} 行 = top-4 loop08 第 {sec['loop08'][0] + j} 行：{a[i]}")
        continue
    for i in range(i1, i2):
        changed["loop04"].add(sec["loop04"][0] + i)
        diff_text.append(f"- [只在 top-4 loop04] 第 {sec['loop04'][0] + i} 行：{a[i]}")
    for j in range(j1, j2):
        changed["loop08"].add(sec["loop08"][0] + j)
        diff_text.append(f"+ [只在 top-4 loop08] 第 {sec['loop08'][0] + j} 行：{b[j]}")

# 3. cited lines and the quoted text itself
basis: dict[tuple, list] = {}
for n in RUN:
    for line in (LOC / "outputs" / f"top4_{n}_locate.jsonl").open(encoding="utf-8"):
        x = json.loads(line)
        _, d, s, e, lab = x["pred_id"].split("|")
        basis[(n, d, int(s), int(e), lab)] = sorted({(q["line_start"], q["line_end"], q["quote"]) for q in x["quotes"]
                                                     if q["role"] == "basis"})


# 4. where the cited text is. A changed line can still contain sentences shared word for word with the other guideline
# (top-4 loop04 line 103 starts with the same two sentences as top-4 loop08 line 37), so inside the Modifier section a
# quote counts as differing text only when it does not occur in the other guideline's Modifier section.
def flat(x):
    return " ".join(norm(x).split())


sec_text = {n: flat(" ".join(lines[n][sec[n][0] - 1:sec[n][1]])) for n in RUN}


def where(n, cited):
    lo, hi, quote = cited
    if not (sec[n][0] <= lo and hi <= sec[n][1]):
        return "以外"
    other = "loop04" if n == "loop08" else "loop08"
    if flat(quote) in sec_text[other]:
        return "相同"
    assert any(k in changed[n] for k in range(lo, hi + 1)), (n, cited)
    return "差异"


CAT = {"差异": "理由引了 Modifier 部分里只有这一份才有的文字", "相同": "理由引的 Modifier 部分文字两份都有，没有引只有一份才有的",
       "以外": "理由引的文字都在 Modifier 部分以外", "无": "没有理由定位（没有预测，或预测不在 codex_locate 里）"}
RIGHT = {"loop08": "top-4 loop08 对", "loop04": "top-4 loop04 对", "neither": "都不对"}
items = []
for kind, right, desc, keys in diffs:
    marks = {}
    refs = {n: set() for n in RUN}
    for n in RUN:
        cited = []
        for k in keys.get(n, []):
            bl = basis.get((n,) + k)
            if bl is None:
                cited.append(f"{k[3]} '{texts[k[0]][k[1]:k[2]]}' 无定位")
            else:
                cited.append(f"{k[3]} '{texts[k[0]][k[1]:k[2]]}' 引 " + "、".join(
                    (f"{q[0]}" if q[0] == q[1] else f"{q[0]}-{q[1]}") + f"（{where(n, q)}）" for q in bl))
                marks.setdefault(n, set()).update(where(n, q) for q in bl)
                refs[n].update((q[0], q[1]) for q in bl if where(n, q) == "差异")
        marks.setdefault(n, set())
        keys[n] = cited or ["没有预测"]
    found = marks["loop08"] | marks["loop04"]
    cat = next((c for c in ("差异", "相同", "以外") if c in found), "无")
    items.append((cat, right, kind, desc, keys, refs))

out: list[str] = []
w = out.append
w("top-4 loop08 与 top-4 loop04：Modifier 标注差异所依据的指南行，是否落在两份 Modifier 部分不同的地方（2026-11-11，离线）")
w("")
w(f"Modifier 部分 = 第 3 节到第 4 节之前：top-4 loop08 第 {sec['loop08'][0]} 至 {sec['loop08'][1]} 行，top-4 loop04 第 {sec['loop04'][0]} 至 {sec['loop04'][1]} 行。")
w("比对前把弯引号换成直引号、去掉行尾空格，只改排版。引文按原句判断：Modifier 部分里的引文在另一份的 Modifier 部分逐字出现，算两份都有。")
w("")
w("A. 总表：69 处标注差异按理由所引的文字分类；一处差异只要有一句引文属于前一类，就归前一类")
w("  类别 | 合计 | " + " | ".join(RIGHT.values()))
for c in ("差异", "相同", "以外", "无"):
    cnt = Counter(it[1] for it in items if it[0] == c)
    w(f"  {CAT[c]} | {sum(cnt.values())} | " + " | ".join(str(cnt[r]) for r in RIGHT))
w("")
w("B. 被引用的、只有一份才有的 Modifier 部分文字（按行号）：引用它的标注差异个数，按这份指南在这些差异上对还是错")
for n in RUN:
    cnt = defaultdict(Counter)
    for cat, right, kind, desc, keys, refs in items:
        for lo, hi in refs[n]:
            cnt[f"{lo}" if lo == hi else f"{lo}-{hi}"]["对" if right == n else "错"] += 1
    w(f"  {NAME[n]}：" + "；".join(f"第 {ln} 行 对 {c['对']}、错 {c['错']}" for ln, c in sorted(cnt.items(), key=lambda x: -sum(x[1].values()))))
w("")
w("C. 逐处标注差异")
for c in ("差异", "相同", "以外", "无"):
    sel = [it for it in items if it[0] == c]
    w(f"  ## {CAT[c]}：{len(sel)} 处")
    for cat, right, kind, desc, keys, refs in sel:
        w(f"  - {desc}  [{kind}，{RIGHT[right]}]")
        for n in RUN:
            w(f"      {NAME[n]}：" + "；".join(keys[n]))
w("")
w("D. 两份 Modifier 部分的逐行比对（- 只在 top-4 loop04，+ 只在 top-4 loop08，其余两份相同）")
out.extend(diff_text)

dest = HERE / "overall_view" / "pair_modifier_section_diff_output.txt"
with dest.open("w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out[:20]))
