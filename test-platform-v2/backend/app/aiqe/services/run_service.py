"""M3 / TA-022：带 Execution Profile 的 Run 启动（隔离 namespace + fixture 锁）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.aiqe.models.profile import ExecutionProfile
from app.aiqe.services.profile_service import (
    acquire_fixture_locks,
    data_namespace,
    release_fixture_locks,
)


@dataclass
class RunProfileScope:
    run_id: str
    namespace: str
    fixture_tokens: dict[str, int] = field(default_factory=dict)


def start_run_with_profile(
    db: Session,
    *,
    run_id: str,
    profile: ExecutionProfile,
    fixtures: list[str] | None = None,
) -> RunProfileScope:
    """启动 Run：返回隔离 namespace，并占用 fixture 锁（并发 Run 互斥）。"""
    tokens = acquire_fixture_locks(db, profile, run_id, list(fixtures or []))
    return RunProfileScope(
        run_id=run_id,
        namespace=data_namespace(profile, run_id),
        fixture_tokens=tokens,
    )


def finish_run_with_profile(db: Session, scope: RunProfileScope) -> None:
    release_fixture_locks(db, scope.fixture_tokens)
    scope.fixture_tokens = {}
