"""C55-4 lifecycle reference and execution-status contracts."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models.audit import AuditLog
from app.models.defect import Defect
from app.models.report_template import ReportTemplate
from app.models.test_case import TestCase as CaseModel
from app.models.test_plan import (
    TestExecution as ExecutionModel,
    TestPlan as PlanModel,
    TestPlanCase as PlanCaseModel,
)
from app.models.test_report import TestReport as ReportModel
from app.models.test_schedule import (
    TestSchedule as ScheduleModel,
    TestScheduleRun as ScheduleRunModel,
)


def _create_case(db_session, *, project_id: int, title: str) -> CaseModel:
    case = CaseModel(project_id=project_id, title=title)
    db_session.add(case)
    db_session.flush()
    return case


def _create_plan(db_session, *, project_id: int, name: str) -> PlanModel:
    plan = PlanModel(project_id=project_id, name=name)
    db_session.add(plan)
    db_session.flush()
    return plan


def _create_execution(
    db_session,
    *,
    plan: PlanModel,
    case: CaseModel,
    status: str = "failed",
) -> tuple[PlanCaseModel, ExecutionModel]:
    plan_case = PlanCaseModel(plan_id=plan.id, case_id=case.id)
    db_session.add(plan_case)
    db_session.flush()
    execution = ExecutionModel(plan_case_id=plan_case.id, status=status)
    db_session.add(execution)
    db_session.commit()
    return plan_case, execution


def test_execution_status_accepts_supported_value_and_rejects_invalid_value(
    client,
    auth_headers,
    db_session,
):
    case = _create_case(db_session, project_id=1, title="C55-4 执行状态用例")
    plan = _create_plan(db_session, project_id=1, name="C55-4 执行状态计划")
    plan_case = PlanCaseModel(plan_id=plan.id, case_id=case.id)
    db_session.add(plan_case)
    db_session.commit()

    accepted = client.post(
        f"/api/v1/test-plans/{plan.id}/cases/{plan_case.id}/execute",
        json={"status": "fail", "actual_result": "断言失败"},
        headers=auth_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "failed"

    rejected = client.post(
        f"/api/v1/test-plans/{plan.id}/cases/{plan_case.id}/execute",
        json={"status": "unexpected"},
        headers=auth_headers,
    )
    assert rejected.status_code == 422
    assert db_session.query(ExecutionModel).count() == 1


def test_failed_execution_can_be_triaged_into_linked_defect(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.api.v1 import defect as defect_api

    monkeypatch.setattr(
        defect_api.ingest_service,
        "ingest_defect_in_new_session",
        lambda *_args, **_kwargs: None,
    )
    case = _create_case(db_session, project_id=1, title="C55-4 失败转缺陷用例")
    plan = _create_plan(db_session, project_id=1, name="C55-4 失败转缺陷计划")
    plan_case, execution = _create_execution(
        db_session,
        plan=plan,
        case=case,
    )
    execution.actual_result = '{"status_code": 500, "error": "server returned 500"}'
    db_session.commit()

    triage = client.post(
        f"/api/v1/test-plans/{plan.id}/triage",
        headers=auth_headers,
    )
    assert triage.status_code == 200
    assert triage.json()["data"]["classified"][0]["category"] == "bug"

    drafted = client.post(
        f"/api/v1/test-plans/{plan.id}/triage/{execution.id}/draft-defect",
        headers=auth_headers,
    )
    assert drafted.status_code == 200
    draft = drafted.json()["data"]
    assert draft["case_id"] == case.id
    assert draft["execution_id"] == execution.id

    created = client.post(
        "/api/v1/defects",
        json=draft,
        headers=auth_headers,
    )
    assert created.status_code == 200
    assert created.json()["data"]["case_id"] == case.id
    assert created.json()["data"]["execution_id"] == execution.id
    assert db_session.get(PlanCaseModel, plan_case.id) is not None


def test_defect_create_accepts_matching_case_and_execution(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.api.v1 import defect as defect_api

    monkeypatch.setattr(
        defect_api.ingest_service,
        "ingest_defect_in_new_session",
        lambda *_args, **_kwargs: None,
    )
    case = _create_case(db_session, project_id=1, title="C55-4 缺陷关联用例")
    plan = _create_plan(db_session, project_id=1, name="C55-4 缺陷关联计划")
    _, execution = _create_execution(db_session, plan=plan, case=case)

    response = client.post(
        "/api/v1/defects",
        json={
            "title": "C55-4 合法关联缺陷",
            "case_id": case.id,
            "execution_id": execution.id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["case_id"] == case.id
    assert response.json()["data"]["execution_id"] == execution.id


def test_defect_create_rejects_foreign_case_and_execution(
    client,
    auth_headers,
    db_session,
):
    foreign_case = _create_case(db_session, project_id=2, title="其他项目用例")
    foreign_plan = _create_plan(db_session, project_id=2, name="其他项目计划")
    _, foreign_execution = _create_execution(
        db_session,
        plan=foreign_plan,
        case=foreign_case,
    )

    for payload in (
        {"title": "跨项目用例缺陷", "case_id": foreign_case.id},
        {"title": "跨项目执行缺陷", "execution_id": foreign_execution.id},
    ):
        response = client.post("/api/v1/defects", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["code"] == 1

    assert db_session.query(Defect).count() == 0


def test_defect_create_rejects_execution_case_mismatch(
    client,
    auth_headers,
    db_session,
):
    execution_case = _create_case(db_session, project_id=1, title="执行关联用例")
    other_case = _create_case(db_session, project_id=1, title="错误关联用例")
    plan = _create_plan(db_session, project_id=1, name="关联一致性计划")
    _, execution = _create_execution(
        db_session,
        plan=plan,
        case=execution_case,
    )

    response = client.post(
        "/api/v1/defects",
        json={
            "title": "执行与用例不一致",
            "case_id": other_case.id,
            "execution_id": execution.id,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["code"] == 1
    assert db_session.query(Defect).count() == 0


def test_defect_update_rejects_foreign_or_mismatched_references(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.api.v1 import defect as defect_api

    monkeypatch.setattr(
        defect_api.ingest_service,
        "ingest_defect_in_new_session",
        lambda *_args, **_kwargs: None,
    )
    own_case = _create_case(db_session, project_id=1, title="当前项目用例")
    other_own_case = _create_case(db_session, project_id=1, title="当前项目其他用例")
    own_plan = _create_plan(db_session, project_id=1, name="当前项目计划")
    _, own_execution = _create_execution(
        db_session,
        plan=own_plan,
        case=own_case,
    )
    foreign_case = _create_case(db_session, project_id=2, title="其他项目用例")
    foreign_plan = _create_plan(db_session, project_id=2, name="其他项目计划")
    _, foreign_execution = _create_execution(
        db_session,
        plan=foreign_plan,
        case=foreign_case,
    )

    created = client.post(
        "/api/v1/defects",
        json={
            "title": "C55-4 待更新缺陷",
            "case_id": own_case.id,
            "execution_id": own_execution.id,
        },
        headers=auth_headers,
    )
    defect_id = created.json()["data"]["id"]

    for payload in (
        {"execution_id": foreign_execution.id},
        {"case_id": other_own_case.id},
    ):
        rejected = client.put(
            f"/api/v1/defects/{defect_id}",
            json=payload,
            headers=auth_headers,
        )
        assert rejected.status_code == 200
        assert rejected.json()["code"] == 1

    db_session.expire_all()
    defect = db_session.get(Defect, defect_id)
    assert defect is not None
    assert defect.case_id == own_case.id
    assert defect.execution_id == own_execution.id


def test_schedule_create_and_update_enforce_plan_project(
    client,
    auth_headers,
    db_session,
):
    own_plan = _create_plan(db_session, project_id=1, name="当前项目计划")
    foreign_plan = _create_plan(db_session, project_id=2, name="其他项目计划")
    db_session.commit()

    created = client.post(
        "/api/v1/schedules",
        json={
            "name": "C55-4 合法调度",
            "plan_id": own_plan.id,
            "cron_expression": "0 9 * * 1-5",
            "enabled": False,
        },
        headers=auth_headers,
    )
    assert created.status_code == 200
    schedule_id = created.json()["data"]["id"]

    rejected_create = client.post(
        "/api/v1/schedules",
        json={
            "name": "C55-4 跨项目调度",
            "plan_id": foreign_plan.id,
            "cron_expression": "0 9 * * 1-5",
            "enabled": False,
        },
        headers=auth_headers,
    )
    assert rejected_create.status_code == 200
    assert rejected_create.json()["code"] == 1

    rejected_update = client.put(
        f"/api/v1/schedules/{schedule_id}",
        json={"plan_id": foreign_plan.id},
        headers=auth_headers,
    )
    assert rejected_update.status_code == 200
    assert rejected_update.json()["code"] == 1
    db_session.expire_all()
    schedule = db_session.get(ScheduleModel, schedule_id)
    assert schedule is not None
    assert schedule.plan_id == own_plan.id
    assert db_session.query(ScheduleModel).count() == 1


def test_schedule_run_executes_plan_and_records_non_pending_result(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.core import db as db_core
    from app.core.scheduler import _execute_schedule

    case = _create_case(db_session, project_id=1, title="C55-4 调度执行用例")
    plan = _create_plan(db_session, project_id=1, name="C55-4 调度执行计划")
    plan_case = PlanCaseModel(plan_id=plan.id, case_id=case.id)
    db_session.add(plan_case)
    db_session.commit()

    created = client.post(
        "/api/v1/schedules",
        json={
            "name": "C55-4 真实执行调度",
            "plan_id": plan.id,
            "cron_expression": "0 9 * * 1-5",
            "enabled": False,
        },
        headers=auth_headers,
    )
    schedule_id = created.json()["data"]["id"]

    isolated_session = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(db_core, "SessionLocal", isolated_session)
    result = _execute_schedule(schedule_id)

    assert result["triggered"] is True
    assert result["result"]["pending"] == 0
    assert result["result"]["skip"] == 1
    db_session.expire_all()
    execution = db_session.scalar(
        select(ExecutionModel).where(ExecutionModel.plan_case_id == plan_case.id),
    )
    assert execution is not None
    assert execution.status == "skipped"
    run = db_session.scalar(
        select(ScheduleRunModel).where(ScheduleRunModel.schedule_id == schedule_id),
    )
    assert run is not None
    assert run.status == "passed"


def test_schedule_run_rejects_duplicate_while_running(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.core import db as db_core
    from app.core.scheduler import _execute_schedule

    plan = _create_plan(db_session, project_id=1, name="C55-4 幂等调度计划")
    db_session.commit()
    created = client.post(
        "/api/v1/schedules",
        json={
            "name": "C55-4 幂等调度",
            "plan_id": plan.id,
            "cron_expression": "0 9 * * 1-5",
            "enabled": False,
        },
        headers=auth_headers,
    )
    schedule_id = created.json()["data"]["id"]
    active = ScheduleRunModel(schedule_id=schedule_id, status="running")
    db_session.add(active)
    db_session.commit()

    isolated_session = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(db_core, "SessionLocal", isolated_session)
    result = _execute_schedule(schedule_id)

    assert result == {
        "triggered": False,
        "reason": "already_running",
        "run_id": active.id,
    }
    assert db_session.query(ScheduleRunModel).count() == 1
    assert db_session.query(ExecutionModel).count() == 0


def test_schedule_run_persists_failed_terminal_state(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.core import db as db_core
    from app.core.scheduler import _execute_schedule
    from app.services import test_plan_service

    plan = _create_plan(db_session, project_id=1, name="C55-4 失败调度计划")
    db_session.commit()
    created = client.post(
        "/api/v1/schedules",
        json={
            "name": "C55-4 失败调度",
            "plan_id": plan.id,
            "cron_expression": "0 9 * * 1-5",
            "enabled": False,
        },
        headers=auth_headers,
    )
    schedule_id = created.json()["data"]["id"]

    isolated_session = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(db_core, "SessionLocal", isolated_session)
    monkeypatch.setattr(
        test_plan_service,
        "execute_all_cases",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = _execute_schedule(schedule_id)

    assert result["triggered"] is False
    assert result["reason"] == "execution_failed"
    db_session.expire_all()
    run = db_session.scalar(
        select(ScheduleRunModel).where(ScheduleRunModel.schedule_id == schedule_id),
    )
    assert run is not None
    assert run.status == "failed"
    assert run.error_message == "boom"


def test_report_create_enforces_template_project(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    from app.api.v1 import report as report_api

    monkeypatch.setattr(
        report_api,
        "_run_notify_in_new_session",
        lambda *_args, **_kwargs: None,
    )
    plan = _create_plan(db_session, project_id=1, name="C55-4 报告计划")
    own_template = ReportTemplate(project_id=1, name="当前项目模板")
    foreign_template = ReportTemplate(project_id=2, name="其他项目模板")
    db_session.add_all([own_template, foreign_template])
    db_session.commit()

    accepted = client.post(
        "/api/v1/reports",
        json={
            "plan_id": plan.id,
            "name": "C55-4 合法报告",
            "template_id": own_template.id,
        },
        headers=auth_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["template_id"] == own_template.id

    rejected = client.post(
        "/api/v1/reports",
        json={
            "plan_id": plan.id,
            "name": "C55-4 跨项目模板报告",
            "template_id": foreign_template.id,
        },
        headers=auth_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["code"] == 1
    assert db_session.query(ReportModel).count() == 1


def test_lifecycle_mutations_persist_audit_after_request_transaction_ends(
    client,
    auth_headers,
    db_session,
    monkeypatch,
):
    """The request dependency closes without committing, so audits must commit."""
    from app.api.v1 import defect as defect_api

    monkeypatch.setattr(
        defect_api.ingest_service,
        "ingest_defect_in_new_session",
        lambda *_args, **_kwargs: None,
    )

    created_plan = client.post(
        "/api/v1/test-plans",
        json={"name": "C55-4 审计持久化计划"},
        headers=auth_headers,
    )
    assert created_plan.status_code == 200

    created_defect = client.post(
        "/api/v1/defects",
        json={"title": "C55-4 审计持久化缺陷"},
        headers=auth_headers,
    )
    assert created_defect.status_code == 200

    # Simulate get_db() ending the request and rolling back any transaction
    # that was merely flushed but never committed.
    db_session.rollback()
    actions = set(
        db_session.scalars(
            select(AuditLog.action).where(
                AuditLog.action.in_(("plan:create", "defect:create")),
            ),
        ).all(),
    )
    assert actions == {"plan:create", "defect:create"}


def test_notification_channel_audit_persists_after_request_transaction_ends(
    client,
    auth_headers,
    db_session,
):
    created = client.post(
        "/api/v1/notify/channels",
        json={
            "name": "C55-4 禁用测试通知",
            "provider": "generic",
            "webhook_url": "",
            "enabled": False,
            "events": ["plan_done"],
        },
        headers=auth_headers,
    )
    assert created.status_code == 200

    db_session.rollback()
    assert db_session.scalar(
        select(AuditLog).where(AuditLog.action == "notify:channel:create"),
    ) is not None
