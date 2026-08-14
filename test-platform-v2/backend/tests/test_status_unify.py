"""Batch 182（FIX-173-P1-06）— 执行状态机统一测试。

覆盖：canonical 规范化、迁移映射、统计/追溯口径、open_api 回写双值兼容、
计划/UI 执行链路终态新词表。
"""
from __future__ import annotations

import hashlib

import pytest

from app.core.execution_status import (
    CANONICAL_STATUSES,
    canonical_exec_status,
)


class TestCanonical:
    def test_new_values_pass_through(self):
        for v in ("pending", "running", "passed", "failed", "skipped", "cancelled", "blocked"):
            assert canonical_exec_status(v) == v

    def test_legacy_values_mapped(self):
        assert canonical_exec_status("pass") == "passed"
        assert canonical_exec_status("fail") == "failed"
        assert canonical_exec_status("skip") == "skipped"
        assert canonical_exec_status("block") == "blocked"
        assert canonical_exec_status("success") == "passed"
        assert canonical_exec_status("done") == "passed"
        assert canonical_exec_status("completed") == "passed"

    def test_unknown_passthrough(self):
        assert canonical_exec_status("weird") == "weird"
        assert canonical_exec_status("") == ""
        assert canonical_exec_status(None) == ""


class TestMigration:
    def test_migration_maps_legacy_statuses(self, tmp_path):
        """b182 迁移把存量旧值映射为新词表（stamp+upgrade 链，旧表预置 legacy 值）。"""
        import os
        import subprocess
        import sys
        from pathlib import Path

        import sqlalchemy as sa

        backend_root = Path(__file__).resolve().parents[1]
        db_path = tmp_path / "b182.sqlite"
        engine = sa.create_engine(f"sqlite:///{db_path.as_posix()}")
        metadata = sa.MetaData()
        # 预置旧结构的执行表（stamp 点之前的表在空库链中不存在，手动建表并塞旧值）
        sa.Table("sys_project", metadata, sa.Column("id", sa.Integer(), primary_key=True))
        sa.Table(
            "test_execution", metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("plan_case_id", sa.Integer(), default=0),
            sa.Column("status", sa.String(20), default="pending"),
        )
        sa.Table(
            "test_plan_case", metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("plan_id", sa.Integer(), default=0),
            sa.Column("case_id", sa.Integer(), default=0),
            sa.Column("last_status", sa.String(20), default="pending"),
        )
        metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "INSERT INTO test_execution (plan_case_id, status) VALUES "
                "(1,'pass'),(2,'fail'),(3,'skip'),(4,'block'),(5,'pending')"
            ))
            conn.execute(sa.text(
                "INSERT INTO test_plan_case (plan_id, case_id, last_status) VALUES "
                "(1,1,'pass'),(1,2,'fail')"
            ))

        env = os.environ.copy()
        env.update({
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
            "AUTO_CREATE_TABLES": "false",
            "PYTHONPATH": str(backend_root),
        })
        # 与 test_project_invite 相同：先 stamp 到 batch105 合并点，再升到 head
        subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", "20260806_merge_batch103_batch105"],
            cwd=backend_root, env=env, capture_output=True, check=True, text=True, timeout=120,
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_root, env=env, capture_output=True, check=True, text=True, timeout=120,
        )

        with engine.connect() as conn:
            statuses = [r[0] for r in conn.execute(sa.text(
                "SELECT status FROM test_execution ORDER BY id"
            ))]
            last_statuses = [r[0] for r in conn.execute(sa.text(
                "SELECT last_status FROM test_plan_case ORDER BY id"
            ))]
        assert statuses == ["passed", "failed", "skipped", "blocked", "pending"]
        assert last_statuses == ["passed", "failed"]


class TestStatsReads:
    def test_plan_stats_maps_new_vocab(self, db_session):
        """计划统计响应键（pass_/fail/skip/block）在 DB 新词表下正确聚合。"""
        from app.models.test_plan import TestPlan, TestPlanCase
        from app.services.test_plan_service import _batch_calc_stats

        plan = TestPlan(project_id=1, name="P182", status="active")
        db_session.add(plan)
        db_session.flush()
        for i, s in enumerate(["passed", "failed", "skipped", "blocked", "pending"]):
            db_session.add(TestPlanCase(plan_id=plan.id, case_id=i + 1, last_status=s))
        db_session.commit()

        stats = _batch_calc_stats(db_session, {plan.id})[plan.id]
        assert stats["pass_"] == 1
        assert stats["fail"] == 1
        assert stats["skip"] == 1
        assert stats["block"] == 1
        assert stats["pending"] == 1
        assert stats["total"] == 5

    def test_statistics_service_uses_new_vocab(self, db_session):
        """statistics_service 在新词表下计数。"""
        from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
        from app.services.statistics_service import get_project_statistics

        plan = TestPlan(project_id=1, name="P182S", status="active")
        db_session.add(plan)
        db_session.flush()
        pc = TestPlanCase(plan_id=plan.id, case_id=1)
        db_session.add(pc)
        db_session.flush()
        db_session.add_all([
            TestExecution(plan_case_id=pc.id, status="passed"),
            TestExecution(plan_case_id=pc.id, status="failed"),
        ])
        db_session.commit()

        result = get_project_statistics(db_session, 1)
        assert result is not None


class TestOpenApiCompat:
    def test_writeback_accepts_legacy_and_new(self, client, auth_headers, db_session):
        """open_api 回写：旧值 pass → 落库 passed；新值 passed → passed。"""
        from app.models.api_token import ApiToken
        from app.models.test_plan import TestPlan, TestPlanCase, TestExecution

        plan = TestPlan(project_id=1, name="P182O", status="active")
        db_session.add(plan)
        db_session.flush()
        pc = TestPlanCase(plan_id=plan.id, case_id=1)
        db_session.add(pc)
        db_session.flush()
        ex = TestExecution(plan_case_id=pc.id, status="pending")
        db_session.add(ex)
        db_session.commit()

        token = ApiToken(project_id=1, name="t", token_hash=hashlib.sha256(b"x182").hexdigest(), enabled=True)
        db_session.add(token)
        db_session.commit()

        # 旧值
        resp = client.post(
            "/api/v1/open/results",
            headers={"Authorization": "Bearer x182"},
            json={"run_id": ex.id, "status": "pass"},
        )
        assert resp.status_code == 200, resp.text
        db_session.refresh(ex)
        assert ex.status == "passed"

        # 新值
        resp = client.post(
            "/api/v1/open/results",
            headers={"Authorization": "Bearer x182"},
            json={"run_id": ex.id, "status": "failed"},
        )
        assert resp.status_code == 200, resp.text
        db_session.refresh(ex)
        assert ex.status == "failed"


class TestExecChains:
    def test_manual_execute_case_writes_new_vocab(self, db_session):
        """手动执行落库统一词表。"""
        from app.models.test_plan import TestPlan, TestPlanCase
        from app.services.test_plan_service import execute_case

        plan = TestPlan(project_id=1, name="P182M", status="active")
        db_session.add(plan)
        db_session.flush()
        pc = TestPlanCase(plan_id=plan.id, case_id=1)
        db_session.add(pc)
        db_session.commit()

        execute_case(db_session, plan.id, pc.id, executor_id=0, status="fail", project_id=1)
        db_session.refresh(pc)
        assert pc.last_status == "failed"

        execute_case(db_session, plan.id, pc.id, executor_id=0, status="passed", project_id=1)
        db_session.refresh(pc)
        assert pc.last_status == "passed"
