"""P0 + AUD-008：Artifact 30 天留存 / GC（墓碑删除，保留审计元数据）。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import ArtifactUploadStatus, RunArtifact
from app.aiqe.services.artifact_storage import get_storage_backend


def purge_expired_artifacts(
    db: Session,
    *,
    retention_days: int = 30,
    now: datetime | None = None,
    storage: Any | None = None,
) -> dict[str, Any]:
    """删除过期**存储对象**并把行标记为 `PURGED` 墓碑（不再硬删记录）。

    v1.5 §02 AUD-008：「过期 Artifact 按 Retention Policy 清理，**元数据保留审计墓碑**」。
    """
    if retention_days < 1:
        raise ValueError("retention_days 必须 >= 1")
    moment = now or datetime.now(UTC)
    cutoff = moment - timedelta(days=retention_days)
    backend = storage or get_storage_backend()
    rows = list(
        db.scalars(
            select(RunArtifact).where(
                RunArtifact.created_at < cutoff,
                RunArtifact.upload_status != ArtifactUploadStatus.PURGED.value,
            )
        )
    )
    purged = 0
    failed = 0
    errors: list[str] = []
    for row in rows:
        try:
            if row.storage_uri:
                backend.delete(row.storage_uri)
        except Exception as exc:  # 保留记录，避免悬空引用
            failed += 1
            errors.append(f"{row.id}: {exc}")
            continue
        row.storage_uri = ""
        row.upload_status = ArtifactUploadStatus.PURGED.value
        row.deleted_at = moment
        row.metadata_json = {
            **(row.metadata_json or {}),
            "purged_at": moment.isoformat(),
            "purge_reason": f"retention_{retention_days}_days",
        }
        purged += 1
    db.flush()
    return {
        "cutoff": cutoff,
        "matched": len(rows),
        "purged": purged,
        "deleted": purged,
        "failed": failed,
        "errors": errors[:10],
    }
