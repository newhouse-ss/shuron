"""Offline regression coverage for pilot parsing, batching, resume and scoring."""

from __future__ import annotations

import concurrent.futures as cf
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (  # noqa: E402
    FIND, S_PLUS, TYPE, hb, load_inputs, output_schema, parse_annotations, prompt, read_json, type_candidates,
)
from run_pilot import arm_dir, call, queue_factory  # noqa: E402
import score_pilot  # noqa: E402
from score_pilot import document_counts, paired_comparisons  # noqa: E402
from common import write_json  # noqa: E402


def message(body, stop="end_turn"):
    return {"content": [{"type": "text", "text": body}], "stop_reason": stop,
            "usage": {"input_tokens": 100, "output_tokens": 200}}


class FakeBatches:
    def __init__(self, response):
        self.response, self.store, self.created = response, {}, []

    def create(self, requests):
        batch_id = f"fake_{len(self.created)}"
        self.created.append(batch_id)
        self.store[batch_id] = [(r["custom_id"], self.response(r["params"])) for r in requests]
        return SimpleNamespace(id=batch_id)

    def retrieve(self, batch_id):
        assert batch_id in self.store
        return SimpleNamespace(processing_status="ended")

    def results(self, batch_id):
        return [SimpleNamespace(custom_id=cid, result=SimpleNamespace(to_dict=lambda result=result: result))
                for cid, result in self.store[batch_id]]


def test_batch_resume_retries(root):
    guideline, entities = load_inputs()
    counter = [0]
    def respond(params):
        assert params["model"] == "claude-haiku-5-5" and params["max_tokens"] == 128000
        assert params["thinking"]["type"] == "adaptive" and params["output_config"]["effort"] == "xhigh"
        counter[0] += 1
        body, stop = ("{}", "refusal") if counter[0] == 1 else (("invalid json", "end_turn") if counter[0] == 2
                                                           else ('{"annotations": []}', "end_turn"))
        return {"type": "succeeded", "message": message(body, stop)}
    batches = FakeBatches(respond)
    queue = hb.BatchQueue(root / "_batchqueue", SimpleNamespace(messages=SimpleNamespace(batches=batches)),
                          float("inf"), quiet=0, poll=0)
    factory = queue_factory(queue, entities)
    queue.start()
    text = prompt("S", "Fake disease", guideline, entities)
    directory = arm_dir(root, "S", 1)
    assert call(directory, "fake.json", "S", "S", 1, text, factory, entities) == {"annotations": []}
    saved = read_json(directory / "raw_replies/fake/S.json")
    assert len(saved["attempts"]) == 3 and saved["cost_jpy"] > 0
    before = len(batches.created)
    # Replay both the per-call checkpoint and the underlying queue without a new request.
    assert call(directory, "fake.json", "S", "S", 1, text, factory, entities) == {"annotations": []}
    assert factory("S", 1, "S", "fake.json").complete("annotate_with_guidelines", text) == '{"annotations": []}'
    assert len(batches.created) == before
    factory("S", 2, "S", "fake.json").complete("annotate_with_guidelines", text)
    assert len(batches.created) == before + 1  # Identical prompt in run 2 gets its own reply.

    # All three structured schemas reach the real QueueProvider/BatchQueue request builder.
    schemas = []
    def schema_reply(params):
        schema = params["output_config"]["format"]["schema"]
        schemas.append(schema)
        key = next(iter(schema["properties"]))
        return {"type": "succeeded", "message": message(json.dumps({key: []}))}
    batches.response = schema_reply
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(factory("T" if s in ("find", "type") else "S+", 1, s, "schema.json").complete,
                               "annotate_with_guidelines", prompt(s, "Fake disease", guideline, entities, []))
                   for s in ("S+", "find", "type")]
        for future in futures:
            future.result()
    assert {json.dumps(s, sort_keys=True) for s in schemas} == {
        json.dumps(output_schema(s, entities), sort_keys=True) for s in ("S+", "find", "type")}

    # Exhaustion is persistent on resume and never exceeds three tries.
    calls = [0]
    def refused(params):
        calls[0] += 1
        return {"type": "succeeded", "message": message("{}", "refusal")}
    batches.response = refused
    for _ in range(2):
        try:
            factory("S", 1, "S", "refused.json").complete("annotate_with_guidelines", text)
        except RuntimeError as exc:
            assert "no usable reply in 3 tries" in str(exc)
        else:
            raise AssertionError("refused replies were accepted")
    assert calls[0] == 3


