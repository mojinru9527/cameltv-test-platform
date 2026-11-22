"""M5 / TA-030 + AUD-018：A6 Learning Curator 单测（指标只来自后端 BenchmarkRun）。"""
from __future__ import annotations

import pytest

from app.aiqe.services.benchmark_service import (
    BenchmarkError,
    add_sample,
    create_dataset,
    freeze_dataset,
    run_benchmark,
)
from app.aiqe.services.learning_service import (
    LearningError,
    activate_candidate,
    approve_candidate,
    create_candidate,
    evaluate_candidate,
    get_candidate,
)


def make_benchmark_run(db_session, *, false_positive_rate: float = 0.05, samples: int = 100):
    """构造一个真实 BenchmarkRun：golden 全为 A，按比例把预测改成 B 制造误报。"""
    fps = int(round(samples * false_positive_rate))
    dataset = create_dataset(
        db_session, project_id=1, dataset_key="learning-ds", task_type="learning"
    )
    for index in range(samples):
        add_sample(
            db_session,
            dataset.id,
            sample_id=f"s-{index}",
            golden_labels=["A"],
            labeler="qa",
            reviewer="lead",
        )
    freeze_dataset(db_session, dataset.id)
    return run_benchmark(
        db_session,
        dataset_id=dataset.id,
        agent_key="A6",
        agent_version="1.1.0",
        prompt_hash="sha256:prompt",
        model_provider="deepseek",
        model_name="deepseek-chat",
        predictor=lambda sample: {"labels": ["B"] if int(sample.sample_id.split("-")[1]) < fps else ["A"]},
    )


def candidate(db_session, *, duplicate_of=None, pattern="LIVE_ENTRY_OVERLAY"):
    return create_candidate(
        db_session,
        project_id=1,
        rule={"pattern": pattern, "description": "浮层遮挡"},
        duplicate_of=duplicate_of,
    )


def test_evaluate_uses_backend_metrics_only(db_session):
    run = make_benchmark_run(db_session, false_positive_rate=0.05)
    row = candidate(db_session)
    evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    assert evaluated.status == "benchmarked"
    assert evaluated.benchmark_json["benchmark_run_id"] == run.id
    assert evaluated.benchmark_json["sample_size"] == 100
    assert evaluated.benchmark_json["metrics"]["precision"] > 0.9
    assert evaluated.benchmark_json["false_positive_rate"] < 0.1


def test_evaluate_rejects_unknown_run(db_session):
    row = candidate(db_session)
    # V16-011：跨项目/不存在统一按 LearningError（404 语义）返回。
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, row.id, benchmark_run_id="missing-run")


def test_high_false_positive_rate_rejected(db_session):
    run = make_benchmark_run(db_session, false_positive_rate=0.35)
    row = candidate(db_session)
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=2)


def test_approve_requires_benchmark(db_session):
    row = candidate(db_session)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=2)


def test_duplicate_requires_acknowledgement(db_session):
    run = make_benchmark_run(db_session)
    row = candidate(db_session, duplicate_of="other-pattern")
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=2)
    approved = approve_candidate(db_session, row.id, approved_by=2, acknowledge_duplicate=True)
    assert approved.status == "approved"
    assert approved.acknowledged is True


def test_activate_creates_bug_pattern(db_session):
    run = make_benchmark_run(db_session)
    row = candidate(db_session, pattern="LIVE_ENTRY_OVERLAY_2")
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    approve_candidate(db_session, row.id, approved_by=2)
    pattern = activate_candidate(db_session, row.id)
    assert pattern is not None
    assert pattern.pattern_key == "LIVE_ENTRY_OVERLAY_2"
    assert get_candidate(db_session, row.id).status == "active"


def test_activate_requires_approval(db_session):
    row = candidate(db_session)
    with pytest.raises(LearningError):
        activate_candidate(db_session, row.id)


def test_duplicate_activation_merges(db_session):
    run = make_benchmark_run(db_session)
    first = candidate(db_session, pattern="DUP_PATTERN")
    evaluate_candidate(db_session, first.id, benchmark_run_id=run.id)
    approve_candidate(db_session, first.id, approved_by=2)
    activate_candidate(db_session, first.id)
    second = candidate(db_session, pattern="DUP_PATTERN_OTHER", duplicate_of=first.id)
    evaluate_candidate(db_session, second.id, benchmark_run_id=run.id)
    approve_candidate(db_session, second.id, approved_by=2, acknowledge_duplicate=True)
    activate_candidate(db_session, second.id)
    assert get_candidate(db_session, second.id).status == "active"


def test_small_dataset_is_reference_only(db_session):
    run = make_benchmark_run(db_session, samples=10, false_positive_rate=0.0)
    assert run.result_status == "REFERENCE_ONLY"
    assert run.metrics_json["gate_eligible"] is False
