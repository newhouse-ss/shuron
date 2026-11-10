"""top-4 loop08 vs top-4 loop04: which gold Modifier mentions make up the 24-TP gap between their Modifier bars (11/10).

Offline, no API calls. Both bars subtract the same 19-run original-guideline mean, so the gap between them equals the
difference in strict Modifier TP of the two single validation runs. This script lists every gold Modifier mention that
one guideline got strictly right and the other did not, with each run's error (from error_rows.csv), how many of the
19 original runs got it right, and the model's stated reason where codex_locate kept one.

The expression groups are a hand-written reading of the mention texts (GROUPS below); the script only checks that they
cover the differing mentions exactly. Quoted guideline lines are checked verbatim against the plain guideline files.
Writes outputs/overall_view/pair_modifier_tp_diff_output.txt.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
VALID = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
LOCATE = HERE / "bar_clause_pilot" / "codex_locate" / "inputs"
RUN = {"loop08": "20261022_haiku-xhigh_topk4_loop08", "loop04": "20261022_haiku-xhigh_topk4_loop04"}

GROUPS = {
    "文中定义过的缩写 VHL 用在 gene、mRNA 等名词前": [
        ("8733131", s) for s in (254, 446, 622, 773, 891, 1049, 1128, 1220, 1431, 1546, 1646, 1725, 1826)],
    "病名后跟括号缩写，再接名词": [
        ("8776595", 693), ("8776595", 729), ("8782829", 288), ("8782829", 332), ("8808606", 128),
        ("8808606", 149), ("8931709", 370), ("8659522", 93)],
    "loop04 先判成 Composite 或 DiseaseClass 的病名（并列病名接名词等）": [
        ("8644702", 133), ("8644702", 1109), ("8644702", 1282), ("8968716", 425), ("8968716", 345),
        ("8700509", 155)],
    "-deficient 形容词修饰 mice、fibroblasts 等": [("8917548", s) for s in (206, 365, 478, 577)],
    "文中没有定义过的缩写（文中定义的是 EMDM，后文写 EDMD）": [("8776595", 879)],
    "病名缩写后接 protein": [("8931701", 271)],
    "找不到条文差别：male breast cancer 接名词": [("9012404", s) for s in (42, 105, 579, 715)],
    "条文差别不确定：单独的 tumour、tumor 接名词": [
        ("8640236", 1442), ("8644702", 1424), ("8651278", 1374), ("9195227", 185)],
    "找不到条文差别：专名里的 Ovarian Cancer 边界": [("8644703", 118)],
}

QUOTES = [  # (guideline, 1-based line of the plain file, verbatim substring)
    ("top4_loop08", 46, "(takes precedence over items 1 and 7)"),
    ("top4_loop08", 46, "A disease-denoting expression is a **Modifier** when it specifies a non-disease head noun rather than naming the disorder itself."),
    ("top4_loop08", 47, "an attributive premodifier of a case, patient, population, sample, study, family/kindred, series, risk, phenotype, gene, or allele noun"),
    ("top4_loop08", 48, "the complement of a history frame"),
    ("top4_loop08", 52, "a short form that the document has explicitly defined as a disease"),
    ("top4_loop08", 52, "label the disease-denoting substring **Modifier**"),
    ("top4_loop08", 53, "(c) a short form has no disease definition in the document, so it is not anchored as a disease reference and cannot be promoted to Modifier by position alone."),
    ("top4_loop08", 89, "The deficiency term is an adjectival modifier that does not head a disease noun phrase (e.g., “[enzyme]-deficient”). Label it **Modifier** (item 3)."),
    ("top4_loop08", 127, "were only included if they specifically identified a new form of the disease."),
    ("top4_loop08", 258, "The defined short form “DTD” in parentheses is **Specific Disease** (item 6)."),
    ("top4_loop08", 259, "“DTD” as a premodifier of “gene” is **Modifier** (item 3, short form defined in the document)."),
    ("top4_loop04", 38, "When the deficiency-type word modifies a different noun, it is attributive and is annotated as **Modifier** (rule 3)"),
    ("top4_loop04", 38, 'The same holds for "deficient patients."'),
    ("top4_loop04", 112, "applies to disease-name spans, full names and short-form aliases"),
    ("top4_loop04", 113, "is **immediately** followed by a common-noun head that it attributively premodifies, with no intervening punctuation, bracket, participle, finite verb, or preposition, **THEN** label the span **Modifier**."),
    ("top4_loop04", 114, "**OTHERWISE**, label the span **Specific Disease**. This covers spans followed by punctuation, a bracket,"),
    ("top4_loop04", 114, "A parenthetical acronym or alias takes the class of its expanded antecedent, judged by the antecedent's syntactic position"),
    ("top4_loop04", 117, "The span is a Disease Class mention or a Composite Mention. Those are resolved by their own definitions before this test is applied."),
    ("top4_loop04", 118, 'In "a family history of ovarian cancer," "ovarian cancer" is **Specific Disease**'),
    ("top4_loop04", 120, "an acronym that the document has already defined as a disease"),
    ("top4_loop04", 120, "The locus designator and any bare gene symbol remain O."),
    ("top4_loop04", 122, 'In "SLS genes," "SLS" is **Modifier**.'),
    ("top4_loop04", 125, "(b) The acronym has no disease definition or established disease referent in the document, so it remains O."),
    ("top4_loop04", 161, "were only included if they specifically identified a new form of the disease."),
    ("top4_loop04", 191, 'gene symbols remain O. Examples include "BRCA1 alterations," "truncating mutations," "FALDH gene," and "WT1 dysfunction."'),
    ("top4_loop04", 289, '"Wiskott-Aldrich syndrome" = **Modifier** (immediately followed by "protein,"'),
]

out: list[str] = []
texts: dict[str, str] = {}
gold: list[tuple[str, int, int]] = []
for path in sorted(VALID.glob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    texts[doc["sourceid"]] = doc["text"]
    for a in doc["denotations"]:
        if a["obj"] == "Modifier":
            gold.append((doc["sourceid"], a["span"]["begin"], a["span"]["end"]))
assert len(gold) == 218

rows = list(csv.DictReader((HERE / "error_rows.csv").open(encoding="utf-8")))
orig_runs = sorted({r["run"] for r in rows if r["guideline"] == "original"})
assert len(orig_runs) == 19
err: dict[str, dict] = defaultdict(lambda: defaultdict(list))  # run -> gold key -> error rows
for r in rows:
    if r["gold_label"] == "Modifier" and r["gold_start"]:
        err[r["run"]][(r["doc"], int(r["gold_start"]), int(r["gold_end"]))].append(r)

tp = {name: {g for g in gold if g not in err[run]} for name, run in RUN.items()}
orig_tp = [len([g for g in gold if g not in err[run]]) for run in orig_runs]
tables = json.loads((HERE / "loop_label_tables.json").read_text(encoding="utf-8"))
assert len(tp["loop08"]) == 161 and len(tp["loop04"]) == 137
assert abs(sum(orig_tp) / 19 - tables["start"]["Modifier"]["tp_mean"]) < 1e-9
for name, key in (("loop08", "top-4 loop08"), ("loop04", "top-4 loop04")):
    assert abs(len(tp[name]) - sum(orig_tp) / 19 - tables["by_label"][key]["Modifier"]["tp"]) < 1e-9

win = sorted(tp["loop08"] - tp["loop04"])
lose = sorted(tp["loop04"] - tp["loop08"])
assert len(win) - len(lose) == 24

mapped = {k: g for g, ks in GROUPS.items() for k in ks}
assert len(mapped) == sum(len(ks) for ks in GROUPS.values())
assert set(mapped) == {(d, s) for d, s, _ in win + lose}, "GROUPS must cover exactly the differing mentions"

reasons = {}
for name in RUN:
    for line in (LOCATE / f"top4_{name}_predictions.jsonl").open(encoding="utf-8"):
        p = json.loads(line)
        reasons[(name, p["doc"], p["pred_start"], p["pred_end"], p["pred_label"])] = p["rationale"]


def n_orig(g):
    return sum(1 for run in orig_runs if g not in err[run])


def state(name, g):
    if g in tp[name]:
        s, e, label = g[1], g[2], "Modifier"
        desc = "标对"
    else:
        r = err[RUN[name]][g][0]
        if not r["pred_start"]:
            return "没标（真正漏标）", None
        s, e, label = int(r["pred_start"]), int(r["pred_end"]), r["pred_label"]
        desc = f"{r['kind']}：标成 {label} '{r['pred_text']}'"
    why = reasons.get((name, g[0], s, e, label))
    return desc, why


def ctx(g, w=60):
    t = texts[g[0]]
    return (t[max(0, g[1] - w):g[1]] + "[[" + t[g[1]:g[2]] + "]]" + t[g[2]:g[2] + w]).replace("\n", " ")


out.append("top-4 loop08 与 top-4 loop04：逐个 gold Modifier 的标对差别（2026-11-10，离线）")
out.append("")
out.append(f"gold Modifier 218 个；严格标对 loop08 {len(tp['loop08'])}，loop04 {len(tp['loop04'])}，差 {len(tp['loop08']) - len(tp['loop04'])}。")
out.append(f"loop08 标对而 loop04 没标对：{len(win)}；loop04 标对而 loop08 没标对：{len(lose)}。")
out.append(f"原指南 19 次运行的 Modifier 标对数：{sorted(orig_tp)}；最小 {min(orig_tp)}，最大 {max(orig_tp)}，平均 {sum(orig_tp) / 19:.3f}。")
out.append("PASS：标对数与 loop_label_tables.json 的起点均值和两份指南的变化量一致；分组恰好覆盖全部差别。")
out.append("")
out.append("A. 按表达分组：loop08 对 loop04 错 / loop04 对 loop08 错 / 净差")
total = 0
for g, ks in GROUPS.items():
    w = sum(1 for d, s, _ in win if (d, s) in ks)
    l = sum(1 for d, s, _ in lose if (d, s) in ks)
    total += w - l
    out.append(f"  {g}：{w} / {l} / {w - l:+d}")
out.append(f"  合计净差：{total:+d}")
assert total == 24

out.append("")
out.append("B. 逐个提及（原指南 = 19 次原指南运行中标对的次数；理由 = codex_locate 输入里保存的模型自述，没有则不列）")
for g, ks in GROUPS.items():
    out.append(f"\n## {g}")
    for key in sorted(k for k in win + lose if (k[0], k[1]) in ks):
        side = "loop08 对、loop04 错" if key in win else "loop04 对、loop08 错"
        out.append(f"- {key[0]} {key[1]}-{key[2]} '{texts[key[0]][key[1]:key[2]]}'  [{side}]  原指南 {n_orig(key)}/19")
        out.append(f"    {ctx(key)}")
        for name in ("loop08", "loop04"):
            desc, why = state(name, key)
            out.append(f"    {name}：{desc}" + (f"  理由：{why}" if why else ""))

out.append("")
out.append("C. 同一篇文档里同一个病名，有括号和没有括号时 loop04 的标法（gold 都是 Modifier）")
for doc, spans in (("8808606", (81, 128, 149)), ("8776595", (4, 693, 729)), ("8659522", (73, 93))):
    for s in spans:
        key = next(k for k in gold if k[0] == doc and k[1] == s)
        out.append(f"  {doc} '{texts[doc][key[1]:key[2]]}'：loop04 {state('loop04', key)[0]}；loop08 {state('loop08', key)[0]}  | {ctx(key, 40)}")

out.append("")
out.append("D. 家族史短语后的非 Modifier gold 被标成 Modifier（只影响 Modifier 错标，不影响标对）")
for name, run in RUN.items():
    hits = []
    for r in rows:
        if r["run"] == run and r["pred_label"] == "Modifier" and r["gold_label"] not in ("", "Modifier") and r["gold_start"]:
            before = texts[r["doc"]][max(0, int(r["gold_start"]) - 25):int(r["gold_start"])]
            if re.search(r"history of\s*$", before):
                hits.append(f"{r['doc']} '{r['gold_text'].strip()}'（gold {r['gold_label']}）")
    out.append(f"  {name}：{len(hits)} 个  " + "；".join(hits))

out.append("")
out.append("G. 验证集上紧跟 history of 的全部 gold 提及：原指南 19 次运行中标对次数，以及两份指南的标法（11/10 追加）")
err_any: dict[str, dict] = defaultdict(dict)  # run -> gold key (any label) -> first error row
for r in rows:
    if r["gold_start"]:
        err_any[r["run"]].setdefault((r["doc"], int(r["gold_start"]), int(r["gold_end"])), r)
hist = []
for path in sorted(VALID.glob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    for a in doc["denotations"]:
        s, e = a["span"]["begin"], a["span"]["end"]
        if re.search(r"history of\s*$", doc["text"][max(0, s - 25):s]):
            hist.append(((doc["sourceid"], s, e), a["obj"]))
assert len(hist) == 9 and all(label != "Modifier" for _, label in hist)


def hist_state(run, key):
    r = err_any[run].get(key)
    if r is None:
        return "标对"
    return f"{r['kind']}：{r['pred_label'] or '没标'}" + (f" '{r['pred_text'].strip()}'" if r["pred_text"] else "")


orig_modifier_here = Counter()
for key, label in hist:
    n_right = sum(1 for run in orig_runs if key not in err_any[run])
    for run in orig_runs:
        if err_any[run].get(key, {}).get("pred_label") == "Modifier":
            orig_modifier_here[run] += 1
    out.append(f"  {key[0]} '{texts[key[0]][key[1]:key[2]].strip()}'（gold {label}）：原指南 {n_right}/19；"
               f"loop08 {hist_state(RUN['loop08'], key)}；loop04 {hist_state(RUN['loop04'], key)}")
out.append(f"  这 9 个 gold 的标签：{dict(Counter(label for _, label in hist))}；Modifier 0 个")
out.append(f"  原指南 19 次运行在这 9 个位置标成 Modifier 的个数：每次 {sorted(orig_modifier_here[r] for r in orig_runs)}")
fp = {r["guideline"]: r for r in csv.DictReader((HERE / "overall_view" / "type_f1.csv").open(encoding="utf-8"))
      if r["label"] == "Modifier"}
out.append(f"  Modifier 错标总数（type_f1.csv）：loop08 {fp['top-4 loop08']['fp']}，loop04 {fp['top-4 loop04']['fp']}")
out.append("  训练集 gold（543 篇）紧跟 history of 的提及见 rule_chain_output.txt D 节：Specific 9、Composite 5、不标 4、DiseaseClass 3，没有 Modifier")

out.append("")
out.append("F. loop04 标成 Composite 的 4 个并列病名：已保存回复里的相关文字（codex_locate 没收这几条，理由取自原始回复）")
want = {("8644702", 133): "cancer susceptibility gene", ("8644702", 1109): "breast-ovarian cancer families",
        ("8644702", 1282): "cancer kindred", ("8968716", 425): "cancer cases"}
seen = 0
for line in (HERE / "20261030_rationale_audit" / "prediction_index.jsonl").open(encoding="utf-8"):
    p = json.loads(line)
    if p["run"] == RUN["loop04"] and (str(p["doc"]), int(p["start"])) in want:
        reply = json.dumps(json.loads((ROOT / p["reply_file"]).read_text(encoding="utf-8")), ensure_ascii=False)
        k = reply.find(want[(str(p["doc"]), int(p["start"]))])
        snippet = reply[max(0, k - 80):k + 380].replace("\\n", " ") if k >= 0 else "回复里没有单独讨论这一处"
        out.append(f"  {p['doc']} {p['start']} {p['pred_label']} '{p['pred_text']}'（{p['reply_file']}）")
        out.append(f"    {snippet}")
        seen += 1
assert seen == 4

out.append("")
out.append("E. 引文逐字核对（plain 指南，行号从 1 起）")
lines = {g: (LOCATE / "guidelines" / f"{g}.txt").read_text(encoding="utf-8").splitlines() for g in ("top4_loop08", "top4_loop04")}
for g, n, q in QUOTES:
    ok = q in lines[g][n - 1]
    out.append(f"  {'PASS' if ok else 'FAIL'} {g} L{n}: {q}")
    assert ok, (g, n, q)
out.append(f"PASS：{len(QUOTES)} 条引文逐字出现在所注行。")

target = HERE / "overall_view" / "pair_modifier_tp_diff_output.txt"
target.write_bytes(("\n".join(out) + "\n").encode("utf-8"))  # LF on every platform
print("\n".join(out[:20]))
