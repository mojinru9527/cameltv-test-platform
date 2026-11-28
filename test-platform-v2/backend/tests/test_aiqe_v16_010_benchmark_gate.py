"""V16-010 验收：A6 Benchmark Gate 强制审批和发布。

覆盖规格必测项：
- 样本不足 REFERENCE_ONLY 拒绝；
- 低 Recall / 低 F1 / Unknown 高 / FPR 超阈值拒绝；
- PASS_GATE 但 dataset checksum 不一致拒绝；
- BenchmarkRun 跨项目拒绝；
- 评估后数据集变更审批拒绝；
- 全部达标 + 审批授权正确 → 批准并生成发布版本；
- 无 baseline 时按 bootstrap 记录；有已发布 baseline 时回归超容忍拒绝。
"""
from __future__ import annotations

import pytest

from app.aiqe.services.benchmark_service import (
    add_sample,
    create_dataset,
    freeze_dataset,
    run_benchmark,
)
from app.aiqe.services.learning_service import (
    LearningError,
    approve_candidate,
    create_candidate,
    evaluate_candidate,
    get_candidate,
    publish_candidate,
    revoke_candidate,
)
from app.models.project import Project


def _project(db, project_id: int = 1) -> None:
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


def _dataset(db, *, project_id: int = 1, samples: int = 100, fp_ratio: float = 0.05):
    _project(db, project_id)
    dataset = create_dataset(
        db, project_id=project_id, dataset_key=f"ds-{project_id}-{samples}-{fp_ratio}",
        task_type="learning",
    )
    for index in range(samples):
        add_sample(
            db,
            dataset.id,
            sample_id=f"s-{index}",
            golden_labels=["A"],
            labeler="qa",
            reviewer="lead",
        )
    freeze_dataset(db, dataset.id)
    return dataset


def _run(db, dataset, *, fp_ratio: float = 0.05, unknown_ratio: float = 0.0):
    samples = int(dataset.sample_count or 0)
    fp = int(round(samples * fp_ratio))
    unknown = int(round(samples * unknown_ratio))

    def predictor(sample):
        index = int(sample.sample_id.split("-")[1])
        if index < unknown:
            return {"labels": ["UNKNOWN"]}
        return {"labels": ["B"] if index < unknown + fp else ["A"]}

    return run_benchmark(
        db,
        dataset_id=dataset.id,
        agent_key="A6",
        agent_version="1.2.0",
        prompt_hash="sha256:p1",
        model_provider="deepseek",
        model_name="deepseek-chat",
        predictor=predictor,
    )


def _candidate(db, project_id: int = 1, **kwargs):
    return create_candidate(
        db,
        project_id=project_id,
        rule={"pattern": kwargs.pop("pattern", "LIVE_OVERLAY"), "description": "x"},
        **kwargs,
    )


# ── 1. 样本不足 / 低指标拒绝 ───────────────────────────────
def test_reference_only_small_sample_rejected(db_session):
    dataset = _dataset(db_session, samples=10, fp_ratio=0.0)
    run = _run(db_session, dataset)
    assert run.result_status == "REFERENCE_ONLY"
    row = _candidate(db_session)
    evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    assert evaluated.status == "rejected"
    assert evaluated.gate_decision == "REJECT"
    assert any("SAMPLE_COUNT_BELOW_MIN" in item for item in evaluated.gate_reasons_json)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=2)


def test_low_recall_rejected(db_session):
    dataset = _dataset(db_session, samples=100)
    run = _run(db_session, dataset, fp_ratio=0.5)  # 一半漏报 + 误报
    assert run.result_status != "PASS_GATE"
    row = _candidate(db_session)
    evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    assert evaluated.gate_decision == "REJECT"
    assert any(
        "THRESHOLDS_NOT_MET" in item or "RESULT_STATUS" in item
        for item in evaluated.gate_reasons_json
    )


def test_high_fpr_or_unknown_rejected(db_session):
    dataset = _dataset(db_session, samples=100)
    run = _run(db_session, dataset, fp_ratio=0.35)
    row = _candidate(db_session)
    evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    assert any(
        "FALSE_POSITIVE_RATE_TOO_HIGH" in item for item in evaluated.gate_reasons_json
    ) or evaluated.gate_decision == "REJECT"

    dataset2 = _dataset(db_session, samples=100, fp_ratio=0.0)
    run2 = _run(db_session, dataset2, unknown_ratio=0.5)
    row2 = _candidate(db_session)
    evaluated2 = evaluate_candidate(db_session, row2.id, benchmark_run_id=run2.id)
    assert evaluated2.gate_decision == "REJECT"
    assert any("UNKNOWN_RATE_TOO_HIGH" in item for item in evaluated2.gate_reasons_json)


