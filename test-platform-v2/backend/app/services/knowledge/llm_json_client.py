"""Small DeepSeek/OpenAI-compatible JSON client for knowledge extraction.

Only sanitized text is sent to the external model. OCR remains a local
responsibility; this client performs semantic analysis of already-extracted text.

Batch 208 (C5): the transport/gate/parse is delegated to the shared
``app.services.ai_client``; this module keeps knowledge-local sanitization and
error types.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings  # noqa: F401  (module-level compat)
from app.services import ai_client
from app.services.ai_config_service import (  # noqa: F401  (module-level compat)
    AIProviderUnconfiguredError,
    ai_config_service,
)

class LLMUnavailableError(RuntimeError):
    """The configured semantic model cannot currently be used."""


class LLMResponseError(ValueError):
    """The semantic model returned an unusable response."""


_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (
        re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\b\s*[:=]\s*[^\s,;]+"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"),
        "[REDACTED_EMAIL]",
    ),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[REDACTED_PHONE]"),
)


def sanitize_external_text(value: str, *, max_chars: int = 60_000) -> str:
    """Redact common credentials and personal contact data before egress."""
    sanitized = value or ""
    for pattern, replacement in _REDACTIONS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized[:max_chars]


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_external_text(value)
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_payload(item) for key, item in value.items()}
    return value


def _parse_json_object(raw: str) -> dict:
    """Back-compat alias delegating to the shared JSON parser."""
    try:
        return ai_client.parse_json_object(raw)
    except ai_client.AiClientResponseError as exc:
        raise LLMResponseError(str(exc)) from exc


async def call_json_model(
    *,
    db,
    project_id: int,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Call the configured model and return one validated JSON object."""
    if not settings.ai_enabled:
        raise LLMUnavailableError("AI service is disabled")
    try:
        ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError as exc:
        raise LLMUnavailableError("未配置 AI 提供方") from exc
    try:
        result = await ai_client.achat_completions(
            db,
            project_id,
            system_prompt=sanitize_external_text(system_prompt),
            user_message=json.dumps(
                _sanitize_payload(user_payload), ensure_ascii=False
            ),
            max_tokens=max_tokens,
            json_mode=True,
        )
    except ai_client.AiClientUnavailableError as exc:
        raise LLMUnavailableError(str(exc)) from exc
    except ai_client.AiClientResponseError as exc:
        raise LLMResponseError(str(exc)) from exc
    if not isinstance(result, dict):
        raise LLMResponseError("AI response must be a JSON object")
    return result
