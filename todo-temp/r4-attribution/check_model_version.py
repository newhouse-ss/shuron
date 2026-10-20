"""Identify which model version actually sits behind each Azure deployment.

The deployment *name* in .env is just a label - the response ``model`` field is
what Azure reports as the real backing model (e.g. gpt-5.2-... vs gpt-5.4-...).
Sends one tiny request per configured key. Prints no secrets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib import request

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402
from llm_guideline_moderation.providers.openai import azure_config_from_env  # noqa: E402

CANDIDATE_KEYS = ("4o", "5_1", "5_2", "5_4")


def probe(key: str) -> None:
    try:
        config = azure_config_from_env(key)
    except KeyError:
        print(f"\n=== {key} ===\n  SKIP  not configured")
        return

    endpoint = config["ENDPOINT"].rstrip("/")
    url = (
        f"{endpoint}/openai/deployments/{config['DEPLOYMENT_NAME']}"
        f"/chat/completions?api-version={config['API_VERSION']}"
    )
    payload = {
        "messages": [{"role": "user", "content": "Reply with: ok"}],
        "max_completion_tokens": 512,
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "api-key": config["API_KEY"]},
        method="POST",
    )

    print(f"\n=== {key} ===")
    print(f"  endpoint   : {endpoint}")
    print(f"  deployment : {config['DEPLOYMENT_NAME']}  (label from .env)")
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).replace("\n", " ")
        print(f"  request    : FAIL  {detail[:200]}")
        return

    print(f"  model      : {body.get('model')}  <- actual backing model")
    print(f"  fingerprint: {body.get('system_fingerprint')}")


def main() -> int:
    loaded = load_dotenv()
    print(f"loaded {len(loaded)} entries from .env" if loaded else "no .env found, using shell env")
    for key in CANDIDATE_KEYS:
        probe(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
