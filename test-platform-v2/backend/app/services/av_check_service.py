"""AV check service."""
from __future__ import annotations

import json
import logging
import math
import statistics
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_user_names, paginate
from app.models.av_check import AvCheckMeasurement, AvCheckMetric, AvCheckTask
from app.models.user import User

logger = logging.getLogger("avcheck")


MEASUREMENT_TEMPLATES: dict[str, dict] = {
    "video_delay": {
        "name": "主播到观众视频延迟", "unit": "ms", "threshold": 2000,
        "comparator": "<=", "pass_basis": "p95", "method": "OCR 时间戳",
        "preconditions": ["主播端播放带时间戳素材并推流", "观众端录屏不少于 60 秒", "同一场景建议重复 3 次"],
    },
    "call_delay": {
        "name": "连麦视频延迟", "unit": "ms", "threshold": 2000,
        "comparator": "<=", "pass_basis": "p95", "method": "双端同步时间戳/OCR",
        "preconditions": ["主客两端时间同步", "分别录制双向画面", "注明主播-观众或主播-主播场景"],
    },
    "av_sync": {
        "name": "音画同步偏差", "unit": "ms", "threshold": 200,
        "comparator": "<=", "pass_basis": "p95", "method": "采集器波形/Audacity",
        "preconditions": ["使用 Beep + 闪光同步素材", "同时采集声音与光信号", "正负方向在备注中记录"],
    },
    "frame_rate": {
        "name": "播放帧率", "unit": "fps", "threshold": 24,
        "comparator": ">=", "pass_basis": "mean", "method": "录屏/ffprobe/OpenCV",
        "preconditions": ["录制稳定测试素材不少于 60 秒", "按秒提取帧率", "注明清晰度和设备"],
    },
    "first_frame": {
        "name": "直播间首帧加载耗时", "unit": "ms", "threshold": 2000,
        "comparator": "<=", "pass_basis": "p95", "method": "录屏解帧",
        "preconditions": ["开启触摸显示或使用可识别点击标记", "连续进出直播间 12 次", "记录点击帧和首帧出现帧"],
    },
}


def _generate_task_id(db: Session, project_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(AvCheckTask.id)).where(
            AvCheckTask.project_id == project_id,
            AvCheckTask.task_id.like(f"AV-{today}-%"),
        )
    ) or 0
    return f"AV-{today}-{count + 1:03d}"


def _task_to_dict(
    r: AvCheckTask,
    creator_name: str = "",
    metrics: list[dict] | None = None,
    measurements: list[dict] | None = None,
) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "task_id": r.task_id,
        "name": r.name,
        "stream_url": r.stream_url,
        "protocol": r.protocol,
        "status": r.status,
        "last_result": r.last_result,
        "creator_id": r.creator_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "creator_name": creator_name,
        "metrics": metrics or [],
        "measurements": measurements or [],
    }


def list_tasks(
    db: Session, project_id: int,
    protocol: str | None = None, status: str | None = None,
    keyword: str = "", page: int = 1, page_size: int = 20,
):
    base = select(AvCheckTask).where(AvCheckTask.project_id == project_id)
    if protocol:
        base = base.where(AvCheckTask.protocol == protocol)
    if status:
        base = base.where(AvCheckTask.status == status)
    if keyword:
        base = base.where(AvCheckTask.name.contains(keyword))

    rows, total = paginate(db, base.order_by(AvCheckTask.created_at.desc()), page=page, page_size=page_size)

    # Batch load creator names (was N+1 per row)
    creator_ids = {r.creator_id for r in rows}
    user_map = batch_user_names(db, creator_ids)

    items = [_task_to_dict(r, user_map.get(r.creator_id, "")) for r in rows]
    return items, total


def get_task(db: Session, task_id: int, project_id: int) -> dict | None:
    r = db.scalar(select(AvCheckTask).where(AvCheckTask.id == task_id, AvCheckTask.project_id == project_id))
    if not r:
        return None
    metrics = [
        {"id": m.id, "task_id": m.task_id, "metric_name": m.metric_name,
         "metric_value": m.metric_value, "threshold": m.threshold, "pass_": m.pass_, "detail": m.detail}
        for m in r.metrics
    ]
    creator_name = ""
    if r.creator_id:
        u = db.get(User, r.creator_id)
        if u:
            creator_name = u.nickname or u.username
    measurements = [_measurement_to_dict(item) for item in r.measurements]
    return _task_to_dict(r, creator_name, metrics, measurements)


