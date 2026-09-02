"""Synchronous LLM JSON client for the AITDE intelligence chain (Batch 207).

Mirrors the knowledge chain's async ``call_json_model`` but synchronous,
matching the sync route/service layer and the ``legacy_cutover`` precedent.
Only sanitized, structured payloads leave the process; errors are classified
so the service layer can decide whether to degrade (transient) or surface a
contract break (malformed response).
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai_config_service import (
    AIProviderUnconfiguredError,
    ai_config_service,
)


class IntelligenceLLMError(RuntimeError):
    """The configured model could not be reached (disabled/transient/HTTP)."""


class IntelligenceLLMResponseError(ValueError):
    """The model returned an unusable response (contract break, never masked)."""


def resolve_config(db, project_id: int):
    """Resolve the project's effective AI config or raise IntelligenceLLMError."""
    if not settings.ai_enabled:
        raise IntelligenceLLMError("AI service is disabled")
    try:
        return ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError as exc:
        raise IntelligenceLLMError(str(exc)) from exc


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        # tolerate fenced markdown output
        text = text.split("\\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntelligenceLLMResponseError("AI response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise IntelligenceLLMResponseError("AI response must be a JSON object")
    return parsed


def call_llm_json(
    *,
    db,
    project_id: int,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call the configured model and return one validated JSON object.

    Transient failures (timeout/network/5xx/429) retry up to
    ``settings.ai_retry_attempts`` then raise ``IntelligenceLLMError``;
    malformed envelopes/content raise ``IntelligenceLLMResponseError``.
    """
    cfg = resolve_config(db, project_id)
    request_body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ],
        "max_tokens": max_tokens,
        "temperature": settings.ai_temperature,
        "response_format": {"type": "json_object"},
    }
    attempts = max(1, settings.ai_retry_attempts)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = httpx.post(
                f"{cfg.api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=settings.ai_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"]
            return _parse_json_object(raw)
        except httpx.TimeoutException as exc:  # subclass first
            last_error = exc
            if attempt + 1 < attempts:
                continue
        except httpx.RequestError as exc:
            last_error = exc
            if attempt + 1 < attempts:
                continue
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if (
                exc.response.status_code in {429, 500, 502, 503, 504}
                and attempt + 1 < attempts
            ):
                continue
            raise IntelligenceLLMError(
                f"AI API returned HTTP {exc.response.status_code}"
            ) from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise IntelligenceLLMResponseError("AI response envelope is invalid") from exc
    raise IntelligenceLLMError(f"AI request failed: {last_error}") from last_error
