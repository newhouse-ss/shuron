"""Offline: run the pilot's run_all against a fake Batches API and count how many batches it sends.

No network, no credentials. Run from the repository root:
    python -B nodes/2026-11-16_seminar/two-step-pilot/scripts/pilot/check_two_batches.py
"""
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

PILOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PILOT))
import run_pilot  # noqa: E402

created = []


def reply(params):
    schema = params["output_config"]["format"]["schema"]
    key = next(iter(schema["properties"]))
    text = params["messages"][0]["content"]
    if isinstance(text, list):
        text = text[0]["text"]
    if key == "decisions":
        rows = [{"id": 1, "entity": "SpecificDisease", "rationale": "r", "guideline_section": "g"}]
    else:
        body = text.split("**TEXT TO ANNOTATE:**\n---\n", 1)[1].split("\n---", 1)[0]
        token = body.split()[0]
        fields = schema["properties"][key]["items"]["properties"]
        row = {"start": 0, "end": len(token), "text": token, "rationale": "r", "guideline_section": "g"}
        if "entity" in fields:
            row["entity"] = "SpecificDisease"
        if "excluded" in fields:
            row["excluded"] = "no"
        rows = [row]
    return {"type": "succeeded", "message": {"content": [{"type": "text", "text": json.dumps({key: rows})}],
                                             "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1}}}


class FakeBatches:
    def __init__(self):
        self.store = {}

    def create(self, requests):
        batch_id = f"fake_{len(created)}"
        created.append((batch_id, len(requests)))
        self.store[batch_id] = [(r["custom_id"], reply(r["params"])) for r in requests]
        return SimpleNamespace(id=batch_id)

    def retrieve(self, batch_id):
        return SimpleNamespace(processing_status="ended")

    def results(self, batch_id):
        return [SimpleNamespace(custom_id=cid, result=SimpleNamespace(to_dict=lambda result=result: result))
                for cid, result in self.store[batch_id]]


with tempfile.TemporaryDirectory() as tmp:
    client = SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches()))
    summary = run_pilot.run_all(Path(tmp) / "run", client, quiet=2, poll=0)
    print("status:", summary["status"], "logical calls:", summary["logical_calls"])
    print("batches sent:", len(created), [n for _, n in created])
