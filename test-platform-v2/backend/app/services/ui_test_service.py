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


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite-naive and timezone-aware timestamps to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _job_to_dict(r: UiTestJob, creator_name: str = "") -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "name": r.name, "description": r.description,
        "test_spec": r.test_spec, "browser": r.browser,
        "environment_id": r.environment_id,
        "case_id": getattr(r, "case_id", None),
        "case_title": "",
        "status": r.status,
        "cron_expression": r.cron_expression,
        "schedule_enabled": r.schedule_enabled, "last_result": r.last_result,
        "creator_id": r.creator_id, "creator_name": creator_name,
        "created_at": r.created_at, "updated_at": r.updated_at,
        "last_run_status": "", "last_run_time": None,
    }


def _run_to_dict(r: UiTestRun, job: UiTestJob | None = None) -> dict:
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
    # Compute duration
    duration = None
    if r.started_at and r.finished_at:
        duration = round((_as_utc(r.finished_at) - _as_utc(r.started_at)).total_seconds(), 2)
    elif r.started_at and r.status == "running":
        now = datetime.now(timezone.utc)
        duration = round((now - _as_utc(r.started_at)).total_seconds(), 2)
    # Browser from job
    browser = job.browser if job else ""
    # Truncate stdout/stderr for API response
    stdout_summary = (r.stdout or "")[:5000]
    stderr_summary = (r.stderr or "")[:2000]
    return {
        "id": r.id, "job_id": r.job_id, "status": r.status,
        "result": result, "screenshots": screenshots,
        "video_url": r.video_url, "trace_id": r.trace_id,
        "base_url": r.base_url or "",
        "browser": browser,
        "duration": duration,
        "error_message": r.error_message or "",
        "stdout": stdout_summary,
        "stderr": stderr_summary,
        "artifact_dir": r.artifact_dir or "",
        "report_json_path": r.report_json_path or "",
        "html_report_path": r.html_report_path or "",
        "process_id": r.process_id,
        "cancel_requested": bool(r.cancel_requested),
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

    # C151-1: 批量加载关联用例标题
    case_ids = {getattr(r, "case_id", None) for r in rows if getattr(r, "case_id", None)}
    case_title_map: dict[int, str] = {}
    if case_ids:
        from app.models.test_case import TestCase
        case_rows = db.scalars(select(TestCase).where(TestCase.id.in_(case_ids))).all()
        case_title_map = {c.id: c.title for c in case_rows}

    items = []
    for r in rows:
        d = _job_to_dict(r, user_map.get(r.creator_id, ""))
        d["case_title"] = case_title_map.get(getattr(r, "case_id", None), "")
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
        case_id=getattr(data, "case_id", None),
        cron_expression=getattr(data, "cron_expression", ""),
        schedule_enabled=getattr(data, "schedule_enabled", False),
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()
    _sync_schedule(db, r, project_id)
    return _job_to_dict(r)


def update_job(db: Session, job_id: int, data, project_id: int) -> dict | None:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        return None
    update_fields = ["name", "description", "test_spec", "browser", "environment_id", "case_id",
                     "cron_expression", "schedule_enabled"]
    update_data = data.model_dump(exclude_none=True)
    for k in update_fields:
        if k in update_data:
            setattr(r, k, update_data[k])
    db.flush()
    db.refresh(r)
    _sync_schedule(db, r, project_id)
    return _job_to_dict(r)


def delete_job(db: Session, job_id: int, project_id: int) -> bool:
    r = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not r:
        return False
    _disable_linked_schedule(db, job_id, project_id)
    db.delete(r)
    db.flush()
    return True


def _sync_schedule(db: Session, job, project_id: int) -> None:
    """B112-3：UI job 定时开关与 cron 联动 TestSchedule（job_type=ui）。"""
    from app.models.test_schedule import TestSchedule
    from app.core.scheduler import add_schedule_job, toggle_schedule_job

    sched = db.scalar(
        select(TestSchedule).where(
            TestSchedule.job_type == "ui",
            TestSchedule.job_id == job.id,
            TestSchedule.project_id == project_id,
        )
    )
    if job.schedule_enabled and job.cron_expression:
        if sched is None:
            sched = TestSchedule(
                project_id=project_id,
                name=f"UI:{job.name}",
                description=f"UI job #{job.id} 定时回归（B112-3）",
                plan_id=None,
                job_type="ui",
                job_id=job.id,
                cron_expression=job.cron_expression,
                enabled=True,
                creator_id=job.creator_id,
            )
            db.add(sched)
            db.flush()
            add_schedule_job(sched.id, sched.cron_expression)
        else:
            if sched.cron_expression != job.cron_expression or not sched.enabled:
                sched.cron_expression = job.cron_expression
                sched.enabled = True
                add_schedule_job(sched.id, sched.cron_expression)
    else:
        _disable_linked_schedule(db, job.id, project_id)


def _disable_linked_schedule(db: Session, job_id: int, project_id: int) -> None:
    from app.models.test_schedule import TestSchedule
    from app.core.scheduler import toggle_schedule_job

    sched = db.scalar(
        select(TestSchedule).where(
            TestSchedule.job_type == "ui",
            TestSchedule.job_id == job_id,
            TestSchedule.project_id == project_id,
        )
    )
    if sched and sched.enabled:
        toggle_schedule_job(sched.id, False, sched.cron_expression)
        sched.enabled = False


def _resolve_environment(db: Session, environment_id: int | None, project_id: int):
    """Resolve an execution environment without crossing the project boundary."""
    if not environment_id:
        return None
    from app.models.environment import Environment
    return db.scalar(
        select(Environment).where(
            Environment.id == environment_id,
            Environment.project_id == project_id,
        )
    )


def trigger_job(
    db: Session,
    job_id: int,
    project_id: int,
    *,
    confirm_prod: bool = False,
    has_trigger_prod: bool = False,
) -> dict:
    """触发 UI 测试执行 — 创建 run 记录，入队，立即返回。

    Playwright 执行由 ui_runner_queue 后台线程池异步驱动，
    不再阻塞请求线程或依赖 FastAPI BackgroundTasks。
    """

    from app.services.playwright_executor import _check_playwright_installed

    job = db.scalar(select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id))
    if not job:
        raise ValueError("任务不存在")

    if job.status == "running":
        raise ValueError("任务正在执行中，请等待完成后再触发")

    environment = _resolve_environment(db, job.environment_id, project_id)
    if job.environment_id and not environment:
        raise ValueError("执行环境不存在或不属于当前项目")
    if environment and (environment.env_type == "prod" or environment.is_production):
        if not has_trigger_prod:
            raise PermissionError("生产环境 UI 自动化需要 uitest:trigger_prod 权限")
        if not confirm_prod:
            raise ValueError("生产环境 UI 自动化需要 confirm_prod=true 确认")

    # 检查 Playwright 可用性并记录
    pw_ok, pw_msg = _check_playwright_installed()

    # 解析环境的 base_url
    base_url = environment.base_url if environment else ""

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
        run.status = "failed"
        run.finished_at = now
        run.error_message = f"Playwright 不可用: {pw_msg}"
        run.result = json.dumps({"error": pw_msg}, ensure_ascii=False)
        job.status = "failed"
        job.last_result = json.dumps({"error": f"Playwright 不可用: {pw_msg}"}, ensure_ascii=False)

    db.add(run)
    db.commit()
    db.refresh(run)

    # 仅当 Playwright 可用时才入队后台执行（不可用时 run 已标记 fail）
    if pw_ok:
        from app.services.ui_runner_queue import enqueue_run
        enqueue_run(run.id, job_id, project_id)

    return _run_to_dict(run, job)


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
        # C151-1: 回写用例结果
        run = db.get(UiTestRun, run_id)
        job = db.get(UiTestJob, job_id)
        if run and job:
            writeback_case_result(db, job, run)
            db.commit()
    except Exception:
        logger.exception("UI test async execution failed: run_id=%s, job_id=%s", run_id, job_id)
        try:
            run = db.get(UiTestRun, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.error_message = "执行器崩溃: 详见日志"
            job = db.get(UiTestJob, job_id)
            if job:
                job.status = "failed"
                job.last_result = json.dumps({"error": "执行器内部异常"}, ensure_ascii=False)
                writeback_case_result(db, job, run) if run else None
            db.commit()
        except Exception:
            logger.exception("Failed to update run/job after crash: run_id=%s", run_id)
    finally:
        db.close()


def writeback_case_result(db: Session, job: UiTestJob, run: UiTestRun) -> None:
    """C151-1: UI 运行结果回写关联用例（last_run_status + last_response_json）。"""
    case_id = getattr(job, "case_id", None)
    if not case_id:
        return
    from app.models.test_case import TestCase

    from app.core.execution_status import canonical_exec_status

    case = db.get(TestCase, case_id)
    if not case:
        return
    # Batch 182（P1-06）：run.status 已是统一词表（passed/failed/…）；
    # 兼容历史 done/fail 旧值；回写用例 last_run_status 使用统一词表
    s = canonical_exec_status(run.status)
    status_map = {"passed": "passed", "failed": "failed", "cancelled": "skipped",
                  "pending": "pending", "running": "running"}
    case.last_run_status = status_map.get(s, s)
    try:
        summary = json.loads(run.result or "{}")
    except (json.JSONDecodeError, TypeError):
        summary = {"error": (run.error_message or "")[:500]}
    summary["ui_run_id"] = run.id
    summary["ui_job_id"] = job.id
    case.last_response_json = json.dumps(summary, ensure_ascii=False)[:4000]


def create_jobs_from_cases(
    db: Session,
    *,
    project_id: int,
    case_ids: list[int],
    creator_id: int,
) -> dict:
    """C151-1: 从用例批量创建 UI 任务（映射 case_id，spec 由用户后续补充）。"""
    from app.models.test_case import TestCase

    if not case_ids:
        raise ValueError("请选择用例")
    rows = db.scalars(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestCase.id.in_(case_ids),
        )
    ).all()
    if not rows:
        raise ValueError("用例不存在或不属于当前项目")
    created = []
    for case in rows:
        job = UiTestJob(
            project_id=project_id,
            name=f"[用例] {case.title}"[:200],
            case_id=case.id,
            browser="chromium",
            creator_id=creator_id,
        )
        db.add(job)
        db.flush()
        created.append({"job_id": job.id, "case_id": case.id, "case_title": case.title})
    db.commit()
    return {"created": len(created), "items": created}


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


