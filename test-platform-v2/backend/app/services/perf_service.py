"""Performance monitoring business service — session CRUD + statistics + comparison."""
from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.perf import PerfDevice, PerfMetric, PerfSession
from app.schemas.perf import (
    AnomalyEvent,
    CompareResponse,
    MetricDelta,
    MetricStats,
    PerfReportResponse,
    PerfSessionCreate,
    PerfSessionOut,
)
from app.services import perf_collector_service as collector

logger = logging.getLogger("perf")

# ── Metric thresholds (aligned with PerfDog / Google Android Vitals) ──
METRIC_THRESHOLDS: dict[str, dict[str, Any]] = {
    "cpu":     {"unit": "%",   "threshold": 60.0, "comparator": "<="},
    "memory":  {"unit": "MB",  "threshold": 512.0, "comparator": "<="},
    "fps":     {"unit": "fps", "threshold": 30.0, "comparator": ">="},
    "jank":    {"unit": "次",  "threshold": 0.0,  "comparator": "<="},
    "startup": {"unit": "ms",  "threshold": 2000.0, "comparator": "<="},
    "anr":     {"unit": "次",  "threshold": 0.0,  "comparator": "<="},
}


def _generate_session_id(db: Session, project_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(PerfSession.id)).where(
            PerfSession.project_id == project_id,
            PerfSession.session_id.like(f"PERF-{today}-%"),
        )
    ) or 0
    return f"PERF-{today}-{count + 1:03d}"


# ── Device ──

def list_devices(db: Session) -> list[dict[str, Any]]:
    """获取已连接设备 + 缓存的应用列表。"""
    devices = collector.get_connected_devices()
    for d in devices:
        cached = db.scalar(
            select(PerfDevice).where(PerfDevice.device_id == d["device_id"])
        )
        if cached:
            cached.status = "online"
            cached.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(PerfDevice(
                device_id=d["device_id"],
                device_name=d.get("device_name", ""),
                device_model=d.get("device_model", ""),
                platform=d["platform"],
                os_version=d.get("os_version", ""),
                status="online",
            ))
        # 获取已安装应用
        try:
            d["installed_apps"] = collector.get_device_apps(d["device_id"], d["platform"])
        except Exception:
            d["installed_apps"] = []
    db.commit()
    return devices


# ── Session ──

