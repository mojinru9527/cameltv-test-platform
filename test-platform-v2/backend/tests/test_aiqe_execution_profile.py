"""M3 / TA-022：Execution Profile / 数据隔离单测。"""
from __future__ import annotations

import pytest

from app.aiqe.services import resource_lock
from app.aiqe.services.profile_service import (
    ProfileError,
    ProfileIsolationError,
    approve_profile,
    create_profile,
    data_namespace,
    profile_checksum,
    update_config,
)
from app.aiqe.services.run_service import finish_run_with_profile, start_run_with_profile


def profile(db, purpose="integration", name="p1", config=None):
    return create_profile(
        db,
        project_id=1,
        name=name,
        purpose=purpose,
        config=config or {"browser": "chromium"},
    )


def test_unknown_purpose_rejected(db_session):
    with pytest.raises(ProfileError):
        profile(db_session, purpose="chaos")


def test_checksum_reproducible_and_content_sensitive():
    a = profile_checksum({"a": 1, "b": 2}, purpose="integration", name="p", version=1)
    b = profile_checksum({"b": 2, "a": 1}, purpose="integration", name="p", version=1)
    c = profile_checksum({"a": 1, "b": 3}, purpose="integration", name="p", version=1)
    d = profile_checksum({"a": 1, "b": 2}, purpose="core_isolated", name="p", version=1)
    assert a == b
    assert a != c and a != d


def test_namespaces(db_session):
    core = profile(db_session, purpose="core_isolated")
    integration = profile(db_session, purpose="integration")
    live = profile(db_session, purpose="external_live")
    assert data_namespace(core, "run-1") == "iso-run-1"
    assert data_namespace(core, "run-2") == "iso-run-2"
    assert data_namespace(integration, "run-1") == "integration"
    assert data_namespace(live, "run-1") == "live"


def test_external_live_rejects_fixture_mutation(db_session):
    live = profile(db_session, purpose="external_live")
    with pytest.raises(ProfileIsolationError):
        start_run_with_profile(db_session, run_id="run-1", profile=live, fixtures=["match"])


def test_two_runs_cannot_share_fixture(db_session):
    shared = profile(db_session, purpose="integration")
    scope1 = start_run_with_profile(db_session, run_id="run-1", profile=shared, fixtures=["match"])
    with pytest.raises(resource_lock.LockUnavailable):
        start_run_with_profile(db_session, run_id="run-2", profile=shared, fixtures=["match"])
    finish_run_with_profile(db_session, scope1)
    scope2 = start_run_with_profile(db_session, run_id="run-2", profile=shared, fixtures=["match"])
    assert scope2.fixture_tokens
    finish_run_with_profile(db_session, scope2)


def test_approved_profile_immutable(db_session):
    row = profile(db_session)
    approve_profile(db_session, row.id)
    with pytest.raises(ProfileError):
        update_config(db_session, row.id, {"browser": "webkit"})


def test_core_isolated_starts_with_run_namespace(db_session):
    core = profile(db_session, purpose="core_isolated")
    scope = start_run_with_profile(db_session, run_id="run-9", profile=core, fixtures=["data"])
    assert scope.namespace == "iso-run-9"
    finish_run_with_profile(db_session, scope)
