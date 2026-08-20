"""Minimal .env loader, no third-party dependency.

Keeps API keys out of shell history and out of the repository. Values already
present in os.environ win, so an exported variable always overrides the file.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def load_dotenv(path: str | Path | None = None) -> dict[str, str]:
    """Parse a .env file into os.environ without overwriting existing values."""
    env_path = Path(path) if path else DEFAULT_ENV_PATH
    loaded: dict[str, str] = {}
    if not env_path.is_file():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value:
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded
