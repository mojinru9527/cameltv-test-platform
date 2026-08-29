"""Mission service (V30-012).

Owns lifecycle validation so illegal status jumps (e.g. DRAFT → CONTRACT_FROZEN)
are rejected at the service boundary, not silently accepted at the DB layer.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import AcceptanceStatus, MissionStatus, MissionType
from app.modules.aitde.mission import repository
from app.modules.aitde.mission.models import Mission

# Whitelist of legal lifecycle transitions. Anything not listed is rejected.
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SOURCE_READY", "SCOPE_ANALYZING", "ARCHIVED"},
    "SOURCE_READY": {"SCOPE_ANALYZING", "SCOPE_REVIEW", "ARCHIVED"},
    "SCOPE_ANALYZING": {"SCOPE_REVIEW", "ARCHIVED"},
    "SCOPE_REVIEW": {"CONTRACT_BUILDING", "ARCHIVED"},
    "CONTRACT_BUILDING": {"CONTRACT_REVIEW", "ARCHIVED"},
    "CONTRACT_REVIEW": {"CONTRACT_FROZEN", "ARCHIVED"},
    "CONTRACT_FROZEN": {"SCENARIO_BUILDING", "ARCHIVED"},
    "SCENARIO_BUILDING": {"SCENARIO_REVIEW", "ARCHIVED"},
    "SCENARIO_REVIEW": {"SCENARIO_READY", "ARCHIVED"},
    "SCENARIO_READY": {"ARCHIVED"},
    "ARCHIVED": set(),
}

_VALID_TYPES = {m.value for m in MissionType}
_VALID_STATUSES = {s.value for s in MissionStatus}


def _validate_status_transition(current: str, target: str) -> None:
    """Reject illegal jumps; identity is a no-op."""
    if current == target:
        return
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise APIException(
            code=400,
            msg=f"非法状态迁移：{current} → {target}",
            http_status=400,
        )


def create_mission(
    db: Session, data: dict[str, Any], project_id: int, user_id: int
) -> Mission:
    title = (data.get("title") or "").strip()
    if not title:
        raise APIException(code=400, msg="标题不能为空", http_status=400)

    mission_type = (data.get("mission_type") or MissionType.VERSION.value)
    if mission_type not in _VALID_TYPES:
        raise APIException(
            code=400, msg=f"非法任务类型：{mission_type}", http_status=400
        )

    payload: dict[str, Any] = {
        "mission_key": repository._build_mission_key(db, project_id),
        "mission_type": mission_type,
        "title": title,
        "version_label": data.get("version_label"),
        "qa_owner_id": data.get("qa_owner_id"),
        "default_environment_id": data.get("default_environment_id"),
        "owner_id": user_id,
        "status": MissionStatus.DRAFT.value,
        "acceptance_status": AcceptanceStatus.NOT_EVALUATED.value,
    }
    return repository.create(db, payload, project_id, user_id)


def list_missions(
    db: Session,
    project_id: int,
    status: str | None = None,
    mission_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Mission], int]:
    if status and status not in _VALID_STATUSES:
        raise APIException(code=400, msg=f"非法状态：{status}", http_status=400)
    return repository.list_missions(
        db,
        project_id,
        status=status,
        mission_type=mission_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


def get_mission(db: Session, mission_id: int, project_id: int) -> Mission:
    row = repository.get(db, mission_id, project_id)
    if not row:
        raise APIException(code=404, msg="任务不存在", http_status=404)
    return row


def update_mission(
    db: Session, mission_id: int, project_id: int, data: dict[str, Any]
) -> Mission:
    row = get_mission(db, mission_id, project_id)

    target_status = data.get("status")
    if target_status is not None:
        if target_status not in _VALID_STATUSES:
            raise APIException(
                code=400, msg=f"非法状态：{target_status}", http_status=400
            )
        _validate_status_transition(row.status, target_status)

    target_type = data.get("mission_type")
    if target_type is not None and target_type not in _VALID_TYPES:
        raise APIException(
            code=400, msg=f"非法任务类型：{target_type}", http_status=400
        )

    return repository.update(
        db,
        row,
        {
            "title": data.get("title"),
            "version_label": data.get("version_label"),
            "owner_id": data.get("owner_id"),
            "qa_owner_id": data.get("qa_owner_id"),
            "default_environment_id": data.get("default_environment_id"),
            "status": target_status,
            "acceptance_status": data.get("acceptance_status"),
        },
    )


def archive_mission(db: Session, mission_id: int, project_id: int) -> Mission:
    row = get_mission(db, mission_id, project_id)
    return repository.archive(db, row)