def get_run(db: Session, run_id: int, project_id: int | None = None) -> dict | None:
    r = db.get(UiTestRun, run_id)
    if not r:
        return None
    # Verify project isolation: the run's job must belong to the current project
    if project_id is not None and project_id != 0:
        job = db.get(UiTestJob, r.job_id)
        if not job or job.project_id != project_id:
            return None  # treat as not-found to avoid leaking cross-project data
    else:
        job = db.get(UiTestJob, r.job_id)
    return _run_to_dict(r, job)


def get_project_run(db: Session, run_id: int, project_id: int) -> UiTestRun | None:
    """Load a run only through its owning job and current project (route-layer)."""
    return db.scalar(
        select(UiTestRun)
        .join(UiTestJob, UiTestJob.id == UiTestRun.job_id)
        .where(UiTestRun.id == run_id, UiTestJob.project_id == project_id)
    )


def get_run_orm(db: Session, run_id: int) -> UiTestRun | None:
    """Fetch a run record by primary key (route-layer cancel path)."""
    return db.get(UiTestRun, run_id)


def get_job_orm(db: Session, job_id: int) -> UiTestJob | None:
    """Fetch a job record by primary key (route-layer cancel path)."""
    return db.get(UiTestJob, job_id)


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


# ═══════════════════════════════════════════════════════
# Batch 182（C181-1）open_api 路由层 ORM 收敛薄函数
# ═══════════════════════════════════════════════════════