def test_parser_and_scoring():
    _, entities = load_inputs()
    text = "alpha beta gamma"
    rows = [{"start": 2, "end": 7, "text": "alpha", "entity": "Specific Disease",
             "rationale": "r", "guideline_section": "s", "excluded": "yes"},
            {"start": 6, "end": 10, "text": "beta", "entity": "DiseaseClass",
             "rationale": "r", "guideline_section": "s", "excluded": "no"}]
    track1, track2 = parse_annotations("S+", {"annotations": rows}, text, entities)
    assert [(a.start, a.end, a.entity) for a in track1] == [(6, 10, "DiseaseClass")]
    assert [(a.start, a.end, a.entity) for a in track2] == [(0, 5, "SpecificDisease"), (6, 10, "DiseaseClass")]
    typed1, typed2, undecided = type_candidates(track2, {"decisions": [
        {"id": 1, "entity": "NONE", "rationale": "r", "guideline_section": "s"},
        {"id": 1, "entity": "SpecificDisease", "rationale": "r", "guideline_section": "s"},
        {"id": 999, "entity": "SpecificDisease", "rationale": "r", "guideline_section": "s"}]}, entities)
    assert not typed1 and undecided == 1 and all(a.entity == "Candidate" for a in typed2)
    gold = {"text": text, "denotations": [{"span": {"begin": 0, "end": 5}, "obj": "SpecificDisease"},
                                           {"span": {"begin": 6, "end": 10}, "obj": "DiseaseClass"}]}
    # A wrong type and boundary still prevent a true miss. Nonoverlap predictions count separately.
    pred = {"text": text, "denotations": [{"span": {"begin": 1, "end": 3}, "obj": "Candidate"},
                                           {"span": {"begin": 11, "end": 16}, "obj": "Candidate"}]}
    assert document_counts("synthetic", gold, pred) == {
        "true_misses": 1, "misses_by_gold_label": {"DiseaseClass": 1}, "nonoverlap_predictions": 1}
    names = [f"d{i}" for i in range(200)]
    for values, outcome in (((2, 2, 1), "pass"), ((2, 0, 1), "wins S only, not S+"),
                            ((1, 0, 1), "does not win S"), ((0, 2, 1), "does not win S")):
        means = {arm: dict.fromkeys(names, value) for arm, value in zip(("S", "S+", "T"), values)}
        result = paired_comparisons(means, names)
        assert result["outcome"] == outcome and result["resamples"] == 10000
    varying = {arm: {n: (i % 5) + offset for i, n in enumerate(names)}
               for arm, offset in (("S", 2), ("S+", 1), ("T", 0))}
    assert paired_comparisons(varying, names) == paired_comparisons(varying, names)
    # A nonconstant two-document difference has three possible resampled sums.
    result = paired_comparisons({"S": {"a": 2, "b": 2}, "S+": {"a": 1, "b": 1},
                                 "T": {"a": 0, "b": 3}}, ["a", "b"])
    assert result["comparisons"]["T_minus_S"] == {"sum_difference": -1, "ci95": [-4, 2], "passes": False}


def test_fixed_texts():
    design = (Path(__file__).resolve().parents[3] / "notes/20261113_two_step_pilot_design.md").read_text(encoding="utf-8")
    paragraphs = [line[2:] for line in design.splitlines() if line.startswith("> ")]
    assert paragraphs == [S_PLUS, FIND, TYPE]
    _, entities = load_inputs()
    original = output_schema("S", entities)["properties"]["annotations"]["items"]["properties"]
    extended = output_schema("S+", entities)["properties"]["annotations"]["items"]["properties"]
    assert {k: v for k, v in extended.items() if k != "excluded"} == original


