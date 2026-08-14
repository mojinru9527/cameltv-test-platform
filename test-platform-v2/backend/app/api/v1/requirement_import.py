"""需求文档 API 路由 —— /api/v1/requirements/*（AI 用例评审 + 导入 + 已确认 API 匹配）

Batch 181（FIX-173-P2-10）拆分自 requirement.py，端点逻辑逐字迁移。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException, not_found
from app.schemas.common import R
from app.schemas.requirement import (
    AIGenerateResult,
    CaseImportRequest,
    CaseImportResult,
    RequirementReviewRequest,
    RequirementReviewState,
)
from app.services import audit_service, requirement_service

router = APIRouter(prefix="/requirements", tags=["需求文档-导入"])


def _audit(
    req: Request, cu: CurrentUser, db: Session,
    action: str, target: str, detail: str = "",
) -> None:
    """Write audit entry with null-safe user access (P0-5/P1-3 fix)."""
    username = ""
    if cu.user:
        username = cu.user.nickname or cu.user.username
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=username,
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


class ConfirmApiMatchRequest(BaseModel):
    service_id: int | None = None
    endpoint_ids: list[int] = Field(default_factory=list)


class ApiMatchSelection(BaseModel):
    service_id: int | None = None
    endpoint_ids: list[int] = Field(default_factory=list)


@router.get(
    "/{document_id}/match-api/selection",
    response_model=R[ApiMatchSelection],
    summary="读取已确认的 API 匹配",
)
def get_confirmed_api_matches(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    result = requirement_service.get_api_match_selection(
        db,
        doc_id=document_id,
        project_id=current.project_id or 0,
    )
    if result is None:
        raise not_found("需求文档")
    return R.ok(ApiMatchSelection(**result))


@router.post(
    "/{document_id}/match-api/confirm",
    response_model=R[ApiMatchSelection],
    summary="确认并持久化 API 匹配",
)
def confirm_api_matches(
    document_id: int,
    body: ConfirmApiMatchRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    try:
        result = requirement_service.confirm_api_match_selection(
            db,
            doc_id=document_id,
            project_id=current.project_id or 0,
            service_id=body.service_id,
            endpoint_ids=body.endpoint_ids,
            commit=False,
        )
        if result is None:
            raise not_found("需求文档")
        _audit(
            req,
            current,
            db,
            "requirement:match-api:confirm",
            f"doc#{document_id}",
            f"确认服务 {result['service_id'] or '-'}，接口 {len(result['endpoint_ids'])} 个",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return R.ok(ApiMatchSelection(**result))


# ── 导入用例 ──────────────────────────────────────────

@router.get(
    "/{document_id}/review-state",
    response_model=R[RequirementReviewState],
    summary="读取 AI 用例审查队列",
)
def get_requirement_review_state(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    result = requirement_service.get_review_state(
        db, document_id, current.project_id or 0
    )
    if result is None:
        raise not_found("需求文档或 AI 用例")
    return R.ok(RequirementReviewState(**result))


@router.post(
    "/{document_id}/review/{case_index}",
    response_model=R[dict],
    summary="审查 AI 生成用例",
)
def review_generated_case(
    document_id: int,
    case_index: int,
    body: RequirementReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    try:
        result = requirement_service.set_review_action(
            db,
            doc_id=document_id,
            project_id=current.project_id or 0,
            case_index=case_index,
            action=body.action,
            reviewer_id=current.user.id,
            edited_data=body.edited_data,
            commit=False,
        )
        if result is None:
            raise not_found("需求文档或用例")
        _audit(
            req,
            current,
            db,
            f"requirement:review:{body.action}",
            f"doc#{document_id}/case#{case_index}",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return R.ok(result)

@router.post("/{document_id}/import", response_model=R[CaseImportResult])
def import_generated_cases(
    document_id: int,
    body: CaseImportRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:import")),
    db: Session = Depends(get_db),
):
    """Import selected AI-generated cases into the test_case table."""
    try:
        selected = requirement_service.prepare_cases_for_import(
            db,
            doc_id=document_id,
            project_id=current.project_id or 0,
            indices=body.indices,
            edited_cases=[
                case.model_dump(by_alias=True, exclude_unset=True)
                for case in body.edited_cases
            ],
            reviewer_id=current.user.id,
        )
        if not selected:
            raise APIException(
                code=400,
                msg="请先生成测试用例并选择有效用例",
                http_status=400,
            )
        result = requirement_service.import_cases(
            db,
            document_id,
            selected,
            project_id=current.project_id or 0,
            commit=False,
        )
        _audit(
            req,
            current,
            db,
            "requirement:import",
            f"doc#{document_id}",
            f"导入 {result['imported']} 条用例，跳过 {result['skipped']} 条",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIException(
            code=409,
            msg="用例已导入，请刷新后重试",
            http_status=409,
        ) from exc
    except Exception:
        db.rollback()
        raise

    return R.ok(CaseImportResult(**result))


# ── 查看已生成用例 ──────────────────────────────────────

@router.get("/{document_id}/cases", response_model=R[AIGenerateResult])
def get_generated_cases(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """View previously generated test cases for a document."""
    result = requirement_service.get_requirement_cases(
        db, document_id, project_id=current.project_id or 0,
    )
    if not result:
        return R(code=404, msg="该文档尚未生成用例，请先点击 AI 生成")
    return R.ok(AIGenerateResult(**result))
