"""top-4 loop04 and top-4 loop08 against the original guideline: which gold Modifier mentions each newly gets right,
which guideline lines the model's reasons point to, and which of them make up the gap between the two bars (11/11).

Offline, no API calls. Inputs are saved artifacts only: validation gold, error_rows.csv (all 30 validation runs), and
the codex_locate results (the guideline lines each saved prediction's reason relies on, role "basis").

Bands follow report section 5: the original guideline "almost always gets a mention right" at >=15 of 19 runs and
"almost always gets it wrong" at <=4 of 19 runs; 5 to 14 means it flips by itself.
  newly right = original <=4/19 and this guideline right;  newly wrong = original >=15/19 and this guideline wrong.
Each bar equals the sum over the 218 gold Modifiers of (this guideline right ? 1 : 0) - (original runs right)/19.
Run from the repository root. Writes outputs/overall_view/pair_vs_original_output.txt.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
LOC = ROOT / "nodes/2026-11-06_seminar/error-analysis/outputs" / "bar_clause_pilot" / "codex_locate"
RUN = {"loop04": "20261022_haiku-xhigh_topk4_loop04", "loop08": "20261022_haiku-xhigh_topk4_loop08"}
NAME = {"loop04": "top-4 loop04", "loop08": "top-4 loop08"}

texts: dict[str, str] = {}
gold: list[tuple[str, int, int]] = []
for path in sorted(VALID.glob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    texts[doc["sourceid"]] = doc["text"]
    gold += [(doc["sourceid"], a["span"]["begin"], a["span"]["end"]) for a in doc["denotations"] if a["obj"] == "Modifier"]
assert len(gold) == 218 == len(set(gold))

rows = list(csv.DictReader((ROOT / "nodes/shared/error-analysis/outputs" / "error_rows.csv").open(encoding="utf-8")))
orig_runs = sorted({r["run"] for r in rows if r["guideline"] == "original"})
assert len(orig_runs) == 19
err: dict[str, dict] = defaultdict(lambda: defaultdict(list))
for r in rows:
    if r["gold_label"] == "Modifier" and r["gold_start"]:
        err[r["run"]][(r["doc"], int(r["gold_start"]), int(r["gold_end"]))].append(r)

k = {g: sum(g not in err[run] for run in orig_runs) for g in gold}  # original runs that got g right
right = {n: {g for g in gold if g not in err[run]} for n, run in RUN.items()}
assert len(right["loop08"]) == 161 and len(right["loop04"]) == 137
tables = json.loads((ROOT / "nodes/shared/error-analysis/outputs" / "loop_label_tables.json").read_text(encoding="utf-8"))

basis: dict[tuple, list[tuple[int, int]]] = {}
for n in RUN:
    for line in (LOC / "outputs" / f"top4_{n}_locate.jsonl").open(encoding="utf-8"):
        x = json.loads(line)
        _, d, s, e, lab = x["pred_id"].split("|")
        basis[(n, d, int(s), int(e), lab)] = sorted({(q["line_start"], q["line_end"]) for q in x["quotes"] if q["role"] == "basis"})
reason: dict[tuple, str] = {}
for n in RUN:
    for line in (LOC / "inputs" / f"top4_{n}_predictions.jsonl").open(encoding="utf-8"):
        p = json.loads(line)
        reason[(n, p["doc"], p["pred_start"], p["pred_end"], p["pred_label"])] = p["rationale"]


def band(g):
    return "orig_wrong" if k[g] <= 4 else ("orig_right" if k[g] >= 15 else "flips")


def cites(lines, n):
    return any(a <= n <= b for a, b in lines)


def fmt_lines(lines):
    return "、".join(f"{a}" if a == b else f"{a}-{b}" for a, b in lines)


def cite(lines):
    return f"理由引第 {fmt_lines(lines)} 行" if lines else "理由没有定位结果"


def ctx(g, w=45):
    d, s, e = g
    t = texts[d]
    return (t[max(0, s - w):s] + "[[" + t[s:e] + "]]" + t[e:e + w]).replace("\n", " ")


def wrong_pred(n, g):
    """How guideline n got gold g wrong, and the basis lines of that prediction if one exists."""
    out = []
    for r in err[RUN[n]][g]:
        if r["kind"] == "missed":
            out.append("没标")
        else:
            key = (n, r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"])
            out.append(f"{r['kind']}：标成 {r['pred_label']} '{r['pred_text']}'，{cite(basis.get(key, []))}")
    return "；".join(out)


def group_gain(n, lines):
    if n == "loop04":
        if cites(lines, 120):
            return "引第 120 行：gene 前的病名或文中定义过的缩写标 Modifier"
        if cites(lines, 38):
            return "引第 38 行：-deficient 修饰别的名词标 Modifier"
        assert cites(lines, 113), lines
        return "其余，都引第 113 行：病名紧挨中心名词标 Modifier"
    if cites(lines, 259):
        return "引第 259 行 “DTD” gene 的例子（同时引第 46 行）"
    if cites(lines, 89):
        return "引第 89 行：-deficient 标 Modifier（同时引第 46 行）"
    if cites(lines, 46):
        return "引第 46、47 行：病名修饰非疾病名词就标 Modifier"
    assert lines == [(52, 52)], lines
    return "其余，只引第 52 行：文中命名里的病名标 Modifier"


out: list[str] = []
w = out.append
w("top-4 loop04、top-4 loop08 相对原指南：新标对、新标错的 gold Modifier 与理由引用的指南行（2026-11-11，离线）")
w("")
w("新标对 = 原指南 19 次运行中至多 4 次标对、这份指南标对；新标错 = 原指南至少 15 次标对、这份指南标错（报告第 5 节的界线）。")
w("行号取自 codex_locate 对每个已保存预测的理由所定位的指南行（role 为 basis），行号从 1 起。")
w("")
w("A. 概况：柱高 = 这份指南标对数 - 原指南 19 次平均；按原指南稳定程度拆开，各部分相加等于柱高")
orig_mean = sum(k.values()) / 19
gains: dict[str, list] = {}
for n in RUN:
    bar = len(right[n]) - orig_mean
    assert abs(bar - tables["by_label"][NAME[n]]["Modifier"]["tp"]) < 1e-9
    parts = Counter()
    count = Counter()
    for g in gold:
        parts[(band(g), g in right[n])] += (g in right[n]) - k[g] / 19
        count[(band(g), g in right[n])] += 1
    assert abs(sum(parts.values()) - bar) < 1e-9
    gains[n] = [g for g in gold if band(g) == "orig_wrong" and g in right[n]]
    w(f"  {NAME[n]}：柱高 {bar:+.2f}")
    for key, label in ((("orig_wrong", True), "新标对（原指南几乎总标错，这份标对）"),
                       (("orig_wrong", False), "原指南几乎总标错，这份也没标对"),
                       (("orig_right", True), "原指南几乎总标对，这份也标对"),
                       (("orig_right", False), "新标错（原指南几乎总标对，这份标错）"),
                       (("flips", True), "原指南自己时对时错，这份标对"),
                       (("flips", False), "原指南自己时对时错，这份没标对")):
        orig_avg = sum(k[g] / 19 for g in gold if band(g) == key[0] and (g in right[n]) == key[1])
        w(f"    {label}：{count[key]} 个，原指南平均每次在其中标对 {orig_avg:.2f} 个，对柱高 {parts[key]:+.2f}")
w("")

for sec, n in (("B", "loop04"), ("C", "loop08")):
    w(f"{sec}. {NAME[n]} 新标对的 {len(gains[n])} 个，按理由引用的行分组（一个提及可引几行，按组的先后归入第一个符合的组）")
    groups = defaultdict(list)
    line_count = Counter()
    for g in gains[n]:
        lines = basis[(n, g[0], g[1], g[2], "Modifier")]
        groups[group_gain(n, lines)].append((g, lines))
        for a, b in lines:
            line_count[(a, b)] += 1
    for gname, items in groups.items():
        w(f"  ## {gname}：{len(items)} 个")
        for g, lines in items:
            w(f"  - {g[0]} {g[1]}-{g[2]} '{texts[g[0]][g[1]:g[2]]}'  原指南 {k[g]}/19  {cite(lines)}")
            w(f"      {ctx(g)}")
            w(f"      理由：{reason[(n, g[0], g[1], g[2], 'Modifier')]}")
    w(f"  各行被引用的提及数：" + "；".join(f"第 {fmt_lines([ab])} 行 {c}" for ab, c in line_count.most_common()))
    lost = [g for g in gold if band(g) == "orig_right" and g not in right[n]]
    w(f"  新标错 {len(lost)} 个：")
    for g in lost:
        w(f"  - {g[0]} '{texts[g[0]][g[1]:g[2]]}'  原指南 {k[g]}/19  {wrong_pred(n, g)}")
        w(f"      {ctx(g)}")
    w("")

w("D. 两份指南结果不同的 gold Modifier：按原指南稳定程度分开，列出对的一方理由引的行和错的一方怎样错")
only = {"loop08": sorted(right["loop08"] - right["loop04"]), "loop04": sorted(right["loop04"] - right["loop08"])}
assert len(only["loop08"]) == 33 and len(only["loop04"]) == 9
for n, other in (("loop08", "loop04"), ("loop04", "loop08")):
    w(f"  只有 {NAME[n]} 标对：{len(only[n])} 个")
    for key, label in (("orig_wrong", f"{NAME[n]} 新标对、{NAME[other]} 没有"),
                       ("orig_right", f"{NAME[other]} 新标错"),
                       ("flips", "原指南自己时对时错")):
        sel = [g for g in only[n] if band(g) == key]
        w(f"  ## {label}：{len(sel)} 个")
        for g in sel:
            lines = basis.get((n, g[0], g[1], g[2], "Modifier"), [])
            w(f"  - {g[0]} '{texts[g[0]][g[1]:g[2]]}'  原指南 {k[g]}/19  {NAME[n]} {cite(lines)}；{NAME[other]}：{wrong_pred(other, g)}")
            w(f"      {ctx(g)}")
both = [g for g in gains["loop04"] if g in gains["loop08"]]
w(f"  两份都新标对的：{len(both)} 个（{'、'.join(texts[g[0]][g[1]:g[2]] for g in both)}）")
assert len(both) + len([g for g in only["loop04"] if band(g) == "orig_wrong"]) == len(gains["loop04"])
assert len(both) + len([g for g in only["loop08"] if band(g) == "orig_wrong"]) == len(gains["loop08"])
w("")
w("PASS：两份指南的柱高与 loop_label_tables.json 一致；各部分相加等于柱高；只有一份标对的 33、9 个与 pair_modifier_tp_diff_output.txt 一致。")

dest = HERE / "overall_view" / "pair_vs_original_output.txt"
with dest.open("w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