def test_scoring_files(root):
    """Exercise the complete scorer on synthetic data, never pilot gold or model replies."""
    _, entities = load_inputs()
    names = [f"fake{i:03d}.json" for i in range(200)]
    frozen = {"pilot_documents": names}
    originals = score_pilot.freeze_inputs, score_pilot.manifest, score_pilot.TRAIN
    training = root / "fake_train"
    run_root = root / "fake_run"
    gold = {"text": "alpha beta", "sourcedb": "synthetic", "denotations": [
        {"span": {"begin": 0, "end": 5}, "obj": "SpecificDisease"}]}
    predicted = {**gold, "denotations": []}
    for i, name in enumerate(names):
        write_json(training / name, {**gold, "sourceid": str(i)})
        for arm in ("S", "S+", "T"):
            for run in (1, 2):
                directory = arm_dir(run_root, arm, run)
                prediction = gold if arm == "T" else predicted
                for track in ("track1_predictions", "track2_predictions"):
                    write_json(directory / track / name, {**prediction, "sourceid": str(i)})
                write_json(directory / "documents" / name, {"status": "completed", "undecided": 0})
                write_json(directory / "raw_replies" / Path(name).stem / "fake.json", {
                    "document": name, "step": "fake", "provider_name": f"{arm}-{run}-{i}", "status": "ok",
                    "cost_jpy": 0, "attempts": []})
    write_json(run_root / "manifest.json", frozen)
    score_pilot.freeze_inputs = lambda root: (frozen, "", entities)
    score_pilot.manifest = lambda: frozen
    score_pilot.TRAIN = training
    try:
        result = score_pilot.score(run_root, root / "report_complete")
        assert result["outcome"] == "pass"
        assert result["comparisons"]["T_minus_S"]["sum_difference"] == -200
        assert result["arms"]["S"]["track1_f1_mean"] == 0
        assert result["arms"]["T"]["track1_f1_mean"] == 1
        # Threshold is strictly greater than 5%, not greater than or equal to it.
        for i, name in enumerate(names[:61]):
            path = arm_dir(run_root, "T", 1) / "raw_replies" / Path(name).stem / "fake.json"
            saved = read_json(path)
            saved.update(status="unusable", error="synthetic exhausted retries")
            write_json(path, saved)
            if i == 59:
                result = score_pilot.score(run_root, root / "report_exactly_five_percent")
                assert result["outcome"] == "pass" and result["unusable_fraction"] == 0.05
        result = score_pilot.score(run_root, root / "report_unusable")
        assert result["outcome"] == "inconclusive" and len(result["unusable_calls"]) == 61
        assert result["unusable_fraction"] > 0.05
        # Missing source units must never become zero-miss predictions.
        for name in names[:61]:
            path = arm_dir(run_root, "T", 1) / "raw_replies" / Path(name).stem / "fake.json"
            saved = read_json(path)
            saved["status"] = "ok"
            write_json(path, saved)
        path = arm_dir(run_root, "S", 1) / "documents" / names[0]
        saved = read_json(path)
        saved["status"] = "failed"
        write_json(path, saved)
        result = score_pilot.score(run_root, root / "report_missing")
        assert result["outcome"] == "inconclusive" and result["missing_units"] and result["unusable_fraction"] == 0
    finally:
        score_pilot.freeze_inputs, score_pilot.manifest, score_pilot.TRAIN = originals


def run_regressions(root):
    test_fixed_texts()
    test_parser_and_scoring()
    test_batch_resume_retries(root)
    test_scoring_files(root / "scoring")
    return "PILOT TESTS: PASS (fixed texts, alignment, labels, NONE/missing/repeated/unknown IDs, bootstrap outcomes, request schemas, retries, usage, resume, run isolation, synthetic end-to-end scoring, inconclusive cases)"
