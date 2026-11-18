"""AUD-019：Noise Intelligence（12 类干扰 Detector / Observation 持久化 / Triage 生命周期）。

v1.5 §03 AUD-019 + §04：

- Detector 是**确定性**的，只产出 ``InterferenceObservation``，不得修改 Run Outcome；
- 12 个规范类别：ENVIRONMENT / TEST_DATA / CONCURRENCY / THIRD_PARTY / NETWORK / TIME /
  CROSS_FEATURE / UI_OVERLAY / AUTOMATION / REQUIREMENT_GAP / FLAKY / UNKNOWN；
- 每个 Detector 给出建议实验 E1–E6；无法归因时保留 UNKNOWN，不硬选单一根因；
- TriageCase 走固定生命周期，禁止跳级。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.interference import InterferenceObservation, TriageCase
from app.aiqe.services import interference_service

CATEGORIES: tuple[str, ...] = (
    "ENVIRONMENT",
    "TEST_DATA",
    "CONCURRENCY",
    "THIRD_PARTY",
    "NETWORK",
    "TIME",
    "CROSS_FEATURE",
    "UI_OVERLAY",
    "AUTOMATION",
    "REQUIREMENT_GAP",
    "FLAKY",
    "UNKNOWN",
)

#: 旧 10 类资源信号 → 12 类规范类别。
CATEGORY_OF_DETECTOR: dict[str, str] = {
    "cpu_throttle": "ENVIRONMENT",
    "memory_pressure": "ENVIRONMENT",
    "disk_full": "ENVIRONMENT",
    "port_conflict": "ENVIRONMENT",
    "process_crash": "ENVIRONMENT",
    "network_latency": "NETWORK",
    "dns_failure": "NETWORK",
    "dependency_5xx": "THIRD_PARTY",
    "clock_skew": "TIME",
    "lock_contention": "CONCURRENCY",
}

#: 每类干扰的建议实验（v1.5 §04-6）。
EXPERIMENT_OF_CATEGORY: dict[str, str] = {
    "ENVIRONMENT": "E5",
    "TEST_DATA": "E2",
    "CONCURRENCY": "E2",
    "THIRD_PARTY": "E3",
    "NETWORK": "E6",
    "TIME": "E1",
    "CROSS_FEATURE": "E4",
    "UI_OVERLAY": "E4",
    "AUTOMATION": "E5",
    "REQUIREMENT_GAP": "E1",
    "FLAKY": "E1",
    "UNKNOWN": "E1",
}

TRIAGE_LIFECYCLE: tuple[str, ...] = (
    "DETECTED",
    "EVIDENCE_COLLECTED",
    "HYPOTHESES_READY",
    "EXPERIMENT_PROPOSED",
    "EXPERIMENT_RUNNING",
    "ATTRIBUTED",
    "UNKNOWN",
    "NEEDS_HUMAN",
)
TRIAGE_TERMINAL: frozenset[str] = frozenset({"ATTRIBUTED", "UNKNOWN", "NEEDS_HUMAN"})
ALLOWED_TRIAGE_TRANSITIONS: dict[str, frozenset[str]] = {
    "DETECTED": frozenset({"EVIDENCE_COLLECTED", "UNKNOWN", "NEEDS_HUMAN"}),
    "EVIDENCE_COLLECTED": frozenset({"HYPOTHESES_READY", "UNKNOWN", "NEEDS_HUMAN"}),
    "HYPOTHESES_READY": frozenset({"EXPERIMENT_PROPOSED", "UNKNOWN", "NEEDS_HUMAN"}),
    "EXPERIMENT_PROPOSED": frozenset({"EXPERIMENT_RUNNING", "UNKNOWN", "NEEDS_HUMAN"}),
    "EXPERIMENT_RUNNING": frozenset({"ATTRIBUTED", "UNKNOWN", "NEEDS_HUMAN"}),
    "ATTRIBUTED": frozenset(),
    "UNKNOWN": frozenset(),
    "NEEDS_HUMAN": frozenset(),
}
DETECTOR_VERSION = "1.0.0"
DEFAULT_WINDOW_BEFORE_SECONDS = 15
DEFAULT_WINDOW_AFTER_SECONDS = 10


class NoiseIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class Detection:
    detector_key: str
    category: str
    severity: str
    signal: dict[str, Any]
    recommended_experiment: str
    evidence_refs: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        return {
            "detector_key": self.detector_key,
            "category": self.category,
            "severity": self.severity,
            "signal": dict(self.signal),
            "recommended_experiment": self.recommended_experiment,
            "evidence_refs": list(self.evidence_refs),
        }


def _get(payload: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _detection(
    detector_key: str, category: str, *, severity: str, signal: dict[str, Any], evidence=()
) -> Detection:
    return Detection(
        detector_key=detector_key,
        category=category,
        severity=severity,
        signal=signal,
        recommended_experiment=EXPERIMENT_OF_CATEGORY[category],
        evidence_refs=tuple(evidence),
    )


def detect_categories(payload: dict[str, Any] | None) -> list[Detection]:
    """确定性检测（不做因果推断）：返回全部命中的干扰观测。"""
    data = dict(payload or {})
    detections: list[Detection] = []

    for signal in interference_service.detect(data):
        category = CATEGORY_OF_DETECTOR.get(signal.kind, "UNKNOWN")
        detections.append(
            _detection(
                signal.kind,
                category,
                severity=signal.severity,
                signal={"legacy_signal": signal.evidence},
                evidence=tuple(str(item) for item in signal.evidence.get("evidence_refs", [])),
            )
        )

    overlap = float(_get(data, "ui.overlap_ratio", 0) or 0)
    if overlap > 0.5:
        detections.append(
            _detection(
                "ui_overlay_hit_target",
                "UI_OVERLAY",
                severity="critical" if overlap >= 0.9 else "warning",
                signal={"overlap_ratio": overlap, "target": _get(data, "ui.target")},
                evidence=tuple(_get(data, "ui.evidence_refs", []) or []),
            )
        )

    if _get(data, "feature_flag.changed") in (True, "true", 1):
        detections.append(
            _detection(
                "cross_feature_flag_change",
                "CROSS_FEATURE",
                severity="warning",
                signal={"flag": _get(data, "feature_flag.name"), "actor": _get(data, "feature_flag.actor")},
                evidence=tuple(_get(data, "feature_flag.evidence_refs", []) or []),
            )
        )

    if _get(data, "runner.crash") in (True, "true", 1) or _get(data, "browser.crashed") in (
        True,
        "true",
        1,
    ):
        detections.append(
            _detection(
                "automation_runner_crash",
                "AUTOMATION",
                severity="critical",
                signal={"runner": _get(data, "runner.id"), "reason": _get(data, "runner.reason")},
                evidence=tuple(_get(data, "runner.evidence_refs", []) or []),
            )
        )

    results = _get(data, "runs.results", []) or []
    if isinstance(results, list) and len(set(str(item) for item in results)) > 1:
        detections.append(
            _detection(
                "flaky_multi_run",
                "FLAKY",
                severity="warning",
                signal={"results": list(results)},
            )
        )

    if _get(data, "requirement.missing_ac") in (True, "true", 1) or _get(
        data, "requirement.ambiguous"
    ) in (True, "true", 1):
        detections.append(
            _detection(
                "requirement_gap_missing_ac",
                "REQUIREMENT_GAP",
                severity="warning",
                signal={
                    "requirement_id": _get(data, "requirement.id"),
                    "ambiguous_terms": _get(data, "requirement.ambiguous_terms", []),
                },
            )
        )

    if _get(data, "fixture.conflict") in (True, "true", 1) or _get(data, "fixture.overwritten_by"):
        detections.append(
            _detection(
                "test_data_namespace_conflict",
                "TEST_DATA",
                severity="warning",
                signal={
                    "namespace": _get(data, "fixture.namespace"),
                    "overwritten_by": _get(data, "fixture.overwritten_by"),
                },
            )
        )

    skew_ms = float(_get(data, "clock.skew_ms", 0) or 0)
    if abs(skew_ms) > 1000:
        detections.append(
            _detection(
                "time_clock_skew",
                "TIME",
                severity="warning",
                signal={"skew_ms": skew_ms},
            )
        )

    if not detections:
        detections.append(
            _detection(
                "unknown_interference",
                "UNKNOWN",
                severity="warning",
                signal={"note": "未命中任何确定性 Detector，保留 UNKNOWN/多因素假设"},
            )
        )
    return detections


def persist_observations(
    db: Session,
    *,
    project_id: int,
    run_id: str,
    detections: list[Detection],
    node_run_id: str | None = None,
    observed_at: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> list[InterferenceObservation]:
    """写入 Observation；只记录事实，不修改 Run/Node 状态。"""
    moment = observed_at or datetime.now(UTC)
    start = window_start or (moment - timedelta(seconds=DEFAULT_WINDOW_BEFORE_SECONDS))
    end = window_end or (moment + timedelta(seconds=DEFAULT_WINDOW_AFTER_SECONDS))
    rows: list[InterferenceObservation] = []
    for detection in detections:
        row = InterferenceObservation(
            project_id=int(project_id),
            run_id=str(run_id),
            node_run_id=node_run_id,
            detector_key=detection.detector_key,
            detector_version=DETECTOR_VERSION,
            category=detection.category,
            severity=detection.severity,
            observed_at=moment,
            window_start=start,
            window_end=end,
            signal_json=detection.signal,
            evidence_refs_json=list(detection.evidence_refs),
            recommended_experiment=detection.recommended_experiment,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def list_observations(
    db: Session, *, project_id: int, run_id: str
) -> list[InterferenceObservation]:
    return list(
        db.scalars(
            select(InterferenceObservation)
            .where(
                InterferenceObservation.project_id == int(project_id),
                InterferenceObservation.run_id == str(run_id),
            )
            .order_by(InterferenceObservation.observed_at)
        )
    )


def create_triage_case(
    db: Session,
    *,
    project_id: int,
    run_id: str,
    node_run_id: str | None = None,
    observed_at: datetime | None = None,
) -> TriageCase:
    moment = observed_at or datetime.now(UTC)
    row = TriageCase(
        project_id=int(project_id),
        run_id=str(run_id),
        node_run_id=node_run_id,
        status="DETECTED",
        window_start=moment - timedelta(seconds=DEFAULT_WINDOW_BEFORE_SECONDS),
        window_end=moment + timedelta(seconds=DEFAULT_WINDOW_AFTER_SECONDS),
        created_at=moment,
        updated_at=moment,
    )
    db.add(row)
    db.flush()
    return row


def get_triage_case(db: Session, *, triage_id: str, project_id: int) -> TriageCase:
    row = db.get(TriageCase, str(triage_id))
    if row is None or int(row.project_id or 0) != int(project_id):
        raise NoiseIntelligenceError(f"TriageCase 不存在: {triage_id}")
    return row


def transition_triage_case(
    db: Session,
    *,
    triage_id: str,
    project_id: int,
    target: str,
    attribution: dict[str, Any] | None = None,
) -> TriageCase:
    row = get_triage_case(db, triage_id=triage_id, project_id=project_id)
    target = str(target or "").upper()
    if target not in TRIAGE_LIFECYCLE:
        raise NoiseIntelligenceError(f"未知 Triage 状态: {target}")
    if target not in ALLOWED_TRIAGE_TRANSITIONS.get(row.status, frozenset()):
        raise NoiseIntelligenceError(f"非法 Triage 状态迁移: {row.status} → {target}")
    row.status = target
    if attribution is not None:
        row.attribution_json = dict(attribution)
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def suppression_allowed(*, category: str, priority: str, action: str) -> bool:
    """P0 原始 FAIL 永远不能被 suppress/quarantine 转成 PASS。"""
    if str(priority).upper() == "P0" and action in {"suppress", "quarantine"}:
        return False
    return category in CATEGORIES


__all__ = [
    "ALLOWED_TRIAGE_TRANSITIONS",
    "CATEGORIES",
    "CATEGORY_OF_DETECTOR",
    "DEFAULT_WINDOW_AFTER_SECONDS",
    "DEFAULT_WINDOW_BEFORE_SECONDS",
    "DETECTOR_VERSION",
    "EXPERIMENT_OF_CATEGORY",
    "TRIAGE_LIFECYCLE",
    "TRIAGE_TERMINAL",
    "Detection",
    "NoiseIntelligenceError",
    "create_triage_case",
    "detect_categories",
    "get_triage_case",
    "list_observations",
    "persist_observations",
    "suppression_allowed",
    "transition_triage_case",
]
