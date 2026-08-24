"""B组「假成功与状态一致性」单元/接口回归测试。

覆盖：B1 集成 sync-now 诚实语义、B3 Playground TODO 拦截、B4 DSH 场景 0 产物、
B5 缺陷 PUT 走状态机、B6 last_run_status 规范词表、B7 report/trace 状态词表、
B11 删除用户引用校验、B12 认证审计（失败亦记录）。
"""
from __future__ import annotations

import pytest

from app.core.execution_status import canonical_exec_status


class TestB1SyncNowHonestSemantics:
    def _seed_env_and_config(self, db_session, *, sync_direction="push_only"):
        from app.models.environment import Environment
        from app.models.integration import IntegrationConfig

        env = Environment(project_id=1, name="test-env", env_type="test",
                          base_url="http://api.test.local", is_production=False)
        db_session.add(env)
        db_session.flush()
        cfg = IntegrationConfig(project_id=1, name="jira", provider_type="jira",
                                base_url="http://jira.local", sync_direction=sync_direction)
        db_session.add(cfg)
        db_session.flush()
        db_session.commit()
        return env, cfg

    def test_sync_now_errors_returns_failure_code(self, client, auth_headers, db_session, monkeypatch):
        """errors>0 → 返回 code!=0 失败语义并携带 errors 明细（不再恒报成功）。"""
        from app.models.defect import Defect
        from app.services.sync import engine as sync_engine_mod

        env, cfg = self._seed_env_and_config(db_session)
        db_session.add(Defect(project_id=1, defect_id="D1", title="d", status="open", external_id=""))
        db_session.commit()

        monkeypatch.setattr(
            sync_engine_mod, "push_defect",
            lambda *a, **k: {"status": "failed", "message": "boom"},
        )
        resp = client.post(
            f"/api/v1/integrations/{cfg.id}/sync-now",
            headers=auth_headers,
            params={"environment_id": env.id, "direction": "push_only", "confirm_prod": "true"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] != 0, body
        assert body["data"]["errors"] == 1
        assert "失败" in body["msg"]

    def test_sync_now_zero_change_is_honest(self, client, auth_headers, db_session):
        """推拉全 0 且无错误 → 不报「同步完成」，返回警示语义。"""
        env, cfg = self._seed_env_and_config(db_session)
        resp = client.post(
            f"/api/v1/integrations/{cfg.id}/sync-now",
            headers=auth_headers,
            params={"environment_id": env.id, "direction": "push_only", "confirm_prod": "true"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] != 0, body
        assert body["data"]["pushed"] == 0 and body["data"]["pulled"] == 0 and body["data"]["errors"] == 0
        assert "未产生任何变更" in body["msg"]


class TestB3PlaygroundTodoBlock:
    def test_todo_spec_has_todo_detected(self):
        from app.services.playground_service import _spec_has_todo
        assert _spec_has_todo("// TODO: xxx // 未识别步骤") is True
        assert _spec_has_todo("await page.goto('x');") is False

    def test_playground_todo_blocked_run(self, db_session):
        """has_todo 用例：不执行、不判通过，回写 canonical failed + 原因。"""
        from app.models.test_case import TestCase
        from app.services.playground_service import run_case_batch

        tc = TestCase(
            project_id=1, case_id="C1", title="todo case", case_type="manual",
            preconditions="[]",
            steps='[{"desc":"完全无法识别的操作xyz"}]',
        )
        db_session.add(tc)
        db_session.commit()

        res = run_case_batch(
            db_session, project_id=1, creator_id=0, case_ids=[tc.id],
            write_back_to_ui=False, timeout_ms=5000,
        )
        assert res.todo_blocked == 1
        assert res.passed == 0
        db_session.refresh(tc)
        assert tc.last_run_status == "failed"
        assert "TODO 拦截" in (tc.last_response_json or "")


class TestB4DshZeroArtifact:
    def test_scene_task_zero_artifact_returns_reason(self, db_session):
        """生产场景任务 0 产物返回 reason（供任务层不再标 success）。"""
        from app.models.dsh_task import DshTask
        from app.services.dsh.dsh_artifact_service import ingest_artifacts

        task = DshTask(project_id=1, task="x", status="running",
                       params_json='{"scene":"functional"}',
                       output_text="no manifest here", mode="single")
        db_session.add(task)
        db_session.commit()

        written, reason = ingest_artifacts(db_session, task)
        assert written == 0
        assert reason  # 非空原因（不再静默 0,None）

    def test_general_scene_zero_artifact_is_normal(self, db_session):
        """scene=general（空产物场景）→ 0 产物但无原因（保持正常）。"""
        from app.models.dsh_task import DshTask
        from app.services.dsh.dsh_artifact_service import ingest_artifacts

        task = DshTask(project_id=1, task="x", status="running",
                       params_json='{"scene":"general"}',
                       output_text="no manifest", mode="single")
        db_session.add(task)
        db_session.commit()

        written, reason = ingest_artifacts(db_session, task)
        assert written == 0
        assert reason is None


class TestB5DefectPutStateMachine:
    def _mk_defect(self, db_session, status="open", defect_id="DEF-T"):
        from app.models.defect import Defect

        d = Defect(project_id=1, defect_id=defect_id, title="t", severity="P1", status=status)
        db_session.add(d)
        db_session.commit()
        return d

    def test_illegal_transition_open_to_closed_rejected(self, client, auth_headers, db_session):
        """非法状态流转按仓库 envelope 契约拒绝（HTTP 200 + code=1），状态保持不变。"""
        d = self._mk_defect(db_session, status="open", defect_id="DEF-T1")
        resp = client.put(
            f"/api/v1/defects/{d.id}", headers=auth_headers, json={"status": "closed"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["code"] == 1, resp.text
        assert "流转" in resp.json()["msg"]
        db_session.refresh(d)
        assert d.status == "open"

    def test_legal_transition_via_put(self, client, auth_headers, db_session):
        d = self._mk_defect(db_session, status="open", defect_id="DEF-T2")
        resp = client.put(
            f"/api/v1/defects/{d.id}", headers=auth_headers, json={"status": "confirmed"},
        )
        assert resp.status_code == 200, resp.text
        db_session.refresh(d)
        assert d.status == "confirmed"

    def test_same_status_put_is_noop(self, client, auth_headers, db_session):
        d = self._mk_defect(db_session, status="open", defect_id="DEF-T3")
        resp = client.put(
            f"/api/v1/defects/{d.id}", headers=auth_headers, json={"status": "open"},
        )
        assert resp.status_code == 200, resp.text
        db_session.refresh(d)
        assert d.status == "open"


class TestB6LastRunStatusVocab:
    def test_save_execution_backfill_writes_canonical(self, db_session):
        from app.models.test_case import TestCase
        from app.services.test_case_service import save_execution_backfill

        tc = TestCase(project_id=1, case_id="C1", title="t", case_type="api")
        db_session.add(tc)
        db_session.commit()

        assert save_execution_backfill(db_session, tc.id, 1, {"all_pass": True}) is True
        db_session.commit()
        db_session.refresh(tc)
        assert tc.last_run_status == "passed"

        assert save_execution_backfill(db_session, tc.id, 1, {"all_pass": False}) is True
        db_session.commit()
        db_session.refresh(tc)
        assert tc.last_run_status == "failed"
        # 非词表旧值不再出现
        assert tc.last_run_status in ("passed", "failed")


class TestB7ReportTraceVocab:
    def test_report_stats_key_includes_running_cancelled(self):
        from app.services.report_service import _REPORT_STATS_KEY
        assert _REPORT_STATS_KEY["running"] == "running"
        assert _REPORT_STATS_KEY["cancelled"] == "cancelled"
        assert _REPORT_STATS_KEY["passed"] == "pass"

    def test_trend_retains_running_cancelled(self, db_session):
        from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
        from app.services.trace_service import get_trend

        plan = TestPlan(project_id=1, name="P", status="active")
        db_session.add(plan)
        db_session.flush()
        pc = TestPlanCase(plan_id=plan.id, case_id=1)
        db_session.add(pc)
        db_session.flush()
        db_session.add_all([
            TestExecution(plan_case_id=pc.id, status="running"),
            TestExecution(plan_case_id=pc.id, status="cancelled"),
        ])
        db_session.commit()

        r = get_trend(db_session, 1, days=30)
        assert sum(b["running"] for b in r["trend"]) == 1
        assert sum(b["cancelled"] for b in r["trend"]) == 1


class TestB11UserDeleteReferences:
    def test_delete_blocked_by_plan_assignee(self, db_session):
        from app.models.test_plan import TestPlan
        from app.models.user import User
        from app.services.user_service import delete_user

        u = User(username="u1", password="x", status=1)
        db_session.add(u)
        db_session.flush()
        db_session.add(TestPlan(project_id=1, name="P", status="active", assignee_id=u.id))
        db_session.commit()

        with pytest.raises(ValueError) as ei:
            delete_user(db_session, u.id)
        assert "测试计划" in str(ei.value)

    def test_delete_with_no_refs_succeeds(self, db_session):
        from app.models.user import User
        from app.services.user_service import delete_user

        u = User(username="u2", password="x", status=1)
        db_session.add(u)
        db_session.commit()

        assert delete_user(db_session, u.id) is True


class TestB12AuthAudit:
    def test_login_failure_writes_audit(self, client, db_session):
        from app.models.audit import AuditLog

        resp = client.post("/api/v1/auth/login", json={"username": "nouser", "password": "wrong"})
        assert resp.status_code == 401
        actions = [r.action for r in db_session.query(AuditLog).all()]
        assert "auth.login" in actions

    def test_login_success_writes_audit(self, client, auth_headers, db_session):
        from app.models.audit import AuditLog

        # auth_headers fixture already logged in as admin_test — but that login
        # ran in a differ request; here force a fresh login to capture audit.
        db_session.query(AuditLog).delete()
        db_session.commit()
        resp = client.post("/api/v1/auth/login", json={"username": "admin_test", "password": "admin123"})
        assert resp.status_code == 200
        actions = [r.action for r in db_session.query(AuditLog).all()]
        assert "auth.login" in actions


class TestCanonicalRef:
    def test_legacy_pass_maps_to_passed(self):
        assert canonical_exec_status("pass") == "passed"
