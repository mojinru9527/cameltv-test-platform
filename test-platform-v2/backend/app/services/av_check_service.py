"""AV check service."""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_user_names, paginate
from app.models.av_check import AvCheckMetric, AvCheckTask
from app.models.user import User


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
    """Simulate AV check and generate metrics."""
    r = db.scalar(select(AvCheckTask).where(AvCheckTask.id == task_id, AvCheckTask.project_id == project_id))
    if not r:
        raise ValueError("任务不存在")

    r.status = "running"
    db.flush()

    # Simulate metrics
    metric_defs = [
        ("起播时延", "ms", 2000),
        ("卡顿率", "%", 5.0),
        ("音画同步", "ms", 100),
        ("首帧时间", "ms", 3000),
        ("缓冲次数", "次", 3),
    ]
    metrics = []
    for name, unit, threshold in metric_defs:
        value = round(random.uniform(0, threshold * 1.5), 2)
        passed = value <= threshold
        m = AvCheckMetric(
            task_id=task_id, metric_name=f"{name}({unit})",
            metric_value=value, threshold=threshold, pass_=passed,
            detail=json.dumps({"unit": unit, "recommended": f"<={threshold}"}, ensure_ascii=False),
        )
        db.add(m)
        metrics.append(m)

    result_summary = {
        "total": len(metrics),
        "pass_count": sum(1 for m in metrics if m.pass_),
        "checked_at": datetime.now(timezone.utc).isoformat(),
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
