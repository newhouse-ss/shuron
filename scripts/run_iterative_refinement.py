from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from llm_guideline_moderation.artifacts import write_json
from llm_guideline_moderation.dotenv import load_dotenv
from llm_guideline_moderation.evaluation import PubAnnotationEvaluatorOptions
from llm_guideline_moderation.experiment import ExperimentSpec
from llm_guideline_moderation.iterative import run_iterative_refinement
from llm_guideline_moderation.layout import prepare_run_layout
from llm_guideline_moderation.providers.deepseek import DeepSeekProvider
from llm_guideline_moderation.providers.gemini import GeminiProvider
from llm_guideline_moderation.providers.openai import OpenAIProvider
from llm_guideline_moderation.sampling import (
    load_sampled_document,
    sample_pubannotation_documents,
)
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run iterative guideline refinement on a random train subset."
    )
    parser.add_argument("--spec", required=True, help="Path to experiment spec JSON")
    parser.add_argument("--threshold-f1", type=float, help="Override the strict-match micro F1 stopping threshold from the spec")
    parser.add_argument("--n-examples", type=int, help="Override the prompt evidence example count from the spec")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "deepseek"],
        help="Override provider from the spec",
    )
    parser.add_argument("--model", help="Override model from the spec")
    parser.add_argument("--output-dir", help="Override output directory from the spec")
    parser.add_argument(
        "--reasoning-effort",
        help="OpenAI reasoning depth: low, medium, high, or xhigh. Overrides the spec.",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        help="Gemini thinking budget in tokens. Overrides the spec.",
    )
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
    parser.add_argument(
        "--run-name",
        help="Output folder name. Defaults to '<experiment_id>_iterative'. "
             "Use something readable, e.g. 20260805_ncbi_gpt54-high_moderation.",
    )
    parser.add_argument(
        "--dev-split",
        help="JSON file listing the development documents by filename, as written by "
             "reproduction/make_dev_splits.py. Overrides the spec's sample_size and seed. "
             "Use this for size experiments: random.sample is only incidentally nested "
             "across different sample_size values, so an explicit list is what makes a "
             "smaller split a guaranteed subset of a larger one.",
    )
    return parser


