"""需求文档 API 路由 —— /api/v1/requirements/*（文档 CRUD + 覆盖率）

Batch 181（FIX-173-P2-10）拆分自 requirement.py，端点逻辑逐字迁移。
"""
from __future__ import annotations

import html
import logging
import re
from pathlib import Path

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile,
)
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException, not_found
from app.schemas.common import Page, R
from app.schemas.requirement import (
    RequirementDocumentBrief,
    RequirementDocumentOut,
)
from app.services import audit_service, requirement_service
from app.services.file_parser_service import parse_docx, parse_markdown, parse_xlsx
from app.services.knowledge import ingest_service

router = APIRouter(prefix="/requirements", tags=["需求文档"])
logger = logging.getLogger("requirement")

# Max upload size: 20 MB
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
# Safe filename pattern: allow Chinese, alphanumeric, spaces, hyphens, underscores, dots
_SAFE_FILENAME_RE = re.compile(r'[^\w一-鿿\-\.\s]')


def _sanitize_filename(filename: str) -> str:
    """Strip path separators and dangerous chars (XSS/Path-traversal prevention)."""
    # Remove any path components
    name = Path(filename).name
    # Strip chars that aren't word chars, Chinese chars, hyphens, underscores, dots, or spaces
    name = _SAFE_FILENAME_RE.sub('', name)
    return name.strip()[:255] or "untitled"


def _audit(
    req: Request, cu: CurrentUser, db: Session,
    action: str, target: str, detail: str = "",
) -> None:
    """Write audit entry with null-safe user access (P0-5/P1-3 fix)."""
    username = ""
    if cu.user:
        username = cu.user.nickname or cu.user.username
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=username,
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── 列表 ──────────────────────────────────────────────

@router.get("", response_model=R[Page[RequirementDocumentBrief]], summary="需求文档列表")
def list_requirements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="搜索标题/来源"),
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """分页列出项目内的需求文档。P0-1/P1-4: 添加分页 + 列表 schema 不含 content 全量文本。"""
    pid = current.project_id or 0
    total, rows = requirement_service.list_requirements_page(
        db, pid, keyword=keyword, page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[
            RequirementDocumentBrief(
                **requirement_service._doc_to_dict(row, creator_name or "")
            )
            for row, creator_name in rows
        ],
    ))


