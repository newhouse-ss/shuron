from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from http.client import HTTPException
from time import monotonic, sleep
from urllib import error, request

from .base import ModerationProvider
from ._shared import JSON_MODE_SYSTEM_PROMPT, is_json_task


AZURE_ENV_FIELDS = ("ENDPOINT", "API_KEY", "API_VERSION", "DEPLOYMENT_NAME")

# Background polling tolerates transient network failures; this bounds how many
# in a row before the endpoint is treated as genuinely unreachable.
MAX_CONSECUTIVE_POLL_FAILURES = 10

# A healthy background job leaves "queued" within seconds - the successful runs
# measured here finished end to end in about 110s. Jobs that are still queued
# well past that never start at all: two were observed sitting at "queued"
# hours after submission, with no error field ever set. Waiting out the full
# poll timeout on one of those cost two multi-hour runs, so a job that has not
# started by this point is abandoned and resubmitted instead.
QUEUED_STALL_SECONDS = 180
MAX_RESUBMISSIONS = 3


def azure_config_from_env(model_key: str) -> dict[str, str]:
    """Read AZURE_OPENAI_<model_key>_{ENDPOINT,API_KEY,API_VERSION,DEPLOYMENT_NAME}.

    Both spellings of the model part are accepted (``5_1`` and ``5-1``), since
    hyphens are legal in a .env file but break shell expansion.
    """
    variants = {model_key, model_key.replace("_", "-"), model_key.replace("-", "_")}
    resolved: dict[str, str] = {}
    for field_name in AZURE_ENV_FIELDS:
        for variant in variants:
            value = os.environ.get(f"AZURE_OPENAI_{variant}_{field_name}")
            if value:
                resolved[field_name] = value
                break

    missing = [name for name in AZURE_ENV_FIELDS if name not in resolved]
    if missing:
        raise KeyError(
            f"Azure model '{model_key}' is missing: "
            + ", ".join(f"AZURE_OPENAI_{model_key}_{name}" for name in missing)
        )
    return resolved


