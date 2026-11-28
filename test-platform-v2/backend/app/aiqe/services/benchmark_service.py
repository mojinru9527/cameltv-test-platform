"""AUD-018：Benchmark 执行与**后端计算**指标（不接受 Agent 自报）。

v1.5 §03 AUD-018：

- 数据集必须冻结（content_hash + sample_count），``sample_count < 30`` 只能作为实验参考，
  不得用于自动门禁；
- 正式 Benchmark 必须真实调用 Agent；预测结果与 golden labels 由代码确定性比较；
- 指标（Precision/Recall/F1/Unknown rate 等）由系统计算并落库，API 不接受自报数值；
- 连续版本必须与 baseline 对照，不达门槛不得批准发布。

V1.6.2（FIX-006）加固：

- ``metrics_of`` 从**逐样本 prediction/ground truth** 复算 TP/FP/FN/TN 与
  precision/recall/f1，存储的 ``metrics_json`` 只用于对账（被篡改即拒绝）；
- Run 记录数据集绑定快照（dataset_id/content_hash/样本数）；数据集 hash 或样本
  在 Run 之后变化 → 旧 Run 不可冒充新 Dataset 结果；
- 样本口径显式：``total = valid + excluded``，剔除样本逐条记录原因；
- 样本导入做重复 id / 非法标签校验，空数据集与全负类有定义明确的结果。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.benchmark import BenchmarkDataset, BenchmarkRun, BenchmarkSample
from app.services import ai_client

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
#: 标签词表：大写字母开头 + 大写字母/数字/下划线，最长 64。
_LABEL_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
#: 样本 id 允许的字符（既有样本形如 WWY-V5-001 / s-003）。
_SAMPLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
#: 指标对账键（存储值必须与逐样本复算值一致）。
#: 口径字段（total_samples/excluded_samples）无法从有效样本复算，单独做一致性校验。
METRIC_COMPARE_KEYS: tuple[str, ...] = (
    "samples",
    "true_positives",
    "false_positives",
    "false_negatives",
    "sample_true_positives",
    "sample_false_positives",
    "sample_false_negatives",
    "sample_true_negatives",
    "precision",
    "recall",
    "f1",
    "unknown_rate",
    "gate_eligible",
    "meets_thresholds",
)
UNKNOWN_LABEL = "UNKNOWN"



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
    #: 口径字段：数据集总数 = 有效样本 + 剔除样本（剔除原因逐条记录）。
    total_samples: int = 0
    excluded_samples: int = 0
    exclusions: tuple[dict[str, Any], ...] = ()
    #: 样本级二分类混淆矩阵（positive = 该样本存在 golden 标签且模型给出可用预测）。
    sample_true_positives: int = 0
    sample_false_positives: int = 0
    sample_false_negatives: int = 0
    sample_true_negatives: int = 0

    def payload(self) -> dict[str, Any]:
        return {
            "samples": self.samples,
            "total_samples": self.total_samples,
            "excluded_samples": self.excluded_samples,
            "exclusions": [dict(item) for item in self.exclusions],
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "sample_true_positives": self.sample_true_positives,
            "sample_false_positives": self.sample_false_positives,
            "sample_false_negatives": self.sample_false_negatives,
            "sample_true_negatives": self.sample_true_negatives,
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


def _usable(predicted: set[str]) -> bool:
    return bool(predicted) and predicted != {UNKNOWN_LABEL}


def _metrics_from_pairs(
    pairs: Sequence[tuple[set[str], set[str]]],
    *,
    thresholds: Mapping[str, float] | None = None,
    total_samples: int | None = None,
    exclusions: Sequence[Mapping[str, Any]] = (),
) -> BenchmarkMetrics:
    """唯一指标计算实现：label 级 micro TP/FP/FN + 样本级 2x2 混淆矩阵。"""
    limits = dict(thresholds or DEFAULT_THRESHOLDS)
    true_positives = false_positives = false_negatives = 0
    sample_tp = sample_fp = sample_fn = sample_tn = 0
    unknown = 0
    for golden, predicted in pairs:
        if not _usable(predicted):
            unknown += 1
            false_negatives += len(golden)
        else:
            true_positives += len(golden & predicted)
            false_positives += len(predicted - golden)
            false_negatives += len(golden - predicted)
        golden_positive = bool(golden)
        predicted_positive = _usable(predicted)
        if golden_positive and predicted_positive:
            sample_tp += 1
        elif golden_positive and not predicted_positive:
            sample_fn += 1
        elif predicted_positive and not golden_positive:
            sample_fp += 1
        else:
            sample_tn += 1
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
    samples_count = len(pairs)
    total = samples_count if total_samples is None else int(total_samples)
    excluded = len(exclusions)
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
        total_samples=total,
        excluded_samples=excluded,
        exclusions=tuple(dict(item) for item in exclusions),
        sample_true_positives=sample_tp,
        sample_false_positives=sample_fp,
        sample_false_negatives=sample_fn,
        sample_true_negatives=sample_tn,
    )


def compute_metrics(
    samples: Sequence[BenchmarkSample],
    predictions: Mapping[str, Any],
    *,
    thresholds: Mapping[str, float] | None = None,
    total_samples: int | None = None,
    exclusions: Sequence[Mapping[str, Any]] = (),
) -> BenchmarkMetrics:
    """确定性指标计算：micro TP/FP/FN over label sets（服务端唯一实现）。"""
    pairs = [
        (_labels(sample.golden_labels_json), _labels(predictions.get(sample.sample_id)))
        for sample in samples
    ]
    return _metrics_from_pairs(
        pairs,
        thresholds=thresholds,
        total_samples=total_samples,
        exclusions=exclusions,
    )


def recompute_metrics(
    per_sample: Sequence[Mapping[str, Any]],
    *,
    thresholds: Mapping[str, float] | None = None,
) -> BenchmarkMetrics:
    """从**已落库的逐样本预测记录**复算指标（不信任 summary 数值）。"""
    if not isinstance(per_sample, (list, tuple)) or not per_sample:
        raise BenchmarkError("PER_SAMPLE_RECORDS_MISSING: 没有逐样本预测记录，无法复算指标")
    pairs: list[tuple[set[str], set[str]]] = []
    for record in per_sample:
        if not isinstance(record, Mapping):
            raise BenchmarkError("PER_SAMPLE_RECORD_INVALID: 逐样本记录必须是对象")
        if "golden" not in record or "predicted" not in record:
            raise BenchmarkError(
                "PER_SAMPLE_RECORD_INCOMPLETE: 逐样本记录缺少 golden/predicted"
            )
        pairs.append((_labels(record.get("golden")), _labels(record.get("predicted"))))
    return _metrics_from_pairs(pairs, thresholds=thresholds)


def result_status_of(metrics: BenchmarkMetrics | Mapping[str, Any]) -> str:
    """指标 → Run 结果状态（PASS_GATE / REFERENCE_ONLY / BELOW_THRESHOLD）。"""
    meets = (
        metrics.meets_thresholds
        if isinstance(metrics, BenchmarkMetrics)
        else bool(metrics.get("meets_thresholds"))
    )
    eligible = (
        metrics.gate_eligible
        if isinstance(metrics, BenchmarkMetrics)
        else bool(metrics.get("gate_eligible"))
    )
    if meets:
        return "PASS_GATE"
    return "REFERENCE_ONLY" if not eligible else "BELOW_THRESHOLD"


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


def get_dataset(
    db: Session, dataset_id: str, *, project_id: int | None = None
) -> BenchmarkDataset:
    row = db.get(BenchmarkDataset, dataset_id)
    if row is None or (
        project_id is not None
        and row.project_id is not None
        and int(row.project_id) != int(project_id)
    ):
        # V16-011：跨项目按 404 语义拒绝（不暴露资源存在性）。
        raise BenchmarkError(f"数据集不存在: {dataset_id}")
    return row


def add_sample(
    db: Session,
    dataset_id: str,
    *,
    sample_id: str,
    golden_labels: Sequence[str],
    project_id: int | None = None,
    task_type: str = "",
    input_refs: Sequence[str] | None = None,
    frozen_context: dict[str, Any] | None = None,
    expected_schema: dict[str, Any] | None = None,
    source: str = "",
    labeler: str = "",
    reviewer: str = "",
) -> BenchmarkSample:
    dataset = get_dataset(db, dataset_id, project_id=project_id)
    if dataset.status != "DRAFT":
        raise BenchmarkError("只有 DRAFT 数据集可以追加样本（冻结后不可改）")
    normalized_id = str(sample_id or "").strip()
    if not normalized_id:
        raise BenchmarkError("sample_id 不能为空")
    if not _SAMPLE_ID_PATTERN.match(normalized_id):
        raise BenchmarkError(f"INVALID_SAMPLE_ID: 样本 id 非法: {normalized_id!r}")
    existing = db.scalar(
        select(BenchmarkSample.id).where(
            BenchmarkSample.dataset_id == dataset.id,
            BenchmarkSample.sample_id == normalized_id,
        )
    )
    if existing is not None:
        raise BenchmarkError(f"DUPLICATE_SAMPLE_ID: 样本已存在: {normalized_id}")
    raw_labels = [str(item).strip() for item in (golden_labels or []) if str(item).strip()]
    if not raw_labels:
        raise BenchmarkError("样本必须有 golden_labels")
    labels = sorted(_labels(raw_labels))
    illegal = [label for label in labels if not _LABEL_PATTERN.match(label)]
    if illegal:
        raise BenchmarkError(
            f"INVALID_LABEL: 标签必须是 [A-Z][A-Z0-9_]{{0,63}}，非法标签: {illegal}"
        )
    sample = BenchmarkSample(
        dataset_id=dataset.id,
        sample_id=normalized_id,
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


def list_samples(
    db: Session, dataset_id: str, *, project_id: int | None = None
) -> list[BenchmarkSample]:
    get_dataset(db, dataset_id, project_id=project_id)
    return list(
        db.scalars(
            select(BenchmarkSample)
            .where(BenchmarkSample.dataset_id == dataset_id)
            .order_by(BenchmarkSample.sample_id)
        )
    )


def partition_samples(
    samples: Sequence[BenchmarkSample],
) -> tuple[list[BenchmarkSample], list[dict[str, Any]]]:
    """口径拆分：有效样本 + 剔除样本（逐条记录原因，保证 total = valid + excluded）。"""
    valid: list[BenchmarkSample] = []
    excluded: list[dict[str, Any]] = []
    for sample in samples:
        labels = _labels(sample.golden_labels_json)
        if not labels:
            excluded.append(
                {"sample_id": str(sample.sample_id), "reason": "MISSING_GOLDEN_LABELS"}
            )
            continue
        if any(not _LABEL_PATTERN.match(label) for label in labels):
            excluded.append(
                {"sample_id": str(sample.sample_id), "reason": "INVALID_GOLDEN_LABEL"}
            )
            continue
        valid.append(sample)
    return valid, excluded


def dataset_binding(db: Session, dataset: BenchmarkDataset) -> dict[str, Any]:
    """数据集绑定快照：Run 记录该快照，事后数据集变化即可被发现。"""
    samples = list_samples(db, dataset.id)
    valid, excluded = partition_samples(samples)
    return {
        "dataset_id": dataset.id,
        "dataset_key": str(dataset.dataset_key or ""),
        "revision": int(dataset.revision or 0),
        "task_type": str(dataset.task_type or ""),
        "status": str(dataset.status or ""),
        "content_hash": str(dataset.content_hash or ""),
        "computed_content_hash": compute_content_hash(samples),
        "sample_count": len(samples),
        "valid_samples": len(valid),
        "excluded_samples": len(excluded),
    }


def verify_dataset_integrity(
    db: Session, dataset: BenchmarkDataset
) -> list[BenchmarkSample]:
    """校验 Dataset 口径：字段样本数 = 实际样本数；冻结 hash = 当前样本 hash。"""
    samples = list_samples(db, dataset.id)
    rows = len(samples)
    declared = int(dataset.sample_count or 0)
    if declared != rows:
        raise BenchmarkError(
            f"DATASET_SAMPLE_COUNT_MISMATCH: sample_count={declared} 实际样本行={rows}"
        )
    if str(dataset.status) == "FROZEN":
        declared_hash = str(dataset.content_hash or "")
        if not declared_hash:
            raise BenchmarkError("DATASET_CHECKSUM_MISSING: 冻结数据集缺少 content_hash")
        actual = compute_content_hash(samples)
        if actual != declared_hash:
            raise BenchmarkError(
                "DATASET_HASH_MISMATCH: 数据集样本在冻结后被修改"
                f"（记录 {declared_hash[:12]}… / 实际 {actual[:12]}…）"
            )
    return samples


def verify_run_dataset_binding(db: Session, run: BenchmarkRun) -> dict[str, Any]:
    """Run 记录的数据集快照必须与当前数据集一致，否则旧 Run 不可冒充新 Dataset。"""
    stored = dict((run.metrics_json or {}).get("dataset_snapshot") or {})
    if not stored:
        raise BenchmarkError(
            "DATASET_SNAPSHOT_MISSING: BenchmarkRun 未记录数据集版本/hash，不能作为当前数据集证据"
        )
    dataset = get_dataset(db, run.dataset_id, project_id=run.project_id)
    current = dataset_binding(db, dataset)
    problems: list[str] = []
    if str(stored.get("dataset_id") or "") != current["dataset_id"]:
        problems.append("DATASET_ID_MISMATCH")
    if str(stored.get("computed_content_hash") or "") != current["computed_content_hash"]:
        problems.append("DATASET_HASH_CHANGED")
    if str(stored.get("content_hash") or "") != current["content_hash"]:
        problems.append("DATASET_FREEZE_HASH_CHANGED")
    if int(stored.get("sample_count") or 0) != current["sample_count"]:
        problems.append("DATASET_SAMPLE_COUNT_CHANGED")
    if problems:
        raise BenchmarkError(
            "DATASET_BINDING_STALE: " + ", ".join(problems) + "；旧 Run 不能冒充新 Dataset 结果"
        )
    return current


def _stored_metric_problems(
    stored: Mapping[str, Any], computed: BenchmarkMetrics
) -> list[str]:
    """逐键对账：存储指标必须与逐样本复算值一致（拒绝调用方自报/人工改数）。"""
    problems: list[str] = []
    payload = computed.payload()
    for key in METRIC_COMPARE_KEYS:
        if key not in stored:
            problems.append(f"MISSING_{key.upper()}")
            continue
        left = stored.get(key)
        right = payload.get(key)
        if isinstance(right, float):
            if not isinstance(left, (int, float)) or isinstance(left, bool):
                problems.append(f"INVALID_{key.upper()}")
            elif round(float(left), 4) != round(right, 4):
                problems.append(f"TAMPERED_{key.upper()}")
        elif left != right:
            problems.append(f"TAMPERED_{key.upper()}")
    total = stored.get("total_samples")
    excluded = stored.get("excluded_samples")
    samples = stored.get("samples")
    exclusions = stored.get("exclusions") or []
    if not isinstance(total, int) or not isinstance(excluded, int) or not isinstance(samples, int):
        problems.append("SAMPLE_ACCOUNTING_MISSING")
        return problems
    if samples + excluded != total:
        problems.append("SAMPLE_ACCOUNTING_MISMATCH")
    if len(exclusions) != excluded:
        problems.append("EXCLUSION_RECORDS_MISMATCH")
    if not all(
        isinstance(item, Mapping) and item.get("sample_id") and item.get("reason")
        for item in exclusions
    ):
        problems.append("EXCLUSION_REASON_MISSING")
    return problems


def freeze_dataset(
    db: Session,
    dataset_id: str,
    *,
    approved_by: int | None = None,
    project_id: int | None = None,
) -> BenchmarkDataset:
    dataset = get_dataset(db, dataset_id, project_id=project_id)
    if dataset.status == "FROZEN":
        return dataset
    samples = list_samples(db, dataset.id)
    if not samples:
        raise BenchmarkError("空数据集不能冻结")
    valid, _ = partition_samples(samples)
    if not valid:
        raise BenchmarkError("数据集没有有效样本（缺标签/非法标签），不能冻结")
    dataset.content_hash = compute_content_hash(samples)
    dataset.sample_count = len(samples)
    dataset.gate_eligible = len(valid) >= GATING_MIN_SAMPLES
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
    project_id: int | None = None,
    agent_version: str = "",
    prompt_hash: str = "",
    model_provider: str = "",
    model_name: str = "",
    predictor: Callable[[BenchmarkSample], Any],
    thresholds: Mapping[str, float] | None = None,
) -> BenchmarkRun:
    """真实执行 Agent 并计算指标；预测结果由 ``predictor`` 调用 Agent 得到。"""
    dataset = get_dataset(db, dataset_id, project_id=project_id)
    if dataset.status != "FROZEN":
        raise BenchmarkError("Benchmark 必须使用 FROZEN 数据集")
    samples = verify_dataset_integrity(db, dataset)
    valid, exclusions = partition_samples(samples)
    if not valid:
        raise BenchmarkError("NO_VALID_SAMPLES: 数据集没有有效样本，不能作为 Benchmark")
    binding = dataset_binding(db, dataset)
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
        for sample in valid:
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
    metrics = compute_metrics(
        valid,
        predictions,
        thresholds=thresholds,
        total_samples=len(samples),
        exclusions=exclusions,
    )
    run.metrics_json = {
        **metrics.payload(),
        "dataset_snapshot": binding,
        "provenance": {
            "computed_by": "server:benchmark_service",
            "per_sample_records": len(per_sample),
            "metric_policy": "recompute_from_per_sample",
        },
    }
    run.per_sample_json = per_sample
    run.token_usage_json = {"input": token_input, "output": token_output}
    run.result_status = result_status_of(metrics)
    run.status = "COMPLETED"
    run.completed_at = datetime.now(UTC)
    db.flush()
    return run


def get_run(
    db: Session, run_id: str, *, project_id: int | None = None
) -> BenchmarkRun:
    row = db.get(BenchmarkRun, run_id)
    if row is None or (
        project_id is not None
        and row.project_id is not None
        and int(row.project_id) != int(project_id)
    ):
        raise BenchmarkError(f"BenchmarkRun 不存在: {run_id}")
    return row


def metrics_of(
    db: Session,
    run_id: str,
    *,
    project_id: int | None = None,
    verify_dataset: bool = True,
) -> dict[str, Any]:
    """唯一可信指标入口：从逐样本记录复算，并与存储值对账。"""
    run = get_run(db, run_id, project_id=project_id)
    if run.status != "COMPLETED" or not run.metrics_json:
        raise BenchmarkError("BenchmarkRun 尚未完成，没有可引用指标")
    stored = dict(run.metrics_json)
    if verify_dataset:
        verify_run_dataset_binding(db, run)
    recomputed = recompute_metrics(
        run.per_sample_json or [], thresholds=stored.get("thresholds")
    )
    problems = _stored_metric_problems(stored, recomputed)
    if problems:
        raise BenchmarkError(
            "METRICS_TAMPERED: 存储指标与逐样本复算不一致: " + ", ".join(problems[:6])
        )
    expected_status = result_status_of(recomputed)
    if str(run.result_status or "") != expected_status:
        raise BenchmarkError(
            f"RESULT_STATUS_MISMATCH: 存储={run.result_status or 'EMPTY'} 复算={expected_status}"
        )
    payload = recomputed.payload()
    # 口径字段来自已校验的存储口径（有效样本无法从 per_sample 反推剔除样本）。
    payload["total_samples"] = int(stored.get("total_samples") or 0)
    payload["excluded_samples"] = int(stored.get("excluded_samples") or 0)
    payload["exclusions"] = [dict(item) for item in stored.get("exclusions") or []]
    return payload


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
    "METRIC_COMPARE_KEYS",
    "TASK_TYPES",
    "UNKNOWN_LABEL",
    "BenchmarkError",
    "BenchmarkMetrics",
    "add_sample",
    "compare_with_baseline",
    "compute_content_hash",
    "compute_metrics",
    "create_dataset",
    "dataset_binding",
    "freeze_dataset",
    "get_dataset",
    "get_run",
    "list_samples",
    "metrics_of",
    "partition_samples",
    "recompute_metrics",
    "result_status_of",
    "run_benchmark",
    "verify_dataset_integrity",
    "verify_run_dataset_binding",
]


BENCHMARK_SYSTEM_PROMPT = (
    "You are the AIQE benchmark agent. Given exactly one frozen sample, predict the "
    'classification labels. Return strict JSON: {"labels": ["..."], "rationale": "..."}. '
    "labels must be chosen from the sample's expected label space; never invent metrics, "
    "confidence numbers, or evidence. If the sample is insufficient, return labels [\"UNKNOWN\"]."
)


def build_llm_predictor(db: Session, *, project_id: int) -> Callable[[BenchmarkSample], Any]:
    """构造真实 LLM predictor：每个样本单独调用一次项目配置的 Provider。"""

    def predictor(sample: BenchmarkSample) -> dict[str, Any]:
        payload = {
            "sample_id": sample.sample_id,
            "task_type": sample.task_type,
            "inputs": sample.input_refs_json or [],
            "context": sample.frozen_context_json or {},
            "expected_schema": sample.expected_schema_json or {},
        }
        summary = ai_client.chat_completions_full(
            db,
            project_id,
            system_prompt=BENCHMARK_SYSTEM_PROMPT,
            user_message=json.dumps(payload, ensure_ascii=False, default=str),
            max_tokens=512,
            temperature=0,
            json_mode=True,
            cache_namespace=f"aiqe-benchmark:{sample.dataset_id}",
        )
        parsed = ai_client.parse_json_object(str(summary.get("content") or ""))
        labels = parsed.get("labels") or parsed.get("predicted_labels") or []
        usage = summary.get("usage") or {}
        return {
            "labels": labels,
            "rationale": str(parsed.get("rationale") or "")[:500],
            "output_hash": hashlib.sha256(
                str(summary.get("content") or "").encode()
            ).hexdigest()[:16],
            "token_usage": {
                "input": int(usage.get("input_tokens") or 0),
                "output": int(usage.get("output_tokens") or 0),
            },
        }

    return predictor


def run_llm_benchmark(
    db: Session,
    *,
    dataset_id: str,
    project_id: int,
    agent_key: str = "A6",
    agent_version: str = "",
    thresholds: Mapping[str, float] | None = None,
) -> BenchmarkRun:
    """使用项目已配置的 LLM Provider 执行冻结数据集；未配置 Provider 时 fail-closed。"""
    dataset = get_dataset(db, dataset_id)
    if dataset.project_id is not None and int(dataset.project_id) != int(project_id):
        raise BenchmarkError("数据集不属于当前项目")
    if not ai_client.is_configured(db, project_id):
        raise BenchmarkError(
            "AI_PROVIDER_UNCONFIGURED: 请先在项目中配置 AI Provider 后再运行 Benchmark"
        )
    cfg = ai_client.resolve_config(db, project_id)
    prompt_hash = "sha256:" + hashlib.sha256(
        BENCHMARK_SYSTEM_PROMPT.encode()
    ).hexdigest()[:16]
    return run_benchmark(
        db,
        dataset_id=dataset.id,
        agent_key=agent_key,
        agent_version=agent_version or "llm",
        prompt_hash=prompt_hash,
        model_provider=str(getattr(cfg, "provider_type", "")),
        model_name=str(getattr(cfg, "model", "")),
        predictor=build_llm_predictor(db, project_id=project_id),
        thresholds=thresholds,
    )
