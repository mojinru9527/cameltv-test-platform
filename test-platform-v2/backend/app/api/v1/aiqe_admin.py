"""AIQE Console 管理 API（P1）：质量门禁、噪音规则、Profile、Artifact GC。

batch-336：Console 统一门禁 `menu:aiqe_runs`（菜单权限点 = 执行中心入口权限）。
- 无该权限 → 403（不再依赖 defect:list 才能读管理页）；
- 写操作继续叠加 `defect:update`，避免只读角色凭菜单权限获得写能力。
"""
from __future__ import annotations

from datetime import datetime

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.aiqe.security.target_policy import (
    TargetPolicyConfigError,
    list_target_policies,
    upsert_target_policy,
)
from app.aiqe.services.artifact_gc import purge_expired_artifacts
from app.aiqe.services.query_registry import (
    RegisteredQueryError,
    approve_registered_query,
    list_registered_queries,
    register_query,
)
from app.aiqe.services.noise_rule_service import (
    approve_rule,
    get_rule,
    NoiseRuleError,
    create_rule,
    delete_rule,
    is_effective,
    list_rules,
    renew_rule,
    update_rule,
)
from app.aiqe.services.profile_service import (
    ProfileError,
    approve_profile,
    create_profile,
    list_profiles,
    update_config,
)
from app.aiqe.services.quality_gate_service import (
    GateError,
    GateNotFound,
    evaluate_from_facts,
    latest_snapshot,
    snapshot_dict,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/admin", tags=["AIQE 管理"])

# 执行中心菜单权限点：Console 页面与 API 的唯一入口门禁（batch-336）
_console_access = require_permission("menu:aiqe_runs")


class QualityGateIn(BaseModel):
    """v1.4：只接受事实定位参数，不接受前端 p0_total/p0_passed。"""

    version_task_id: int | None = None
    run_ids: list[str] = []
    build_ref: str = ""
    environment_ref: str = ""


class NoiseRuleIn(BaseModel):
    pattern: str
    action: str = "suppress"
    scope: str = "run"
    expires_at: datetime | None = None
    # AUD-019 治理字段
    reason: str = ""
    environment_id: int | None = None
    profile_id: str | None = None
    detector_key: str | None = None
    error_class: str | None = None
    selector: dict | None = None
    app_version: str | None = None
    evidence_refs: list[str] | None = None
    require_approval: bool = True


class NoiseRulePatchIn(BaseModel):
    pattern: str | None = None
    action: str | None = None
    expires_at: datetime | None = None


def _noise_rule_out(row) -> dict:
    return {
        "id": row.id,
        "pattern": row.pattern,
        "action": row.action,
        "scope": row.scope,
        "expires_at": row.expires_at,
        "status": row.status,
        "effective": is_effective(row),
        "detector_key": row.detector_key,
        "error_class": row.error_class,
        "environment_id": row.environment_id,
        "profile_id": row.profile_id,
        "selector": row.selector_json,
        "app_version": row.app_version,
        "evidence_refs": row.evidence_refs_json or [],
        "reason": row.reason,
        "version": row.version,
        "approved_by": row.approved_by,
        "valid_from": row.valid_from,
        "matched_count": row.matched_count,
        "false_suppress_count": row.false_suppress_count,
    }


class ProfileIn(BaseModel):
    name: str
    purpose: str = "core_isolated"
    config: dict = {}


class ProfileConfigIn(BaseModel):
    config: dict


def _profile_out(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "purpose": row.purpose,
        "version": row.version,
        "approval_status": row.approval_status,
        "checksum": row.checksum,
        "owner_id": row.owner_id,
        "frozen": row.approval_status == "approved",
    }


@router.post("/quality-gate", response_model=R[dict], summary="质量门禁判定（服务端事实计算）")
def quality_gate(
    body: QualityGateIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    try:
        snapshot = evaluate_from_facts(
            db,
            project_id=current.project_id or 0,
            run_ids=list(body.run_ids),
            version_task_id=body.version_task_id,
            build_ref=body.build_ref,
            environment_ref=body.environment_ref,
            computed_by=current.user.id,
        )
        db.commit()
    except GateNotFound as exc:
        db.rollback()
        raise APIException(code=404, msg=str(exc), http_status=404) from None
    except GateError as exc:
        db.rollback()
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return R.ok(snapshot_dict(snapshot))


@router.get("/quality-gate/latest", response_model=R[dict], summary="最近一次门禁快照")
def quality_gate_latest(
    version_task_id: int | None = Query(default=None),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    row = latest_snapshot(
        db, project_id=current.project_id or 0, version_task_id=version_task_id
    )
    return R.ok(snapshot_dict(row) if row else None)


@router.get("/noise-rules", response_model=R[list], summary="噪音规则列表")
def get_noise_rules(
    include_expired: bool = Query(default=True),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_rules(db, current.project_id or 0, include_expired=include_expired)
    return R.ok([_noise_rule_out(row) for row in rows])


@router.post("/noise-rules", response_model=R[dict], summary="创建噪音规则")
def post_noise_rule(
    body: NoiseRuleIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = create_rule(
            db,
            project_id=current.project_id or 0,
            pattern=body.pattern,
            action=body.action,
            scope=body.scope,
            expires_at=body.expires_at,
            created_by=current.user.id,
            environment_id=body.environment_id,
            profile_id=body.profile_id,
            detector_key=body.detector_key,
            error_class=body.error_class,
            selector=body.selector,
            app_version=body.app_version,
            evidence_refs=body.evidence_refs,
            reason=body.reason,
            require_approval=body.require_approval,
        )
    except NoiseRuleError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return R.ok(_noise_rule_out(row))


@router.patch("/noise-rules/{rule_id}", response_model=R[dict], summary="更新噪音规则")
def patch_noise_rule(
    rule_id: int,
    body: NoiseRulePatchIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = get_rule(db, rule_id, project_id=current.project_id or 0)
        row = update_rule(
            db,
            rule_id,
            pattern=body.pattern,
            action=body.action,
            expires_at=body.expires_at,
            project_id=current.project_id or 0,
        )
    except NoiseRuleError as exc:
        message = str(exc)
        status = 404 if "不存在" in message else 400
        raise APIException(code=status, msg=message, http_status=status) from None
    return R.ok(_noise_rule_out(row))


@router.post(
    "/noise-rules/{rule_id}/approve", response_model=R[dict], summary="人工批准噪音规则（AUD-019）"
)
def post_approve_rule(
    rule_id: int,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = approve_rule(
            db, rule_id, project_id=current.project_id or 0, approved_by=current.user.id
        )
    except NoiseRuleError as exc:
        message = str(exc)
        status = 404 if "不存在" in message else 400
        raise APIException(code=status, msg=message, http_status=status) from None
    return R.ok(_noise_rule_out(row))


@router.post("/noise-rules/{rule_id}/renew", response_model=R[dict], summary="续期噪音规则")
def post_renew_rule(
    rule_id: int,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = renew_rule(db, rule_id, project_id=current.project_id or 0)
    except NoiseRuleError as exc:
        raise APIException(code=404, msg=str(exc), http_status=404) from None
    return R.ok(_noise_rule_out(row))


@router.delete("/noise-rules/{rule_id}", response_model=R[dict], summary="删除噪音规则")
def remove_noise_rule(
    rule_id: int,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        delete_rule(db, rule_id, project_id=current.project_id or 0)
    except NoiseRuleError as exc:
        raise APIException(code=404, msg=str(exc), http_status=404) from None
    return R.ok({"id": rule_id, "deleted": True})


@router.post("/artifacts/gc", response_model=R[dict], summary="Artifact 留存清理")
def run_artifact_gc(
    retention_days: int = Query(default=30, ge=1),
    _console: CurrentUser = Depends(_console_access),
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    return R.ok(purge_expired_artifacts(db, retention_days=retention_days))


@router.get("/profiles", response_model=R[list], summary="Execution Profile 列表")
def get_profiles(
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_profiles(db, current.project_id or 0)
    return R.ok([_profile_out(row) for row in rows])


@router.post("/profiles", response_model=R[dict], summary="创建 Execution Profile")
def post_profile(
    body: ProfileIn,
    _console: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = create_profile(
            db,
            project_id=current.project_id or 0,
            name=body.name,
            purpose=body.purpose,
            config=body.config,
            owner_id=current.user.id,
        )
    except ProfileError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return R.ok(_profile_out(row))


@router.post("/profiles/{profile_id}/approve", response_model=R[dict], summary="审批 Execution Profile（approved 冻结）")
def post_approve_profile(
    profile_id: str,
    _console: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = approve_profile(db, profile_id)
    except ProfileError as exc:
        raise APIException(code=404, msg=str(exc), http_status=404) from None
    return R.ok(_profile_out(row))


@router.patch("/profiles/{profile_id}", response_model=R[dict], summary="更新 Execution Profile 配置")
def patch_profile(
    profile_id: str,
    body: ProfileConfigIn,
    _console: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = update_config(db, profile_id, body.config)
    except ProfileError as exc:
        message = str(exc)
        status = 409 if "approved" in message else 404
        raise APIException(code=status, msg=message, http_status=status) from None
    return R.ok(_profile_out(row))

# ── V16-004 / V16-001：Query Registry 与 Target Policy 管理 API ──────────


class QueryRegisterIn(BaseModel):
    query_key: str
    statement: str
    allowed_params: list[str]
    connection_ref: str = ""
    environment_id: int | None = None
    allowed_tables: list[str] = []
    allowed_columns: list[str] = []
    max_rows: int = 100
    max_execution_ms: int = 2000
    result_schema: dict | None = None
    approval_status: str = "pending"


class TargetPolicyIn(BaseModel):
    policy: dict
    environment_id: int | None = None
    name: str = "default"
    base_version: int | None = None


def _query_out(row: Any) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "environment_id": row.environment_id,
        "query_key": row.query_key,
        "version": row.version,
        "statement_hash": row.statement_hash,
        "allowed_params": list(row.allowed_params or []),
        "allowed_tables": list(row.allowed_tables or []),
        "allowed_columns": list(row.allowed_columns or []),
        "max_rows": row.max_rows,
        "max_execution_ms": row.max_execution_ms,
        "connection_ref": row.connection_ref,
        "approval_status": row.approval_status,
        "active": bool(row.active),
        "approved_by": row.approved_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _policy_out(row: Any) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "environment_id": row.environment_id,
        "name": row.name,
        "version": row.version,
        "active": bool(row.active),
        "policy": dict(row.policy_json or {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/query-registry", response_model=R[list], summary="登记查询列表（项目隔离）")
def list_query_registry(
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_registered_queries(db, project_id=int(current.project_id or 0))
    return R.ok([_query_out(row) for row in rows])


@router.post("/query-registry", response_model=R[dict], summary="登记只读查询（需审批后执行）")
def create_query_registry(
    body: QueryRegisterIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    project_id = int(current.project_id or 0)
    try:
        row = register_query(
            db,
            project_id=project_id,
            query_key=body.query_key,
            statement=body.statement,
            allowed_params=body.allowed_params,
            connection_ref=body.connection_ref,
            environment_id=body.environment_id,
            allowed_tables=body.allowed_tables,
            allowed_columns=body.allowed_columns,
            max_rows=body.max_rows,
            max_execution_ms=body.max_execution_ms,
            result_schema=body.result_schema,
            approval_status=body.approval_status,
            created_by=current.user.id,
        )
    except RegisteredQueryError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    return R.ok(_query_out(row))


@router.post(
    "/query-registry/{query_id}/approve",
    response_model=R[dict],
    summary="审批登记查询（approved 才可执行）",
)
def approve_query_registry(
    query_id: str,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    row = approve_registered_query(
        db,
        project_id=int(current.project_id or 0),
        query_id=str(query_id),
        approved_by=current.user.id,
    )
    if row is None:
        raise APIException(code=404, msg="登记查询不存在", http_status=404)
    db.commit()
    return R.ok(_query_out(row))


@router.get("/target-policies", response_model=R[list], summary="目标策略列表（含历史版本）")
def list_target_policies_route(
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_target_policies(db, project_id=int(current.project_id or 0))
    return R.ok([_policy_out(row) for row in rows])


@router.post("/target-policies", response_model=R[dict], summary="写入新版本目标策略（管理员）")
def create_target_policy(
    body: TargetPolicyIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    project_id = int(current.project_id or 0)
    try:
        row = upsert_target_policy(
            db,
            project_id=project_id,
            environment_id=body.environment_id,
            policy=body.policy,
            name=body.name,
            created_by=current.user.id,
            base_version=body.base_version,
        )
    except TargetPolicyConfigError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    return R.ok(_policy_out(row))
