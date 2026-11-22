"""AUD-004：反事实实验必须绑定真实验证 Run（v1.5 §01 AUD-004 / §04 E1–E6）。

本文件替换原先编码了违规行为的旧用例：
- 旧用例断言 `verification_run_id` 是 36 位随机 UUID（实为 `uuid4()` 伪造）；
- 旧用例断言创建即 `status="completed"`（没有真实 Run）。
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.triage import TriageExperiment
from app.aiqe.services.triage_service import (
    EXPERIMENTS,
    ExperimentError,
    create_experiment,
    launch_experiment,
    list_experiments,
    record_experiment_result,
    snapshot_diff,
    spec_for,
    sync_experiment_result,
    validate_change,
)

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "login",
            "driver": "http",
            "input": {"url": "https://api.allowed.test/login", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "login_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-LOGIN",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "verify",
            "driver": "http",
            "input": {"url": "https://api.allowed.test/state", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "state_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-STATE",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
    ],
    "edges": [],
}


def _seed_baseline(db, *, key: str = "RUN-BASE-0001") -> TestRun:
    from app.aiqe.services import dag_scheduler
    from app.aiqe.services.capability_registry import register_manifest
    from app.models.project import Project

    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="TEST", name="Test", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )
    run = TestRun(
        project_id=1,
        run_key=key,
        source_type="manual",
        status="COMPLETED",
        outcome="FAIL",
        build_ref="build-2026-11-18",
        commit_sha="a" * 40,
        environment_snapshot_json={"contract_checksum": "c1", "workflow_checksum": "w1"},
    )
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, GRAPH)
    db.commit()
    return run


# ── E1–E6 定义与单变量校验 ─────────────────────────────────
def test_experiment_matrix_matches_spec_unique_variables():
    expected = {
        "E1": "run_attempt",
        "E2": "fixture_namespace",
        "E3": "upstream_mode",
        "E4": "feature_flag",
        "E5": "worker_instance",
        "E6": "network_profile",
    }
    assert {key: spec.variable for key, spec in EXPERIMENTS.items()} == expected
    assert len({spec.variable for spec in EXPERIMENTS.values()}) == 6


@pytest.mark.parametrize(("key", "variable"), list(
    (key, spec.variable) for key, spec in EXPERIMENTS.items()
))
def test_change_accepts_only_its_own_variable(key, variable):
    assert validate_change(key, {variable: "x"}) == (variable, "x")
    other = next(spec.variable for k, spec in EXPERIMENTS.items() if k != key)
    with pytest.raises(ExperimentError):
        validate_change(key, {other: "x"})


def test_double_variable_and_empty_value_rejected():
    with pytest.raises(ExperimentError):
        validate_change("E2", {"fixture_namespace": "ns", "feature_flag": "on"})
    with pytest.raises(ExperimentError):
        validate_change("E2", {})
    with pytest.raises(ExperimentError):
        validate_change("E2", {"fixture_namespace": "  "})


def test_unknown_experiment_rejected():
    with pytest.raises(ExperimentError):
        spec_for("E9")


# ── 创建：只落 Validated，不伪造 verification Run ───────────
def test_create_requires_real_baseline_run(db_session):
    with pytest.raises(ExperimentError):
        create_experiment(
            db_session,
            experiment_key="E2",
            change={"fixture_namespace": "aiqe-run-2"},
            idempotency_key="idem-nobase",
            baseline_run_id="does-not-exist",
        )
    assert db_session.query(TriageExperiment).count() == 0


def test_create_is_validated_not_completed(db_session):
    baseline = _seed_baseline(db_session)
    row = create_experiment(
        db_session,
        experiment_key="E2",
        change={"fixture_namespace": "aiqe-run-2"},
        idempotency_key="idem-create",
        baseline_run_id=baseline.id,
        triage_case_id="case-1",
    )
    assert row.status == "VALIDATED"
    assert row.verification_run_id is None
    assert row.changed_dimension == "fixture_namespace"
    assert row.baseline_run_id == baseline.id
    assert row.baseline_snapshot_hash
    assert row.project_id == baseline.project_id
    assert row.completed_at is None


def test_idempotency_returns_same_record(db_session):
    baseline = _seed_baseline(db_session)
    first = create_experiment(
        db_session,
        experiment_key="E1",
        change={"run_attempt": "2"},
        idempotency_key="idem-same",
        baseline_run_id=baseline.id,
    )
    second = create_experiment(
        db_session,
        experiment_key="E1",
        change={"run_attempt": "2"},
        idempotency_key="idem-same",
        baseline_run_id=baseline.id,
    )
    assert first.id == second.id
    assert db_session.query(TriageExperiment).count() == 1


# ── 启动：真实验证 Run + 单变量快照 ─────────────────────────
def test_launch_creates_real_run_bound_to_baseline(db_session):
    baseline = _seed_baseline(db_session)
    row = create_experiment(
        db_session,
        experiment_key="E4",
        change={"feature_flag": "ad_overlay=on"},
        idempotency_key="idem-launch",
        baseline_run_id=baseline.id,
    )
    launched = launch_experiment(db_session, row.id)

    assert launched.verification_run_id
    run = db_session.get(TestRun, launched.verification_run_id)
    assert run is not None, "verification_run_id 必须指向真实 TestRun"
    assert run.project_id == baseline.project_id
    assert run.retest_of == baseline.id
    assert run.source_type == "experiment"
    # 派发后 scheduler 迁移为 RUNNING；Worker 领取前不得出现 PASS/FAIL 结果。
    assert run.status in {"QUEUED", "RUNNING"}
    assert launched.status in {"QUEUED", "RUNNING"}
    assert launched.started_at is not None

    # 验证 Run 必须有可执行节点（否则无法真实执行）
    nodes = list(
        db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id))
    )
    assert {n.node_key for n in nodes} == {"login", "verify"}

    diff = launched.snapshot_diff_json
    assert diff["single_variable"] is True
    assert diff["expected_dimension"] == "feature_flag"
    assert diff["changed"] == ["environment_snapshot.feature_flag"]

    # baseline 不可变
    assert snapshot_diff(baseline, run)["changed"] == ["environment_snapshot.feature_flag"]
    assert baseline.outcome == "FAIL"


def test_launch_is_idempotent(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0002")
    row = create_experiment(
        db_session,
        experiment_key="E6",
        change={"network_profile": "3g-lossy"},
        idempotency_key="idem-launch-2",
        baseline_run_id=baseline.id,
    )
    first = launch_experiment(db_session, row.id)
    second = launch_experiment(db_session, row.id)
    assert first.verification_run_id == second.verification_run_id
    runs = list(
        db_session.query(TestRun).filter(TestRun.source_type == "experiment").all()
    )
    assert len(runs) == 1


def test_multi_variable_launcher_blocks_experiment(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0003")
    row = create_experiment(
        db_session,
        experiment_key="E4",
        change={"feature_flag": "on"},
        idempotency_key="idem-multi",
        baseline_run_id=baseline.id,
    )

    def two_variable_launcher(db, experiment, base) -> str:
        run = TestRun(
            project_id=base.project_id,
            run_key="RUN-MULTI-1",
            source_type="experiment",
            scenario_id=base.scenario_id,
            workflow_definition_id=base.workflow_definition_id,
            build_ref=base.build_ref,
            commit_sha=base.commit_sha,
            environment_id=base.environment_id,
            execution_profile_id=base.execution_profile_id,
            environment_snapshot_json={
                "feature_flag": "on",
                "network_profile": "3g-lossy",
            },
            retest_of=base.id,
            status="QUEUED",
        )
        db.add(run)
        db.flush()
        return run.id

    launched = launch_experiment(db_session, row.id, launcher=two_variable_launcher)
    assert launched.status == "BLOCKED"
    assert launched.error_code == "MULTI_VARIABLE_EXPERIMENT"
    assert launched.snapshot_diff_json["single_variable"] is False


# ── 收敛：只有 Run 终态才能 COMPLETED ───────────────────────
def test_sync_keeps_queued_while_run_not_terminal(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0004")
    row = create_experiment(
        db_session,
        experiment_key="E5",
        change={"worker_instance": "runner-b"},
        idempotency_key="idem-sync-1",
        baseline_run_id=baseline.id,
    )
    launch_experiment(db_session, row.id)
    synced = sync_experiment_result(db_session, row.id)
    assert synced.status in {"QUEUED", "RUNNING"}
    assert synced.completed_at is None


def test_sync_completes_after_run_terminal(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0005")
    row = create_experiment(
        db_session,
        experiment_key="E1",
        change={"run_attempt": "3"},
        idempotency_key="idem-sync-2",
        baseline_run_id=baseline.id,
    )
    launched = launch_experiment(db_session, row.id)
    run = db_session.get(TestRun, launched.verification_run_id)
    run.status = "COMPLETED"
    run.outcome = "PASS"
    db_session.commit()

    synced = sync_experiment_result(db_session, row.id)
    assert synced.status == "COMPLETED"
    assert synced.error_code is None
    assert synced.completed_at is not None
    assert synced.experiment_result is None  # 结论需要单独记录

    record_experiment_result(db_session, row.id, result="SUPPORTED")
    assert synced.experiment_result == "SUPPORTED"


def test_sync_unknown_when_verification_run_missing(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0006")
    row = create_experiment(
        db_session,
        experiment_key="E3",
        change={"upstream_mode": "recorded"},
        idempotency_key="idem-sync-3",
        baseline_run_id=baseline.id,
    )
    launched = launch_experiment(db_session, row.id)
    db_session.delete(db_session.get(TestRun, launched.verification_run_id))
    db_session.commit()

    synced = sync_experiment_result(db_session, row.id)
    assert synced.status == "UNKNOWN"
    assert synced.error_code == "VERIFICATION_RUN_MISSING"


def test_result_requires_completed_experiment(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0007")
    row = create_experiment(
        db_session,
        experiment_key="E2",
        change={"fixture_namespace": "ns"},
        idempotency_key="idem-result",
        baseline_run_id=baseline.id,
    )
    with pytest.raises(ExperimentError):
        record_experiment_result(db_session, row.id, result="SUPPORTED")
    with pytest.raises(ExperimentError):
        record_experiment_result(db_session, row.id, result="MAYBE")


def test_all_six_experiments_recorded_and_listed(db_session):
    baseline = _seed_baseline(db_session, key="RUN-BASE-0008")
    for key, spec in EXPERIMENTS.items():
        name = spec.variable
        create_experiment(
            db_session,
            experiment_key=key,
            change={name: f"value-{key}"},
            idempotency_key=f"idem-all-{key}",
            baseline_run_id=baseline.id,
            triage_case_id="case-all",
        )
    rows = list_experiments(db_session, "case-all")
    assert len(rows) == len(EXPERIMENTS)
    assert {row.experiment_key for row in rows} == set(EXPERIMENTS)
    assert all(row.status == "VALIDATED" for row in rows)
    assert all(row.verification_run_id is None for row in rows)
