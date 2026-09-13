"""Shared LLM client (Batch 208, C5/C6).

Single sync + async OpenAI-compatible chat-completions transport with one
config gate, one retry policy and one error taxonomy. The four legacy call
sites (ai_service, knowledge/llm_json_client, intelligence/llm_sync,
legacy_cutover) are converged onto this module; callers keep their own
sanitization, prompt and result-shaping logic.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.ai_gateway.cache import lookup_exact_cache, store_exact_cache
from app.services.ai_gateway.keys import build_cache_key, sha256_text
from app.services.ai_config_service import (
    AIProviderUnconfiguredError,
    ai_config_service,
)


logger = logging.getLogger("ai_gateway.client")


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
    project_id: int,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
    cache_namespace: str | None,
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
    if _is_openai_official(cfg.api_base_url):
        namespace = cache_namespace or hashlib.sha256(
            system_prompt.encode("utf-8")
        ).hexdigest()[:16]
        identity = "|".join(
            (
                str(project_id),
                str(getattr(cfg, "provider_id", "")),
                str(cfg.model),
                namespace,
            )
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        prefix = "aitde" if (cache_namespace or "").startswith("aitde") else "prompt"
        body["prompt_cache_key"] = f"{prefix}-{digest}"
    return body


def _is_openai_official(api_base_url: str) -> bool:
    """Only send OpenAI-specific request fields to the official API host."""
    try:
        return (urlparse(api_base_url).hostname or "").lower() == "api.openai.com"
    except ValueError:
        return False


def _token_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(0, int(value))


def normalize_token_usage(raw: Any) -> dict[str, Any]:
    """Normalize OpenAI and DeepSeek usage envelopes for durable telemetry."""
    if not isinstance(raw, dict):
        return {}
    known_fields = {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_tokens_details",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
    }
    if not any(key in raw for key in known_fields):
        return {}

    input_tokens = _token_count(raw.get("prompt_tokens"))
    output_tokens = _token_count(raw.get("completion_tokens"))
    total_tokens = _token_count(raw.get("total_tokens"))
    cached_tokens: int | None = None
    uncached_tokens: int | None = None
    details = raw.get("prompt_tokens_details")
    if isinstance(details, dict) and "cached_tokens" in details:
        cached_tokens = _token_count(details.get("cached_tokens"))
    elif "prompt_cache_hit_tokens" in raw:
        cached_tokens = _token_count(raw.get("prompt_cache_hit_tokens"))
    if "prompt_cache_miss_tokens" in raw:
        uncached_tokens = _token_count(raw.get("prompt_cache_miss_tokens"))

    if all(
        value is None
        for value in (input_tokens, output_tokens, total_tokens, cached_tokens, uncached_tokens)
    ):
        return {}

    cache_details_available = cached_tokens is not None
    if input_tokens is None and cached_tokens is not None and uncached_tokens is not None:
        input_tokens = cached_tokens + uncached_tokens
    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0
    total_tokens = total_tokens if total_tokens is not None else input_tokens + output_tokens
    if cache_details_available and uncached_tokens is None:
        uncached_tokens = max(0, input_tokens - (cached_tokens or 0))

    normalized: dict[str, Any] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_details_available": cache_details_available,
    }
    if cache_details_available:
        normalized.update(
            {
                "cached_input_tokens": cached_tokens or 0,
                "uncached_input_tokens": uncached_tokens or 0,
                "cache_hit_rate": round((cached_tokens or 0) / input_tokens, 4)
                if input_tokens
                else 0.0,
            }
        )
    return normalized


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
            "usage": normalize_token_usage(data.get("usage")),
        }
    except (KeyError, TypeError, IndexError) as exc:
        raise AiClientResponseError("AI response envelope is invalid") from exc


def _retry_attempts() -> range:
    return range(max(1, settings.ai_retry_attempts))


def _parse_result(content: str, json_mode: bool) -> Any:
    return parse_json_object(content) if json_mode else content


def _effective_temperature(temperature: float | None) -> float:
    return settings.ai_temperature if temperature is None else float(temperature)


def _exact_cache_key(
    db,
    *,
    project_id: int,
    cfg: Any,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    cache_namespace: str | None,
) -> str | None:
    if not settings.ai_exact_cache_enabled or db is None or not cache_namespace:
        return None
    return build_cache_key(
        project_id=project_id,
        provider_id=int(getattr(cfg, "provider_id", 0) or 0),
        model=str(cfg.model),
        namespace=cache_namespace,
        system_prompt=system_prompt,
        user_message=user_message,
        json_mode=json_mode,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _cache_hit(summary: dict[str, Any], cache_key: str) -> dict[str, Any]:
    """Return a truthful current-call summary with zero new token usage."""
    cached = dict(summary)
    saved_usage = cached.get("usage") or {}
    cached.update(
        {
            "usage": {},
            "cache_saved_usage": saved_usage,
            "cache_status": "hit",
            "cache_key": cache_key[:16],
        }
    )
    return cached


def _finish_with_cache(
    summary: dict[str, Any],
    *,
    db,
    project_id: int,
    cfg: Any,
    cache_namespace: str | None,
    cache_key: str | None,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
) -> dict[str, Any]:
    summary["cache_key"] = cache_key[:16] if cache_key else ""
    if cache_key is None:
        summary["cache_status"] = "disabled"
        _schedule_shadow_safely(
            project_id=project_id,
            cfg=cfg,
            cache_namespace=cache_namespace,
            system_prompt=system_prompt,
            user_message=user_message,
            primary=summary,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )
        return summary
    if summary.get("truncated"):
        summary["cache_status"] = "bypass_truncated"
        _schedule_shadow_safely(
            project_id=project_id,
            cfg=cfg,
            cache_namespace=cache_namespace,
            system_prompt=system_prompt,
            user_message=user_message,
            primary=summary,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )
        return summary
    try:
        store_exact_cache(
            db,
            project_id=project_id,
            namespace=cache_namespace or "",
            cache_key=cache_key,
            provider_id=int(getattr(cfg, "provider_id", 0) or 0),
            provider_type=str(getattr(cfg, "provider_type", "")),
            model=str(cfg.model),
            prompt_hash=sha256_text(system_prompt),
            input_hash=sha256_text(user_message),
            response=summary,
            usage=summary.get("usage") or {},
        )
        summary["cache_status"] = "write"
    except Exception:  # noqa: BLE001 - cache must never break the model call
        logger.exception("Exact AI cache write wrapper failed")
        summary["cache_status"] = "bypass_error"
    _schedule_shadow_safely(
        project_id=project_id,
        cfg=cfg,
        cache_namespace=cache_namespace,
        system_prompt=system_prompt,
        user_message=user_message,
        primary=summary,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )
    return summary


def _schedule_shadow_safely(
    *,
    project_id: int,
    cfg: Any,
    cache_namespace: str | None,
    system_prompt: str,
    user_message: str,
    primary: dict[str, Any],
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
) -> None:
    try:
        from app.services.ai_gateway.shadow import schedule_shadow_run

        schedule_shadow_run(
            project_id=project_id,
            primary_config=cfg,
            namespace=cache_namespace or "",
            system_prompt=system_prompt,
            user_message=user_message,
            primary=primary,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )
    except Exception:  # noqa: BLE001 - shadow is observational only
        logger.exception("Shadow scheduling failed")


def _call_configured_full(
    cfg: Any,
    *,
    project_id: int,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
    cache_namespace: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Call one OpenAI-compatible config without resolving a project provider."""
    body = _build_request(
        cfg,
        project_id=project_id,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        cache_namespace=cache_namespace,
    )
    started = time.perf_counter()
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
                timeout=timeout_seconds or settings.ai_timeout_seconds,
            )
            response.raise_for_status()
            summary = _summary_from_response(response)
            summary.update(
                {
                    "model_provider": str(getattr(cfg, "provider_type", "")),
                    "model_name": str(cfg.model),
                    "prompt_cache_key": str(body.get("prompt_cache_key") or ""),
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                }
            )
            return summary
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


