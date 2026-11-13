"""Validate evidence-backed manual judgments and render the fixed rationale audit.

Offline. Reads only the frozen sample, selection manifest and semantic coding.
The coding is an interpretive record, not an automatically inferred label.
"""
from __future__ import annotations

import hashlib
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "nodes/shared/error-analysis/outputs/20261030_rationale_audit"
# semantic_coding.json records evidence paths from before the 2026-11-13 move (todo-temp/error-analysis/outputs/...).
LEGACY = ("todo-temp/error-analysis/outputs/20261030_rationale_audit/", "nodes/shared/error-analysis/outputs/20261030_rationale_audit/")


def moved(p):
    return p.replace(*LEGACY, 1) if p.startswith(LEGACY[0]) else p
AXES = {
    "text_rationale": "原文与理由",
    "guideline_rationale": "指南与理由",
    "rationale_label": "理由与标签",
    "rationale_boundary": "理由与边界",
    "guideline_prediction": "指南与预测",
}
STATUS = {"supported": "支持", "unsupported": "不支持", "undetermined": "无法确定", "not_stated": "未说明"}


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def check_legacy_citations():
    by_doc = defaultdict(list)
    with (OUT / "prediction_index.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if "_topk" in r["run"]:
                group = ("top-1 " if "_topk1_" in r["run"] else "top-4 ") + r["run"].split("_")[-1]
                by_doc[group, r["doc"]].append(r)
    count, matched = 0, 0
    with (ROOT / "nodes/2026-10-30_seminar/error-analysis/outputs/cited_sections.csv").open(encoding="utf-8") as f:
        for old in csv.DictReader(f):
            if old["part"] != "B":
                continue
            start, end = map(int, old["span"].split("-"))
            overlap = [r for r in by_doc[old["guideline"], old["doc"]]
                       if min(end, r["end"]) > max(start, r["start"])]
            new = max(overlap, key=lambda r: min(end, r["end"]) - max(start, r["start"]))
            count += 1
            matched += new["raw_rationale"] == old["rationale"] and new["cited_section"] == old["cited_section"]
    return {"checked": count, "identical_rationale_and_citation": matched}


def main():
    sample = {r["case_id"]: r for r in read("sample.json")["cases"]}
    manifest = read("selection_manifest.json")
    selection = {r["case_id"]: r for r in manifest["selected"]}
    scores = {r["case_id"]: r["scoring"] for r in manifest["gold_and_status"]}
    coding = read("semantic_coding.json")
    records = coding["cases"]
    assert len(records) == len({r["id"] for r in records}) == len(sample) == 16
    assert {r["id"] for r in records} == set(sample)
    counts = {axis: Counter() for axis in AXES}
    comparisons = coding.get("comparisons", [])
    assert len(comparisons) <= 4
    for r in records:
        for axis in AXES:
            item = r[axis]
            assert item["status"] in STATUS and item["reason"].strip(), (r["id"], axis)
            counts[axis][item["status"]] += 1
        for ev in r["evidence"]:
            path = ROOT / moved(ev["path"])
            lines = path.read_text(encoding="utf-8").splitlines()
            assert 1 <= ev["start"] <= ev["end"] <= len(lines), (r["id"], ev)
            assert ev["quote"] in "\n".join(lines[ev["start"] - 1:ev["end"]]), (r["id"], ev)
    summary = {
        "primary_predictions": len(records),
        "documents": len({r["doc"] for r in sample.values()}),
        "prediction_labels": dict(Counter(r["pred_label"] for r in sample.values())),
        "scoring_states": dict(Counter(r["kind"] for r in selection.values())),
        "labels_by_scoring_state": {
            kind: dict(Counter(sample[r["case_id"]]["pred_label"] for r in selection.values() if r["kind"] == kind))
            for kind in ("correct", "label", "boundary", "extra")
        },
        "guideline_groups": dict(Counter(r["guideline_group"] for r in selection.values())),
        "guideline_texts": len({r["guideline_sha256"] for r in sample.values()}),
        "axes": {k: dict(v) for k, v in counts.items()},
        "rationale_missing": sum(not c["raw_rationale"] for c in sample.values()),
        "additional_comparisons": len(comparisons),
        "gold_disagreeing_guideline_supported_ids": [
            r["id"] for r in records
            if r["guideline_prediction"]["status"] == "supported" and scores[r["id"]]["kind"] != "correct"
        ],
        "boundary_errors_rationale_status": dict(Counter(
            r["rationale_boundary"]["status"] for r in records if scores[r["id"]]["kind"] == "boundary"
        )),
        "legacy_92_citation_check": check_legacy_citations(),
        "coding_sha256": hashlib.sha256((OUT / "semantic_coding.json").read_bytes()).hexdigest(),
        "selection_sha256": manifest["selection_sha256"],
        "limitation": "Purposive workload-limited audit; counts describe these predictions only. Groups are not paired and do not estimate improvement.",
    }
    (OUT / "semantic_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# 已保存理由的逐例语义核查", "", coding["method"], "",
          "下列判断分别检查原文、规则应用、标签和边界。gold 只在每例末尾展示，不用来反推理由是否成立。", "",
          "| 核查关系 | 支持 | 不支持 | 无法确定 | 未说明 |",
          "| --- | ---: | ---: | ---: | ---: |"]
    for axis, label in AXES.items():
        md.append("| " + label + " | " + " | ".join(str(counts[axis][s]) for s in STATUS) + " |")
    for r in sorted(records, key=lambda x: x["id"]):
        c = sample[r["id"]]
        sel = selection[r["id"]]
        score = scores[r["id"]]
        md += ["", f"## {r['id']}：{c['pred_text']}", "",
               f"文档 {c['doc']}，运行 `{sel['run']}`。预测 `{c['pred_label']}`，字符区间 [{c['start']}, {c['end']})。", "",
               "原句上下文：", "", "> " + c["context"].replace("\n", "\n> "), "",
               "模型理由：", "", "> " + (c["raw_rationale"] or "（未提供）"), "",
               "模型引用：" + (c["cited_section"] or "（未提供）") + "。", "",
               "判断：" + r["summary"], ""]
        for axis, label in AXES.items():
            md.append(f"- {label}：{STATUS[r[axis]['status']]}。{r[axis]['reason']}")
        md += ["", "条文证据：", ""]
        for ev in r["evidence"]:
            location = (ROOT / moved(ev["path"])).as_posix()
            md += [f"[原文第 {ev['start']} 至 {ev['end']} 行]({location}:{ev['start']})", "",
                   "> " + ev["quote"].replace("\n", "\n> "), ""]
        md += ["按指南允许的结果：" + r["allowed_under_guideline"], "",
               "与 gold 的独立比较：`" + score["kind"] + "`。对应 gold：" +
               ("；".join(f"{g['text']!r} ({g['label']}, [{g['start']}, {g['end']}))" for g in score["paired_gold"]) or "无重叠 gold") + "。", "",
               f"来源：`{c['reply_file']}`，原始条目序号 {c['raw_item_index']}。"]
        if r.get("review_note"):
            md += ["", "复核说明：" + r["review_note"]]
    (OUT / "cases_reviewed.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
