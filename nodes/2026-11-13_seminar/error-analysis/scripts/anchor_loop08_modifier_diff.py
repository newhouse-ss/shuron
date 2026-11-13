"""以 top-4 loop08 为锚点，列出 gold 为 Modifier、两份改后指南的验证集标注结果不同的位置（2026-11-12，离线）。

对其余 10 份改后指南逐份比较：gold 为 Modifier 的位置上，一份标成 Modifier（位置和类型都对）而另一份没有。
先列只有 top-4 loop08 标对的位置，再列只有另一份标对的位置；"->" 后是另一份在该位置的标注
（O 表示没标；overlap 表示标了与之重叠的其他范围）。
用法：python nodes/2026-11-13_seminar/error-analysis/scripts/anchor_loop08_modifier_diff.py > nodes/2026-11-13_seminar/error-analysis/outputs/overall_view/anchor_loop08_modifier_diff_output.txt
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
V = ROOT / "data" / "datasets" / "ncbi_disease" / "valid"
O = ROOT / "outputs" / "ncbi_disease"
RUNS = ["topk4_loop04", "topk4_loop01", "topk1_loop07", "topk4_loop09", "topk4_loop02",
        "topk4_loop05", "topk4_loop07", "topk4_loop06", "topk1_loop05", "topk4_loop10"]


def load(run):
    d = O / f"20261022_haiku-xhigh_{run}" / "valid_predictions"
    return {f.stem: {(x["span"]["begin"], x["span"]["end"]): x["obj"]
                     for x in json.load(open(f, encoding="utf-8"))["denotations"]}
            for f in d.glob("*.json")}


G, T = {}, {}
for f in V.glob("*.json"):
    g = json.load(open(f, encoding="utf-8"))
    T[g["sourceid"]] = g["text"]
    G[g["sourceid"]] = {(x["span"]["begin"], x["span"]["end"]): x["obj"] for x in g["denotations"]}
P8 = load("topk4_loop08")
for run in RUNS:
    P = load(run)
    gain, loss = [], []
    for doc, gs in sorted(G.items()):
        t = T[doc]
        for s, lab in sorted(gs.items()):
            if lab != "Modifier":
                continue
            a = P8[doc].get(s) == "Modifier"
            b = P[doc].get(s) == "Modifier"
            if a == b:
                continue
            other = P[doc] if a else P8[doc]
            ol = other.get(s)
            if ol is None:
                ov = [f"{t[o[0]:o[1]]}={l}" for o, l in other.items() if o[0] < s[1] and s[0] < o[1]]
                ol = ("overlap:" + ";".join(ov)) if ov else "O"
            row = f"  {doc} {t[max(0, s[0] - 25):s[0]]}[{t[s[0]:s[1]]}]{t[s[1]:s[1] + 25]} -> {ol}".replace("\n", " ")
            (gain if a else loss).append(row)
    print(f"== {run}: 只有 top-4 loop08 标对 {len(gain)}，只有 {run} 标对 {len(loss)}")
    print("\n".join(gain))
    print(" -- 只有另一份标对:")
    print("\n".join(loss))
