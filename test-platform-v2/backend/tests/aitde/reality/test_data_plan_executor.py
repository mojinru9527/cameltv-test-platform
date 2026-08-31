"""V3.9-R2 DATA-002 — DataPlanExecutor real orchestration + physical verify.

Covers the full provisioning path: a plan carrying DB_FIXTURE / EXISTING steps is
executed against a real sqlite DataSource; the fixture only reaches READY after the
physical effect is created/found AND verified, and physical facts are recorded on
every FixtureEntity. A failed physical effect drives the fixture/plan to FAILED.
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.data import fixture_service, repository
from app.modules.aitde.data.executors import DataPlanExecutor
from app.modules.aitde.data.executors.base import PHYSICAL_CREATED, PHYSICAL_FOUND, VERIFIED
from app.modules.aitde.data.models import DataPlanStatus, FixtureStatus
from app.modules.aitde.drivers.database.base import DatabaseDriver


class _SqliteDriver(DatabaseDriver):
    source_type = "SQLITE"

    def build_url(self) -> str:
        return f"sqlite:///{self.config['db_path']}"


@pytest.fixture()
def membership_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE membership (id INTEGER PRIMARY KEY, status TEXT, user_id INTEGER)")
        )
        conn.execute(text("INSERT INTO membership (id, status, user_id) VALUES (1, 'ACTIVE', 5)"))
    engine.dispose()
    driver = _SqliteDriver({"db_path": path, "table_allowlist": ["membership"]}, "ref")
    yield driver
    os.remove(path)


def _seed_graph(
    db: Session,
    *,
    strategy: str,
    source_type: str,
    access_mode: str,
    constraints: dict | None = None,
    allowlist: list | None = None,
):
    constraints = constraints if constraints is not None else {"status": "ACTIVE", "user_id": 5}
    source = repository.create_data_source(
        db,
        {
            "source_type": source_type,
            "name": "test-source",
            "access_mode": access_mode,
            "config_json": json.dumps({"table_allowlist": allowlist or ["membership"]}),
        },
        project_id=1,
        user_id=9,
    )
    repository.create_data_requirement(
        db,
        1,
        {
            "requirement_key": "data-membership",
            "entity_type": "membership",
            "constraints_json": json.dumps(constraints),
            "required": True,
            "sharing_policy": "EXCLUSIVE",
            "cleanup_policy": "ALWAYS",
            "source_refs_json": "[]",
        },
    )
    plan = repository.create_data_plan(
        db,
        {
            "scenario_version_id": 1,
            "environment_id": 1,
            "status": "APPROVED",
            "strategy": strategy,
            "plan_hash": "h",
            "risk_level": "P2",
            "created_by_type": "USER",
        },
    )
    repository.create_data_plan_step(
        db,
        {
            "data_plan_id": plan.id,
            "sequence": 1,
            "step_type": "FIND" if strategy == "EXISTING" else "CREATE",
            "driver": strategy.lower(),
            "command_json": json.dumps({"requirement_key": "data-membership", "entity": "membership"}),
            "status": "PENDING",
        },
    )
    db.commit()
    db.refresh(source)
    db.refresh(plan)
    return source, plan


def _fixture_with_entity(
    db: Session, plan, source, *, physical_ref: dict, entity_type: str = "membership", created_by_fixture: bool = True
):
    fixture = repository.create_fixture(
        db,
        {
            "project_id": 1,
            "scenario_version_id": 1,
            "data_plan_id": plan.id,
            "environment_id": 1,
            "data_source_id": source.id,
            "strategy": plan.strategy,
            "status": FixtureStatus.PROVISIONING.value,
            "namespace": f"plan-{plan.id}",
            "manifest_json": "{}",
        },
    )
    entity = repository.create_fixture_entity(
        db,
        {
            "fixture_id": fixture.id,
            "entity_type": entity_type,
            "logical_key": "data-membership",
            "physical_ref_json": json.dumps(physical_ref, ensure_ascii=False),
            "created_by_fixture": created_by_fixture,
            "cleanup_action_json": None,
        },
    )
    db.commit()
    db.refresh(fixture)
    db.refresh(entity)
    return fixture, entity


def test_execute_db_fixture_creates_verifies_and_readies(db, membership_db, monkeypatch):
    source, plan = _seed_graph(db, strategy="DB_FIXTURE", source_type="MYSQL", access_mode="READWRITE")
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver", lambda s: membership_db
    )
    fixture, entity = _fixture_with_entity(
        db, plan, source,
        physical_ref={"kind": "write", "table": "membership", "set": {"status": "ACTIVE", "user_id": 5}},
    )
    outcome = DataPlanExecutor(db).execute(plan, fixture, source)

    assert outcome["ok"] is True
    assert fixture.status == FixtureStatus.READY.value
    # The plan was APPROVED before execution; it stays reusable after READY.
    assert plan.status == DataPlanStatus.APPROVED.value
    assert entity.physical_status == PHYSICAL_CREATED
    assert entity.verification_status == VERIFIED
    assert entity.verified_at is not None
    physical = json.loads(entity.physical_ref_json)
    assert physical["kind"] == "write"
    assert physical["row"]["status"] == "ACTIVE"
    assert physical["row"]["user_id"] == 5
    assert repository.list_steps_by_plan(db, plan.id)[0].status == "SUCCEEDED"


def test_execute_existing_finds_readies_and_not_created_by_fixture(db, membership_db, monkeypatch):
    source, plan = _seed_graph(db, strategy="EXISTING", source_type="MYSQL", access_mode="READONLY")
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver", lambda s: membership_db
    )
    fixture, entity = _fixture_with_entity(
        db, plan, source,
        physical_ref={"kind": "read", "where": {"status": "ACTIVE", "user_id": 5}, "row_limit": 100},
        created_by_fixture=False,
    )
    outcome = DataPlanExecutor(db).execute(plan, fixture, source)

    assert outcome["ok"] is True
    assert fixture.status == FixtureStatus.READY.value
    assert plan.status == DataPlanStatus.APPROVED.value
    # EXISTING references pre-existing data — the fixture did NOT create it.
    assert entity.created_by_fixture is False
    assert entity.physical_status == PHYSICAL_FOUND
    assert entity.verification_status == VERIFIED
    physical = json.loads(entity.physical_ref_json)
    assert physical["kind"] == "read"
    assert physical["rows"][0]["status"] == "ACTIVE"


def test_execute_not_found_fails_closed(db, membership_db, monkeypatch):
    source, plan = _seed_graph(db, strategy="EXISTING", source_type="MYSQL", access_mode="READONLY")
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver", lambda s: membership_db
    )
    fixture, entity = _fixture_with_entity(
        db, plan, source,
        physical_ref={"kind": "read", "where": {"status": "NONE"}, "row_limit": 100},
        created_by_fixture=False,
    )
    outcome = DataPlanExecutor(db).execute(plan, fixture, source)

    assert outcome["ok"] is False
    assert fixture.status == FixtureStatus.FAILED.value
    assert plan.status == DataPlanStatus.FAILED.value
    assert entity.physical_status == "FAILED"
    assert entity.verification_status == "FAILED"
    assert repository.list_steps_by_plan(db, plan.id)[0].status == "FAILED"


def test_execute_unsupported_kind_fails_closed(db, membership_db, monkeypatch):
    source, plan = _seed_graph(db, strategy="DB_FIXTURE", source_type="MYSQL", access_mode="READWRITE")
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver", lambda s: membership_db
    )
    fixture, entity = _fixture_with_entity(
        db, plan, source, physical_ref={"kind": "workflow", "actions": []}
    )
    outcome = DataPlanExecutor(db).execute(plan, fixture, source)

    assert outcome["ok"] is False
    assert fixture.status == FixtureStatus.FAILED.value
    assert entity.physical_status == "FAILED"


# ────────────────────────────────────────────────────────────────────────────
# provision_fixture end-to-end (builder + executor + verify)
# ────────────────────────────────────────────────────────────────────────────


def test_provision_fixture_readies_on_success(db, membership_db, monkeypatch):
    source, plan = _seed_graph(db, strategy="DB_FIXTURE", source_type="MYSQL", access_mode="READWRITE")
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver", lambda s: membership_db
    )
    fixture = fixture_service.provision_fixture(db, plan, source, 1, 1)
    assert fixture.status == FixtureStatus.READY.value
    entity = repository.list_fixture_entities(db, fixture.id)[0]
    assert entity.verification_status == VERIFIED


def test_provision_fixture_raises_on_physical_failure(db, membership_db, monkeypatch):
    # EXISTING with a constraint that matches no row -> real NOT_FOUND at execution.
    source, plan = _seed_graph(
        db, strategy="EXISTING", source_type="MYSQL", access_mode="READONLY",
        constraints={"status": "NONE"},
    )
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver", lambda s: membership_db
    )
    with pytest.raises(APIException):
        fixture_service.provision_fixture(db, plan, source, 1, 1)
    # The fixture was created but left FAILED because verification failed.
    from app.modules.aitde.data.models import DataFixture

    failed = db.query(DataFixture).filter(DataFixture.data_plan_id == plan.id).one()
    assert failed.status == FixtureStatus.FAILED.value