def create_session(db: Session, data: PerfSessionCreate, creator_id: int, project_id: int) -> PerfSession:
    """创建采集会话（状态 pending）。"""
    session = PerfSession(
        project_id=project_id,
        session_id=_generate_session_id(db, project_id),
        device_id=data.device_id,
        device_name=data.device_name,
        device_model=data.device_model,
        platform=data.platform,
        pkg_name=data.pkg_name,
        metrics=",".join(data.metrics),
        status="pending",
        duration=data.duration,
        creator_id=creator_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> PerfSession | None:
    return db.get(PerfSession, session_id)


def list_sessions(
    db: Session,
    project_id: int,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    device_id: str | None = None,
    pkg_name: str | None = None,
) -> tuple[list[PerfSession], int]:
    """分页查询采集会话列表。"""
    q = select(PerfSession).where(PerfSession.project_id == project_id)
    if platform:
        q = q.where(PerfSession.platform == platform)
    if device_id:
        q = q.where(PerfSession.device_id == device_id)
    if pkg_name:
        q = q.where(PerfSession.pkg_name == pkg_name)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(
        q.order_by(PerfSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def start_session(db: Session, session_id: int) -> PerfSession | None:
    """标记会话为 running 并记录开始时间。"""
    session = db.get(PerfSession, session_id)
    if not session or session.status not in ("pending", "completed", "failed", "cancelled"):
        return None
    session.status = "running"
    session.started_at = datetime.now(timezone.utc)
    session.error_message = ""
    db.commit()
    db.refresh(session)
    return session


def stop_session(db: Session, session_id: int, error: str = "") -> PerfSession | None:
    """停止采集并计算统计摘要。"""
    session = db.get(PerfSession, session_id)
    if not session:
        return None

    # If the session was never started, just mark it cancelled
    if not session.started_at:
        session.status = "cancelled"
        session.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        return session

    session.status = "failed" if error else "completed"
    session.ended_at = datetime.now(timezone.utc)
    session.error_message = error

    # Both datetimes are from datetime.now(timezone.utc) but SQLite strips TZ.
    # Normalize to naive UTC before arithmetic.
    started = session.started_at.replace(tzinfo=None) if session.started_at.tzinfo else session.started_at
    ended = session.ended_at.replace(tzinfo=None) if session.ended_at.tzinfo else session.ended_at
    session.actual_duration_s = int((ended - started).total_seconds())

    # 计算统计摘要
    summary = _compute_summary(db, session_id)
    session.summary_json = json.dumps(summary, ensure_ascii=False, default=str)
    db.commit()
    db.refresh(session)
    return session


# ── Metrics ──

def save_snapshot(db: Session, session_id: int, timestamp: float, elapsed_s: float, data: dict) -> PerfMetric:
    """保存一次采样快照。"""
    metric = PerfMetric(
        session_id=session_id,
        timestamp=timestamp,
        elapsed_s=elapsed_s,
        metric_type="snapshot",
        data_json=json.dumps(data, ensure_ascii=False, default=str),
    )
    db.add(metric)
    db.commit()
    return metric


def get_metrics(db: Session, session_id: int, since_ts: float = 0) -> list[PerfMetric]:
    """获取会话的时序数据点。"""
    q = select(PerfMetric).where(
        PerfMetric.session_id == session_id,
        PerfMetric.timestamp >= since_ts,
    ).order_by(PerfMetric.timestamp.asc())
    return list(db.scalars(q).all())


# ── Report ──

def get_report(db: Session, session_id: int) -> PerfReportResponse | None:
    """生成采集报告——统计摘要 + 异常事件。"""
    session = get_session(db, session_id)
    if not session:
        return None

    metrics = get_metrics(db, session_id)
    if not metrics:
        return PerfReportResponse(
            session=PerfSessionOut.model_validate(session),
            metrics=[],
            anomalies=[],
        )

    # 从快照中提取各指标时序
    metric_series: dict[str, list[float]] = {}
    anomalies: list[AnomalyEvent] = []

    for m in metrics:
        try:
            data = json.loads(m.data_json)
        except (json.JSONDecodeError, TypeError):
            continue
        # 提取数值
        cpu = data.get("cpu", {})
        mem = data.get("memory", {})
        fps = data.get("fps", {})

        if "appCpuRate" in cpu:
            metric_series.setdefault("cpu", []).append(float(cpu["appCpuRate"]))
        if "total" in mem:
            metric_series.setdefault("memory", []).append(float(mem["total"]))
        if "fps" in fps:
            metric_series.setdefault("fps", []).append(float(fps["fps"]))
        if "jank" in fps:
            metric_series.setdefault("jank", []).append(float(fps["jank"]))

        # 收集事件
        for evt in data.get("events", []):
            anomalies.append(AnomalyEvent(
                timestamp=m.timestamp,
                event_type=evt.get("event_type", "unknown"),
                detail=evt.get("detail", ""),
                metric_snapshot=data,
            ))

    # 计算各指标统计
    stats_list: list[MetricStats] = []
    for mtype, values in metric_series.items():
        if not values:
            continue
        threshold_def = METRIC_THRESHOLDS.get(mtype, {})
        threshold = threshold_def.get("threshold", 0)
        comparator = threshold_def.get("comparator", "<=")
        passed = _check_threshold(values, threshold, comparator)

        stats_list.append(MetricStats(
            metric_type=mtype,
            unit=threshold_def.get("unit", ""),
            samples=len(values),
            mean=round(statistics.mean(values), 2),
            median=round(statistics.median(values), 2),
            p95=round(_percentile(values, 95), 2),
            min_val=round(min(values), 2),
            max_val=round(max(values), 2),
            stddev=round(statistics.stdev(values) if len(values) > 1 else 0, 2),
            threshold=threshold,
            threshold_comparator=comparator,
            passed=passed,
        ))

    return PerfReportResponse(
        session=PerfSessionOut.model_validate(session),
        metrics=stats_list,
        anomalies=anomalies,
    )


# ── Compare ──

def compare_sessions(db: Session, a_id: int, b_id: int) -> CompareResponse | None:
    """对比两次采集会话的性能指标。"""
    report_a = get_report(db, a_id)
    report_b = get_report(db, b_id)
    if not report_a or not report_b:
        return None

    deltas: list[MetricDelta] = []
    metrics_b = {m.metric_type: m for m in report_b.metrics}

    for ma in report_a.metrics:
        mb = metrics_b.get(ma.metric_type)
        if not mb:
            continue
        delta_abs = round(ma.mean - mb.mean, 2)
        delta_pct = round((delta_abs / mb.mean) * 100, 1) if mb.mean != 0 else 0.0

        direction = "unchanged"
        if abs(delta_pct) > 3:
            # 对于阈值是 >= 的指标（如 fps），值越大越好
            threshold_def = METRIC_THRESHOLDS.get(ma.metric_type, {})
            better_higher = threshold_def.get("comparator", "<=") == ">="
            if better_higher:
                direction = "improved" if delta_abs > 0 else "degraded"
            else:
                direction = "improved" if delta_abs < 0 else "degraded"

        deltas.append(MetricDelta(
            metric_type=ma.metric_type,
            session_a_mean=ma.mean,
            session_b_mean=mb.mean,
            delta_absolute=delta_abs,
            delta_percent=delta_pct,
            direction=direction,
            significant=abs(delta_pct) > 10,
        ))

    return CompareResponse(
        session_a=report_a.session,
        session_b=report_b.session,
        deltas=deltas,
    )


# ── Internal helpers ──

def _compute_summary(db: Session, session_id: int) -> dict:
    """计算会话级统计摘要（存放在 summary_json）。"""
    metrics = get_metrics(db, session_id)
    return {
        "total_samples": len(metrics),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def _percentile(values: list[float], p: float) -> float:
    """计算百分位数（线性插值）。"""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (p / 100) * (len(sorted_vals) - 1)
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_vals):
        return sorted_vals[f] + c * (sorted_vals[f + 1] - sorted_vals[f])
    return sorted_vals[f]


def _check_threshold(values: list[float], threshold: float, comparator: str) -> bool:
    """使用 P95 判定是否通过阈值。"""
    p95 = _percentile(values, 95)
    if comparator == "<=":
        return p95 <= threshold
    elif comparator == ">=":
        return p95 >= threshold
    return True
