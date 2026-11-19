"""M5 / TA-030：A6 Learning Curator（候选规则 → benchmark → 人审 → ACTIVE）。

护栏：
- 未 benchmark 不得批准；
- 误报率 > 20% 不得批准；
- 重复候选必须人工确认（acknowledged），且激活时合并到已有 pattern，不新增重复规则。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.learning import BugPattern, LearningCandidate

FALSE_POSITIVE_LIMIT = 0.2
STATUSES = ("draft", "benchmarked", "approved", "active", "rejected")


class LearningError(ValueError):
    pass


def create_candidate(
    db: Session,
    *,
    project_id: int,
    rule: dict[str, Any],
    source: str = "bug",
    duplicate_of: str | None = None,
    created_by: int | None = None,
) -> LearningCandidate:
    if not isinstance(rule, dict) or not str(rule.get("pattern") or "").strip():
        raise LearningError("候选规则必须包含非空 pattern")
    row = LearningCandidate(
        project_id=project_id,
        rule_json=rule,
        source=source,
        duplicate_of=duplicate_of,
        created_by=created_by,
        status="draft",
    )
    db.add(row)
    db.flush()
    return row


def get_candidate(
    db: Session, candidate_id: str, *, project_id: int | None = None
) -> LearningCandidate:
    row = db.get(LearningCandidate, candidate_id)
    if row is None or (
        project_id is not None and int(row.project_id or 0) != int(project_id)
    ):
        raise LearningError(f"候选不存在: {candidate_id}")
    return row


GATE_POLICY_VERSION = "V16-010.1"
MIN_GATE_SAMPLES = 30
FALSE_POSITIVE_LIMIT = 0.2
UNKNOWN_RATE_LIMIT = 0.3
REGRESSION_TOLERANCE = 0.02
METRIC_KEYS = ("precision", "recall", "f1")


def _rule_hash(rule: dict[str, Any]) -> str:
    import hashlib
    import json

    canonical = json.dumps(rule, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dataset_checksum(db: Session, dataset_id: str) -> str:
    from app.aiqe.services import benchmark_service

    dataset = benchmark_service.get_dataset(db, dataset_id)
    return benchmark_service.compute_content_hash(
        benchmark_service.list_samples(db, dataset.id)
    )


def _baseline_candidate(db: Session, *, project_id: int, exclude_id: str) -> LearningCandidate | None:
    return db.scalar(
        select(LearningCandidate)
        .where(
            LearningCandidate.project_id == int(project_id),
            LearningCandidate.id != str(exclude_id),
            LearningCandidate.published_at.is_not(None),
            LearningCandidate.revoked_at.is_(None),
        )
        .order_by(LearningCandidate.published_at.desc())
    )


def _evaluate_gate(
    db: Session,
    *,
    candidate: LearningCandidate,
    run: Any,
    dataset: Any,
    metrics: dict[str, Any],
    dataset_checksum: str,
) -> tuple[str, list[str], dict[str, Any]]:
    """服务端唯一 gate 判定；返回 (PASS/REJECT, reasons, snapshot)。"""
    reasons: list[str] = []
    if str(run.status) != "COMPLETED":
        reasons.append("BENCHMARK_RUN_NOT_COMPLETED")
    if str(run.result_status) != "PASS_GATE":
        reasons.append(f"RESULT_STATUS_{run.result_status or 'EMPTY'}")
    if not bool(metrics.get("gate_eligible")):
        reasons.append("GATE_NOT_ELIGIBLE")
    samples = int(metrics.get("samples") or 0)
    if samples < MIN_GATE_SAMPLES:
        reasons.append(f"SAMPLE_COUNT_BELOW_MIN({samples}<{MIN_GATE_SAMPLES})")
    if not bool(metrics.get("meets_thresholds")):
        reasons.append("THRESHOLDS_NOT_MET")
    for key in METRIC_KEYS:
        if metrics.get(key) is None:
            reasons.append(f"METRIC_MISSING_{key.upper()}")
    true_positives = int(metrics.get("true_positives") or 0)
    false_positives = int(metrics.get("false_positives") or 0)
    denominator = true_positives + false_positives
    fpr = (false_positives / denominator) if denominator else 0.0
    if fpr > FALSE_POSITIVE_LIMIT:
        reasons.append(f"FALSE_POSITIVE_RATE_TOO_HIGH({fpr:.3f}>{FALSE_POSITIVE_LIMIT})")
    unknown_rate = float(metrics.get("unknown_rate") or 0.0)
    if unknown_rate > UNKNOWN_RATE_LIMIT:
        reasons.append(f"UNKNOWN_RATE_TOO_HIGH({unknown_rate:.3f}>{UNKNOWN_RATE_LIMIT})")
    if str(dataset.status) != "FROZEN":
        reasons.append("DATASET_NOT_FROZEN")
    if not str(dataset.content_hash or ""):
        reasons.append("DATASET_CHECKSUM_MISSING")
    elif dataset_checksum != str(dataset.content_hash):
        reasons.append("DATASET_CHECKSUM_MISMATCH")
    if str(run.dataset_id) != str(dataset.id):
        reasons.append("RUN_DATASET_MISMATCH")
    rule = dict(candidate.rule_json or {})
    expected_agent = str(rule.get("agent_version") or "")
    if expected_agent and expected_agent != str(run.agent_version or ""):
        reasons.append("AGENT_VERSION_MISMATCH")
    expected_prompt = str(rule.get("prompt_hash") or "")
    if expected_prompt and expected_prompt != str(run.prompt_hash or ""):
        reasons.append("PROMPT_HASH_MISMATCH")
    baseline = _baseline_candidate(db, project_id=int(candidate.project_id), exclude_id=candidate.id)
    baseline_metrics: dict[str, Any] = {}
    baseline_version = ""
    if baseline is not None:
        baseline_version = str(baseline.id)
        baseline_run_id = str((baseline.benchmark_json or {}).get("benchmark_run_id") or "")
        if baseline_run_id:
            try:
                from app.aiqe.services import benchmark_service

                baseline_metrics = benchmark_service.metrics_of(db, baseline_run_id)
            except Exception:
                reasons.append("BASELINE_METRICS_UNAVAILABLE")
        if baseline_metrics:
            for key in METRIC_KEYS:
                current_value = float(metrics.get(key) or 0.0)
                base_value = float(baseline_metrics.get(key) or 0.0)
                if current_value + REGRESSION_TOLERANCE < base_value:
                    reasons.append(
                        f"REGRESSION_{key.upper()}({current_value:.3f}<{base_value:.3f})"
                    )
    else:
        reasons.append("BOOTSTRAP_NO_PUBLISHED_BASELINE")
    decision = "PASS" if not reasons or reasons == ["BOOTSTRAP_NO_PUBLISHED_BASELINE"] else "REJECT"
    snapshot = {
        "gate_policy_version": GATE_POLICY_VERSION,
        "benchmark_run_id": run.id,
        "dataset_id": dataset.id,
        "dataset_checksum": dataset_checksum,
        "metrics": dict(metrics),
        "false_positive_rate": fpr,
        "unknown_rate": unknown_rate,
        "samples": samples,
        "baseline_candidate_id": baseline_version,
        "baseline_metrics": baseline_metrics,
        "candidate_rule_hash": _rule_hash(rule),
        "agent_version": str(run.agent_version or ""),
        "prompt_hash": str(run.prompt_hash or ""),
        "model_provider": str(run.model_provider or ""),
        "model_name": str(run.model_name or ""),
        "gate_decision": decision,
        "gate_reasons": reasons,
    }
    return decision, reasons, snapshot


def evaluate_candidate(
    db: Session,
    candidate_id: str,
    benchmark: dict[str, Any] | None = None,
    *,
    benchmark_run_id: str,
    project_id: int | None = None,
) -> LearningCandidate:
    """V16-010：只接受 benchmark_run_id，服务端读取 Run/数据集并计算 gate。"""
    from app.aiqe.services import benchmark_service

    row = get_candidate(db, candidate_id, project_id=project_id)
    try:
        run = benchmark_service.get_run(
            db, str(benchmark_run_id), project_id=row.project_id
        )
    except benchmark_service.BenchmarkError as exc:
        raise LearningError(str(exc)) from exc
    if run.project_id is not None and int(run.project_id) != int(row.project_id):
        raise LearningError("BenchmarkRun 属于其他项目，拒绝评估")
    dataset = benchmark_service.get_dataset(db, run.dataset_id, project_id=row.project_id)
    if dataset.project_id is not None and int(dataset.project_id) != int(row.project_id):
        raise LearningError("数据集属于其他项目，拒绝评估")
    metrics = benchmark_service.metrics_of(db, run.id, project_id=row.project_id)
    if int(metrics.get("samples") or 0) <= 0:
        raise LearningError("BenchmarkRun 没有有效样本，不能作为评估依据")
    dataset_checksum = _dataset_checksum(db, dataset.id)
    decision, reasons, snapshot = _evaluate_gate(
        db,
        candidate=row,
        run=run,
        dataset=dataset,
        metrics=metrics,
        dataset_checksum=dataset_checksum,
    )
    row.benchmark_run_id = run.id
    row.dataset_checksum = dataset_checksum
    row.baseline_version = str(snapshot.get("baseline_candidate_id") or "")
    row.gate_policy_version = GATE_POLICY_VERSION
    row.gate_decision = decision
    row.gate_reasons_json = list(reasons)
    row.evaluation_snapshot_json = snapshot
    row.rule_hash = str(snapshot["candidate_rule_hash"])
    row.benchmark_json = {
        "benchmark_run_id": run.id,
        "dataset_id": dataset.id,
        "dataset_checksum": dataset_checksum,
        "sample_size": int(metrics.get("samples") or 0),
        "metrics": metrics,
        "false_positive_rate": snapshot["false_positive_rate"],
        "unknown_rate": snapshot["unknown_rate"],
        "gate_eligible": metrics.get("gate_eligible"),
        "meets_thresholds": metrics.get("meets_thresholds"),
        "result_status": run.result_status,
        "gate_decision": decision,
        "gate_reasons": list(reasons),
        "gate_policy_version": GATE_POLICY_VERSION,
    }
    # V16-010：不无条件标记 benchmarked —— gate 拒绝时进入 rejected。
    row.status = "benchmarked" if decision == "PASS" else "rejected"
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def _resolve_approver(candidate: LearningCandidate, approved_by: int | None) -> int:
    if approved_by is None:
        raise LearningError("审批必须提供 approved_by（人工审批身份）")
    # 自动化服务身份发起 → 禁止自审；人类用户自审按组织策略允许（可用配置收紧）。
    if (
        candidate.created_by is not None
        and int(candidate.created_by) == int(approved_by)
        and str(candidate.source or "").lower() in {"automation", "agent", "auto"}
    ):
        raise LearningError("审批人不能是候选发起者（自动化服务身份）")
    return int(approved_by)


def _revalidate(db: Session, row: LearningCandidate) -> None:
    """审批/发布前重读最新 Run/数据集/候选，避免评估后被篡改。"""
    from app.aiqe.services import benchmark_service

    run_id = str(row.benchmark_run_id or "")
    if not run_id:
        raise LearningError("候选缺少 benchmark_run_id，必须先评估")
    run = benchmark_service.get_run(db, run_id)
    if int(run.project_id or 0) != int(row.project_id):
        raise LearningError("BenchmarkRun 项目不一致")
    dataset = benchmark_service.get_dataset(db, run.dataset_id)
    if str(dataset.status) != "FROZEN":
        raise LearningError("数据集已不再冻结，拒绝审批")
    checksum = _dataset_checksum(db, dataset.id)
    if checksum != str(row.dataset_checksum or ""):
        raise LearningError("数据集在评估后发生变化，拒绝审批")
    if _rule_hash(dict(row.rule_json or {})) != str(row.rule_hash or ""):
        raise LearningError("候选规则在评估后发生变化，拒绝审批")
    metrics = benchmark_service.metrics_of(db, run.id)
    snapshot = dict(row.evaluation_snapshot_json or {})
    if dict(snapshot.get("metrics") or {}) != dict(metrics):
        raise LearningError("BenchmarkRun 指标在评估后发生变化，拒绝审批")
    if str(run.result_status) != "PASS_GATE":
        raise LearningError("BenchmarkRun 不是 PASS_GATE，拒绝审批")
    if str(row.gate_decision) != "PASS":
        raise LearningError(f"gate 未通过，拒绝审批: {row.gate_reasons_json}")


def approve_candidate(
    db: Session,
    candidate_id: str,
    *,
    approved_by: int | None = None,
    acknowledge_duplicate: bool = False,
    approval_reason: str = "",
    project_id: int | None = None,
) -> LearningCandidate:
    row = get_candidate(db, candidate_id, project_id=project_id)
    if row.status not in ("benchmarked",):
        raise LearningError(f"必须先通过 benchmark gate 才能批准（当前 {row.status}）")
    approver = _resolve_approver(row, approved_by)
    _revalidate(db, row)
    if row.duplicate_of and not (acknowledge_duplicate or row.acknowledged):
        raise LearningError("重复候选需人工确认（acknowledge_duplicate）")
    row.acknowledged = True
    row.status = "approved"
    row.approved_by = approver
    row.approved_at = datetime.now(UTC)
    row.approval_reason = str(approval_reason or "")[:500]
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def publish_candidate(
    db: Session,
    candidate_id: str,
    *,
    approved_by: int | None,
    project_id: int | None = None,
) -> BugPattern | None:
    """发布前再次校验 Run 未撤销/数据集/候选版本未变，然后激活。"""
    row = get_candidate(db, candidate_id, project_id=project_id)
    if row.status != "approved":
        raise LearningError("只有 approved 候选才能发布")
    _resolve_approver(row, approved_by)
    _revalidate(db, row)
    if row.revoked_at is not None:
        raise LearningError("候选已撤销，不能发布")
    pattern = _activate_pattern(db, row)
    row.published_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    db.flush()
    return pattern


def revoke_candidate(
    db: Session, candidate_id: str, *, project_id: int | None = None, reason: str = ""
) -> LearningCandidate:
    row = get_candidate(db, candidate_id, project_id=project_id)
    if row.status not in ("approved", "active"):
        raise LearningError("只有已批准/已发布候选才能撤销")
    row.status = "revoked"
    row.revoked_at = datetime.now(UTC)
    row.approval_reason = str(reason or row.approval_reason or "")[:500]
    pattern = db.scalar(
        select(BugPattern).where(BugPattern.source_candidate_id == row.id)
    )
    if pattern is not None:
        pattern.status = "revoked"
    previous = _baseline_candidate(db, project_id=int(row.project_id), exclude_id=row.id)
    if previous is not None and previous.status == "active":
        previous_pattern = db.scalar(
            select(BugPattern).where(BugPattern.source_candidate_id == previous.id)
        )
        if previous_pattern is not None:
            previous_pattern.status = "active"
    db.flush()
    return row


def _activate_pattern(db: Session, row: LearningCandidate) -> BugPattern | None:
    if row.duplicate_of:
        row.status = "active"
        row.updated_at = datetime.now(UTC)
        db.flush()
        return None
    key = str(row.rule_json["pattern"]).strip()
    existing = db.scalar(select(BugPattern).where(BugPattern.pattern_key == key))
    if existing is not None:
        row.duplicate_of = existing.id
        existing.status = "active"
        row.status = "active"
        row.updated_at = datetime.now(UTC)
        db.flush()
        return existing
    pattern = BugPattern(
        pattern_key=key,
        description=str(row.rule_json.get("description") or ""),
        status="active",
        source_candidate_id=row.id,
    )
    db.add(pattern)
    row.status = "active"
    row.updated_at = datetime.now(UTC)
    db.flush()
    return pattern


def activate_candidate(
    db: Session, candidate_id: str, *, project_id: int | None = None
) -> BugPattern | None:
    row = get_candidate(db, candidate_id, project_id=project_id)
    if row.status != "approved":
        raise LearningError("只有 approved 候选才能 ACTIVE")
    if row.published_at is None:
        return publish_candidate(db, candidate_id, approved_by=row.approved_by, project_id=project_id)
    return _activate_pattern(db, row)


def list_candidates(db: Session, project_id: int) -> list[LearningCandidate]:
    return list(
        db.scalars(
            select(LearningCandidate)
            .where(LearningCandidate.project_id == project_id)
            .order_by(LearningCandidate.created_at.desc())
        )
    )

def list_bug_patterns(
    db: Session, *, status: str | None = "active", limit: int = 100
) -> list[BugPattern]:
    """batch-349：BugPattern 只读查询（Console 学习页）。"""
    stmt = select(BugPattern).order_by(BugPattern.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(BugPattern.status == status)
    return list(db.scalars(stmt))
