"""Why five, and could it be more? What the three limits set by n_examples cost in prompt size and money.

Offline, no API calls. n_examples = 5 is the default of the published code (iterative.py, experiment.py); the
three limits it sets are in iterative.py (documents in the "do not break" block, line 399; matched annotations
listed per document, line 397; error examples per cluster, line 379).

1. Measured: per step type, prompt characters, input and output tokens and cost of every call of the 20 Haiku loops
   (calls.json of each loop, usage of each saved batch reply, priced with todo-temp/haiku-trial/run_haiku.cost_jpy).
2. Rebuilt: for each of the 44 rounds, the "do not break" block exactly as _build_true_positive_examples renders it,
   from the round's snapshot (gold and predictions before the rewrite). Check: the rebuilt capped block must occur
   verbatim in the round's rewrite prompt. Then the same block with the per-document limit lifted (still at most 5
   documents) and with both limits lifted (every document, every matched annotation), and every targeted cluster's
   error examples without the per-cluster limit.
3. Estimate (not observed): added input tokens = added characters x the measured tokens per character of the same
   step type; added cost at the batch input price, for each prompt that carries the block (the rewrite prompt and
   every analysis prompt of the round).

Run with PYTHONHASHSEED=0 (as the loops were), so set iteration order matches the published rendering.
Writes example_caps_output.txt.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1] / "outputs"
OUT = ROOT / "outputs" / "ncbi_disease"
TRAIN = ROOT / "data" / "datasets" / "ncbi_disease" / "train"
REPLIES = OUT / "20261022_haiku-xhigh_batchqueue" / "replies"
sys.path.insert(0, str(ROOT / "todo-temp" / "haiku-trial"))
sys.path.insert(0, str(ROOT / "todo-temp" / "deepseek-stability"))
import run_haiku as rh  # noqa: E402

assert os.environ.get("PYTHONHASHSEED") == "0", "run with PYTHONHASHSEED=0"
FOLDERS = sorted(OUT.glob("20261022_haiku-xhigh_topk*_loop*"))
out = []

# 1. measured cost by step type
STEPS = ("annotate_with_guidelines", "infer_discrepancy_patterns", "generate_moderation_principle", "refine_guidelines")
by = defaultdict(lambda: {"calls": 0, "chars": [], "in": 0, "out": 0, "jpy": 0.0})
ratio = defaultdict(list)
jpy = {}
for folder in FOLDERS:
    for c in json.loads((folder / "calls.json").read_text(encoding="utf-8")):
        reply = REPLIES / f"{c['custom_id']}.json"
        if not reply.exists():
            continue
        u = json.loads(reply.read_text(encoding="utf-8"))["message"].get("usage") or {}
        tin = sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        task = c["task"].rstrip("_1234")  # top-4 numbers its analysis and principle steps _1 to _4
        b = by[task]
        b["calls"] += 1
        b["chars"].append(c["prompt_chars"])
        b["in"] += tin
        b["out"] += u.get("output_tokens", 0) or 0
        b["jpy"] += rh.cost_jpy(u, True)
        jpy[c["custom_id"]] = rh.cost_jpy(u, True)
        ratio[task].append(tin / c["prompt_chars"])
total = sum(b["jpy"] for b in by.values())
out.append(f"1. Measured, 20 loops (top-1 and top-4 loop01-10), all calls with a saved reply, annotation including the 100 "
           f"validation documents of each loop; total JPY {total:.0f}")
out.append(f"   {'step':<31} {'calls':>5} {'prompt chars mean / max':>24} {'input tok':>10} {'output tok':>11} {'JPY':>7} {'share':>6} {'tok/char':>8}")
for t in STEPS:
    b = by[t]
    out.append(f"   {t:<31} {b['calls']:>5} {statistics.mean(b['chars']):>13,.0f} / {max(b['chars']):>7,} {b['in']:>10,} {b['out']:>11,} "
               f"{b['jpy']:>7.0f} {b['jpy'] / total:>6.1%} {statistics.mean(ratio[t]):>8.3f}")
price_in = rh.cost_jpy({"input_tokens": 1_000_000}, True)  # JPY per million fresh input tokens at the batch price
out.append(f"   batch input price used for the estimates below: JPY {price_in:.2f} per million input tokens (run_haiku.cost_jpy)")


# 2. rebuild the block from each round's snapshot
def summary(label: str, b: int, e: int, text: str) -> str:
    return f'{label} [{b}, {e}] "{text}"'


def block(files: list, per_doc: int | None, docs: int | None) -> tuple[str, int, int]:
    blocks, listed = [], 0
    for f in files:
        gold = {(d["start"], d["end"], d["label"]): d for d in f["reference_denotations"]}
        pred = {(d["start"], d["end"], d["label"]): d for d in f["study_denotations"]}
        matched = [gold[k] for k in gold.keys() & pred.keys()]
        if not matched:
            continue
        text = json.loads((TRAIN / f["filename"]).read_text(encoding="utf-8"))["text"]
        shown = matched if per_doc is None else matched[:per_doc]
        listed += len(shown)
        lines = [f"FILE: {f['filename']}", f"TEXT: {text}", "MATCHED ANNOTATIONS:"]
        lines += [f"- {summary(d['label'], d['start'], d['end'], d['text'])}" for d in shown]
        blocks.append("\n".join(lines))
        if docs is not None and len(blocks) >= docs:
            break
    return "\n\n".join(blocks), len(blocks), listed


def errors(cluster: dict, cap: int | None) -> str:
    ex = cluster["examples"] if cap is None else cluster["examples"][:cap]
    return "\n\n".join("\n".join([f"Example {i + 1} (Doc: {e['doc_id']}):", f'Snippet: "...{e["text_snippet"]}..."',
                                  f"Gold: {e['gold_entity']}, LLM: {e['llm_entity']}", f'Entity Text: "{e["entity_text"]}"'])
                       for i, e in enumerate(ex))


verbatim = rounds = 0
mismatch = []
rows = defaultdict(list)
for folder in FOLDERS:
    k = 1 if "topk1" in folder.name else 4
    for it in sorted((folder / "rounds").glob("iteration_*")):
        rounds += 1
        s = json.loads((it / "snapshot.json").read_text(encoding="utf-8"))
        files = s["diagnostics_before"]["files"]
        capped, n_docs, n_listed = block(files, 5, 5)
        if capped in (it / "refine_guidelines.txt").read_text(encoding="utf-8"):
            verbatim += 1
        else:
            mismatch.append(f"{folder.name.split('_', 2)[2]} {it.name}")
        per_doc, _, n_per_doc = block(files, None, 5)
        full, n_full_docs, n_full = block(files, None, None)
        targets = s["summary_before"]["all_clusters"][:k]
        err_added = sum(len(errors(c, None)) - len(errors(c, 5)) for c in targets)
        rows["carriers"].append(1 + len(targets))  # the rewrite prompt and one analysis prompt per targeted cluster
        rows["capped"].append(len(capped))
        rows["per_doc_added"].append(len(per_doc) - len(capped))
        rows["full_added"].append(len(full) - len(capped))
        rows["listed"].append((n_listed, n_per_doc, n_full, n_full_docs))
        rows["err_added"].append(err_added)
        rows["refine_chars"].append(len((it / "refine_guidelines.txt").read_text(encoding="utf-8")))
out.append(f"\n2. Rebuilt 'do not break' block, {rounds} rounds. Check: the rebuilt capped block occurs verbatim in the rewrite prompt "
           f"in {verbatim} of {rounds} rounds; not in: {', '.join(mismatch) or '-'}")
mean = statistics.mean
out.append(f"   rewrite prompt now: mean {mean(rows['refine_chars']):,.0f} chars (max {max(rows['refine_chars']):,}); "
           f"block now: mean {mean(rows['capped']):,.0f} chars, listing {mean(r[0] for r in rows['listed']):.1f} matched annotations")
out.append(f"   per-document limit lifted (5 documents): +{mean(rows['per_doc_added']):,.0f} chars per block (max +{max(rows['per_doc_added']):,}), "
           f"listing {mean(r[1] for r in rows['listed']):.1f}")
out.append(f"   both limits lifted (every document): +{mean(rows['full_added']):,.0f} chars per block (max +{max(rows['full_added']):,}), "
           f"listing {mean(r[2] for r in rows['listed']):.1f} in {mean(r[3] for r in rows['listed']):.1f} documents")
out.append(f"   error-example limit lifted: +{mean(rows['err_added']):,.0f} chars per round over its analysis prompts (max +{max(rows['err_added']):,})")

# 3. estimated added cost per round and per 20-loop batch of runs like this one
tpc_ref, tpc_inf = mean(ratio["refine_guidelines"]), mean(ratio["infer_discrepancy_patterns"])
out.append("\n3. Estimate (added characters x measured tokens per character x batch input price; the block is in the rewrite "
           "prompt and every analysis prompt of the round)")
for name, key in (("per-document limit lifted", "per_doc_added"), ("both limits lifted", "full_added")):
    tok = [a * (tpc_ref + (c - 1) * tpc_inf) for a, c in zip(rows[key], rows["carriers"])]
    out.append(f"   {name:<27} +{mean(tok):,.0f} input tokens per round, JPY {mean(tok) * price_in / 1e6:.2f} per round, "
               f"JPY {sum(tok) * price_in / 1e6:.1f} over these {rounds} rounds")
tok = [a * tpc_inf for a in rows["err_added"]]
out.append(f"   {'error-example limit lifted':<27} +{mean(tok):,.0f} input tokens per round, JPY {mean(tok) * price_in / 1e6:.2f} per round, "
           f"JPY {sum(tok) * price_in / 1e6:.1f} over these {rounds} rounds")
out.append(f"   for scale: the {rounds} rounds and their loops cost JPY {total:.0f} in all")

# 4. measured cost of what a replay of the 44 rounds repeats: each round's rewrite, and one annotation of the 10
# development documents with its candidate (a loop's first 10 x (1 + rounds) annotation calls; its last 100 are validation)
rewrite = defaultdict(list)
dev_pass = []
round_steps = 0.0  # analysis, principle and rewrite calls of every round
for folder in FOLDERS:
    calls = json.loads((folder / "calls.json").read_text(encoding="utf-8"))
    n_rounds = len(list((folder / "rounds").glob("iteration_*")))
    ann = [c for c in calls if c["task"] == "annotate_with_guidelines"]
    assert len(ann) == 10 * (1 + n_rounds) + 100, folder.name
    dev_pass.append(sum(jpy[c["custom_id"]] for c in ann[:10 * (1 + n_rounds)]) / (1 + n_rounds))
    rewrite["top-1" if "topk1" in folder.name else "top-4"] += [jpy[c["custom_id"]] for c in calls if c["task"] == "refine_guidelines"]
    round_steps += sum(jpy[c["custom_id"]] for c in calls if c["task"] != "annotate_with_guidelines")
arm = sum(sum(v) for v in rewrite.values()) + rounds * mean(dev_pass)
whole = round_steps + rounds * mean(dev_pass)
out.append("\n4. Measured cost per call of what a replay repeats")
for m, v in sorted(rewrite.items()):
    out.append(f"   rewrite, {m}: {len(v)} calls, JPY {min(v):.2f} to {max(v):.2f} (mean {mean(v):.2f})")
out.append(f"   one annotation of the 10 development documents: JPY {min(dev_pass):.2f} to {max(dev_pass):.2f} per loop (mean {mean(dev_pass):.2f})")
out.append(f"   replay, one arm (every round rewritten once, each candidate annotated once): about JPY {arm:.0f}; "
           f"two arms JPY {2 * arm:.0f} (estimate from these measured costs)")
out.append(f"   replay of the whole round step, one arm (analysis, principles and rewrite regenerated, each candidate annotated "
           f"once): about JPY {whole:.0f}; two arms JPY {2 * whole:.0f} (estimate from these measured costs)")

(HERE / "example_caps_output.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
print("\n".join(out))
