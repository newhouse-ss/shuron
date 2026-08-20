"""Check an Azure deployment before committing to a long run.

Verifies the deployment answers at all, that JSON mode works (the annotation
task depends on it), and that reasoning effort actually changes compute -
compared via usage.completion_tokens_details.reasoning_tokens, since an ignored
parameter would silently turn an H2 comparison into two identical runs.

Costs a handful of tiny requests. Prints no secrets.

    python reproduction/probe_azure.py --models 4o 5_1 5_2 5_4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402
from llm_guideline_moderation.providers.openai import (  # noqa: E402
    OpenAIProvider,
    azure_config_from_env,
)

EFFORTS = ("low", "medium", "high", "xhigh")
PUZZLE = (
    "A farmer must cross a river with a wolf, a goat and a cabbage. The boat "
    "holds the farmer plus one item. Give the shortest safe crossing sequence."
)


def _reasoning_tokens(usage: dict) -> int | None:
    return (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")


def _call(label: str, provider: OpenAIProvider, task: str, prompt: str) -> dict:
    try:
        text = provider.complete(task, prompt)
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).replace("\n", " ")
        print(f"  {label:<22} FAIL  {detail[:170]}")
        return {"ok": False, "error": detail[:400]}

    usage = provider.last_usage
    reasoning = _reasoning_tokens(usage)
    print(
        f"  {label:<22} OK    prompt={usage.get('prompt_tokens')} "
        f"completion={usage.get('completion_tokens')} reasoning={reasoning}"
        f"   -> {text.strip()[:32]!r}"
    )
    return {"ok": True, "usage": usage, "reasoning_tokens": reasoning}


def probe(model_key: str, max_output_tokens: int) -> dict:
    config = azure_config_from_env(model_key)
    key = config["API_KEY"]
    print(f"\n=== {model_key} ===")
    print(f"  endpoint    : {config['ENDPOINT']}")
    print(f"  deployment  : {config['DEPLOYMENT_NAME']}")
    print(f"  api_version : {config['API_VERSION']}")
    print(f"  api_key     : {key[:4]}...{key[-2:]}\n")

    findings: dict[str, object] = {"deployment": config["DEPLOYMENT_NAME"]}

    provider = OpenAIProvider.from_azure_env(model_key, max_output_tokens=max_output_tokens)
    findings["reachable"] = _call("reachable", provider, "probe", "Reply with: ok")
    if not findings["reachable"]["ok"]:
        print("\n  unreachable - skipping the rest")
        return findings

    findings["json_mode"] = _call(
        "json mode", provider, "annotate_with_guidelines",
        'Return exactly {"annotations": []} and nothing else.',
    )

    by_effort: dict[str, int | None] = {}
    for effort in EFFORTS:
        graded = OpenAIProvider.from_azure_env(
            model_key, reasoning_effort=effort, max_output_tokens=max_output_tokens
        )
        result = _call(f"effort={effort}", graded, "probe", PUZZLE)
        findings[f"effort::{effort}"] = result
        if result["ok"]:
            by_effort[effort] = result["reasoning_tokens"]

    print()
    accepted = [e for e in EFFORTS if by_effort.get(e) is not None]
    if not accepted:
        print("  reasoning effort : NOT SUPPORTED (non-reasoning model)")
    else:
        counts = {e: by_effort[e] for e in accepted}
        print(f"  reasoning tokens : {counts}")
        if len(set(counts.values())) == 1:
            print("  effort effect    : NONE - identical across levels, parameter ignored")
        else:
            print(f"  effort effect    : confirmed, max at '{max(counts, key=counts.get)}'")
    findings["reasoning_tokens_by_effort"] = by_effort
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Azure OpenAI deployments.")
    parser.add_argument("--models", nargs="+", required=True, help="Model keys, e.g. 4o 5_1 5_2 5_4")
    parser.add_argument("--max-output-tokens", type=int, default=32000)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "results" / "azure_probe.json"))
    args = parser.parse_args()

    loaded = load_dotenv()
    print(f"loaded {len(loaded)} entries from .env" if loaded else "no .env found, using the shell environment")

    findings = {}
    for model_key in args.models:
        try:
            findings[model_key] = probe(model_key, args.max_output_tokens)
        except KeyError as exc:
            print(f"\n=== {model_key} ===\n  SKIP  {exc}")
            findings[model_key] = {"error": str(exc)}

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwritten to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
