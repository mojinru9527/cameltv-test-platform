"""AUD-012：可复现缺陷草稿 API（服务端证据校验 + 复现包 + 人工确认）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services.defect_draft_service import (
    DefectDraftError,
    build_bundle,
    build_defect_draft,
    get_defect,
    promote_draft,
)
from app.aiqe.services.evidence_service import EvidenceRefError
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/defects", tags=["AIQE Defect Draft"])


class DraftIn(BaseModel):
    run_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=300)
    severity: str = Field(default="P2", max_length=10)
    description: str = Field(default="", max_length=4000)
    evidence_refs: list[str] = Field(default_factory=list)
    ac_refs: list[str] = Field(default_factory=list)
    node_run_id: str | None = Field(default=None, max_length=36)
    attempt_id: str | None = Field(default=None, max_length=36)
    no_assertion_reason: str = Field(default="", max_length=1000)
    correlation_id: str = Field(default="", max_length=128)


def _not_found(defect_id: int) -> APIException:
    return APIException(code=404, msg=f"缺陷不存在: {defect_id}", http_status=404)


def _draft_out(defect) -> dict:
    return {
        "id": defect.id,
        "project_id": defect.project_id,
        "title": defect.title,
        "severity": defect.severity,
        "is_draft": bool(defect.is_draft),
        "draft_id": defect.draft_id,
        "approved_by": defect.approved_by,
        "approved_at": defect.approved_at,
        "reproduction_status": defect.reproduction_status,
        "evidence_refs": defect.evidence_refs_json or [],
        "failing_assertion_refs": defect.failing_assertion_refs_json or [],
        "no_assertion_reason": defect.no_assertion_reason,
        "aiqe_run_id": defect.aiqe_run_id,
        "fixture_namespace": defect.fixture_namespace,
    }


def _load_defect(db: Session, defect_id: int, project_id: int):
    defect = get_defect(db, defect_id=defect_id, project_id=project_id)
    if defect is None:
        raise _not_found(defect_id)
    return defect


@router.post("/drafts", response_model=R[dict], summary="创建可复现缺陷草稿")
def create_draft_api(
    body: DraftIn,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    try:
        defect = build_defect_draft(
            db,
            project_id=current.project_id or 0,
            run_id=body.run_id,
            title=body.title,
            severity=body.severity,
            description=body.description,
            evidence_refs=body.evidence_refs,
            ac_refs=body.ac_refs,
            node_run_id=body.node_run_id,
            attempt_id=body.attempt_id,
            no_assertion_reason=body.no_assertion_reason,
            creator_id=getattr(current.user, "id", 0) or 0,
            correlation_id=body.correlation_id,
        )
    except EvidenceRefError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=exc.reason) from None
    except DefectDraftError as exc:
        db.rollback()
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    return R.ok(_draft_out(defect))


@router.get("/{defect_id}/reproduction-bundle", response_model=R[dict], summary="复现包（JSON）")
def get_bundle_api(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    defect = _load_defect(db, defect_id, current.project_id or 0)
    try:
        bundle = build_bundle(db, project_id=current.project_id or 0, defect=defect)
    except DefectDraftError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    except EvidenceRefError as exc:
        raise APIException(code=422, msg=str(exc), http_status=422) from None
    return R.ok({"bundle": bundle.to_dict(), "markdown": bundle.to_markdown()})


@router.get("/{defect_id}/reproduction-bundle/download", summary="下载复现包（zip）")
def download_bundle_api(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    defect = _load_defect(db, defect_id, current.project_id or 0)
    try:
        bundle = build_bundle(db, project_id=current.project_id or 0, defect=defect)
    except DefectDraftError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return Response(
        content=bundle.to_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="defect-{defect_id}-repro.zip"'},
    )


@router.post("/{defect_id}/confirm", response_model=R[dict], summary="人工确认草稿为正式缺陷")
def confirm_draft_api(
    defect_id: int,
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    _load_defect(db, defect_id, current.project_id or 0)
    try:
        defect = promote_draft(
            db,
            defect_id=defect_id,
            project_id=current.project_id or 0,
            approver_id=getattr(current.user, "id", 0) or 0,
        )
    except DefectDraftError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    return R.ok(_draft_out(defect))
