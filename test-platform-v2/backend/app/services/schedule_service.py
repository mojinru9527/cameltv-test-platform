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
            "cron_expression": s.cron_expression,
            "enabled": s.enabled,
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
        "cron_expression": s.cron_expression,
        "enabled": s.enabled,
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
    # Validate plan
    plan = db.scalar(
        select(TestPlan).where(
            TestPlan.id == data.plan_id,
            TestPlan.project_id == project_id,
        )
    )
    if not plan:
        raise ValueError("计划不存在")

    next_run = _compute_next_run(data.cron_expression)

    s = TestSchedule(
        project_id=project_id,
        name=data.name,
        description=data.description,
        plan_id=data.plan_id,
        cron_expression=data.cron_expression,
        enabled=data.enabled,
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
        "plan_name": plan.name,
        "cron_expression": s.cron_expression,
        "enabled": s.enabled,
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
    if data.plan_id is not None:
        s.plan_id = data.plan_id
        changed = True
    if data.cron_expression is not None:
        s.cron_expression = data.cron_expression
        cron_changed = True
        changed = True
    if data.enabled is not None:
        # toggle
        if data.enabled != s.enabled:
            toggle_schedule_job(s.id, data.enabled, s.cron_expression)
        s.enabled = data.enabled
        changed = True

    if cron_changed and s.enabled:
        # Re-register with new cron
        add_schedule_job(s.id, s.cron_expression)
        s.next_run = _compute_next_run(s.cron_expression)

    if changed:
        db.flush()

    plan = db.scalar(select(TestPlan).where(TestPlan.id == s.plan_id))
    return {
        "id": s.id,
        "project_id": s.project_id,
        "name": s.name,
        "description": s.description,
        "plan_id": s.plan_id,
        "plan_name": plan.name if plan else "",
        "cron_expression": s.cron_expression,
        "enabled": s.enabled,
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
    """Manually trigger a schedule. Creates a run record and executes."""
    s = db.scalar(
        select(TestSchedule).where(
            TestSchedule.id == schedule_id,
            TestSchedule.project_id == project_id,
        )
    )
    if not s:
        raise ValueError("调度不存在")

    db.commit()  # release session state before background execution
    _execute_schedule(schedule_id)

    return {"triggered": True, "schedule_id": schedule_id}


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
