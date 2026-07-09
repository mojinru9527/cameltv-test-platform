"""Version mission API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException, not_found
from app.schemas.common import R
from app.schemas.version_mission import (
    AgentWorkLogCreate,
    AgentWorkLogOut,
    OpenApiGenerateRequest,
    QualityGateOut,
    TrafficGenerateRequest,
    UiDraftGenerateRequest,
    VersionMissionCreate,
    VersionMissionOut,
    VersionMissionUpdate,
)
from app.services import case_generation_service, version_mission_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/version-missions", tags=["版本测试任务"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db,
        user_id=cu.user.id,
        username=cu.user.username or "",
        project_id=cu.project_id or 0,
        action=action,
        target=target,
        detail=detail,
        ip=req.client.host if req.client else "",
    )


@router.get("", response_model=R[dict])
def list_missions(
    status: str = Query(""),
    version: str = Query(""),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    items, total = version_mission_service.list_missions(
        db,
        current.project_id or 0,
        status=status,
        version=version,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("", response_model=R[VersionMissionOut])
def create_mission(
    req: Request,
    body: VersionMissionCreate,
    current: CurrentUser = Depends(require_permission("mission:create")),
    db: Session = Depends(get_db),
):
    data = version_mission_service.create_mission(
        db,
        body.model_dump(),
        current.project_id or 0,
        current.user.id,
    )
    _audit(req, current, db, "mission:create", data["mission_key"], data["title"])
    return R.ok(VersionMissionOut(**data))


@router.get("/{mission_id}", response_model=R[dict])
def get_mission(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = version_mission_service.get_mission_detail(db, mission_id, current.project_id or 0)
    if not data:
        raise not_found("版本测试任务")
    return R.ok(data)


@router.put("/{mission_id}", response_model=R[VersionMissionOut])
def update_mission(
    req: Request,
    mission_id: int,
    body: VersionMissionUpdate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    data = version_mission_service.update_mission(
        db,
        mission_id,
        current.project_id or 0,
        body.model_dump(exclude_unset=True),
    )
    if not data:
        raise not_found("版本测试任务")
    _audit(req, current, db, "mission:update", data["mission_key"])
    return R.ok(VersionMissionOut(**data))


@router.delete("/{mission_id}", response_model=R[dict])
def delete_mission(
    req: Request,
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:delete")),
    db: Session = Depends(get_db),
):
    ok = version_mission_service.delete_mission(db, mission_id, current.project_id or 0)
    if not ok:
        raise not_found("版本测试任务")
    _audit(req, current, db, "mission:delete", f"#{mission_id}")
    return R.ok({"deleted": True})


@router.post("/{mission_id}/logs", response_model=R[AgentWorkLogOut])
def add_log(
    mission_id: int,
    body: AgentWorkLogCreate,
    current: CurrentUser = Depends(require_permission("mission:log")),
    db: Session = Depends(get_db),
):
    data = version_mission_service.add_log(db, mission_id, current.project_id or 0, body.model_dump())
    if not data:
        raise not_found("版本测试任务")
    return R.ok(AgentWorkLogOut(**data))


@router.get("/{mission_id}/logs", response_model=R[dict])
def list_logs(
    mission_id: int,
    department: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    items, total = version_mission_service.list_logs(
        db,
        mission_id,
        current.project_id or 0,
        department=department,
        page=page,
        page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("/{mission_id}/generate/api-openapi", response_model=R[dict])
def generate_api_openapi(
    mission_id: int,
    body: OpenApiGenerateRequest,
    current: CurrentUser = Depends(require_permission("mission:generate")),
    db: Session = Depends(get_db),
):
    try:
        data = case_generation_service.generate_api_cases_from_openapi(
            db,
            mission_id=mission_id,
            project_id=current.project_id or 0,
            spec=body.spec,
            source_name=body.source_name,
            import_to_case_library=body.import_to_case_library,
        )
    except ValueError as e:
        raise APIException(str(e))
    return R.ok(data)


@router.post("/{mission_id}/generate/api-traffic", response_model=R[dict])
def generate_api_traffic(
    mission_id: int,
    body: TrafficGenerateRequest,
    current: CurrentUser = Depends(require_permission("mission:generate")),
    db: Session = Depends(get_db),
):
    try:
        data = case_generation_service.generate_api_cases_from_traffic(
            db,
            mission_id=mission_id,
            project_id=current.project_id or 0,
            traffic=body.traffic,
            source_name=body.source_name,
            import_to_case_library=body.import_to_case_library,
        )
    except ValueError as e:
        raise APIException(str(e))
    return R.ok(data)


@router.post("/{mission_id}/generate/ui-draft", response_model=R[dict])
def generate_ui_draft(
    mission_id: int,
    body: UiDraftGenerateRequest,
    current: CurrentUser = Depends(require_permission("mission:generate")),
    db: Session = Depends(get_db),
):
    try:
        data = case_generation_service.generate_ui_drafts(
            db,
            mission_id=mission_id,
            project_id=current.project_id or 0,
            priorities=body.priorities,
            write_specs=body.write_specs,
            max_cases=body.max_cases,
        )
    except ValueError as e:
        raise APIException(str(e))
    return R.ok(data)


@router.get("/{mission_id}/quality-gate", response_model=R[QualityGateOut])
def quality_gate(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = version_mission_service.compute_quality_gate(db, mission_id, current.project_id or 0)
    if not data:
        raise not_found("版本测试任务")
    return R.ok(QualityGateOut(**data))
