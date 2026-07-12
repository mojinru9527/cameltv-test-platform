"""UI test service."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_user_names, paginate
from app.models.ui_test import UiTestJob, UiTestRun
from app.models.user import User

logger = logging.getLogger("uitest")


def _job_to_dict(r: UiTestJob, creator_name: str = "") -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "name": r.name, "description": r.description,
        "test_spec": r.test_spec, "browser": r.browser,
        "environment_id": r.environment_id,
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
        "base_url": r.base_url or "",
        "error_message": r.error_message or "",
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
        browser=data.browser, environment_id=data.environment_id,
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()
    return _job_to_dict(r)


def update_job(db: Session, job_id: int, data, project_id: int) -> dict | None:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        return None
    update_fields = ["name", "description", "test_spec", "browser", "environment_id"]
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


def _resolve_base_url(db: Session, environment_id: int | None) -> str:
    """从环境配置解析 base_url，未配置则返回空字符串。"""
    if not environment_id:
        return ""
    from app.models.environment import Environment
    env = db.get(Environment, environment_id)
    return env.base_url if env else ""


def trigger_job(db: Session, job_id: int, project_id: int) -> dict:
    """触发 UI 测试执行 — 创建 run 记录并立即返回（异步执行由 BackgroundTasks 驱动）。"""

    from app.services.playwright_executor import _check_playwright_installed

    job = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not job:
        raise ValueError("任务不存在")

    if job.status == "running":
        raise ValueError("任务正在执行中，请等待完成后再触发")

    # 检查 Playwright 可用性并记录
    pw_ok, pw_msg = _check_playwright_installed()

    # 解析环境的 base_url
    base_url = _resolve_base_url(db, job.environment_id)

    now = datetime.now(timezone.utc)
    job.status = "running"
    job.last_result = json.dumps({}, ensure_ascii=False)

    # 创建运行记录（pending → 后台 worker 会更新为 running → done/fail）
    run = UiTestRun(
        job_id=job_id,
        status="pending",
        base_url=base_url,
        started_at=now,
        result=json.dumps({}, ensure_ascii=False),
    )
    if not pw_ok:
        # Playwright 不可用 → 直接标记失败，无需后台执行
        run.status = "fail"
        run.finished_at = now
        run.error_message = f"Playwright 不可用: {pw_msg}"
        run.result = json.dumps({"error": pw_msg}, ensure_ascii=False)
        job.status = "fail"
        job.last_result = json.dumps({"error": f"Playwright 不可用: {pw_msg}"}, ensure_ascii=False)

    db.add(run)
    db.commit()
    db.refresh(run)
    return _run_to_dict(run)


def execute_playwright_async(run_id: int, job_id: int, project_id: int):
    """后台异步执行 Playwright 测试（独立 DB session）。

    由 BackgroundTasks 调用，更新已有的 UiTestRun 记录。
    所有失败路径都会将 run.status 设为 'fail' 并记录 error_message。
    """
    from app.core.db import SessionLocal
    from app.services.playwright_executor import run_playwright_test as _run_pw

    db = SessionLocal()
    try:
        _run_pw(db, run_id, job_id, project_id)
    except Exception:
        logger.exception("UI test async execution failed: run_id=%s, job_id=%s", run_id, job_id)
        try:
            run = db.get(UiTestRun, run_id)
            if run:
                run.status = "fail"
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = f"执行器崩溃: 详见日志"
            job = db.get(UiTestJob, job_id)
            if job:
                job.status = "fail"
                job.last_result = json.dumps({"error": "执行器内部异常"}, ensure_ascii=False)
            db.commit()
        except Exception:
            logger.exception("Failed to update run/job after crash: run_id=%s", run_id)
    finally:
        db.close()


def list_available_specs() -> list[str]:
    """返回可用的 Playwright 测试脚本列表。"""
    from app.services.playwright_executor import _list_available_specs
    return _list_available_specs()


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


# ═══════════════════════════════════════════════════════
# UI 脚本资产管理
# ═══════════════════════════════════════════════════════

def list_script_assets(db: Session, project_id: int) -> list[dict]:
    """列出项目的脚本资产。"""
    from app.models.ui_test import UiTestScript
    rows = db.scalars(
        select(UiTestScript)
        .where(UiTestScript.project_id == project_id)
        .order_by(UiTestScript.updated_at.desc())
    ).all()
    return [_script_to_dict(r) for r in rows]


def get_script_asset(db: Session, script_id: int, project_id: int) -> dict | None:
    from app.models.ui_test import UiTestScript
    r = db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id, UiTestScript.project_id == project_id
    ))
    return _script_to_dict(r) if r else None


def create_script_asset(db: Session, data, project_id: int) -> dict:
    from app.models.ui_test import UiTestScript
    r = UiTestScript(
        project_id=project_id, name=data.name,
        script_key=data.script_key, spec_path=data.spec_path,
        module=data.module, owner=data.owner,
        tags=data.tags, status=data.status,
    )
    db.add(r)
    db.flush()
    return _script_to_dict(r)


def update_script_asset(db: Session, script_id: int, data, project_id: int) -> dict | None:
    from app.models.ui_test import UiTestScript
    r = db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id, UiTestScript.project_id == project_id
    ))
    if not r:
        return None
    update_fields = ["name", "script_key", "spec_path", "module", "owner", "tags", "status"]
    update_data = data.model_dump(exclude_none=True)
    for k in update_fields:
        if k in update_data:
            setattr(r, k, update_data[k])
    db.flush()
    db.refresh(r)
    return _script_to_dict(r)


def delete_script_asset(db: Session, script_id: int, project_id: int) -> bool:
    from app.models.ui_test import UiTestScript
    r = db.scalar(select(UiTestScript).where(
        UiTestScript.id == script_id, UiTestScript.project_id == project_id
    ))
    if not r:
        return False
    db.delete(r)
    db.flush()
    return True


def _script_to_dict(r) -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "name": r.name, "script_key": r.script_key,
        "spec_path": r.spec_path, "module": r.module,
        "owner": r.owner, "tags": r.tags, "status": r.status,
        "created_at": r.created_at, "updated_at": r.updated_at,
    }
