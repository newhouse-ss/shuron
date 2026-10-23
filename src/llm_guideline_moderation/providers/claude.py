from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ._shared import JSON_MODE_SYSTEM_PROMPT, is_json_task
from .base import ModerationProvider

_FENCED = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n?```\s*$", re.DOTALL)


@dataclass(slots=True)
class ClaudeProvider(ModerationProvider):
    """Messages API client for Claude through the official ``anthropic`` SDK.

    Checked against the Claude API notes bundled with Claude Code (models, Haiku 5.5 migration, Python SDK)
    and platform.claude.com/docs/en/about-claude/pricing, read 2026-10-22:

    * Claude Haiku 5.5 thinks adaptively by default and sets the depth with ``output_config.effort`` (low,
      medium, high, xhigh, max; default medium). ``budget_tokens`` and any non-default ``temperature``,
      ``top_p`` or ``top_k`` return a 400, so none of them is sent.
    * Thinking counts toward ``max_tokens``. 64000 is the cap used for DeepSeek and GPT-5.4; a request that
      large is streamed, as the SDK expects for long calls.
    * ``display: "summarized"`` returns a readable summary of the thinking; billing is the same with or without
      it. The summary stays in ``last_response`` for error analysis.
    * A response that stopped at ``max_tokens`` or with ``refusal`` raises instead of returning its text, so a
      cut-off annotation or rewrite never enters a run as if it were complete.
    * Haiku 5.5 bills a request on a higher rate card when its prompt is over 100,000 tokens. ``last_usage``
      keeps the input counts so a caller can see which card applied.
    * JSON tasks get the system prompt DeepSeek's JSON mode uses. DeepSeek's ``response_format`` guarantees bare
      JSON. The Claude equivalent is structured outputs: with a schema in ``json_schemas`` for the task,
      ``output_config.format`` makes every reply that ends normally valid JSON matching that schema (supported on
      Haiku 5.5, with thinking and in batches). The schema used for annotation is built from the prompt's own
      field list (``_shared.annotation_json_schema``), so it asks for nothing the prompt does not. A refusal or a
      cut-off may not match the schema; both raise before any parsing.
    * Without a schema the reply is read leniently: as it is if it parses, else the inside of one code fence,
      else the span from the first "{" to the last "}" if that parses; otherwise it is passed on unchanged and
      fails visibly. ``last_extraction`` says which path was taken, so a run can check that constrained replies
      were all read as they came ("plain").

    ``build_params`` is the request body ``complete`` sends, and ``read_message`` is how a response becomes
    text; a batch runner uses the same two methods, so batch and live calls are built and read alike.
    """

    model: str
    effort: str = "medium"
    max_output_tokens: int = 64000
    thinking_display: str = "summarized"
    json_schemas: dict[str, dict] = field(default_factory=dict)
    api_key: str | None = None
    max_retries: int = 4
    client: object = field(default=None, repr=False)
    last_usage: dict[str, object] = field(default_factory=dict)
    last_response: dict[str, object] = field(default_factory=dict)
    last_extraction: str = ""

    def build_params(self, task: str, prompt: str) -> dict[str, object]:
        params: dict[str, object] = {
            "model": self.model,
            "max_tokens": self.max_output_tokens,
            "thinking": {"type": "adaptive", "display": self.thinking_display},
            "output_config": {"effort": self.effort},
            "messages": [{"role": "user", "content": prompt}],
        }
        if is_json_task(task):
            params["system"] = JSON_MODE_SYSTEM_PROMPT
            if task in self.json_schemas:
                params["output_config"]["format"] = {"type": "json_schema", "schema": self.json_schemas[task]}
        return params

    def complete(self, task: str, prompt: str) -> str:
        # Cleared first so a failed request cannot leave the previous call's usage behind.
        self.last_usage = {}
        self.last_response = {}
        self.last_extraction = ""
        with self._client().messages.stream(**self.build_params(task, prompt)) as stream:
            message = stream.get_final_message()
        return self.read_message(message.to_dict(), task)

    def read_message(self, message: dict, task: str) -> str:
        self.last_response = message
        self.last_usage = message.get("usage") or {}
        stop = message.get("stop_reason")
        if stop == "refusal":
            raise RuntimeError(f"Claude declined the request (stop_details={message.get('stop_details')!r})")
        if stop == "max_tokens":
            raise RuntimeError(f"Claude response cut off at max_tokens={self.max_output_tokens} "
                               f"(usage={self.last_usage})")
        text = "\n".join(block.get("text", "") for block in message.get("content") or []
                         if block.get("type") == "text")
        if not text.strip():
            raise RuntimeError(f"Claude response did not contain text output (stop_reason={stop!r})")
        self.last_extraction = "plain"
        if is_json_task(task):
            text, self.last_extraction = _json_text(text)
        return text

    def _client(self):
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=self.max_retries)
        return self.client


def _parses(text: str) -> bool:
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def _json_text(text: str) -> tuple[str, str]:
    if _parses(text):
        return text, "plain"
    fenced = _FENCED.match(text)
    if fenced and _parses(fenced.group(1)):
        return fenced.group(1), "fence"
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end and _parses(text[start:end + 1]):
        return text[start:end + 1], "brace"
    return text, "unparsed"
