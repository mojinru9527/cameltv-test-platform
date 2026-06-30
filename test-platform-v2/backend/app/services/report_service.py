"""Report service — list / get / create (snapshot) / delete."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.defect import Defect
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.test_report import TestReport
from app.services.elk_service import build_kibana_link


def _generate_report_id(db: Session, project_id: int) -> str:
    """Generate RP-YYYYMMDD-NNN unique within project."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(TestReport.id)).where(
            TestReport.project_id == project_id,
            TestReport.report_id.like(f"RP-{today}-%"),
        )
    ) or 0
    return f"RP-{today}-{count + 1:03d}"


def _build_content(db: Session, plan_id: int) -> str:
    """Build JSON snapshot of the plan."""
    plan = db.scalar(select(TestPlan).where(TestPlan.id == plan_id))

    plan_info = {}
    if plan:
        plan_info = {
            "id": plan.id,
            "plan_id": plan.plan_id,
            "name": plan.name,
            "description": plan.description,
            "status": plan.status,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
        }

    # plan cases with inline case info
    pcases = db.execute(
        select(TestPlanCase, TestCase)
        .join(TestCase, TestCase.id == TestPlanCase.case_id)
        .where(TestPlanCase.plan_id == plan_id)
        .order_by(TestPlanCase.sort_order)
    ).all()

    # Get latest trace_id per plan case from executions
    case_trace_map: dict[int, str] = {}
    pcase_ids = [pc.id for pc, _ in pcases]
    if pcase_ids:
        from sqlalchemy import desc
        for pcase_id in pcase_ids:
            last_exec = db.scalar(
                select(TestExecution)
                .where(TestExecution.plan_case_id == pcase_id)
                .order_by(desc(TestExecution.executed_at))
                .limit(1)
            )
            if last_exec and last_exec.trace_id:
                case_trace_map[pcase_id] = last_exec.trace_id

    cases = []
    stats = {"total": 0, "pass_": 0, "fail": 0, "skip": 0, "block": 0, "pending": 0}
    for pc, tc in pcases:
        trace_id = case_trace_map.get(pc.id, "")
        cases.append({
            "pcase_id": pc.id,
            "case_id": tc.id,
            "case_id_code": tc.case_id,
            "title": tc.title,
            "domain": tc.domain,
            "module": tc.module,
            "priority": tc.priority,
            "case_type": tc.case_type,
            "sort_order": pc.sort_order,
            "last_status": pc.last_status,
            "last_executed_at": pc.last_executed_at.isoformat() if pc.last_executed_at else None,
            "trace_id": trace_id,
            "kibana_link": build_kibana_link(trace_id) if trace_id else "",
        })
        stats["total"] += 1
        key = pc.last_status if pc.last_status in stats else "pending"
        stats[key] = stats.get(key, 0) + 1

    content = {
        "plan_info": plan_info,
        "stats": stats,
        "cases": cases,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(content, ensure_ascii=False)


def list_reports(
    db: Session,
    project_id: int,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """Paginated report list with plan_name."""
    base = (
        select(TestReport, TestPlan.name.label("plan_name"))
        .outerjoin(TestPlan, TestPlan.id == TestReport.plan_id)
        .where(TestReport.project_id == project_id)
    )
    if keyword:
        base = base.where(TestReport.name.contains(keyword))

    total = db.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    ) or 0

    rows = db.execute(
        base.order_by(TestReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for r, plan_name in rows:
        d = {
            "id": r.id,
            "project_id": r.project_id,
            "report_id": r.report_id,
            "name": r.name,
            "description": r.description,
            "plan_id": r.plan_id,
            "plan_name": plan_name or "",
            "creator_id": r.creator_id,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        items.append(d)

    return items, total


def get_report(db: Session, report_id: int, project_id: int) -> dict | None:
    row = db.execute(
        select(TestReport, TestPlan.name.label("plan_name"))
        .outerjoin(TestPlan, TestPlan.id == TestReport.plan_id)
        .where(TestReport.id == report_id, TestReport.project_id == project_id)
    ).first()

    if not row:
        return None

    r, plan_name = row
    content = None
    try:
        content = json.loads(r.content)
    except (json.JSONDecodeError, TypeError):
        content = {}

    return {
        "id": r.id,
        "project_id": r.project_id,
        "report_id": r.report_id,
        "name": r.name,
        "description": r.description,
        "plan_id": r.plan_id,
        "plan_name": plan_name or "",
        "creator_id": r.creator_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "content": content,
    }


def create_report(
    db: Session,
    data,           # ReportCreate
    creator_id: int,
    project_id: int,
) -> dict:
    # Validate plan exists in project
    plan = db.scalar(
        select(TestPlan).where(
            TestPlan.id == data.plan_id,
            TestPlan.project_id == project_id,
        )
    )
    if not plan:
        raise ValueError("计划不存在")

    report_id = _generate_report_id(db, project_id)
    content = _build_content(db, data.plan_id)

    r = TestReport(
        project_id=project_id,
        report_id=report_id,
        name=data.name,
        description=data.description,
        plan_id=data.plan_id,
        content=content,
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()

    # Compute quality gate
    gate = _compute_gate(db, data.plan_id, project_id, content)

    return {
        "id": r.id,
        "project_id": r.project_id,
        "report_id": r.report_id,
        "name": r.name,
        "description": r.description,
        "plan_id": r.plan_id,
        "plan_name": plan.name,
        "creator_id": r.creator_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "gate_status": gate["status"],
        "gate_details": gate["details"],
    }


def _compute_gate(db, plan_id: int, project_id: int, content_str: str) -> dict:
    """Compute quality gate for a report. Returns {status, details}."""
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except json.JSONDecodeError:
        content = {}

    stats = content.get("stats", {}) if isinstance(content, dict) else {}
    total = stats.get("total", 0)
    pass_count = stats.get("pass", 0)
    pass_rate = round(pass_count / total * 100, 1) if total else 0

    # Check for P0 open defects linked to this plan's cases
    pcases = db.scalars(
        select(TestPlanCase.case_id).where(TestPlanCase.plan_id == plan_id)
    ).all()
    case_ids = {pc[0] for pc in pcases} if pcases else set()
    p0_defects = 0
    if case_ids:
        p0_defects = db.scalar(
            select(func.count(Defect.id)).where(
                Defect.project_id == project_id,
                Defect.severity == "P0",
                Defect.status.in_(["open", "confirmed", "fixing"]),
                Defect.case_id.in_(case_ids),
            )
        ) or 0

    details = []
    passed = True

    if pass_rate < 80:
        passed = False
        details.append(f"通过率 {pass_rate}% 低于门禁阈值 80%")
    else:
        details.append(f"通过率 {pass_rate}% >= 80% (通过)")

    if p0_defects > 0:
        passed = False
        details.append(f"存在 {p0_defects} 个未关闭的 P0 缺陷")
    else:
        details.append("无未关闭 P0 缺陷 (通过)")

    return {"status": "pass" if passed else "fail", "details": details}


def delete_report(db: Session, report_id: int, project_id: int) -> bool:
    r = db.scalar(
        select(TestReport).where(
            TestReport.id == report_id,
            TestReport.project_id == project_id,
        )
    )
    if not r:
        return False
    db.delete(r)
    db.flush()
    return True
