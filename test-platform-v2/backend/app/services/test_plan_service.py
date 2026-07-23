"""测试计划 Service — 计划 CRUD + 用例关联 + 执行记录 + 进度统计。"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.base_service import batch_user_names, paginate
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.user import User
from app.services.elk_service import build_kibana_link, extract_trace_id


# ═══════════════════════════════════════════════════════
# 计划 CRUD
# ═══════════════════════════════════════════════════════

def list_plans(
    db: Session,
    *,
    project_id: int = 0,
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页查询计划列表（batch stats, no N+1 per plan）。"""
    stmt = select(TestPlan).where(TestPlan.project_id == project_id)
    count_stmt = select(func.count(TestPlan.id)).where(TestPlan.project_id == project_id)

    if status:
        stmt = stmt.where(TestPlan.status == status)
        count_stmt = count_stmt.where(TestPlan.status == status)
    if keyword:
        stmt = stmt.where(
            (TestPlan.name.contains(keyword)) | (TestPlan.plan_id.contains(keyword))
        )
        count_stmt = count_stmt.where(
            (TestPlan.name.contains(keyword)) | (TestPlan.plan_id.contains(keyword))
        )

    total = db.scalar(count_stmt) or 0

    rows = db.scalars(
        stmt.order_by(TestPlan.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    # Batch calc stats for all plan_ids in one query (was N individual _calc_stats calls)
    plan_ids = {r.id for r in rows}
    stats_map = _batch_calc_stats(db, plan_ids)

    # Batch load assignee names
    assignee_ids = {r.assignee_id for r in rows if r.assignee_id}
    user_map = batch_user_names(db, assignee_ids)

    plans = []
    for r in rows:
        d = _plan_to_dict(r)
        d["stats"] = stats_map.get(r.id, {"total": 0, "pending": 0, "pass_": 0, "fail": 0, "skip": 0, "block": 0})
        d["assignee_name"] = user_map.get(r.assignee_id, "") if r.assignee_id else ""
        plans.append(d)

    return plans, total


def get_plan(db: Session, plan_id: int, project_id: int = 0) -> dict | None:
    """获取计划详情，含用例列表 + 统计。"""
    row = db.scalar(
        select(TestPlan)
        .where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
        .options(joinedload(TestPlan.plan_cases))
    )
    if not row:
        return None

    d = _plan_to_dict(row)

    # Batch load cases for all plan_cases in one query (was N+1 per case)
    case_ids = {pc.case_id for pc in row.plan_cases}
    cases = {}
    if case_ids:
        case_rows = db.scalars(select(TestCase).where(TestCase.id.in_(case_ids))).all()
        cases = {c.id: c for c in case_rows}

    d["cases"] = [_plan_case_to_dict(pc, cases.get(pc.case_id)) for pc in row.plan_cases]
    d["stats"] = _calc_stats(db, row.id)
    return d


def create_plan(db: Session, data: dict, creator_id: int, project_id: int = 0) -> dict:
    """创建计划。"""
    data["project_id"] = project_id
    data["creator_id"] = creator_id
    row = TestPlan(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _plan_to_dict(row)


def update_plan(db: Session, plan_id: int, data: dict, project_id: int = 0) -> dict | None:
    """更新计划。"""
    row = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not row:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _plan_to_dict(row)


def delete_plan(db: Session, plan_id: int, project_id: int = 0) -> bool:
    """删除计划（级联删除关联用例 + 执行记录由 FK cascade 处理）。"""
    row = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════
# 用例关联
# ═══════════════════════════════════════════════════════

def add_cases(
    db: Session, plan_id: int, case_ids: list[int], project_id: int = 0
) -> int:
    """批量添加用例到计划（跳过已存在的）。"""
    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        return 0

    # 查询已有关联
    existing = set(
        db.scalars(
            select(TestPlanCase.case_id).where(TestPlanCase.plan_id == plan_id)
        ).all()
    )

    # 获取当前最大 sort_order
    max_sort = db.scalar(
        select(func.max(TestPlanCase.sort_order)).where(TestPlanCase.plan_id == plan_id)
    ) or 0

    added = 0
    for case_id in case_ids:
        if case_id in existing:
            continue
        # 验证用例存在且属于同项目
        tc = db.get(TestCase, case_id)
        if not tc or tc.project_id != project_id:
            continue
        max_sort += 1
        pc = TestPlanCase(plan_id=plan_id, case_id=case_id, sort_order=max_sort)
        db.add(pc)
        added += 1

    db.commit()
    return added


def remove_cases(
    db: Session, plan_id: int, case_ids: list[int], project_id: int = 0
) -> int:
    """批量从计划中移除用例。"""
    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        return 0

    rows = db.scalars(
        select(TestPlanCase).where(
            TestPlanCase.plan_id == plan_id,
            TestPlanCase.case_id.in_(case_ids),
        )
    ).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return len(rows)


def update_case_sort(
    db: Session, pcase_id: int, sort_order: int, project_id: int = 0
) -> bool:
    """更新计划内某条用例的排序。"""
    pc = db.get(TestPlanCase, pcase_id)
    if not pc:
        return False
    # 验证所属计划的 project
    plan = db.get(TestPlan, pc.plan_id)
    if not plan or plan.project_id != project_id:
        return False
    pc.sort_order = sort_order
    db.commit()
    return True


# ═══════════════════════════════════════════════════════
# 执行记录
# ═══════════════════════════════════════════════════════

def execute_case(
    db: Session,
    plan_id: int,
    pcase_id: int,
    executor_id: int,
    status: str,
    actual_result: str = "",
    notes: str = "",
    project_id: int = 0,
) -> dict | None:
    """执行一条用例 → 创建 execution 记录 + 更新 plan_case 状态。"""
    pc = db.get(TestPlanCase, pcase_id)
    if not pc or pc.plan_id != plan_id:
        return None

    # 验证所属计划的 project
    plan = db.get(TestPlan, pc.plan_id)
    if not plan or plan.project_id != project_id:
        return None

    now = datetime.now()
    trace_id = extract_trace_id(actual_result) or extract_trace_id(notes) or ""
    exec_row = TestExecution(
        plan_case_id=pcase_id,
        executor_id=executor_id,
        status=status,
        actual_result=actual_result,
        notes=notes,
        trace_id=trace_id,
        executed_at=now,
    )
    db.add(exec_row)

    # 更新 plan_case 的最新状态
    pc.last_status = status
    pc.last_executed_at = now
    pc.executor_id = executor_id

    db.commit()
    db.refresh(exec_row)

    case = db.get(TestCase, pc.case_id)
    return _execution_to_dict(exec_row, case)


def get_executions(
    db: Session,
    plan_id: int,
    *,
    pcase_id: int = 0,
    page: int = 1,
    page_size: int = 50,
    project_id: int = 0,
) -> tuple[list[dict], int]:
    """查询计划的执行历史。可指定 plan_case_id 只看单条用例的历史。"""
    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        return [], 0

    pcase_ids = [
        pc.id for pc in db.scalars(
            select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)
        ).all()
    ]

    stmt = select(TestExecution).where(TestExecution.plan_case_id.in_(pcase_ids))
    count_stmt = select(func.count(TestExecution.id)).where(
        TestExecution.plan_case_id.in_(pcase_ids)
    )

    if pcase_id:
        stmt = stmt.where(TestExecution.plan_case_id == pcase_id)
        count_stmt = count_stmt.where(TestExecution.plan_case_id == pcase_id)

    total = db.scalar(count_stmt) or 0

    rows = db.scalars(
        stmt.order_by(TestExecution.executed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    # Batch load plan_case and test_case (was N+1 per execution row)
    pc_ids = {r.plan_case_id for r in rows}
    pc_map: dict[int, TestPlanCase] = {}
    case_map: dict[int, TestCase] = {}
    if pc_ids:
        pc_rows = db.scalars(select(TestPlanCase).where(TestPlanCase.id.in_(pc_ids))).all()
        pc_map = {p.id: p for p in pc_rows}
        case_ids = {p.case_id for p in pc_rows}
        if case_ids:
            case_rows = db.scalars(select(TestCase).where(TestCase.id.in_(case_ids))).all()
            case_map = {c.id: c for c in case_rows}

    items = []
    for r in rows:
        pc = pc_map.get(r.plan_case_id)
        case = case_map.get(pc.case_id) if pc else None
        items.append(_execution_to_dict(r, case))

    return items, total


# ═══════════════════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════════════════

def _batch_calc_stats(db: Session, plan_ids: set[int]) -> dict[int, dict]:
    """Batch calculate execution progress for multiple plans (avoids N+1 per plan)."""
    if not plan_ids:
        return {}
    rows = db.execute(
        select(TestPlanCase.plan_id, TestPlanCase.last_status)
        .where(TestPlanCase.plan_id.in_(plan_ids))
    ).all()

    # Initialize stats for every requested plan
    empty = {"total": 0, "pending": 0, "pass_": 0, "fail": 0, "skip": 0, "block": 0}
    stats: dict[int, dict] = {pid: dict(empty) for pid in plan_ids}

    for plan_id, s in rows:
        entry = stats[plan_id]
        entry["total"] += 1
        key = s if s in ("pending", "pass", "fail", "skip", "block") else "pending"
        if key == "pass":
            entry["pass_"] += 1
        else:
            entry[key] += 1

    return stats


def _calc_stats(db: Session, plan_id: int) -> dict:
    """Calculate execution progress for a single plan. Uses _batch_calc_stats."""
    result = _batch_calc_stats(db, {plan_id})
    return result.get(plan_id, {"total": 0, "pending": 0, "pass_": 0, "fail": 0, "skip": 0, "block": 0})


# ═══════════════════════════════════════════════════════
# API 用例自动执行
# ═══════════════════════════════════════════════════════

def auto_execute_api_cases(
    db: Session,
    plan_id: int,
    *,
    executor_id: int = 0,
    environment_id: int | None = None,
    project_id: int = 0,
) -> dict:
    """自动执行计划中所有 API 类型用例，返回汇总。"""
    from app.services.api_execution_service import execute_api_case

    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        raise ValueError("计划不存在")

    # 获取所有 API 类型用例的 plan_case
    pcs = db.scalars(
        select(TestPlanCase)
        .where(TestPlanCase.plan_id == plan_id)
    ).all()

    api_cases = []
    for pc in pcs:
        tc = db.get(TestCase, pc.case_id)
        if tc and tc.case_type == "api":
            api_cases.append((pc, tc))

    if not api_cases:
        return {"total": 0, "executed": 0, "passed": 0, "failed": 0, "details": [], "message": "计划中没有 API 类型用例"}

    now = datetime.now()
    results = []
    executed = 0
    passed = 0
    failed = 0

    for pc, tc in api_cases:
        try:
            exec_result = execute_api_case(
                db, tc.id,
                project_id=project_id,
                environment_id=environment_id,
            )
            api_pass = exec_result.get("all_pass", False)
            status = "pass" if api_pass else "fail"
            actual_result = json.dumps(exec_result, ensure_ascii=False, default=str)

            # 创建执行记录
            exec_row = TestExecution(
                plan_case_id=pc.id,
                executor_id=executor_id,
                status=status,
                actual_result=actual_result,
                notes=f"API 自动执行: {tc.api_method or 'GET'} {tc.api_endpoint}",
                trace_id="",
                executed_at=now,
            )
            db.add(exec_row)
            executed += 1
            if api_pass:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            status = "fail"
            actual_result = json.dumps({"error": str(e)}, ensure_ascii=False)
            exec_row = TestExecution(
                plan_case_id=pc.id,
                executor_id=executor_id,
                status=status,
                actual_result=actual_result,
                notes=f"API 执行异常: {e}",
                trace_id="",
                executed_at=now,
            )
            db.add(exec_row)
            executed += 1
            failed += 1

        # 更新 plan_case 状态
        pc.last_status = status
        pc.last_executed_at = now
        pc.executor_id = executor_id

        results.append({
            "plan_case_id": pc.id,
            "case_id": tc.id,
            "case_title": tc.title,
            "status": status,
        })

    db.commit()

    return {
        "total": len(api_cases),
        "executed": executed,
        "passed": passed,
        "failed": failed,
        "details": results,
    }


# ═══════════════════════════════════════════════════════
# 批量一键执行 (所有类型)
# ═══════════════════════════════════════════════════════

def execute_all_cases(
    db: Session,
    plan_id: int,
    *,
    executor_id: int = 0,
    environment_id: int | None = None,
    project_id: int = 0,
) -> dict:
    """一键执行计划中全部用例：API 用例自动执行，人工/UI 用例标记 skip。"""
    from app.services.api_execution_service import execute_api_case

    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        raise ValueError("计划不存在")

    pcs = db.scalars(
        select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)
    ).all()

    if not pcs:
        return {"total": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "details": [], "message": "计划中没有关联用例"}

    now = datetime.now()
    details = []
    executed = 0
    passed = 0
    failed = 0
    skipped = 0

    for pc in pcs:
        tc = db.get(TestCase, pc.case_id)
        if not tc:
            skipped += 1
            details.append({"plan_case_id": pc.id, "case_id": pc.case_id, "case_title": "(已删除)", "case_type": "unknown", "status": "skip", "error": "用例不存在"})
            continue

        if tc.case_type == "api":
            try:
                exec_result = execute_api_case(
                    db, tc.id,
                    project_id=project_id,
                    environment_id=environment_id,
                )
                api_pass = exec_result.get("all_pass", False)
                status = "pass" if api_pass else "fail"
                actual_result = json.dumps(exec_result, ensure_ascii=False, default=str)
                notes = f"批量自动执行: {tc.api_method or 'GET'} {tc.api_endpoint}"
            except Exception as e:
                status = "fail"
                actual_result = json.dumps({"error": str(e)}, ensure_ascii=False)
                notes = f"批量执行异常: {e}"
        else:
            # 人工/UI 用例：标记 skip
            status = "skip"
            actual_result = ""
            notes = "需人工执行"

        # 创建执行记录
        exec_row = TestExecution(
            plan_case_id=pc.id,
            executor_id=executor_id,
            status=status,
            actual_result=actual_result,
            notes=notes,
            trace_id="",
            executed_at=now,
        )
        db.add(exec_row)

        # 更新 plan_case 状态
        pc.last_status = status
        pc.last_executed_at = now
        pc.executor_id = executor_id

        if status == "pass":
            passed += 1
            executed += 1
        elif status == "fail":
            failed += 1
            executed += 1
        else:
            skipped += 1

        details.append({
            "plan_case_id": pc.id,
            "case_id": tc.id,
            "case_title": tc.title,
            "case_type": tc.case_type,
            "status": status,
            "error": notes if status == "skip" else ("" if status == "pass" else notes),
        })

    # 更新计划状态为 active
    if plan.status == "draft":
        plan.status = "active"

    db.commit()

    return {
        "total": len(pcs),
        "executed": executed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "details": details,
    }


# ═══════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════

def _plan_to_dict(r: TestPlan) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "plan_id": r.plan_id,
        "name": r.name,
        "description": r.description,
        "status": r.status,
        "creator_id": r.creator_id,
        "assignee_id": r.assignee_id or 0,
        "start_date": r.start_date.isoformat() if r.start_date else None,
        "end_date": r.end_date.isoformat() if r.end_date else None,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _plan_case_to_dict(pc: TestPlanCase, case: TestCase | None) -> dict:
    return {
        "id": pc.id,
        "plan_id": pc.plan_id,
        "case_id": pc.case_id,
        "sort_order": pc.sort_order,
        "last_status": pc.last_status,
        "last_executed_at": pc.last_executed_at.isoformat() if pc.last_executed_at else None,
        "executor_id": pc.executor_id,
        # 内联用例摘要
        "case_title": case.title if case else "",
        "case_id_code": case.case_id if case else "",
        "domain": case.domain if case else "",
        "module": case.module if case else "",
        "priority": case.priority if case else "P2",
        "case_type": case.case_type if case else "manual",
        "source_req_id": case.source_req_id if case else "",
    }


def _execution_to_dict(r: TestExecution, case: TestCase | None) -> dict:
    trace_id = getattr(r, "trace_id", "") or ""
    return {
        "id": r.id,
        "plan_case_id": r.plan_case_id,
        "executor_id": r.executor_id,
        "status": r.status,
        "actual_result": r.actual_result,
        "notes": r.notes,
        "trace_id": trace_id,
        "kibana_link": build_kibana_link(trace_id) if trace_id else "",
        "executed_at": r.executed_at.isoformat() if r.executed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "case_title": case.title if case else "",
        "executor_name": "",
    }
