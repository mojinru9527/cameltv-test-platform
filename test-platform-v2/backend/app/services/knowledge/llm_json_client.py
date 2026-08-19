"""Small DeepSeek/OpenAI-compatible JSON client for knowledge extraction.

Only sanitized text is sent to the external model. OCR remains a local
responsibility; this client performs semantic analysis of already-extracted text.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai_config_service import AIProviderUnconfiguredError, ai_config_service


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


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fenced:
        text = fenced.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMResponseError("AI response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMResponseError("AI response must be a JSON object")
    return parsed


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
        cfg = ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError as exc:
        raise LLMUnavailableError(str(exc)) from exc

    request_body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": sanitize_external_text(system_prompt)},
            {
                "role": "user",
                "content": json.dumps(
                    _sanitize_payload(user_payload),
                    ensure_ascii=False,
                ),
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
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                response = await client.post(
                    f"{cfg.api_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {cfg.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"]
            return _parse_json_object(raw)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
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
            raise LLMUnavailableError(
                f"AI API returned HTTP {exc.response.status_code}"
            ) from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LLMResponseError("AI response envelope is invalid") from exc

    raise LLMUnavailableError(f"AI request failed: {last_error}") from last_error
