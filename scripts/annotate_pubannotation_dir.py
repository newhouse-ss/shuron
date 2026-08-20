from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from llm_guideline_moderation.dataset_annotation import annotate_pubannotation_directory
from llm_guideline_moderation.dotenv import load_dotenv
from llm_guideline_moderation.providers.deepseek import DeepSeekProvider
from llm_guideline_moderation.providers.gemini import GeminiProvider
from llm_guideline_moderation.providers.openai import OpenAIProvider
from llm_guideline_moderation.types import EntityDefinition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Annotate every PubAnnotation JSON file in a directory with the final refined guidelines."
    )
    parser.add_argument("--input-dir", required=True, help="Directory containing PubAnnotation JSON files")
    parser.add_argument("--guidelines", required=True, help="Path to the final guidelines text file")
    parser.add_argument("--entities", required=True, help="Path to the entity schema JSON file")
    parser.add_argument("--output-dir", required=True, help="Directory where annotated PubAnnotation JSON files will be written")
    parser.add_argument("--provider", default="openai", choices=["openai", "gemini", "deepseek"], help="LLM provider")
    parser.add_argument("--model", help="Model name. On Azure, defaults to the configured deployment.")
    parser.add_argument(
        "--reasoning-effort",
        help="OpenAI reasoning depth: low, medium, high, or xhigh",
    )
    parser.add_argument("--thinking-budget", type=int, help="Gemini thinking budget in tokens")
    parser.add_argument(
        "--azure-model-key",
        help="Use Azure OpenAI, reading AZURE_OPENAI_<key>_* from the environment or .env",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=64000,
        help="Completion token cap. Must cover reasoning tokens as well as the answer.",
    )
    return parser


def _build_provider(
    provider_name: str,
    model_name: str | None,
    *,
    reasoning_effort: str | None = None,
    thinking_budget: int | None = None,
    azure_model_key: str | None = None,
    max_output_tokens: int = 64000,
):
    if provider_name == "openai":
        if azure_model_key:
            overrides = {"model": model_name} if model_name else {}
            return OpenAIProvider.from_azure_env(
                azure_model_key,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
                **overrides,
            )
        return OpenAIProvider(
            model=model_name or "gpt-5",
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
    if provider_name == "gemini":
        return GeminiProvider(model=model_name, thinking_budget=thinking_budget)
    if provider_name == "deepseek":
        return DeepSeekProvider(model=model_name)
    raise ValueError(f"Unsupported provider: {provider_name}")


def main() -> None:
    args = build_parser().parse_args()
    load_dotenv()
    guidelines = Path(args.guidelines).read_text(encoding="utf-8")
    entity_rows = json.loads(Path(args.entities).read_text(encoding="utf-8"))
    entities = [
        EntityDefinition(name=row) if isinstance(row, str) else EntityDefinition(**row)
        for row in entity_rows
    ]
    provider = _build_provider(
        args.provider,
        args.model,
        reasoning_effort=args.reasoning_effort,
        thinking_budget=args.thinking_budget,
        azure_model_key=args.azure_model_key,
        max_output_tokens=args.max_output_tokens,
    )
    annotate_pubannotation_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        guidelines=guidelines,
        entities=entities,
        provider=provider,
    )


if __name__ == "__main__":
    main()