def get_job_row(db: Session, job_id: int, project_id: int) -> UiTestJob | None:
    """项目内按 id 查询 UI 任务行（open_api CI 触发复用）。"""
    return db.scalar(
        select(UiTestJob).where(UiTestJob.id == job_id, UiTestJob.project_id == project_id)
    )


def trigger_ui_test_from_ci(
    db: Session,
    job_id: int,
    project_id: int,
    *,
    token_name: str,
) -> tuple[UiTestJob | None, UiTestRun | None, str | None]:
    """外部 CI 触发 UI 任务：创建 run 记录并更新 job 状态。

    返回 (job, run, pw_error)：
    - job 不存在 → (None, None, None)；
    - 任务正在执行 → 抛 ValueError（路由层转 400）；
    - Playwright 不可用 → run 已标记 failed，pw_error 为原因（非空）。
    沿用调用方会话、不 commit（提交由路由层负责）。
    """
    job = get_job_row(db, job_id, project_id)
    if not job:
        return None, None, None

    if job.status == "running":
        raise ValueError("任务正在执行中，请等待完成后再触发")

    # 检查 Playwright
    from app.services.playwright_executor import _check_playwright_installed
    pw_ok, pw_msg = _check_playwright_installed()

    # 解析环境 base_url
    base_url = ""
    if job.environment_id:
        env = _resolve_environment(db, job.environment_id, project_id)
        base_url = env.base_url if env else ""

    now = datetime.now(timezone.utc)
    job.status = "running" if pw_ok else "failed"
    job.last_result = json.dumps({} if pw_ok else {"error": pw_msg}, ensure_ascii=False)

    run = UiTestRun(
        job_id=job_id,
        status="pending" if pw_ok else "failed",
        base_url=base_url,
        started_at=now,
        result=json.dumps({}, ensure_ascii=False),
    )
    if not pw_ok:
        run.status = "failed"
        run.finished_at = now
        run.error_message = f"Playwright 不可用: {pw_msg}"
        run.result = json.dumps({"error": pw_msg}, ensure_ascii=False)

    db.add(run)
    db.flush()
    return job, run, None if pw_ok else pw_msg
