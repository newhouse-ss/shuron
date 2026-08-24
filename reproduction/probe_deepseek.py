"""Find out what the DeepSeek endpoint actually accepts, before spending the budget.

Four things have to be established empirically rather than assumed, because
getting any of them wrong wastes paid tokens on failed calls:

  1. model id      the catalogue is queried rather than guessed
  2. token param   DeepSeek follows the legacy `max_tokens`; the Azure GPT-5.x
                   deployments reject that name and need `max_completion_tokens`,
                   which is what the provider defaults to
  3. temperature   the whole point of the ablation. A reasoning model may reject
                   it with a 400, accept and ignore it, or honour it. Only the
                   third case makes the experiment possible, and the three are
                   told apart by whether two calls at temperature 0 return
                   byte-identical text while two calls at the default do not
  4. cost          one real annotation is priced by its token counts, so the
                   number of runs the remaining budget buys is arithmetic rather
                   than a guess

Nothing here writes to the experiment tree. Roughly a dozen small calls plus
four annotations of a single document.

    python reproduction/probe_deepseek.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402


def post(url: str, key: str, payload: dict, timeout: int = 300) -> tuple[int, dict | str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except Exception as exc:  # noqa: BLE001 - a probe reports failures, it does not raise
        return 0, f"{type(exc).__name__}: {exc}"


def get(url: str, key: str, timeout: int = 60) -> tuple[int, dict | str]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


def text_of(body: dict) -> str:
    try:
        return body["choices"][0]["message"]["content"] or ""
    except Exception:  # noqa: BLE001
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base", default="https://api.deepseek.com")
    parser.add_argument("--model", help="skip catalogue lookup and probe this id")
    parser.add_argument("--document", default="reproduction/dev_splits/ncbi_disease_dev10.json")
    parser.add_argument("--probe-tokens", type=int, default=4000,
                        help="output budget for the temperature samples; reasoning models "
                             "need enough room to finish thinking and still emit text")
    parser.add_argument("--annotate-tokens", type=int, default=32000,
                        help="output budget for the real annotation")
    args = parser.parse_args()

    load_dotenv()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("DEEPSEEK_API_KEY is not set")
    print(f"key loaded, {len(key)} chars, prefix {key[:6]}...\n")

    chat_url = f"{args.base.rstrip('/')}/chat/completions"

    # ---- 1. catalogue ----------------------------------------------------
    print("== 1. model catalogue ==")
    status, body = get(f"{args.base.rstrip('/')}/models", key)
    models: list[str] = []
    if status == 200 and isinstance(body, dict):
        models = [m.get("id", "?") for m in body.get("data", [])]
        for name in models:
            print(f"   {name}")
    else:
        print(f"   HTTP {status}: {str(body)[:300]}")
    candidates = [args.model] if args.model else models or ["deepseek-chat"]
    print()

    # ---- 2. token parameter ----------------------------------------------
    print("== 2. which token parameter is accepted ==")
    working: dict[str, str] = {}
    for model in candidates:
        for parameter in ("max_tokens", "max_completion_tokens"):
            status, body = post(chat_url, key, {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                parameter: 32,
            })
            if status == 200:
                usage = body.get("usage", {}) if isinstance(body, dict) else {}
                print(f"   {model:<26} {parameter:<24} OK   usage={usage}")
                working.setdefault(model, parameter)
            else:
                detail = body.get("error", {}).get("message", "") if isinstance(body, dict) else str(body)
                print(f"   {model:<26} {parameter:<24} HTTP {status}  {detail[:110]}")
    if not working:
        sys.exit("\nno model/parameter combination worked; nothing further to probe")
    model = next(iter(working))
    parameter = working[model]
    print(f"\n   -> using model={model}  token parameter={parameter}\n")

    # ---- 3. temperature ---------------------------------------------------
    print("== 3. is temperature honoured, ignored, or rejected ==")
    prompt = ("List three uncommon English words, comma separated, no explanation. "
              "Choose freely.")

    # These are reasoning models: the trivial probe above spent 25 of its 27
    # completion tokens on the reasoning trace. Too small a budget returns an
    # empty message, and two empty messages compare equal, which would read as
    # determinism. Give the reasoning room, and treat empty as a failed sample.
    def sample(temperature: float | None) -> tuple[int, str, dict]:
        payload = {"model": model,
                   "messages": [{"role": "user", "content": prompt}],
                   parameter: args.probe_tokens}
        if temperature is not None:
            payload["temperature"] = temperature
        status, body = post(chat_url, key, payload)
        if status != 200:
            return status, str(body)[:200], {}
        return status, text_of(body).strip(), body.get("usage", {})

    status, zero_a, usage_a = sample(0.0)
    if status != 200:
        print(f"   temperature=0 REJECTED, HTTP {status}: {zero_a[:200]}")
        print("   -> the ablation cannot be run on this model")
    else:
        _, zero_b, _ = sample(0.0)
        _, default_a, _ = sample(None)
        _, default_b, _ = sample(None)
        samples = {"temperature=0 a": zero_a, "temperature=0 b": zero_b,
                   "default a": default_a, "default b": default_b}
        for label, value in samples.items():
            shown = value[:90] if value else "(EMPTY - reasoning consumed the whole budget)"
            print(f"   {label:<16} {shown}")
        print(f"   first call usage: {json.dumps(usage_a)}")
        if any(not v for v in samples.values()):
            verdict = ("UNUSABLE: at least one sample came back empty. Raise "
                       "--probe-tokens and rerun; no conclusion can be drawn.")
        elif zero_a == zero_b and default_a != default_b:
            verdict = "HONOURED: temperature 0 is deterministic, the default is not"
        elif zero_a == zero_b and default_a == default_b:
            verdict = ("INCONCLUSIVE: both pairs identical. The prompt may be too "
                       "constrained to expose sampling; try a freer one.")
        else:
            verdict = "IGNORED: temperature 0 still varies, so the parameter buys nothing"
        print(f"   -> {verdict}")
    print()

    # ---- 4. cost of one real annotation -----------------------------------
    print("== 4. token cost of one real annotation ==")
    # Driven through the real pipeline rather than a hand-built prompt, so the
    # measurement is of the call the experiment will actually make.
    from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402
    from llm_guideline_moderation.providers.openai import OpenAIProvider  # noqa: E402
    from llm_guideline_moderation.sampling import load_sampled_document  # noqa: E402
    from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402

    names = json.loads((REPO_ROOT / args.document).read_text(encoding="utf-8"))["documents"]
    document = load_sampled_document(REPO_ROOT / "data/datasets/ncbi_disease/train" / names[0])
    guidelines = (REPO_ROOT / "data/guidelines/ncbi_disease_guidelines.txt").read_text(encoding="utf-8")
    entities = [EntityDefinition(name=r) for r in json.loads(
        (REPO_ROOT / "data/schemas/ncbi_entities.schema.json").read_text(encoding="utf-8"))]

    provider = OpenAIProvider(
        model=model,
        api_key=key,
        base_url=chat_url,
        token_param=parameter,
        max_output_tokens=args.annotate_tokens,
        use_background=False,
    )
    try:
        result = annotate_with_guidelines(
            text=document.text, guidelines=guidelines, entities=entities,
            provider=provider, instructions="",
            output_configuration=OutputConfiguration(include_rationale=True,
                                                     include_guideline_section=True),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"   annotation failed: {type(exc).__name__}: {exc}")
        return
    usage = provider.last_usage
    print(f"   document {document.filename}, {len(document.text)} chars, "
          f"{len(document.gold_annotations)} gold, {len(result.annotations)} predicted")
    print(f"   usage: {json.dumps(usage)}")
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total = prompt_tokens + completion_tokens
    print(f"\n   one annotation = {total} tokens ({prompt_tokens} in, {completion_tokens} out)")
    print("   scale that by the plan below, then check current DeepSeek pricing:")
    for label, calls in (("temperature ablation, 5 repeats x dev10 x 2 conditions", 100),
                         ("the same on dev30", 300),
                         ("one full moderation run on dev10", 50)):
        print(f"     {label:<52} {calls:>4} calls  ~{total * calls / 1000:>8.0f}k tokens")


if __name__ == "__main__":
    main()
