"""top-4 loop08 against top-4 loop04, Modifier only (11/11). Three steps, as the user set them:

1. Reserve: both guidelines read in full, line by line (not a keyword search), keeping every passage that defines when
   a disease expression is a Modifier, excludes it from Modifier, ranks Modifier against another label, or gives an
   example of one of these. Passages read and left out because they apply to every label or decide another label
   (gender, general terms, abbreviations, Composite coordination, the general precedence principle) are listed in
   section A with the reason. Check: every line containing the label word "Modifier" is in the reserve.
2. For each of the 69 Modifier annotation differences (pair_all_diff.py), the guideline text that the reasons of the
   predictions involved actually cite (codex_locate, role basis), looked up in the reserve.
3. The differences grouped by which reserve passages each guideline's reasons cite, so the cited texts of the two
   guidelines can be compared side by side.
Offline, no API calls. Run from the repository root. Writes outputs/overall_view/pair_modifier_cited_text_output.txt.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
LOC = HERE / "bar_clause_pilot" / "codex_locate"
RUN = {"loop08": "20261022_haiku-xhigh_topk4_loop08", "loop04": "20261022_haiku-xhigh_topk4_loop04"}
NAME = {"loop08": "top-4 loop08", "loop04": "top-4 loop04"}
lines = {n: (LOC / "inputs" / "guidelines" / f"top4_{n}.txt").read_text(encoding="utf-8").split("\n") for n in RUN}

# 1. reserve: (first line, last line, what the passage says about Modifier)
RESERVE = {
    "loop08": [
        (17, 17, "优先级：修饰非疾病名词的病名归第 3 节标 Modifier，第 1 节的指称测试和基因定义条款不管它"),
        (36, 37, "第 3 节定义：病名修饰名词短语时标 Modifier"),
        (39, 44, "第 3 节例子：colorectal cancer、HNPCC 标 Modifier"),
        (46, 48, "条件：病名修饰非疾病名词就标 Modifier，优先于第 1、7 节；第 47 行列 case、patient、family、gene 等名词，第 48 行 history of 的宾语"),
        (50, 50, "排除：只在起修饰作用时标；病名本身是中心词或完整实体时按第 1、7 节"),
        (52, 53, "条件和排除：命名里的病名（全称或文中定义的缩写）修饰非疾病名词时标 Modifier；病名本身是中心词、命名里没有病名、缩写文中没定义时不标"),
        (55, 55, "排除：with、has 后面的病名，以及被描述某一型、某一形式的病名，标 Specific"),
        (89, 89, "条件：形容词性的缺乏词（[enzyme]-deficient）标 Modifier"),
        (159, 159, "优先级：Modifier 先于 Specific、DiseaseClass，history 框架也是；病名本身是中心词时不是 Modifier"),
        (165, 165, "优先级：[enzyme]-deficient 标 Modifier，不是 Specific"),
        (233, 234, "例 20：the classical form of Coats disease 的 Coats disease 标 Specific（第 55 行排除的例子）"),
        (236, 237, "例 21：family history of ovarian cancer 和 ovarian cancer cases 的病名都标 Modifier"),
        (239, 240, "例 22：kindreds with SLS 的 SLS 标 Specific，不是修饰"),
        (242, 243, "例 23：Norrie disease gene 的 Norrie disease 标 Modifier"),
        (257, 259, "例 27：括号里定义的 DTD 标 Specific；DTD gene 的 DTD 标 Modifier"),
    ],
    "loop04": [
        (38, 38, "条件：缺乏词修饰别的名词标 Modifier（G6PD-deficient phenotype、deficient patients）"),
        (39, 39, "排除：否定或正常状态的形容词（non-deficient、normal）标 O"),
        (44, 44, "优先级：修饰用法是 Modifier，不进第 1b 节的测试"),
        (53, 53, "优先级：修饰用法是 Modifier，不是 Specific"),
        (78, 78, "条件：early onset 这类单独的严重度、发病、时间限定语标 Modifier"),
        (96, 96, "转介：共用 cancer 的并列病名不按并列修饰词规则，按第 1b、3 节判；多病并列按 Composite"),
        (102, 103, "第 3 节定义：病名修饰名词短语时标 Modifier；带专名也一样，第 1b 节的测试不推翻"),
        (105, 110, "第 3 节例子：colorectal cancer、HNPCC 标 Modifier"),
        (112, 118, "条件和排除：病名紧挨名词才标 Modifier，否则（隔括号、标点、分词、动词、介词或后面没有词）标 Specific，缩写跟全称；不能只凭后面名词的意思判；DiseaseClass、Composite 先判；history of 的病名标 Specific"),
        (120, 120, "条件：gene、locus 前的病名或定义过的缩写标 Modifier；基因符号不标"),
        (122, 127, "例子和排除：BRCA1、SLS genes；病名本身是中心词、缩写没定义也没公认所指、基因符号、非疾病修饰词时不适用"),
        (145, 145, "条件：缩写跟全称的类型（第 3 节）"),
        (187, 188, "排除：否定的缺乏形容词 non-deficient 标 O"),
        (190, 192, "排除和例外：基因层面不标；修饰它们的病名标 Modifier"),
        (203, 203, "优先级：修饰用法先标 Modifier"),
        (207, 207, "优先级：基因层面不标，除非病名修饰它们"),
        (281, 282, "例 21：Sjogren-Larsson syndrome (SLS) 后面跟括号，标 Specific，缩写跟全称（第 114 行的例子）"),
        (288, 290, "例 22：Wiskott-Aldrich syndrome protein 的病名标 Modifier，WASP 标 O"),
        (292, 294, "例 23：family history of ovarian cancer 标 Specific，cases、risk 前标 Modifier"),
        (296, 298, "例 24：breast cancer susceptibility gene 1 的 breast cancer 标 Modifier"),
        (300, 302, "例 25：G6PD deficient phenotype 标 Modifier，non-deficient 标 O"),
        (308, 309, "例 27：Coats telangiectasis 后面跟 is，标 Specific（第 114 行的例子）"),
        (316, 317, "例 29：Coats' disease 后面跟 of，标 Specific（第 114 行的例子）"),
        (322, 324, "例 30：fragile X syndrome patients 标 Modifier"),
    ],
}
LEFT_OUT = {
    "loop08": [
        (11, 11, "基因定义的疾病标 Specific；第 17 行已说修饰用法不受它管"),
        (29, 29, "Composite 的定义：并列的病名作为一个提及"),
        (75, 75, "缩写和全称分成两个提及，没说类型"),
        (126, 129, "性别词不进范围，对所有类型都适用"),
        (134, 137, "笼统词不标；cancer、tumor 保留，对所有类型都适用"),
        (157, 157, "通用优先原则：窄的规则先用"),
        (175, 178, "例 2：early onset 算不算进病名范围"),
    ],
    "loop04": [
        (87, 87, "Composite 的定义"),
        (92, 94, "并列修饰词共用病理中心词时标 Composite，说的不是病名作修饰语"),
        (160, 163, "性别词不进范围，对所有类型都适用"),
        (168, 171, "笼统词不标；cancer、tumor 保留，对所有类型都适用"),
        (201, 201, "通用优先原则：窄的规则先用"),
        (209, 209, "并列修饰词先于症状规则，说的是 Composite"),
        (219, 222, "例 2：early onset 算不算进病名范围"),
    ],
}


def in_reserve(n, lo, hi):
    return [r for r in RESERVE[n] if r[0] <= hi and lo <= r[1]]


def heading(n, i):
    for k in range(i - 1, -1, -1):
        if lines[n][k].startswith("#"):
            return lines[n][k].lstrip("# ").replace("**", "").strip()
    return ""


def rid(r):
    return f"{r[0]}" if r[0] == r[1] else f"{r[0]}-{r[1]}"


# 2. the 69 differences and the text their reasons cite
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
    if g not in err[n]:
        return [(g[0], g[1], g[2], gold[g])]
    return [(r["doc"], int(r["pred_start"]), int(r["pred_end"]), r["pred_label"]) for r in err[n][g] if r["pred_start"]]


diffs = []  # (who is right, description, {run: [prediction keys]})
for g, lab in gold.items():
    if lab == "Modifier" and state("loop08", g) != state("loop04", g):
        s8, s4 = state("loop08", g), state("loop04", g)
        right = "loop08" if s8 is None else "loop04" if s4 is None else "neither"
        diffs.append((right, f"{g[0]} gold Modifier '{texts[g[0]][g[1]:g[2]]}'", {n: preds_on_gold(n, g) for n in RUN},
                      (g[0], texts[g[0]][g[1]:g[2]])))
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
            keys[other] = preds_on_gold(other, (r["doc"], int(r["gold_start"]), int(r["gold_end"])))
            where = f"gold {r['gold_label']} '{r['gold_text']}'"
        else:
            keys[other] = []
            where = "不对应任何 gold"
        diffs.append((other, f"{r['doc']} {NAME[n]} 标成 Modifier '{r['pred_text']}'（{where}）", keys, (r["doc"], r["pred_text"])))
assert len(diffs) == 69

basis: dict[tuple, list] = {}
for n in RUN:
    for line in (LOC / "outputs" / f"top4_{n}_locate.jsonl").open(encoding="utf-8"):
        x = json.loads(line)
        _, d, s, e, lab = x["pred_id"].split("|")
        basis[(n, d, int(s), int(e), lab)] = sorted({(q["line_start"], q["line_end"]) for q in x["quotes"] if q["role"] == "basis"})

items = []
outside = {n: Counter() for n in RUN}
for right, desc, keys, key in diffs:
    side = {}
    detail = {}
    for n in RUN:
        if not keys[n]:
            side[n], detail[n] = ("没有预测",), "没有预测"
            continue
        ids, parts = set(), []
        for k in keys[n]:
            bl = basis.get((n,) + k)
            if bl is None:
                parts.append(f"{k[3]} '{texts[k[0]][k[1]:k[2]]}'：理由没有定位")
                continue
            refs = []
            for lo, hi in bl:
                hit = in_reserve(n, lo, hi)
                ids.update(rid(r) for r in hit)
                if not hit:
                    outside[n][(lo, hi, heading(n, lo))] += 1
                refs.append((f"{lo}" if lo == hi else f"{lo}-{hi}") + ("" if hit else "（备用之外）"))
            parts.append(f"{k[3]} '{texts[k[0]][k[1]:k[2]]}'：引 " + "、".join(refs))
        side[n] = tuple(sorted(ids, key=lambda x: int(x.split("-")[0]))) or (("理由没有定位",) if all(
            "没有定位" in p for p in parts) else ("只引备用之外",))
        detail[n] = "；".join(parts)
    items.append((right, desc, side, detail, key))

RIGHT = {"loop08": "top-4 loop08 对", "loop04": "top-4 loop04 对", "neither": "都不对"}
out: list[str] = []
w = out.append
w("top-4 loop08 与 top-4 loop04：Modifier 标注不同的地方，两份理由各自引用的 Modifier 相关原文（2026-11-11，离线）")
w("")
w("A. 备用：逐行通读两份全文，与 Modifier 标签有关的全部段落（行号从 1 起；凡含 Modifier 一词的行都在内）")
for n in RUN:
    w(f"  {NAME[n]}：{len(RESERVE[n])} 段，共 {sum(r[1] - r[0] + 1 for r in RESERVE[n])} 行")
    for r in RESERVE[n]:
        w(f"    第 {rid(r)} 行：{r[2]}")
    covered = {i for r in RESERVE[n] for i in range(r[0], r[1] + 1)}
    assert all(i in covered for i, x in enumerate(lines[n], 1) if "Modifier" in x), n
    w("    读过、没收进备用的段落（对所有类型都适用，或决定的是别的类型）：")
    for r in LEFT_OUT[n]:
        w(f"      第 {rid(r)} 行：{r[2]}")
w("")
w("B. 69 处标注不同的地方，理由所引原文落在备用里还是备用之外（按引用次数）")
for n in RUN:
    w(f"  {NAME[n]} 引到备用之外的行：" + "；".join(f"第 {lo if lo == hi else f'{lo}-{hi}'} 行（{h}）{c} 次"
                                              for (lo, hi, h), c in sorted(outside[n].items())))
w("")
w("C. 按两份理由各自引用的备用段落分组（每组：top-4 loop08 引的段落 | top-4 loop04 引的段落）")
groups = defaultdict(list)
for it in items:
    groups[(it[2]["loop08"], it[2]["loop04"])].append(it)
for (k8, k4), its in sorted(groups.items(), key=lambda x: -len(x[1])):
    cnt = Counter(it[0] for it in its)
    w(f"  ## top-4 loop08 引 {'、'.join(k8)} | top-4 loop04 引 {'、'.join(k4)}：{len(its)} 处（" +
      "，".join(f"{RIGHT[r]} {cnt[r]}" for r in RIGHT if cnt[r]) + "）")
    for right, desc, side, detail, key in its:
        w(f"  - {desc}  [{RIGHT[right]}]")
        w(f"      top-4 loop08：{detail['loop08']}")
        w(f"      top-4 loop04：{detail['loop04']}")

# 3. how the two guidelines' texts differ for each difference. Rows are written by reading the cited reserve passages
# of both guidelines; where one guideline cites nothing (no prediction, or its reason was not located), its passage on
# the same construction is looked up in its reserve. Keyed by (doc, gold text) or, for wrong Modifier predictions,
# (doc, predicted text).
ROWS = {
    "1a": ("两份都有规定，答案相反", "病名和后面的名词之间隔着括号缩写",
           "第 46-48 行只看是否修饰非疾病名词；第 52-53 行定义过的缩写也标 Modifier",
           "第 112-118 行必须紧挨，隔着括号就标 Specific；第 145 行缩写跟全称走"),
    "1b": ("两份都有规定，答案相反", "history of 后面的病名", "第 48 行、例 21（第 236-237 行）标 Modifier",
           "第 118 行、例 23（第 292-294 行）标 Specific"),
    "1c": ("两份都有规定，答案相反", "文中没定义过的缩写", "第 53 行 (c)：不能凭位置标 Modifier",
           "第 125 行 (b)：文中有公认所指就标"),
    "1d": ("两份都有规定，答案相反", "病名缩写接 type 编号", "第 55 行：描述疾病的某一型时，病名标 Specific",
           "第 113 行：紧挨名词就标 Modifier"),
    "2a": ("一份写明，另一份前后矛盾", "定义过的病名缩写同时是基因名，或用在基因名里", "例 27（第 257-259 行）：DTD gene 的 DTD 标 Modifier",
           "第 120 行前半句标 Modifier，末句和第 191 行说基因符号不标"),
    "2b": ("一份只写一半，另一份前后矛盾", "Modifier 和 Composite、DiseaseClass 哪个先判",
           "第 159 行 Modifier 先于 DiseaseClass；和 Composite 哪个先没写",
           "第 117 行 Composite、DiseaseClass 先判；第 96、203 行又让并列的 cancer 和修饰用法走 Modifier"),
    "2c": ("只有一份有规定", "early onset 这类发病、时间限定语", "没有", "第 78 行：标 Modifier"),
    "3a": ("两份规定一样，宽窄不同", "-deficient 修饰别的名词", "第 89、165 行：[enzyme]-deficient 标 Modifier",
           "第 38 行：任何缺乏词修饰别的名词都标 Modifier"),
    "3b": ("两份规定一样", "病名紧挨普通名词", "第 46-48 行：标 Modifier", "第 112-118 行：标 Modifier"),
    "3c": ("两份规定一样", "范围：male、Familial 算不算进去", "第 127 行（性别，备用之外）", "第 160-161 行（性别，备用之外），与 top-4 loop08 同一句"),
    "4": ("两份都没有引文", "按写法也归不进上面任何一行", "", ""),
}
ASSIGN = {}
for row, keys in {
    "1a": [("8776595", "Emery-Dreifuss muscular dystrophy"), ("8776595", "EMDM"), ("8782829", "hereditary nonpolyposis colorectal cancer"),
           ("8782829", "HNPCC"), ("8808606", "myotonic dystrophy"), ("8808606", "DM"), ("8931709", "adenomatous polyposis coli"),
           ("8659522", "HD")],
    "1b": [("8968716", "breast , ovarian , or other cancers"), ("9012404", "cancer"), ("9145677", "breast cancer"),
           ("9145677", "ovarian cancer"), ("9195227", "cancer")],
    "1c": [("8776595", "EDMD")],
    "1d": [("9083764", "SJS")],
    "2a": [("8733131", "VHL"), ("8673131", "DM")],
    "2b": [("8644702", "breast and ovarian cancer"), ("8644702", "breast-ovarian cancer"), ("8968716", "breast and ovarian cancer"),
           ("8700509", "breast / ovarian cancer"), ("8968716", "breast and 79 ovarian cancer"), ("8968716", "cancer"),
           ("8968760", "cancer"), ("8640236", "tumour")],
    "2c": [("8644703", "early-onset"), ("8968716", "early onset")],
    "3a": [("8917548", "Atm-deficient"), ("8673132", "Dmpk deficient"), ("8894695", "doubly-deficient"), ("8808605", "enzyme-deficient")],
    "3b": [("8640236", "pancreatic tumour"), ("8644702", "tumor"), ("8651278", "tumor"), ("9195227", "tumour"), ("8931701", "WAS"),
           ("8786135", "AT"), ("8666397", "scurfy"), ("8666397", "sf")],
    "3c": [("9012404", "male breast cancer"), ("8644703", "Ovarian Cancer")],
    "4": [("9271438", "von Hippel-Lindau tumor"), ("8954016", "multiple endocrine neoplasia ( MEN ) types 1 and 2"), ("8954016", "MEN")],
}.items():
    for k in keys:
        assert k not in ASSIGN, k
        ASSIGN[k] = row
assert all(it[4] in ASSIGN for it in items) and len(ASSIGN) == len({it[4] for it in items})
REAL = lambda side: side[0] not in ("没有预测", "理由没有定位", "只引备用之外")
w("")
w("D. 两份引用的原文怎样不同（行号前为 top-4 loop08，后为 top-4 loop04；另一份没有引文时，按写法在它的备用里查）")
cover = Counter(sum(REAL(it[2][n]) for n in RUN) for it in items)
w(f"  两份理由都引到备用的 {cover[2]} 处，只有一份引到的 {cover[1]} 处，两份都没引到的 {cover[0]} 处")
w("  模式 | 写法 | top-4 loop08 的原文 | top-4 loop04 的原文 | 处数 | " + " | ".join(RIGHT.values()))
by_kind = defaultdict(Counter)
for row, (kind, what, t8, t4) in ROWS.items():
    sel = [it for it in items if ASSIGN[it[4]] == row]
    cnt = Counter(it[0] for it in sel)
    by_kind[kind].update(cnt)
    w(f"  {kind} | {what} | {t8} | {t4} | {len(sel)} | " + " | ".join(str(cnt[r]) for r in RIGHT))
    for right, desc, side, detail, key in sel:
        tag = {2: "两份都有引文", 1: "一份有引文", 0: "两份都没有引文"}[sum(REAL(side[n]) for n in RUN)]
        w(f"      - {desc}  [{RIGHT[right]}；{tag}]")
w("  按模式合计：")
for kind, cnt in by_kind.items():
    w(f"    {kind}：{sum(cnt.values())} 处，" + "，".join(f"{RIGHT[r]} {cnt[r]}" for r in RIGHT))
w("")
w("E. 拆到柱子上：Modifier 柱子只算标对的 gold Modifier，所以柱高差 24 = 只有 top-4 loop08 标对的 33 个 - 只有 top-4 loop04 标对的 9 个；")
w("   标成 Modifier 的错误预测不进柱子，但进柱子下面的 Modifier F1，另列；两份都没标对的不影响两者")


def split(it):
    right, desc = it[0], it[1]
    if right == "neither":
        return "都没标对"
    if " gold Modifier " in desc:
        return f"柱子：只有 {NAME[right]} 标对"
    return f"错标：只在 {NAME['loop04' if right == 'loop08' else 'loop08']}"


COLS = ["柱子：只有 top-4 loop08 标对", "柱子：只有 top-4 loop04 标对", "错标：只在 top-4 loop08", "错标：只在 top-4 loop04", "都没标对"]
w("  模式 | 写法 | " + " | ".join(COLS))
tot = Counter()
kind_tot = defaultdict(Counter)
for row, (kind, what, t8, t4) in ROWS.items():
    cnt = Counter(split(it) for it in items if ASSIGN[it[4]] == row)
    tot.update(cnt)
    kind_tot[kind].update(cnt)
    w(f"  {kind} | {what} | " + " | ".join(str(cnt[c]) for c in COLS))
w("  合计 | | " + " | ".join(str(tot[c]) for c in COLS))
assert tot[COLS[0]] == 33 and tot[COLS[1]] == 9
w("  按模式合计：")
for kind, cnt in kind_tot.items():
    w(f"    {kind}：" + "，".join(f"{c} {cnt[c]}" for c in COLS))

dest = HERE / "overall_view" / "pair_modifier_cited_text_output.txt"
with dest.open("w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
