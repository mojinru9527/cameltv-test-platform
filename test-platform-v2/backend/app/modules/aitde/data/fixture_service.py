"""FixtureService state machine (V32-009).

Lifecycle: PROVISIONING → READY → LEASED → IN_USE → CLEANING → CLEANED / FAILED.
Illegal transitions are rejected.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import DataSourceAccessMode, DataSourceType, FixtureStatus
from app.modules.aitde.data import repository
from app.modules.aitde.data.models import DataFixture, DataPlan, DataSource
from app.modules.aitde.data.strategies import get_builder

_ALLOWED = {
    FixtureStatus.PROVISIONING.value: {FixtureStatus.READY.value, FixtureStatus.FAILED.value},
    FixtureStatus.READY.value: {FixtureStatus.LEASED.value, FixtureStatus.FAILED.value, FixtureStatus.CLEANING.value},
    FixtureStatus.LEASED.value: {FixtureStatus.IN_USE.value, FixtureStatus.READY.value, FixtureStatus.CLEANING.value, FixtureStatus.FAILED.value},
    FixtureStatus.IN_USE.value: {FixtureStatus.CLEANING.value, FixtureStatus.FAILED.value},
    FixtureStatus.CLEANING.value: {FixtureStatus.CLEANED.value, FixtureStatus.FAILED.value},
}


def provision_fixture(
    db: Session,
    plan: DataPlan,
    source: DataSource | None,
    environment_id: int | None,
    project_id: int,
) -> DataFixture:
    """Build the fixture + entities from the plan's strategy and requirements."""
    requirements = repository.list_requirements_by_scenario_version(
        db, plan.scenario_version_id
    )
    if not requirements:
        raise APIException(code=400, msg="数据计划无数据需求，无法 provision", http_status=400)

    builder = get_builder(plan.strategy)
    entities = []
    for req in requirements:
        result = builder.build(source, req, environment_id, project_id)
        entities.extend(result.entities)

    fixture = repository.create_fixture(
        db,
        {
            "project_id": project_id,
            "scenario_version_id": plan.scenario_version_id,
            "data_plan_id": plan.id,
            "environment_id": environment_id,
            "data_source_id": source.id if source else None,
            "strategy": plan.strategy,
            "status": FixtureStatus.PROVISIONING.value,
            "namespace": f"plan-{plan.id}",
            "manifest_json": json.dumps([asdict(e) for e in entities], ensure_ascii=False),
        },
    )
    for e in entities:
        repository.create_fixture_entity(
            db,
            {
                "fixture_id": fixture.id,
                "entity_type": e.entity_type,
                "logical_key": e.logical_key,
                "physical_ref_json": json.dumps(e.physical_ref, ensure_ascii=False),
                "created_by_fixture": e.created_by_fixture,
                "cleanup_action_json": (
                    json.dumps(e.cleanup_action, ensure_ascii=False)
                    if e.cleanup_action
                    else None
                ),
            },
        )
    fixture.status = FixtureStatus.READY.value
    db.commit()
    db.refresh(fixture)
    return fixture


def _resolve_source(
    db: Session,
    project_id: int,
    environment_id: int | None,
    strategy: str,
    data_source_id: int | None,
) -> DataSource | None:
    """Resolve a DataSource for a plan strategy (explicit id wins)."""
    if data_source_id:
        source = repository.get_data_source(db, data_source_id, project_id)
        if not source:
            raise APIException(code=404, msg="数据源不存在", http_status=404)
        return source

    sources = repository.list_data_sources(db, project_id)
    if environment_id is not None:
        sources = [
            s
            for s in sources
            if s.environment_id == environment_id or s.environment_id is None
        ]

    if strategy == "EXISTING":
        chosen = next(
            (
                s
                for s in sources
                if s.access_mode == DataSourceAccessMode.READONLY.value
                and s.source_type in ("MYSQL", "POSTGRES", "API")
            ),
            None,
        )
    elif strategy == "DB_FIXTURE":
        chosen = next(
            (
                s
                for s in sources
                if s.access_mode == DataSourceAccessMode.READWRITE.value
                and s.source_type in ("MYSQL", "POSTGRES")
            ),
            None,
        )
    elif strategy == "API_BUILDER":
        chosen = next(
            (s for s in sources if s.source_type == DataSourceType.API.value), None
        )
    else:  # WORKFLOW / STATIC — no external source needed
        chosen = None

    if strategy in ("EXISTING", "DB_FIXTURE", "API_BUILDER") and chosen is None:
        raise APIException(
            code=400, msg=f"缺少可用于 {strategy} 策略的数据源", http_status=400
        )
    return chosen


def provision_fixture_from_plan(
    db: Session,
    plan_id: int,
    project_id: int,
    environment_id: int | None,
    data_source_id: int | None,
) -> DataFixture:
    """Provision a fixture directly from a data plan (POST /api/v2/fixtures)."""
    plan = repository.get_data_plan(db, plan_id)
    if not plan:
        raise APIException(code=404, msg="数据计划不存在", http_status=404)
    # Policy: high-risk plans must be approved; low-risk plans may provision from DRAFT.
    if plan.status not in ("APPROVED", "EXECUTING"):
        if not (plan.status == "DRAFT" and plan.risk_level in ("P2", "P3")):
            raise APIException(
                code=400,
                msg="数据计划需先批准（APPROVED）后才能 provision",
                http_status=400,
            )
    source = _resolve_source(
        db, project_id, environment_id, plan.strategy, data_source_id
    )
    return provision_fixture(db, plan, source, environment_id, project_id)


def get_fixture(db: Session, fixture_id: int) -> DataFixture:
    fixture = repository.get_fixture(db, fixture_id)
    if not fixture:
        raise APIException(code=404, msg="Fixture 不存在", http_status=404)
    return fixture


def transition_fixture(
    db: Session, fixture_id: int, target: str
) -> DataFixture:
    fixture = repository.get_fixture(db, fixture_id)
    if not fixture:
        raise APIException(code=404, msg="Fixture 不存在", http_status=404)
    allowed = _ALLOWED.get(fixture.status, set())
    if target not in allowed:
        raise APIException(
            code=400,
            msg=f"非法状态迁移：{fixture.status} → {target}",
            http_status=400,
        )
    fixture.status = target
    db.commit()
    db.refresh(fixture)
    return fixture


def to_fixture_dict(db: Session, fixture: DataFixture) -> dict[str, Any]:
    entities = repository.list_fixture_entities(db, fixture.id)
    return {
        "id": fixture.id,
        "project_id": fixture.project_id,
        "scenario_version_id": fixture.scenario_version_id,
        "run_id": fixture.run_id,
        "data_plan_id": fixture.data_plan_id,
        "environment_id": fixture.environment_id,
        "data_source_id": fixture.data_source_id,
        "strategy": fixture.strategy,
        "status": fixture.status,
        "namespace": fixture.namespace,
        "manifest_json": fixture.manifest_json,
        "created_at": fixture.created_at.isoformat() if fixture.created_at else None,
        "expires_at": fixture.expires_at.isoformat() if fixture.expires_at else None,
        "cleanup_status": fixture.cleanup_status,
        "entities": [
            {
                "id": e.id,
                "fixture_id": e.fixture_id,
                "entity_type": e.entity_type,
                "logical_key": e.logical_key,
                "physical_ref_json": e.physical_ref_json,
                "created_by_fixture": e.created_by_fixture,
                "cleanup_action_json": e.cleanup_action_json,
            }
            for e in entities
        ],
    }