def call_configured_full(
    cfg: Any,
    *,
    project_id: int,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None = None,
    json_mode: bool = True,
    cache_namespace: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Public configured-config transport used by shadow evaluation."""
    return _call_configured_full(
        cfg,
        project_id=project_id,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        cache_namespace=cache_namespace,
        timeout_seconds=timeout_seconds,
    )


def chat_completions_full(
    db,
    project_id: int,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = True,
    cache_namespace: str | None = None,
) -> dict[str, Any]:
    """Sync call returning content, finish state and normalized usage."""
    cfg = resolve_config(db, project_id)
    if cfg is None:
        raise AiClientUnavailableError("AI service is not configured")
    effective_max_tokens = max_tokens or settings.ai_max_tokens
    effective_temperature = _effective_temperature(temperature)
    cache_key = _exact_cache_key(
        db,
        project_id=project_id,
        cfg=cfg,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=effective_max_tokens,
        temperature=effective_temperature,
        json_mode=json_mode,
        cache_namespace=cache_namespace,
    )
    if cache_key:
        cached = lookup_exact_cache(db, project_id=project_id, cache_key=cache_key)
        if cached is not None:
            return _cache_hit(cached, cache_key)

    summary = _call_configured_full(
        cfg,
        project_id=project_id,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=effective_max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        cache_namespace=cache_namespace,
    )
    return _finish_with_cache(
        summary,
        db=db,
        project_id=project_id,
        cfg=cfg,
        cache_namespace=cache_namespace,
        cache_key=cache_key,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=effective_max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )

async def achat_completions_full(
    db,
    project_id: int,
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = True,
    cache_namespace: str | None = None,
) -> dict[str, Any]:
    """Async call returning content, finish state and normalized usage."""
    cfg = resolve_config(db, project_id)
    if cfg is None:
        raise AiClientUnavailableError("AI service is not configured")
    effective_max_tokens = max_tokens or settings.ai_max_tokens
    effective_temperature = _effective_temperature(temperature)
    cache_key = _exact_cache_key(
        db,
        project_id=project_id,
        cfg=cfg,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=effective_max_tokens,
        temperature=effective_temperature,
        json_mode=json_mode,
        cache_namespace=cache_namespace,
    )
    if cache_key:
        cached = lookup_exact_cache(db, project_id=project_id, cache_key=cache_key)
        if cached is not None:
            return _cache_hit(cached, cache_key)

    body = _build_request(
        cfg,
        project_id=project_id,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=effective_max_tokens,
        temperature=temperature,
        json_mode=json_mode,
        cache_namespace=cache_namespace,
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
            summary = _summary_from_response(response)
            summary.update(
                {
                    "model_provider": str(getattr(cfg, "provider_type", "")),
                    "model_name": str(cfg.model),
                    "prompt_cache_key": str(body.get("prompt_cache_key") or ""),
                }
            )
            return _finish_with_cache(
                summary,
                db=db,
                project_id=project_id,
                cfg=cfg,
                cache_namespace=cache_namespace,
                cache_key=cache_key,
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=effective_max_tokens,
                temperature=temperature,
                json_mode=json_mode,
            )
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
    cache_namespace: str | None = None,
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
        cache_namespace=cache_namespace,
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
    cache_namespace: str | None = None,
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
        cache_namespace=cache_namespace,
    )
    return _parse_result(full["content"], json_mode)
