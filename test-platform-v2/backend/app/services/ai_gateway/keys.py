"""Stable cache-key helpers for exact AI response reuse."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_cache_key(
    *,
    project_id: int,
    provider_id: int,
    model: str,
    namespace: str,
    system_prompt: str,
    user_message: str,
    json_mode: bool,
    max_tokens: int,
    temperature: float,
) -> str:
    """Return a project-scoped key that changes with every semantic input."""
    identity = canonical_json(
        {
            "project_id": int(project_id or 0),
            "provider_id": int(provider_id or 0),
            "model": model or "",
            "namespace": namespace or "",
            "system_prompt_hash": sha256_text(system_prompt),
            "user_message_hash": sha256_text(user_message),
            "json_mode": bool(json_mode),
            "max_tokens": int(max_tokens or 0),
            "temperature": round(float(temperature), 6),
        }
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
