"""UI test API routes."""
from __future__ import annotations

from datetime import datetime, timezone

import os as _os
from pathlib import Path as _Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import R
from app.schemas.ui_test import UiTestJobCreate, UiTestJobDetailOut, UiTestJobOut, UiTestJobUpdate, UiTestRunOut
from app.services import ui_test_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/ui-tests", tags=["UI 自动化"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db, user_id=cu.user.id, username=cu.user.username or "",
        project_id=cu.project_id or 0, action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ═══════════════════════════════════════════════════════
# 静态路径路由（必须在 /{job_id} 之前注册，避免被动态段误匹配）
# ═══════════════════════════════════════════════════════

@router.get("", response_model=R[dict])
def list_jobs(
    status: str | None = Query(None),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("uitest:list")),
    db: Session = Depends(get_db),
):
    items, total = ui_test_service.list_jobs(
        db, project_id=current.project_id or 0,
        status=status, keyword=keyword, page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("", response_model=R[UiTestJobOut])
def create_job(
    req: Request, body: UiTestJobCreate,
    current: CurrentUser = Depends(require_permission("uitest:create")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.create_job(db, body, current.user.id, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "uitest:create", f"#{r['id']} {r['name']}")
    return R.ok(UiTestJobOut(**r))


@router.get("/scripts", response_model=R[dict], summary="脚本资产列表")
def list_script_assets(
    current: CurrentUser = Depends(require_permission("uitest:list")),
    db: Session = Depends(get_db),
):
    """返回脚本资产 + 文件系统中可用的 Playwright 脚本。"""
    assets = ui_test_service.list_script_assets(db, current.project_id or 0)
    specs = ui_test_service.list_available_specs()
    return R.ok({"assets": assets, "available_specs": specs})


@router.post("/scripts", response_model=R[dict], summary="创建脚本资产")
def create_script_asset(
    req: Request, body,
    current: CurrentUser = Depends(require_permission("uitest:create")),
    db: Session = Depends(get_db),
):
    from app.schemas.ui_test import UiTestScriptCreate as C
    body = C.model_validate(body if isinstance(body, dict) else body.model_dump())
    r = ui_test_service.create_script_asset(db, body, current.project_id or 0)
    db.commit()
    _audit(req, current, db, "uitest:script_create", f"#{r['id']} {r['name']}")
    return R.ok(r)


@router.get("/scripts/{script_id}", response_model=R[dict], summary="脚本资产详情")
def get_script_asset(
    script_id: int,
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.get_script_asset(db, script_id, current.project_id or 0)
    if not r:
        raise HTTPException(404, "脚本资产不存在")
    return R.ok(r)


@router.put("/scripts/{script_id}", response_model=R[dict], summary="更新脚本资产")
def update_script_asset(
    req: Request, script_id: int, body,
    current: CurrentUser = Depends(require_permission("uitest:update")),
    db: Session = Depends(get_db),
):
    from app.schemas.ui_test import UiTestScriptUpdate as U
    body = U.model_validate(body if isinstance(body, dict) else body.model_dump())
    r = ui_test_service.update_script_asset(db, script_id, body, current.project_id or 0)
    if not r:
        raise HTTPException(404, "脚本资产不存在")
    db.commit()
    _audit(req, current, db, "uitest:script_update", f"#{script_id}")
    return R.ok(r)


@router.delete("/scripts/{script_id}", response_model=R[dict], summary="删除脚本资产")
def delete_script_asset(
    req: Request, script_id: int,
    current: CurrentUser = Depends(require_permission("uitest:delete")),
    db: Session = Depends(get_db),
):
    ok = ui_test_service.delete_script_asset(db, script_id, current.project_id or 0)
    if not ok:
        raise HTTPException(404, "脚本资产不存在")
    db.commit()
    _audit(req, current, db, "uitest:script_delete", f"#{script_id}")
    return R.ok({"deleted": True})


@router.get("/runs/{run_id}", response_model=R[UiTestRunOut], summary="获取运行记录详情")
def get_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    """查询单次运行记录（用于前端轮询状态）。"""
    run = ui_test_service.get_run(db, run_id)
    if not run:
        from app.core.exceptions import not_found
        raise not_found("运行记录")
    return R.ok(UiTestRunOut(**run))


@router.post("/runs/{run_id}/cancel", response_model=R[dict], summary="取消运行中的 UI 测试")
def cancel_run(
    req: Request, run_id: int,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
    db: Session = Depends(get_db),
):
    """取消正在运行的 UI 测试。"""
    from app.models.ui_test import UiTestRun, UiTestJob
    run = db.get(UiTestRun, run_id)
    if not run:
        raise HTTPException(404, "运行记录不存在")
    if run.status not in ("pending", "running"):
        raise HTTPException(400, f"只能取消 pending/running 状态的运行（当前: {run.status}）")
    run.status = "cancelled"
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = "用户手动取消"
    # Update job status too
    job = db.get(UiTestJob, run.job_id)
    if job and job.status == "running":
        job.status = "idle"
    db.commit()
    _audit(req, current, db, "uitest:cancel", f"run #{run_id}")
    return R.ok({"status": "cancelled", "run_id": run_id})


@router.get("/runs/{run_id}/artifacts", response_model=R[list[dict]], summary="运行产物列表")
def list_artifacts(
    run_id: int,
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    """列出某次运行的所有产物文件（截图/视频/trace/报告）。"""
    from app.models.ui_test import UiTestRun

    run = db.get(UiTestRun, run_id)
    if not run:
        raise HTTPException(404, "运行记录不存在")

    artifact_dir = _Path(run.artifact_dir) if run.artifact_dir else None
    if not artifact_dir or not artifact_dir.exists():
        return R.ok([])

    files = []
    for f in sorted(artifact_dir.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(artifact_dir)).replace("\\", "/")
            files.append({
                "name": f.name,
                "path": rel,
                "size_bytes": f.stat().st_size,
                "type": f.suffix.lstrip("."),
            })
    return R.ok(files)


@router.get("/runs/{run_id}/artifacts/{filename:path}", summary="下载运行产物")
def download_artifact(
    run_id: int,
    filename: str,
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    """下载某次运行的产物文件。"""
    from app.models.ui_test import UiTestRun

    run = db.get(UiTestRun, run_id)
    if not run:
        raise HTTPException(404, "运行记录不存在")

    artifact_dir = _Path(run.artifact_dir) if run.artifact_dir else None
    if not artifact_dir:
        raise HTTPException(404, "该运行无产物目录")

    # 防目录遍历
    safe_path = _os.path.normpath(filename).lstrip("\\/")
    file_path = (artifact_dir / safe_path).resolve()
    if not str(file_path).startswith(str(artifact_dir.resolve())):
        raise HTTPException(403, "非法文件路径")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"产物文件不存在: {safe_path}")

    return FileResponse(file_path, filename=file_path.name)


# ═══════════════════════════════════════════════════════
# 动态 {job_id} 路由（必须在静态路径之后注册）
# ═══════════════════════════════════════════════════════

@router.get("/{job_id}", response_model=R[UiTestJobDetailOut])
def get_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.get_job(db, job_id, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("UI测试任务")
    return R.ok(UiTestJobDetailOut(**r))


@router.put("/{job_id}", response_model=R[UiTestJobOut])
def update_job(
    req: Request, job_id: int, body: UiTestJobUpdate,
    current: CurrentUser = Depends(require_permission("uitest:update")),
    db: Session = Depends(get_db),
):
    r = ui_test_service.update_job(db, job_id, body, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("UI测试任务")
    db.commit()
    _audit(req, current, db, "uitest:update", f"#{job_id}")
    return R.ok(UiTestJobOut(**r))


@router.delete("/{job_id}", response_model=R[dict])
def delete_job(
    req: Request, job_id: int,
    current: CurrentUser = Depends(require_permission("uitest:delete")),
    db: Session = Depends(get_db),
):
    ok = ui_test_service.delete_job(db, job_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("UI测试任务")
    db.commit()
    _audit(req, current, db, "uitest:delete", f"job #{job_id}")
    return R.ok({"deleted": True})


@router.post("/{job_id}/trigger", response_model=R[UiTestRunOut])
def trigger_job(
    req: Request, job_id: int,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
    db: Session = Depends(get_db),
):
    """触发 UI 测试 — 立即创建 run 并返回，后台异步执行 Playwright。"""
    try:
        run_dict = ui_test_service.trigger_job(db, job_id, current.project_id or 0)
        db.commit()
        _audit(req, current, db, "uitest:trigger", f"#{job_id} run=#{run_dict['id']}")

        # 仅当 Playwright 可用时才调度后台执行（不可用时 run 已标记 fail）
        if run_dict["status"] == "pending":
            background_tasks.add_task(
                ui_test_service.execute_playwright_async,
                run_dict["id"], job_id, current.project_id or 0,
            )

        return R.ok(UiTestRunOut(**run_dict))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{job_id}/runs", response_model=R[dict])
def get_runs(
    job_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("uitest:detail")),
    db: Session = Depends(get_db),
):
    items, total = ui_test_service.list_runs(
        db, job_id, current.project_id or 0, page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})
