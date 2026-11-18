"""AUD-018：Benchmark 执行与**后端计算**指标（不接受 Agent 自报）。

v1.5 §03 AUD-018：

- 数据集必须冻结（content_hash + sample_count），``sample_count < 30`` 只能作为实验参考，
  不得用于自动门禁；
- 正式 Benchmark 必须真实调用 Agent；预测结果与 golden labels 由代码确定性比较；
- 指标（Precision/Recall/F1/Unknown rate 等）由系统计算并落库，API 不接受自报数值；
- 连续版本必须与 baseline 对照，不达门槛不得批准发布。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.benchmark import BenchmarkDataset, BenchmarkRun, BenchmarkSample

GATING_MIN_SAMPLES = 30
DEFAULT_THRESHOLDS: dict[str, float] = {
    "precision": 0.80,
    "recall": 0.80,
    "f1": 0.75,
}
DATASET_STATUSES: tuple[str, ...] = ("DRAFT", "FROZEN", "RETIRED")
TASK_TYPES: tuple[str, ...] = (
    "requirement",
    "test_design",
    "workflow",
    "triage",
    "learning",
    "change_impact",
)


class BenchmarkError(ValueError):
    pass


@dataclass(frozen=True)
class BenchmarkMetrics:
    samples: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    unknown_rate: float
    gate_eligible: bool
    meets_thresholds: bool
    thresholds: Mapping[str, float]

    def payload(self) -> dict[str, Any]:
        return {
            "samples": self.samples,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "unknown_rate": round(self.unknown_rate, 4),
            "gate_eligible": self.gate_eligible,
            "meets_thresholds": self.meets_thresholds,
            "thresholds": dict(self.thresholds),
        }

    @property
    def false_positive_rate(self) -> float:
        denominator = self.true_positives + self.false_positives
        return 0.0 if denominator == 0 else self.false_positives / denominator


def _labels(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value.strip().upper()} if value.strip() else set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip().upper() for item in value if str(item).strip()}
    return {str(value).strip().upper()}


def compute_metrics(
    samples: Sequence[BenchmarkSample],
    predictions: Mapping[str, Any],
    *,
    thresholds: Mapping[str, float] | None = None,
) -> BenchmarkMetrics:
    """确定性指标计算：micro TP/FP/FN over label sets。"""
    limits = dict(thresholds or DEFAULT_THRESHOLDS)
    true_positives = false_positives = false_negatives = 0
    unknown = 0
    for sample in samples:
        golden = _labels(sample.golden_labels_json)
        predicted = _labels(predictions.get(sample.sample_id))
        if not predicted or predicted == {"UNKNOWN"}:
            # UNKNOWN 视为弃权：计入 Unknown rate 与漏报，但不制造误报
            unknown += 1
            false_negatives += len(golden)
            continue
        true_positives += len(golden & predicted)
        false_positives += len(predicted - golden)
        false_negatives += len(golden - predicted)
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0.0
    )
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    samples_count = len(samples)
    gate_eligible = samples_count >= GATING_MIN_SAMPLES
    meets = (
        precision >= limits.get("precision", 0)
        and recall >= limits.get("recall", 0)
        and f1 >= limits.get("f1", 0)
        and gate_eligible
    )
    return BenchmarkMetrics(
        samples=samples_count,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        unknown_rate=(unknown / samples_count) if samples_count else 0.0,
        gate_eligible=gate_eligible,
        meets_thresholds=meets,
        thresholds=limits,
    )


def compute_content_hash(samples: Sequence[BenchmarkSample]) -> str:
    payload = [
        {
            "sample_id": sample.sample_id,
            "task_type": sample.task_type,
            "input_refs": sample.input_refs_json or [],
            "golden_labels": sorted(_labels(sample.golden_labels_json)),
            "expected_schema": sample.expected_schema_json or {},
        }
        for sample in sorted(samples, key=lambda item: item.sample_id)
    ]
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def create_dataset(
    db: Session,
    *,
    project_id: int | None,
    dataset_key: str,
    task_type: str,
    created_by: int | None = None,
) -> BenchmarkDataset:
    key = str(dataset_key or "").strip()
    if not key:
        raise BenchmarkError("dataset_key 不能为空")
    if task_type not in TASK_TYPES:
        raise BenchmarkError(f"未知 task_type: {task_type!r}")
    revisions = list(
        db.scalars(select(BenchmarkDataset).where(BenchmarkDataset.dataset_key == key))
    )
    row = BenchmarkDataset(
        project_id=project_id,
        dataset_key=key,
        revision=max((int(item.revision or 0) for item in revisions), default=0) + 1,
        task_type=task_type,
        status="DRAFT",
        created_by=created_by,
    )
    db.add(row)
    db.flush()
    return row


def get_dataset(db: Session, dataset_id: str) -> BenchmarkDataset:
    row = db.get(BenchmarkDataset, dataset_id)
    if row is None:
        raise BenchmarkError(f"数据集不存在: {dataset_id}")
    return row


def add_sample(
    db: Session,
    dataset_id: str,
    *,
    sample_id: str,
    golden_labels: Sequence[str],
    task_type: str = "",
    input_refs: Sequence[str] | None = None,
    frozen_context: dict[str, Any] | None = None,
    expected_schema: dict[str, Any] | None = None,
    source: str = "",
    labeler: str = "",
    reviewer: str = "",
) -> BenchmarkSample:
    dataset = get_dataset(db, dataset_id)
    if dataset.status != "DRAFT":
        raise BenchmarkError("只有 DRAFT 数据集可以追加样本（冻结后不可改）")
    if not str(sample_id or "").strip():
        raise BenchmarkError("sample_id 不能为空")
    labels = sorted(_labels(golden_labels))
    if not labels:
        raise BenchmarkError("样本必须有 golden_labels")
    sample = BenchmarkSample(
        dataset_id=dataset.id,
        sample_id=str(sample_id).strip(),
        task_type=task_type or dataset.task_type,
        input_refs_json=list(input_refs or []),
        frozen_context_json=dict(frozen_context or {}),
        expected_schema_json=dict(expected_schema or {}),
        golden_labels_json=labels,
        source=source,
        labeler=labeler,
        reviewer=reviewer,
    )
    db.add(sample)
    dataset.sample_count = int(dataset.sample_count or 0) + 1
    db.flush()
    return sample


def list_samples(db: Session, dataset_id: str) -> list[BenchmarkSample]:
    return list(
        db.scalars(
            select(BenchmarkSample)
            .where(BenchmarkSample.dataset_id == dataset_id)
            .order_by(BenchmarkSample.sample_id)
        )
    )


def freeze_dataset(
    db: Session, dataset_id: str, *, approved_by: int | None = None
) -> BenchmarkDataset:
    dataset = get_dataset(db, dataset_id)
    if dataset.status == "FROZEN":
        return dataset
    samples = list_samples(db, dataset.id)
    if not samples:
        raise BenchmarkError("空数据集不能冻结")
    dataset.content_hash = compute_content_hash(samples)
    dataset.sample_count = len(samples)
    dataset.gate_eligible = len(samples) >= GATING_MIN_SAMPLES
    dataset.status = "FROZEN"
    dataset.approved_by = approved_by
    dataset.approved_at = datetime.now(UTC)
    db.flush()
    return dataset


def run_benchmark(
    db: Session,
    *,
    dataset_id: str,
    agent_key: str,
    agent_version: str = "",
    prompt_hash: str = "",
    model_provider: str = "",
    model_name: str = "",
    predictor: Callable[[BenchmarkSample], Any],
    thresholds: Mapping[str, float] | None = None,
) -> BenchmarkRun:
    """真实执行 Agent 并计算指标；预测结果由 ``predictor`` 调用 Agent 得到。"""
    dataset = get_dataset(db, dataset_id)
    if dataset.status != "FROZEN":
        raise BenchmarkError("Benchmark 必须使用 FROZEN 数据集")
    samples = list_samples(db, dataset.id)
    run = BenchmarkRun(
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        agent_key=str(agent_key),
        agent_version=str(agent_version),
        prompt_hash=str(prompt_hash),
        model_provider=str(model_provider),
        model_name=str(model_name),
        status="RUNNING",
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()
    predictions: dict[str, Any] = {}
    per_sample: list[dict[str, Any]] = []
    token_input = token_output = 0
    try:
        for sample in samples:
            output = predictor(sample)
            if isinstance(output, Mapping):
                labels = output.get("labels") or output.get("predicted_labels") or output.get(
                    "output"
                )
                tokens = output.get("token_usage") or {}
                if isinstance(tokens, Mapping):
                    token_input += int(tokens.get("input") or 0)
                    token_output += int(tokens.get("output") or 0)
                output_hash = str(output.get("output_hash") or "")
            else:
                labels = output
                output_hash = ""
            predictions[sample.sample_id] = labels
            per_sample.append(
                {
                    "sample_id": sample.sample_id,
                    "predicted": sorted(_labels(labels)),
                    "golden": sorted(_labels(sample.golden_labels_json)),
                    "output_hash": output_hash,
                }
            )
    except Exception as exc:
        run.status = "FAILED"
        run.error_text = f"{type(exc).__name__}: {exc}"[:2000]
        run.completed_at = datetime.now(UTC)
        db.flush()
        raise
    metrics = compute_metrics(samples, predictions, thresholds=thresholds)
    run.metrics_json = metrics.payload()
    run.per_sample_json = per_sample
    run.token_usage_json = {"input": token_input, "output": token_output}
    run.result_status = (
        "PASS_GATE"
        if metrics.meets_thresholds
        else ("REFERENCE_ONLY" if not metrics.gate_eligible else "BELOW_THRESHOLD")
    )
    run.status = "COMPLETED"
    run.completed_at = datetime.now(UTC)
    db.flush()
    return run


def get_run(db: Session, run_id: str) -> BenchmarkRun:
    row = db.get(BenchmarkRun, run_id)
    if row is None:
        raise BenchmarkError(f"BenchmarkRun 不存在: {run_id}")
    return row


def metrics_of(db: Session, run_id: str) -> dict[str, Any]:
    run = get_run(db, run_id)
    if run.status != "COMPLETED" or not run.metrics_json:
        raise BenchmarkError("BenchmarkRun 尚未完成，没有可引用指标")
    return dict(run.metrics_json)


def compare_with_baseline(
    current: Mapping[str, Any], baseline: Mapping[str, Any] | None
) -> dict[str, Any]:
    if not baseline:
        return {"baseline": None, "delta": {}}
    delta: dict[str, float] = {}
    for key in ("precision", "recall", "f1"):
        if key in current and key in baseline:
            delta[key] = round(float(current[key]) - float(baseline[key]), 4)
    return {"baseline": dict(baseline), "delta": delta}


__all__ = [
    "DATASET_STATUSES",
    "DEFAULT_THRESHOLDS",
    "GATING_MIN_SAMPLES",
    "TASK_TYPES",
    "BenchmarkError",
    "BenchmarkMetrics",
    "add_sample",
    "compare_with_baseline",
    "compute_content_hash",
    "compute_metrics",
    "create_dataset",
    "freeze_dataset",
    "get_dataset",
    "get_run",
    "list_samples",
    "metrics_of",
    "run_benchmark",
]
