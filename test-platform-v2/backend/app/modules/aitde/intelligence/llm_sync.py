"""Synchronous LLM JSON client for the AITDE intelligence chain (Batch 207).

Batch 208 (C5): transport/gate/parse now delegate to the shared
``app.services.ai_client``; this module keeps the intelligence-domain error
types so providers/services do not depend on the generic client taxonomy.
"""
from __future__ import annotations

import json
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
    try:
        result = ai_client.chat_completions(
            db,
            project_id,
            system_prompt=system_prompt,
            user_message=json.dumps(user_payload, ensure_ascii=False),
            max_tokens=max_tokens,
            json_mode=True,
        )
    except ai_client.AiClientUnavailableError as exc:
        raise IntelligenceLLMError(str(exc)) from exc
    except ai_client.AiClientResponseError as exc:
        raise IntelligenceLLMResponseError(str(exc)) from exc
    if not isinstance(result, dict):
        raise IntelligenceLLMResponseError("AI response must be a JSON object")
    return result