def list_measurement_templates() -> list[dict]:
    return [
        {"metric_type": metric_type, **config}
        for metric_type, config in MEASUREMENT_TEMPLATES.items()
    ]


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _calculate_stats(samples: list[float]) -> dict:
    values = [float(item) for item in samples]
    return {
        "sample_count": len(values),
        "mean": round(statistics.fmean(values), 3),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "stddev": round(statistics.pstdev(values), 3),
        "p95": round(_percentile(values, 0.95), 3),
    }


def _measurement_to_dict(row: AvCheckMeasurement) -> dict:
    template = MEASUREMENT_TEMPLATES.get(row.metric_type, {})
    try:
        samples = [float(item) for item in json.loads(row.samples_json or "[]")]
    except (TypeError, ValueError, json.JSONDecodeError):
        samples = []
    try:
        stats = json.loads(row.stats_json or "{}")
    except json.JSONDecodeError:
        stats = {}
    return {
        "id": row.id,
        "task_id": row.task_id,
        "metric_type": row.metric_type,
        "metric_name": template.get("name", row.metric_type),
        "scenario": row.scenario,
        "method": row.method,
        "environment": row.environment,
        "device_info": row.device_info,
        "network_condition": row.network_condition,
        "samples": samples,
        "unit": row.unit,
        "threshold": row.threshold,
        "comparator": row.comparator,
        "pass_basis": row.pass_basis,
        "passed": row.passed,
        "simulated": False,
        "notes": row.notes,
        "creator_id": row.creator_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        **stats,
    }


def _apply_measurement_data(row: AvCheckMeasurement, data) -> None:
    template = MEASUREMENT_TEMPLATES.get(data.metric_type)
    if not template:
        raise ValueError("不支持的指标类型")
    samples = [float(item) for item in data.samples]
    stats = _calculate_stats(samples)
    threshold = float(data.threshold if data.threshold is not None else template["threshold"])
    comparator = template["comparator"]
    pass_basis = template["pass_basis"]
    basis_value = float(stats[pass_basis])

    row.metric_type = data.metric_type
    row.scenario = data.scenario
    row.method = data.method or template["method"]
    row.environment = data.environment
    row.device_info = data.device_info
    row.network_condition = data.network_condition
    row.unit = template["unit"]
    row.samples_json = json.dumps(samples, ensure_ascii=False)
    row.threshold = threshold
    row.comparator = comparator
    row.stats_json = json.dumps(stats, ensure_ascii=False)
    row.pass_basis = pass_basis
    row.passed = basis_value <= threshold if comparator == "<=" else basis_value >= threshold
    row.notes = data.notes


def create_measurement(
    db: Session, task_id: int, project_id: int, creator_id: int, data,
) -> dict:
    task = db.scalar(select(AvCheckTask).where(
        AvCheckTask.id == task_id, AvCheckTask.project_id == project_id,
    ))
    if not task:
        raise ValueError("任务不存在")
    row = AvCheckMeasurement(task_id=task_id, creator_id=creator_id)
    _apply_measurement_data(row, data)
    db.add(row)
    db.flush()
    return _measurement_to_dict(row)


def update_measurement(
    db: Session, task_id: int, measurement_id: int, project_id: int, data,
) -> dict | None:
    row = db.scalar(
        select(AvCheckMeasurement)
        .join(AvCheckTask, AvCheckTask.id == AvCheckMeasurement.task_id)
        .where(
            AvCheckMeasurement.id == measurement_id,
            AvCheckMeasurement.task_id == task_id,
            AvCheckTask.project_id == project_id,
        )
    )
    if not row:
        return None
    _apply_measurement_data(row, data)
    db.flush()
    return _measurement_to_dict(row)


def delete_measurement(db: Session, task_id: int, measurement_id: int, project_id: int) -> bool:
    row = db.scalar(
        select(AvCheckMeasurement)
        .join(AvCheckTask, AvCheckTask.id == AvCheckMeasurement.task_id)
        .where(
            AvCheckMeasurement.id == measurement_id,
            AvCheckMeasurement.task_id == task_id,
            AvCheckTask.project_id == project_id,
        )
    )
    if not row:
        return False
    db.delete(row)
    db.flush()
    return True


