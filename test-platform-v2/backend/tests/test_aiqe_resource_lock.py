"""M2 / TA-010.3：资源锁单测。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.aiqe.models.workflow import ResourceLock
from app.aiqe.services import resource_lock


def test_acquire_exclusive_and_fencing(db_session):
    token1 = resource_lock.acquire(db_session, "fixture:match", "run1:n1")
    assert token1 == 1
    with pytest.raises(resource_lock.LockUnavailable):
        resource_lock.acquire(db_session, "fixture:match", "run2:n1")

    # 同 owner 续租，token 不变
    assert resource_lock.acquire(db_session, "fixture:match", "run1:n1") == token1
    assert resource_lock.release(db_session, "fixture:match", token1) is True

    token2 = resource_lock.acquire(db_session, "fixture:match", "run2:n1")
    assert token2 == token1 + 1


def test_renew_requires_matching_token(db_session):
    token = resource_lock.acquire(db_session, "account:admin", "run1:n1")
    assert resource_lock.renew(db_session, "account:admin", token) is True
    assert resource_lock.renew(db_session, "account:admin", token + 1) is False


def test_expired_lock_can_be_taken_over(db_session):
    token = resource_lock.acquire(db_session, "db:write", "run1:n1")
    row = db_session.get(ResourceLock, "db:write")
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    token2 = resource_lock.acquire(db_session, "db:write", "run2:n1")
    assert token2 == token + 1
    assert resource_lock.renew(db_session, "db:write", token) is False


def test_release_wrong_token_rejected(db_session):
    token = resource_lock.acquire(db_session, "device:phone", "run1:n1")
    assert resource_lock.release(db_session, "device:phone", token + 1) is False
    assert resource_lock.release(db_session, "device:phone", token) is True


def test_reap_expired(db_session):
    token = resource_lock.acquire(db_session, "network:egress", "run1:n1")
    resource_lock.release(db_session, "network:egress", token)
    assert resource_lock.reap_expired(db_session) == 1
