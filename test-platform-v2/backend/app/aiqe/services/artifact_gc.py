"""P0：Artifact 30 天留存 / GC。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.services.artifact_storage import get_storage_backend


def purge_expired_artifacts(
    db: Session,
    *,
    retention_days: int = 30,
    now: datetime | None = None,
    storage: Any | None = None,
) -> dict[str, Any]:
    if retention_days < 1:
        raise ValueError("retention_days 必须 >= 1")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    backend = storage or get_storage_backend()
    rows = list(
        db.scalars(select(RunArtifact).where(RunArtifact.created_at < cutoff))
    )
    deleted = 0
    failed = 0
    errors: list[str] = []
    for row in rows:
        try:
            backend.delete(row.storage_uri)
        except Exception as exc:  # 保留记录，避免悬空引用
            failed += 1
            errors.append(f"{row.id}: {exc}")
            continue
        db.delete(row)
        deleted += 1
    db.flush()
    return {
        "cutoff": cutoff,
        "matched": len(rows),
        "deleted": deleted,
        "failed": failed,
        "errors": errors[:10],
    }