def create_task(db: Session, data, creator_id: int, project_id: int) -> dict:
    task_id = _generate_task_id(db, project_id)
    r = AvCheckTask(
        project_id=project_id, task_id=task_id,
        name=data.name, stream_url=data.stream_url, protocol=data.protocol,
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()
    return _task_to_dict(r)


def update_task(db: Session, task_id: int, project_id: int, data) -> dict | None:
    row = db.scalar(select(AvCheckTask).where(
        AvCheckTask.id == task_id, AvCheckTask.project_id == project_id,
    ))
    if not row:
        return None
    for field in ("name", "stream_url", "protocol"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(row, field, value)
    db.flush()
    return get_task(db, task_id, project_id)


def delete_task(db: Session, task_id: int, project_id: int) -> bool:
    r = db.scalar(select(AvCheckTask).where(AvCheckTask.id == task_id, AvCheckTask.project_id == project_id))
    if not r:
        return False
    db.delete(r)
    db.flush()
    return True


def trigger_check(db: Session, task_id: int, project_id: int) -> dict:
    """触发 AV 质量检测 — 使用 ffprobe 真实探测流媒体。"""
    from app.services.ffmpeg_service import probe_stream, _check_ffmpeg_installed

    r = db.scalar(select(AvCheckTask).where(AvCheckTask.id == task_id, AvCheckTask.project_id == project_id))
    if not r:
        raise ValueError("任务不存在")

    stream_url = (r.stream_url or "").strip()

    # 检查 ffprobe 可用性
    ff_ok, ff_ver = _check_ffmpeg_installed()
    if not ff_ok:
        r.status = "fail"
        r.last_result = json.dumps({"error": f"FFmpeg 不可用: {ff_ver}"}, ensure_ascii=False)
        db.commit()
        return _task_to_dict(r, metrics=[])

    if not stream_url:
        r.status = "fail"
        r.last_result = json.dumps({"error": "流地址为空"}, ensure_ascii=False)
        db.commit()
        return _task_to_dict(r, metrics=[])

    r.status = "running"
    db.flush()

    # 执行 ffprobe 探测
    logger.info(f"AV check #{task_id}: probing {stream_url[:100]}...")
    probe_result = probe_stream(stream_url, protocol=r.protocol or "HLS")

    if not probe_result["ok"]:
        # 探测失败
        r.status = "fail"
        r.last_result = json.dumps({
            "error": probe_result.get("error", "探测失败"),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)
        db.commit()
        return _task_to_dict(r, metrics=[])

    # 保存指标到数据库
    metrics = []
    for m in probe_result["metrics"]:
        db_metric = AvCheckMetric(
            task_id=task_id,
            metric_name=f"{m['name']}({m['unit']})" if m.get("unit") else m["name"],
            metric_value=float(m["value"]) if m["value"] is not None else 0,
            threshold=float(m["threshold"]),
            pass_=bool(m["passed"]),
            detail=json.dumps({
                "unit": m.get("unit", ""),
                "recommended": m.get("recommended", ""),
                "raw_value": m.get("raw_value"),
            }, ensure_ascii=False),
        )
        db.add(db_metric)
        metrics.append(db_metric)

    pass_count = sum(1 for m in metrics if m.pass_)
    result_summary = {
        "total": len(metrics),
        "pass_count": pass_count,
        "ffprobe_version": probe_result.get("raw", {}).get("ffprobe_version", ff_ver),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        **{f"raw_{k}": v for k, v in (probe_result.get("raw") or {}).items()},
    }
    r.last_result = json.dumps(result_summary, ensure_ascii=False)
    r.status = "done"

    db.flush()
    db.refresh(r)

    metric_dicts = [
        {"id": m.id, "task_id": m.task_id, "metric_name": m.metric_name,
         "metric_value": m.metric_value, "threshold": m.threshold, "pass_": m.pass_, "detail": m.detail}
        for m in metrics
    ]
    return _task_to_dict(r, metrics=metric_dicts)


def get_metrics(db: Session, task_id: int, project_id: int) -> list[dict]:
    r = db.scalar(select(AvCheckTask).where(AvCheckTask.id == task_id, AvCheckTask.project_id == project_id))
    if not r:
        return []
    return [
        {"id": m.id, "task_id": m.task_id, "metric_name": m.metric_name,
         "metric_value": m.metric_value, "threshold": m.threshold, "pass_": m.pass_, "detail": m.detail}
        for m in r.metrics
    ]
