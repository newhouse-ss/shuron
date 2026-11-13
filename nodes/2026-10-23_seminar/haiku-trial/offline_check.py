"""Offline checks of ClaudeProvider and the trial runner's result handling. No network, no API key.

1. read_message: plain JSON passes, a fenced JSON reply is unwrapped, refusal / max_tokens / no text raise.
2. complete() through a fake client that records the request: the params sent are build_params' output.
3. A batch-style result replayed through ReplayProvider and annotate_with_guidelines: spans come out aligned,
   "Specific Disease" is mapped to the schema name, and a changed prompt is refused.
4. Cost: a prompt over 100,000 tokens is priced on the higher card; batch halves the price.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_haiku as rh  # noqa: E402
from run_haiku import rs  # noqa: E402

from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402

TASK = rh.TASK


def message(text: str, stop: str = "end_turn") -> dict:
    return {"id": "msg_test", "model": rh.MODEL, "stop_reason": stop, "stop_details": None,
            "content": [{"type": "thinking", "thinking": "summary", "signature": "x"},
                        {"type": "text", "text": text}],
            "usage": {"input_tokens": 2500, "output_tokens": 9000, "output_tokens_details": {"thinking_tokens": 8000}}}


def expect_error(fn, label: str) -> None:
    try:
        fn()
    except RuntimeError as exc:
        print(f"ok   {label}: raises ({str(exc)[:70]})")
        return
    raise AssertionError(f"{label}: did not raise")


def main() -> None:
    p = rh.make_provider("H_high")
    body = '{"annotations": []}'
    for reply, path in ((body, "plain"), (f"```json\n{body}\n```", "fence"),
                        (f"Here are the annotations:\n{body}\nDone.", "brace")):
        assert p.read_message(message(reply), TASK) == body and p.last_extraction == path, (reply, path)
    assert p.read_message(message("no json here"), TASK) == "no json here" and p.last_extraction == "unparsed"
    assert p.read_message(message("prose"), "infer_discrepancy_patterns") == "prose" and p.last_extraction == "plain"
    print("ok   read_message: plain, fenced and prose-wrapped JSON read; non-JSON passed on as 'unparsed'; "
          "text tasks untouched")
    params = rh.make_provider("H_xhigh").build_params(TASK, "x")
    assert params["output_config"] == {"effort": "xhigh", "format": {"type": "json_schema", "schema": rh.SCHEMA}}
    assert "format" not in rh.make_provider("H_high").build_params("infer_discrepancy_patterns", "x")["output_config"]
    print("ok   H_xhigh sends effort xhigh plus the JSON schema; text tasks get no schema")
    item = rh.SCHEMA["properties"]["annotations"]["items"]
    prompt_fields = ["start", "end", "text", "entity", "rationale", "guideline_section"]
    assert list(item["properties"]) == prompt_fields and item["required"] == prompt_fields
    assert item["additionalProperties"] is False and rh.SCHEMA["additionalProperties"] is False
    assert [item["properties"][f]["type"] for f in prompt_fields] == ["integer"] * 2 + ["string"] * 4
    print(f"ok   schema = the prompt's field list {prompt_fields}, all required, no extra keys")
    expect_error(lambda: p.read_message(message(body, "refusal"), TASK), "refusal")
    expect_error(lambda: p.read_message(message(body, "max_tokens"), TASK), "max_tokens")
    expect_error(lambda: p.read_message(message("  "), TASK), "no text")

    class FakeStream:
        def __init__(self, sent: dict) -> None:
            self.sent = sent

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_final_message(self):
            class Final:
                @staticmethod
                def to_dict():
                    return message(body)
            return Final()

    class FakeClient:
        def __init__(self) -> None:
            self.sent: dict = {}
            self.messages = self

        def stream(self, **params):
            self.sent = params
            return FakeStream(params)

    fake = FakeClient()
    q = rh.make_provider("H_high")
    q.client = fake
    assert q.complete(TASK, "PROMPT") == body and fake.sent == q.build_params(TASK, "PROMPT")
    assert "temperature" not in fake.sent and fake.sent["output_config"]["effort"] == "high"
    assert fake.sent["output_config"]["format"]["schema"] == rh.SCHEMA
    assert q.last_usage["output_tokens"] == 9000
    print("ok   complete(): sends build_params unchanged (no temperature, effort high), keeps usage")

    guideline, documents, entities = rs.load_inputs()
    doc = documents[rs.PROBE_DOC]
    prompt = rs.render_prompt(doc, guideline, entities)
    gold = doc.gold_annotations[:3]
    reply = {"annotations": [{"start": a.start, "end": a.end, "text": a.text,
                              "entity": "Specific Disease" if a.entity == "SpecificDisease" else a.entity,
                              "rationale": "r", "guideline_section": "s"} for a in gold]}
    replay = rh.ReplayProvider(p, message(json.dumps(reply)), rs.sha256(prompt))
    out = annotate_with_guidelines(doc.text, guideline, entities, replay, instructions="",
                                   output_configuration=rs.OUTPUT_CONFIGURATION).annotations
    assert [(a.start, a.end, a.entity) for a in out] == [(a.start, a.end, a.entity) for a in gold], out
    print(f"ok   replay: {len(out)} gold spans back unchanged, label spelling mapped "
          f"({sorted({a.entity for a in gold})})")
    stale = rh.ReplayProvider(p, message(json.dumps(reply)), "0" * 64)
    expect_error(lambda: annotate_with_guidelines(doc.text, guideline, entities, stale, instructions="",
                                                  output_configuration=rs.OUTPUT_CONFIGURATION), "changed prompt")

    small = {"input_tokens": 2500, "output_tokens": 9000}
    large = {"input_tokens": 60_000, "cache_read_input_tokens": 50_000, "output_tokens": 9000}
    s_std, s_batch = rh.cost_jpy(small, False), rh.cost_jpy(small, True)
    expected = (2500 * 0.10 + 9000 * 0.50) / 1e6 * rs.JPY_PER_USD
    assert abs(s_std - expected) < 1e-9 and abs(s_batch - expected / 2) < 1e-9
    l_std = rh.cost_jpy(large, False)
    expected_large = (60_000 * 0.50 + 50_000 * 0.05 + 9000 * 2.50) / 1e6 * rs.JPY_PER_USD
    assert abs(l_std - expected_large) < 1e-9
    print(f"ok   cost: 2,500 in / 9,000 out = JPY {s_std:.3f} standard, {s_batch:.3f} batch; "
          f"a 110,000-token prompt uses the higher card (JPY {l_std:.3f})")

    import contextlib
    import io

    def picked(high, xhigh) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rh.effort_rule({"H_high": {"f1": high}, "H_xhigh": {"f1": xhigh}})
        return buffer.getvalue().strip().rsplit(" ", 1)[-1]

    base = [0.80, 0.81, 0.79, 0.80, 0.82, 0.78, 0.80, 0.81]
    up = [x + 0.05 for x in base]
    assert picked(base, base) == "H_high" and picked(base, up) == "H_xhigh" and picked(up, base) == "H_high"

    def verdict(high, xhigh) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rh.effort_rule({"H_high": {"f1": high}, "H_xhigh": {"f1": xhigh}})
        return next(line for line in buffer.getvalue().splitlines() if "->" in line).split("-> ")[1]

    assert verdict(base, up) == "H_xhigh significantly better"
    assert verdict(up, base) == "H_high significantly better"
    assert verdict(base, base) == "no significant difference"
    print("ok   two-sided verdict: xhigh better / high better / no significant difference")
    assert list(rh.ARMS) == ["H_high", "H_xhigh", "H_max"]
    print("ok   arms high, xhigh, max; effort rule: equal -> high; xhigh higher -> xhigh; xhigh lower -> high")

    def max_pick(xhigh, top) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rh.effort_rule({"H_high": {"f1": base}, "H_xhigh": {"f1": xhigh}, "H_max": {"f1": top}})
        return next(line for line in buffer.getvalue().splitlines() if line.startswith("max rule")).rsplit(" ", 1)[-1]

    assert max_pick(base, up) == "H_max" and max_pick(base, base) == "H_xhigh" and max_pick(up, base) == "H_xhigh"
    assert rh.make_provider("H_max").build_params(TASK, "x")["output_config"]["effort"] == "max"
    print("ok   max rule: max higher -> max; equal or lower -> xhigh; H_max sends effort max")
    print("all offline checks passed")


if __name__ == "__main__":
    main()
