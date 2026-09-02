"""Shared LLM client (Batch 208, C5/C6).

Single sync + async OpenAI-compatible chat-completions transport with one
config gate, one retry policy and one error taxonomy. The four legacy call
sites (ai_service, knowledge/llm_json_client, intelligence/llm_sync,
legacy_cutover) are converged onto this module; callers keep their own
sanitization, prompt and result-shaping logic.
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


class AiClientUnavailableError(RuntimeError):
    """The configured model could not be reached (disabled/transient/HTTP)."""


class AiClientResponseError(ValueError):
    """The model returned an unusable envelope/content (contract break)."""


def resolve_config(db, project_id: int) -> Any | None:
    """Return the project's effective AI config or None.

    ``settings.ai_enabled`` is the global kill-switch; the per-project provider
    row is the source of truth when a DB session is available (C6 unification).
    """
    if not settings.ai_enabled:
        return None
    try:
        return ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError:
        return None


def is_configured(db, project_id: int) -> bool:
    """True when AI is enabled globally AND the project has a usable provider."""
    return resolve_config(db, project_id) is not None


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a model reply into one JSON object, tolerating fenced output."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AiClientResponseError("AI response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise AiClientResponseError("AI response must be a JSON object")
    return parsed


def _build_request(
    cfg: Any,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": settings.ai_temperature if temperature is None else temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


def _summary_from_response(response: httpx.Response) -> dict[str, Any]:
    data = response.json()
    try:
        choice = data["choices"][0]
        content = str(choice["message"]["content"])
        finish_reason = str(choice.get("finish_reason") or "unknown")
        return {
            "content": content,
            "finish_reason": finish_reason,
            "truncated": finish_reason == "length",
        }
    except (KeyError, TypeError, IndexError) as exc:
        raise AiClientResponseError("AI response envelope is invalid") from exc


def _retry_attempts() -> range:
    return range(max(1, settings.ai_retry_attempts))


def _parse_result(content: str, json_mode: bool) -> Any:
    return parse_json_object(content) if json_mode else content


def chat_completions_full(
    db,
    project_id: int,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = True,
) -> dict[str, Any]:
    """Sync call returning {content, finish_reason, truncated}."""
    cfg = resolve_config(db, project_id)
    if cfg is None:
        raise AiClientUnavailableError("AI service is not configured")
    body = _build_request(
        cfg,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens or settings.ai_max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )
    last_error: Exception | None = None
    for _ in _retry_attempts():
        try:
            response = httpx.post(
                f"{cfg.api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=settings.ai_timeout_seconds,
            )
            response.raise_for_status()
            return _summary_from_response(response)
        except httpx.TimeoutException as exc:  # subclass first
            last_error = exc
        except httpx.RequestError as exc:
            last_error = exc
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                raise AiClientUnavailableError(
                    f"AI API returned HTTP {exc.response.status_code}"
                ) from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AiClientResponseError("AI response envelope is invalid") from exc
    raise AiClientUnavailableError(f"AI request failed: {last_error}") from last_error


async def achat_completions_full(
    db,
    project_id: int,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = True,
) -> dict[str, Any]:
    """Async call returning {content, finish_reason, truncated}."""
    cfg = resolve_config(db, project_id)
    if cfg is None:
        raise AiClientUnavailableError("AI service is not configured")
    body = _build_request(
        cfg,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens or settings.ai_max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )
    last_error: Exception | None = None
    for _ in _retry_attempts():
        try:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                response = await client.post(
                    f"{cfg.api_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {cfg.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            response.raise_for_status()
            return _summary_from_response(response)
        except httpx.TimeoutException as exc:  # subclass first
            last_error = exc
        except httpx.RequestError as exc:
            last_error = exc
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                raise AiClientUnavailableError(
                    f"AI API returned HTTP {exc.response.status_code}"
                ) from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AiClientResponseError("AI response envelope is invalid") from exc
    raise AiClientUnavailableError(f"AI request failed: {last_error}") from last_error


def chat_completions(
    db,
    project_id: int,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = True,
) -> Any:
    """Synchronous call returning parsed JSON (json_mode) or raw text."""
    full = chat_completions_full(
        db,
        project_id,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )
    return _parse_result(full["content"], json_mode)


async def achat_completions(
    db,
    project_id: int,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = True,
) -> Any:
    """Async call returning parsed JSON (json_mode) or raw text."""
    full = await achat_completions_full(
        db,
        project_id,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )
    return _parse_result(full["content"], json_mode)
