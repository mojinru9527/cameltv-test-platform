"""TC-005: release 后锁必须立即可被其他 owner 获取。"""
from __future__ import annotations

from app.aiqe.services import resource_lock


def test_released_lock_is_immediately_acquirable(db_session):
    key = "match:TC005-test"
    first = resource_lock.acquire(db_session, key, "run-a", ttl_seconds=60)
    assert resource_lock.release(db_session, key, first) is True
    second = resource_lock.acquire(db_session, key, "run-b", ttl_seconds=60)
    assert second != first
    assert resource_lock.release(db_session, key, second) is True
