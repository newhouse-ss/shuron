"""Make the upstream package importable without modifying it.

Everything under ``reproduction/`` reads from ``src/llm_guideline_moderation`` and
never writes to it.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def ensure_upstream_importable() -> Path:
    if not SRC_ROOT.is_dir():
        raise RuntimeError(f"upstream source tree not found at {SRC_ROOT}")
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    return REPO_ROOT
