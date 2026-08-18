"""需求文档 AI 路由 —— /api/v1/requirements/*（Stage-1 功能拆分 + 异步 AI 任务）

Batch 181（FIX-173-P2-10）拆分自 requirement.py，端点逻辑逐字迁移。
（AI 生成/API 匹配在 requirement_ai_generate.py，评审/导入在 requirement_import.py）
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import not_found
from app.schemas.common import R
from app.schemas.requirement import (
    ExtractionConfirmRequest,
    ExtractionQualityOut,
    FeatureExtractionResult,
    VersionInfo,
)
from app.services import audit_service, requirement_service

router = APIRouter(prefix="/requirements", tags=["需求文档-AI"])
logger = logging.getLogger("requirement")


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


# ── Stage 1: 功能拆分 (Feature Extraction) ────────────

@router.post("/{document_id}/extract", response_model=R[FeatureExtractionResult])
async def extract_features(
    document_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    """Stage 1: Extract test modules and function points from the requirement document.

    This is the first stage of the two-stage pipeline. It only extracts
    and decomposes requirements — no test case generation happens here.
    The result is saved and presented for human review.
    """
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc:
        return R(code=404, msg="需求文档不存在")

    # ── Version diff context (batch-26): if this is an update, only analyze changed pages ──
    diff_summary = None
    inherited_from_version = ""
    inherited_fp_count = 0
    inherited_fps: list[dict] = []

    diff_json_str = doc.get("diff_json", "")
    if doc.get("diff_status") == "update" and diff_json_str:
        try:
            diff_data = json.loads(diff_json_str) if isinstance(diff_json_str, str) else diff_json_str
            diff_summary = diff_data.get("summary", {})
            inherited_from_version = diff_data.get("base_version", "")

            # Load parent's confirmed extraction for inheritance
            parent_id = doc.get("parent_id")
            if parent_id:
                parent_doc = requirement_service.get_requirement(db, parent_id, project_id=current.project_id or 0)
                if parent_doc and parent_doc.get("extraction_status") == "confirmed" and parent_doc.get("extraction_raw"):
                    try:
                        parent_extraction = json.loads(parent_doc["extraction_raw"])
                    except json.JSONDecodeError:
                        parent_extraction = {}

                    # Map unchanged page names to parent's function points
                    unchanged_pages = {
                        p.get("page_name", "").strip()
                        for p in diff_data.get("pages", [])
                        if p.get("change_type") == "unchanged"
                    }

                    if unchanged_pages:
                        # Inherit FPs from modules that were associated with unchanged pages
                        for parent_module in parent_extraction.get("modules", []):
                            for fp in parent_module.get("function_points", []):
                                source_page = fp.get("source_page", fp.get("page_name", ""))
                                if source_page in unchanged_pages:
                                    fp_copy = dict(fp)
                                    fp_copy["_inherited"] = True
                                    fp_copy["_from_version"] = inherited_from_version
                                    inherited_fps.append(fp_copy)
                        inherited_fp_count = len(inherited_fps)

                        # ── Log inherit match rate for monitoring (batch-28) ──
                        total_parent_fps = sum(
                            len(m.get("function_points", []))
                            for m in parent_extraction.get("modules", [])
                        )
                        if total_parent_fps > 0:
                            logger.info(
                                "fp_inherit_match_rate: %d/%d (%.1f%%) [doc_id=%d, base_version=%s]",
                                inherited_fp_count, total_parent_fps,
                                inherited_fp_count / total_parent_fps * 100,
                                document_id, inherited_from_version,
                            )

                        # Build filtered content: only include text from changed (new/modified) pages
                        changed_pages_info = []
                        for p in diff_data.get("pages", []):
                            if p.get("change_type") in ("new", "modified"):
                                changed_pages_info.append(
                                    f"页面: {p.get('page_name', '')}\n"
                                    f"变更类型: {p.get('change_type', '')}\n"
                                    + (f"变动描述: {p.get('ocr_diff', '')}" if p.get("ocr_diff") else "")
                                )
                        if changed_pages_info:
                            # Prepend diff context to the document content for AI
                            diff_context = (
                                f"## 版本变更摘要 ({diff_data.get('base_version', '?')} → {diff_data.get('current_version', '?')})\n"
                                f"新增 {diff_summary.get('new_pages', 0)} 页, "
                                f"修改 {diff_summary.get('modified_pages', 0)} 页, "
                                f"不变 {diff_summary.get('unchanged_pages', 0)} 页, "
                                f"删除 {diff_summary.get('deleted_pages', 0)} 页\n\n"
                                f"### 仅需分析以下变更页面:\n"
                                + "\n---\n".join(changed_pages_info)
                                + "\n\n### 以下页面无变更(将继承上版本{v}的功能点):\n".format(v=inherited_from_version)
                                + ", ".join(sorted(unchanged_pages))
                                + "\n\n---\n\n"
                            )
                            doc_content = diff_context + (doc.get("content") or "")
                        else:
                            doc_content = doc.get("content") or ""
                    else:
                        doc_content = doc.get("content") or ""
                else:
                    doc_content = doc.get("content") or ""
            else:
                doc_content = doc.get("content") or ""
        except Exception as e:
            logger.warning("Failed to parse diff_json for doc_id=%d: %s", document_id, e)
            doc_content = doc.get("content") or ""
    else:
        doc_content = doc.get("content") or ""

    try:
        from app.services.ai_service import extract_features as ai_extract

        extraction_result = await ai_extract(
            db,
            content=doc_content,
            file_type=doc["file_type"],
            source_ref=doc["source_ref"],
            project_id=current.project_id or 0,
        )
    except ValueError as e:
        return R(code=400, msg=str(e))
    except Exception as e:
        return R(code=500, msg=f"功能拆分失败: {str(e)}")

    # ── Merge inherited function points from parent version ──
    if inherited_fps:
        existing_modules = extraction_result.get("modules", [])
        # Add inherited FPs as a separate module or merge into existing modules
        inherited_module = {
            "name": f"沿用自 {inherited_from_version}",
            "description": "以下功能点在上版本已确认，本版本无变更，直接沿用",
            "function_points": inherited_fps,
            "client_scope": [],
        }
        existing_modules.append(inherited_module)
        extraction_result["modules"] = existing_modules

    module_count = len(extraction_result.get("modules", []))
    fp_count = sum(
        len(m.get("function_points", []))
        for m in extraction_result.get("modules", [])
    )

    # batch-167: 提取完整度元数据（分块/截断/降级显式透出）
    meta = extraction_result.get("extraction_meta") or {}
    extraction_meta = {
        "mode": str(meta.get("mode", "single")),
        "chunks": int(meta.get("chunks", 1)),
        "truncated": bool(meta.get("truncated", False)),
        "fallback": bool(extraction_result.get("fallback_used", False)),
        "module_count": module_count,
        "function_point_count": fp_count,
        "warnings": list(meta.get("warnings") or []),
    }

    try:
        requirement_service.update_extraction(
            db, document_id, extraction_result, commit=False
        )
        _audit(
            req,
            current,
            db,
            "requirement:extract",
            f"doc#{document_id}",
            f"提取 {module_count} 模块 + {fp_count} 功能点",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Build version_info from changelog if available
    changelog = extraction_result.get("changelog", {})
    version_info: list[VersionInfo] = []
    client_scope = extraction_result.get("client_scope", [])
    client_summary = f"涉及 {'/'.join(client_scope)}" if client_scope else ""

    if changelog and isinstance(changelog, dict):
        versions = changelog.get("versions", [])
        for v in versions if isinstance(versions, list) else []:
            version_info.append(VersionInfo(
                version=v.get("version", ""),
                title=v.get("title", ""),
                update_items=v.get("update_items", []),
                clients=v.get("clients", []),
                folder_hint=v.get("folder_hint", ""),
            ))

    return R.ok(FeatureExtractionResult(
        document_id=document_id,
        modules=extraction_result.get("modules", []),
        overall_assessment=extraction_result.get("overall_assessment", ""),
        raw_response=json.dumps(extraction_result, ensure_ascii=False),
        extraction_summary=extraction_result.get("extraction_summary", ""),
        extraction_status="pending_review",
        version_info=version_info,
        client_summary=client_summary,
        diff_summary=diff_summary,
        inherited_from_version=inherited_from_version,
        inherited_fp_count=inherited_fp_count,
    ))


@router.get("/{document_id}/extraction", response_model=R[FeatureExtractionResult])
def get_extraction(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """Get the Stage 1 extraction result (for resuming a review session)."""
    doc = requirement_service.get_requirement(
        db, document_id, project_id=current.project_id or 0
    )
    if doc is None:
        raise not_found("需求文档")
    result = requirement_service.get_extraction(db, document_id, current.project_id or 0)
    if not result:
        raise not_found("功能拆分结果")
    return R.ok(FeatureExtractionResult(**result))


@router.get("/{document_id}/extraction-quality", response_model=R[ExtractionQualityOut], summary="提取完整度与降级状态（Phase 1）")
def get_extraction_quality(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """返回提取模式（single/chunked）、截断、降级与功能点计数。"""
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if doc is None:
        raise not_found("需求文档")
    raw = doc.get("extraction_meta") or "{}"
    try:
        meta = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        meta = {}
    return R.ok(ExtractionQualityOut(
        document_id=document_id,
        mode=str(meta.get("mode", "single")),
        chunks=int(meta.get("chunks", 1)),
        truncated=bool(meta.get("truncated", False)),
        fallback=bool(meta.get("fallback", False)),
        module_count=int(meta.get("module_count", 0)),
        function_point_count=int(meta.get("function_point_count", 0)),
        warnings=list(meta.get("warnings") or []),
        extraction_meta=json.dumps(meta, ensure_ascii=False),
    ))
@router.post("/{document_id}/extraction/confirm", response_model=R[dict])
def confirm_extraction(
    document_id: int,
    body: ExtractionConfirmRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    """Confirm or reject the Stage 1 extraction result.

    - action=confirm: Save confirmed modules, set extraction_status to confirmed.
    - action=reject: Reset extraction_status to not_started for re-extraction.
    """
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc:
        return R(code=404, msg="需求文档不存在")

    if body.action not in ("confirm", "reject"):
        return R(code=400, msg="action 必须是 confirm 或 reject")

    try:
        original = json.loads(doc.get("extraction_raw") or "{}")
    except (json.JSONDecodeError, TypeError):
        original = {}
    if not isinstance(original, dict):
        original = {}
    confirmed_data = {
        **original,
        "modules": body.modules,
        "rejected_modules": body.rejected_modules,
        "rejected_notes": body.rejected_notes,
    }

    audit_detail = "确认功能拆分" if body.action == "confirm" else f"拒绝功能拆分: {body.rejected_notes[:100]}"
    try:
        result = requirement_service.confirm_extraction(
            db,
            document_id,
            confirmed_data,
            body.action,
            commit=False,
        )
        if not result:
            raise not_found("需求文档")
        _audit(
            req,
            current,
            db,
            "requirement:extract:confirm",
            f"doc#{document_id}",
            audit_detail,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return R.ok(result)


# ── 异步 AI 任务（C102-1，大文档不 502） ──────────────

@router.post("/{document_id}/extract-async", response_model=R[dict], summary="异步 AI 提取（C102-1，大文档不 502）")
async def extract_features_async(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    from app.services.ai_tasks import submit_ai_task
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc:
        return R(code=404, msg="需求文档不存在")
    content = doc.get("content") or doc.get("requirement_text") or ""

    task = submit_ai_task(document_id=document_id, task_type="extract", project_id=current.project_id or 0)
    return R.ok(task)


@router.post("/{document_id}/generate-async", response_model=R[dict], summary="异步 AI 生成用例（C102-1，大文档不 502）")
async def generate_test_cases_async(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    from app.services.ai_tasks import submit_ai_task
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc:
        return R(code=404, msg="需求文档不存在")
    content = doc.get("content") or doc.get("requirement_text") or ""

    task = submit_ai_task(document_id=document_id, task_type="generate", project_id=current.project_id or 0)
    return R.ok(task)


@router.get("/ai-task/{task_id}", response_model=R[dict], summary="异步 AI 任务状态（C102-1）")
def get_ai_task_status(
    task_id: str,
    current: CurrentUser = Depends(require_permission("requirement:generate")),
):
    from app.services.ai_tasks import get_ai_task
    task = get_ai_task(task_id)
    if not task:
        raise not_found("AI 任务不存在")
    return R.ok(task)
