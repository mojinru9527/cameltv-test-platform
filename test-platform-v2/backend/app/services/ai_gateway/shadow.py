"""Background local-model shadow evaluation."""
from __future__ import annotations

import hashlib
import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.ai_shadow_run import AiShadowRun
from app.services import ai_client
from app.services.ai_gateway.runtime import local_runtime_config, shadow_sample_rate

logger = logging.getLogger("ai_gateway.shadow")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-shadow")


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _json_valid(content: str) -> bool:
    try:
        ai_client.parse_json_object(content)
        return True
    except ai_client.AiClientResponseError:
        return False


def compare_outputs(primary: dict[str, Any], shadow: dict[str, Any], *, json_mode: bool) -> dict[str, Any]:
    primary_content = str(primary.get("content") or "")
    shadow_content = str(shadow.get("content") or "")
    return {
        "primary_content_hash": _hash_text(primary_content),
        "shadow_content_hash": _hash_text(shadow_content),
        "primary_json_valid": _json_valid(primary_content) if json_mode else True,
        "shadow_json_valid": _json_valid(shadow_content) if json_mode else True,
        "exact_match": primary_content == shadow_content,
        "primary_duration_ms": int(primary.get("duration_ms") or 0),
        "shadow_duration_ms": int(shadow.get("duration_ms") or 0),
        "length_delta": len(shadow_content) - len(primary_content),
        "primary_usage_json": json.dumps(primary.get("usage") or {}, ensure_ascii=False),
        "shadow_usage_json": json.dumps(shadow.get("usage") or {}, ensure_ascii=False),
    }


def _record_running(
    db: Session,
    *,
    project_id: int,
    namespace: str,
    input_hash: str,
    primary: dict[str, Any],
    shadow_model: str,
    json_mode: bool,
) -> AiShadowRun:
    row = AiShadowRun(
        project_id=project_id,
        namespace=namespace,
        status="running",
        input_hash=input_hash,
        primary_provider=str(primary.get("model_provider") or ""),
        primary_model=str(primary.get("model_name") or ""),
        shadow_provider="local_openai_compatible",
        shadow_model=shadow_model,
        json_mode=json_mode,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_shadow_once(
    *,
    project_id: int,
    primary_config: Any,
    namespace: str,
    system_prompt: str,
    user_message: str,
    primary: dict[str, Any],
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
) -> int | None:
    """Run one local shadow call synchronously and persist the comparison."""
    cfg = local_runtime_config()
    if cfg is None:
        return None
    db = SessionLocal()
    try:
        row = _record_running(
            db,
            project_id=project_id,
            namespace=namespace,
            input_hash=_hash_text(f"{system_prompt}\n{user_message}"),
            primary=primary,
            shadow_model=cfg.model,
            json_mode=json_mode,
        )
        try:
            shadow = ai_client.call_configured_full(
                cfg.as_ai_config(),
                project_id=project_id,
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
                timeout_seconds=cfg.timeout_seconds,
            )
            comparison = compare_outputs(primary, shadow, json_mode=json_mode)
            for key, value in comparison.items():
                setattr(row, key, value)
            row.status = "succeeded"
            row.finished_at = datetime.now()
            db.commit()
            return row.id
        except Exception as exc:  # noqa: BLE001 - shadow failure is isolated
            row.status = "failed"
            row.error_code = type(exc).__name__[:64]
            row.error_message = str(exc)[:500]
            row.finished_at = datetime.now()
            db.commit()
            logger.warning("Local shadow call failed: %s", exc)
            return row.id
    finally:
        db.close()


def schedule_shadow_run(
    *,
    project_id: int,
    primary_config: Any,
    namespace: str,
    system_prompt: str,
    user_message: str,
    primary: dict[str, Any],
    max_tokens: int,
    temperature: float | None,
    json_mode: bool,
) -> bool:
    """Queue a shadow comparison when enabled; never affect the primary call."""
    if not settings.ai_shadow_enabled or local_runtime_config() is None:
        return False
    rate = shadow_sample_rate()
    if rate <= 0.0 or random.random() >= rate:
        return False
    _executor.submit(
        run_shadow_once,
        project_id=project_id,
        primary_config=primary_config,
        namespace=namespace,
        system_prompt=system_prompt,
        user_message=user_message,
        primary=primary,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )
    return True


def list_shadow_runs(db: Session, project_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(AiShadowRun)
            .where(AiShadowRun.project_id == project_id)
            .order_by(AiShadowRun.id.desc())
            .limit(max(1, min(limit, 200)))
        ).all()
    )
    return [
        {
            "id": row.id,
            "namespace": row.namespace,
            "status": row.status,
            "primary_model": row.primary_model,
            "shadow_model": row.shadow_model,
            "primary_json_valid": row.primary_json_valid,
            "shadow_json_valid": row.shadow_json_valid,
            "exact_match": row.exact_match,
            "primary_duration_ms": row.primary_duration_ms,
            "shadow_duration_ms": row.shadow_duration_ms,
            "length_delta": row.length_delta,
            "error_code": row.error_code,
            "error_message": row.error_message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        }
        for row in rows
    ]
