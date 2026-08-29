"""Cleanup idempotency tests (V32-012)."""
from __future__ import annotations

from app.modules.aitde.common.enums import CleanupStatus, FixtureStatus
from app.modules.aitde.data import cleanup_service, repository


def test_cleanup_success_then_idempotent(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    first = cleanup_service.cleanup_fixture(db, fixture.id)
    assert first["status"] == CleanupStatus.SUCCEEDED.value
    assert first["idempotent"] is False
    assert len(first["actions"]) >= 1

    refreshed = repository.get_fixture(db, fixture.id)
    assert refreshed.status == FixtureStatus.CLEANED.value

    # Second + third cleanups return a consistent no-op result.
    second = cleanup_service.cleanup_fixture(db, fixture.id)
    third = cleanup_service.cleanup_fixture(db, fixture.id)
    assert second["status"] == CleanupStatus.SUCCEEDED.value
    assert second["idempotent"] is True
    assert second["actions"] == []
    assert third["status"] == CleanupStatus.SUCCEEDED.value


def test_cleanup_missing_fixture_rejected(db):
    import pytest

    from app.core.exceptions import APIException

    with pytest.raises(APIException) as exc:
        cleanup_service.cleanup_fixture(db, 9999)
    assert exc.value.http_status == 404
