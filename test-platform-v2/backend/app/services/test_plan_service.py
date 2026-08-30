"""测试计划 Service — 计划 CRUD + 用例关联 + 执行记录 + 进度统计。"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.base_service import batch_user_names
from app.core.config import settings
from app.core.execution_status import canonical_exec_status

logger = logging.getLogger(__name__)
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
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
    # Batch 182（P1-06）：统一词表兜底（调用方可能传旧值）
    status = canonical_exec_status(status)
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
# 环境预检（Batch 148 / C147-2）
# ═══════════════════════════════════════════════════════

_VAR_TOKEN = re.compile(r"\$\{(\w+)\}")


def ensure_plan_execution_ready(
    db: Session,
    plan_id: int,
    *,
    project_id: int,
    environment_id: int | None,
) -> None:
    """执行前环境/Token 就绪检查（Batch 148 / C147-2）。

    仅当计划包含 API 类型用例时强制检查：
    - 必须提供环境且环境属于当前项目；
    - 相对路径端点要求环境已配置 base_url；
    - 用例引用但环境变量中不存在的 ${{var}}（如 ${{token}}）直接拦截。

    未就绪抛 ValueError，由 router 转 R(code=1, msg=...) 明确提示，
    不产生任何执行记录。
    """
    from app.models.environment import EnvironmentVariable
    from app.services.environment_service import get_environment

    pcs = db.scalars(
        select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)
    ).all()
    api_cases = []
    for pc in pcs:
        tc = db.get(TestCase, pc.case_id)
        if tc and tc.case_type == "api":
            api_cases.append((pc, tc))
    if not api_cases:
        return  # 纯人工/UI 计划不需要环境

    if not environment_id:
        raise ValueError("计划包含 API 用例，请先选择执行环境（含 base_url 与变量）后再执行")

    env = get_environment(db, environment_id, project_id)
    if not env:
        raise ValueError("执行环境不存在或不属于当前项目，请重新选择")

    var_rows = db.scalars(
        select(EnvironmentVariable).where(EnvironmentVariable.environment_id == environment_id)
    ).all()
    var_keys = {v.key for v in var_rows}

    need_base_url = False
    missing_vars: set[str] = set()
    for _pc, tc in api_cases:
        endpoint = (tc.api_endpoint or "").strip()
        if endpoint and not endpoint.startswith(("http://", "https://")):
            need_base_url = True
        for template in (tc.api_headers or "", tc.api_body or "", endpoint):
            for m in _VAR_TOKEN.finditer(template):
                key = m.group(1)
                if key not in var_keys:
                    missing_vars.add(f"{key}（用例「{tc.title}」）")

    if need_base_url and not (env.get("base_url") or "").strip():
        raise ValueError(f"执行环境「{env['name']}」未配置 base_url，无法拼接用例的相对路径")
    if missing_vars:
        raise ValueError(
            "执行环境缺少以下变量（请先在环境变量中配置）: " + "、".join(sorted(missing_vars))
        )


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
        # Batch 182（P1-06）：DB 词表已统一为 passed/failed/skipped/blocked，
        # 响应键（pass_/fail/skip/block）保持兼容映射
        key = _STATS_RESPONSE_KEY.get(canonical_exec_status(s), "pending")
        entry[key] += 1

    return stats


# DB 状态 → 计划统计响应键（响应契约兼容）
_STATS_RESPONSE_KEY = {
    "pending": "pending",
    "passed": "pass_",
    "failed": "fail",
    "skipped": "skip",
    "blocked": "block",
}


def _calc_stats(db: Session, plan_id: int) -> dict:
    """Calculate execution progress for a single plan. Uses _batch_calc_stats."""
    result = _batch_calc_stats(db, {plan_id})
    return result.get(plan_id, {"total": 0, "pending": 0, "pass_": 0, "fail": 0, "skip": 0, "block": 0})


# ═══════════════════════════════════════════════════════
# API 用例自动执行
# ═══════════════════════════════════════════════════════

def batch_assign(
    db: Session,
    plan_id: int,
    *,
    pcase_ids: list[int],
    assignee_id: int,
    project_id: int = 0,
) -> int:
    """批量指派计划中的用例给执行人。返回成功指派的条数。"""
    from sqlalchemy import update

    result = db.execute(
        update(TestPlanCase)
        .where(
            TestPlanCase.plan_id == plan_id,
            TestPlanCase.id.in_(pcase_ids),
            TestPlanCase.plan.has(TestPlan.project_id == project_id),
        )
        .values(executor_id=assignee_id)
    )
    db.commit()
    return result.rowcount


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

    ensure_plan_execution_ready(
        db, plan_id, project_id=project_id, environment_id=environment_id,
    )

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

    for idx, (pc, tc) in enumerate(api_cases, start=1):
        try:
            exec_result = execute_api_case(
                db, tc.id,
                project_id=project_id,
                environment_id=environment_id,
            )
            api_pass = exec_result.get("all_pass", False)
            status = "passed" if api_pass else "failed"
            actual_result = json.dumps(exec_result, ensure_ascii=False, default=str)

            # 创建执行记录（Batch 186 / C182-1：唯一事实源 = test_execution，
            # 不再双写 api_execution_task/items——统计/报告/追溯已统一读 test_execution）
            exec_status_code, exec_error_type, exec_error_message = _execution_error_fields(actual_result)
            exec_row = TestExecution(
                plan_case_id=pc.id,
                executor_id=executor_id,
                status=status,
                actual_result=actual_result,
                notes=f"API 自动执行: {tc.api_method or 'GET'} {tc.api_endpoint}",
                trace_id="",
                status_code=exec_status_code,
                error_type=exec_error_type,
                error_message=exec_error_message,
                executed_at=now,
            )
            db.add(exec_row)
            executed += 1
            if api_pass:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            status = "failed"
            exec_result = {"error": str(e), "status_code": 0}
            actual_result = json.dumps(exec_result, ensure_ascii=False)
            exec_status_code, exec_error_type, exec_error_message = _execution_error_fields(actual_result)
            exec_row = TestExecution(
                plan_case_id=pc.id,
                executor_id=executor_id,
                status=status,
                actual_result=actual_result,
                notes=f"API 执行异常: {e}",
                trace_id="",
                status_code=exec_status_code,
                error_type=exec_error_type,
                error_message=exec_error_message,
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

        # Batch 174（FIX-173-P0-03）：分批短事务提交，避免单长事务锁行
        if idx % 10 == 0:
            db.commit()

    db.commit()

    return {
        "total": len(api_cases),
        "executed": executed,
        "passed": passed,
        "failed": failed,
        "details": results,
    }


def _compile_ui_case(db, case, project_id: int, base_url: str) -> tuple[str, str]:
    """LLM 优先编译 UI spec；LLM 不可用/失败时回退规则引擎。返回 (spec_code, compiler)。"""
    try:
        from app.services.case_compiler_service import compile_to_playwright
        compiled = compile_to_playwright(db, case, project_id=project_id, base_url=base_url, validate=False)
        spec_code = (compiled.get("spec_code") or "").strip()
        if spec_code and "TODO" not in spec_code:
            return spec_code, "llm"
    except Exception:
        logger.exception("LLM 编译失败，回退规则引擎: case=%s", getattr(case, "id", None))

    from app.schemas.playground import CompileRequest, SourceType
    from app.services.playground_service import build_gherkin_from_case, compile_spec
    source = build_gherkin_from_case(case)
    compiled = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
    return compiled.spec_code, "rules"


def _case_has_actionable_steps(case) -> bool:
    """manual 用例是否具备可转 UI 的步骤。"""
    try:
        steps = json.loads(case.steps or "[]")
    except (json.JSONDecodeError, TypeError):
        steps = []
    if not isinstance(steps, list) or not steps:
        return False
    return any(
        isinstance(item, dict) and (item.get("desc") or item.get("step") or "").strip()
        for item in steps
    )


def _resolve_plan_base_url(db: Session, environment_id: int | None, project_id: int) -> str:
    """取计划执行环境的 base_url 作为 UI 自动化被测地址（无环境时回退 localhost）。"""
    from app.models.environment import Environment
    if environment_id:
        row = db.scalar(
            select(Environment).where(
                Environment.id == environment_id,
                Environment.project_id == project_id,
            )
        )
        if row and row.base_url:
            return row.base_url
    return "http://localhost:5173"


def _ui_error_summary(ui_result: dict) -> str:
    """batch-168 D6：UI 执行失败时给出可读摘要（error/exit_code/stdout 尾部）。"""
    if ui_result.get("error"):
        return str(ui_result["error"])[:500]
    parts = []
    if ui_result.get("exit_code") not in (None, 0):
        parts.append(f"exit_code={ui_result['exit_code']}")
    tail = str(ui_result.get("stdout_tail") or "").strip()
    if tail:
        parts.append("stdout: " + tail[-300:])
    return " ".join(parts).strip() or "未知"


def _resolve_ui_storage_state(db: Session, ui_environment_id: int | None, project_id: int) -> dict | None:
    """batch-170：从 UI 执行环境读取 UI_STORAGE_STATE_JSON（Playwright storageState）。

    环境变量可加密；解密失败保留原值。JSON 非法时返回 None，不阻断执行。
    """
    if not ui_environment_id:
        return None
    from app.models.environment import EnvironmentVariable
    row = db.scalar(
        select(EnvironmentVariable).where(
            EnvironmentVariable.environment_id == ui_environment_id,
            EnvironmentVariable.key == "UI_STORAGE_STATE_JSON",
        )
    )
    if not row:
        return None
    value = row.value or ""
    if row.encrypted and value:
        try:
            from app.core.cipher import decrypt_value
            value = decrypt_value(value)
        except Exception:
            logger.exception("UI storageState 解密失败 environment=%d", ui_environment_id)
            return None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _write_plan_ui_job(db: Session, case, spec_code: str, creator_id: int, project_id: int) -> None:
    """把计划执行生成的可执行 spec 回写为 UI 任务资产（失败不阻断执行）。"""
    if not spec_code:
        return
    try:
        from app.services.playground_service import _write_spec_as_ui_job
        _write_spec_as_ui_job(db, case, spec_code, creator_id, project_id)
    except Exception:
        logger.exception("计划 UI 任务回写失败: case=%s", getattr(case, "id", None))


def _execute_ui_case_sync(db, case, project_id: int, *, base_url: str = "", storage_state: dict | None = None) -> dict:
    """同步编译并执行一条 UI 用例（batch-167: LLM 优先 + 规则兜底 + 真实 Playwright 链路）。

    返回 pass/fail、产物与执行摘要；编译含 TODO 占位或执行失败都如实返回。
    """

    base_url = (base_url or "").strip() or "http://localhost:5173"
    spec_code, compiler = _compile_ui_case(db, case, project_id, base_url)
    if not spec_code:
        return {"ok": False, "error": "编译失败，未生成可执行 spec", "compiler": compiler, "spec_code": ""}
    if "TODO" in spec_code:
        return {"ok": False, "error": "编译含 TODO 占位，无法执行", "spec_code": spec_code, "compiler": compiler}

    playwright_dir = Path(__file__).resolve().parent.parent.parent / "tests" / "playwright"
    generated_dir = playwright_dir / "specs" / "generated"
    artifact_root = Path(__file__).resolve().parent.parent.parent / "storage" / "ui-runs" / "plan-sync"

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "-", case.case_id or f"TC-{case.id}")
    generated_dir.mkdir(parents=True, exist_ok=True)
    spec_file = generated_dir / f"plan74-{safe_id}.spec.ts"
    spec_file.write_text(spec_code, encoding="utf-8")
    rel_spec = str(spec_file.relative_to(playwright_dir)).replace("\\", "/")
    artifact_dir = artifact_root / safe_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    default_shot = playwright_dir / "playground-screenshot.png"
    # 清理上一轮的残留截图，避免把无关文件当作本次产物
    try:
        default_shot.unlink(missing_ok=True)
    except OSError:
        logger.warning("默认截图清理失败")

    try:
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        if not npx:
            return {"ok": False, "error": "npx/playwright 不可用", "spec_code": spec_code, "compiler": compiler}
        storage_state_path = None
        run_env = None
        if storage_state:
            import tempfile as _tempfile
            _fd, storage_state_path = _tempfile.mkstemp(prefix="plan-ui-state-", suffix=".json")
            with open(_fd, "w", encoding="utf-8") as _fh:
                json.dump(storage_state, _fh, ensure_ascii=False)
            run_env = {**os.environ, "PLAYWRIGHT_STORAGE_STATE": storage_state_path}
        result = subprocess.run(
            [
                npx, "playwright", "test", rel_spec,
                "--project", "chromium", "--reporter", "json",
                "--output", str(artifact_dir),
            ],
            capture_output=True, text=True, timeout=float(getattr(settings, "ui_run_timeout_seconds", 90.0) or 90.0),
            cwd=str(playwright_dir), encoding="utf-8", errors="replace", env=run_env,
        )
        stdout_text = result.stdout or ""
        stderr_text = (result.stderr or "")[:2000]
        report = _parse_playwright_report(stdout_text)
        if report is None:
            return {
                "ok": False, "error": "Playwright 未输出有效 JSON 报告", "compiler": compiler, "spec_code": spec_code,
                "exit_code": result.returncode, "stdout_tail": stdout_text[-1500:], "stderr_tail": stderr_text,
                "storage_state": bool(storage_state),
            }
        passed, failed, skipped, total = report
        screenshots = [str(f.relative_to(artifact_dir)).replace("\\", "/") for f in sorted(artifact_dir.rglob("*.png"))]
        # spec 默认截图写到 runner cwd；移动到产物目录统一收集
        if default_shot.exists() and not screenshots:
            try:
                target = artifact_dir / "playground-screenshot.png"
                target.write_bytes(default_shot.read_bytes())
                screenshots = ["playground-screenshot.png"]
            except OSError:
                logger.warning("默认截图写入失败")
        return {
            "ok": failed == 0 and total > 0,
            "total": total, "passed": passed, "failed": failed, "skipped": skipped,
            "screenshots": screenshots[:20],
            "artifact_dir": str(artifact_dir).replace("\\", "/"),
            "exit_code": result.returncode,
            "stdout_tail": stdout_text[-1500:], "stderr_tail": stderr_text,
            "spec_code": spec_code, "compiler": compiler,
            "storage_state": bool(storage_state),
        }
    except subprocess.TimeoutExpired:
        seconds = int(float(getattr(settings, "ui_run_timeout_seconds", 90.0) or 90.0))
        return {"ok": False, "error": f"UI 执行超时（{seconds}s）", "spec_code": spec_code, "compiler": compiler}
    except FileNotFoundError:
        return {"ok": False, "error": "npx/playwright 不可用", "spec_code": spec_code, "compiler": compiler}
    finally:
        try:
            spec_file.unlink(missing_ok=True)
        except OSError:
            logger.warning("spec 文件清理失败")
        if storage_state_path:
            try:
                Path(storage_state_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("storageState 临时文件清理失败")
def _parse_playwright_report(stdout_text: str) -> tuple[int, int, int, int] | None:
    """解析 Playwright --reporter=json 输出，返回 (passed, failed, skipped, total)。"""
    payload = None
    for candidate in (stdout_text, stdout_text.strip().lstrip("\ufeff")):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and isinstance(parsed.get("suites"), list):
                payload = parsed
                break
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    if payload is None:
        return None

    def _collect(suite_list: list[dict]) -> list[dict]:
        specs: list[dict] = []
        for s in suite_list:
            specs.extend(s.get("specs", []))
            specs.extend(_collect(s.get("suites", [])))
        return specs

    passed = failed = skipped = total = 0
    for spec in _collect(payload.get("suites", [])):
        for test in spec.get("tests", []):
            total += 1
            results_list = test.get("results", [])
            if not results_list:
                skipped += 1
                continue
            status = results_list[-1].get("status", "skipped")
            if status in ("passed", "expected"):
                passed += 1
            elif status in ("failed", "unexpected"):
                failed += 1
            else:
                skipped += 1
    return passed, failed, skipped, total


# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# 批量一键执行 (所有类型)
# ═══════════════════════════════════════════════════════

def execute_all_cases(
    db: Session,
    plan_id: int,
    *,
    executor_id: int = 0,
    environment_id: int | None = None,
    auto_ui: bool = True,
    ui_environment_id: int | None = None,
    project_id: int = 0,
) -> dict:
    """一键执行计划中全部用例：API 用例自动执行，人工/UI 用例标记 skip。"""
    from app.services.api_execution_service import execute_api_case

    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        raise ValueError("计划不存在")
    # batch-168 D7：API 用执行环境、UI 用 UI 环境（缺省回退执行环境）
    base_url = _resolve_plan_base_url(db, ui_environment_id or environment_id, project_id)
    # batch-170：登录态注入（来自 UI 环境变量 UI_STORAGE_STATE_JSON）
    ui_storage_state = _resolve_ui_storage_state(db, ui_environment_id, project_id)

    ensure_plan_execution_ready(
        db, plan_id, project_id=project_id, environment_id=environment_id,
    )

    pcs = db.scalars(
        select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)
    ).all()

    if not pcs:
        return {"total": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "details": [], "message": "计划中没有关联用例"}

    # Batch 161（G4）：批量预载用例，避免大计划（数千条）逐条 SELECT 造成一键执行 >120s
    _case_ids = [pc.case_id for pc in pcs]
    _case_map = {}
    if _case_ids:
        _case_rows = db.scalars(
            select(TestCase).where(TestCase.id.in_(_case_ids))
        ).all()
        _case_map = {c.id: c for c in _case_rows}

    now = datetime.now()
    details = []
    pending_exec_rows = []  # Batch 161：非 API 执行记录延迟批量入库
    executed = 0
    passed = 0
    failed = 0
    skipped = 0
    # Batch 174（FIX-173-P0-03）：分批短事务提交，避免整计划单长事务
    # 锁行数分钟（生产 PG statement timeout / 调度线程阻塞）。每 BATCH_COMMIT_SIZE 条
    # 提交一次；commit 会 expire ORM 对象，pc/tc 由 SQLAlchemy 自动重查。
    BATCH_COMMIT_SIZE = 10

    for idx, pc in enumerate(pcs, start=1):
        tc = _case_map.get(pc.case_id)
        if not tc:
            skipped += 1
            details.append({"plan_case_id": pc.id, "case_id": pc.case_id, "case_title": "(已删除)", "case_type": "unknown", "status": "skipped", "error": "用例不存在"})
            continue

        if tc.case_type == "api":
            try:
                exec_result = execute_api_case(
                    db, tc.id,
                    project_id=project_id,
                    environment_id=environment_id,
                )
                api_pass = exec_result.get("all_pass", False)
                status = "passed" if api_pass else "failed"
                actual_result = json.dumps(exec_result, ensure_ascii=False, default=str)
                notes = f"批量自动执行: {tc.api_method or 'GET'} {tc.api_endpoint}"
            except Exception as e:
                status = "failed"
                exec_result = {"error": str(e), "status_code": 0}
                actual_result = json.dumps(exec_result, ensure_ascii=False)
                notes = f"批量执行异常: {e}"
        elif tc.case_type == "ui":
            # UI 用例：真实编译 + headless Chromium 执行（batch-74 统一编排）
            try:
                ui_result = _execute_ui_case_sync(db, tc, project_id, base_url=base_url, storage_state=ui_storage_state)
                status = "passed" if ui_result.get("ok") else "failed"
                actual_result = json.dumps(ui_result, ensure_ascii=False, default=str)
                if ui_result.get("ok"):
                    notes = (
                        f"UI 自动执行: {ui_result.get('total', 0)} 条断言全部通过, "
                        f"截图 {len(ui_result.get('screenshots', []))} 张"
                    )
                else:
                    notes = f"UI 执行失败: {_ui_error_summary(ui_result)}"
            except Exception as e:
                status = "failed"
                actual_result = json.dumps({"error": str(e)}, ensure_ascii=False)
                notes = f"UI 执行异常: {e}"
        else:
            # batch-167 Phase 3b: manual P0/P1 有步骤用例自动转 UI 执行，不再一律 skip
            if (
                auto_ui
                and tc.priority in ("P0", "P1")
                and _case_has_actionable_steps(tc)
            ):
                try:
                    ui_result = _execute_ui_case_sync(db, tc, project_id, base_url=base_url, storage_state=ui_storage_state)
                    status = "passed" if ui_result.get("ok") else "failed"
                    actual_result = json.dumps(ui_result, ensure_ascii=False, default=str)
                    notes = (
                        f"手动用例自动转 UI 执行: {ui_result.get('total', 0)} 条断言"
                        if ui_result.get("ok") else f"手动用例转 UI 执行失败: {_ui_error_summary(ui_result)}"
                    )
                    if ui_result.get("ok") or ui_result.get("spec_code"):
                        _write_plan_ui_job(db, tc, ui_result.get("spec_code", ""), executor_id, project_id)
                except Exception as e:
                    status = "failed"
                    actual_result = json.dumps({"error": str(e)}, ensure_ascii=False)
                    notes = f"手动用例转 UI 执行异常: {e}"
            else:
                status = "skipped"
                actual_result = ""
                notes = "需人工执行（无步骤/优先级低于 P1/auto_ui 关闭）"

        # 创建执行记录（Batch 148: 失败根因独立字段）
        exec_status_code, exec_error_type, exec_error_message = _execution_error_fields(actual_result)
        exec_row = TestExecution(
            plan_case_id=pc.id,
            executor_id=executor_id,
            status=status,
            actual_result=actual_result,
            notes=notes,
            trace_id="",
            status_code=exec_status_code,
            error_type=exec_error_type,
            error_message=exec_error_message,
            executed_at=now,
        )
        # Batch 161（G4）：非 API 行延迟 add_all 批量入库；API 行直接 add（Batch 186/C182-1：不再登记任务快照）
        if tc.case_type == "api":
            db.add(exec_row)
        else:
            pending_exec_rows.append(exec_row)

        # 更新 plan_case 状态
        pc.last_status = status
        pc.last_executed_at = now
        pc.executor_id = executor_id

        if status == "passed":
            passed += 1
            executed += 1
        elif status == "failed":
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
            "error": notes if status == "skipped" else ("" if status == "passed" else notes),
        })

        # Batch 174（FIX-173-P0-03）：分批短事务提交，避免整计划单长事务
        # 锁行数分钟（生产 PG statement timeout / APScheduler 线程阻塞 cron）。
        if idx % BATCH_COMMIT_SIZE == 0:
            if pending_exec_rows:
                db.add_all(pending_exec_rows)
                pending_exec_rows = []
            db.commit()

    # Batch 161（G4）：非 API 执行记录一次性批量入库（避免数千条逐条 ORM add）
    if pending_exec_rows:
        db.add_all(pending_exec_rows)

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

def _execution_error_fields(actual_result: str) -> tuple[int, str, str]:
    """从 actual_result JSON 提取 (status_code, error_type, error_message)。

    兼容历史行：Batch 148 之前失败根因只存在 actual_result JSON 里，
    DB 独立字段为空时由 _execution_to_dict 调用本函数回填展示。
    """
    try:
        data = json.loads(actual_result) if actual_result else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        return 0, "", ""

    status_code = data.get("status_code") or 0
    try:
        status_code = int(status_code)
    except (TypeError, ValueError):
        status_code = 0

    error_type = data.get("error_type") or ""
    error_message = data.get("error") or data.get("message") or ""

    if error_message and not error_type:
        error_type = "EXECUTION_ERROR"
    if not error_message and data.get("all_pass") is False:
        summary = data.get("assertion_summary") or {}
        if isinstance(summary, dict):
            failed = int(summary.get("failed") or 0)
            total = int(summary.get("total") or 0)
            error_message = f"断言失败 {failed}/{total} 条"
        else:
            error_message = f"断言失败（HTTP {status_code}）"
        error_type = error_type or "ASSERTION_FAILED"
    return status_code, error_type, error_message



def run_failure_auto_chain(
    db: Session,
    plan_id: int,
    project_id: int = 0,
    creator_id: int = 0,
) -> dict:
    """C147-6（Batch 155 实现）：计划失败自动转缺陷/报告/通知。

    开关（auto_defect_on_fail）关闭时直接跳过；开启时对失败执行做规则分诊
    （use_llm=False，避免后台任务依赖 LLM 造成延迟），将 bug/case_defect 类
    生成缺陷草稿并入库，再生成失败报告，最后推送 plan_failed 通知。

    必须在独立 DB session 中调用（后台任务），不污染请求事务。
    """
    from app.schemas.defect import DefectCreate
    from app.schemas.test_report import ReportCreate
    from app.services.defect_service import create_defect
    from app.services.notify_service import notify_sync
    from app.services.report_service import create_report
    from app.services.triage_service import generate_defect_draft, triage_failed_cases

    plan = db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )
    if not plan:
        return {"error": "计划不存在"}
    if not plan.auto_defect_on_fail:
        return {"skipped": "auto_defect_on_fail=false"}

    # Batch 161：triage 失败不阻断链路（记日志并返回错误，后台任务不抛未捕获异常）
    try:
        triage = triage_failed_cases(db, plan_id, project_id=project_id, use_llm=False)
    except Exception as e:  # noqa: BLE001 - 后台任务必须吞掉并记录
        logger.warning("失败自动链路 triage 异常: plan=%s err=%s", plan_id, e)
        return {"error": f"triage 失败: {e}"}
    classified = triage.get("classified", []) or []
    defects = []
    defect_errors = []
    for item in classified:
        if item.get("category") not in ("bug", "case_defect"):
            continue
        # Batch 161：单条缺陷生成失败不中断整条链路（其余缺陷/报告/通知照常）
        try:
            draft = generate_defect_draft(item)
            data = DefectCreate(
                title=draft["title"],
                description=draft["description"],
                severity=draft.get("severity", "P2"),
                case_id=draft.get("case_id") or None,
                execution_id=draft.get("execution_id") or None,
            )
            defects.append(create_defect(db, data, creator_id=creator_id, project_id=project_id))
        except Exception as e:  # noqa: BLE001 - 单条失败跳过
            defect_errors.append(str(e)[:200])
            logger.warning("失败自动转缺陷跳过: plan=%s exec=%s err=%s", plan_id, item.get("execution_id"), e)

    report = None
    try:
        report = create_report(
            db,
            ReportCreate(plan_id=plan_id, name=f"失败自动报告-{plan.name or plan_id}"),
            creator_id=creator_id,
            project_id=project_id,
        )
    except Exception as e:  # 报告生成失败不阻断缺陷与通知
        logger.warning("失败自动报告生成失败: plan=%s err=%s", plan_id, e)

    try:
        notify_sync(
            db,
            project_id,
            "plan_failed",
            {
                "plan_name": plan.name or "",
                "failed": triage.get("total_failures", 0),
                "defects": len(defects),
                "report": (report or {}).get("report_id") or (report or {}).get("id") or "-",
                "link": f"/testplan/{plan_id}",
            },
        )
    except Exception as e:
        logger.warning("plan_failed 通知失败: plan=%s err=%s", plan_id, e)

    # Batch 161 follow-up3：create_defect/create_report 只 flush 不 commit，
    # 后台独立会话关闭即回滚 → 生产缺陷/报告从未落库。这里统一提交持久化。
    try:
        db.commit()
    except Exception as e:  # noqa: BLE001 - 提交失败也要记录
        logger.warning("失败自动链路提交失败: plan=%s err=%s", plan_id, e)
        db.rollback()

    return {
        "plan_id": plan_id,
        "total_failures": triage.get("total_failures", 0),
        "defects_created": len(defects),
        "defect_errors": defect_errors,
        "report_id": (report or {}).get("report_id") or (report or {}).get("id") or None,
        "notified": True,
    }

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
        "auto_defect_on_fail": bool(getattr(r, "auto_defect_on_fail", False)),
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
    # Batch 148: 独立字段优先，缺失时（历史行）从 actual_result JSON 回填
    parsed_sc, parsed_et, parsed_em = _execution_error_fields(r.actual_result or "")
    status_code = getattr(r, "status_code", 0) or parsed_sc
    error_type = getattr(r, "error_type", "") or parsed_et
    error_message = getattr(r, "error_message", "") or parsed_em
    return {
        "id": r.id,
        "plan_case_id": r.plan_case_id,
        "executor_id": r.executor_id,
        "status": r.status,
        "actual_result": r.actual_result,
        "notes": r.notes,
        "trace_id": trace_id,
        "kibana_link": build_kibana_link(trace_id) if trace_id else "",
        "status_code": status_code,
        "error_type": error_type,
        "error_message": error_message,
        "api_task_id": getattr(r, "api_task_id", None),
        "executed_at": r.executed_at.isoformat() if r.executed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "case_id": case.id if case else 0,
        "case_title": case.title if case else "",
        "executor_name": "",
    }

def run_async_execute_all(
    *,
    plan_id: int,
    executor_id: int,
    environment_id: int | None,
    ui_environment_id: int | None,
    auto_ui: bool,
    project_id: int,
) -> None:
    """batch-169 C168-2：后台执行计划全部用例，避免同步请求被网关 300s 切断。"""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        execute_all_cases(
            db,
            plan_id,
            executor_id=executor_id,
            environment_id=environment_id,
            ui_environment_id=ui_environment_id,
            auto_ui=auto_ui,
            project_id=project_id,
        )
    except Exception:
        logger.exception("后台计划执行失败 plan_id=%d", plan_id)
        db.rollback()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# 路由层 ORM 收敛薄函数（Batch 181 路由拆分）
# ═══════════════════════════════════════════════════════

def create_plan_with_cases(
    db: Session,
    *,
    project_id: int,
    name: str,
    description: str,
    creator_id: int,
    case_ids: list[int],
) -> dict:
    """OpenAPI 导入后自动创建测试计划并关联用例（沿用调用方会话，提交由路由层负责）。

    返回 {"id", "plan_id", "name", "case_count"}，与路由原逻辑一致。
    """
    plan_id_str = f"PLAN-{uuid.uuid4().hex[:8].upper()}"
    plan = TestPlan(
        project_id=project_id,
        plan_id=plan_id_str,
        name=name,
        description=description,
        status="draft",
        creator_id=creator_id,
    )
    db.add(plan)
    db.flush()

    for sort_idx, cid in enumerate(case_ids):
        db.add(TestPlanCase(
            plan_id=plan.id,
            case_id=cid,
            sort_order=sort_idx + 1,
        ))

    return {"id": plan.id, "plan_id": plan_id_str, "name": name, "case_count": len(case_ids)}


# ── Batch 182（C181-1）open_api 路由层 ORM 收敛薄函数 ──

def get_plan_row(db: Session, plan_id: int, project_id: int) -> TestPlan | None:
    """项目内按 id 查询计划行（open_api CI 触发复用）。"""
    return db.scalar(
        select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id)
    )


def list_plan_cases(db: Session, plan_id: int) -> list[TestPlanCase]:
    """计划下全部用例关联行（open_api CI 触发复用）。"""
    return list(
        db.scalars(select(TestPlanCase).where(TestPlanCase.plan_id == plan_id)).all()
    )


def get_execution(db: Session, run_id: int) -> TestExecution | None:
    """按 id 查询执行记录（open_api CI 查询/回写复用）。"""
    return db.scalar(select(TestExecution).where(TestExecution.id == run_id))


def get_plan_case(db: Session, plan_case_id: int) -> TestPlanCase | None:
    """按 id 查询计划用例行（连带 plan，避免路由层惰性加载）。"""
    return db.scalar(
        select(TestPlanCase)
        .where(TestPlanCase.id == plan_case_id)
        .options(joinedload(TestPlanCase.plan))
    )


def trigger_plan_from_ci(
    db: Session,
    plan_id: int,
    project_id: int,
    *,
    token_name: str,
) -> tuple[TestPlan | None, int]:
    """外部 CI 触发计划：为全部用例创建 pending 执行并回写 last_status。

    返回 (plan_row, executed)；plan 不存在返回 (None, 0)。
    沿用调用方会话、不 commit（提交由路由层负责）。
    """
    plan = get_plan_row(db, plan_id, project_id)
    if not plan:
        return None, 0
    pcases = list_plan_cases(db, plan_id)

    now = datetime.now()
    executed = 0
    for pc in pcases:
        exec_row = TestExecution(
            plan_case_id=pc.id, executor_id=0, status="pending",
            actual_result="", notes=f"[CI 自动触发] token={token_name}",
            executed_at=now,
        )
        db.add(exec_row)
        pc.last_status = "pending"
        pc.last_executed_at = now
        executed += 1
    db.flush()
    return plan, executed

