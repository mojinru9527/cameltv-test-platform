"""测试用例 API 路由（CRUD/批量/API 执行/评审/版本历史） — /api/v1/test-cases/*

Batch 181（FIX-173-P2-10）路由拆分：原 test_case.py 按域拆分为
test_case_crud.py（本文件）/ test_case_taxonomy.py / test_case_files.py。
端点函数体逐字移动，仅调整 import；ORM 查询收敛至 services。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.api_asset import ApiExecutionRequest
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
)
from app.services import audit_service, rbac_service, test_case_service
from app.services.api_execution_service import execute_api_case
from app.services.knowledge import ingest_service
from app.services.production_operation_guard import ProductionOperation, require_allowed_operation

router = APIRouter(prefix="/test-cases", tags=["测试用例"])
logger = logging.getLogger("test_case")


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


# ── 用例 CRUD ─────────────────────────────────────────

@router.get("", response_model=R[Page[TestCaseOut]])
def list_test_cases(
    case_id: str = "",
    domain: str = "",
    module: str = "",
    surface: str = "",
    taxonomy_domain: str = "",
    taxonomy_module: str = "",
    taxonomy_direct: bool = False,
    case_type: str = "",
    positive_negative: str = "",
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
        case_id=case_id,
        domain=domain,
        module=module,
        surface=surface,
        taxonomy_domain=taxonomy_domain,
        taxonomy_module=taxonomy_module,
        taxonomy_direct=taxonomy_direct,
        case_type=case_type,
        positive_negative=positive_negative,
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
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    data = body.model_dump()
    data["project_id"] = current.project_id or 0
    row = test_case_service.create_case(db, data)
    db.commit()
    _audit(req, current, db, "case:create", f"#{row['id']} {row['title']}")
    if row.get("case_type") == "api":
        background_tasks.add_task(
            ingest_service.ingest_test_case_in_new_session, current.project_id or 0, row["id"]
        )
    return R.ok(TestCaseOut(**row))


# ── 批量操作 ──────────────────────────────────────────
# 契约铁律：静态路径段 /batch 必须注册在动态 /{case_id} 之前。
# FastAPI 按注册顺序匹配，若 /{case_id} 在先，PUT/DELETE /test-cases/batch
# 会被它抢匹配 → "batch" 解析为 int 失败 → 422。见 [[common-pitfalls]]。

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


@router.put("/{case_id}", response_model=R[TestCaseOut])
def update_test_case(
    case_id: int,
    body: TestCaseUpdate,
    req: Request,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("testcase:update")),
    db: Session = Depends(get_db),
):
    # C68-2：source_doc_id 必须指向当前项目内存在的需求文档
    link_error = test_case_service.validate_source_doc(
        db, body.source_doc_id, current.project_id or 0
    )
    if link_error:
        return R(code=400, msg=link_error)
    row = test_case_service.update_case(db, case_id, body.model_dump(exclude_none=True))
    if not row:
        return R(code=404, msg="用例不存在")
    _audit(req, current, db, "case:update", f"#{row['id']} {row['title']}")
    if row.get("case_type") == "api":
        background_tasks.add_task(
            ingest_service.ingest_test_case_in_new_session, current.project_id or 0, row["id"]
        )
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


# ── API 执行 ──────────────────────────────────────────

@router.post("/{case_id}/execute", response_model=R[dict], summary="执行 API 用例")
def execute_test_case(
    case_id: int,
    body: ApiExecutionRequest | None = None,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """对已保存的 API 类型用例发起真实 HTTP 请求，返回响应 + 断言结果。
    P1: 生产环境执行需要额外 apitest:execute_prod 权限。
    """
    env_id = body.environment_id if body else None
    confirm_prod = body.confirm_prod if body else False
    if body and body.case_ids and body.case_ids != [case_id]:
        return R(code=400, msg="请求 case_ids 与路径用例不一致")

    if env_id is not None:
        case = test_case_service.get_case(db, case_id, current.project_id or 0)
        if not case:
            return R(code=404, msg="用例不存在或不属于当前项目")
        method = (case.get("api_method") or "GET").upper()
        try:
            require_allowed_operation(
                db,
                ProductionOperation(
                    action=f"Execute API case #{case_id} ({method})",
                    project_id=current.project_id or 0,
                    environment_id=env_id,
                    permission="apitest:execute_prod" if method in {"POST", "PUT", "PATCH", "DELETE"} else "",
                    confirmed=confirm_prod,
                ),
                set(current.permissions),
            )
        except APIException as exc:
            return R(code=exc.code, msg=exc.msg)

    try:
        result = execute_api_case(
            db, case_id,
            project_id=current.project_id or 0,
            environment_id=env_id,
            dataset_id=body.dataset_id if body else None,
            confirm_prod=confirm_prod,
            has_execute_prod=(
                current.is_super
                or rbac_service.has_permission(current.permissions, "apitest:execute_prod")
            ),
        )
    except ValueError as e:
        return R(code=1, msg=str(e))
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    # Batch 103：执行结果回填到用例（请求结果可视）
    try:
        if test_case_service.save_execution_backfill(
            db, case_id, current.project_id or 0, result
        ):
            db.commit()
    except Exception:
        db.rollback()
        logger.warning("execution result backfill failed for case_id=%d", case_id)

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

    # approve/reject use review:approve permission
    if body.action in ("approve", "reject"):
        # Re-check permission — the Depends above allows submit/withdraw via review:submit
        if not rbac_service.has_permission(current.permissions, "review:approve"):
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


# ── 版本历史 ──

@router.get("/{case_id}/versions", response_model=R[list[dict]], summary="用例版本历史")
def list_versions(
    case_id: int,
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """返回用例的所有版本快照列表。"""
    from app.services.version_service import list_versions

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
