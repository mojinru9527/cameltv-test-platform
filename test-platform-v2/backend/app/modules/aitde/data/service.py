"""AITDE V3.2 DataSource service (V32-001).

Creates / lists / reads typed data sources with a conservative write policy:

* A data source targeting a **production environment** may only be created
  ``READONLY`` — a ``READWRITE`` data source against production is rejected.
* The secret value is never stored or serialized; only ``secret_ref`` (the
  reference) is persisted and returned.
* ``PROD_TEMPLATE`` is a reserved enum only in V3.2 and is rejected on create.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.environment import Environment
from app.modules.aitde.common.enums import (
    DataPlanStepType,
    DataPlanStrategy,
    DataPlanStatus,
    DataRequirementCleanupPolicy,
    DataRequirementSharingPolicy,
    DataSourceAccessMode,
    DataSourceStatus,
    DataSourceType,
)
from app.modules.aitde.data import repository
from app.modules.aitde.data.models import DataPlan, DataRequirement, DataSource
from app.modules.aitde.data.schemas import (
    DataPlanGenerateRequest,
    DataRequirementUpdate,
    DataSourceCreate,
)
from app.modules.aitde.drivers.database import get_driver
from app.modules.aitde.drivers.database.base import DatabaseDriverUnavailable, ping_driver
from app.modules.aitde.scenario.models import TestScenarioVersion

_SOURCE_TYPES = {st.value for st in DataSourceType}
# Reserved-only in V3.2 (deferred to V3.6); never created this version.
_RESERVED_TYPES = {DataSourceType.PROD_TEMPLATE.value}

# Config keys that must never carry a secret: secrets are referenced through
# secret_ref into an external store. Exact (case-insensitive) key match only,
# so a header named e.g. "X-Token" is not falsely rejected.
_SECRET_CONFIG_KEYS = {
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
    "authorization",
    "client_secret",
}


def _find_secret_key(obj: Any) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in _SECRET_CONFIG_KEYS:
                return str(k)
            found = _find_secret_key(v)
            if found:
                return found
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found = _find_secret_key(item)
            if found:
                return found
    return None


def _redact_config(config_json: str) -> str:
    """Defense-in-depth read redaction of any sensitive config key values."""
    try:
        config = json.loads(config_json or "{}")
    except (ValueError, TypeError):
        return config_json or "{}"

    def _redact(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: ("<REDACTED>" if str(k).lower() in _SECRET_CONFIG_KEYS else _redact(v))
                for k, v in node.items()
            }
        if isinstance(node, (list, tuple)):
            return [_redact(v) for v in node]
        return node

    return json.dumps(_redact(config), ensure_ascii=False)


def _is_prod_environment(db: Session, environment_id: int | None) -> bool:
    if environment_id is None:
        return False
    env = db.get(Environment, environment_id)
    if env is None:
        return False
    return env.env_type == "prod" or env.is_production


def create_data_source(
    db: Session, payload: DataSourceCreate, project_id: int, user_id: int
) -> DataSource:
    stype = payload.source_type.value
    if stype not in _SOURCE_TYPES:
        raise APIException(code=400, msg=f"不支持的数据源类型：{stype}", http_status=400)
    if stype in _RESERVED_TYPES:
        raise APIException(
            code=400, msg=f"数据源类型 {stype} 暂不开放（预留模板）", http_status=400
        )

    access_mode = payload.access_mode.value
    if payload.environment_id is not None and _is_prod_environment(
        db, payload.environment_id
    ):
        if access_mode == DataSourceAccessMode.READWRITE.value:
            raise APIException(
                code=400,
                msg="生产环境数据源仅允许只读（READONLY），禁止 READWRITE 创建",
                http_status=400,
            )

    # Secrets must never be embedded in config_json; only secret_ref is stored.
    config = payload.config or {}
    offending = _find_secret_key(config)
    if offending:
        raise APIException(
            code=400,
            msg=f"config 中禁止包含敏感字段：{offending}，请改用 secret_ref 引用密钥",
            http_status=400,
        )

    data: dict[str, Any] = {
        "environment_id": payload.environment_id,
        "source_type": stype,
        "name": payload.name,
        "network_zone": payload.network_zone,
        "secret_ref": payload.secret_ref,
        "access_mode": access_mode,
        "config_json": json.dumps(config, ensure_ascii=False),
        "policy_ref": payload.policy_ref,
        "status": DataSourceStatus.ACTIVE.value,
    }
    row = repository.create_data_source(db, data, project_id, user_id)
    db.commit()
    db.refresh(row)
    return row


def get_data_source(db: Session, data_source_id: int, project_id: int) -> DataSource:
    row = repository.get_data_source(db, data_source_id, project_id)
    if not row:
        raise APIException(code=404, msg="数据源不存在", http_status=404)
    return row


def list_data_sources(db: Session, project_id: int) -> list[DataSource]:
    return repository.list_data_sources(db, project_id)


def test_data_source_connection(
    db: Session, data_source_id: int, project_id: int
) -> dict[str, Any]:
    """Best-effort connection test; never leaks the secret value.

    DB / STATIC sources ping via the typed driver; unsupported types report a
    category instead of a raw error. Credentials never enter the result.
    """
    row = get_data_source(db, data_source_id, project_id)
    try:
        config = json.loads(row.config_json or "{}")
        driver = get_driver(row.source_type, config, row.secret_ref)
        result = ping_driver(driver)
    except DatabaseDriverUnavailable:
        result = {
            "ok": False,
            "latency_ms": 0,
            "detail": f"unsupported:{row.source_type}",
            "secret_leaked": False,
        }
    # Defense-in-depth: strip any echoed secret reference from the detail.
    if row.secret_ref and row.secret_ref in str(result.get("detail", "")):
        result["detail"] = "<REDACTED>"
    result["data_source_id"] = row.id
    result["source_type"] = row.source_type
    result["access_mode"] = row.access_mode
    return result


def to_dict(row: DataSource) -> dict[str, Any]:
    """Serialize a DataSource without ever exposing the referenced secret value.

    Only ``secret_ref`` (the reference) is carried; the secret it points at is
    never read into this dict.
    """
    return {
        "id": row.id,
        "project_id": row.project_id,
        "environment_id": row.environment_id,
        "source_type": row.source_type,
        "name": row.name,
        "network_zone": row.network_zone,
        "secret_ref": row.secret_ref,
        "access_mode": row.access_mode,
        "config_json": _redact_config(row.config_json),
        "policy_ref": row.policy_ref,
        "status": row.status,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# ────────────────────────────────────────────────────────────────────────────
# DataRequirement (V32-002) — business data needs, never SQL.
# ────────────────────────────────────────────────────────────────────────────


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts to dotted keys: {"a": {"b": 1}} -> {"a.b": 1}."""
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
    return out


