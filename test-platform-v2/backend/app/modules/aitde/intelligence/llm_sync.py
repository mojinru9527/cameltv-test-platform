"""Synchronous LLM JSON client for the AITDE intelligence chain (Batch 207).

Batch 208 (C5): transport/gate/parse now delegate to the shared
``app.services.ai_client``; this module keeps the intelligence-domain error
types so providers/services do not depend on the generic client taxonomy.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from app.services import ai_client


class IntelligenceLLMError(RuntimeError):
    """The configured model could not be reached (disabled/transient/HTTP)."""


class IntelligenceLLMResponseError(ValueError):
    """The model returned an unusable response (contract break, never masked)."""


def call_llm_json(
    *,
    db,
    project_id: int,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call the configured model and return one validated JSON object.

    Transient failures retry per ``settings.ai_retry_attempts`` then raise
    ``IntelligenceLLMError``; malformed content raises
    ``IntelligenceLLMResponseError``.
    """
    result, _metadata = call_llm_json_full(
        db=db,
        project_id=project_id,
        system_prompt=system_prompt,
        user_payload=user_payload,
        max_tokens=max_tokens,
    )
    return result


def call_llm_json_full(
    *,
    db,
    project_id: int,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int = 4096,
    prompt_version: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return validated JSON plus privacy-safe operation telemetry."""
    user_message = json.dumps(user_payload, ensure_ascii=False, sort_keys=True)
    started = time.perf_counter()
    try:
        full = ai_client.chat_completions_full(
            db,
            project_id,
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            json_mode=True,
            cache_namespace="aitde-cache-v1",
        )
    except ai_client.AiClientUnavailableError as exc:
        raise IntelligenceLLMError(str(exc)) from exc
    except ai_client.AiClientResponseError as exc:
        raise IntelligenceLLMResponseError(str(exc)) from exc
    try:
        result = ai_client.parse_json_object(full["content"])
    except ai_client.AiClientResponseError as exc:
        raise IntelligenceLLMResponseError(str(exc)) from exc
    if not isinstance(result, dict):
        raise IntelligenceLLMResponseError("AI response must be a JSON object")
    provider = str(full.get("model_provider") or "")
    model = str(full.get("model_name") or "")
    metadata = {
        "model_provider": provider,
        "model_name": model,
        "model_config_hash": hashlib.sha256(
            f"{provider}|{model}".encode("utf-8")
        ).hexdigest(),
        "prompt_version": f"{prompt_version}:cache-v1" if prompt_version else "cache-v1",
        "input_hash": hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "token_usage": full.get("usage") or {},
        "exact_cache_status": str(full.get("cache_status") or ""),
        "exact_cache_key": str(full.get("cache_key") or ""),
        "exact_cache_saved_usage": full.get("cache_saved_usage") or {},
    }
    return result, metadata
