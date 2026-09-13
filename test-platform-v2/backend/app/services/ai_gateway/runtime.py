"""Local OpenAI-compatible runtime configuration and health helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass
from types import SimpleNamespace

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class LocalRuntimeConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    max_output_chars: int

    def as_ai_config(self) -> SimpleNamespace:
        return SimpleNamespace(
            provider_id=0,
            provider_name="Local Runtime",
            provider_type="local_openai_compatible",
            model=self.model,
            api_base_url=self.base_url.rstrip("/"),
            api_key=self.api_key,
        )


def local_runtime_config() -> LocalRuntimeConfig | None:
    if not settings.ai_local_runtime_enabled:
        return None
    base_url = (settings.ai_local_base_url or "").strip().rstrip("/")
    model = (settings.ai_local_model or "").strip()
    if not base_url or not model:
        return None
    return LocalRuntimeConfig(
        base_url=base_url,
        api_key=settings.ai_local_api_key or "",
        model=model,
        timeout_seconds=max(1.0, float(settings.ai_shadow_timeout_seconds)),
        max_output_chars=max(1000, int(settings.ai_shadow_max_output_chars)),
    )


def shadow_sample_rate() -> float:
    return min(1.0, max(0.0, float(settings.ai_shadow_sample_rate or 0.0)))


def runtime_status() -> dict:
    cfg = local_runtime_config()
    return {
        "enabled": bool(settings.ai_local_runtime_enabled),
        "configured": cfg is not None,
        "base_url": cfg.base_url if cfg else (settings.ai_local_base_url or "").rstrip("/"),
        "model": cfg.model if cfg else "",
        "shadow_enabled": bool(settings.ai_shadow_enabled),
        "shadow_sample_rate": shadow_sample_rate(),
        "shadow_timeout_seconds": max(1.0, float(settings.ai_shadow_timeout_seconds)),
        "api_key_configured": bool(settings.ai_local_api_key),
    }


def check_local_runtime(timeout: float = 5.0) -> dict:
    cfg = local_runtime_config()
    if cfg is None:
        return {"ok": False, "kind": "unconfigured", "error": "本地 runtime 未启用或未配置"}
    headers = {}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    started = time.perf_counter()
    try:
        response = httpx.get(
            f"{cfg.base_url.rstrip('/')}/models",
            headers=headers,
            timeout=min(max(1.0, float(timeout)), cfg.timeout_seconds),
        )
        response.raise_for_status()
        data = response.json()
        models = data.get("data") if isinstance(data, dict) else None
        ids = [item.get("id") for item in models or [] if isinstance(item, dict) and item.get("id")]
        return {
            "ok": True,
            "kind": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "model": cfg.model,
            "model_available": cfg.model in ids if ids else None,
        }
    except Exception as exc:  # noqa: BLE001 - health endpoint must return readable status
        return {
            "ok": False,
            "kind": "unreachable",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }
