from __future__ import annotations

from pathlib import Path


def prepare_run_layout(root_output_dir: str | Path, experiment_id: str) -> dict[str, Path]:
    root = Path(root_output_dir)
    run_root = root / experiment_id
    paths = {
        "run_root": run_root,
        "inputs": run_root / "inputs",
        "prompts": run_root / "prompts",
        "rounds": run_root / "rounds",
        "final": run_root / "final",
        "links": run_root / "links",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