def _derive_candidates(db: Session, scenario_version_id: int) -> list[dict[str, Any]]:
    version = db.get(TestScenarioVersion, scenario_version_id)
    if version is None:
        raise APIException(code=404, msg="ScenarioVersion 不存在", http_status=404)

    given = json.loads(version.given_model_json or "{}")
    expected = json.loads(version.expected_state_json or "{}")
    merged: dict[str, Any] = {**_flatten(given), **_flatten(expected)}

    by_entity: dict[str, dict[str, Any]] = {}
    for dotted, value in merged.items():
        entity, sep, field = dotted.partition(".")
        if not sep:
            continue
        by_entity.setdefault(entity, {})[field] = value

    candidates: list[dict[str, Any]] = []
    for entity, constraints in sorted(by_entity.items()):
        candidates.append(
            {
                "requirement_key": f"data-{entity}",
                "entity_type": entity,
                "constraints_json": json.dumps(constraints, ensure_ascii=False),
                "required": True,
                "sharing_policy": DataRequirementSharingPolicy.EXCLUSIVE.value,
                "cleanup_policy": DataRequirementCleanupPolicy.ALWAYS.value,
                "source_refs_json": json.dumps(
                    [{"scenario_version_id": scenario_version_id}], ensure_ascii=False
                ),
            }
        )
    return candidates


