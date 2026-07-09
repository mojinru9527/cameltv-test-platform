"""Version mission orchestration service."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import paginate
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlanCase
from app.models.version_mission import AgentWorkLog, GeneratedArtifact, VersionMission


DEPARTMENTS = {
    "product-department",
    "pm-department",
    "design-department",
    "dev-department",
    "qa-department",
    "team-leader",
}


def create_mission(db: Session, data: dict, project_id: int, user_id: int) -> dict:
    mission_key = _build_mission_key(db, project_id, data.get("version") or "v")
    row = VersionMission(
        project_id=project_id,
        mission_key=mission_key,
        title=data.get("title", ""),
        version=data.get("version", ""),
        requirement_url=data.get("requirement_url", ""),
        test_env_url=data.get("test_env_url", ""),
        admin_env_url=data.get("admin_env_url", ""),
        environment_id=data.get("environment_id"),
        requirement_doc_id=data.get("requirement_doc_id"),
        test_plan_id=data.get("test_plan_id"),
        scope=json.dumps(data.get("scope") or {}, ensure_ascii=False),
        created_by=user_id,
        qa_owner_id=data.get("qa_owner_id") or user_id,
        status="draft",
    )
    db.add(row)
    db.flush()
    write_log(
        db,
        project_id=project_id,
        mission_id=row.id,
        department="pm-department",
        agent_name="version-mission-service",
        action="mission:create",
        detail=f"Created mission {row.mission_key} for version {row.version}",
        payload={"mission_key": row.mission_key, "version": row.version},
    )
    db.commit()
    db.refresh(row)
    return mission_to_dict(row)


def update_mission(db: Session, mission_id: int, project_id: int, data: dict) -> dict | None:
    row = _get_mission_row(db, mission_id, project_id)
    if not row:
        return None
    for field in (
        "title", "version", "requirement_url", "test_env_url", "admin_env_url",
        "environment_id", "requirement_doc_id", "test_plan_id", "status",
        "summary", "qa_owner_id",
    ):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    if "scope" in data and data["scope"] is not None:
        row.scope = json.dumps(data["scope"], ensure_ascii=False)
    db.flush()
    write_log(
        db,
        project_id=project_id,
        mission_id=row.id,
        department="pm-department",
        agent_name="version-mission-service",
        action="mission:update",
        detail="Mission metadata updated",
        payload={k: v for k, v in data.items() if v is not None},
    )
    db.commit()
    db.refresh(row)
    return mission_to_dict(row)


def list_missions(
    db: Session,
    project_id: int,
    *,
    status: str = "",
    version: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = select(VersionMission).where(VersionMission.project_id == project_id)
    if status:
        stmt = stmt.where(VersionMission.status == status)
    if version:
        stmt = stmt.where(VersionMission.version == version)
    if keyword:
        stmt = stmt.where(
            (VersionMission.title.contains(keyword))
            | (VersionMission.mission_key.contains(keyword))
            | (VersionMission.version.contains(keyword))
        )
    rows, total = paginate(db, stmt.order_by(VersionMission.created_at.desc()), page=page, page_size=page_size)
    return [mission_to_dict(r) for r in rows], total


def get_mission(db: Session, mission_id: int, project_id: int) -> dict | None:
    row = _get_mission_row(db, mission_id, project_id)
    return mission_to_dict(row) if row else None


def get_mission_detail(db: Session, mission_id: int, project_id: int) -> dict | None:
    row = _get_mission_row(db, mission_id, project_id)
    if not row:
        return None
    return {
        **mission_to_dict(row),
        "logs": list_logs(db, mission_id, project_id, page=1, page_size=100)[0],
        "artifacts": list_artifacts(db, mission_id, project_id),
        "coverage": compute_summary(db, mission_id, project_id),
    }


def delete_mission(db: Session, mission_id: int, project_id: int) -> bool:
    row = _get_mission_row(db, mission_id, project_id)
    if not row:
        return False
    for log in db.scalars(select(AgentWorkLog).where(AgentWorkLog.mission_id == mission_id)).all():
        db.delete(log)
    for artifact in db.scalars(select(GeneratedArtifact).where(GeneratedArtifact.mission_id == mission_id)).all():
        db.delete(artifact)
    db.delete(row)
    db.commit()
    return True


def write_log(
    db: Session,
    *,
    project_id: int,
    mission_id: int,
    department: str,
    agent_name: str,
    action: str,
    status: str = "done",
    input_ref: str = "",
    output_ref: str = "",
    detail: str = "",
    payload: dict[str, Any] | None = None,
    duration_ms: int = 0,
) -> dict:
    if department not in DEPARTMENTS:
        department = "qa-department"
    row = AgentWorkLog(
        project_id=project_id,
        mission_id=mission_id,
        department=department,
        agent_name=agent_name,
        action=action,
        status=status,
        input_ref=input_ref,
        output_ref=output_ref,
        detail=detail,
        payload=json.dumps(payload or {}, ensure_ascii=False),
        duration_ms=duration_ms,
    )
    db.add(row)
    db.flush()
    return log_to_dict(row)


def add_log(db: Session, mission_id: int, project_id: int, data: dict) -> dict | None:
    if not _get_mission_row(db, mission_id, project_id):
        return None
    row = write_log(
        db,
        project_id=project_id,
        mission_id=mission_id,
        department=data.get("department", "qa-department"),
        agent_name=data.get("agent_name", ""),
        action=data.get("action", ""),
        status=data.get("status", "done"),
        input_ref=data.get("input_ref", ""),
        output_ref=data.get("output_ref", ""),
        detail=data.get("detail", ""),
        payload=data.get("payload") or {},
        duration_ms=data.get("duration_ms", 0),
    )
    db.commit()
    return row


def list_logs(
    db: Session,
    mission_id: int,
    project_id: int,
    *,
    department: str = "",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    stmt = select(AgentWorkLog).where(
        AgentWorkLog.project_id == project_id,
        AgentWorkLog.mission_id == mission_id,
    )
    if department:
        stmt = stmt.where(AgentWorkLog.department == department)
    rows, total = paginate(db, stmt.order_by(AgentWorkLog.created_at.desc()), page=page, page_size=page_size)
    return [log_to_dict(r) for r in rows], total


def record_artifact(
    db: Session,
    *,
    project_id: int,
    mission_id: int,
    artifact_type: str,
    source: str,
    name: str,
    ref_id: str = "",
    content: str = "",
    meta: dict[str, Any] | None = None,
) -> dict:
    row = GeneratedArtifact(
        project_id=project_id,
        mission_id=mission_id,
        artifact_type=artifact_type,
        source=source,
        name=name,
        ref_id=ref_id,
        content=content,
        meta=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return artifact_to_dict(row)


def list_artifacts(db: Session, mission_id: int, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(GeneratedArtifact)
        .where(GeneratedArtifact.project_id == project_id, GeneratedArtifact.mission_id == mission_id)
        .order_by(GeneratedArtifact.created_at.desc())
    ).all()
    return [artifact_to_dict(r) for r in rows]


def compute_summary(db: Session, mission_id: int, project_id: int) -> dict:
    mission = _get_mission_row(db, mission_id, project_id)
    if not mission:
        return {}

    case_stmt = select(TestCase).where(TestCase.project_id == project_id)
    if mission.requirement_doc_id:
        case_stmt = case_stmt.where(TestCase.source_doc_id == mission.requirement_doc_id)
    cases = db.scalars(case_stmt).all()
    artifact_rows = db.scalars(
        select(GeneratedArtifact).where(
            GeneratedArtifact.project_id == project_id,
            GeneratedArtifact.mission_id == mission_id,
        )
    ).all()
    log_rows = db.scalars(
        select(AgentWorkLog).where(
            AgentWorkLog.project_id == project_id,
            AgentWorkLog.mission_id == mission_id,
        )
    ).all()

    by_type: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for case in cases:
        by_type[case.case_type] = by_type.get(case.case_type, 0) + 1
        by_priority[case.priority] = by_priority.get(case.priority, 0) + 1

    executions = []
    if mission.test_plan_id:
        plan_case_ids = db.scalars(
            select(TestPlanCase.id).where(TestPlanCase.plan_id == mission.test_plan_id)
        ).all()
        if plan_case_ids:
            executions = db.scalars(
                select(TestExecution).where(TestExecution.plan_case_id.in_(plan_case_ids))
            ).all()

    executed = len(executions)
    passed = sum(1 for e in executions if e.status == "pass")
    failed = sum(1 for e in executions if e.status == "fail")

    return {
        "case_total": len(cases),
        "case_by_type": by_type,
        "case_by_priority": by_priority,
        "artifact_total": len(artifact_rows),
        "artifact_by_type": _count_by([a.artifact_type for a in artifact_rows]),
        "log_total": len(log_rows),
        "departments_logged": sorted({l.department for l in log_rows}),
        "execution_total": executed,
        "execution_passed": passed,
        "execution_failed": failed,
        "execution_pass_rate": round(passed / executed * 100, 1) if executed else 0.0,
    }


def compute_quality_gate(db: Session, mission_id: int, project_id: int) -> dict | None:
    mission = _get_mission_row(db, mission_id, project_id)
    if not mission:
        return None
    summary = compute_summary(db, mission_id, project_id)
    departments = set(summary.get("departments_logged", []))
    missing_departments = sorted(DEPARTMENTS - departments)
    checks = [
        {
            "name": "功能/API/UI 用例资产",
            "passed": summary.get("case_total", 0) > 0 or summary.get("artifact_total", 0) > 0,
            "detail": f"cases={summary.get('case_total', 0)}, artifacts={summary.get('artifact_total', 0)}",
        },
        {
            "name": "QA 部门日志",
            "passed": "qa-department" in departments,
            "detail": "qa-department log required",
        },
        {
            "name": "部门留痕完整度",
            "passed": len(missing_departments) <= 2,
            "detail": f"missing={','.join(missing_departments) if missing_departments else 'none'}",
        },
        {
            "name": "测试执行通过率",
            "passed": summary.get("execution_total", 0) == 0 or summary.get("execution_pass_rate", 0) >= 80,
            "detail": f"pass_rate={summary.get('execution_pass_rate', 0)}%",
        },
    ]
    score = round(sum(25 for c in checks if c["passed"]))
    passed = all(c["passed"] for c in checks)
    return {
        "mission_id": mission_id,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "score": score,
        "checks": checks,
        "summary": summary,
    }


def mark_status(db: Session, mission_id: int, project_id: int, status: str) -> dict | None:
    row = _get_mission_row(db, mission_id, project_id)
    if not row:
        return None
    row.status = status
    db.flush()
    write_log(
        db,
        project_id=project_id,
        mission_id=mission_id,
        department="team-leader",
        agent_name="version-mission-service",
        action="mission:status",
        status="done",
        detail=f"Mission status changed to {status}",
        payload={"status": status},
    )
    db.commit()
    db.refresh(row)
    return mission_to_dict(row)


def mission_to_dict(r: VersionMission) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "mission_key": r.mission_key,
        "title": r.title,
        "version": r.version,
        "requirement_url": r.requirement_url,
        "test_env_url": r.test_env_url,
        "admin_env_url": r.admin_env_url,
        "environment_id": r.environment_id,
        "requirement_doc_id": r.requirement_doc_id,
        "test_plan_id": r.test_plan_id,
        "status": r.status,
        "scope": _json_loads(r.scope, {}),
        "summary": r.summary,
        "created_by": r.created_by,
        "qa_owner_id": r.qa_owner_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def log_to_dict(r: AgentWorkLog) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "mission_id": r.mission_id,
        "department": r.department,
        "agent_name": r.agent_name,
        "action": r.action,
        "status": r.status,
        "input_ref": r.input_ref,
        "output_ref": r.output_ref,
        "detail": r.detail,
        "payload": _json_loads(r.payload, {}),
        "duration_ms": r.duration_ms,
        "created_at": r.created_at,
    }


def artifact_to_dict(r: GeneratedArtifact) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "mission_id": r.mission_id,
        "artifact_type": r.artifact_type,
        "source": r.source,
        "name": r.name,
        "ref_id": r.ref_id,
        "content": r.content,
        "meta": _json_loads(r.meta, {}),
        "created_at": r.created_at,
    }


def _get_mission_row(db: Session, mission_id: int, project_id: int) -> VersionMission | None:
    return db.scalar(
        select(VersionMission).where(
            VersionMission.id == mission_id,
            VersionMission.project_id == project_id,
        )
    )


def _build_mission_key(db: Session, project_id: int, version: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in version).strip("-").upper() or "V"
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"VM-{cleaned}-{today}"
    count = db.scalar(
        select(func.count(VersionMission.id)).where(
            VersionMission.project_id == project_id,
            VersionMission.mission_key.like(f"{prefix}-%"),
        )
    ) or 0
    return f"{prefix}-{count + 1:03d}"


def _json_loads(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw) if raw else default
    except (TypeError, json.JSONDecodeError):
        return default


def _count_by(values: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result
