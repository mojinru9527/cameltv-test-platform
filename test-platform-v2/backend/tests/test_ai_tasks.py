"""Batch 120 — C117-2 AI 任务 DB 队列（多 worker 认领）测试。"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from unittest.mock import patch


def _task(db_session, task_id: str = "ai-test-1", status: str = "pending",
          locked_at=None, task_type: str = "generate", document_id: int = 5):
    from app.models.ai_task import AiTask

    row = AiTask(
        id=task_id,
        task_type=task_type,
        project_id=1,
        document_id=document_id,
        status=status,
        progress=0 if status == "pending" else 5,
        result_json="null",
        error="",
        locked_at=locked_at,
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestClaim:
    def test_claim_only_pending(self, db_session):
        from app.services.ai_tasks import claim_next_task

        _task(db_session, "t1")
        _task(db_session, "t2", status="running")
        claimed = claim_next_task(db_session)
        assert claimed is not None and claimed.id == "t1"
        assert claimed.status == "running"
        assert claimed.locked_at is not None
        assert claim_next_task(db_session) is None

    def test_claim_stale_lock(self, db_session):
        from app.services.ai_tasks import claim_next_task

        _task(db_session, "t1", locked_at=datetime.utcnow() - timedelta(minutes=10))
        claimed = claim_next_task(db_session)
        assert claimed is not None and claimed.id == "t1"

    def test_claim_fresh_lock_skipped(self, db_session):
        from app.services.ai_tasks import claim_next_task

        _task(db_session, "t1", locked_at=datetime.utcnow())
        assert claim_next_task(db_session) is None


class TestExecute:
    def test_execute_success_writes_result(self, db_session):
        from app.services.ai_tasks import claim_next_task, execute_task

        _task(db_session, "t1")
        task = claim_next_task(db_session)
        execute_task(db_session, task, dispatch=lambda task_type, doc_id, db: {"ok": True, "doc": doc_id})
        db_session.refresh(task)
        assert task.status == "done"
        assert task.progress == 100
        assert task.locked_at is None
        assert task.finished_at is not None
        assert json.loads(task.result_json) == {"ok": True, "doc": 5}

    def test_execute_failure_writes_error(self, db_session):
        from app.services.ai_tasks import claim_next_task, execute_task

        _task(db_session, "t1")
        task = claim_next_task(db_session)

        def boom(task_type, doc_id, db):
            raise RuntimeError("模拟失败")

        execute_task(db_session, task, dispatch=boom)
        db_session.refresh(task)
        assert task.status == "failed"
        assert "模拟失败" in task.error
        assert task.locked_at is None


class TestWorkerLifecycle:
    def test_shutdown_joins_worker_thread(self):
        from app.services import ai_tasks

        ai_tasks.shutdown_worker()

        def wait_for_shutdown():
            ai_tasks._shutdown_event.wait(timeout=1)

        with patch.object(ai_tasks, "_worker_loop", wait_for_shutdown):
            ai_tasks.ensure_worker_running()
            thread = ai_tasks._worker_thread
            assert isinstance(thread, threading.Thread)
            assert thread.is_alive()
            ai_tasks.shutdown_worker(timeout=1)

        assert not thread.is_alive()
        assert ai_tasks._worker_thread is None
