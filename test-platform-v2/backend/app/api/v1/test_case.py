"""测试用例 API 路由 — /api/v1/test-cases/*"""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.schemas.common import Page, R
from app.schemas.test_case import (
    DomainNode,
    TestCaseCreate,
    TestCaseFilter,
    TestCaseOut,
    TestCaseUpdate,
)
from app.services import audit_service, test_case_service
from app.services.api_execution_service import execute_api_case

router = APIRouter(prefix="/test-cases", tags=["测试用例"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    audit_service.write_audit(
        db,
        user_id=cu.user.id,
        username=cu.user.username,
        project_id=cu.project_id or 0,
        action=action,
        target=target,
        detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── 域树 ──────────────────────────────────────────────

@router.get("/domains", response_model=R[list[DomainNode]])
def list_domains(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tree = test_case_service.get_domain_tree(db, project_id=current.project_id or 0)
    return R.ok(tree)


# ── 用例 CRUD ─────────────────────────────────────────

@router.get("", response_model=R[Page[TestCaseOut]])
def list_test_cases(
    domain: str = "",
    module: str = "",
    case_type: str = "",
    priority: str = "",
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    items, total = test_case_service.list_cases(
        db,
        project_id=current.project_id or 0,
        domain=domain,
        module=module,
        case_type=case_type,
        priority=priority,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return R.ok(
        Page(total=total, page=page, page_size=page_size, items=[TestCaseOut(**it) for it in items])
    )


@router.get("/{case_id}", response_model=R[TestCaseOut])
def get_test_case(
    case_id: int,
    current: CurrentUser = Depends(require_permission("testcase:detail")),
    db: Session = Depends(get_db),
):
    row = test_case_service.get_case(db, case_id, project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="用例不存在")
    return R.ok(TestCaseOut(**row))


@router.post("", response_model=R[TestCaseOut])
def create_test_case(
    body: TestCaseCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    data = body.model_dump()
    data["project_id"] = current.project_id or 0
    row = test_case_service.create_case(db, data)
    _audit(req, current, db, "case:create", f"#{row['id']} {row['title']}")
    return R.ok(TestCaseOut(**row))


@router.put("/{case_id}", response_model=R[TestCaseOut])
def update_test_case(
    case_id: int,
    body: TestCaseUpdate,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:update")),
    db: Session = Depends(get_db),
):
    row = test_case_service.update_case(db, case_id, body.model_dump(exclude_none=True))
    if not row:
        return R(code=404, msg="用例不存在")
    _audit(req, current, db, "case:update", f"#{row['id']} {row['title']}")
    return R.ok(TestCaseOut(**row))


@router.delete("/{case_id}", response_model=R[dict])
def delete_test_case(
    case_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:delete")),
    db: Session = Depends(get_db),
):
    ok = test_case_service.delete_case(db, case_id, project_id=current.project_id or 0)
    if not ok:
        return R(code=404, msg="用例不存在或无权操作")
    _audit(req, current, db, "case:delete", f"#{case_id}")
    return R.ok({"deleted": case_id})


# ── 批量操作 ──────────────────────────────────────────

from pydantic import BaseModel, Field


class BatchUpdateBody(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=200)
    priority: str | None = None
    domain: str | None = None
    module: str | None = None
    status: str | None = None
    case_type: str | None = None


class BatchDeleteBody(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=200)


@router.put("/batch", response_model=R[dict], summary="批量更新用例")
def batch_update_test_cases(
    body: BatchUpdateBody,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:update")),
    db: Session = Depends(get_db),
):
    """批量更新指定用例的优先级/域/模块/状态/类型。"""
    from app.core.base_service import transaction

    fields = {k: v for k, v in body.model_dump().items() if k != "ids" and v is not None}
    if not fields:
        return R(code=1, msg="请至少指定一个要更新的字段")

    updated = 0
    with transaction(db):
        for case_id in body.ids:
            row = test_case_service.update_case(db, case_id, fields)
            if row:
                updated += 1

    _audit(req, current, db, "case:batch_update", f"{updated}/{len(body.ids)} 条用例")
    return R.ok({"updated": updated, "total": len(body.ids)})


@router.delete("/batch", response_model=R[dict], summary="批量删除用例")
def batch_delete_test_cases(
    body: BatchDeleteBody,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:delete")),
    db: Session = Depends(get_db),
):
    """批量删除指定用例（事务原子性）。"""
    from app.core.base_service import transaction

    deleted = 0
    with transaction(db):
        for case_id in body.ids:
            if test_case_service.delete_case(db, case_id, project_id=current.project_id or 0):
                deleted += 1

    _audit(req, current, db, "case:batch_delete", f"{deleted}/{len(body.ids)} 条用例")
    return R.ok({"deleted": deleted, "total": len(body.ids)})


# ── API 执行 ──────────────────────────────────────────

class ExecuteApiBody(BaseModel):
    environment_id: int | None = None

@router.post("/{case_id}/execute", response_model=R[dict], summary="执行 API 用例")
def execute_test_case(
    case_id: int,
    body: ExecuteApiBody | None = None,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """对已保存的 API 类型用例发起真实 HTTP 请求，返回响应 + 断言结果。"""
    try:
        result = execute_api_case(
            db, case_id,
            project_id=current.project_id or 0,
            environment_id=body.environment_id if body else None,
        )
    except ValueError as e:
        return R(code=1, msg=str(e))
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    return R.ok(result)


# ── 评审流 ──────────────────────────────────────────

class ReviewBody(BaseModel):
    action: str = Field(..., pattern="^(submit|approve|reject|withdraw)$")
    comment: str = Field("", max_length=500)


def _run_notify_in_new_session(project_id: int, event: str, data: dict) -> None:
    """在独立 DB session 中发送通知（供 BackgroundTasks 调用）。"""
    import logging
    from app.core.db import SessionLocal
    from app.services.notify_service import notify_sync
    logger = logging.getLogger("review")
    db2 = SessionLocal()
    try:
        notify_sync(db2, project_id, event, data)
    except Exception:
        logger.exception("Background notification failed")
    finally:
        db2.close()


@router.post("/{case_id}/review", response_model=R[TestCaseOut], summary="用例评审操作")
def review_case(
    case_id: int,
    body: ReviewBody,
    req: Request,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("review:submit")),
    db: Session = Depends(get_db),
):
    """提交评审 / 通过 / 驳回 / 撤回。合法流转详见 review_service 状态机。"""
    from app.services import review_service
    from fastapi import BackgroundTasks as BgTasks

    # approve/reject use review:approve permission
    if body.action in ("approve", "reject"):
        # Re-check permission — the Depends above allows submit/withdraw via review:submit
        if "review:approve" not in current.permissions:
            from app.core.exceptions import APIException
            raise APIException(code=403, msg="需要审批评审权限 (review:approve)", http_status=403)

    try:
        row = review_service.transition_review(
            db, case_id, body.action,
            project_id=current.project_id or 0,
            operator_id=current.user.id,
            operator_name=current.user.nickname or current.user.username,
            comment=body.comment,
        )
    except ValueError as e:
        return R(code=1, msg=str(e))

    if not row:
        return R(code=404, msg="用例不存在")

    db.commit()

    _audit(req, current, db, "case:review", f"#{case_id} {body.action}", body.comment)

    # Background notification
    action_labels = {"submit": "提交评审", "approve": "评审通过", "reject": "评审驳回", "withdraw": "撤回评审"}
    background_tasks.add_task(
        _run_notify_in_new_session,
        current.project_id or 0,
        "case_reviewed",
        {
            "case_title": row.get("title", f"#{case_id}"),
            "action": action_labels.get(body.action, body.action),
            "reviewer": current.user.nickname or current.user.username,
            "comment": body.comment or "无",
            "link": "",
        },
    )

    return R.ok(TestCaseOut(**row))


@router.get("/{case_id}/review-history", response_model=R[list[dict]], summary="用例评审历史")
def review_history(
    case_id: int,
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """返回用例的完整评审流转记录。"""
    from app.services import review_service

    history = review_service.get_review_history(db, case_id, project_id=current.project_id or 0)
    return R.ok(history)


# ── Xmind 导入导出 ──────────────────────────────────

from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse


@router.get("/export/xmind", summary="导出用例为 Xmind")
def export_xmind(
    domain: str = "",
    module: str = "",
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """导出当前项目用例为 Xmind 文件（域→模块→用例树形结构）。"""
    from app.services.xmind_service import cases_to_xmind_bytes

    items, _ = test_case_service.list_cases(
        db, project_id=current.project_id or 0,
        domain=domain, module=module, page=1, page_size=10000,
    )
    buf = cases_to_xmind_bytes(items, root_title=f"测试用例-项目{current.project_id}")
    return StreamingResponse(
        BytesIO(buf.getvalue()),  # type: ignore[arg-type]
        media_type="application/vnd.xmind.workbook",
        headers={"Content-Disposition": "attachment; filename=test-cases.xmind"},
    )


@router.post("/import/xmind", response_model=R[dict], summary="从 Xmind 导入用例")
def import_xmind(
    req: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    """解析 Xmind 文件，批量创建用例。"""
    from app.core.base_service import transaction
    from app.services.xmind_service import xmind_bytes_to_cases

    if not file.filename or not file.filename.endswith(".xmind"):
        return R(code=1, msg="请上传 .xmind 文件")

    # P1-S6a: Content-Length 前置检查，避免读取超大文件 (max 10 MB)
    content_length = req.headers.get("content-length")
    if content_length:
        cl = int(content_length)
        max_bytes = 10 * 1024 * 1024
        if cl > max_bytes:
            from app.core.exceptions import APIException
            raise APIException(
                f"上传文件超过限制 (max: 10 MB, got: {cl / (1024*1024):.1f} MB)",
                code=413,
            )

    # P1-S6d: 流式写入临时文件，zipfile 直接从磁盘读取，避免全量加载到内存
    import os
    import shutil
    import tempfile
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xmind") as tmp:
            shutil.copyfileobj(file.file, tmp, length=64 * 1024)
            tmp_path = tmp.name
        cases = xmind_bytes_to_cases(tmp_path)
    finally:
        if tmp_path:
            os.unlink(tmp_path)
    if not cases:
        return R(code=1, msg="未能从 Xmind 文件中解析出用例")

    imported = 0
    with transaction(db):
        for c in cases:
            c["project_id"] = current.project_id or 0
            c["source"] = "xmind_import"
            row = test_case_service.create_case(db, c)
            if row:
                imported += 1

    return R.ok({"imported": imported, "total": len(cases)})


# ── Excel 导入导出 ──

@router.get("/export/excel", summary="导出用例为 Excel")
def export_excel(
    domain: str = "",
    module: str = "",
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """导出当前项目用例为 Excel 文件（.xlsx）。"""
    from app.services.excel_service import cases_to_excel_bytes

    items, _ = test_case_service.list_cases(
        db, project_id=current.project_id or 0,
        domain=domain, module=module, page=1, page_size=10000,
    )
    buf = cases_to_excel_bytes(items)
    return StreamingResponse(
        BytesIO(buf),  # type: ignore[arg-type]
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test-cases.xlsx"},
    )


@router.post("/import/excel", response_model=R[dict], summary="从 Excel 导入用例")
def import_excel(
    req: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    """解析 Excel 文件，批量创建用例。"""
    from app.core.base_service import transaction
    from app.services.excel_service import excel_bytes_to_cases

    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return R(code=1, msg="请上传 .xlsx 或 .xls 文件")

    # Content-Length check (max 10 MB)
    content_length = req.headers.get("content-length")
    if content_length:
        cl = int(content_length)
        max_bytes = 10 * 1024 * 1024
        if cl > max_bytes:
            from app.core.exceptions import APIException
            raise APIException(
                f"上传文件超过限制 (max: 10 MB, got: {cl / (1024*1024):.1f} MB)",
                code=413,
            )

    contents = file.file.read()
    cases = excel_bytes_to_cases(contents)
    if not cases:
        return R(code=1, msg="未能从 Excel 文件中解析出用例（请确保包含「用例标题」列）")

    imported = 0
    with transaction(db):
        for c in cases:
            c["project_id"] = current.project_id or 0
            row = test_case_service.create_case(db, c)
            if row:
                imported += 1

    return R.ok({"imported": imported, "total": len(cases)})


# ── 版本历史 ──

@router.get("/{case_id}/versions", response_model=R[list[dict]], summary="用例版本历史")
def list_versions(
    case_id: int,
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """返回用例的所有版本快照列表。"""
    from app.services.version_service import list_versions, get_version

    case = test_case_service.get_case(db, case_id, project_id=current.project_id or 0)
    if not case:
        return R.err(code=404, msg="用例不存在")

    versions = list_versions(db, case_id)
    return R.ok(versions)


@router.get("/{case_id}/versions/{version_id}", response_model=R[dict], summary="版本详情")
def get_version_detail(
    case_id: int,
    version_id: int,
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """返回单个版本快照详情（含完整 snapshot）。"""
    from app.services.version_service import get_version

    case = test_case_service.get_case(db, case_id, project_id=current.project_id or 0)
    if not case:
        return R.err(code=404, msg="用例不存在")

    version = get_version(db, version_id)
    if not version or version["case_id"] != case_id:
        return R.err(code=404, msg="版本不存在")
    return R.ok(version)
