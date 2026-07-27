"""批量执行任务测试。"""
import json


class TestApiExecutionTask:
    """Task 5: 批量执行任务创建和执行。"""

    def test_create_task_with_api_cases(self, db_session):
        """从 API 用例列表创建任务应正确创建 task + items。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase

        # 创建测试用例
        case1 = TestCase(
            project_id=1, title="API Case 1", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        case2 = TestCase(
            project_id=1, title="API Case 2", case_type="api",
            api_method="POST", api_endpoint="https://httpbin.org/post",
            api_body='{"test":true}',
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add_all([case1, case2])
        db_session.commit()

        # 创建任务
        task = ApiExecutionTask(
            project_id=1, task_id="TEST-TASK-01", name="批量测试",
            total=2, creator_id=1,
        )
        db_session.add(task)
        db_session.flush()

        item1 = ApiExecutionTaskItem(task_id=task.id, case_id=case1.id)
        item2 = ApiExecutionTaskItem(task_id=task.id, case_id=case2.id)
        db_session.add_all([item1, item2])
        db_session.commit()

        # 验证
        found = db_session.query(ApiExecutionTask).filter_by(task_id="TEST-TASK-01").first()
        assert found is not None
        assert found.total == 2
        assert found.status == "pending"

        items = db_session.query(ApiExecutionTaskItem).filter_by(task_id=task.id).all()
        assert len(items) == 2
        assert items[0].case_id in (case1.id, case2.id)

    def test_task_status_transitions(self, db_session):
        """任务状态应从 pending → running → success/failed。"""
        from app.models.api_asset import ApiExecutionTask
        from datetime import datetime, timezone

        task = ApiExecutionTask(project_id=1, task_id="STATUS-TEST", name="状态测试", total=5)
        db_session.add(task)
        db_session.commit()

        assert task.status == "pending"

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(task)
        assert task.status == "running"

        task.status = "success"
        task.passed = 5
        task.finished_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(task)
        assert task.status == "success"
        assert task.passed == 5

    def test_task_item_stores_snapshot(self, db_session):
        """任务明细应正确存储请求/响应/断言快照。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

        task = ApiExecutionTask(project_id=1, task_id="SNAP-TEST", name="快照测试", total=1)
        db_session.add(task)
        db_session.flush()

        request_snap = json.dumps({"method": "GET", "url": "https://example.com/api/test"})
        response_snap = json.dumps({"status_code": 200, "response_body": {"ok": True}})
        assertion_snap = json.dumps([{"type": "status_code", "passed": True}])

        item = ApiExecutionTaskItem(
            task_id=task.id, case_id=1, status="passed", duration_ms=123.4,
            request_snapshot=request_snap,
            response_snapshot=response_snap,
            assertion_results=assertion_snap,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.status == "passed"
        assert item.duration_ms == 123.4
        assert "example.com" in item.request_snapshot
        assert item.assertion_results
        parsed = json.loads(item.assertion_results)
        assert parsed[0]["passed"] is True
