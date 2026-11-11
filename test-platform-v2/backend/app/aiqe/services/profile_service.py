"""M3 / TA-022：Execution Profile / 数据隔离（13 号 §4.13 / §19 TA-022）。

- 三档 purpose：core_isolated / integration / external_live；
- checksum = canonical JSON(purpose+name+version+config) sha256，可复现；
- core_isolated：Run 级 namespace（`iso-<run_id>`）；
- integration：共享 namespace `integration`，但 fixture 写仍需资源锁；
- external_live：禁止写共享 fixture（fail-closed）；
- 并发 Run 通过 `fixture:<key>` 资源锁互斥，第二个 Run 拿不到锁。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.aiqe.models.profile import ExecutionProfile
from app.aiqe.services import resource_lock

PURPOSES = frozenset({"core_isolated", "integration", "external_live"})


class ProfileError(ValueError):
    pass


class ProfileIsolationError(ProfileError):
    pass


def profile_checksum(
    config: dict[str, Any], *, purpose: str, name: str, version: int = 1
) -> str:
    canonical = json.dumps(
        {"purpose": purpose, "name": name, "version": version, "config": config},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_profile(
    db: Session,
    *,
    project_id: int,
    name: str,
    purpose: str,
    config: dict[str, Any] | None = None,
    owner_id: int | None = None,
    version: int = 1,
) -> ExecutionProfile:
    if purpose not in PURPOSES:
        raise ProfileError(f"未知 purpose: {purpose!r}")
    if not name.strip():
        raise ProfileError("profile name 不能为空")
    cfg = config or {}
    row = ExecutionProfile(
        project_id=project_id,
        name=name.strip(),
        purpose=purpose,
        config_json=cfg,
        version=version,
        checksum=profile_checksum(cfg, purpose=purpose, name=name.strip(), version=version),
        owner_id=owner_id,
    )
    db.add(row)
    db.flush()
    return row


def get_profile(db: Session, profile_id: str) -> ExecutionProfile:
    row = db.get(ExecutionProfile, profile_id)
    if row is None:
        raise ProfileError(f"profile 不存在: {profile_id}")
    return row


def approve_profile(db: Session, profile_id: str) -> ExecutionProfile:
    row = get_profile(db, profile_id)
    row.approval_status = "approved"
    db.flush()
    return row


def update_config(db: Session, profile_id: str, config: dict[str, Any]) -> ExecutionProfile:
    row = get_profile(db, profile_id)
    if row.approval_status == "approved":
        raise ProfileError("approved profile 不可修改，请新建 version")
    row.config_json = config
    row.checksum = profile_checksum(
        config, purpose=row.purpose, name=row.name, version=row.version
    )
    db.flush()
    return row


def data_namespace(profile: ExecutionProfile, run_id: str) -> str:
    if profile.purpose == "core_isolated":
        return f"iso-{run_id}"
    if profile.purpose == "integration":
        return "integration"
    return "live"


def guard_fixture_mutation(profile: ExecutionProfile, fixtures: list[str]) -> None:
    if profile.purpose == "external_live" and fixtures:
        raise ProfileIsolationError("external_live 禁止写共享 fixture")


def acquire_fixture_locks(
    db: Session,
    profile: ExecutionProfile,
    run_id: str,
    fixtures: list[str],
    *,
    ttl_seconds: int = 60,
) -> dict[str, int]:
    """按 fixture key 加锁；两个并发 Run 不能同时写同一 fixture。"""
    guard_fixture_mutation(profile, fixtures)
    tokens: dict[str, int] = {}
    acquired: list[str] = []
    try:
        for fixture in fixtures:
            key = f"fixture:{fixture}"
            tokens[key] = resource_lock.acquire(
                db, key, run_id, ttl_seconds=ttl_seconds
            )
            acquired.append(key)
    except resource_lock.LockUnavailable:
        for key in acquired:
            resource_lock.release(db, key, tokens[key])
        raise
    return tokens


def release_fixture_locks(db: Session, tokens: dict[str, int]) -> None:
    for key, token in tokens.items():
        resource_lock.release(db, key, token)
