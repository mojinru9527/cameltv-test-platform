"""UI test service."""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_user_names, paginate
from app.models.ui_test import UiTestJob, UiTestRun
from app.models.user import User


def _job_to_dict(r: UiTestJob, creator_name: str = "") -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "name": r.name, "description": r.description,
        "test_spec": r.test_spec, "browser": r.browser,
        "status": r.status, "last_result": r.last_result,
        "creator_id": r.creator_id, "creator_name": creator_name,
        "created_at": r.created_at, "updated_at": r.updated_at,
        "last_run_status": "", "last_run_time": None,
    }


def _run_to_dict(r: UiTestRun) -> dict:
    result = None
    try:
        result = json.loads(r.result) if r.result else {}
    except (json.JSONDecodeError, TypeError):
        result = {}
    screenshots = []
    try:
        screenshots = json.loads(r.screenshots) if r.screenshots else []
    except (json.JSONDecodeError, TypeError):
        screenshots = []
    return {
        "id": r.id, "job_id": r.job_id, "status": r.status,
        "result": result, "screenshots": screenshots,
        "video_url": r.video_url, "trace_id": r.trace_id,
        "started_at": r.started_at, "finished_at": r.finished_at,
    }


def list_jobs(
    db: Session, project_id: int,
    status: str | None = None, keyword: str = "",
    page: int = 1, page_size: int = 20,
):
    base = select(UiTestJob).where(UiTestJob.project_id == project_id)
    if status:
        base = base.where(UiTestJob.status == status)
    if keyword:
        base = base.where(UiTestJob.name.contains(keyword))

    rows, total = paginate(db, base.order_by(UiTestJob.created_at.desc()), page=page, page_size=page_size)

    # Batch load creator names (was N+1 per row)
    creator_ids = {r.creator_id for r in rows}
    user_map = batch_user_names(db, creator_ids)

    # Batch last-run info: subquery to get latest UiTestRun per job
    job_ids = {r.id for r in rows}
    run_map: dict[int, tuple] = {}
    if job_ids:
        from sqlalchemy import and_
        latest_sub = (
            select(
                UiTestRun.job_id,
                func.max(UiTestRun.started_at).label("max_started"),
            )
            .where(UiTestRun.job_id.in_(job_ids))
            .group_by(UiTestRun.job_id)
            .subquery()
        )
        run_rows = db.execute(
            select(UiTestRun.job_id, UiTestRun.status, UiTestRun.finished_at, UiTestRun.started_at)
            .join(latest_sub, and_(
                UiTestRun.job_id == latest_sub.c.job_id,
                UiTestRun.started_at == latest_sub.c.max_started,
            ))
        ).all()
        run_map = {r[0]: (r[1], r[2] or r[3]) for r in run_rows}

    items = []
    for r in rows:
        d = _job_to_dict(r, user_map.get(r.creator_id, ""))
        if r.id in run_map:
            d["last_run_status"] = run_map[r.id][0]
            d["last_run_time"] = run_map[r.id][1]
        items.append(d)
    return items, total


def get_job(db: Session, job_id: int, project_id: int) -> dict | None:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        return None
    creator_name = ""
    if r.creator_id:
        u = db.get(User, r.creator_id)
        if u:
            creator_name = u.nickname or u.username
    d = _job_to_dict(r, creator_name)
    d["runs"] = [_run_to_dict(run) for run in r.runs]
    if r.runs:
        last = r.runs[0]
        d["last_run_status"] = last.status
        d["last_run_time"] = last.finished_at or last.started_at
    return d


def create_job(db: Session, data, creator_id: int, project_id: int) -> dict:
    r = UiTestJob(
        project_id=project_id, name=data.name,
        description=data.description, test_spec=data.test_spec,
        browser=data.browser, creator_id=creator_id,
    )
    db.add(r)
    db.flush()
    return _job_to_dict(r)


def update_job(db: Session, job_id: int, data, project_id: int) -> dict | None:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        return None
    update_fields = ["name", "description", "test_spec", "browser"]
    update_data = data.model_dump(exclude_none=True)
    for k in update_fields:
        if k in update_data:
            setattr(r, k, update_data[k])
    db.flush()
    db.refresh(r)
    return _job_to_dict(r)


def delete_job(db: Session, job_id: int, project_id: int) -> bool:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        return False
    db.delete(r)
    db.flush()
    return True


def trigger_job(db: Session, job_id: int, project_id: int) -> dict:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        raise ValueError("任务不存在")

    r.status = "running"
    db.flush()

    run = UiTestRun(job_id=job_id, status="running", started_at=datetime.now(timezone.utc))
    db.add(run)
    db.flush()

    # Simulate execution
    total = random.randint(5, 20)
    pass_ = random.randint(0, total)
    fail = total - pass_
    result = {
        "total": total, "pass_": pass_, "fail": fail,
        "skip": 0, "duration": round(random.uniform(10, 120), 1),
    }
    run.result = json.dumps(result, ensure_ascii=False)
    run.status = "done"
    run.finished_at = datetime.now(timezone.utc)
    run.screenshots = json.dumps([f"screenshots/job_{job_id}_run_{run.id}_01.png"], ensure_ascii=False)

    r.last_result = json.dumps(result, ensure_ascii=False)
    r.status = "done"

    db.flush()
    db.refresh(run)
    return _run_to_dict(run)


def list_runs(db: Session, job_id: int, project_id: int, page: int = 1, page_size: int = 20):
    job = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not job:
        return [], 0
    base = select(UiTestRun).where(UiTestRun.job_id == job_id)
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    rows = db.execute(
        base.order_by(UiTestRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return [_run_to_dict(r) for r in rows], total


def get_run(db: Session, run_id: int) -> dict | None:
    r = db.get(UiTestRun, run_id)
    if not r:
        return None
    return _run_to_dict(r)
