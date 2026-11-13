"""Offline exact provenance and a frozen, rationale-independent validation sample.

Run with Python 3.10+ from any directory. No public package initializers,
credential loaders, SDKs, training data, or test splits are imported/read.
Only this file and outputs/20261030_rationale_audit are owned by this utility.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import json
import re
import sys
import types
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "nodes/shared/error-analysis/outputs/20261030_rationale_audit"
RUNROOT = ROOT / "outputs/ncbi_disease"
VALID = ROOT / "data/datasets/ncbi_disease/valid"
REPLIES = RUNROOT / "20261022_haiku-xhigh_batchqueue/replies"
ERRORS = ROOT / "nodes/shared/error-analysis/outputs/error_rows.csv"
SOURCE = ROOT / "src/llm_guideline_moderation"
SEED = 20261030
TASK = "annotate_with_guidelines"
STATES = ("correct", "label", "boundary", "extra")


def sha(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(name, value):
    (OUT / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def jsonline(handle, value):
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_pure():
    """Bypass __init__.py and extract only inspected pure pipeline/provider code."""
    package = "_rationale_audit_pure"
    for suffix, directory in (("", SOURCE), (".providers", SOURCE / "providers")):
        module = types.ModuleType(package + suffix)
        module.__path__ = [str(directory)]
        sys.modules[module.__name__] = module
    modules = {}
    for name in ("types", "prompts", "prompt_utils", "text_utils", "pubannotation", "providers._shared"):
        path = SOURCE / (name.replace(".", "/") + ".py")
        spec = importlib.util.spec_from_file_location(package + "." + name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    t = modules["types"]
    env = {"json": json, "re": re, "replace": replace,
           "Annotation": t.Annotation, "InitialAnnotationResult": t.InitialAnnotationResult,
           "ModerationRoundInput": t.ModerationRoundInput,
           "generate_schema_parts": modules["prompt_utils"].generate_schema_parts,
           "render_prompt": modules["prompts"].render_prompt,
           "align_annotations": modules["text_utils"].align_annotations,
           "JSON_MODE_SYSTEM_PROMPT": modules["providers._shared"].JSON_MODE_SYSTEM_PROMPT,
           "is_json_task": modules["providers._shared"].is_json_task}
    names = {"_entity_schema_text", "normalize_entity_labels", "_parse_initial_annotation_result",
             "annotate_with_guidelines"}
    pipeline = ast.parse((SOURCE / "pipeline.py").read_text(encoding="utf-8"))
    nodes = [n for n in pipeline.body if isinstance(n, ast.FunctionDef) and n.name in names]
    provider = ast.parse((SOURCE / "providers/claude.py").read_text(encoding="utf-8"))
    nodes += [n for n in provider.body if isinstance(n, ast.FunctionDef) and n.name in {"_parses", "_json_text"}]
    nodes += [n for n in provider.body if isinstance(n, ast.Assign)
              and any(isinstance(x, ast.Name) and x.id == "_FENCED" for x in n.targets)]
    cls = next(n for n in provider.body if isinstance(n, ast.ClassDef) and n.name == "ClaudeProvider")
    nodes += [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {"read_message", "build_params"}]
    tree = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), "<inspected-pure-project-functions>", "exec"), env)
    return modules, types.SimpleNamespace(**env)


def build_prompt(pure, text, guideline, entities, config):
    class Capture:
        def complete(self, task, prompt):
            self.prompt = prompt
            return '{"annotations": []}'
    capture = Capture()
    pure.annotate_with_guidelines(text, guideline, entities, capture, instructions="", output_configuration=config)
    return capture.prompt


def denotation_key(d):
    return d["span"]["begin"], d["span"]["end"], d["obj"]


def annotation_key(a):
    return a.start, a.end, a.entity


def overlap(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def replay(message, text, entities, modules, pure):
    reader = types.SimpleNamespace(max_output_tokens=128000)
    payload = pure.read_message(reader, message, TASK)
    if reader.last_extraction == "unparsed":
        raise ValueError("annotation reply is not JSON")
    parsed = pure._parse_initial_annotation_result(payload)
    original = parsed.annotations
    # Alignment copies raw_entity unchanged. A temporary marker therefore tracks
    # raw item identity without depending on rationale, text uniqueness or offsets.
    tagged = [replace(a, raw_entity=str(i)) for i, a in enumerate(original)]
    aligned_tagged = modules["text_utils"].align_annotations(text, tagged)
    restored = [replace(a, raw_entity=original[int(a.raw_entity)].raw_entity) for a in aligned_tagged]
    direct = modules["text_utils"].align_annotations(text, original)
    if restored != direct:
        raise AssertionError("raw identity tracing changed pure alignment")
    normalized = pure.normalize_entity_labels(direct, entities)
    by_raw = {int(a.raw_entity): normalized[i] for i, a in enumerate(aligned_tagged)}
    traces = []
    for i, item in enumerate(original):
        aligned = by_raw.get(i)
        solo = modules["text_utils"].align_annotations(text, [item]) if aligned is None else []
        reason = None
        proposed = None
        conflicts = []
        if aligned is None:
            if not modules["text_utils"].normalize_text_preserve_spacing(item.text):
                reason = "empty_normalized_text"
            elif not solo:
                reason = "text_not_found_including_whitespace_fallback"
            else:
                reason = "overlaps_previously_kept_raw_item"
                proposed = asdict(solo[0])
                conflicts = [j for j, a in by_raw.items() if j < i and overlap(annotation_key(solo[0]), annotation_key(a))]
        traces.append({"raw_item_index": i, "raw": parsed.raw_response["annotations"][i],
                       "aligned": asdict(aligned) if aligned else None, "dropped": aligned is None,
                       "drop_reason": reason, "proposed_alignment": proposed,
                       "conflicting_raw_item_indices": conflicts})
    return normalized, traces, reader.last_extraction


def choose_exact(candidates, call_records, expected, text, entities, modules, pure):
    """Recorded call association precedes equality; ties remain ambiguous."""
    results, exact = [], []
    for reply in candidates:
        m = reply["meta"]
        calls = [c for c in call_records if c.get("custom_id") == reply["custom_id"]
                 and all(c.get(k) == m.get(k) for k in ("loop", "task", "prompt_sha256", "occurrence", "attempt", "prompt_chars"))
                 and ("max_tokens" not in c or "max_tokens" not in m or c["max_tokens"] == m["max_tokens"])]
        result = {k: reply[k] for k in ("reply_file", "reply_sha256", "custom_id", "meta")}
        result["recorded_call_matches"] = len(calls)
        if not calls:
            result["status"] = "not_associated_with_recorded_call"
        else:
            try:
                aligned, traces, extraction = replay(reply["message"], text, entities, modules, pure)
                got = Counter(annotation_key(a) for a in aligned)
                result.update(replay_equal=got == expected, extraction=extraction,
                              replay_count=sum(got.values()), raw_count=len(traces),
                              dropped_count=sum(x["dropped"] for x in traces))
                result["status"] = "equal" if got == expected else "replay_mismatch"
                if got != expected:
                    result["missing_saved_tuples"] = [list(k) + [v] for k, v in sorted((expected - got).items())]
                    result["unexpected_replay_tuples"] = [list(k) + [v] for k, v in sorted((got - expected).items())]
                else:
                    exact.append((reply, aligned, traces))
            except (ValueError, TypeError, KeyError, RuntimeError, AssertionError) as exc:
                result.update(status="replay_error", error=f"{type(exc).__name__}: {exc}")
        results.append(result)
    status = "exact" if len(exact) == 1 else "ambiguous_equal_replies" if exact else "no_exact_reply"
    return status, exact[0] if len(exact) == 1 else None, results


def scoring(run, doc, denotations, gold, text, error_map):
    gold_keys = [denotation_key(d) for d in gold]
    pred_keys = [denotation_key(d) for d in denotations]
    remaining = Counter(gold_keys)
    result = []
    for key in pred_keys:
        strict = remaining[key] > 0
        rows = error_map.get((run, doc, *key), [])
        if strict:
            remaining[key] -= 1
            if rows:
                raise ValueError(f"strict prediction also has error row: {run}/{doc}/{key}")
            kind, paired = "correct", [key]
            evidence = "independent_strict_tuple_multiset"
        else:
            if len(rows) != 1:
                raise ValueError(f"expected one prediction-key error row, found {len(rows)}: {run}/{doc}/{key}")
            row = rows[0]
            kind = row["kind"]
            paired = [(int(row["gold_start"]), int(row["gold_end"]), row["gold_label"])] if row["gold_start"] else []
            if any(g not in gold_keys for g in paired):
                raise ValueError("error_rows gold reference absent from actual valid gold")
            evidence = "error_rows.csv_prediction_key"
        all_overlaps = []
        for gi, g in enumerate(gold_keys):
            ov = overlap(key, g)
            if ov:
                all_overlaps.append({"gold_index": gi, "gold_id": gold[gi].get("id"),
                                     "start": g[0], "end": g[1], "label": g[2], "text": text[g[0]:g[1]],
                                     "overlap_chars": ov,
                                     "overlapping_prediction_indices": [i for i, p in enumerate(pred_keys) if overlap(p, g)]})
        if (kind == "extra") != (len(all_overlaps) == 0):
            raise ValueError(f"extra must mean zero gold overlap: {run}/{doc}/{key}")
        result.append({"kind": kind, "evidence": evidence,
                       "paired_gold": [{"start": g[0], "end": g[1], "label": g[2], "text": text[g[0]:g[1]]} for g in paired],
                       "all_gold_overlaps": all_overlaps, "error_rows": rows})
    return result


def seed_order(value):
    return sha(f"{SEED}|{value}")


def select(candidates):
    """Use metadata only; candidate dictionaries deliberately contain no rationale."""
    cells = [(group, kind) for group in ("original", "changed") for kind in STATES]
    buckets = {cell: [c for c in candidates if (c["guideline_group"], c["kind"]) == cell] for cell in cells}
    chosen = []
    doc_use, label_use, guideline_use, run_use = Counter(), Counter(), Counter(), Counter()
    occupied = set()
    per_cell_docs = defaultdict(set)
    # Two round-robin passes distribute coverage before any cell gets its second.
    for slot in range(2):
        for cell in cells:
            pool = [c for c in buckets[cell] if c["doc"] not in per_cell_docs[cell]
                    and (c["doc"], c["start"], c["end"]) not in occupied and doc_use[c["doc"]] < 2]
            if not pool:
                continue
            best = min(pool, key=lambda c: (doc_use[c["doc"]] > 0,
                       label_use[c["pred_label"]] > 0, label_use[c["pred_label"]],
                       guideline_use[c["guideline_sha256"]] > 0, guideline_use[c["guideline_sha256"]],
                       run_use[c["run"]] > 0, run_use[c["run"]], seed_order(c["case_key"])))
            chosen.append(best)
            doc_use[best["doc"]] += 1
            label_use[best["pred_label"]] += 1
            guideline_use[best["guideline_sha256"]] += 1
            run_use[best["run"]] += 1
            per_cell_docs[cell].add(best["doc"])
            occupied.add((best["doc"], best["start"], best["end"]))
    # Opaque aliases are assigned after selection, in a separate seeded order.
    chosen.sort(key=lambda c: seed_order("blind|" + c["case_key"]))
    return [dict(c, case_id=f"R{i:02d}") for i, c in enumerate(chosen, 1)], buckets


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "documents").mkdir(exist_ok=True)
    (OUT / "guidelines").mkdir(exist_ok=True)
    modules, pure = load_pure()
    original = (ROOT / "data/guidelines/ncbi_disease_guidelines.txt").read_text(encoding="utf-8")
    original_hash = sha(original)
    gold_docs = {p.stem: (p, read(p)) for p in sorted(VALID.glob("*.json"))}
    if len(gold_docs) != 100:
        raise ValueError(f"expected valid100, got {len(gold_docs)}")
    gold_total = sum(len(data["denotations"]) for _, data in gold_docs.values())
    for doc, (_, data) in gold_docs.items():
        (OUT / "documents" / f"{doc}.txt").write_bytes(data["text"].encode("utf-8"))
    error_map = defaultdict(list)
    with ERRORS.open(encoding="utf-8", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), 2):
            if row["pred_start"]:
                key = (row["run"], row["doc"], int(row["pred_start"]), int(row["pred_end"]), row["pred_label"])
                error_map[key].append(dict(row, csv_line=line))
    reply_map = defaultdict(list)
    task_counts = Counter()
    for path in sorted(REPLIES.glob("*.json")):
        raw_bytes = path.read_bytes()
        r = json.loads(raw_bytes)
        task_counts[r["meta"]["task"]] += 1
        if r["meta"]["task"] == TASK:
            # Thinking blocks are neither needed nor retained in the index.
            r["message"]["content"] = [b for b in r["message"].get("content", []) if b.get("type") == "text"]
            r.update(reply_file=rel(path), reply_sha256=sha(raw_bytes))
            m = r["meta"]
            reply_map[m["loop"], m["task"], m["prompt_sha256"]].append(r)
    runs = [(f"E1R{i:02d}", f"20261022_haiku-xhigh_e1_run{i:02d}") for i in range(1, 11)]
    runs += [(f"topk{k}L{i:02d}", f"20261022_haiku-xhigh_topk{k}_loop{i:02d}") for k in (1, 4) for i in range(1, 11)]
    candidates, run_manifest, failures = [], [], []
    totals, drops = Counter(), Counter()
    selection_lookup = {}
    with (OUT / "prediction_index.jsonl").open("w", encoding="utf-8", newline="\n") as index_file, \
         (OUT / "provenance_documents.jsonl").open("w", encoding="utf-8", newline="\n") as doc_file, \
         (OUT / "raw_alignment.jsonl").open("w", encoding="utf-8", newline="\n") as raw_file:
        for loop, run in runs:
            folder = RUNROOT / run
            guideline_path = folder / ("inputs/initial_guidelines.txt" if loop.startswith("E1") else "final/final_guidelines.txt")
            guideline = guideline_path.read_text(encoding="utf-8")
            ghash = sha(guideline)
            group = "original" if ghash == original_hash else "changed"
            guide_ref = f"guidelines/{ghash}.txt"
            (OUT / guide_ref).write_bytes(guideline.encode("utf-8"))
            schema_path = folder / "inputs/entity_schema.json"
            rows = read(schema_path)
            entities = [modules["types"].EntityDefinition(r) if isinstance(r, str) else modules["types"].EntityDefinition(**r) for r in rows]
            config = modules["types"].OutputConfiguration(True, True)
            schema = modules["providers._shared"].annotation_json_schema(config)
            settings = read(folder / "inputs/resolved_run_config.json")["settings"]
            request_config = types.SimpleNamespace(model=settings["model"], effort=settings["effort"],
                max_output_tokens=settings["max_tokens"], thinking_display=settings["thinking"]["display"], json_schemas={TASK: schema})
            calls_path = folder / "calls.json"
            calls_by_hash = defaultdict(list)
            for c in read(calls_path):
                if c["loop"] == loop and c["task"] == TASK:
                    calls_by_hash[c["prompt_sha256"]].append(c)
            run_counts = Counter()
            if {p.stem for p in (folder / "valid_predictions").glob("*.json")} != set(gold_docs):
                raise ValueError(f"prediction files differ from valid100: {run}")
            for doc, (gold_path, gold) in gold_docs.items():
                pred_path = folder / "valid_predictions" / f"{doc}.json"
                pred = read(pred_path)
                text = gold["text"]
                if pred["text"] != text:
                    raise ValueError(f"saved text differs from valid text: {run}/{doc}")
                prompt = build_prompt(pure, text, guideline, entities, config)
                phash = sha(prompt)
                params = pure.build_params(request_config, TASK, prompt)
                # The runner deliberately fixes 64000 in its cache identity even
                # when requests use a higher output cap. No provider is created.
                params["max_tokens"] = 64000
                request_hash = sha(json.dumps(params, sort_keys=True, ensure_ascii=False))
                found = reply_map.get((loop, TASK, phash), [])
                call_records = calls_by_hash.get(phash, [])
                for r in found:
                    m = r["meta"]
                    cid = sha(f"{loop}|{TASK}|{request_hash}|{m['occurrence']}|{m['attempt']}")[:48]
                    if cid != r["custom_id"] or cid != Path(r["reply_file"]).stem:
                        raise ValueError(f"full request custom_id mismatch: {run}/{doc}")
                    if m["prompt_chars"] != len(prompt):
                        raise ValueError(f"prompt length mismatch: {run}/{doc}")
                expected = Counter(denotation_key(d) for d in pred["denotations"])
                status, exact, diagnostics = choose_exact(found, call_records, expected, text, entities, modules, pure)
                drecord = {"run": run, "doc": doc, "loop": loop, "task": TASK,
                           "prompt_sha256": phash, "prompt_chars": len(prompt), "request_params_sha256": request_hash,
                           "request_identity_max_tokens": 64000, "provenance_status": status,
                           "calls_file": rel(calls_path), "recorded_calls": call_records,
                           "candidate_replies": diagnostics, "saved_prediction_file": rel(pred_path),
                           "saved_prediction_sha256": sha(pred_path.read_bytes()), "saved_prediction_count": sum(expected.values()),
                           "text_ref": f"documents/{doc}.txt", "text_sha256": sha(text),
                           "guideline_path": rel(guideline_path), "guideline_sha256": ghash,
                           "guideline_snapshot": guide_ref, "guideline_group": group}
                jsonline(doc_file, drecord)
                totals["documents"] += 1
                totals[status + "_documents"] += 1
                run_counts[status + "_documents"] += 1
                if status != "exact":
                    failures.append({"run": run, "doc": doc, "status": status, "candidates": diagnostics})
                trace_by_key = defaultdict(list)
                if exact:
                    reply, aligned, traces = exact
                    for trace in traces:
                        jsonline(raw_file, {"run": run, "doc": doc, "reply_file": reply["reply_file"],
                            "custom_id": reply["custom_id"], "meta": reply["meta"], **trace})
                        totals["raw_items"] += 1
                        if trace["dropped"]:
                            drops[trace["drop_reason"]] += 1
                        else:
                            a = trace["aligned"]
                            trace_by_key[a["start"], a["end"], a["entity"]].append(trace)
                score_rows = scoring(run, doc, pred["denotations"], gold["denotations"], text, error_map)
                for pi, (denotation, score) in enumerate(zip(pred["denotations"], score_rows)):
                    key = denotation_key(denotation)
                    case_key = "P" + sha(json.dumps([run, doc, pi, list(key)], separators=(",", ":")))[:20]
                    matches = trace_by_key.get(key, [])
                    annotation_exact = status == "exact" and len(matches) == 1
                    trace = matches[0] if annotation_exact else None
                    meta = {"case_key": case_key, "run": run, "doc": doc,
                            "prediction_index": pi, "prediction_id": denotation.get("id"),
                            "start": key[0], "end": key[1], "pred_label": key[2], "pred_text": text[key[0]:key[1]],
                            "kind": score["kind"], "guideline_group": group,
                            "guideline_path": rel(guideline_path), "guideline_sha256": ghash,
                            "guideline_snapshot": guide_ref, "text_ref": f"documents/{doc}.txt",
                            "prompt_sha256": phash, "provenance_status": status,
                            "annotation_provenance_exact": annotation_exact,
                            "reply_file": exact[0]["reply_file"] if exact else None,
                            "custom_id": exact[0]["custom_id"] if exact else None,
                            "raw_item_index": trace["raw_item_index"] if trace else None}
                    record = {**meta, "scoring": score, "saved_prediction": denotation,
                              "saved_prediction_file": rel(pred_path), "loop": loop, "task": TASK,
                              "request_params_sha256": request_hash,
                              "reply_meta": exact[0]["meta"] if exact else None,
                              "raw_version": trace["raw"] if trace else None,
                              "aligned_version": trace["aligned"] if trace else None,
                              "raw_rationale": trace["raw"].get("rationale") if trace else None,
                              "cited_section": trace["raw"].get("guideline_section") if trace else None,
                              "context_start": max(0, key[0] - 100),
                              "context": text[max(0, key[0] - 100):min(len(text), key[1] + 100)]}
                    jsonline(index_file, record)
                    totals["predictions"] += 1
                    run_counts["predictions"] += 1
                    run_counts[score["kind"]] += 1
                    totals["exact_predictions"] += annotation_exact
                    if annotation_exact and score["kind"] in STATES:
                        candidates.append(meta)
                        selection_lookup[case_key] = record
            saved_metrics = read(folder / "valid_metrics.json")["strict_match"]["pubannotation"]
            tp = run_counts["correct"]
            score_equal = (tp, run_counts["predictions"] - tp, gold_total - tp) == (
                saved_metrics["true_positives"], saved_metrics["false_positives"], saved_metrics["false_negatives"])
            if not score_equal:
                raise ValueError(f"strict count disagreement with saved metrics: {run}")
            run_manifest.append({"run": run, "loop": loop, "guideline_group": group,
                "guideline_path": rel(guideline_path), "guideline_sha256": ghash,
                "guideline_file_sha256": sha(guideline_path.read_bytes()), "guideline_snapshot": guide_ref,
                "schema_path": rel(schema_path), "schema_sha256": sha(schema_path.read_bytes()),
                "calls_path": rel(calls_path), "calls_sha256": sha(calls_path.read_bytes()),
                "counts": dict(run_counts), "saved_strict_counts_equal": score_equal})
            print(f"{loop}: exact {run_counts['exact_documents']}/100, predictions {run_counts['predictions']}", flush=True)
    selected, buckets = select(candidates)
    if [c["case_key"] for c in select(list(reversed(candidates)))[0]] != [c["case_key"] for c in selected]:
        raise AssertionError("selection depends on input traversal order")
    if len({(c["doc"], c["start"], c["end"]) for c in selected}) != len(selected):
        raise AssertionError("duplicate selected document/span")
    algorithm = {
        "seed": SEED, "workload_cap": 16, "per_cell_target": 2,
        "cell_order": [[g, k] for g in ("original", "changed") for k in STATES],
        "algorithm": "Two round-robin passes over cell_order. Within a cell require different documents, global unique (doc,start,end), and global document count <2. Lexicographic preference: unused document, unused prediction label, smaller label count, unused guideline text hash, smaller guideline count, unused run, smaller run count, SHA256(seed|case_key). No relaxation or replacement if insufficient candidates. Assign opaque R IDs by SHA256(seed|blind|case_key) after selection.",
        "eligibility": "unique recorded calls.json custom_id association, full keyed request hash, exact full replayed (start,end,label) multiset, unique raw item identity, scoring kind in four states",
        "original_definition": "SHA256 of UTF-8 guideline text read with universal newline conversion equals original guideline text hash; method labels ignored",
        "excluded_selection_inputs": ["rationale", "guideline_section", "rationale_missingness", "validation_F1"],
        "limitation_zh": "16 是工作量上限，不是统计充分性保证；按 gold 评分状态选样，不是与 gold 无关的抽样。不因语义发现替换或追加样本。unpaired 组计数不能衡量改进。"}
    counts = []
    for cell, pool in buckets.items():
        counts.append({"guideline_group": cell[0], "kind": cell[1], "eligible_predictions": len(pool),
                       "eligible_documents": len({c["doc"] for c in pool}),
                       "eligible_runs": len({c["run"] for c in pool}),
                       "prediction_labels": dict(Counter(c["pred_label"] for c in pool)),
                       "selected": sum((c["guideline_group"], c["kind"]) == cell for c in selected)})
    manifest = {"algorithm": algorithm, "original_guideline_sha256": original_hash,
                "eligible_counts_by_cell": counts, "selected": selected,
                "selection_sha256": sha(json.dumps(selected, ensure_ascii=False, sort_keys=True)),
                "selected_label_counts": dict(Counter(c["pred_label"] for c in selected)),
                "selected_document_counts": dict(Counter(c["doc"] for c in selected)),
                "gold_and_status": [{"case_id": c["case_id"], "case_key": c["case_key"],
                    "scoring": selection_lookup[c["case_key"]]["scoring"]} for c in selected]}
    # Freeze the selection before constructing any rationale-bearing cards.
    dump("selection_manifest.json", manifest)
    print(f"Frozen selection: {len(selected)} cases", flush=True)
    with (OUT / "eligible_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        names = list(candidates[0]) + ["gold_labels"] if candidates else ["case_key"]
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        for c in candidates:
            gold_labels = sorted({g["label"] for g in selection_lookup[c["case_key"]]["scoring"]["all_gold_overlaps"]})
            writer.writerow({**c, "gold_labels": "|".join(gold_labels)})
    cards, markdown = [], ["# Rationale 审核案例", "", "请先独立核对原文、实际指南和预测。完整文档与完整指南均为不含 gold 的文本副本。评分状态与 gold 单独保存。", ""]
    for chosen in selected:
        record = selection_lookup[chosen["case_key"]]
        card = {k: record[k] for k in ("case_key", "doc", "prediction_index", "prediction_id", "start", "end", "pred_label", "pred_text",
                 "text_ref", "guideline_path", "guideline_sha256", "guideline_snapshot", "prompt_sha256", "reply_file", "custom_id",
                 "raw_item_index", "raw_version", "aligned_version", "raw_rationale", "cited_section", "context_start", "context")}
        card["case_id"] = chosen["case_id"]
        cards.append(card)
        markdown += [f"## {card['case_id']}", "", f"文档：{card['doc']}。完整原文：[text]({card['text_ref']})。", "",
            f"实际预测：`{card['pred_label']}`，字符区间 `[{card['start']}, {card['end']})`，文本 {json.dumps(card['pred_text'], ensure_ascii=False)}。", "",
            f"完整实际指南：[guideline]({card['guideline_snapshot']})。原路径：`{card['guideline_path']}`。文本 SHA256：`{card['guideline_sha256']}`。", "",
            f"上下文起点：{card['context_start']}。", "", "```text", card["context"], "```", "",
            "原始预测版本：", "", "```json", json.dumps(card["raw_version"], ensure_ascii=False, indent=2), "```", "",
            "对齐后的预测版本：", "", "```json", json.dumps(card["aligned_version"], ensure_ascii=False, indent=2), "```", "",
            "理由：", "", card["raw_rationale"] if card["raw_rationale"] is not None else "（字段缺失或 null）", "",
            "模型引用：", "", card["cited_section"] if card["cited_section"] is not None else "（字段缺失或 null）", "",
            f"来源：`{card['reply_file']}`，raw item index `{card['raw_item_index']}`，custom_id `{card['custom_id']}`。", ""]
    dump("sample.json", {"cases": cards})
    (OUT / "sample_blinded.md").write_bytes(("\n".join(markdown) + "\n").encode("utf-8"))
    dump("run_manifest.json", run_manifest)
    dependencies = ["types.py", "prompts.py", "prompt_utils.py", "text_utils.py", "pipeline.py", "pubannotation.py", "providers/_shared.py", "providers/claude.py"]
    diagnostics = {"totals": dict(totals), "drop_reasons": dict(drops), "failures": failures,
                   "original_runs": sum(r["guideline_group"] == "original" for r in run_manifest),
                   "changed_runs": sum(r["guideline_group"] == "changed" for r in run_manifest),
                   "eligible_predictions": len(candidates), "selected_predictions": len(selected),
                   "reply_files_by_task": dict(task_counts),
                   "multiple_reply_hash_groups": sum(len(v) > 1 for v in reply_map.values()),
                   "pure_code_sha256": {rel(SOURCE / p): sha((SOURCE / p).read_bytes()) for p in dependencies},
                   "utility_sha256": sha(Path(__file__).read_bytes()), "error_rows_sha256": sha(ERRORS.read_bytes()),
                   "checks": {"recorded_call_and_reply_custom_id": totals["exact_documents"] == 3000,
                              "full_request_key_hash": totals["exact_documents"] == 3000,
                              "full_replay_multiset_equality": totals["exact_documents"] == 3000,
                              "saved_strict_counts_all_30": all(r["saved_strict_counts_equal"] for r in run_manifest),
                              "selection_order_independent": True,
                              "all_four_prediction_labels_selected": len({c["pred_label"] for c in selected}) == 4},
                   "ambiguity_policy": "Compare recorded call-associated replies only; require one full replay-equal candidate. Multiple equal candidates remain ambiguous and ineligible. No arbitrary earliest/latest or text-list selection.",
                   "offset_policy": "Pure project alignment operates in normalized text offsets. Original offsets, normalized aligned offsets, document slice, and drop reasons are retained; no additional repair is invented."}
    dump("diagnostics.json", diagnostics)
    print(json.dumps({"totals": dict(totals), "drops": dict(drops), "eligible": len(candidates), "selected": len(selected), "output": rel(OUT)}, ensure_ascii=False), flush=True)
    return 0 if totals["exact_documents"] == 3000 and len(selected) == 16 else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, AssertionError, OSError) as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        dump("fatal_diagnostic.json", {"error_type": type(exc).__name__, "error": str(exc)})
        raise
