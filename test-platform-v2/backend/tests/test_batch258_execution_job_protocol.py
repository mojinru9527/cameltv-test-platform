"""Batch 258 / B1-4 — ExecutionJob 协议：认领 → 心跳 → 上报 → 超时回收。

方案口径（09-platform-landing-plan.md §3.2）：`ExecutionJob` 与 `AiJob` **并列、不合并**；
租约沿用 AiJob 的 claim/heartbeat/stale 语义（因此不另建 job_leases 表，避免双份记账）。

DoD（backlog B1-4）：全链路测试通过；跨项目不可认领；权限点独立。
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.exceptions import APIException
from app.services import ai_agent_service, execution_job_service


def _register_node(db, node_id: str, project_id: int, capabilities: list[str]):
    return ai_agent_service.register_agent(db, node_id, project_id, capabilities, issue_token=False)


class TestJobProduction:
    def test_create_job_defaults_to_pending(self, db_session):
        job = execution_job_service.create_job(
            db_session, project_id=1, kind="api", case_refs=["case-1", "case-2"], env_ref="test5"
        )
        assert job.status == "pending"
        assert job.kind == "api"
        assert job.attempt == 0
        assert job.node_id == ""
        assert execution_job_service.job_dict(job)["case_refs"] == ["case-1", "case-2"]

    def test_invalid_kind_is_rejected(self, db_session):
        with pytest.raises(APIException):
            execution_job_service.create_job(db_session, project_id=1, kind="soap", case_refs=[])

    def test_project_isolation_on_read(self, db_session):
        job = execution_job_service.create_job(db_session, project_id=1, kind="web", case_refs=["c"])
        assert execution_job_service.get_job(db_session, project_id=1, job_id=job.id) is not None
        assert execution_job_service.get_job(db_session, project_id=2, job_id=job.id) is None
        rows, total = execution_job_service.list_jobs(db_session, project_id=1)
        assert total == 1 and rows[0].id == job.id
        assert execution_job_service.list_jobs(db_session, project_id=2)[1] == 0


class TestClaimHeartbeatReport:
    def test_full_claim_heartbeat_report_cycle(self, db_session):
        _register_node(db_session, "node-1", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c1"])

        claimed = execution_job_service.claim_job(db_session, node_id="node-1", project_id=1)
        assert claimed is not None and claimed.id == job.id
        assert claimed.status == "running"
        assert claimed.node_id == "node-1"
        assert claimed.attempt == 1
        assert claimed.lease_expires_at is not None
        assert claimed.claimed_at is not None

        assert execution_job_service.heartbeat(db_session, job_id=job.id, node_id="node-1") is True

        reported = execution_job_service.report(
            db_session,
            job_id=job.id,
            node_id="node-1",
            status="completed",
            summary="8/8 pass",
            result={"passed": 8},
            evidence_bundle_id=42,
        )
        assert reported is not None
        assert reported.status == "completed"
        assert reported.evidence_bundle_id == 42
        assert reported.finished_at is not None
        assert execution_job_service.job_dict(reported)["result"] == {"passed": 8}

    def test_claim_requires_online_registered_node(self, db_session):
        execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        with pytest.raises(APIException):
            execution_job_service.claim_job(db_session, node_id="ghost", project_id=1)

    def test_claim_respects_capability(self, db_session):
        _register_node(db_session, "node-api", 1, ["api"])
        execution_job_service.create_job(db_session, project_id=1, kind="web", case_refs=["c"])
        assert execution_job_service.claim_job(db_session, node_id="node-api", project_id=1) is None

    def test_cross_project_claim_is_impossible(self, db_session):
        _register_node(db_session, "node-p2", 2, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        assert execution_job_service.claim_job(db_session, node_id="node-p2", project_id=2) is None
        db_session.refresh(job)
        assert job.status == "pending" and job.node_id == ""

    def test_heartbeat_from_another_node_is_rejected(self, db_session):
        _register_node(db_session, "node-a", 1, ["api"])
        _register_node(db_session, "node-b", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        execution_job_service.claim_job(db_session, node_id="node-a", project_id=1)
        assert execution_job_service.heartbeat(db_session, job_id=job.id, node_id="node-b") is False

    def test_heartbeat_extends_lease(self, db_session):
        _register_node(db_session, "node-x", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        claimed = execution_job_service.claim_job(db_session, node_id="node-x", project_id=1)
        first_expiry = claimed.lease_expires_at
        claimed.lease_expires_at = first_expiry - timedelta(seconds=60)
        db_session.commit()

        assert execution_job_service.heartbeat(db_session, job_id=job.id, node_id="node-x") is True
        db_session.refresh(job)
        assert job.lease_expires_at > first_expiry - timedelta(seconds=60)

    def test_report_rejects_illegal_status(self, db_session):
        _register_node(db_session, "node-y", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        execution_job_service.claim_job(db_session, node_id="node-y", project_id=1)
        with pytest.raises(APIException):
            execution_job_service.report(
                db_session, job_id=job.id, node_id="node-y", status="exploded", summary=""
            )

    def test_report_from_another_node_is_rejected(self, db_session):
        _register_node(db_session, "node-z", 1, ["api"])
        _register_node(db_session, "node-w", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        execution_job_service.claim_job(db_session, node_id="node-z", project_id=1)
        assert (
            execution_job_service.report(
                db_session, job_id=job.id, node_id="node-w", status="completed", summary="stolen"
            )
            is None
        )


class TestStaleReclaim:
    def test_expired_lease_returns_job_to_pending_and_bumps_attempt(self, db_session):
        _register_node(db_session, "node-lost", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        claimed = execution_job_service.claim_job(db_session, node_id="node-lost", project_id=1)
        assert claimed.attempt == 1

        # 租约过期（节点断网/崩溃）
        claimed.lease_expires_at = execution_job_service.now() - timedelta(seconds=5)
        claimed.heartbeat_at = claimed.lease_expires_at
        db_session.commit()

        assert execution_job_service.reclaim_stale(db_session) == 1
        db_session.refresh(job)
        assert job.status == "pending"
        assert job.node_id == ""
        assert job.lease_expires_at is None
        assert job.error_message.startswith("reclaimed")

    def test_reclaimed_job_can_be_claimed_again(self, db_session):
        """断线不丢任务：节点回来后同一任务可再认领，attempt 递增。"""
        _register_node(db_session, "node-dead", 1, ["api"])
        job = execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        execution_job_service.claim_job(db_session, node_id="node-dead", project_id=1)
        job.lease_expires_at = execution_job_service.now() - timedelta(seconds=1)
        db_session.commit()
        execution_job_service.reclaim_stale(db_session)

        _register_node(db_session, "node-alive", 1, ["api"])
        again = execution_job_service.claim_job(db_session, node_id="node-alive", project_id=1)
        assert again is not None and again.id == job.id
        assert again.attempt == 2
        assert again.node_id == "node-alive"

    def test_live_lease_is_not_reclaimed(self, db_session):
        _register_node(db_session, "node-live", 1, ["api"])
        execution_job_service.create_job(db_session, project_id=1, kind="api", case_refs=["c"])
        execution_job_service.claim_job(db_session, node_id="node-live", project_id=1)
        assert execution_job_service.reclaim_stale(db_session) == 0


class TestReclaimedNodeDoesNotLoseTaskOverApi:
    """端到端：断线 → 回 pending → 重启节点继续（backlog B1-5 的 DoD 前置）。"""

    def test_claim_then_lose_then_reclaim_over_http(self, db_session, client, auth_headers):
        reg = client.post(
            "/api/v1/ai/agents/register",
            json={"agent_id": "node-http", "capabilities": ["api"]},
            headers=auth_headers,
        )
        assert reg.status_code == 200
        node_token = reg.json()["data"]["token"]

        created = client.post(
            "/api/v1/execution-jobs",
            json={"kind": "api", "case_refs": ["case-A"], "env_ref": "test5"},
            headers=auth_headers,
        )
        assert created.status_code == 200
        job_id = created.json()["data"]["id"]

        claimed = client.post(
            "/api/v1/execution-jobs/claim",
            json={"node_id": "node-http"},
            headers={"X-AI-Agent-Token": node_token},
        )
        assert claimed.status_code == 200
        assert claimed.json()["data"]["id"] == job_id

        # 模拟断线：租约过期
        job = execution_job_service.get_job(db_session, project_id=1, job_id=job_id)
        job.lease_expires_at = execution_job_service.now() - timedelta(seconds=1)
        db_session.commit()

        reclaimed = client.post(
            "/api/v1/execution-jobs/reclaim-stale", headers=auth_headers, json={}
        )
        assert reclaimed.status_code == 200
        assert reclaimed.json()["data"]["reclaimed"] == 1

        again = client.post(
            "/api/v1/execution-jobs/claim",
            json={"node_id": "node-http"},
            headers={"X-AI-Agent-Token": node_token},
        )
        assert again.status_code == 200
        assert again.json()["data"]["id"] == job_id
        assert again.json()["data"]["attempt"] == 2

    def test_claim_with_bad_node_token_is_401(self, client, auth_headers):
        resp = client.post(
            "/api/v1/execution-jobs/claim",
            json={"node_id": "node-http"},
            headers={"X-AI-Agent-Token": "agt_bogus"},
        )
        assert resp.status_code == 401

    def test_claim_without_any_credential_is_rejected(self, client, auth_headers):
        resp = client.post("/api/v1/execution-jobs/claim", json={"node_id": "node-http"})
        assert resp.status_code in (401, 403)

    def test_static_path_is_not_shadowed_by_job_id_param(self, client, auth_headers):
        """bug-guard：静态路径段必须先于 /{job_id} 注册，否则 claim 命中 /{job_id} → 422。"""
        resp = client.post(
            "/api/v1/execution-jobs/claim",
            json={"node_id": "node-http"},
            headers=auth_headers,
        )
        assert resp.status_code != 422
