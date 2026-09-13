"""Persistence and operational helpers for exact AI response caching."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.ai_gateway_cache import AiResponseCache

logger = logging.getLogger("ai_gateway.cache")


def _new_session(bind=None) -> Session:
    if bind is not None:
        return Session(bind=bind)
    return SessionLocal()


def lookup_exact_cache(db, *, project_id: int, cache_key: str) -> dict[str, Any] | None:
    """Return a cached response summary and bump its hit counter.

    Cache failures are deliberately non-fatal: the caller must fall through to
    the configured model rather than turning an optimization into an outage.
    """
    if db is None or not cache_key:
        return None
    session = None
    try:
        session = _new_session(db.get_bind())
        row = session.scalar(
            select(AiResponseCache).where(
                AiResponseCache.project_id == int(project_id or 0),
                AiResponseCache.cache_key == cache_key,
            )
        )
        if row is None:
            return None
        now = datetime.now()
        if row.expires_at is not None and row.expires_at <= now:
            session.delete(row)
            session.commit()
            return None
        row.hit_count = int(row.hit_count or 0) + 1
        row.last_hit_at = now
        session.commit()
        try:
            parsed = json.loads(row.response_json or "{}")
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed exact-cache response: key=%s", cache_key[:16])
            session.delete(row)
            session.commit()
            return None
        return parsed if isinstance(parsed, dict) else None
    except SQLAlchemyError:
        logger.exception("Exact AI cache lookup failed; falling through to model")
        return None
    finally:
        if session is not None:
            session.close()


def store_exact_cache(
    db,
    *,
    project_id: int,
    namespace: str,
    cache_key: str,
    provider_id: int,
    provider_type: str,
    model: str,
    prompt_hash: str,
    input_hash: str,
    response: dict[str, Any],
    usage: dict[str, Any] | None = None,
    ttl_seconds: int | None = None,
) -> None:
    """Persist a successful, non-truncated model response summary."""
    if db is None or not cache_key or not namespace:
        return
    ttl = settings.ai_exact_cache_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
    expires_at = datetime.now() + timedelta(seconds=max(0, ttl))
    session = None
    try:
        session = _new_session(db.get_bind())
        row = session.scalar(
            select(AiResponseCache).where(
                AiResponseCache.project_id == int(project_id or 0),
                AiResponseCache.cache_key == cache_key,
            )
        )
        payload = json.dumps(response, ensure_ascii=False, default=str)
        usage_payload = json.dumps(usage or {}, ensure_ascii=False, default=str)
        if row is None:
            row = AiResponseCache(
                project_id=int(project_id or 0),
                namespace=namespace,
                cache_key=cache_key,
                provider_id=int(provider_id or 0),
                provider_type=provider_type or "",
                model=model or "",
                prompt_hash=prompt_hash,
                input_hash=input_hash,
                response_json=payload,
                usage_json=usage_payload,
                finish_reason=str(response.get("finish_reason") or "unknown"),
                expires_at=expires_at,
            )
            session.add(row)
        else:
            row.namespace = namespace
            row.provider_id = int(provider_id or 0)
            row.provider_type = provider_type or ""
            row.model = model or ""
            row.prompt_hash = prompt_hash
            row.input_hash = input_hash
            row.response_json = payload
            row.usage_json = usage_payload
            row.finish_reason = str(response.get("finish_reason") or "unknown")
            row.expires_at = expires_at
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
    except SQLAlchemyError:
        logger.exception("Exact AI cache write failed; keeping model response")
    finally:
        if session is not None:
            session.close()


def clear_exact_cache(db, project_id: int, namespace: str | None = None) -> int:
    if db is None:
        return 0
    stmt = delete(AiResponseCache).where(AiResponseCache.project_id == int(project_id or 0))
    if namespace:
        stmt = stmt.where(AiResponseCache.namespace == namespace)
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)


def exact_cache_stats(db, project_id: int) -> dict[str, Any]:
    if db is None:
        return {
            "enabled": bool(settings.ai_exact_cache_enabled),
            "entries": 0,
            "active_entries": 0,
            "expired_entries": 0,
            "hit_count": 0,
            "namespaces": [],
        }
    now = datetime.now()
    rows = list(
        db.scalars(
            select(AiResponseCache)
            .where(AiResponseCache.project_id == int(project_id or 0))
            .order_by(AiResponseCache.namespace.asc(), AiResponseCache.id.asc())
        ).all()
    )
    active = sum(1 for row in rows if row.expires_at is None or row.expires_at > now)
    namespaces = sorted({row.namespace for row in rows if row.namespace})
    return {
        "enabled": bool(settings.ai_exact_cache_enabled),
        "entries": len(rows),
        "active_entries": active,
        "expired_entries": len(rows) - active,
        "hit_count": sum(int(row.hit_count or 0) for row in rows),
        "namespaces": namespaces,
    }

