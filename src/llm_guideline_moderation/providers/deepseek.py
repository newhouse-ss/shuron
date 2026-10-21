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
    """Chat Completions client for api.deepseek.com.

    Checked against the official API reference
    (api-docs.deepseek.com/api/create-chat-completion, read 2026-10-20):

    * Thinking mode is on unless the request turns it off. ``thinking`` is
      therefore always sent, as ``{"type": "enabled"}`` or ``{"type":
      "disabled"}``, so a saved run states its mode instead of relying on a
      server default. ``temperature`` "has no effect in thinking mode" but is
      accepted without error, so it is sent whenever it is set.
    * ``max_tokens`` defaults to 8K with thinking off and 64K with thinking on,
      and reasoning counts against it: one August call spent its whole
      32,000-token budget on reasoning and returned no text
      (logs/ncbi_disease/temp-B2_ds_default-resume.err). 64000 is the cap used
      for GPT-5.4, which also bounds the cost of a single call.
    * ``last_usage`` and ``last_response`` keep the most recent usage block and
      response body, so callers can record the served ``model``, the reasoning
      tokens and ``reasoning_content`` without a second request.
    """

    model: str
    api_key: str | None = None
    thinking: bool = True
    max_output_tokens: int = 64000
    temperature: float | None = None
    timeout_seconds: int = 300
    max_retries: int = 2
    base_url: str = "https://api.deepseek.com/v1/chat/completions"
    extra_headers: dict[str, str] = field(default_factory=dict)
    last_usage: dict[str, object] = field(default_factory=dict)
    last_response: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeekProvider")

    def build_payload(self, task: str, prompt: str) -> dict[str, object]:
        """The request body ``complete`` sends; exposed so a dry run can show it."""
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_output_tokens,
            "thinking": {"type": "enabled" if self.thinking else "disabled"},
        }

        if self.temperature is not None:
            payload["temperature"] = self.temperature

        if is_json_task(task):
            payload["messages"] = [
                {"role": "system", "content": JSON_MODE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            payload["response_format"] = {"type": "json_object"}
        return payload

    def complete(self, task: str, prompt: str) -> str:
        payload = self.build_payload(task, prompt)

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

        # Cleared first so a failed request cannot leave the previous call's
        # usage behind to be recorded against this one.
        self.last_usage = {}
        self.last_response = {}
        body = self._send_with_retry(req)
        parsed = json.loads(body)
        self.last_response = parsed
        self.last_usage = parsed.get("usage") or {}
        text = self._extract_text(parsed)
        if not text.strip():
            # With thinking on, a call that spends the whole budget reasoning
            # returns an empty message with finish_reason="length". Surface that
            # rather than letting it look like "the model found no entities".
            finish = (parsed.get("choices") or [{}])[0].get("finish_reason")
            raise RuntimeError(
                "DeepSeek response did not contain text output "
                f"(finish_reason={finish!r}, usage={self.last_usage})"
            )
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