def derive_data_requirements(
    db: Session, scenario_version_id: int
) -> list[DataRequirement]:
    """Derive candidate data requirements from the scenario's Given/Expected.

    Rule-based (deterministic) in V32-002; never emits SQL. Re-derivation is
    idempotent: existing keys are skipped.
    """
    candidates = _derive_candidates(db, scenario_version_id)
    existing_keys = {
        r.requirement_key
        for r in repository.list_requirements_by_scenario_version(
            db, scenario_version_id
        )
    }
    for cand in candidates:
        if cand["requirement_key"] in existing_keys:
            continue
        repository.create_data_requirement(db, scenario_version_id, cand)
    db.commit()
    return repository.list_requirements_by_scenario_version(db, scenario_version_id)


def list_data_requirements(
    db: Session, scenario_version_id: int
) -> list[DataRequirement]:
    return repository.list_requirements_by_scenario_version(db, scenario_version_id)


def update_data_requirement(
    db: Session, requirement_id: int, payload: DataRequirementUpdate
) -> DataRequirement:
    row = repository.get_data_requirement(db, requirement_id)
    if not row:
        raise APIException(code=404, msg="数据需求不存在", http_status=404)
    if payload.entity_type is not None:
        row.entity_type = payload.entity_type
    if payload.constraints is not None:
        row.constraints_json = json.dumps(payload.constraints, ensure_ascii=False)
    if payload.required is not None:
        row.required = payload.required
    if payload.sharing_policy is not None:
        row.sharing_policy = payload.sharing_policy.value
    if payload.cleanup_policy is not None:
        row.cleanup_policy = payload.cleanup_policy.value
    db.commit()
    db.refresh(row)
    return row


