"""Trace where each focus case appears across the four pipeline stages of every round.

Offline only: reads saved snapshots of one moderation run, calls no model.
For each round and case it records:
  - prediction at the exact gold span before and after the round,
  - whether the case is a discrepancy example / its document is a contrast (TP) example
    in infer_discrepancy_patterns,
  - whether the principle or insight mentions the case,
  - whether its document is in the refine_guidelines CONSTRAINT (verified examples) block,
    whether the case string is inside the shown text, and whether its span is listed,
  - guideline lines mentioning the case before and after the round.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CASES = [
    # id, doc, start, end, gold label, gold text, key used to find paraphrases in prompts/guidelines
    ("FALDH", "10577908", 245, 295, "SpecificDisease",
     "deficient activity of fatty aldehyde dehydrogenase", "fatty aldehyde dehydrogenase"),
    ("G6PD", "1303173", 1559, 1577, "SpecificDisease", "deficiency in G6PD", "deficiency in G6PD"),
    ("PAH", "1671881", 138, 185, "SpecificDisease",
     "deficiency of hepatic phenylalanine hydroxylase", "phenylalanine hydroxylase"),
    ("norrin", "10484772", 949, 969, "DiseaseClass", "deficiency of norrin", "norrin"),
    ("retinal_vasc", "10484772", 186, 223, "DiseaseClass",
     "abnormal retinal vascular development", "retinal vascular development"),
]

FILE_BLOCK = re.compile(
    r"FILE: (?P<file>\S+)\nTEXT: (?P<text>.*?)\nMATCHED ANNOTATIONS:\n(?P<anns>(?:- [^\n]*(?:\n|$))*)",
    re.S,
)
ANN_LINE = re.compile(r'- (?P<label>\w+) \[(?P<start>\d+), (?P<end>\d+)\] "(?P<text>.*)"')


def section(text: str, start_marker: str, end_marker: str) -> str:
    i = text.find(start_marker)
    if i < 0:
        return ""
    j = text.find(end_marker, i + len(start_marker))
    return text[i:j if j >= 0 else len(text)]


def parse_blocks(sec: str) -> dict[str, dict]:
    blocks = {}
    for m in FILE_BLOCK.finditer(sec):
        anns = [
            (a["label"], int(a["start"]), int(a["end"]), a["text"])
            for a in ANN_LINE.finditer(m["anns"])
        ]
        blocks[m["file"].replace(".json", "")] = {"text": m["text"], "annotations": anns}
    return blocks


def prediction_at(diagnostics: dict, doc: str, start: int, end: int) -> str:
    for f in diagnostics["files"]:
        if f["filename"].replace(".json", "") != doc:
            continue
        exact = [d["label"] for d in f["study_denotations"] if d["start"] == start and d["end"] == end]
        if exact:
            return exact[0]
        overlap = [
            f'{d["label"]}[{d["start"]},{d["end"]})"{d["text"]}"'
            for d in f["study_denotations"]
            if d["start"] < end and d["end"] > start
        ]
        return "overlap:" + ";".join(overlap) if overlap else "O"
    return "doc-missing"


def guideline_hits(guidelines: str, key: str) -> list[dict]:
    hits = []
    for n, line in enumerate(guidelines.splitlines(), 1):
        if key.lower() in line.lower():
            hits.append({"line": n, "text": line.strip()[:300]})
    return hits


def block_info(blocks: dict, doc: str, start: int, end: int, key: str) -> dict:
    if doc not in blocks:
        return {"doc_shown": False}
    b = blocks[doc]
    return {
        "doc_shown": True,
        "case_text_in_shown_text": key.lower() in b["text"].lower(),
        "case_span_listed": any(s == start and e == end for _, s, e, _ in b["annotations"]),
        "n_listed_annotations": len(b["annotations"]),
    }


def trace(run_dir: Path) -> dict:
    out = {"run": str(run_dir), "rounds": [], "snapshot_sha256": {}}
    for it_dir in sorted((run_dir / "rounds").glob("iteration_*")):
        snap_path = it_dir / "snapshot.json"
        raw = snap_path.read_bytes()
        out["snapshot_sha256"][it_dir.name] = hashlib.sha256(raw).hexdigest()
        s = json.loads(raw)
        prompts = s.get("prompts", {})
        infer = prompts.get("infer_discrepancy_patterns", "")
        refine = prompts.get("refine_guidelines", "")
        disc_sec = section(infer, "**1. DISCREPANCIES TO ANALYZE:**", "**2.")
        tp_blocks = parse_blocks(section(infer, "**2. TRUE POSITIVE EXAMPLES", "**TASK:**"))
        ver_blocks = parse_blocks(section(refine, "**CONSTRAINT: DO NOT BREAK THESE EXAMPLES:**", "**INSTRUCTIONS:**"))
        rnd = {
            "iteration": s.get("iteration"),
            "dominant_cluster": s["summary_before"]["dominant_cluster"]["key"],
            "improved": s.get("improved"),
            "reverted": s.get("reverted"),
            "principle": s.get("moderation_principle", ""),
            "insight": s.get("discrepancy_insight", ""),
            "tp_docs_in_infer": sorted(tp_blocks),
            "verified_docs_in_refine": sorted(ver_blocks),
            "cases": {},
        }
        for cid, doc, start, end, gold, gtext, key in CASES:
            rnd["cases"][cid] = {
                "pred_before": prediction_at(s["diagnostics_before"], doc, start, end),
                "pred_after": prediction_at(s["diagnostics_after"], doc, start, end),
                "is_discrepancy_example": f'Entity Text: "{gtext}"' in disc_sec,
                "infer_tp_block": block_info(tp_blocks, doc, start, end, key),
                "principle_mentions": key.lower() in rnd["principle"].lower(),
                "insight_mentions": key.lower() in rnd["insight"].lower(),
                "refine_verified_block": block_info(ver_blocks, doc, start, end, key),
                "guideline_before": guideline_hits(s["guidelines_before"], key),
                "guideline_after": guideline_hits(s["guidelines_after"], key),
            }
        out["rounds"].append(rnd)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    result = trace(args.run_dir)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for rnd in result["rounds"]:
        print(f'== iteration {rnd["iteration"]} | cluster {rnd["dominant_cluster"]} | '
              f'improved={rnd["improved"]} reverted={rnd["reverted"]}')
        print(f'   TP docs (infer): {rnd["tp_docs_in_infer"]}')
        print(f'   verified docs (refine): {rnd["verified_docs_in_refine"]}')
        for cid, c in rnd["cases"].items():
            gb = [h["line"] for h in c["guideline_before"]]
            ga = [h["line"] for h in c["guideline_after"]]
            print(f'   {cid:12s} pred {c["pred_before"]:>15s} -> {c["pred_after"]:<15s} '
                  f'disc_ex={int(c["is_discrepancy_example"])} '
                  f'tp={c["infer_tp_block"]} principle={int(c["principle_mentions"])} '
                  f'verified={c["refine_verified_block"]} gl_before={gb} gl_after={ga}')


if __name__ == "__main__":
    main()