@dataclass(slots=True)
class OpenAIProvider(ModerationProvider):
    """Chat Completions client for both api.openai.com and Azure OpenAI.

    Setting ``azure_endpoint`` switches to Azure, where the deployment lives in
    the URL rather than the payload, auth is the ``api-key`` header rather than
    a bearer token, and the api-version is a query parameter. In that mode
    ``model`` names the deployment. Left unset, behaviour is unchanged.

    Two payload details were corrected against live GPT-5.x deployments:

    * ``max_completion_tokens`` replaces ``max_tokens``, which every GPT-5.x
      deployment rejects with `400 Unsupported parameter: 'max_tokens' is not
      supported with this model.` Older models that only accept the legacy name
      can set ``token_param="max_tokens"``.
    * ``reasoning_effort: "high"`` replaces the nested
      ``reasoning: {"effort": ...}``, which is rejected with `400 Unknown
      parameter: 'reasoning'.` - the nested form belongs to the Responses API,
      not Chat Completions. Accepted values are low / medium / high / xhigh.

    ``last_usage`` keeps the most recent ``usage`` block so callers can record
    token counts and reasoning tokens without a second request.
    """

    model: str
    api_key: str | None = None
    reasoning_effort: str | None = None
    max_output_tokens: int = 64000
    temperature: float | None = None
    timeout_seconds: int = 300
    max_retries: int = 2
    base_url: str = "https://api.openai.com/v1/chat/completions"
    azure_endpoint: str | None = None
    api_version: str | None = None
    token_param: str = "max_completion_tokens"
    # None means "decide automatically" - see _should_use_background.
    use_background: bool | None = None
    background_poll_timeout: int = 3600
    extra_headers: dict[str, str] = field(default_factory=dict)
    last_usage: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_azure_env(cls, model_key: str, **overrides) -> "OpenAIProvider":
        """Build an Azure-backed provider from AZURE_OPENAI_<model_key>_* variables."""
        config = azure_config_from_env(model_key)
        return cls(
            model=overrides.pop("model", config["DEPLOYMENT_NAME"]),
            api_key=config["API_KEY"],
            azure_endpoint=config["ENDPOINT"],
            api_version=config["API_VERSION"],
            **overrides,
        )

    def __post_init__(self) -> None:
        if self.azure_endpoint:
            if not self.api_version:
                raise ValueError("api_version is required when azure_endpoint is set")
            if self.api_key is None:
                self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("an API key is required for Azure OpenAI")
            return

        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider")

    @property
    def is_azure(self) -> bool:
        return bool(self.azure_endpoint)

    @property
    def request_url(self) -> str:
        if not self.is_azure:
            return self.base_url
        endpoint = self.azure_endpoint.rstrip("/")
        return (
            f"{endpoint}/openai/deployments/{self.model}"
            f"/chat/completions?api-version={self.api_version}"
        )

    @property
    def responses_url(self) -> str:
        endpoint = self.azure_endpoint.rstrip("/")
        return f"{endpoint}/openai/responses?api-version={self.api_version}"

    def _should_use_background(self) -> bool:
        """Deep reasoning has to go through the queued Responses API.

        Synchronous chat/completions holds one connection open for the whole
        request, and the reasoning phase emits nothing - not even with
        stream=true, because the gateway withholds response headers until the
        first *content* token. Measured against a live gpt-5.4 deployment on a
        real annotation prompt: low took 35s and medium 61s, both fine, while
        high dropped at 130s (and succeeded on one retry at 89s) and xhigh
        dropped at 180.1s, 180.2s and 181.4s across three api-versions and both
        stream modes. The variance is in the model, not the network: the same
        prompt at high spent 9,214 reasoning tokens on the run that survived
        and 23,375 on another, so anything at high or above is a coin flip.

        The Responses API queues the request server-side and is polled, which
        removes the wall entirely - xhigh ran 279s with no disconnect. So high
        and xhigh default to background mode; low and medium keep the simpler
        synchronous path. Pass use_background explicitly to override.
        """
        if self.use_background is not None:
            return self.use_background
        return bool(self.is_azure and self.reasoning_effort in {"high", "xhigh"})

    def complete(self, task: str, prompt: str) -> str:
        if self._should_use_background():
            return self._complete_via_responses(task, prompt)

        payload: dict[str, object] = {
            "messages": [{"role": "user", "content": prompt}],
            self.token_param: self.max_output_tokens,
        }
        if not self.is_azure:
            # On Azure the deployment in the URL selects the model.
            payload["model"] = self.model

        if self.temperature is not None:
            payload["temperature"] = self.temperature

        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort

        if is_json_task(task):
            payload["messages"] = [
                {"role": "system", "content": JSON_MODE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self.is_azure:
            headers["api-key"] = self.api_key
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)

        req = request.Request(
            self.request_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        body = self._send_with_retry(req)

        parsed = json.loads(body)
        self.last_usage = parsed.get("usage") or {}
        text = self._extract_text(parsed)
        if not text.strip():
            # A reasoning model that spends the whole budget thinking returns an
            # empty message with finish_reason="length". Surface that rather than
            # letting it look like "the model found no entities".
            finish = (parsed.get("choices") or [{}])[0].get("finish_reason")
            raise RuntimeError(
                "OpenAI response did not contain text output "
                f"(finish_reason={finish!r}, usage={self.last_usage})"
            )
        return text

    def _complete_via_responses(self, task: str, prompt: str) -> str:
        """Submit to the Responses API in background mode, then poll to completion."""
        if not self.is_azure:
            raise ValueError("background mode is currently implemented for Azure only")

        payload: dict[str, object] = {
            "model": self.model,
            "input": prompt,
            "background": True,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort:
            # The Responses API takes the nested form, unlike chat/completions.
            payload["reasoning"] = {"effort": self.reasoning_effort}
        if is_json_task(task):
            payload["text"] = {"format": {"type": "json_object"}}

        endpoint = self.azure_endpoint.rstrip("/")
        deadline = monotonic() + self.background_poll_timeout
        status = "unknown"
        response_id = None

        for submission in range(MAX_RESUBMISSIONS + 1):
            submitted = self._request_json(self.responses_url, payload=payload)
            response_id = submitted.get("id")
            if not response_id:
                raise RuntimeError(f"Responses API did not return an id: {submitted}")

            poll_url = f"{endpoint}/openai/responses/{response_id}?api-version={self.api_version}"
            queued_since = monotonic()
            delay = 2.0
            poll_failures = 0

            while monotonic() < deadline:
                sleep(delay)
                try:
                    current = self._request_json(poll_url, method="GET")
                except RuntimeError as exc:
                    # The job is running server-side; a failed status check says
                    # nothing about it. Losing a whole run because one GET hit a
                    # dropped TLS connection is never the right trade, so keep
                    # polling until the deadline instead of giving up.
                    poll_failures += 1
                    if poll_failures > MAX_CONSECUTIVE_POLL_FAILURES:
                        raise RuntimeError(
                            f"{poll_failures} consecutive poll failures for {response_id}; "
                            f"last error: {exc}"
                        ) from exc
                    delay = min(delay * 2, 30.0)
                    continue

                poll_failures = 0
                status = current.get("status")

                if status == "in_progress":
                    queued_since = None
                    delay = min(delay * 1.5, 15.0)
                    continue

                if status == "queued":
                    if queued_since and monotonic() - queued_since > QUEUED_STALL_SECONDS:
                        break  # never started - resubmit
                    delay = min(delay * 1.5, 15.0)
                    continue

                self.last_usage = current.get("usage") or {}
                if status != "completed":
                    detail = current.get("incomplete_details") or current.get("error")
                    raise RuntimeError(
                        f"Responses API returned status={status!r} "
                        f"(detail={detail}, usage={self.last_usage})"
                    )

                text = self._extract_responses_text(current)
                if not text.strip():
                    raise RuntimeError(
                        f"Responses API completed with no text output (usage={self.last_usage})"
                    )
                return text

            if monotonic() >= deadline:
                break
            # Stalled in the queue. Free the abandoned job if the service lets
            # us, then submit a fresh one.
            self._cancel_quietly(endpoint, response_id)

        raise RuntimeError(
            f"Responses API never completed: last status={status!r}, "
            f"{submission + 1} submission(s), id={response_id}"
        )

    def _cancel_quietly(self, endpoint: str, response_id: str) -> None:
        try:
            self._request_json(
                f"{endpoint}/openai/responses/{response_id}/cancel?api-version={self.api_version}",
                payload={},
            )
        except Exception:  # noqa: BLE001 - best effort, the job is abandoned either way
            pass

    def _request_json(self, url: str, payload: dict | None = None, method: str = "POST") -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        headers.update(self.extra_headers)
        req = request.Request(url, data=data, headers=headers, method=method)
        return json.loads(self._send_with_retry(req))

    @staticmethod
    def _extract_responses_text(response_json: dict) -> str:
        """Assistant text lives in output[].content[].text, not choices[]."""
        chunks: list[str] = []
        for item in response_json.get("output") or []:
            if item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if part.get("type") in {"output_text", "text"} and part.get("text"):
                    chunks.append(part["text"])
        return "".join(chunks)

    def _send_with_retry(self, req: request.Request) -> str:
        attempt = 0
        while True:
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    return response.read().decode("utf-8")
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < self.max_retries:
                    sleep(self._retry_delay_seconds(exc.headers))
                    attempt += 1
                    continue
                if exc.code in {502, 503, 504} and attempt < self.max_retries:
                    sleep(2**attempt)
                    attempt += 1
                    continue
                raise RuntimeError(f"OpenAI request failed: {exc.code} {detail}") from exc
            except (error.URLError, HTTPException, ConnectionError, TimeoutError) as exc:
                # Transport-level failures - dropped TLS connections, resets,
                # RemoteDisconnected. These were previously raised on the first
                # occurrence, so a single network hiccup ended the whole run.
                # RemoteDisconnected in particular is neither HTTPError nor
                # URLError, so it used to escape as a bare traceback.
                reason = getattr(exc, "reason", exc)
                if attempt < self.max_retries:
                    sleep(2**attempt)
                    attempt += 1
                    continue
                raise RuntimeError(
                    f"OpenAI request failed after {attempt + 1} attempts: {reason}"
                ) from exc

    @staticmethod
    def _retry_delay_seconds(headers) -> float:
        retry_after = headers.get("retry-after")
        if not retry_after:
            return 1.0
        try:
            return float(retry_after)
        except ValueError:
            return 1.0

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
