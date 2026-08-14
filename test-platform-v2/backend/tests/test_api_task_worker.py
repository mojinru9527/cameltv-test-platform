"""Phase P0 Task 2: Persistent API Task Worker 测试。

测试范围:
- claim_next_task: 认领 pending 任务、project 过滤、无任务返回 None
- execute_task: cancel_requested 后跳过剩余 item
- API: create_task 立即返回不执行、cancel_task 设置 cancel_requested、retry-failed 创建新任务
"""
from __future__ import annotations

import threading
from unittest.mock import patch


class TestApiTaskWorkerLifecycle:
    """Worker 生命周期必须和应用生命周期保持一致。"""

    def test_shutdown_joins_processor_thread(self):
        """关闭处理器后不应留下访问旧测试数据库的守护线程。

        Batch 181：循环骨架收敛到 app.core.task_queue.QueueWorkerLoop，
        测试改为验证统一循环的 start/shutdown 生命周期。
        """
        from app.services import api_task_worker

        api_task_worker.shutdown_processor()

        def wait_for_shutdown():
            api_task_worker._loop._stop.wait(timeout=1)

        with patch.object(api_task_worker._loop, "_loop", wait_for_shutdown):
            api_task_worker.ensure_processor_running()
            thread = api_task_worker._loop._thread
            assert isinstance(thread, threading.Thread)
            assert thread.is_alive()

            api_task_worker.shutdown_processor(timeout=1)

        assert not thread.is_alive()
        assert api_task_worker._loop._thread is None

    def test_app_lifespan_shuts_down_api_task_worker(self):
        """FastAPI TestClient 退出时必须关闭 API 任务处理器。"""
        from fastapi.testclient import TestClient

        from app.main import app

        with patch(
            "app.services.api_task_worker.shutdown_processor",
        ) as shutdown_api_task_worker:
            with TestClient(app):
                pass

        shutdown_api_task_worker.assert_called_once_with()


