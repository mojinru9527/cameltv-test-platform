"""需求覆盖率服务（平台简化批次：原 trace_service.get_requirement_coverage 迁入）。

质量追溯已随报告中心删除，但需求文档页的覆盖率（纳入计划/执行/通过/缺陷关联）
是需求主链路的保留能力，此处独立保留。
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.defect import Defect
from app.models.requirement import RequirementDocument
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlanCase


def get_requirement_coverage(db: Session, doc_id: int, project_id: int) -> dict | None:
    """Return coverage for a single requirement document (batch-queried, no N+1)."""
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

    pc_rows = db.execute(
        select(TestPlanCase.case_id).where(TestPlanCase.case_id.in_(case_ids)).distinct()
    ).all()
    cases_in_plan_set = {row[0] for row in pc_rows}

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

    defect_rows = db.execute(
        select(Defect.case_id, func.count(Defect.id))
        .where(Defect.case_id.in_(case_ids))
        .group_by(Defect.case_id)
    ).all()
    defect_map = {row[0]: row[1] for row in defect_rows}

    in_plans = 0
    executed = 0
    passed = 0
    with_defects = 0
    case_details = []

    for c in cases:
        in_plan = c.id in cases_in_plan_set
        exec_status = case_status_map.get(c.id)
        is_executed = exec_status is not None
        is_passed = exec_status == "passed"
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
            "id": c.id, "case_id": c.case_id, "title": c.title, "domain": c.domain,
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
