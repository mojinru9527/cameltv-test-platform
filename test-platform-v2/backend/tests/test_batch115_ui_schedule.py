"""Batch 115（B112-3）— UI job 定时能力测试（schedule job_type=ui + 联动）。"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.project import Project
from app.models.test_plan import TestPlan
from app.models.test_schedule import TestSchedule
from app.models.ui_test import UiTestJob
from app.schemas.test_schedule import ScheduleCreate, ScheduleUpdate
from app.schemas.ui_test import UiTestJobCreate, UiTestJobUpdate
from app.services import schedule_service, ui_test_service


def _seed_project(db) -> int:
    p = Project(name="p115", code="p115")
    db.add(p)
    db.flush()
    return p.id


def _seed_plan(db, pid: int) -> int:
    tp = TestPlan(project_id=pid, name="plan115")
    db.add(tp)
    db.flush()
    return tp.id


def _seed_ui_job(db, pid: int) -> int:
    job = UiTestJob(project_id=pid, name="ui115", test_spec="specs/x.spec.ts", creator_id=1)
    db.add(job)
    db.flush()
    return job.id


def _get_schedule(db, schedule_id: int) -> TestSchedule:
    return db.scalar(select(TestSchedule).where(TestSchedule.id == schedule_id))


def test_create_ui_schedule(db_session) -> None:
    pid = _seed_project(db_session)
    job_id = _seed_ui_job(db_session, pid)
    data = ScheduleCreate(name="ui-sched", plan_id=None, job_type="ui", job_id=job_id,
                          cron_expression="0 2 * * *", enabled=False)
    r = schedule_service.create_schedule(db_session, data, creator_id=1, project_id=pid)
    assert r["job_type"] == "ui"
    assert r["job_id"] == job_id
    assert r["plan_id"] is None
    row = _get_schedule(db_session, r["id"])
    assert row.job_type == "ui" and row.job_id == job_id and row.plan_id is None


def test_create_ui_schedule_requires_job_id(db_session) -> None:
    pid = _seed_project(db_session)
    data = ScheduleCreate(name="bad-ui", plan_id=None, job_type="ui", job_id=None,
                          cron_expression="0 2 * * *", enabled=False)
    with pytest.raises(ValueError):
        schedule_service.create_schedule(db_session, data, creator_id=1, project_id=pid)


def test_create_ui_schedule_job_missing(db_session) -> None:
    pid = _seed_project(db_session)
    data = ScheduleCreate(name="missing-ui", plan_id=None, job_type="ui", job_id=99999,
                          cron_expression="0 2 * * *", enabled=False)
    with pytest.raises(ValueError):
        schedule_service.create_schedule(db_session, data, creator_id=1, project_id=pid)


def test_create_plan_schedule_requires_plan(db_session) -> None:
    pid = _seed_project(db_session)
    data = ScheduleCreate(name="bad-plan", plan_id=None, job_type="plan", job_id=None,
                          cron_expression="0 2 * * *", enabled=False)
    with pytest.raises(ValueError):
        schedule_service.create_schedule(db_session, data, creator_id=1, project_id=pid)


def test_update_schedule_switch_to_ui(db_session) -> None:
    pid = _seed_project(db_session)
    plan_id = _seed_plan(db_session, pid)
    job_id = _seed_ui_job(db_session, pid)
    data = ScheduleCreate(name="plan-sched", plan_id=plan_id, job_type="plan", job_id=None,
                          cron_expression="0 2 * * *", enabled=False)
    r = schedule_service.create_schedule(db_session, data, creator_id=1, project_id=pid)
    upd = ScheduleUpdate(job_type="ui", job_id=job_id)
    r2 = schedule_service.update_schedule(db_session, r["id"], upd, project_id=pid)
    assert r2["job_type"] == "ui" and r2["job_id"] == job_id and r2["plan_id"] is None


def test_ui_job_schedule_sync_on_create_and_disable(db_session) -> None:
    pid = _seed_project(db_session)
    data = UiTestJobCreate(name="ui-sync", test_spec="specs/x.spec.ts",
                           cron_expression="0 3 * * *", schedule_enabled=True)
    r = ui_test_service.create_job(db_session, data, creator_id=1, project_id=pid)
    job_id = r["id"]
    linked = db_session.scalar(
        select(TestSchedule).where(TestSchedule.job_type == "ui", TestSchedule.job_id == job_id)
    )
    assert linked is not None
    assert linked.enabled is True and linked.cron_expression == "0 3 * * *"
    # 关闭定时 → 联动禁用
    upd = UiTestJobUpdate(schedule_enabled=False)
    ui_test_service.update_job(db_session, job_id, upd, project_id=pid)
    linked2 = db_session.scalar(
        select(TestSchedule).where(TestSchedule.job_type == "ui", TestSchedule.job_id == job_id)
    )
    assert linked2.enabled is False


def test_ui_job_out_has_schedule_fields(db_session) -> None:
    pid = _seed_project(db_session)
    data = UiTestJobCreate(name="ui-fields", test_spec="specs/x.spec.ts",
                           cron_expression="0 4 * * *", schedule_enabled=True)
    r = ui_test_service.create_job(db_session, data, creator_id=1, project_id=pid)
    assert r["cron_expression"] == "0 4 * * *" and r["schedule_enabled"] is True