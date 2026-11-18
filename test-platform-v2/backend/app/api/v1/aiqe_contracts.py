"""AUD-014/015/017/018/019/020/013：v1.5 §06 目标契约的 REST 面。

所有路由都复用已交付的 service（不新增业务逻辑），并遵守统一的：
project scope（`current.project_id`）、RBAC（`menu:aiqe_runs` / `defect:update`）、
错误映射（400/403/404/422）、以及"前端不得自报事实"的约束。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services import (
    contract_service,
    testcase_service,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe", tags=["AIQE Capabilities"])

_console = require_permission("menu:aiqe_runs")
_edit = require_permission("defect:update")


def _bad(message: str, status: int = 400) -> APIException:
    return APIException(code=status, msg=message, http_status=status)


# ── Contracts (AUD-014) ─────────────────────────────────
class ContractIn(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=80)
    title: str = Field(default="", max_length=300)
    business_goal: str = ""
    actors: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    acceptance_criteria: list[dict[str, Any]] = Field(default_factory=list)


class TransitionIn(BaseModel):
    target: str = Field(min_length=1, max_length=24)


class ApproveAcIn(BaseModel):
    ac_id: str = Field(min_length=1, max_length=40)


@router.post("/contracts", response_model=R[dict], summary="创建 Requirement Contract Draft")
def create_contract_api(
    body: ContractIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        contract = contract_service.create_contract_draft(
            db,
            project_id=current.project_id or 0,
            requirement_id=body.requirement_id,
            title=body.title,
            business_goal=body.business_goal,
            actors=body.actors,
            source_refs=body.source_refs,
            acceptance_criteria=body.acceptance_criteria,
            created_by=getattr(current.user, "id", None),
        )
    except contract_service.InvalidSourceRef as exc:
        db.rollback()
        raise _bad(str(exc), 422) from None
    except contract_service.ContractError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_contract_out(db, contract))


@router.get("/contracts", response_model=R[dict], summary="Contract 列表（项目作用域）")
def list_contracts_api(
    requirement_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    rows = contract_service.list_contracts(
        db,
        project_id=current.project_id or 0,
        requirement_id=requirement_id,
        status=status,
        limit=limit,
    )
    return R.ok(
        {
            "items": [
                {
                    "id": row.id,
                    "requirement_id": row.requirement_id,
                    "revision": row.revision,
                    "title": row.title,
                    "status": row.status,
                    "revision_checksum": row.revision_checksum,
                    "created_at": row.created_at,
                }
                for row in rows
            ],
            "total": len(rows),
        }
    )


@router.get("/contracts/{contract_id}", response_model=R[dict], summary="Contract 详情")
def get_contract_api(
    contract_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        contract = contract_service.get_contract(db, contract_id, current.project_id or 0)
    except contract_service.ContractError as exc:
        raise _bad(str(exc), 404) from None
    return R.ok(_contract_out(db, contract))


@router.post(
    "/contracts/{contract_id}/transition", response_model=R[dict], summary="Contract 状态迁移"
)
def transition_contract_api(
    contract_id: str,
    body: TransitionIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        contract = contract_service.transition_contract(
            db,
            contract_id,
            body.target,
            project_id=current.project_id or 0,
            actor_id=getattr(current.user, "id", None),
        )
    except contract_service.ContractError as exc:
        db.rollback()
        message = str(exc)
        raise _bad(message, 404 if "不存在" in message else 400) from None
    db.commit()
    return R.ok(_contract_out(db, contract))


@router.post(
    "/contracts/{contract_id}/approve-ac", response_model=R[dict], summary="人工批准 AC"
)
def approve_ac_api(
    contract_id: str,
    body: ApproveAcIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        ac = contract_service.approve_ac(
            db,
            contract_id=contract_id,
            ac_id=body.ac_id,
            project_id=current.project_id or 0,
            approver_id=getattr(current.user, "id", 0) or 0,
        )
    except contract_service.ContractError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(
        {
            "contract_id": contract_id,
            "ac_id": ac.ac_id,
            "approval_status": ac.approval_status,
            "approved_by": ac.approved_by,
        }
    )


@router.get(
    "/contracts/{contract_id}/coverage", response_model=R[dict], summary="AC 覆盖报表（AUD-015）"
)
def contract_coverage_api(
    contract_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        report = testcase_service.coverage_report(
            db, contract_id=contract_id, project_id=current.project_id or 0
        )
    except contract_service.ContractError as exc:
        raise _bad(str(exc), 404) from None
    return R.ok(
        {
            "contract_id": contract_id,
            "coverage": report,
            "uncovered": [key for key, value in report.items() if value == "UNCOVERED"],
            "partial": [key for key, value in report.items() if value == "PARTIAL"],
        }
    )


def _contract_out(db: Session, contract) -> dict:
    acs = contract_service.list_acs(db, contract.id)
    return {
        "id": contract.id,
        "project_id": contract.project_id,
        "requirement_id": contract.requirement_id,
        "revision": contract.revision,
        "title": contract.title,
        "status": contract.status,
        "revision_checksum": contract.revision_checksum,
        "source_refs": contract.source_refs_json or [],
        "ambiguities": contract.ambiguities_json or [],
        "approved_by": contract.approved_by,
        "frozen_at": contract.frozen_at,
        "acceptance_criteria": [
            {
                "ac_id": ac.ac_id,
                "priority": ac.priority,
                "oracle_type": ac.oracle_type,
                "oracle_ref": ac.oracle_ref,
                "platforms": ac.platforms_json or [],
                "approval_status": ac.approval_status,
            }
            for ac in acs
        ],
    }


# ── Test Cases (AUD-015) ────────────────────────────────
class CaseIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    priority: str = Field(default="P2", max_length=4)
    contract_id: str | None = None
    contract_revision: int | None = None
    covers_ac_ids: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    platform_targets: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    cleanup: list[str] = Field(default_factory=list)
    oracle_type: str = ""
    oracle_ref: str = ""
    scenario_id: str = ""


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")


@router.post("/cases", response_model=R[dict], summary="创建结构化 Case Draft")
def create_case_api(
    body: CaseIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row, created = testcase_service.create_case_draft(
            db, project_id=current.project_id or 0, payload=body.model_dump()
        )
    except (testcase_service.TestCaseError, contract_service.ContractError) as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok({**_case_out(row), "created": created})


@router.get("/cases", response_model=R[dict], summary="结构化 Case 列表")
def list_cases_api(
    contract_id: str | None = None,
    review_status: str | None = None,
    priority: str | None = None,
    limit: int = 100,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    rows = testcase_service.list_cases(
        db,
        project_id=current.project_id or 0,
        contract_id=contract_id,
        review_status=review_status,
        priority=priority,
        limit=limit,
    )
    return R.ok({"items": [_case_out(row) for row in rows], "total": len(rows)})


@router.post("/cases/{case_id}/review", response_model=R[dict], summary="测试设计审核")
def review_case_api(
    case_id: str,
    body: ReviewIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = testcase_service.review_case(
            db,
            project_id=current.project_id or 0,
            case_id=case_id,
            decision=body.decision,
            reviewer_id=getattr(current.user, "id", 0) or 0,
        )
    except testcase_service.TestCaseError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_case_out(row))


def _case_out(row) -> dict:
    return {
        "case_id": row.case_id,
        "title": row.title,
        "priority": row.priority,
        "automation_grade": row.automation_grade,
        "review_status": row.review_status,
        "contract_id": row.contract_id,
        "contract_revision": row.contract_revision,
        "covers_ac_ids": row.covers_ac_ids_json or [],
        "platform_targets": row.platform_targets_json or [],
        "oracle_ref": row.oracle_ref,
    }


