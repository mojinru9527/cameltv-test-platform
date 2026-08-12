"""Schedule service — CRUD + trigger + run history."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.scheduler import (
    add_schedule_job,
    remove_schedule_job,
    toggle_schedule_job,
    _execute_schedule,
)
from app.models.test_plan import TestPlan
from app.models.test_schedule import TestSchedule, TestScheduleRun


def _compute_next_run(cron_expression: str) -> datetime | None:
    """Compute the next fire time for a cron expression."""
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        now = datetime.now(timezone.utc)
        return trigger.get_next_fire_time(None, now)
    except (ValueError, TypeError, KeyError):
        return None


def _ensure_schedule_env(db: Session, plan_id: int | None, environment_id: int | None, project_id: int) -> None:
    """Batch 162/C161-2：计划类调度若含 API 用例必须绑定执行环境；环境须属于当前项目。"""
    from sqlalchemy import func as _func

    from app.models.environment import Environment
    from app.models.test_case import TestCase
    from app.models.test_plan import TestPlanCase

    if not plan_id:
        return
    has_api = db.scalar(
        select(_func.count())
        .select_from(TestPlanCase)
        .join(TestCase, TestCase.id == TestPlanCase.case_id)
        .where(TestPlanCase.plan_id == plan_id, TestCase.case_type == "api")
    ) or 0
    if has_api and not environment_id:
        raise ValueError("目标计划包含 API 用例，请选择执行环境（含 base_url 与变量）后再保存")
    if environment_id:
        env = db.get(Environment, environment_id)
        if not env or env.project_id != project_id:
            raise ValueError("执行环境不存在或不属于当前项目")


def list_schedules(
    db: Session,
    project_id: int,
    enabled: bool | None = None,
    page: int = 1,
    page_size: int = 20,
):
    base = (
        select(TestSchedule, TestPlan.name.label("plan_name"))
        .outerjoin(TestPlan, TestPlan.id == TestSchedule.plan_id)
        .where(TestSchedule.project_id == project_id)
    )
    if enabled is not None:
        base = base.where(TestSchedule.enabled == enabled)

    total = db.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    ) or 0

    rows = db.execute(
        base.order_by(TestSchedule.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for s, plan_name in rows:
        items.append({
            "id": s.id,
            "project_id": s.project_id,
            "name": s.name,
            "description": s.description,
            "plan_id": s.plan_id,
            "plan_name": plan_name or "",
            "environment_id": getattr(s, "environment_id", None),
            "job_type": s.job_type,

            "job_id": s.job_id,
            "cron_expression": s.cron_expression,
            "enabled": s.enabled,
            "disabled_reason": s.disabled_reason or "",
            "next_run": s.next_run,
            "last_run": s.last_run,
            "creator_id": s.creator_id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return items, total


def get_schedule(db: Session, schedule_id: int, project_id: int) -> dict | None:
    row = db.execute(
        select(TestSchedule, TestPlan.name.label("plan_name"))
        .outerjoin(TestPlan, TestPlan.id == TestSchedule.plan_id)
        .where(TestSchedule.id == schedule_id, TestSchedule.project_id == project_id)
    ).first()

    if not row:
        return None

    s, plan_name = row
    return {
        "id": s.id,
        "project_id": s.project_id,
        "name": s.name,
        "description": s.description,
        "plan_id": s.plan_id,
        "plan_name": plan_name or "",
        "environment_id": getattr(s, "environment_id", None),
        "job_type": s.job_type,

        "job_id": s.job_id,
        "cron_expression": s.cron_expression,
        "enabled": s.enabled,
        "disabled_reason": s.disabled_reason or "",
        "next_run": s.next_run,
        "last_run": s.last_run,
        "creator_id": s.creator_id,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def create_schedule(
    db: Session,
    data,
    creator_id: int,
    project_id: int,
) -> dict:
    # Validate target（B112-3：plan|ui）
    plan = None
    if data.job_type == "ui":
        from app.models.ui_test import UiTestJob
        if not data.job_id:
            raise ValueError("job_type=ui 必须提供 job_id")
        job = db.scalar(
            select(UiTestJob).where(
                UiTestJob.id == data.job_id,
                UiTestJob.project_id == project_id,
            )
        )
        if not job:
            raise ValueError("UI job 不存在")
        plan_id = None
        plan_name = job.name
    else:
        if not data.plan_id:
            raise ValueError("job_type=plan|report 必须提供 plan_id")
        plan = db.scalar(
            select(TestPlan).where(
                TestPlan.id == data.plan_id,
                TestPlan.project_id == project_id,
            )
        )
        if not plan:
            raise ValueError("计划不存在")
        plan_id = data.plan_id
        plan_name = plan.name

    # Batch 162/C161-2：API 计划必须绑定环境
    _ensure_schedule_env(db, plan_id, data.environment_id, project_id)

    next_run = _compute_next_run(data.cron_expression)

    s = TestSchedule(
        project_id=project_id,
        name=data.name,
        description=data.description,
        plan_id=plan_id,
        environment_id=data.environment_id if data.job_type == "plan" else None,
        job_type=data.job_type,
        job_id=data.job_id if data.job_type == "ui" else None,
        cron_expression=data.cron_expression,
        enabled=data.enabled,
        disabled_reason=data.disabled_reason or "",
        next_run=next_run,
        creator_id=creator_id,
    )
    db.add(s)
    db.flush()

    # Register cron job
    if s.enabled:
        add_schedule_job(s.id, s.cron_expression)

    return {
        "id": s.id,
        "project_id": s.project_id,
        "name": s.name,
        "description": s.description,
        "plan_id": s.plan_id,
        "plan_name": plan_name,
        "environment_id": getattr(s, "environment_id", None),
        "job_type": s.job_type,
        "job_id": s.job_id,
        "cron_expression": s.cron_expression,
        "enabled": s.enabled,
        "disabled_reason": s.disabled_reason or "",
        "next_run": s.next_run,
        "last_run": s.last_run,
        "creator_id": s.creator_id,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def update_schedule(
    db: Session,
    schedule_id: int,
    data,
    project_id: int,
) -> dict | None:
    s = db.scalar(
        select(TestSchedule).where(
            TestSchedule.id == schedule_id,
            TestSchedule.project_id == project_id,
        )
    )
    if not s:
        return None

    changed = False
    cron_changed = False

    if data.name is not None:
        s.name = data.name
        changed = True
    if data.description is not None:
        s.description = data.description
        changed = True
    if data.job_type is not None or data.job_id is not None or data.plan_id is not None:
        target_type = data.job_type or s.job_type
        if target_type == "ui":
            from app.models.ui_test import UiTestJob
            job_id = data.job_id if data.job_id is not None else s.job_id
            if not job_id:
                raise ValueError("job_type=ui 必须提供 job_id")
            job = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
            if not job:
                raise ValueError("UI job 不存在")
            s.job_type = "ui"
            s.job_id = job_id
            s.plan_id = None
        else:
            plan_id = data.plan_id if data.plan_id is not None else s.plan_id
            if not plan_id:
                raise ValueError("job_type=plan|report 必须提供 plan_id")
            plan = db.scalar(select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id))
            if not plan:
                raise ValueError("计划不存在")
            s.job_type = "plan"
            s.plan_id = plan_id
            s.job_id = None
        changed = True
    # Batch 162/C161-2：更新执行环境（plan 类）；显式传 null 表示清空
    _fields_set = getattr(data, "model_fields_set", set()) or set()
    if "environment_id" in _fields_set or data.job_type is not None:
        target_type = data.job_type or s.job_type
        if target_type == "plan":
            target_plan = data.plan_id if data.plan_id is not None else s.plan_id
            if "environment_id" in _fields_set:
                new_env = data.environment_id  # 显式 null → 清空（API 计划会被预检拦截）
            else:
                new_env = s.environment_id
            _ensure_schedule_env(db, target_plan, new_env, project_id)
            if new_env != s.environment_id:
                s.environment_id = new_env
                changed = True
        elif s.environment_id is not None:
            s.environment_id = None
            changed = True
    if data.cron_expression is not None:
        s.cron_expression = data.cron_expression
        cron_changed = True
        changed = True
    if data.enabled is not None:
        # toggle（Batch 155 / P2-18：停用必须填写原因；启用时清空）
        if data.enabled != s.enabled:
            if not data.enabled:
                reason = (data.disabled_reason or s.disabled_reason or "").strip()
                if not reason:
                    raise ValueError("停用调度必须填写停用原因")
                s.disabled_reason = reason
            else:
                s.disabled_reason = ""
            toggle_schedule_job(s.id, data.enabled, s.cron_expression)
        s.enabled = data.enabled
        changed = True

    if cron_changed and s.enabled:
        # Re-register with new cron
        add_schedule_job(s.id, s.cron_expression)
        s.next_run = _compute_next_run(s.cron_expression)

    if changed:
        db.flush()

    plan = db.scalar(
        select(TestPlan).where(
            TestPlan.id == s.plan_id,
            TestPlan.project_id == project_id,
        )
    )
    return {
        "id": s.id,
        "project_id": s.project_id,
        "name": s.name,
        "description": s.description,
        "plan_id": s.plan_id,
        "plan_name": plan.name if plan else "",
        "environment_id": getattr(s, "environment_id", None),
        "job_type": s.job_type,
        "job_id": s.job_id,
        "cron_expression": s.cron_expression,
        "enabled": s.enabled,
        "disabled_reason": s.disabled_reason or "",
        "next_run": s.next_run,
        "last_run": s.last_run,
        "creator_id": s.creator_id,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def delete_schedule(db: Session, schedule_id: int, project_id: int) -> bool:
    s = db.scalar(
        select(TestSchedule).where(
            TestSchedule.id == schedule_id,
            TestSchedule.project_id == project_id,
        )
    )
    if not s:
        return False

    remove_schedule_job(schedule_id)
    db.delete(s)
    db.flush()
    return True


def trigger_schedule(db: Session, schedule_id: int, project_id: int) -> dict:
    """Batch 163 / C162-1：手动触发调度 → 立即返回，长计划后台线程执行。

    先建 running run 防止重复触发，再启动后台线程执行；接口不再阻塞到执行结束，
    避免长计划（含 API 用例）触发时 HTTP 超网关返回 502。
    """
    from datetime import datetime, timezone

    from app.core.scheduler import _execute_schedule

    s = db.scalar(
        select(TestSchedule).where(
            TestSchedule.id == schedule_id,
            TestSchedule.project_id == project_id,
        )
    )
    if not s:
        raise ValueError("调度不存在")

    active = db.scalar(
        select(TestScheduleRun)
        .where(
            TestScheduleRun.schedule_id == schedule_id,
            TestScheduleRun.status == "running",
        )
        .order_by(TestScheduleRun.id.desc())
    )
    if active:
        return {
            "schedule_id": schedule_id,
            "triggered": False,
            "reason": "already_running",
            "run_id": active.id,
            "status": "running",
        }

    run = TestScheduleRun(
        schedule_id=schedule_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    import threading

    t = threading.Thread(
        target=_execute_schedule,
        args=(schedule_id, run.id),
        daemon=True,
        name=f"schedule-trigger-{schedule_id}",
    )
    t.start()

    return {
        "schedule_id": schedule_id,
        "triggered": True,
        "run_id": run.id,
        "status": "started",
    }


def get_runs(
    db: Session,
    schedule_id: int,
    project_id: int,
    page: int = 1,
    page_size: int = 20,
):
    # Verify schedule belongs to project
    s = db.scalar(
        select(TestSchedule).where(
            TestSchedule.id == schedule_id,
            TestSchedule.project_id == project_id,
        )
    )
    if not s:
        return [], 0

    base = select(TestScheduleRun).where(
        TestScheduleRun.schedule_id == schedule_id,
    )
    total = db.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    ) or 0

    rows = db.execute(
        base.order_by(TestScheduleRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    items = []
    for r in rows:
        result = None
        try:
            result = json.loads(r.result)
        except (json.JSONDecodeError, TypeError):
            result = {}
        items.append({
            "id": r.id,
            "schedule_id": r.schedule_id,
            "status": r.status,
            "result": result,
            "error_message": r.error_message,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
        })
    return items, total
