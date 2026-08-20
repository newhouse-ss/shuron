from __future__ import annotations

from typing import Protocol

from ..types import LLMTaskName


class ModerationProvider(Protocol):
    def complete(self, task: LLMTaskName, prompt: str) -> str:
        """Run one moderation-related LLM task and return raw text output."""
