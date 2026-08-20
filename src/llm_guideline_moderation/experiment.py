from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ExperimentPaths:
    guidelines_txt: str
    entity_schema_json: str
    output_dir: str


@dataclass(slots=True)
class ExperimentEvidence:
    discrepancy_examples: str = ""
    true_positive_examples: str = ""
    verified_examples: str = ""


@dataclass(slots=True)
class ModerationSamplingConfig:
    source_dir_path: str = ""
    source_split: str = ""
    sampling_method: str = ""
    sample_size: int | None = None
    seed: int | None = None
    shared_across_models: bool = True
    selection_note: str = ""


@dataclass(slots=True)
class ExperimentModelConfig:
    provider: str = "openai"
    model: str = "gpt-5"
    rounds: int = 1
    # Reasoning depth, recorded in the spec so a run is reproducible from it
    # alone. Without these the spec could not express the paper's Section 4.3
    # setup at all: from_json_file expands the "model" block with **, so an
    # unknown key raised TypeError rather than being ignored.
    # OpenAI accepts low / medium / high / xhigh; Gemini takes an integer budget.
    reasoning_effort: str | None = None
    thinking_budget: int | None = None
    # Azure OpenAI only: which AZURE_OPENAI_<key>_* variable group to read.
    azure_model_key: str | None = None


@dataclass(slots=True)
class ExperimentIterativeConfig:
    threshold_f1: float = 0.9
    n_examples: int = 5


@dataclass(slots=True)
class ExperimentSpec:
    experiment_id: str
    description: str = ""
    dataset_name: str = ""
    split: str = ""
    evaluation_url: str = ""
    paths: ExperimentPaths | None = None
    evidence: ExperimentEvidence = field(default_factory=ExperimentEvidence)
    moderation_sampling: ModerationSamplingConfig = field(default_factory=ModerationSamplingConfig)
    model: ExperimentModelConfig = field(default_factory=ExperimentModelConfig)
    iterative: ExperimentIterativeConfig = field(default_factory=ExperimentIterativeConfig)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ExperimentSpec":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        pubannotation_payload = payload.get("pubannotation", {})
        return cls(
            experiment_id=payload["experiment_id"],
            description=payload.get("description", ""),
            dataset_name=payload.get("dataset_name", ""),
            split=payload.get("split", ""),
            evaluation_url=payload.get("evaluation_url", pubannotation_payload.get("evaluation_url", "")),
            paths=ExperimentPaths(**payload["paths"]),
            evidence=ExperimentEvidence(**payload.get("evidence", {})),
            moderation_sampling=ModerationSamplingConfig(**payload.get("moderation_sampling", {})),
            model=ExperimentModelConfig(**payload.get("model", {})),
            iterative=ExperimentIterativeConfig(**payload.get("iterative", {})),
        )

    def to_json_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "description": self.description,
            "dataset_name": self.dataset_name,
            "split": self.split,
            "evaluation_url": self.evaluation_url,
            "paths": {
                "guidelines_txt": self.paths.guidelines_txt if self.paths else "",
                "entity_schema_json": self.paths.entity_schema_json if self.paths else "",
                "output_dir": self.paths.output_dir if self.paths else "",
            },
            "evidence": {
                "discrepancy_examples": self.evidence.discrepancy_examples,
                "true_positive_examples": self.evidence.true_positive_examples,
                "verified_examples": self.evidence.verified_examples,
            },
            "moderation_sampling": {
                "source_dir_path": self.moderation_sampling.source_dir_path,
                "source_split": self.moderation_sampling.source_split,
                "sampling_method": self.moderation_sampling.sampling_method,
                "sample_size": self.moderation_sampling.sample_size,
                "seed": self.moderation_sampling.seed,
                "shared_across_models": self.moderation_sampling.shared_across_models,
                "selection_note": self.moderation_sampling.selection_note,
            },
            "model": {
                "provider": self.model.provider,
                "model": self.model.model,
                "rounds": self.model.rounds,
                "reasoning_effort": self.model.reasoning_effort,
                "thinking_budget": self.model.thinking_budget,
                "azure_model_key": self.model.azure_model_key,
            },
            "iterative": {
                "threshold_f1": self.iterative.threshold_f1,
                "n_examples": self.iterative.n_examples,
            },
        }
