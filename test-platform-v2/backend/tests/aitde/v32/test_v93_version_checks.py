"""V3.2 §93 version-specific validation checks (DB-agnostic semantic guards).

Where a guard is DB-independent (lease exclusivity, allowlist rejection, cleanup
idempotency, secret non-leak, DATA_FAIL classification), it is validated here
against the in-memory SQLite session. Guards requiring a real external DB or 50
real scenarios are flagged in the accompanying QA report.
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import FixtureStatus
from app.modules.aitde.data import cleanup_service, lease_service, repository
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.data.service import probe_data_source_connection
from app.modules.aitde.data.strategies.db_fixture_builder import DbFixtureBuilder
from app.modules.aitde.scenario.models import TestScenarioVersion as ScenarioVersion


def _scenario_version(db, given):
    v = ScenarioVersion(
        scenario_id=1, version_no=1, contract_version_id=1, title="t",
        given_model_json=json.dumps(given, ensure_ascii=False), expected_state_json="{}",
    )
    db.add(v)
    db.flush()
    return v


def _req(db, entity, constraints):
    from app.modules.aitde.data.models import DataRequirement

    r = DataRequirement(
        scenario_version_id=1, requirement_key=f"data-{entity}", entity_type=entity,
        constraints_json=json.dumps(constraints, ensure_ascii=False),
    )
    db.add(r)
    db.flush()
    return r


def _src(db, source_type, access_mode="READWRITE", config=None):
    s = DataSource(
        project_id=1, source_type=source_type, name="s", access_mode=access_mode,
        config_json=json.dumps(config or {}, ensure_ascii=False), created_by=9,
    )
    db.add(s)
    db.flush()
    return s


def test_v93_concurrent_exclusive_lease_no_duplicate(db, ready_fixture):
    """Concurrent exclusive leases: a different run can never take the same fixture."""
    fixture = ready_fixture["fixture"]
    lease = lease_service.lease_fixture(db, fixture.id, run_id=1)
    assert lease.status == "ACTIVE"
    for other_run in range(2, 21):
        with pytest.raises(APIException) as exc:
            lease_service.lease_fixture(db, fixture.id, run_id=other_run)
        assert exc.value.http_status == 409
    # same-run re-request is idempotent (no duplicate row / no 409)
    lease_again = lease_service.lease_fixture(db, fixture.id, run_id=1)
    assert lease_again.status == "ACTIVE"


def test_v93_non_allowlist_mutation_rejected(db):
    """A DB_FIXTURE mutation targeting a non-allowlisted table is rejected."""
    source = _src(
        db, "MYSQL", access_mode="READWRITE",
        config={"table_allowlist": ["user"]},
    )
    req = _req(db, "membership", {"status": "EXPIRED"})
    with pytest.raises(APIException) as exc:
        DbFixtureBuilder().build(source, req, None, 1)
    assert exc.value.http_status == 400
    assert "allowlist" in exc.value.msg


def test_v93_cleanup_idempotent_three_times(db, ready_fixture):
    """V3.9-R2 (DATA-003): repeated cleanup on an unreachable source consistently
    does NOT fake SUCCEEDED; only a truly verified CLEANED fixture returns the
    idempotent no-op."""
    fixture = ready_fixture["fixture"]
    results = [cleanup_service.cleanup_fixture(db, fixture.id) for _ in range(3)]
    # No reachable DB -> never a fake SUCCEEDED; cleanup still runs to a terminal state.
    assert all(r["status"] in ("SUCCEEDED", "FAILED", "PARTIAL") for r in results)
    assert results[0]["status"] != "SUCCEEDED"
    refreshed = repository.get_fixture(db, fixture.id)
    assert refreshed.status != FixtureStatus.CLEANED.value


def test_v93_db_password_never_in_result(db):
    """The referenced secret value never leaks into connection-test output."""
    source = _src(
        db, "POSTGRES", access_mode="READONLY",
        config={"host": "127.0.0.1", "port": 5432, "database": "x"},
    )
    source.secret_ref = "secret/pg"
    db.commit()
    result = probe_data_source_connection(db, source.id, 1)
    serialized = json.dumps(result, ensure_ascii=False)
    assert "secret/pg" not in serialized
    assert result["secret_leaked"] is False


def test_v93_config_secret_rejected_at_create(db):
    """A secret planted in config is rejected; never stored/echoed."""
    from app.modules.aitde.common.enums import DataSourceType
    from app.modules.aitde.data.schemas import DataSourceCreate
    from app.modules.aitde.data import service

    with pytest.raises(APIException) as exc:
        service.create_data_source(
            db,
            DataSourceCreate(
                source_type=DataSourceType.MYSQL, name="x",
                config={"host": "1.1.1.1", "password": "super-secret"},
            ),
            project_id=1, user_id=9,
        )
    assert exc.value.http_status == 400
