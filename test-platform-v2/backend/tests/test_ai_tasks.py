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
        execute_task(db_session, task, dispatch=lambda task_type, doc_id, db, project_id=0: {"ok": True, "doc": doc_id, "pid": project_id})
        db_session.refresh(task)
        assert task.status == "done"
        assert task.progress == 100
        assert task.locked_at is None
        assert task.finished_at is not None
        assert json.loads(task.result_json) == {"ok": True, "doc": 5, "pid": 1}

    def test_execute_failure_writes_error(self, db_session):
        from app.services.ai_tasks import claim_next_task, execute_task

        _task(db_session, "t1")
        task = claim_next_task(db_session)

        def boom(task_type, doc_id, db, project_id=0):
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


class TestMultiWorkerClaimRace:
    """C120-2：两个独立会话（worker）认领同一任务，仅一个成功。"""

    def test_two_sessions_no_double_claim(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.core.db import Base
        from app.models.ai_task import AiTask
        from app.services.ai_tasks import claim_next_task

        db_path = tmp_path / "race.sqlite"
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionFactory = sessionmaker(bind=engine)

        s0 = SessionFactory()
        s0.add(AiTask(id="race-1", task_type="generate", project_id=1, document_id=5,
                      status="pending", progress=0, result_json="null", error=""))
        s0.commit()
        s0.close()

        sA = SessionFactory()
        sB = SessionFactory()
        task_a = claim_next_task(sA)
        task_b = claim_next_task(sB)

        assert task_a is not None and task_a.id == "race-1"
        assert task_a.status == "running"
        assert task_b is None  # 第二个 worker 认领不到（status 守卫）

        sA.close()
        sB.close()
        engine.dispose()

    def test_stale_lock_reclaimable_by_second_session(self, tmp_path):
        from datetime import datetime, timedelta

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.core.db import Base
        from app.models.ai_task import AiTask
        from app.services.ai_tasks import claim_next_task

        db_path = tmp_path / "race-stale.sqlite"
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionFactory = sessionmaker(bind=engine)

        s0 = SessionFactory()
        s0.add(AiTask(id="race-2", task_type="generate", project_id=1, document_id=5,
                      status="pending", progress=0, result_json="null", error="",
                      locked_at=datetime.utcnow() - timedelta(minutes=10)))
        s0.commit()
        s0.close()

        sA = SessionFactory()
        sB = SessionFactory()
        task_a = claim_next_task(sA)
        task_b = claim_next_task(sB)
        assert task_a is not None and task_a.id == "race-2"
        assert task_b is None
        sA.close()
        sB.close()
        engine.dispose()


def test_run_generate_awaits_async_ai(monkeypatch, db_session):
    """C120-2 回归：_run_generate 必须 await async AI（否则 coroutine 对象报错）。"""
    from app.services import ai_tasks

    async def fake_gen(content, file_type="", source_ref="", extraction=None):
        return {"functional_cases": [{"title": "async-ok"}]}

    monkeypatch.setattr(
        "app.services.requirement_service.get_requirement",
        lambda db, doc_id, project_id=0: {"content": "x", "file_type": "md", "source_ref": "r", "extraction_raw": ""},
    )
    monkeypatch.setattr("app.services.ai_service.generate_test_cases", fake_gen)

    result = ai_tasks._run_generate(db_session, 999)
    assert result["functional_cases"][0]["title"] == "async-ok"
    assert "coverage_report" in result


class TestBatch161FollowupProjectScope:
    """Batch 161 follow-up：异步 AI 任务必须按任务 project_id 取文档并传入已确认 extraction。"""

    def test_execute_task_passes_task_project_id(self, db_session, monkeypatch):
        from app.services import ai_tasks
        from app.models.ai_task import AiTask

        captured = []
        row = AiTask(id="scope-1", task_type="generate", project_id=7, document_id=3,
                     status="running", progress=5, result_json="null", error="")
        db_session.add(row)
        db_session.commit()

        def fake_dispatch(task_type, document_id, db, project_id=0):
            captured.append((task_type, document_id, project_id))
            return {"functional_cases": []}

        ai_tasks.execute_task(db_session, row, dispatch=fake_dispatch)
        assert captured == [("generate", 3, 7)], captured

    def test_run_generate_uses_project_id_and_extraction(self, db_session, monkeypatch):
        from app.services import ai_tasks

        seen = {}
        monkeypatch.setattr(
            "app.services.requirement_service.get_requirement",
            lambda db, doc_id, project_id=0: {
                "content": "需求内容", "file_type": "md", "source_ref": "r",
                "extraction_status": "confirmed",
            },
        )
        monkeypatch.setattr(
            "app.services.requirement_service.get_extraction",
            lambda db, doc_id, project_id=0: {
                "modules": [{"id": "MOD-1", "name": "广告", "function_points": [{"id": "FP-1"}]}],
            },
        )

        async def fake_gen(content, file_type="", source_ref="", extraction=None):
            seen["extraction"] = extraction
            return {"functional_cases": [{"title": "guided-ok"}]}

        monkeypatch.setattr("app.services.ai_service.generate_test_cases", fake_gen)

        result = ai_tasks._run_generate(db_session, 5, project_id=7)
        assert result["functional_cases"][0]["title"] == "guided-ok"
        assert seen["extraction"] == {
            "modules": [{"id": "MOD-1", "name": "广告", "function_points": [{"id": "FP-1"}]}]
        }
        assert "coverage_report" in result

    def test_run_extract_uses_project_id(self, db_session, monkeypatch):
        from app.services import ai_tasks

        seen = {}
        monkeypatch.setattr(
            "app.services.requirement_service.get_requirement",
            lambda db, doc_id, project_id=0: (seen.__setitem__("pid", project_id), {"content": "x"})[1],
        )
        import asyncio as _asyncio

        async def fake_extract(content, file_type="", source_ref=""):
            return {"modules": []}

        monkeypatch.setattr("app.services.ai_service.extract_features", fake_extract)
        ai_tasks._run_extract(db_session, 5, project_id=9)
        assert seen["pid"] == 9


class TestBatch161Followup2Persist:
    """Batch 161 follow-up2：异步拆分/生成结果必须持久化（否则 UI 查看/导入为空）。"""

    def test_run_extract_persists_extraction(self, db_session, monkeypatch):
        from app.models.requirement import RequirementDocument
        from app.services import ai_tasks

        doc = RequirementDocument(id=9001, project_id=1, title="t", content="需求内容")
        db_session.add(doc)
        db_session.commit()

        async def fake_extract(content, file_type="", source_ref=""):
            return {"modules": [{"id": "MOD-1", "name": "广告", "function_points": []}]}

        monkeypatch.setattr("app.services.ai_service.extract_features", fake_extract)
        result = ai_tasks._run_extract(db_session, 9001, project_id=1)
        assert result["modules"][0]["id"] == "MOD-1"
        db_session.refresh(doc)
        assert doc.extraction_status == "pending_review"
        assert '"MOD-1"' in doc.extraction_raw

    def test_run_generate_persists_result(self, db_session, monkeypatch):
        from app.models.requirement import RequirementDocument
        from app.services import ai_tasks

        doc = RequirementDocument(
            id=9002, project_id=1, title="t", content="需求内容",
            extraction_status="confirmed",
            extraction_raw='{"modules":[{"id":"MOD-1","function_points":[{"id":"FP-1"}]}]}',
        )
        db_session.add(doc)
        db_session.commit()

        async def fake_gen(content, file_type="", source_ref="", extraction=None):
            return {"functional_cases": [{"title": "persist-ok"}]}

        monkeypatch.setattr("app.services.ai_service.generate_test_cases", fake_gen)
        monkeypatch.setattr(
            "app.services.requirement_service.get_extraction",
            lambda db, doc_id, project_id=0: {"modules": [{"id": "MOD-1", "function_points": [{"id": "FP-1"}]}]},
        )
        result = ai_tasks._run_generate(db_session, 9002, project_id=1)
        assert result["functional_cases"][0]["title"] == "persist-ok"
        db_session.refresh(doc)
        assert "persist-ok" in doc.ai_raw
