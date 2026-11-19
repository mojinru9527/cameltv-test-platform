"""V16-011 验收：Benchmark / Learning 全资源 Project Scope。

要求：Service 层所有敏感读写同时带 resource_id + project_id；
跨项目 get/add_sample/freeze/run/metrics/evaluate/approve/publish 全部拒绝，
不能仅依赖 API 层过滤。
"""
from __future__ import annotations

import pytest

from app.aiqe.services.benchmark_service import (
    BenchmarkError,
    add_sample,
    create_dataset,
    freeze_dataset,
    get_dataset,
    get_run,
    metrics_of,
    run_benchmark,
)
from app.aiqe.services.learning_service import (
    LearningError,
    approve_candidate,
    create_candidate,
    evaluate_candidate,
    get_candidate,
    publish_candidate,
)
from app.models.project import Project


def _project(db, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        db.add(
            Project(
                id=project_id,
                code=f"P{project_id}",
                name=f"Project {project_id}",
                owner_id=1,
                status=1,
            )
        )
        db.flush()


def _frozen_dataset(db, project_id: int, *, key: str, samples: int = 100):
    _project(db, project_id)
    dataset = create_dataset(
        db, project_id=project_id, dataset_key=key, task_type="learning"
    )
    for index in range(samples):
        add_sample(
            db,
            dataset.id,
            project_id=project_id,
            sample_id=f"s-{index}",
            golden_labels=["A"],
        )
    freeze_dataset(db, dataset.id, project_id=project_id)
    return dataset


def _run(db, dataset, *, project_id: int, fp_ratio: float = 0.02):
    fp = int(round(int(dataset.sample_count or 0) * fp_ratio))
    return run_benchmark(
        db,
        dataset_id=dataset.id,
        project_id=project_id,
        agent_key="A6",
        agent_version="1.0.0",
        prompt_hash="sha256:p",
        model_provider="deepseek",
        model_name="deepseek-chat",
        predictor=lambda sample: {
            "labels": ["B"] if int(sample.sample_id.split("-")[1]) < fp else ["A"]
        },
    )


# ── 1. Dataset 跨项目 ──────────────────────────────────────
def test_dataset_cross_project_read_rejected(db_session):
    dataset = _frozen_dataset(db_session, 1, key="scope-a")
    _project(db_session, 2)
    with pytest.raises(BenchmarkError):
        get_dataset(db_session, dataset.id, project_id=2)


def test_add_sample_cross_project_rejected(db_session):
    dataset = _frozen_dataset(db_session, 1, key="scope-b", samples=10)
    # 重新开一个 DRAFT 数据集用于追加
    other = create_dataset(db_session, project_id=1, dataset_key="scope-b-draft", task_type="learning")
    with pytest.raises(BenchmarkError):
        add_sample(
            db_session,
            other.id,
            project_id=2,
            sample_id="x",
            golden_labels=["A"],
        )
    assert dataset.id != other.id


def test_freeze_cross_project_rejected(db_session):
    dataset = create_dataset(
        db_session, project_id=1, dataset_key="scope-freeze", task_type="learning"
    )
    add_sample(db_session, dataset.id, project_id=1, sample_id="s", golden_labels=["A"])
    with pytest.raises(BenchmarkError):
        freeze_dataset(db_session, dataset.id, project_id=2)


# ── 2. BenchmarkRun 跨项目 ─────────────────────────────────
def test_run_benchmark_cross_project_rejected(db_session):
    dataset = _frozen_dataset(db_session, 1, key="scope-run")
    with pytest.raises(BenchmarkError):
        _run(db_session, dataset, project_id=2)


def test_metrics_and_run_cross_project_rejected(db_session):
    dataset = _frozen_dataset(db_session, 1, key="scope-metrics")
    run = _run(db_session, dataset, project_id=1)
    with pytest.raises(BenchmarkError):
        get_run(db_session, run.id, project_id=2)
    with pytest.raises(BenchmarkError):
        metrics_of(db_session, run.id, project_id=2)


# ── 3. LearningCandidate / 关联资源 ─────────────────────────
def test_candidate_cross_project_rejected(db_session):
    _project(db_session, 1)
    _project(db_session, 2)
    row = create_candidate(db_session, project_id=1, rule={"pattern": "SCOPE_X"})
    with pytest.raises(LearningError):
        get_candidate(db_session, row.id, project_id=2)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, project_id=2, approved_by=9)
    with pytest.raises(LearningError):
        publish_candidate(db_session, row.id, project_id=2, approved_by=9)


def test_evaluate_cross_project_benchmark_rejected(db_session):
    _project(db_session, 1)
    dataset_b = _frozen_dataset(db_session, 2, key="scope-bench-b")
    run_b = _run(db_session, dataset_b, project_id=2)
    row = create_candidate(db_session, project_id=1, rule={"pattern": "SCOPE_Y"})
    with pytest.raises(LearningError):
        evaluate_candidate(
            db_session, row.id, benchmark_run_id=run_b.id, project_id=1
        )


def test_related_resources_must_share_project(db_session):
    """数据集属于 A、Run 被伪造成 B：evaluate 必须拒绝，不能只看 ID。"""
    dataset = _frozen_dataset(db_session, 1, key="scope-share")
    run = _run(db_session, dataset, project_id=1)
    run.project_id = 2
    db_session.commit()
    row = create_candidate(db_session, project_id=1, rule={"pattern": "SCOPE_Z"})
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, row.id, benchmark_run_id=run.id, project_id=1)