def to_requirement_dict(row: DataRequirement) -> dict[str, Any]:
    return {
        "id": row.id,
        "scenario_version_id": row.scenario_version_id,
        "requirement_key": row.requirement_key,
        "entity_type": row.entity_type,
        "constraints_json": row.constraints_json,
        "required": row.required,
        "sharing_policy": row.sharing_policy,
        "cleanup_policy": row.cleanup_policy,
        "source_refs_json": row.source_refs_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ────────────────────────────────────────────────────────────────────────────
# DataPlan / Step (V32-003) — planner + policy, never executes.
# ────────────────────────────────────────────────────────────────────────────


def _canonical_hash(*parts: Any) -> str:
    canonical = json.dumps(parts, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _policy_check(db: Session, strategy: str, environment_id: int | None) -> None:
    """Policy check: V3.2 never writes to production; write strategies need a
    non-production environment. No free SQL / schema allowlist bypass here."""
    write_strategies = {
        DataPlanStrategy.DB_FIXTURE.value,
        DataPlanStrategy.WORKFLOW.value,
    }
    if strategy in write_strategies and _is_prod_environment(db, environment_id):
        raise APIException(
            code=400,
            msg="生产环境禁止写入型数据策略（DB_FIXTURE/WORKFLOW）",
            http_status=400,
        )


def _choose_strategy(
    db: Session,
    project_id: int,
    environment_id: int | None,
    requested: DataPlanStrategy | None,
) -> str:
    if requested is not None:
        return requested.value
    ds = repository.list_data_sources(db, project_id)
    if environment_id is not None:
        ds = [
            d
            for d in ds
            if d.environment_id == environment_id or d.environment_id is None
        ]
    readonly_db = [
        d
        for d in ds
        if d.access_mode == DataSourceAccessMode.READONLY.value
        and d.source_type in ("MYSQL", "POSTGRES", "API")
    ]
    readwrite_db = [
        d
        for d in ds
        if d.access_mode == DataSourceAccessMode.READWRITE.value
        and d.source_type in ("MYSQL", "POSTGRES")
    ]
    if readonly_db:
        return DataPlanStrategy.EXISTING.value
    if readwrite_db:
        return DataPlanStrategy.DB_FIXTURE.value
    return DataPlanStrategy.API_BUILDER.value


def _risk_for_strategy(strategy: str) -> str:
    if strategy == DataPlanStrategy.WORKFLOW.value:
        return "P0"
    if strategy == DataPlanStrategy.DB_FIXTURE.value:
        return "P1"
    return "P2"


def _steps_for(requirement: DataRequirement, strategy: str, seq: int) -> dict[str, Any]:
    is_existing = strategy == DataPlanStrategy.EXISTING.value
    step_type = (
        DataPlanStepType.FIND.value if is_existing else DataPlanStepType.CREATE.value
    )
    command = {
        "requirement_key": requirement.requirement_key,
        "entity": requirement.entity_type,
        "constraints": json.loads(requirement.constraints_json or "{}"),
    }
    compensation = None
    if step_type == DataPlanStepType.CREATE.value:
        compensation = {"action": "delete_entity", "entity": requirement.entity_type}
    return {
        "sequence": seq,
        "step_type": step_type,
        "driver": strategy.lower(),
        "command_json": json.dumps(command, ensure_ascii=False),
        "compensation_json": (
            json.dumps(compensation, ensure_ascii=False) if compensation else None
        ),
        "status": "PENDING",
    }


def generate_data_plan(
    db: Session,
    scenario_version_id: int,
    environment_id: int | None,
    project_id: int,
    payload: DataPlanGenerateRequest,
) -> DataPlan:
    requirements = repository.list_requirements_by_scenario_version(
        db, scenario_version_id
    )
    if not requirements:
        requirements = derive_data_requirements(db, scenario_version_id)
    if not requirements:
        raise APIException(
            code=400, msg="该场景无数据需求，无法生成数据计划", http_status=400
        )

    strategy = _choose_strategy(db, project_id, environment_id, payload.strategy)
    _policy_check(db, strategy, environment_id)

    steps = [_steps_for(r, strategy, i + 1) for i, r in enumerate(requirements)]
    plan_hash = _canonical_hash(
        scenario_version_id,
        strategy,
        [r.requirement_key for r in requirements],
        steps,
    )
    plan = repository.create_data_plan(
        db,
        {
            "scenario_version_id": scenario_version_id,
            "environment_id": environment_id,
            "status": DataPlanStatus.DRAFT.value,
            "strategy": strategy,
            "plan_hash": plan_hash,
            "risk_level": _risk_for_strategy(strategy),
            "created_by_type": "USER",
        },
    )
    for step in steps:
        repository.create_data_plan_step(db, {"data_plan_id": plan.id, **step})
    db.commit()
    return plan


def get_data_plan(db: Session, plan_id: int) -> DataPlan:
    plan = repository.get_data_plan(db, plan_id)
    if not plan:
        raise APIException(code=404, msg="数据计划不存在", http_status=404)
    return plan


def approve_data_plan(db: Session, plan_id: int, user_id: int) -> DataPlan:
    plan = repository.get_data_plan(db, plan_id)
    if not plan:
        raise APIException(code=404, msg="数据计划不存在", http_status=404)
    plan.status = DataPlanStatus.APPROVED.value
    plan.approved_by = user_id
    plan.approved_at = datetime.now()
    db.commit()
    db.refresh(plan)
    return plan


def to_plan_dict(db: Session, plan: DataPlan) -> dict[str, Any]:
    steps = repository.list_steps_by_plan(db, plan.id)
    return {
        "id": plan.id,
        "scenario_version_id": plan.scenario_version_id,
        "environment_id": plan.environment_id,
        "status": plan.status,
        "strategy": plan.strategy,
        "plan_hash": plan.plan_hash,
        "risk_level": plan.risk_level,
        "created_by_type": plan.created_by_type,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "approved_by": plan.approved_by,
        "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
        "steps": [
            {
                "id": s.id,
                "data_plan_id": s.data_plan_id,
                "sequence": s.sequence,
                "step_type": s.step_type,
                "driver": s.driver,
                "command_json": s.command_json,
                "compensation_json": s.compensation_json,
                "status": s.status,
            }
            for s in steps
        ],
    }
