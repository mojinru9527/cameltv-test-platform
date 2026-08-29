"""AITDE V3.3 CommandPlanService (V33-002).

Owns CommandPlan + CommandPlanVersion lifecycle: create, version, validate,
approve (→ VALIDATED), activate (→ ACTIVE, staleness the others), and an
immutability guard on ACTIVE versions. ``plan_hash`` is stable for identical IR.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.command import DEFAULT_REGISTRY
from app.modules.aitde.command.models import CommandPlan, CommandPlanVersion
from app.modules.aitde.common.enums import CommandPlanStatus


def _utcnow() -> datetime:
    return datetime.now()


def _canonical_hash(plan_json: dict[str, Any]) -> str:
    canonical = json.dumps(plan_json, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_or_create_plan(db: Session, scenario_adapter_id: int) -> CommandPlan:
    plan = db.scalar(
        select(CommandPlan).where(CommandPlan.scenario_adapter_id == scenario_adapter_id)
    )
    if plan is None:
        plan = CommandPlan(scenario_adapter_id=scenario_adapter_id, current_version_no=1)
        db.add(plan)
        db.flush()
    return plan


def list_versions(db: Session, command_plan_id: int) -> list[CommandPlanVersion]:
    rows = db.scalars(
        select(CommandPlanVersion)
        .where(CommandPlanVersion.command_plan_id == command_plan_id)
        .order_by(CommandPlanVersion.version_no.desc())
    ).all()
    return list(rows)


def create_version(
    db: Session,
    plan: CommandPlan,
    *,
    scenario_version_id: int,
    contract_version_id: int,
    plan_json: dict[str, Any],
    schema_version: str = "1.0",
    generated_by_type: str = "AI",
    model_ref: str | None = None,
    prompt_version: str | None = None,
) -> CommandPlanVersion:
    """Validate the Command IR against the schema registry, then version it."""
    errors = DEFAULT_REGISTRY.validate(plan_json)
    if errors:
        raise APIException(code=400, msg=f"Command IR 校验失败：{errors}", http_status=400)

    max_no = db.scalar(
        select(func.max(CommandPlanVersion.version_no)).where(
            CommandPlanVersion.command_plan_id == plan.id
        )
    ) or 0
    version_no = int(max_no) + 1

    version = CommandPlanVersion(
        command_plan_id=plan.id,
        version_no=version_no,
        scenario_version_id=scenario_version_id,
        contract_version_id=contract_version_id,
        schema_version=schema_version,
        plan_json=json.dumps(plan_json, ensure_ascii=False),
        plan_hash=_canonical_hash(plan_json),
        status=CommandPlanStatus.DRAFT.value,
        generated_by_type=generated_by_type,
        model_ref=model_ref,
        prompt_version=prompt_version,
    )
    db.add(version)
    db.flush()
    return version


def get_version(db: Session, version_id: int) -> CommandPlanVersion:
    v = db.get(CommandPlanVersion, version_id)
    if not v:
        raise APIException(code=404, msg="CommandPlan 版本不存在", http_status=404)
    return v


def approve_version(db: Session, version_id: int, user_id: int) -> CommandPlanVersion:
    """Approve a DRAFT version → VALIDATED (ready to activate)."""
    v = get_version(db, version_id)
    if v.status != CommandPlanStatus.DRAFT.value:
        raise APIException(code=400, msg=f"仅 DRAFT 版本可批准：{v.status}", http_status=400)
    v.status = CommandPlanStatus.VALIDATED.value
    v.approved_by = user_id
    v.approved_at = _utcnow()
    db.commit()
    db.refresh(v)
    return v


def activate_version(db: Session, version_id: int, user_id: int) -> CommandPlanVersion:
    """Activate a VALIDATED version → ACTIVE; mark all other versions STALE.

    The ACTIVE version is immutable thereafter.
    """
    v = get_version(db, version_id)
    if v.status != CommandPlanStatus.VALIDATED.value:
        raise APIException(
            code=400, msg=f"仅 VALIDATED 版本可激活：{v.status}", http_status=400
        )
    siblings = list_versions(db, v.command_plan_id)
    for other in siblings:
        if other.id != v.id and other.status == CommandPlanStatus.ACTIVE.value:
            other.status = CommandPlanStatus.STALE.value
    v.status = CommandPlanStatus.ACTIVE.value
    plan = db.get(CommandPlan, v.command_plan_id)
    if plan:
        plan.current_version_no = v.version_no
    db.commit()
    db.refresh(v)
    return v


def ensure_active_immutable(v: CommandPlanVersion) -> None:
    """An ACTIVE CommandPlanVersion must never be mutated."""
    if v.status == CommandPlanStatus.ACTIVE.value:
        raise APIException(code=400, msg="ACTIVE CommandPlan 不可变", http_status=400)


def to_version_dict(v: CommandPlanVersion) -> dict[str, Any]:
    return {
        "id": v.id,
        "command_plan_id": v.command_plan_id,
        "version_no": v.version_no,
        "scenario_version_id": v.scenario_version_id,
        "contract_version_id": v.contract_version_id,
        "schema_version": v.schema_version,
        "plan_json": json.loads(v.plan_json or "{}"),
        "plan_hash": v.plan_hash,
        "status": v.status,
        "generated_by_type": v.generated_by_type,
        "model_ref": v.model_ref,
        "prompt_version": v.prompt_version,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "approved_by": v.approved_by,
        "approved_at": v.approved_at.isoformat() if v.approved_at else None,
    }
