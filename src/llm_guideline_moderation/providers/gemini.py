from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, parse, request

from .base import ModerationProvider
from ._shared import gemini_response_schema, is_json_task


@dataclass(slots=True)
class GeminiProvider(ModerationProvider):
    model: str
    api_key: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    thinking_budget: int | None = None
    timeout_seconds: int = 300
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider")

    def complete(self, task: str, prompt: str) -> str:
        url = f"{self.base_url}/{self.model}:generateContent?key={parse.quote(self.api_key)}"
        generation_config: dict[str, object] = {}
        if self.temperature is not None:
            generation_config["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            generation_config["maxOutputTokens"] = self.max_output_tokens
        if self.thinking_budget is not None:
            generation_config["thinkingConfig"] = {"thinkingBudget": self.thinking_budget}
        if is_json_task(task):
            generation_config["responseMimeType"] = "application/json"
            schema = gemini_response_schema(task)
            if schema is not None:
                generation_config["responseSchema"] = schema

        payload: dict[str, object] = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        if generation_config:
            payload["generationConfig"] = generation_config

        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc

        parsed = json.loads(body)
        text = self._extract_text(parsed)
        if not text.strip():
            raise RuntimeError("Gemini response did not contain text output")
        return text

    @staticmethod
    def _extract_text(response_json: dict) -> str:
        candidates = response_json.get("candidates", [])
        chunks: list[str] = []
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text:
                    chunks.append(text)
        return "\n".join(chunks)