@router.get("/{document_id}", response_model=R[RequirementDocumentOut], summary="需求文档详情")
def get_requirement_detail(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """Return the full document only when it belongs to the active project."""
    doc = requirement_service.get_requirement(
        db, document_id, project_id=current.project_id or 0
    )
    if doc is None:
        raise not_found("需求文档")
    return R.ok(RequirementDocumentOut(**doc))


# ── 上传 ──────────────────────────────────────────────

@router.post("/upload", response_model=R[RequirementDocumentOut])
async def upload_requirement(
    req: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    lanhu_url: str = Form(""),
    lanhu_description: str = Form(""),
    source_url: str = Form(""),
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """Upload a requirement file (.md / .docx / .xlsx) or submit a lanhu URL."""
    content = ""
    title = ""
    source_ref = ""
    file_type = ""
    parsed_type = "requirement"
    excel_cases: list[dict] | None = None

    if file is not None and file.filename:
        # Multipart headers make Content-Length larger than the file itself, so
        # enforce the limit against the actual payload and read at most one byte
        # beyond the configured maximum.
        file_bytes = await file.read(_MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > _MAX_UPLOAD_BYTES:
            raise APIException(
                code=413,
                msg="上传文件超过限制（最大 20 MB）",
                http_status=413,
            )
        if not file_bytes:
            raise APIException(code=400, msg="上传文件不能为空", http_status=400)
        # P1-S6c: XSS 防御 — 净化文件名
        filename = _sanitize_filename(file.filename)
        source_ref = filename
        # HTML-escape title for safe rendering
        title = html.escape(Path(filename).stem) or "untitled"
        ext = Path(filename).suffix.lower()

        try:
            if ext == ".md":
                file_type = "md"
                content = parse_markdown(file_bytes)
            elif ext == ".docx":
                file_type = "docx"
                content = parse_docx(file_bytes)
            elif ext in (".xlsx", ".xls"):
                file_type = "xlsx"
                result = parse_xlsx(file_bytes)
                content = result["content"]
                parsed_type = result["type"]
                excel_cases = result.get("cases")
            else:
                raise APIException(
                    code=400,
                    msg=f"不支持的文件格式: {ext}，支持 .md / .docx / .xlsx",
                    http_status=400,
                )
        except APIException:
            raise
        except Exception as exc:
            logger.info("requirement file parse rejected: %s", exc)
            raise APIException(
                code=400,
                msg=f"{ext or '文件'} 内容损坏或无法解析",
                http_status=400,
            ) from exc

    elif lanhu_url.strip():
        raise APIException(
            code=409,
            msg="蓝湖链接必须先通过证据包质量门禁，再导入需求/RAG/Wiki",
            http_status=409,
        )
    elif source_url.strip():
        from app.services.requirement_source_service import (
            RequirementSourceError,
            fetch_url_content,
        )
        try:
            fetched = fetch_url_content(source_url.strip())
        except RequirementSourceError as exc:
            return R(code=400, msg=str(exc))
        content = fetched.get("content", "")
        if not content:
            return R(code=400, msg="需求地址未提取到有效内容")
        title = html.escape((fetched.get("title") or "在线需求")[:200])
        file_type = fetched.get("kind", "generic")
        source_ref = source_url.strip()
        parsed_type = "requirement"
    else:
        return R(code=400, msg="请上传文件、输入需求 URL 或蓝湖链接")

    try:
        doc = requirement_service.create_requirement(
            db,
            project_id=current.project_id or 0,
            creator_id=current.user.id,
            title=title,
            file_type=file_type,
            source_ref=source_ref,
            source_url=source_url,
            content=content,
            parsed_type=parsed_type,
            excel_cases=excel_cases,
            commit=False,
        )
        _audit(req, current, db, "requirement:upload", f"#{doc['id']} {title}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    # 知识入库（自带 Session，post-commit，失败不影响主流程）
    background_tasks.add_task(
        ingest_service.ingest_requirement_in_new_session, current.project_id or 0, doc["id"]
    )
    # Wiki Raw Source 入库（仅蓝湖来源 + wiki_enabled；自带 Session，失败不影响主流程）
    if file_type == "lanhu" and source_ref:
        from app.services.wiki import import_service as wiki_import_service
        background_tasks.add_task(
            wiki_import_service.ingest_lanhu_raw_source_in_new_session,
            current.project_id or 0, source_ref,
            business_ref_type="requirement_document", business_ref_id=doc["id"],
            description=lanhu_description.strip() if lanhu_url.strip() else "",
        )
    return R.ok(RequirementDocumentOut(**doc))


# ── 删除需求文档 ──────────────────────────────────────────

@router.delete("/{document_id}", response_model=R[dict])
def delete_requirement(
    document_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """Delete a requirement document."""
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc:
        return R(code=404, msg="需求文档不存在")
    try:
        ok = requirement_service.delete_requirement(
            db,
            document_id,
            project_id=current.project_id or 0,
            commit=False,
        )
        if not ok:
            raise not_found("需求文档")
        _audit(
            req,
            current,
            db,
            "requirement:delete",
            f"#{document_id} {doc.get('title', '')}",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return R.ok({"id": document_id})


# ── 需求覆盖率 ──────────────────────────────────────────

@router.get("/{document_id}/coverage", response_model=R[dict], summary="需求覆盖率")
def get_requirement_coverage(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """返回单个需求文档的用例覆盖情况：已生成用例数、纳入计划数、执行/通过数、缺陷关联数。"""
    from app.services.trace_service import get_requirement_coverage as _cov

    result = _cov(db, document_id, current.project_id or 0)
    if result is None:
        from app.core.exceptions import not_found
        raise not_found("需求文档")
    return R.ok(result)
