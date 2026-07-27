"""Trace / coverage service — requirement-case-plan-execution-defect matrix."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.defect import Defect
from app.models.requirement import RequirementDocument
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase


def get_project_coverage(db: Session, project_id: int) -> dict:
    """Aggregate coverage stats for a project.

    Returns a matrix of case status across the platform:
      total_cases, cases_in_plans, cases_executed, cases_passed,
      cases_with_defects, and by-domain breakdown.
    """
    # Total cases in project
    total_cases = db.scalar(
        select(func.count(TestCase.id)).where(TestCase.project_id == project_id)
    ) or 0

    # Cases that are linked to at least one plan
    plan_case_sub = (
        select(TestPlanCase.case_id)
        .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
        .where(TestPlan.project_id == project_id)
        .distinct()
    )
    cases_in_plans = db.scalar(
        select(func.count()).select_from(plan_case_sub.subquery())
    ) or 0

    # Cases that have been executed at least once
    executed_case_sub = (
        select(TestPlanCase.case_id)
        .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
        .where(TestPlanCase.plan_id.in_(
            select(TestPlan.id).where(TestPlan.project_id == project_id)
        ))
        .distinct()
    )
    cases_executed = db.scalar(
        select(func.count()).select_from(executed_case_sub.subquery())
    ) or 0

    # Cases that passed on their last execution
    passed_case_sub = (
        select(TestPlanCase.case_id)
        .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
        .where(
            TestPlanCase.plan_id.in_(
                select(TestPlan.id).where(TestPlan.project_id == project_id)
            ),
            TestExecution.status == "pass",
        )
        .distinct()
    )
    cases_passed = db.scalar(
        select(func.count()).select_from(passed_case_sub.subquery())
    ) or 0

    # Cases with linked defects
    defected_case_sub = (
        select(Defect.case_id)
        .where(Defect.project_id == project_id, Defect.case_id.isnot(None))
        .distinct()
    )
    cases_with_defects = db.scalar(
        select(func.count()).select_from(defected_case_sub.subquery())
    ) or 0

    # By case_type breakdown
    type_rows = db.execute(
        select(TestCase.case_type, func.count(TestCase.id))
        .where(TestCase.project_id == project_id)
        .group_by(TestCase.case_type)
    ).all()
    by_type = {row[0]: row[1] for row in type_rows}

    # By domain breakdown
    domain_rows = db.execute(
        select(TestCase.domain, func.count(TestCase.id))
        .where(TestCase.project_id == project_id)
        .group_by(TestCase.domain)
    ).all()
    by_domain = {row[0]: row[1] for row in domain_rows}

    # Requirement coverage
    req_count = db.scalar(
        select(func.count(RequirementDocument.id))
        .where(RequirementDocument.project_id == project_id)
    ) or 0

    # Requirements that have had cases imported
    req_with_cases = db.scalar(
        select(func.count(RequirementDocument.id))
        .where(
            RequirementDocument.project_id == project_id,
            RequirementDocument.imported_count > 0,
        )
    ) or 0

    return {
        "total_cases": total_cases,
        "cases_in_plans": cases_in_plans,
        "cases_executed": cases_executed,
        "cases_passed": cases_passed,
        "cases_with_defects": cases_with_defects,
        "by_type": by_type,
        "by_domain": by_domain,
        "coverage_rate": round(cases_in_plans / total_cases * 100, 1) if total_cases else 0,
        "execution_rate": round(cases_executed / total_cases * 100, 1) if total_cases else 0,
        "pass_rate": round(cases_passed / max(cases_executed, 1) * 100, 1),
        "requirement_count": req_count,
        "requirements_with_cases": req_with_cases,
        "requirement_coverage_rate": round(req_with_cases / req_count * 100, 1) if req_count else 0,
    }


def get_requirement_coverage(db: Session, doc_id: int, project_id: int) -> dict | None:
    """Return coverage for a single requirement document (batch-queried, no N+1)."""
    from app.models.requirement import RequirementDocument

    doc = db.get(RequirementDocument, doc_id)
    if not doc or doc.project_id != project_id:
        return None

    cases = db.scalars(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.source_doc_id == doc_id,
        )
    ).all()

    total = len(cases)
    if total == 0:
        return {
            "document_id": doc.id, "document_title": doc.title,
            "document_status": doc.status, "total_cases": 0,
            "imported_count": doc.imported_count or 0,
            "cases_in_plans": 0, "cases_executed": 0, "cases_passed": 0,
            "cases_with_defects": 0, "coverage_rate": 0.0,
            "execution_rate": 0.0, "pass_rate": 0.0, "cases": [],
        }

    case_ids = {c.id for c in cases}

    # Batch: which cases are in plans
    pc_rows = db.execute(
        select(TestPlanCase.case_id).where(TestPlanCase.case_id.in_(case_ids)).distinct()
    ).all()
    cases_in_plan_set = {row[0] for row in pc_rows}

    # Batch: latest execution status per case
    from sqlalchemy import and_
    latest_exec_sub = (
        select(
            TestPlanCase.case_id,
            func.max(TestExecution.executed_at).label("max_ts"),
        )
        .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
        .where(TestPlanCase.case_id.in_(case_ids))
        .group_by(TestPlanCase.case_id)
        .subquery()
    )
    exec_rows = db.execute(
        select(TestPlanCase.case_id, TestExecution.status)
        .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
        .join(latest_exec_sub, and_(
            TestPlanCase.case_id == latest_exec_sub.c.case_id,
            TestExecution.executed_at == latest_exec_sub.c.max_ts,
        ))
    ).all()
    case_status_map = {row[0]: row[1] for row in exec_rows}

    # Batch: defect count per case
    defect_rows = db.execute(
        select(Defect.case_id, func.count(Defect.id))
        .where(Defect.case_id.in_(case_ids))
        .group_by(Defect.case_id)
    ).all()
    defect_map = {row[0]: row[1] for row in defect_rows}

    # Build results
    in_plans = 0
    executed = 0
    passed = 0
    with_defects = 0
    case_details = []

    for c in cases:
        in_plan = c.id in cases_in_plan_set
        exec_status = case_status_map.get(c.id)
        is_executed = exec_status is not None
        is_passed = exec_status == "pass"
        defect_count = defect_map.get(c.id, 0)

        if in_plan:
            in_plans += 1
        if is_executed:
            executed += 1
        if is_passed:
            passed += 1
        if defect_count > 0:
            with_defects += 1

        case_details.append({
            "case_id": c.case_id, "title": c.title, "domain": c.domain,
            "module": c.module, "priority": c.priority,
            "in_plan": in_plan, "executed": is_executed,
            "passed": is_passed, "defect_count": defect_count,
        })

    return {
        "document_id": doc.id, "document_title": doc.title,
        "document_status": doc.status, "total_cases": total,
        "imported_count": doc.imported_count or 0,
        "cases_in_plans": in_plans, "cases_executed": executed,
        "cases_passed": passed, "cases_with_defects": with_defects,
        "coverage_rate": round(in_plans / total * 100, 1),
        "execution_rate": round(executed / total * 100, 1),
        "pass_rate": round(passed / max(executed, 1) * 100, 1),
        "cases": case_details,
    }


def get_trend(db: Session, project_id: int, days: int = 30) -> dict:
    """Return pass-rate trend over the last N days (aggregated daily)."""
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Daily execution stats from TestExecution
    exec_rows = db.execute(
        select(
            func.date(TestExecution.executed_at).label("day"),
            TestExecution.status,
            func.count(TestExecution.id).label("cnt"),
        )
        .join(TestPlanCase, TestExecution.plan_case_id == TestPlanCase.id)
        .join(TestPlan, TestPlanCase.plan_id == TestPlan.id)
        .where(
            TestPlan.project_id == project_id,
            TestExecution.executed_at >= since,
        )
        .group_by("day", TestExecution.status)
        .order_by("day")
    ).all()

    # Build daily buckets
    from collections import defaultdict
    daily: dict[str, dict] = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0, "skip": 0, "block": 0})
    for day, status, cnt in exec_rows:
        key = str(day)
        daily[key]["total"] += cnt
        status_key = "pass" if status == "pass" else status
        if status_key in ("pass", "fail", "skip", "block"):
            daily[key][status_key] += cnt

    trend = []
    for day in sorted(daily):
        d = daily[day]
        rate = round(d["pass"] / d["total"] * 100, 1) if d["total"] else 0
        trend.append({
            "date": day,
            "total": d["total"],
            "pass": d["pass"],
            "fail": d["fail"],
            "skip": d["skip"],
            "block": d["block"],
            "pass_rate": rate,
        })

    # Overall stats for the period
    total_exec = sum(d["total"] for d in daily.values())
    total_pass = sum(d["pass"] for d in daily.values())

    return {
        "period_days": days,
        "total_executions": total_exec,
        "overall_pass_rate": round(total_pass / total_exec * 100, 1) if total_exec else 0,
        "trend": trend,
    }


def get_case_trace(db: Session, case_id: int, project_id: int) -> dict | None:
    """Get the full trace for a single test case: plans → executions → defects."""
    case = db.get(TestCase, case_id)
    if not case or case.project_id != project_id:
        return None

    # Plans containing this case
    plan_cases = db.scalars(
        select(TestPlanCase)
        .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
        .where(
            TestPlanCase.case_id == case_id,
            TestPlan.project_id == project_id,
        )
    ).all()

    # Batch load all executions for all plan_cases (was N+1 per plan_case)
    pc_ids = [pc.id for pc in plan_cases]
    all_execs_by_pc: dict[int, list] = {}
    if pc_ids:
        all_execs = db.scalars(
            select(TestExecution)
            .where(TestExecution.plan_case_id.in_(pc_ids))
            .order_by(TestExecution.executed_at.desc())
        ).all()
        for e in all_execs:
            all_execs_by_pc.setdefault(e.plan_case_id, []).append(e)

    plans = []
    for pc in plan_cases:
        plan = pc.plan
        execs = all_execs_by_pc.get(pc.id, [])
        plans.append({
            "plan_id": plan.id,
            "plan_name": plan.name,
            "plan_status": plan.status,
            "last_status": pc.last_status,
            "executions": [
                {
                    "id": e.id,
                    "status": e.status,
                    "executed_at": e.executed_at.isoformat() if e.executed_at else None,
                    "notes": e.notes,
                }
                for e in execs
            ],
        })

    # Defects linked to this case
    defects = db.scalars(
        select(Defect).where(Defect.case_id == case_id, Defect.project_id == project_id)
    ).all()

    return {
        "case_id": case.case_id,
        "case_title": case.title,
        "domain": case.domain,
        "module": case.module,
        "priority": case.priority,
        "case_type": case.case_type,
        "plans": plans,
        "defects": [
            {"defect_id": d.defect_id, "title": d.title, "severity": d.severity, "status": d.status}
            for d in defects
        ],
    }
