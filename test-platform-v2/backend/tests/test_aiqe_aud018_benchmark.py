"""AUD-018：Benchmark 数据集 / 真实执行 / 后端计算指标 验收测试。

对应 v1.5 §03 AUD-018：
- 数据集冻结有 content_hash 与 sample_count；<30 样本只能作为参考，不得自动门禁；
- 指标由后端从 golden labels 与真实预测计算（Precision/Recall/F1/Unknown rate）；
- 正式 Benchmark 必须使用 FROZEN 数据集，运行记录保存逐样本结果与版本信息；
- API 不接受 Agent 自报 precision/recall/false_positive_rate。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.aiqe.models.benchmark import BenchmarkDataset, BenchmarkRun
from app.aiqe.services.benchmark_service import (
    BenchmarkError,
    add_sample,
    compare_with_baseline,
    compute_metrics,
    create_dataset,
    freeze_dataset,
    list_samples,
    run_benchmark,
)


def _dataset(db, *, samples: int = 40, dataset_key: str = "triage-ds"):
    dataset = create_dataset(db, project_id=1, dataset_key=dataset_key, task_type="triage")
    for index in range(samples):
        add_sample(
            db,
            dataset.id,
            sample_id=f"s-{index:03d}",
            golden_labels=["PRODUCT_DEFECT"] if index % 2 == 0 else ["ENVIRONMENT"],
            input_refs=[f"run:{index}"],
            labeler="qa",
            reviewer="lead",
        )
    return dataset


def _perfect_predictor(sample):
    return {"labels": ["PRODUCT_DEFECT"] if int(sample.sample_id.split("-")[1]) % 2 == 0 else ["ENVIRONMENT"]}


# ── 1. 数据集冻结 ────────────────────────────────────────
def test_dataset_freeze_computes_hash_and_gate_eligibility(db_session):
    dataset = _dataset(db_session, samples=40)
    frozen = freeze_dataset(db_session, dataset.id, approved_by=9)
    assert frozen.status == "FROZEN"
    assert frozen.sample_count == 40
    assert len(frozen.content_hash) == 64
    assert frozen.gate_eligible is True
    assert frozen.approved_by == 9

    small = _dataset(db_session, samples=10, dataset_key="small-ds")
    frozen_small = freeze_dataset(db_session, small.id)
    assert frozen_small.gate_eligible is False


def test_frozen_dataset_cannot_be_modified(db_session):
    dataset = _dataset(db_session, samples=5)
    freeze_dataset(db_session, dataset.id)
    with pytest.raises(BenchmarkError):
        add_sample(db_session, dataset.id, sample_id="late", golden_labels=["X"])


def test_empty_dataset_cannot_freeze(db_session):
    dataset = create_dataset(db_session, project_id=1, dataset_key="empty", task_type="learning")
    with pytest.raises(BenchmarkError):
        freeze_dataset(db_session, dataset.id)


def test_sample_requires_golden_labels(db_session):
    dataset = create_dataset(db_session, project_id=1, dataset_key="labels", task_type="learning")
    with pytest.raises(BenchmarkError):
        add_sample(db_session, dataset.id, sample_id="s1", golden_labels=[])


# ── 2. 指标由后端计算 ───────────────────────────────────
def test_metrics_are_computed_from_labels():
    from app.aiqe.models.benchmark import BenchmarkSample

    samples = [
        BenchmarkSample(dataset_id="d", sample_id="1", golden_labels_json=["A"]),
        BenchmarkSample(dataset_id="d", sample_id="2", golden_labels_json=["A"]),
        BenchmarkSample(dataset_id="d", sample_id="3", golden_labels_json=["B"]),
        BenchmarkSample(dataset_id="d", sample_id="4", golden_labels_json=["C"]),
    ]
    predictions = {"1": ["A"], "2": ["A"], "3": ["B"], "4": ["UNKNOWN"]}
    metrics = compute_metrics(samples, predictions)
    assert metrics.samples == 4
    assert metrics.true_positives == 3
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 1
    assert metrics.precision == 1.0
    assert metrics.recall == pytest.approx(0.75)
    assert 0.8 < metrics.f1 < 0.9
    assert metrics.unknown_rate == 0.25
    assert metrics.gate_eligible is False  # < 30 样本
    assert metrics.meets_thresholds is False


def test_run_benchmark_records_metrics_and_samples(db_session):
    dataset = _dataset(db_session, samples=40)
    freeze_dataset(db_session, dataset.id)
    run = run_benchmark(
        db_session,
        dataset_id=dataset.id,
        agent_key="A4",
        agent_version="1.1.0",
        prompt_hash="sha256:prompt",
        model_provider="deepseek",
        model_name="deepseek-chat",
        predictor=_perfect_predictor,
    )
    assert run.status == "COMPLETED"
    assert run.result_status == "PASS_GATE"
    assert run.metrics_json["precision"] == 1.0
    assert run.metrics_json["recall"] == 1.0
    assert run.metrics_json["samples"] == 40
    assert len(run.per_sample_json) == 40
    assert run.per_sample_json[0]["golden"] == ["PRODUCT_DEFECT"]
    assert run.completed_at is not None


def test_run_requires_frozen_dataset(db_session):
    dataset = _dataset(db_session, samples=5)
    with pytest.raises(BenchmarkError):
        run_benchmark(
            db_session,
            dataset_id=dataset.id,
            agent_key="A4",
            predictor=_perfect_predictor,
        )


def test_small_dataset_is_reference_only(db_session):
    dataset = _dataset(db_session, samples=10)
    freeze_dataset(db_session, dataset.id)
    run = run_benchmark(
        db_session,
        dataset_id=dataset.id,
        agent_key="A4",
        predictor=_perfect_predictor,
    )
    assert run.result_status == "REFERENCE_ONLY"
    assert run.metrics_json["gate_eligible"] is False


def test_below_threshold_status(db_session):
    dataset = _dataset(db_session, samples=40)
    freeze_dataset(db_session, dataset.id)

    def noisy_predictor(sample):
        index = int(sample.sample_id.split("-")[1])
        return {"labels": ["ENVIRONMENT"] if index % 2 == 0 else ["PRODUCT_DEFECT"]}

    run = run_benchmark(
        db_session, dataset_id=dataset.id, agent_key="A4", predictor=noisy_predictor
    )
    assert run.result_status == "BELOW_THRESHOLD"
    assert run.metrics_json["meets_thresholds"] is False


def test_predictor_failure_marks_run_failed(db_session):
    dataset = _dataset(db_session, samples=40)
    freeze_dataset(db_session, dataset.id)

    def boom(sample):
        raise RuntimeError("provider down")

    with pytest.raises(RuntimeError):
        run_benchmark(db_session, dataset_id=dataset.id, agent_key="A4", predictor=boom)
    run = db_session.query(BenchmarkRun).order_by(BenchmarkRun.created_at.desc()).first()
    assert run.status == "FAILED"
    assert "provider down" in run.error_text


def test_compare_with_baseline_delta():
    result = compare_with_baseline(
        {"precision": 0.9, "recall": 0.8, "f1": 0.85},
        {"precision": 0.85, "recall": 0.8, "f1": 0.82},
    )
    assert result["delta"]["precision"] == pytest.approx(0.05)
    assert result["delta"]["recall"] == 0
    assert compare_with_baseline({"precision": 0.9}, None)["baseline"] is None


# ── 3. API 不接受自报指标 ───────────────────────────────
def test_api_rejects_self_reported_metrics(db_session):
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.project import Project, ProjectMember
    from app.models.rbac import Role
    from app.models.user import User

    role = Role(code="tester", name="测试人员", data_scope="project")
    db_session.add(role)
    db_session.flush()
    db_session.add_all(
        [
            User(id=1, username="bench", password="x", nickname="B", email="b@b.local", status=1),
            Project(id=1, code="bench-proj", name="Bench", owner_id=1, status=1),
        ]
    )
    db_session.flush()
    db_session.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db_session.commit()

    def _db():
        yield db_session

    perms = ["menu:aiqe_runs", "defect:list", "defect:update", "aiqe:learning:approve"]

    def _user():
        return CurrentUser(
            user=db_session.get(User, 1),
            permissions=perms,
            project_id=1,
            system_permissions=perms,
        )

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    try:
        client = TestClient(app)
        created = client.post(
            "/api/v1/aiqe/learning/candidates",
            json={"pattern": "自报指标", "description": "x"},
        )
        assert created.status_code == 200, created.text
        candidate_id = created.json()["data"]["id"]
        rejected = client.post(
            f"/api/v1/aiqe/learning/candidates/{candidate_id}/evaluate",
            json={"false_positive_rate": 0.01, "sample_size": 100},
        )
        assert rejected.status_code == 422  # schema 只接受 benchmark_run_id
    finally:
        app.dependency_overrides.clear()
