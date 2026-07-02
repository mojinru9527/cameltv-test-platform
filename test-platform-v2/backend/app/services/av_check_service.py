"""AV check service."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_user_names, paginate
from app.models.av_check import AvCheckMetric, AvCheckTask
from app.models.user import User

logger = logging.getLogger("avcheck")


def _generate_task_id(db: Session, project_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(AvCheckTask.id)).where(
            AvCheckTask.project_id == project_id,
            AvCheckTask.task_id.like(f"AV-{today}-%"),
        )
    ) or 0
    return f"AV-{today}-{count + 1:03d}"


def _task_to_dict(r: AvCheckTask, creator_name: str = "", metrics: list[dict] | None = None) -> dict:
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
    return _task_to_dict(r, creator_name, metrics)


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
