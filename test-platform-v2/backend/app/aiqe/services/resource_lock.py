"""M2 / TA-010.3：资源锁（TTL + heartbeat + fencing token）。

MVP 实现为 DB 行级锁：
- acquire：行不存在则插入（fencing=1）；已过期则 token+1 抢占；同 owner 续租；否则冲突；
- renew：token 必须匹配且未过期；
- release：把 expires_at 置为过期并清空 owner（保留 token 单调）；
- reap_expired：清过期行（可选 GC）。

并发说明：SQLite 单写者 + PK 唯一约束兜底；PostgreSQL 行锁（with_for_update）串行化。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.aiqe.models.workflow import ResourceLock

DEFAULT_TTL_SECONDS = 60


class LockUnavailable(RuntimeError):
    """锁被其他 owner 持有且未过期。"""


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    # SQLite 读回的是 naive datetime；统一按 UTC 解释。
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _row(db: Session, key: str) -> ResourceLock | None:
    return db.scalar(select(ResourceLock).where(ResourceLock.key == key).with_for_update())


def acquire(
    db: Session, key: str, owner_id: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> int:
    ttl = max(1, int(ttl_seconds))
    now = _now()
    row = _row(db, key)
    if row is None:
        row = ResourceLock(
            key=key,
            owner_id=owner_id,
            fencing_token=1,
            expires_at=now + timedelta(seconds=ttl),
            updated_at=now,
        )
        db.add(row)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            row = _row(db, key)
            if row is None:
                raise
            return _take_over(db, row, owner_id, now, ttl)
        return row.fencing_token

    if _as_utc(row.expires_at) <= now or row.owner_id == owner_id:
        return _take_over(db, row, owner_id, now, ttl)
    raise LockUnavailable(f"lock {key!r} held by {row.owner_id!r}")


def _take_over(
    db: Session, row: ResourceLock, owner_id: str, now: datetime, ttl: int
) -> int:
    if row.owner_id != owner_id:
        row.fencing_token = int(row.fencing_token or 0) + 1
    row.owner_id = owner_id
    row.expires_at = now + timedelta(seconds=ttl)
    row.updated_at = now
    db.flush()
    return row.fencing_token


def renew(db: Session, key: str, token: int, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    row = _row(db, key)
    if row is None or row.fencing_token != token:
        return False
    now = _now()
    if _as_utc(row.expires_at) <= now:
        return False
    row.expires_at = now + timedelta(seconds=max(1, int(ttl_seconds)))
    row.updated_at = now
    db.flush()
    return True


def release(db: Session, key: str, token: int) -> bool:
    row = _row(db, key)
    if row is None or row.fencing_token != token:
        return False
    row.owner_id = ""
    row.expires_at = _now() - timedelta(seconds=1)
    row.updated_at = _now()
    db.flush()
    return True


def reap_expired(db: Session) -> int:
    deleted = (
        db.query(ResourceLock)
        .filter(ResourceLock.expires_at < _now())
        .delete(synchronize_session=False)
    )
    return int(deleted or 0)