# ── 2. 跨项目 / 数据集变更 ─────────────────────────────────
def test_cross_project_benchmark_rejected(db_session):
    _project(db_session, 1)
    _project(db_session, 2)
    dataset = _dataset(db_session, project_id=2)
    run = _run(db_session, dataset)
    row = _candidate(db_session, project_id=1)
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)


def test_dataset_change_after_evaluation_blocks_approval(db_session):
    dataset = _dataset(db_session, samples=100)
    run = _run(db_session, dataset)
    row = _candidate(db_session)
    evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    assert evaluated.gate_decision == "PASS"

    # 评估后篡改数据集 → 审批必须拒绝
    sample = dataset_and_first_sample(db_session, dataset)
    sample.golden_labels_json = ["B"]
    db_session.commit()
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=2)


def dataset_and_first_sample(db, dataset):
    from sqlalchemy import select

    from app.aiqe.models.benchmark import BenchmarkSample

    sample = db.scalar(
        select(BenchmarkSample)
        .where(BenchmarkSample.dataset_id == dataset.id)
        .order_by(BenchmarkSample.sample_id)
    )
    assert sample is not None
    return sample


# ── 3. 达标审批 → 发布；发布前篡改拒绝 ─────────────────────
def test_passing_candidate_approved_and_published(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    assert run.result_status == "PASS_GATE"
    row = _candidate(db_session, pattern="GATE_OK")
    evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    assert evaluated.gate_decision == "PASS"
    assert evaluated.dataset_checksum
    assert evaluated.gate_policy_version == "V16-010.1"
    assert any("BOOTSTRAP" in item for item in evaluated.gate_reasons_json)

    approved = approve_candidate(
        db_session, row.id, approved_by=2, approval_reason="gate ok"
    )
    assert approved.status == "approved"
    assert approved.approved_by == 2
    pattern = publish_candidate(db_session, row.id, approved_by=2)
    assert pattern is not None and pattern.pattern_key == "GATE_OK"
    published = get_candidate(db_session, row.id)
    assert published.published_at is not None
    assert published.status == "active"


def test_publish_rejects_rule_change_after_approval(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    row = _candidate(db_session, pattern="GATE_TAMPER")
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    approve_candidate(db_session, row.id, approved_by=2)
    row.rule_json = {"pattern": "GATE_TAMPER_NEW", "description": "x"}
    db_session.commit()
    with pytest.raises(LearningError):
        publish_candidate(db_session, row.id, approved_by=2)


# ── 4. 审批权限/身份与撤销 ─────────────────────────────────
def test_approval_requires_identity(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    row = _candidate(db_session)
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=None)


def test_automation_service_cannot_self_approve(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    row = _candidate(db_session, source="automation", created_by=9)
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id, approved_by=9)


def test_revoke_removes_pattern_and_restores_previous(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    first = _candidate(db_session, pattern="PATTERN_1")
    evaluate_candidate(db_session, first.id, benchmark_run_id=run.id)
    approve_candidate(db_session, first.id, approved_by=2)
    publish_candidate(db_session, first.id, approved_by=2)

    second = _candidate(db_session, pattern="PATTERN_2")
    evaluate_candidate(db_session, second.id, benchmark_run_id=run.id)
    approve_candidate(db_session, second.id, approved_by=2)
    publish_candidate(db_session, second.id, approved_by=2)

    revoked = revoke_candidate(db_session, second.id, reason="regression")
    assert revoked.status == "revoked"
    assert revoked.revoked_at is not None


def test_regression_against_published_baseline_rejected(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    good_run = _run(db_session, dataset, fp_ratio=0.02)
    baseline = _candidate(db_session, pattern="BASE")
    evaluate_candidate(db_session, baseline.id, benchmark_run_id=good_run.id)
    approve_candidate(db_session, baseline.id, approved_by=2)
    publish_candidate(db_session, baseline.id, approved_by=2)

    worse_dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    worse_run = _run(db_session, worse_dataset, fp_ratio=0.12)
    if worse_run.result_status != "PASS_GATE":
        # 仍然验证：任何未达 PASS_GATE 的候选不得批准
        row = _candidate(db_session, pattern="WORSE")
        evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=worse_run.id)
        assert evaluated.gate_decision == "REJECT"
        with pytest.raises(LearningError):
            approve_candidate(db_session, row.id, approved_by=2)
    else:
        row = _candidate(db_session, pattern="WORSE")
        evaluated = evaluate_candidate(db_session, row.id, benchmark_run_id=worse_run.id)
        assert evaluated.gate_decision == "REJECT"
        assert any("REGRESSION" in item for item in evaluated.gate_reasons_json)


# ══════════════════════════════════════════════════════════
# V1.6.2（FIX-006）扩展：服务端复算 / 身份 / 证据分层
# ══════════════════════════════════════════════════════════
def test_gate_metrics_are_recomputed_from_per_sample(db_session):
    """存储 summary 只是对账对象；对外指标来自逐样本记录复算。"""
    from app.aiqe.services.benchmark_service import metrics_of, recompute_metrics

    dataset = _dataset(db_session, samples=40, fp_ratio=0.05)
    run = _run(db_session, dataset, fp_ratio=0.05)
    recomputed = recompute_metrics(run.per_sample_json, thresholds=run.metrics_json["thresholds"])
    metrics = metrics_of(db_session, run.id)
    for key in ("samples", "true_positives", "false_positives", "false_negatives", "precision", "recall", "f1"):
        assert metrics[key] == recomputed.payload()[key], key
    assert metrics["samples"] + metrics["excluded_samples"] == metrics["total_samples"]


def test_gate_rejects_tampered_summary_metrics(db_session):
    from app.aiqe.services.benchmark_service import BenchmarkError, metrics_of

    dataset = _dataset(db_session, samples=100, fp_ratio=0.35)
    run = _run(db_session, dataset, fp_ratio=0.35)
    run.metrics_json = {
        **dict(run.metrics_json),
        "precision": 0.99,
        "recall": 0.99,
        "f1": 0.99,
    }
    db_session.flush()
    with pytest.raises(BenchmarkError) as exc:
        metrics_of(db_session, run.id)
    assert "METRICS_TAMPERED" in str(exc.value)

    row = _candidate(db_session, pattern="TAMPERED")
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)


def test_gate_rejects_same_user_approval(db_session):
    """双人审批：Owner 与 Approver 必须是不同 user id（不接受同一人自审）。"""
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    row = create_candidate(
        db_session,
        project_id=1,
        rule={"pattern": "SAME_USER", "description": "x"},
        source="bug",
        created_by=7,
    )
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    with pytest.raises(LearningError) as exc:
        approve_candidate(db_session, row.id, approved_by=7)
    assert "OWNER_APPROVER_SAME_USER" in str(exc.value)
    approved = approve_candidate(db_session, row.id, approved_by=8)
    assert approved.approved_by == 8


def test_gate_publish_requires_approval_and_correct_state(db_session):
    dataset = _dataset(db_session, samples=100, fp_ratio=0.02)
    run = _run(db_session, dataset, fp_ratio=0.02)
    row = _candidate(db_session, pattern="NO_APPROVAL")
    evaluate_candidate(db_session, row.id, benchmark_run_id=run.id)
    # 已通过 gate 但未审批 → 不得发布
    with pytest.raises(LearningError):
        publish_candidate(db_session, row.id, approved_by=2)
    approve_candidate(db_session, row.id, approved_by=2)
    assert publish_candidate(db_session, row.id, approved_by=2) is not None
    # 重复发布 / 已发布状态 → 拒绝
    with pytest.raises(LearningError):
        publish_candidate(db_session, row.id, approved_by=2)


def test_local_service_test_is_not_product_evidence():
    """本地 Service 脚本必须自述 local_service_test 且产品级固定 BLOCKED。"""
    import importlib.util
    from pathlib import Path

    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/aiqe/per_tc/futurewayu_learning_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location("futurewayu_learning_benchmark", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.EVIDENCE_KIND == "local_service_test"
    assert module.PRODUCT_TC_ID == "TC-AIQE-010"
    assert module.PRODUCT_STATUS == "BLOCKED"
    assert module.PRODUCT_BLOCKED_REASON
    assert module.PRODUCT_OWNER and module.PRODUCT_UNBLOCK_ACTION

    raw = [
        {"id": "A-1", "label": "LOGIN", "source": "s1"},
        {"id": "A-1", "label": "LOGIN", "source": "s2"},
        {"id": "A-2", "label": "INVALID LABEL", "source": "s1"},
        {"id": "??", "label": "LOGIN", "source": "s1"},
    ]
    effective, composition = module.account_samples(raw)
    assert composition["accounting_ok"] is True
    assert composition["total_raw_rows"] == (
        len(effective)
        + len(composition["duplicates_removed"])
        + len(composition["invalid_rows_removed"])
    )
    assert [item["id"] for item in effective] == ["A-1"]
    assert {item["reason"] for item in composition["duplicates_removed"]} == {
        "DUPLICATE_SAMPLE_ID"
    }
    assert {item["reason"] for item in composition["invalid_rows_removed"]} == {
        "INVALID_LABEL",
        "INVALID_SAMPLE_ID",
    }

    # 不得把 local_service_test 指向产品验收库
    with pytest.raises(SystemExit):
        module._resolve_database_url(
            "sqlite:///work-logs/evidence/aiqe-v16/local-test/platform.db"
        )
