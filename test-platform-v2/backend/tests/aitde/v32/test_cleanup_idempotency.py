"""Cleanup idempotency tests (V32-012)."""
from __future__ import annotations

from app.modules.aitde.common.enums import CleanupStatus, FixtureStatus
from app.modules.aitde.data import cleanup_service, repository


def test_cleanup_no_fake_success_without_real_source(db, ready_fixture):
    """V3.9-R2 (DATA-003): a MYSQL source with no reachable DB must NOT report
    CLEANED — cleanup is real compensation and only CLEANED after verification."""
    fixture = ready_fixture["fixture"]
    first = cleanup_service.cleanup_fixture(db, fixture.id)
    assert first["status"] in (CleanupStatus.FAILED.value, CleanupStatus.PARTIAL.value)
    assert first["idempotent"] is False

    refreshed = repository.get_fixture(db, fixture.id)
    assert refreshed.status != FixtureStatus.CLEANED.value
    assert refreshed.cleanup_status in (
        CleanupStatus.FAILED.value,
        CleanupStatus.PARTIAL.value,
    )


def test_cleanup_missing_fixture_rejected(db):
    import pytest

    from app.core.exceptions import APIException

    with pytest.raises(APIException) as exc:
        cleanup_service.cleanup_fixture(db, 9999)
    assert exc.value.http_status == 404


def test_cleanup_already_cleaned_is_idempotent(db, ready_fixture):
    """V3.9-R2 (DATA-003): a truly-CLEANED fixture returns the idempotent no-op,
    but only after it was really verified — never a silent fake success."""
    fixture = ready_fixture["fixture"]
    fixture.status = FixtureStatus.CLEANED.value
    fixture.cleanup_status = CleanupStatus.SUCCEEDED.value
    db.commit()

    result = cleanup_service.cleanup_fixture(db, fixture.id)
    assert result["status"] == CleanupStatus.SUCCEEDED.value
    assert result["idempotent"] is True
    assert result["actions"] == []