class TestApiTaskWorkerClaim:
    """Worker claim_next_task 单元测试。"""

    def test_claims_only_pending_tasks(self, db_session):
        """Worker 只认领 pending 任务，设置 status=running 和 locked_by。"""
        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import claim_next_task

        pending = ApiExecutionTask(
            project_id=1, task_id="T-PENDING", name="Pending",
            total=2, status="pending",
        )
        running = ApiExecutionTask(
            project_id=1, task_id="T-RUNNING", name="Running",
            total=2, status="running",
        )
        db_session.add_all([pending, running])
        db_session.commit()

        claimed = claim_next_task(db_session, worker_id="test-worker")
        assert claimed is not None
        assert claimed.id == pending.id
        assert claimed.status == "running"
        assert claimed.locked_by == "test-worker"
        assert claimed.locked_at is not None

    def test_respects_project_id_filter(self, db_session):
        """Worker 认领时按 project_id 过滤。"""
        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import claim_next_task

        p1 = ApiExecutionTask(
            project_id=1, task_id="T-P1", name="P1", total=1, status="pending",
        )
        p2 = ApiExecutionTask(
            project_id=2, task_id="T-P2", name="P2", total=1, status="pending",
        )
        db_session.add_all([p1, p2])
        db_session.commit()

        claimed = claim_next_task(db_session, worker_id="w", project_id=2)
        assert claimed is not None
        assert claimed.project_id == 2
        assert claimed.task_id == "T-P2"

    def test_returns_none_when_no_pending(self, db_session):
        """无 pending 任务时返回 None。"""
        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import claim_next_task

        t = ApiExecutionTask(
            project_id=1, task_id="T-SUCCESS", name="Done",
            total=1, status="success",
        )
        db_session.add(t)
        db_session.commit()

        asserted = claim_next_task(db_session, worker_id="w")
        assert asserted is None

    def test_sets_started_at_on_first_claim(self, db_session):
        """首次认领应填充 started_at。"""
        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import claim_next_task

        t = ApiExecutionTask(
            project_id=1, task_id="T-START", name="Start Test",
            total=1, status="pending",
        )
        db_session.add(t)
        db_session.commit()
        assert t.started_at is None

        claimed = claim_next_task(db_session, worker_id="w")
        assert claimed.started_at is not None

    def test_claim_does_not_touch_other_workers_running_task(self, db_session):
        """Batch 174（FIX-173-P0-01/02）：running 任务（其他 worker 持有）不得被再次认领，
        双 Worker/多副本重复执行回归防护。"""
        from datetime import datetime, timedelta, timezone

        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import claim_next_task

        running = ApiExecutionTask(
            project_id=1, task_id="T-HELD", name="Held By Another",
            total=1, status="running", locked_by="worker-A",
            locked_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db_session.add(running)
        db_session.commit()

        claimed = claim_next_task(db_session, worker_id="worker-B")
        assert claimed is None

    def test_reap_stale_api_tasks_recovers_zombie(self, db_session):
        """Batch 174（FIX-173-P0-01）：锁定超时的 running 任务被回收为 failed，
        僵尸任务（永久卡 running 无结果）不再存在。"""
        from datetime import datetime, timedelta, timezone

        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import reap_stale_api_tasks

        stale = ApiExecutionTask(
            project_id=1, task_id="T-ZOMBIE", name="Zombie",
            total=1, status="running", locked_by="dead-worker",
            locked_at=datetime.now(timezone.utc) - timedelta(hours=2),
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        fresh = ApiExecutionTask(
            project_id=1, task_id="T-FRESH", name="Fresh",
            total=1, status="running", locked_by="live-worker",
            locked_at=datetime.now(timezone.utc),
        )
        db_session.add_all([stale, fresh])
        db_session.commit()

        reaped = reap_stale_api_tasks(db_session)
        assert reaped == 1

        db_session.refresh(stale)
        db_session.refresh(fresh)
        assert stale.status == "failed"
        assert stale.locked_by == ""
        # 注：ApiExecutionTask 无 error_message 列（历史代码仅设瞬态属性），
        # Batch 181 起统一回收原语不再伪造未落库字段，此处不断言该属性。
        assert fresh.status == "running"  # 非失联任务不受影响

    def test_claim_recovers_stale_before_claiming(self, db_session):
        """Batch 174：认领前先回收僵尸任务，后续 pending 任务可正常认领。"""
        from datetime import datetime, timedelta, timezone

        from app.models.api_asset import ApiExecutionTask
        from app.services.api_task_worker import claim_next_task

        zombie = ApiExecutionTask(
            project_id=1, task_id="T-ZB2", name="Zombie2",
            total=1, status="running", locked_by="dead",
            locked_at=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        pending = ApiExecutionTask(
            project_id=1, task_id="T-NEXT", name="Next",
            total=1, status="pending",
        )
        db_session.add_all([zombie, pending])
        db_session.commit()

        claimed = claim_next_task(db_session, worker_id="w")
        assert claimed is not None
        assert claimed.task_id == "T-NEXT"

        db_session.refresh(zombie)
        assert zombie.status == "failed"


class TestTaskWorkerNoApiBranch:
    """Batch 174（FIX-173-P0-01）：task_worker（APScheduler 轮询）不再处理 API 批量任务，
    消除与 api_task_worker 守护线程的双 Worker 竞态。"""

    def test_poll_and_execute_does_not_process_api_tasks(self):
        """poll_and_execute 不应再调用任何 API 任务认领逻辑。"""
        from unittest.mock import MagicMock, patch

        from app.services import task_worker

        with patch("app.services.task_worker._process_ui_runs") as mock_ui, \
             patch("app.services.lanhu_evidence.worker.poll_and_execute_evidence_jobs") as mock_evidence, \
             patch("app.services.api_task_worker.claim_next_task") as mock_claim:
            task_worker.poll_and_execute()

        mock_ui.assert_called_once()
        mock_evidence.assert_called_once()
        mock_claim.assert_not_called()  # API 认领必须不再被 APScheduler 轮询触发

    def test_task_worker_has_no_api_semaphore(self):
        """_semaphore_api 与 API 处理函数必须已移除。"""
        from app.services import task_worker

        assert not hasattr(task_worker, "_semaphore_api")
        assert not hasattr(task_worker, "_process_api_tasks")
        assert not hasattr(task_worker, "_run_api_task")


class TestApiTaskWorkerExecute:
    """Worker execute_task 测试。"""

    def test_execute_task_backfills_case_last_response(self, db_session):
        """Batch 111（C110-3/C103-7）：执行后必须回填 TestCase.last_response_json/last_run_status。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase
        from app.services import api_task_worker

        case = TestCase(
            project_id=1, title="Backfill Case", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.commit()

        task = ApiExecutionTask(
            project_id=1, task_id="T-BACKFILL", name="Backfill Test",
            total=1, status="pending",
        )
        db_session.add(task)
        db_session.flush()
        db_session.add(ApiExecutionTaskItem(task_id=task.id, case_id=case.id, status="pending"))
        db_session.commit()

        fake_result = {
            "all_pass": True,
            "duration_ms": 12,
            "status_code": 200,
            "response_headers": {"content-type": "application/json"},
            "raw_body": '{"ok":true}',
            "assertions": [],
        }

        class _NoCloseSession:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def close(self):
                pass

        wrapped = _NoCloseSession(db_session)
        with patch("app.services.api_task_worker.SessionLocal", return_value=wrapped), \
             patch("app.services.api_execution_service.execute_api_case", return_value=fake_result):
            api_task_worker.execute_task(task.id, project_id=1, worker_id="test-worker")

        db_session.refresh(case)
        assert case.last_run_status == "passed"
        assert case.last_response_json is not None
        assert '"status_code": 200' in case.last_response_json

    def test_cancel_requested_skips_all_pending_items(self, db_session):
        """cancel_requested=True 时，所有 pending item 应被标记为 skipped，任务状态为 cancelled。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.services.api_task_worker import execute_task

        # 创建无用例的纯模型测试（不需要真实用例，因为 cancel_requested 会让 worker 提前退出）
        task = ApiExecutionTask(
            project_id=1, task_id="T-CANCEL", name="Cancel Test",
            total=2, status="pending", cancel_requested=True,
        )
        db_session.add(task)
        db_session.flush()

        item1 = ApiExecutionTaskItem(task_id=task.id, case_id=1, status="pending")
        item2 = ApiExecutionTaskItem(task_id=task.id, case_id=2, status="pending")
        db_session.add_all([item1, item2])
        db_session.commit()

        # Patch SessionLocal — 返回 db_session 的浅层副本（同 engine）
        # execute_task 内部会调用 db.close()，我们让 close 变成空操作
        class _NoCloseSession:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def close(self):
                pass  # 不关闭测试 session

        wrapped = _NoCloseSession(db_session)
        with patch("app.services.api_task_worker.SessionLocal", return_value=wrapped):
            execute_task(task.id, project_id=1, worker_id="test-worker")

        db_session.refresh(task)
        assert task.status == "cancelled"
        assert task.skipped == 2

        db_session.refresh(item1)
        db_session.refresh(item2)
        assert item1.status == "skipped"
        assert item1.error_message == "任务已取消"
        assert item2.status == "skipped"

    def test_handles_missing_task_gracefully(self, db_session):
        """不存在的 task_id 不该崩溃。"""
        from app.services.api_task_worker import execute_task

        # 应该不抛异常
        execute_task(99999, project_id=1, worker_id="test-worker")


class TestApiTaskWorkerApi:
    """通过 API 端点验证 worker 集成行为。"""

    def test_create_task_returns_immediately_status_pending(self, client, auth_headers, db_session):
        """POST /apitest/tasks 应立即返回，任务状态为 pending（不执行）。"""
        from app.models.test_case import TestCase

        case = TestCase(
            project_id=1, title="Immediate Test", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.commit()

        resp = client.post("/api/v1/apitest/tasks", headers=auth_headers, json={
            "name": "立即返回测试",
            "case_ids": [case.id],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "pending"
        assert data["total"] == 1
        assert data["started_at"] is None  # 尚未开始执行

    def test_cancel_task_sets_cancel_requested(self, client, auth_headers, db_session):
        """POST /apitest/tasks/{id}/cancel 应设置 cancel_requested=True。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase

        case = TestCase(
            project_id=1, title="Cancel API Test", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.commit()

        task = ApiExecutionTask(
            project_id=1, task_id="T-API-CANCEL", name="API Cancel",
            total=1, status="pending",
        )
        db_session.add(task)
        db_session.flush()
        db_session.add(ApiExecutionTaskItem(task_id=task.id, case_id=case.id))
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelling"

        db_session.refresh(task)
        assert task.cancel_requested is True

    def test_cancel_rejects_non_pending_running(self, client, auth_headers, db_session):
        """只能取消 pending 或 running 状态的任务。"""
        from app.models.api_asset import ApiExecutionTask

        task = ApiExecutionTask(
            project_id=1, task_id="T-DONE", name="Done",
            total=1, status="success",
        )
        db_session.add(task)
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_retry_failed_creates_new_task_with_failed_cases(self, client, auth_headers, db_session):
        """POST /apitest/tasks/{id}/retry-failed 应创建新任务（trigger_type=retry_failed），仅含失败 case。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase

        case1 = TestCase(
            project_id=1, title="Retry Case 1", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        case2 = TestCase(
            project_id=1, title="Retry Case 2", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add_all([case1, case2])
        db_session.commit()

        task = ApiExecutionTask(
            project_id=1, task_id="T-RETRY-SRC", name="Retry Source",
            total=2, status="success", passed=1, failed=1,
        )
        db_session.add(task)
        db_session.flush()

        db_session.add(ApiExecutionTaskItem(
            task_id=task.id, case_id=case1.id, status="passed",
        ))
        db_session.add(ApiExecutionTaskItem(
            task_id=task.id, case_id=case2.id, status="failed",
            error_message="请求超时",
        ))
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/retry-failed",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["retry_count"] == 1
        assert "new_task_id" in data
        new_task_id = data["new_task_id"]

        # 验证新任务
        from app.models.api_asset import ApiExecutionTask
        new_task = db_session.get(ApiExecutionTask, new_task_id)
        assert new_task is not None
        assert new_task.trigger_type == "retry_failed"
        assert new_task.total == 1
        assert new_task.status == "pending"

        # 验证新任务的 item 只包含失败用例
        items = db_session.query(ApiExecutionTaskItem).filter_by(task_id=new_task.id).all()
        assert len(items) == 1
        assert items[0].case_id == case2.id

    def test_retry_failed_rejects_empty_failed(self, client, auth_headers, db_session):
        """无失败项时应返回 400。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase

        case = TestCase(
            project_id=1, title="All Pass", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.commit()

        task = ApiExecutionTask(
            project_id=1, task_id="T-ALL-PASS", name="All Pass",
            total=1, status="success", passed=1,
        )
        db_session.add(task)
        db_session.flush()
        db_session.add(ApiExecutionTaskItem(
            task_id=task.id, case_id=case.id, status="passed",
        ))
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/retry-failed",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_retry_failed_enforces_project_isolation(self, client, auth_headers, db_session):
        """retry-failed 应拒绝跨项目访问。"""
        from app.models.api_asset import ApiExecutionTask

        task = ApiExecutionTask(
            project_id=999, task_id="T-OTHER", name="Other Project",
            total=1, status="failed",
        )
        db_session.add(task)
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/retry-failed",
            headers=auth_headers,  # X-Project-Id: 1
        )
        assert resp.status_code == 403

    def test_cancel_enforces_project_isolation(self, client, auth_headers, db_session):
        """cancel 应拒绝跨项目访问。"""
        from app.models.api_asset import ApiExecutionTask

        task = ApiExecutionTask(
            project_id=999, task_id="T-OTHER-C", name="Other Cancel",
            total=1, status="pending",
        )
        db_session.add(task)
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_retry_failed_deduplicates_case_ids(self, client, auth_headers, db_session):
        """同一 case 多次失败只应在新任务中出现一次。"""
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
        from app.models.test_case import TestCase

        case = TestCase(
            project_id=1, title="Dup Case", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(case)
        db_session.commit()

        task = ApiExecutionTask(
            project_id=1, task_id="T-DUP", name="Dup Test",
            total=2, status="failed", failed=2,
        )
        db_session.add(task)
        db_session.flush()

        # 同一 case 两次失败（参数化场景可能发生）
        db_session.add(ApiExecutionTaskItem(
            task_id=task.id, case_id=case.id, status="failed",
        ))
        db_session.add(ApiExecutionTaskItem(
            task_id=task.id, case_id=case.id, status="failed",
        ))
        db_session.commit()

        resp = client.post(
            f"/api/v1/apitest/tasks/{task.id}/retry-failed",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["retry_count"] == 1  # 去重后只有 1 个 case
