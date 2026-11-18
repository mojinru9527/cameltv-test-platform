"""AUD-005：Driver Capability Registry 真实性 + Preflight 验收测试。

对应 v1.5 §01 AUD-005「完成标准」：
- 声明支持但无真实设备/浏览器的 Driver 不得显示 VERIFIED；
- 不具备能力时在 Run Launch 前 BLOCKED，且**不创建空跑 Job**；
- Runner 版本/驱动改变后 VERIFIED 必须降级重新验收。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import capability_registry as registry
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.aiqe.services.preflight import (
    DRIVER_REQUIRED_CAPABILITIES,
    INPROCESS_DRIVERS,
    preflight_graph,
    preflight_node,
    required_capabilities_for,
)
from app.models.execution_job import ExecutionJob


# ── 1. 6 态状态机 ─────────────────────────────────────────
def test_registered_without_evidence(db_session):
    row = registry.register_manifest(
        db_session, node_id="n1", capabilities=["browser.chromium"]
    )
    assert row.capability_status == "REGISTERED"
    assert row.available is False
    assert registry.compute_effective_status(row) == "REGISTERED"


def test_evidence_moves_to_available(db_session):
    row = registry.register_manifest(
        db_session, node_id="n1", capabilities=["browser.chromium"], evidence_ref="run-1"
    )
    assert row.capability_status == "AVAILABLE"
    assert row.available is True


def test_verified_requires_platform_and_evidence(db_session):
    registry.register_manifest(
        db_session, node_id="n1", capabilities=["browser.chromium"], evidence_ref="run-1"
    )
    with pytest.raises(registry.CapabilityError):
        registry.mark_verified(db_session, "n1", platforms=[], evidence_ref="cap-1")
    with pytest.raises(registry.CapabilityError):
        registry.mark_verified(db_session, "n1", platforms=["linux"], evidence_ref="")

    row = registry.mark_verified(
        db_session, "n1", platforms=["linux"], evidence_ref="cap-run-9"
    )
    assert row.capability_status == "VERIFIED"
    assert row.verified_platforms_json == ["linux"]
    assert registry.compute_effective_status(row) == "VERIFIED"


def test_software_update_downgrades_verified(db_session):
    registry.register_manifest(
        db_session,
        node_id="n1",
        capabilities=["browser.chromium"],
        evidence_ref="run-1",
        driver_version="1.0.0",
        runner_version="build-a",
    )
    registry.mark_verified(db_session, "n1", platforms=["linux"], evidence_ref="cap-1")

    row = registry.register_manifest(
        db_session,
        node_id="n1",
        capabilities=["browser.chromium"],
        evidence_ref="run-2",
        driver_version="2.0.0",  # 软件更新
        runner_version="build-b",
    )
    assert row.capability_status == "AVAILABLE"
    assert row.verified_at is None
    assert row.status_reason == "SOFTWARE_UPDATED_REVERIFY_REQUIRED"

    # 也可以用显式批量失效
    registry.mark_verified(db_session, "n1", platforms=["linux"], evidence_ref="cap-2")
    affected = registry.invalidate_verification(db_session)
    assert affected == ["n1"]


def test_stale_heartbeat_is_unavailable(db_session):
    now = datetime.now(UTC)
    row = registry.register_manifest(
        db_session,
        node_id="n1",
        capabilities=["browser.chromium"],
        evidence_ref="run-1",
        heartbeat_at=now - timedelta(minutes=10),
        now=now,
    )
    assert row.capability_status == "AVAILABLE"  # 注册时按证据落库
    assert registry.compute_effective_status(row, now=now) == "UNAVAILABLE"
    assert registry.select_nodes(db_session, ["browser.chromium"], now=now) == []


def test_degraded_and_revoked(db_session):
    registry.register_manifest(
        db_session, node_id="n1", capabilities=["browser.chromium"], evidence_ref="run-1"
    )
    registry.mark_degraded(db_session, "n1", "browser crash loop")
    assert registry.effective_status(db_session, "n1") == "DEGRADED"
    assert registry.supports(db_session, "n1", "browser.chromium") is False

    registry.revoke(db_session, "n1", "admin disabled")
    assert registry.effective_status(db_session, "n1") == "REVOKED"
    with pytest.raises(registry.CapabilityError):
        registry.mark_verified(db_session, "n1", platforms=["linux"], evidence_ref="x")

    registry.restore(db_session, "n1")
    assert registry.effective_status(db_session, "n1") == "AVAILABLE"


def test_select_nodes_ignores_non_schedulable(db_session):
    now = datetime.now(UTC)
    registry.register_manifest(
        db_session, node_id="ok", capabilities=["browser.chromium"], evidence_ref="r1", now=now
    )
    registry.register_manifest(db_session, node_id="reg-only", capabilities=["browser.chromium"], now=now)
    registry.register_manifest(
        db_session, node_id="revoked", capabilities=["browser.chromium"], evidence_ref="r2", now=now
    )
    registry.revoke(db_session, "revoked", "disabled")
    assert registry.select_nodes(db_session, ["browser.chromium"], now=now) == ["ok"]


def test_platform_matrix_reports_six_state(db_session):
    registry.register_manifest(
        db_session,
        node_id="n1",
        capabilities=["device.android"],
        platforms=["android"],
        evidence_ref="r1",
    )
    registry.mark_verified(db_session, "n1", platforms=["android"], evidence_ref="cap-1")
    matrix = registry.platform_matrix(db_session)
    assert matrix[0]["node_id"] == "n1"
    assert matrix[0]["capability_status"] == "VERIFIED"
    assert matrix[0]["verified_platforms"] == ["android"]


# ── 2. Preflight 判定 ─────────────────────────────────────
def test_required_capabilities_merge_driver_and_declared():
    assert required_capabilities_for({"key": "ui", "driver": "playwright"}) == ("browser.chromium",)
    assert required_capabilities_for(
        {"key": "ui", "driver": "playwright", "capability": "browser.webkit"}
    ) == ("browser.chromium", "browser.webkit")
    assert required_capabilities_for({"key": "x", "driver": "unknown"}) == ()


def test_preflight_unknown_driver_blocked(db_session):
    result = preflight_node(db_session, node_def={"key": "x", "driver": "teleport"})
    assert result.allowed is False
    assert result.blockers[0].code == "UNSUPPORTED_DRIVER"


def test_preflight_inprocess_http_is_ready(db_session):
    assert "http" in INPROCESS_DRIVERS
    result = preflight_node(db_session, node_def={"key": "api", "driver": "http"})
    assert result.allowed is True
    assert result.status == "READY"


def test_preflight_playwright_without_runner_blocked(db_session):
    result = preflight_node(db_session, node_def={"key": "ui", "driver": "playwright"})
    assert result.allowed is False
    assert result.blockers[0].code == "NO_CAPABLE_RUNNER"
    assert result.blockers[0].node_key == "ui"
    assert result.blockers[0].details["required_capabilities"] == ["browser.chromium"]


def test_preflight_playwright_with_verified_runner_ready(db_session):
    registry.register_manifest(
        db_session,
        node_id="runner-test-01",
        capabilities=["browser.chromium"],
        platforms=["linux"],
        evidence_ref="run-1",
    )
    registry.mark_verified(db_session, "runner-test-01", platforms=["linux"], evidence_ref="cap-1")
    result = preflight_node(db_session, node_def={"key": "ui", "driver": "playwright"})
    assert result.allowed is True


def test_preflight_platform_mismatch_blocked(db_session):
    registry.register_manifest(
        db_session,
        node_id="android-only",
        capabilities=["device.android"],
        platforms=["android"],
        evidence_ref="run-1",
    )
    result = preflight_node(
        db_session, node_def={"key": "ios", "driver": "appium", "platform": "ios", "capability": "device.ios"}
    )
    assert result.allowed is False
    assert result.blockers[0].code == "NO_CAPABLE_RUNNER"


def test_preflight_production_blocked(db_session):
    from app.models.environment import Environment

    env = Environment(project_id=1, name="prod", env_type="prod", is_production=True)
    db_session.add(env)
    db_session.flush()
    result = preflight_node(
        db_session, node_def={"key": "api", "driver": "http"}, environment_id=env.id
    )
    assert result.allowed is False
    assert result.blockers[0].code == "PRODUCTION_EXECUTION_FORBIDDEN"

    allowed = preflight_node(
        db_session,
        node_def={"key": "api", "driver": "http", "run_policy": {}},
        environment_id=env.id,
    )
    assert allowed.allowed is False
    # run_policy.allow_production 只能由整图预检开启
    graph = {
        "nodes": [{"key": "api", "driver": "http"}],
        "run_policy": {"allow_production": True},
    }
    assert preflight_graph(db_session, graph=graph, environment_id=env.id).allowed is True


def test_preflight_graph_collects_all_blockers(db_session):
    graph = {
        "nodes": [
            {"key": "api", "driver": "http"},
            {"key": "ui", "driver": "playwright"},
            {"key": "device", "driver": "appium"},
        ]
    }
    result = preflight_graph(db_session, graph=graph)
    assert result.allowed is False
    assert {blocker.node_key for blocker in result.blockers} == {"ui", "device"}
    assert set(result.required_capabilities) >= {"browser.chromium", "device.android"}


def test_preflight_empty_graph_blocked(db_session):
    result = preflight_graph(db_session, graph={"nodes": []})
    assert result.allowed is False
    assert result.blockers[0].code == "EMPTY_WORKFLOW"


# ── 3. 与调度/执行的集成：不创建空跑 Job ───────────────────
GRAPH_WITH_UI = {
    "schema_version": "1.0",
    "nodes": [{"key": "ui", "driver": "playwright", "input": {"url": "https://example.test"}}],
    "edges": [],
}


def _seed_run(db, graph=GRAPH_WITH_UI, key="RUN-AUD005-1") -> tuple[TestRun, ExecutionJob]:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(
        db, run.id, graph, dispatch=lambda row: enqueue_node_run(db, row, graph=graph)
    )
    db.commit()
    job = db.scalar(select(ExecutionJob).where(ExecutionJob.status == "pending"))
    return run, job


def test_schedule_with_preflight_blocks_and_creates_no_job(db_session):
    graph = GRAPH_WITH_UI
    run = TestRun(project_id=1, run_key="RUN-AUD005-2", status="QUEUED")
    db_session.add(run)
    db_session.flush()

    from app.aiqe.services.preflight import schedule_guard

    guard = schedule_guard(db_session, run=run, graph=graph)
    dag_scheduler.schedule(
        db_session,
        run.id,
        graph,
        dispatch=lambda row: enqueue_node_run(db_session, row, graph=graph),
        preflight=guard,
    )
    db_session.commit()

    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    assert node.error_class == "PREFLIGHT_BLOCKED"
    assert node.output_ref["preflight"]["code"] == "PREFLIGHT_BLOCKED"
    jobs = list(db_session.scalars(select(ExecutionJob).where(ExecutionJob.node_id.isnot(None))))
    assert [job for job in jobs if job.payload_json and run.id in job.payload_json] == []
    db_session.expire_all()
    assert db_session.get(TestRun, run.id).status == "COMPLETED"
    assert db_session.get(TestRun, run.id).outcome == "INCOMPLETE"


def test_job_consumer_blocks_when_capability_missing(db_session):
    run, job = _seed_run(db_session, key="RUN-AUD005-3")
    claimed = job_consumer.claim_aiqe_jobs(db_session)
    # 进程内消费者只认领 http 节点；playwright 节点应留给外部节点，不在此处认领。
    assert claimed == []
    job.status = "running"
    db_session.commit()

    outcome = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    assert outcome["error_class"] == "PREFLIGHT_BLOCKED"
    detail = node.output_ref["preflight"]
    assert detail["blockers"][0]["code"] == "NO_CAPABLE_RUNNER"


def test_job_consumer_runs_http_node_after_preflight(db_session, monkeypatch):
    graph = {
        "schema_version": "1.0",
        "nodes": [{"key": "api", "driver": "http", "input": {"url": "https://api.allowed.test/x"}}],
        "edges": [],
    }
    from app.aiqe.security import SafeHttpResult, upsert_target_policy

    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["api.allowed.test"], "allowed_ports": [443]},
    )
    run, job = _seed_run(db_session, graph=graph, key="RUN-AUD005-4")

    def _fake(self, request, policy):
        return SafeHttpResult(
            ok=True,
            status_code=200,
            duration_ms=1,
            request={"url": request.url},
            response={"status_code": 200},
            policy_version=policy.version,
        )

    monkeypatch.setattr("app.aiqe.services.node_executor.SafeHttpExecutor.request", _fake)
    job_consumer.claim_aiqe_jobs(db_session)
    outcome = job_consumer.run_job(db_session, job.id)
    assert outcome["node_status"] == "PASSED"


def test_driver_capability_map_covers_all_supported_drivers():
    from app.aiqe.services.node_executor import execute_node

    del execute_node  # 仅确保模块可导入
    for driver in ("http", "playwright", "appium", "db", "miniapp", "desktop", "iot", "external_e2e"):
        assert driver in DRIVER_REQUIRED_CAPABILITIES