def _build_provider(
    provider_name: str,
    model_name: str,
    *,
    reasoning_effort: str | None = None,
    thinking_budget: int | None = None,
    azure_model_key: str | None = None,
    max_output_tokens: int = 64000,
):
    if provider_name == "openai":
        # Reasoning depth has to reach the provider, otherwise the Section 4.3
        # low/high comparison cannot be run from the CLI at all.
        if azure_model_key:
            # model_name is optional here: left unset, the deployment named in
            # AZURE_OPENAI_<key>_DEPLOYMENT_NAME is used.
            overrides = {"model": model_name} if model_name else {}
            return OpenAIProvider.from_azure_env(
                azure_model_key,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
                **overrides,
            )
        return OpenAIProvider(
            model=model_name,
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
    spec = ExperimentSpec.from_json_file(args.spec)

    provider_name = args.provider or spec.model.provider
    azure_model_key = args.azure_model_key or spec.model.azure_model_key
    # On Azure the deployment name substitutes for the model name, so leave it
    # unset unless it was asked for explicitly.
    model_name = args.model or (None if azure_model_key else spec.model.model)
    reasoning_effort = args.reasoning_effort or spec.model.reasoning_effort
    thinking_budget = args.thinking_budget if args.thinking_budget is not None else spec.model.thinking_budget
    output_root = args.output_dir or spec.paths.output_dir
    source_dir = spec.moderation_sampling.source_dir_path
    sample_size = spec.moderation_sampling.sample_size or 10
    seed = spec.moderation_sampling.seed
    threshold_f1 = args.threshold_f1 if args.threshold_f1 is not None else spec.iterative.threshold_f1
    n_examples = args.n_examples if args.n_examples is not None else spec.iterative.n_examples

    guidelines = Path(spec.paths.guidelines_txt).read_text(encoding="utf-8")
    entity_rows = json.loads(Path(spec.paths.entity_schema_json).read_text(encoding="utf-8"))
    entities = [
        EntityDefinition(name=row) if isinstance(row, str) else EntityDefinition(**row)
        for row in entity_rows
    ]

    if args.dev_split:
        # An explicit document list, so that a size experiment compares the same
        # documents plus more rather than a different draw at each size.
        split = json.loads(Path(args.dev_split).read_text(encoding="utf-8"))
        sampled_documents = [
            load_sampled_document(Path(source_dir) / name) for name in split["documents"]
        ]
        sample_size, seed = len(sampled_documents), None
    else:
        sampled_documents = sample_pubannotation_documents(
            source_dir,
            sample_size=sample_size,
            seed=seed,
        )
    provider = _build_provider(
        provider_name,
        model_name,
        reasoning_effort=reasoning_effort,
        thinking_budget=thinking_budget,
        azure_model_key=azure_model_key,
        max_output_tokens=args.max_output_tokens,
    )
    # Everything the run does not depend on is written before the first API
    # call, and each iteration is checkpointed as it finishes. A failure part
    # way through then costs only the iteration in flight rather than the whole
    # run - a dropped connection during re-annotation has already wiped out a
    # 30 minute run once.
    layout = prepare_run_layout(output_root, args.run_name or f"{spec.experiment_id}_iterative")

    def write_status(state: str, **extra) -> None:
        # Marks a half-finished output directory as such, so a crashed run is
        # not mistaken for a complete one later.
        write_json(layout["run_root"] / "status.json", {"status": state, **extra})

    write_status("running")
    # Record what actually ran, not just what the spec asked for, so the CLI
    # overrides above stay reproducible from the output directory alone.
    write_json(
        layout["inputs"] / "resolved_run_config.json",
        {
            "provider": provider_name,
            "model": getattr(provider, "model", model_name),
            "azure_model_key": azure_model_key,
            "reasoning_effort": reasoning_effort,
            "thinking_budget": thinking_budget,
            "max_output_tokens": args.max_output_tokens,
            "threshold_f1": threshold_f1,
            "n_examples": n_examples,
            "sample_size": sample_size,
            "seed": seed,
            "dev_split": args.dev_split,
        },
    )
    write_json(layout["inputs"] / "experiment_spec.json", spec.to_json_dict())
    write_json(
        layout["inputs"] / "sampled_train_documents.json",
        [
            {
                "filename": document.filename,
                "sourceid": document.sourceid,
                "path": document.path,
            }
            for document in sampled_documents
        ],
    )
    Path(layout["inputs"] / "initial_guidelines.txt").write_text(guidelines, encoding="utf-8")
    write_json(layout["inputs"] / "entity_schema.json", entity_rows)

    def checkpoint(snapshot) -> None:
        round_dir = layout["rounds"] / f"iteration_{snapshot.iteration:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        write_json(round_dir / "snapshot.json", snapshot)
        for prompt_name, prompt_text in snapshot.prompts.items():
            (round_dir / f"{prompt_name}.txt").write_text(prompt_text, encoding="utf-8")
        Path(round_dir / "guidelines_after.txt").write_text(
            snapshot.guidelines_after, encoding="utf-8"
        )
        # On a reverted round guidelines_after is just the previous text, so the
        # proposal itself would otherwise leave no trace.
        Path(round_dir / "guidelines_candidate.txt").write_text(
            snapshot.guidelines_candidate, encoding="utf-8"
        )
        write_status("running", last_completed_iteration=snapshot.iteration)
        # Report the candidate's score, not summary_after: on a reverted
        # iteration summary_after is reset to summary_before, so printing it
        # would show "F1 x -> x" and hide what the refinement actually scored.
        candidate_f1 = (
            snapshot.summary_candidate.overall_f1
            if snapshot.summary_candidate is not None
            else snapshot.summary_after.overall_f1
        )
        print(
            f"[iteration {snapshot.iteration}] F1 "
            f"{snapshot.summary_before.overall_f1:.4f} -> {candidate_f1:.4f} (candidate)"
            f"  improved={snapshot.improved}  checkpointed to {round_dir}",
            flush=True,
        )

    try:
        result = run_iterative_refinement(
            sampled_documents=sampled_documents,
            guidelines=guidelines,
            entities=entities,
            provider=provider,
            threshold_f1=threshold_f1,
            n_examples=n_examples,
            output_configuration=OutputConfiguration(
                include_rationale=True,
                include_guideline_section=True,
            ),
            evaluation_options=PubAnnotationEvaluatorOptions(),
            on_iteration=checkpoint,
        )
    except BaseException as exc:
        write_status("failed", error=f"{type(exc).__name__}: {exc}")
        raise

    write_json(layout["final"] / "iterative_refinement_run.json", result)
    Path(layout["final"] / "final_guidelines.txt").write_text(result.final_guidelines, encoding="utf-8")
    write_json(
        layout["links"] / "reader_links.json",
        {
            "pubannotation_evaluation": spec.evaluation_url,
        },
    )
    write_status(
        "completed",
        stop_reason=result.stop_reason,
        iterations=len(result.iterations),
        initial_f1=result.initial_summary.overall_f1,
        final_f1=result.final_summary.overall_f1,
    )


if __name__ == "__main__":
    main()
