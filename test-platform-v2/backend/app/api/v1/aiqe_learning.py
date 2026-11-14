"""batch-349（M10-4）：学习候选 / BugPattern Console API。

状态机：draft → benchmarked（evaluate）→ approved（approve）→ active（activate）。
批准需要独立权限 `aiqe:learning:approve`；误报率 >20% 由服务层拒绝（fail-closed）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services.learning_service import (
    LearningError,
    activate_candidate,
    approve_candidate,
    create_candidate,
    evaluate_candidate,
    get_candidate,
    list_bug_patterns,
    list_candidates,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/learning", tags=["AIQE Learning"])

_console_access = require_permission("menu:aiqe_runs")


class CandidateIn(BaseModel):
    pattern: str = Field(min_length=1, max_length=200)
    description: str = ""
    source: str = "bug"
    duplicate_of: str | None = None


class EvaluateIn(BaseModel):
    false_positive_rate: float = Field(ge=0, le=1)
    sample_size: int = Field(gt=0)


def _candidate_out(row) -> dict:
    return {
        "id": row.id,
        "rule": row.rule_json,
        "source": row.source,
        "status": row.status,
        "benchmark": row.benchmark_json,
        "duplicate_of": row.duplicate_of,
        "acknowledged": row.acknowledged,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/candidates", response_model=R[list], summary="学习候选列表")
def get_candidates(
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_candidates(db, current.project_id or 0)
    return R.ok([_candidate_out(row) for row in rows])


@router.post("/candidates", response_model=R[dict], summary="创建学习候选")
def post_candidate(
    body: CandidateIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = create_candidate(
            db,
            project_id=current.project_id or 0,
            rule={"pattern": body.pattern, "description": body.description},
            source=body.source,
            duplicate_of=body.duplicate_of,
        )
    except LearningError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return R.ok(_candidate_out(row))


@router.post("/candidates/{candidate_id}/evaluate", response_model=R[dict], summary="候选基准评估")
def post_evaluate(
    candidate_id: str,
    body: EvaluateIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = evaluate_candidate(
            db,
            candidate_id,
            {
                "false_positive_rate": body.false_positive_rate,
                "sample_size": body.sample_size,
            },
            project_id=current.project_id or 0,
        )
    except LearningError as exc:
        status = 404 if "不存在" in str(exc) else 400
        raise APIException(code=status, msg=str(exc), http_status=status) from None
    return R.ok(_candidate_out(row))


@router.post(
    "/candidates/{candidate_id}/approve",
    response_model=R[dict],
    summary="批准学习候选（需 aiqe:learning:approve）",
)
def post_approve(
    candidate_id: str,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("aiqe:learning:approve")),
    db: Session = Depends(get_db),
):
    try:
        row = approve_candidate(
            db, candidate_id, project_id=current.project_id or 0
        )
    except LearningError as exc:
        status = 404 if "不存在" in str(exc) else 400
        raise APIException(code=status, msg=str(exc), http_status=status) from None
    return R.ok(_candidate_out(row))


@router.post("/candidates/{candidate_id}/activate", response_model=R[dict], summary="激活候选为 BugPattern")
def post_activate(
    candidate_id: str,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("aiqe:learning:approve")),
    db: Session = Depends(get_db),
):
    try:
        row = get_candidate(db, candidate_id, project_id=current.project_id or 0)
        pattern = activate_candidate(
            db, candidate_id, project_id=current.project_id or 0
        )
    except LearningError as exc:
        status = 404 if "不存在" in str(exc) else 400
        raise APIException(code=status, msg=str(exc), http_status=status) from None
    return R.ok(
        {
            "candidate": _candidate_out(row),
            "pattern": (
                {
                    "pattern_key": pattern.pattern_key,
                    "description": pattern.description,
                    "status": pattern.status,
                }
                if pattern is not None
                else None
            ),
        }
    )


@router.get("/bug-patterns", response_model=R[list], summary="已激活 BugPattern 列表")
def get_bug_patterns(
    status: str | None = Query(default="active", max_length=16),
    limit: int = Query(default=100, ge=1, le=500),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_bug_patterns(db, status=status, limit=limit)
    return R.ok(
        [
            {
                "pattern_key": row.pattern_key,
                "description": row.description,
                "status": row.status,
                "source_candidate_id": row.source_candidate_id,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    )
