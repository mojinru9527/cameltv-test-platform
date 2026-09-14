"""HTTP client for delegated AI Gateway execution."""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class AiGatewayRemoteError(RuntimeError):
    """The configured AI Gateway could not complete the delegated request."""


def remote_requested() -> bool:
    return bool(settings.ai_gateway_url and settings.ai_gateway_role != "gateway")


def remote_enabled() -> bool:
    return bool(remote_requested() and settings.ai_gateway_token)


def _require_token() -> None:
    if not settings.ai_gateway_token:
        raise AiGatewayRemoteError("AI Gateway URL is configured but token is missing")


def _url(path: str) -> str:
    return f"{settings.ai_gateway_url.rstrip('/')}/{path.lstrip('/')}"


def _headers() -> dict[str, str]:
    return {"X-AI-Gateway-Token": settings.ai_gateway_token}


def chat_full(
    *,
    project_id: int,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
    cache_namespace: str | None,
) -> dict[str, Any]:
    _require_token()
    _require_token()
    payload = {
        "project_id": project_id,
        "system_prompt": system_prompt,
        "user_message": user_message,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "json_mode": json_mode,
        "cache_namespace": cache_namespace,
    }
    try:
        response = httpx.post(
            _url("/internal/ai/v1/chat"),
            headers=_headers(),
            json=payload,
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001 - transport boundary
        raise AiGatewayRemoteError(f"AI Gateway request failed: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        raise AiGatewayRemoteError("AI Gateway returned an invalid response")
    return data["data"]


async def achat_full(
    *,
    project_id: int,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
    cache_namespace: str | None,
) -> dict[str, Any]:
    payload = {
        "project_id": project_id,
        "system_prompt": system_prompt,
        "user_message": user_message,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "json_mode": json_mode,
        "cache_namespace": cache_namespace,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(
                _url("/internal/ai/v1/chat"),
                headers=_headers(),
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001 - transport boundary
        raise AiGatewayRemoteError(f"AI Gateway request failed: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        raise AiGatewayRemoteError("AI Gateway returned an invalid response")
    return data["data"]


def embed(texts: list[str]) -> list[list[float]]:
    _require_token()
    try:
        response = httpx.post(
            _url("/internal/ai/v1/embed"),
            headers=_headers(),
            json={"texts": texts},
            timeout=settings.ai_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001 - transport boundary
        raise AiGatewayRemoteError(f"AI Gateway embedding request failed: {exc}") from exc
    vectors = data.get("data", {}).get("vectors") if isinstance(data, dict) else None
    if not isinstance(vectors, list):
        raise AiGatewayRemoteError("AI Gateway returned invalid embeddings")
    return vectors
