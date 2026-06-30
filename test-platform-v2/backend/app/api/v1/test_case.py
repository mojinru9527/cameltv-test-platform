"""测试用例 API 路由 — /api/v1/test-cases/*"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
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


# ── 评审流 ──────────────────────────────────────────

class ReviewBody(BaseModel):
    action: str = Field(..., pattern="^(submit|approve|reject)$")
    comment: str = Field("", max_length=500)


_REVIEW_TRANSITIONS = {
    "submit":  {"from": {"draft", "rejected"}, "to": "submitted"},
    "approve": {"from": {"submitted"},            "to": "approved"},
    "reject":  {"from": {"submitted"},            "to": "rejected"},
}
_REVIEW_LABELS = {"draft": "草稿", "submitted": "已提交", "approved": "已通过", "rejected": "已驳回"}


@router.post("/{case_id}/review", response_model=R[TestCaseOut], summary="用例评审操作")
def review_case(
    case_id: int,
    body: ReviewBody,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:update")),
    db: Session = Depends(get_db),
):
    """提交评审 / 通过 / 驳回。合法流转: draft/rejected→submitted→approved/rejected。"""
    row = test_case_service.update_case(db, case_id, {"_": None})  # just check exists
    # Actually fetch the raw ORM row for review_status
    from app.models.test_case import TestCase
    case = db.scalar(
        __import__("sqlalchemy").select(TestCase).where(
            TestCase.id == case_id, TestCase.project_id == current.project_id
        )
    )
    if not case:
        return R(code=404, msg="用例不存在")

    rule = _REVIEW_TRANSITIONS[body.action]
    if case.review_status not in rule["from"]:
        allowed = ", ".join(f"{s}({_REVIEW_LABELS.get(s,s)})" for s in rule["from"])
        return R(code=1, msg=f"不允许从「{_REVIEW_LABELS.get(case.review_status, case.review_status)}」执行「{body.action}」，仅允许从 {allowed} 操作")

    case.review_status = rule["to"]
    case.review_comment = body.comment
    case.reviewer_id = current.user.id
    db.commit()
    db.refresh(case)

    _audit(req, current, db, "case:review", f"#{case_id} {body.action}", body.comment)
    row_dict = test_case_service.get_case(db, case_id, project_id=current.project_id or 0)
    return R.ok(TestCaseOut(**row_dict) if row_dict else TestCaseOut(id=case_id))


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
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    """解析 Xmind 文件，批量创建用例。"""
    from app.core.base_service import transaction
    from app.services.xmind_service import xmind_bytes_to_cases

    if not file.filename or not file.filename.endswith(".xmind"):
        return R(code=1, msg="请上传 .xmind 文件")

    raw = file.file.read()
    cases = xmind_bytes_to_cases(raw)
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
