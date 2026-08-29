"""Fixture lifecycle state machine tests (V32-009)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import FixtureStatus
from app.modules.aitde.data import fixture_service, repository


def test_provision_fixture_is_ready(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    assert fixture.status == FixtureStatus.READY.value
    entities = repository.list_fixture_entities(db, fixture.id)
    assert len(entities) >= 1


def test_legal_transition_read_to_leased(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    updated = fixture_service.transition_fixture(db, fixture.id, "LEASED")
    assert updated.status == FixtureStatus.LEASED.value


def test_illegal_transition_rejected(db, ready_fixture):
    fixture = ready_fixture["fixture"]
    # PROVISIONING is not a legal successor of READY.
    with pytest.raises(APIException) as exc:
        fixture_service.transition_fixture(db, fixture.id, "PROVISIONING")
    assert exc.value.http_status == 400
    assert "非法状态迁移" in exc.value.msg


def test_transition_missing_fixture_rejected(db):
    with pytest.raises(APIException) as exc:
        fixture_service.transition_fixture(db, 9999, "READY")
    assert exc.value.http_status == 404
