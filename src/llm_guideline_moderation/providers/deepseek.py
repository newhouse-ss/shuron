from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from time import sleep
from urllib import error, request

from ._shared import JSON_MODE_SYSTEM_PROMPT, is_json_task
from .base import ModerationProvider


@dataclass(slots=True)
class DeepSeekProvider(ModerationProvider):
    model: str
    api_key: str | None = None
    max_output_tokens: int = 8192
    temperature: float | None = None
    timeout_seconds: int = 300
    max_retries: int = 2
    base_url: str = "https://api.deepseek.com/v1/chat/completions"
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeekProvider")

    def complete(self, task: str, prompt: str) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_output_tokens,
        }

        if self.temperature is not None:
            payload["temperature"] = self.temperature

        if is_json_task(task):
            payload["messages"] = [
                {"role": "system", "content": JSON_MODE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)

        req = request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        body = self._send_with_retry(req)
        parsed = json.loads(body)
        text = self._extract_text(parsed)
        if not text.strip():
            raise RuntimeError("DeepSeek response did not contain text output")
        return text

    def _send_with_retry(self, req: request.Request) -> str:
        attempt = 0
        while True:
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    return response.read().decode("utf-8")
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < self.max_retries:
                    sleep(1.0)
                    attempt += 1
                    continue
                if exc.code in {502, 503, 504} and attempt < self.max_retries:
                    sleep(2**attempt)
                    attempt += 1
                    continue
                raise RuntimeError(f"DeepSeek request failed: {exc.code} {detail}") from exc
            except error.URLError as exc:
                raise RuntimeError(f"DeepSeek request failed: {exc.reason}") from exc

    @staticmethod
    def _extract_text(response_json: dict) -> str:
        choices = response_json.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if item.get("type") == "text":
                    chunks.append(item.get("text", ""))
            return "\n".join(chunk for chunk in chunks if chunk)
        return ""
