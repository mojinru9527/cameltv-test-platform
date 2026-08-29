"""Fixture lease concurrency tests (V32-010)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import FixtureLeaseStatus, FixtureStatus
from app.modules.aitde.data import fixture_service, lease_service, repository


def test_lease_activates_and_excludes_other_run(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    lease = lease_service.lease_fixture(db, fixture.id, run_id=100)
    assert lease.status == FixtureLeaseStatus.ACTIVE.value
    # A different run cannot take the same exclusive fixture.
    with pytest.raises(APIException) as exc:
        lease_service.lease_fixture(db, fixture.id, run_id=200)
    assert exc.value.http_status == 409
    # Same run re-lease (e.g. after expiry) is allowed.
    lease2 = lease_service.lease_fixture(db, fixture.id, run_id=100)
    assert lease2.status == FixtureLeaseStatus.ACTIVE.value


def test_lease_on_non_ready_fixture_rejected(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    fixture_service.transition_fixture(db, fixture.id, "CLEANING")
    with pytest.raises(APIException) as exc:
        lease_service.lease_fixture(db, fixture.id, run_id=100)
    assert exc.value.http_status == 400


def test_release_returns_fixture_to_ready(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    lease = lease_service.lease_fixture(db, fixture.id, run_id=7)
    released = lease_service.release_lease(db, lease.id)
    assert released.status == FixtureLeaseStatus.RELEASED.value
    assert released.released_at is not None
    refreshed = repository.get_fixture(db, fixture.id)
    assert refreshed.status == FixtureStatus.READY.value


def test_release_missing_lease_rejected(db):
    with pytest.raises(APIException) as exc:
        lease_service.release_lease(db, 9999)
    assert exc.value.http_status == 404
