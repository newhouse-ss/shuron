"""Annotate a directory, skipping documents already written.

`annotate_pubannotation_directory` re-annotates every file from the start, so a
run killed at document 54 of 100 loses all 54 when restarted. On this project
that has happened repeatedly: power failures, dropped TLS connections, and
Azure returning a transient `incomplete` or `server_error` mid-directory. Each
document here is written as soon as it is produced and skipped on a rerun, so a
restart costs only the document that was in flight.

Upstream is untouched; this drives the same per-document call the shipped
directory annotator uses.

    python reproduction/annotate_valid_resumable.py \
        --input-dir data/datasets/ncbi_disease/valid \
        --guidelines outputs/<run>/final/final_guidelines.txt \
        --output-dir outputs/<name>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import monotonic

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_guideline_moderation.dotenv import load_dotenv  # noqa: E402
from llm_guideline_moderation.pipeline import annotate_with_guidelines  # noqa: E402
from llm_guideline_moderation.providers.openai import OpenAIProvider  # noqa: E402
from llm_guideline_moderation.pubannotation import annotations_to_pubannotation  # noqa: E402
from llm_guideline_moderation.types import EntityDefinition, OutputConfiguration  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--guidelines", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--entities", default="data/schemas/ncbi_entities.schema.json")
    parser.add_argument("--azure-model-key", default="5_4")
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--max-output-tokens", type=int, default=64000)
    args = parser.parse_args()

    load_dotenv()
    guidelines = Path(args.guidelines).read_text(encoding="utf-8")
    entities = [EntityDefinition(name=row) for row in
                json.loads(Path(args.entities).read_text(encoding="utf-8"))]
    configuration = OutputConfiguration(include_rationale=True, include_guideline_section=True)
    provider = OpenAIProvider.from_azure_env(
        args.azure_model_key,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
    )

    input_root, output_root = Path(args.input_dir), Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    documents = sorted(input_root.glob("*.json"))
    pending = [p for p in documents if not (output_root / p.name).exists()]

    print(f"guideline {len(guidelines)} chars, {len(documents)} documents, "
          f"{len(documents) - len(pending)} already written, {len(pending)} to go", flush=True)

    started = monotonic()
    for index, path in enumerate(pending, 1):
        began = monotonic()
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = annotate_with_guidelines(
            text=raw["text"], guidelines=guidelines, entities=entities,
            provider=provider, instructions="", output_configuration=configuration,
        )
        document = annotations_to_pubannotation(
            text=raw["text"], annotations=result.annotations,
            sourcedb=raw.get("sourcedb", "unknown"),
            sourceid=raw.get("sourceid", path.stem),
            project=raw.get("project"), target=raw.get("target"),
        )
        (output_root / path.name).write_text(
            json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {path.name:<16} {len(result.annotations):>3} annotations  "
              f"{monotonic() - began:6.1f}s  {index}/{len(pending)}  "
              f"(elapsed {(monotonic() - started) / 60:.1f} min)", flush=True)

    print(f"done: {len(list(output_root.glob('*.json')))} of {len(documents)} written")


if __name__ == "__main__":
    main()
