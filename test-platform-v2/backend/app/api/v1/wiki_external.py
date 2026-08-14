"""LLM-Wiki 外部连接 / 健康体检 API 路由（外部连接域） —— /api/v1/wiki/*

Batch 181（FIX-173-P2-10）路由拆分：外部 LLM-Wiki 连接 CRUD + 检索/图谱 + Lint
+ Wiki 同步前置条件只读检查。
端点函数体与原 wiki.py 逐字一致；ExternalWikiConnection ORM 查询收敛到
app.services.wiki.external_connection_service。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.cipher import encrypt_value
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import Page, R
from app.schemas.release_bundle import WikiSyncAvailabilityOut
from app.schemas.wiki import (
    ExternalWikiConnectionCreate,
    ExternalWikiConnectionOut,
    ExternalWikiConnectionUpdate,
    ExternalWikiGraphResult,
    ExternalWikiHealthResult,
    ExternalWikiPageResult,
    ExternalWikiSearchRequest,
    ExternalWikiSearchResult,
    WikiLintConvertRequest,
    WikiLintIssueOut,
    WikiLintReportBrief,
    WikiLintReportOut,
    WikiLintRunRequest,
)
from app.services import audit_service
from app.services.wiki import lint_service
from app.services.wiki.external_connection_service import (
    create_external_connection as _create_external_connection,
    get_external_connection as _get_external_connection,
    list_external_connections as _list_external_connections,
)
from app.services.wiki.external_llm_wiki import (
    graph as ext_graph,
    health_check as ext_health_check,
    read_page as ext_read_page,
    search as ext_search,
)
from app.services.wiki.sync_service import get_sync_availability

router = APIRouter(prefix="/wiki", tags=["Wiki 外部连接"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _require_external_llm_wiki_enabled() -> None:
    if not settings.external_llm_wiki_enabled:
        raise APIException(code=503, msg="外部 LLM-Wiki 连接器未启用（external_llm_wiki_enabled=False）", http_status=503)


def _require_wiki_lint_enabled() -> None:
    if not settings.wiki_lint_enabled:
        raise APIException(code=503, msg="Wiki 健康体检未启用（wiki_lint_enabled=False）", http_status=503)


# ═══════════════════════════════════════════════════════
# 外部 LLM-Wiki 连接器（VNext-5）
# ═══════════════════════════════════════════════════════

@router.post("/external-connections", response_model=R[ExternalWikiConnectionOut],
             summary="创建外部 Wiki 连接")
def create_external_connection(
    body: ExternalWikiConnectionCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    pid = current.project_id or 0
    token_encrypted = None
    if body.token:
        token_encrypted = encrypt_value(body.token)
    conn = _create_external_connection(
        db,
        project_id=pid,
        name=body.name,
        provider=body.provider,
        base_url=body.base_url.rstrip("/"),
        token_encrypted=token_encrypted,
        external_project_id=body.external_project_id,
        enabled=body.enabled,
    )
    _audit(req, current, db, action="wiki.external.create", target=body.name,
           detail=f"conn#{conn.id} provider={body.provider}")
    db.commit()
    return R.ok(ExternalWikiConnectionOut.model_validate(conn))


@router.get("/external-connections", response_model=R[list[ExternalWikiConnectionOut]],
            summary="外部 Wiki 连接列表")
def list_external_connections(
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    pid = current.project_id or 0
    rows = _list_external_connections(db, pid)
    return R.ok([ExternalWikiConnectionOut.model_validate(r) for r in rows])


@router.get("/external-connections/{conn_id}", response_model=R[ExternalWikiConnectionOut],
            summary="外部 Wiki 连接详情")
def get_external_connection(
    conn_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    return R.ok(ExternalWikiConnectionOut.model_validate(conn))


@router.put("/external-connections/{conn_id}", response_model=R[ExternalWikiConnectionOut],
            summary="更新外部 Wiki 连接")
def update_external_connection(
    conn_id: int,
    body: ExternalWikiConnectionUpdate,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")

    if body.name is not None:
        conn.name = body.name
    if body.provider is not None:
        conn.provider = body.provider
    if body.base_url is not None:
        conn.base_url = body.base_url.rstrip("/")
    if body.token is not None and body.token != "":
        conn.token_encrypted = encrypt_value(body.token)
    if body.external_project_id is not None:
        conn.external_project_id = body.external_project_id
    if body.enabled is not None:
        conn.enabled = body.enabled

    _audit(req, current, db, action="wiki.external.update", target=f"conn#{conn_id}",
           detail=f"name={conn.name}")
    db.commit()
    return R.ok(ExternalWikiConnectionOut.model_validate(conn))


@router.delete("/external-connections/{conn_id}", response_model=R[None],
               summary="删除外部 Wiki 连接")
def delete_external_connection(
    conn_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    _audit(req, current, db, action="wiki.external.delete", target=f"conn#{conn_id}",
           detail=f"name={conn.name}")
    db.delete(conn)
    db.commit()
    return R.ok(msg="已删除")


@router.post("/external-connections/{conn_id}/health-check",
             response_model=R[ExternalWikiHealthResult], summary="测试外部 Wiki 连接")
def check_external_connection_health(
    conn_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    result = ext_health_check(conn)
    _audit(req, current, db, action="wiki.external.health_check", target=f"conn#{conn_id}",
           detail=f"ok={result.get('ok')} provider={conn.provider}")
    return R.ok(ExternalWikiHealthResult(
        ok=result["ok"],
        version=result.get("version", ""),
        message=result.get("message", ""),
    ))


@router.post("/external-connections/{conn_id}/search",
             response_model=R[ExternalWikiSearchResult], summary="搜索外部 Wiki")
def search_external_wiki(
    conn_id: int,
    body: ExternalWikiSearchRequest,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    items = ext_search(conn, body.query, body.limit)
    return R.ok(ExternalWikiSearchResult(items=items, total=len(items)))


@router.get("/external-connections/{conn_id}/files/content",
            response_model=R[ExternalWikiPageResult], summary="读取外部 Wiki 页面")
def read_external_page(
    conn_id: int,
    path: str = Query(..., min_length=1, max_length=500),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    result = ext_read_page(conn, path)
    return R.ok(ExternalWikiPageResult(
        ok=result["ok"],
        title=result.get("title", ""),
        content_md=result.get("content_md", ""),
        meta=result.get("meta", {}),
        error=result.get("error", ""),
    ))


@router.get("/external-connections/{conn_id}/graph",
            response_model=R[ExternalWikiGraphResult], summary="获取外部 Wiki 图谱")
def get_external_graph(
    conn_id: int,
    node: str = Query(..., min_length=1, max_length=500),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    _require_external_llm_wiki_enabled()
    conn = _get_external_connection(db, conn_id, current.project_id or 0)
    if not conn:
        return R(code=404, msg="连接不存在")
    result = ext_graph(conn, node)
    return R.ok(ExternalWikiGraphResult(
        ok=result["ok"],
        node=result.get("node", node),
        edges=result.get("edges", []),
        nodes=result.get("nodes", []),
        error=result.get("error", ""),
    ))


# ═══════════════════════════════════════════════════════
# Wiki 健康体检 / Lint（VNext-6）
# ═══════════════════════════════════════════════════════

@router.post("/lint", response_model=R[WikiLintReportOut], summary="运行 Wiki 健康体检")
def run_wiki_lint(
    body: WikiLintRunRequest = WikiLintRunRequest(),
    req: Request = None,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    _require_wiki_lint_enabled()
    if (
        body.project_id_override
        and body.project_id_override != (current.project_id or 0)
        and not current.is_super
    ):
        raise APIException(
            code=403,
            msg="Only a super administrator may override project scope",
            http_status=403,
        )
    pid = body.project_id_override if body.project_id_override else (current.project_id or 0)
    if not pid:
        raise APIException(code=400, msg="缺少项目上下文")
    report = lint_service.run_lint(db, project_id=pid,
                                   operator_id=current.user.id if current.user else 0)
    issues = lint_service.get_issues(db, report.id)
    _audit(req, current, db, action="wiki.lint.run", target=f"project#{pid}",
           detail=f"report#{report.id} status={report.status}")
    db.commit()
    out = WikiLintReportOut.model_validate(report)
    out.issues = [WikiLintIssueOut.model_validate(i) for i in issues]
    return R.ok(out)


@router.get("/lint/reports", response_model=R[Page[WikiLintReportBrief]], summary="Lint 报告列表")
def list_lint_reports(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    rows, total = lint_service.list_reports(db, pid, status=status, page=page, page_size=page_size)
    return R.ok(Page(total=total, page=page, page_size=page_size,
                     items=[WikiLintReportBrief.model_validate(r) for r in rows]))


@router.get("/lint/reports/{report_id}", response_model=R[WikiLintReportOut], summary="Lint 报告详情（含问题列表）")
def get_lint_report(
    report_id: int,
    rule: str | None = Query(None),
    severity: str | None = Query(None),
    review_status: str | None = Query(None),
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    pid = current.project_id or 0
    report = lint_service.get_report(db, report_id, pid)
    if not report:
        return R(code=404, msg="报告不存在")
    issues = lint_service.get_issues(db, report_id, rule=rule, severity=severity, review_status=review_status)
    out = WikiLintReportOut.model_validate(report)
    out.issues = [WikiLintIssueOut.model_validate(i) for i in issues]
    return R.ok(out)


@router.post("/lint/reports/{report_id}/convert", response_model=R[dict], summary="Lint 问题转待审 AI 产物")
def convert_lint_issues(
    report_id: int,
    body: WikiLintConvertRequest = WikiLintConvertRequest(),
    req: Request = None,
    current: CurrentUser = Depends(require_permission("wiki:approve")),
    db: Session = Depends(get_db),
):
    _require_wiki_lint_enabled()
    pid = current.project_id or 0
    report = lint_service.get_report(db, report_id, pid)
    if not report:
        return R(code=404, msg="报告不存在")
    artifacts = lint_service.convert_issues_to_artifacts(
        db, report,
        issue_ids=body.issue_ids if body.issue_ids else None,
        artifact_type=body.artifact_type,
        operator_id=current.user.id if current.user else 0,
    )
    _audit(req, current, db, action="wiki.lint.convert", target=f"report#{report_id}",
           detail=f"converted {len(artifacts)} issues")
    db.commit()
    return R.ok({"converted": len(artifacts), "artifact_ids": [a.id for a in artifacts]})


# ═══════════════════════════════════════════════════════
# M3 蓝湖模块树 → Wiki 基线同步（Batch 27 Knowledge Sphere）
# ═══════════════════════════════════════════════════════

@router.get(
    "/sync/availability",
    response_model=R[WikiSyncAvailabilityOut],
    summary="Wiki 同步前置条件",
)
def get_wiki_sync_availability(
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    """只读检查当前项目是否存在可用于 Wiki 同步的启用发布包。"""
    availability = get_sync_availability(
        db,
        project_id=current.project_id or 0,
        wiki_enabled=settings.wiki_enabled,
    )
    return R.ok(WikiSyncAvailabilityOut(
        available=availability.available,
        reason=availability.reason,
        release_bundle_id=availability.release_bundle_id,
        release_bundle_name=availability.release_bundle_name,
        release_bundle_status=availability.release_bundle_status,
    ))
