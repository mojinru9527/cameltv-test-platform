"""Batch 186（C182-1）— 执行记录单一事实源测试。

计划 API 执行只写 test_execution，不再双写 api_execution_task/items；
历史 plan 任务保留可读；手动批量任务（manual/retry_failed）不受影响。
"""
from __future__ import annotations

from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
from app.models.environment import Environment
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase


def _plan_with_api_cases(db_session, n: int = 3):
    plan = TestPlan(project_id=1, name="C1821-PLAN", status="draft")
    db_session.add(plan)
    db_session.commit()
    pcs = []
    for i in range(n):
        from app.models.test_case import TestCase
        case = TestCase(
            project_id=1, title=f"C1821-CASE-{i}", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.flush()
        pc = TestPlanCase(plan_id=plan.id, case_id=case.id)
        db_session.add(pc)
        pcs.append(pc)
    db_session.commit()
    return plan, pcs


class TestSingleFactSource:
    def _env(self, db_session):
        env = Environment(
            project_id=1, name="C1821-ENV", env_type="test",
            base_url="https://httpbin.org",
        )
        db_session.add(env)
        db_session.commit()
        return env

    def test_execute_all_creates_only_test_execution(self, db_session, monkeypatch):
        """execute_all：API 用例仅落 test_execution；无 plan 任务快照/互指。"""

        from app.services import test_plan_service

        plan, pcs = _plan_with_api_cases(db_session, 3)
        env = self._env(db_session)
        monkeypatch.setattr(
            "app.services.api_execution_service.execute_api_case",
            lambda *a, **k: {"all_pass": True, "status_code": 200, "assertions": []},
        )

        test_plan_service.execute_all_cases(
            db_session, plan.id, executor_id=1, environment_id=env.id,
            auto_ui=False, project_id=1,
        )

        exec_count = (
            db_session.query(TestExecution)
            .filter_by(plan_case_id=pcs[0].id)
            .count()
        )
        assert exec_count == 1
        plan_task_count = (
            db_session.query(ApiExecutionTask).filter_by(trigger_type="plan").count()
        )
        assert plan_task_count == 0
        assert db_session.query(ApiExecutionTaskItem).count() == 0
        exec_row = (
            db_session.query(TestExecution)
            .filter_by(plan_case_id=pcs[0].id)
            .first()
        )
        assert exec_row.api_task_id is None

    def test_auto_execute_creates_only_test_execution(self, db_session, monkeypatch):
        """auto_execute_api_cases：同样只写 test_execution。"""
        from app.services import test_plan_service

        plan, pcs = _plan_with_api_cases(db_session, 2)
        env = self._env(db_session)
        monkeypatch.setattr(
            "app.services.api_execution_service.execute_api_case",
            lambda *a, **k: (
                {"all_pass": False, "status_code": 500,
                 "assertions": [], "error": "boom"}
            ),
        )

        result = test_plan_service.auto_execute_api_cases(
            db_session, plan.id, executor_id=1, environment_id=env.id, project_id=1,
        )
        assert result["failed"] == 2
        assert db_session.query(TestExecution).count() == 2
        plan_task_count = (
            db_session.query(ApiExecutionTask).filter_by(trigger_type="plan").count()
        )
        assert plan_task_count == 0
        assert db_session.query(ApiExecutionTaskItem).count() == 0

    def test_historical_plan_tasks_remain_readable(self, db_session):
        """存量 plan 任务保留（可读、含 items），不受新行为影响。"""
        task = ApiExecutionTask(
            project_id=1, task_id="PLAN-HISTORY", name="计划执行-历史",
            status="success", trigger_type="plan", total=1, passed=1,
        )
        db_session.add(task)
        db_session.flush()
        db_session.add(
            ApiExecutionTaskItem(task_id=task.id, case_id=1, status="passed")
        )
        db_session.commit()

        rows = db_session.query(ApiExecutionTask).filter_by(trigger_type="plan").all()
        assert len(rows) == 1
        items = db_session.query(ApiExecutionTaskItem).filter_by(task_id=task.id).all()
        assert len(items) == 1  # 历史 items 保留可读

    def test_manual_batch_task_still_created(self, db_session):
        """手动批量任务（非 plan 路径）不受影响。"""
        from app.services.api_execution_service import create_execution_task

        task = create_execution_task(
            db_session, project_id=1, task_id="MANUAL-1", name="手动批量",
            environment_id=None, service_id=None, status="pending",
            total=1, creator_id=1, confirm_prod=False, trigger_type="manual",
        )
        db_session.commit()
        assert task.trigger_type == "manual"
