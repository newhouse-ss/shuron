"""One tiny request to check whether background jobs on the Azure 5_4 deployment leave "queued".

Context: the first R3-minus-FALDH attempt (attempt1_20261016_queued/) had 12 of 12 background jobs
stay queued until cancelled. This sends one job through the same Responses API background path
with a trivial prompt, reasoning low and max_output_tokens 300 (worst case under 1 yen), and no
resubmission, so it ends within about 3 minutes either way. Every poll status is recorded.

    python todo-temp/r4-isolation/probe_queue.py
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import llm_guideline_moderation.providers.openai as oa  # noqa: E402
from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402

oa.MAX_RESUBMISSIONS = 0  # one submission only
load_dotenv()
provider = oa.OpenAIProvider.from_azure_env("5_4", reasoning_effort="low", max_output_tokens=300,
                                            use_background=True)
polls = []
original = provider._request_json
t0 = time.monotonic()


def wrapped(url, payload=None, method="POST"):
    response = original(url, payload=payload, method=method)
    polls.append({"t": round(time.monotonic() - t0, 1), "method": method,
                  **{k: response.get(k) for k in ("id", "model", "status", "created_at")}})
    return response


provider._request_json = wrapped
record = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "deployment": provider.model}
try:
    record.update(status="ok", text=provider.complete("refine_guidelines", "Reply with the single word OK."))
except Exception as exc:
    record.update(status="error", error=f"{type(exc).__name__}: {exc}")
record.update(usage=provider.last_usage, polls=polls, finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
out = Path(__file__).resolve().parent / f"probe_queue_{time.strftime('%Y%m%dT%H%M%S')}.json"
out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: record[k] for k in ("started", "finished", "status", "usage")}, ensure_ascii=False))
print("error:", record.get("error"), "| text:", record.get("text"))
print("status sequence:", [(p["t"], p["status"]) for p in polls])
print("saved:", out.name)
