"""V33-002 CommandPlan Versioning tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.command import service
from app.modules.aitde.command.models import CommandPlanVersion
from app.modules.aitde.common.enums import CommandPlanStatus


def _ir():
    return {
        "schema_version": "1.0",
        "commands": [
            {"driver": "browser", "action": "goto", "input": {"route": "/member"}},
            {"driver": "assertion", "action": "evaluate", "input": {"oracle_key": "ui-active"}},
        ],
    }


def test_create_version_hash_stable_and_validates(db):
    plan = service.get_or_create_plan(db, 1)
    v1 = service.create_version(db, plan, scenario_version_id=10, contract_version_id=20, plan_json=_ir())
    v2 = service.create_version(db, plan, scenario_version_id=10, contract_version_id=20, plan_json=_ir())
    assert v1.plan_hash == v2.plan_hash
    assert v1.status == CommandPlanStatus.DRAFT.value
    assert v1.version_no == 1
    assert v2.version_no == 2


def test_create_version_rejects_invalid_ir(db):
    plan = service.get_or_create_plan(db, 1)
    with pytest.raises(APIException) as exc:
        service.create_version(
            db, plan, scenario_version_id=10, contract_version_id=20,
            plan_json={"schema_version": "1.0", "commands": [{"driver": "browser", "action": "teleport", "input": {}}]},
        )
    assert exc.value.http_status == 400


def test_activate_marks_others_stale_and_current(db):
    plan = service.get_or_create_plan(db, 1)
    v1 = service.create_version(db, plan, scenario_version_id=10, contract_version_id=20, plan_json=_ir())
    service.approve_version(db, v1.id, 9)
    active = service.activate_version(db, v1.id, 9)
    assert active.status == CommandPlanStatus.ACTIVE.value
    assert plan.current_version_no == 1

    v2 = service.create_version(db, plan, scenario_version_id=10, contract_version_id=20, plan_json=_ir())
    service.approve_version(db, v2.id, 9)
    active2 = service.activate_version(db, v2.id, 9)
    assert active2.status == CommandPlanStatus.ACTIVE.value
    db.refresh(active)
    assert active.status == CommandPlanStatus.STALE.value


def test_activate_requires_validated(db):
    plan = service.get_or_create_plan(db, 1)
    v = service.create_version(db, plan, scenario_version_id=10, contract_version_id=20, plan_json=_ir())
    with pytest.raises(APIException) as exc:
        service.activate_version(db, v.id, 9)
    assert exc.value.http_status == 400


def test_active_version_immutable(db):
    plan = service.get_or_create_plan(db, 1)
    v = service.create_version(db, plan, scenario_version_id=10, contract_version_id=20, plan_json=_ir())
    service.approve_version(db, v.id, 9)
    service.activate_version(db, v.id, 9)
    refreshed = db.get(CommandPlanVersion, v.id)
    with pytest.raises(APIException) as exc:
        service.ensure_active_immutable(refreshed)
    assert exc.value.http_status == 400
