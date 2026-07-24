"""需求文档 API 路由 — /api/v1/requirements/*"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.schemas.common import R
from app.schemas.requirement import (
    AIGenerateResult,
    AIGeneratedCase,
    CaseImportRequest,
    CaseImportResult,
    ExtractionConfirmRequest,
    ExtractedRequirement,
    FeatureExtractionResult,
    GenerateRequest,
    Issue,
    RequirementAnalysis,
    RequirementDocumentOut,
    VersionInfo,
)
from app.services import audit_service, requirement_service
from app.services.file_parser_service import parse_docx, parse_markdown, parse_xlsx
from app.services.knowledge import ingest_service

router = APIRouter(prefix="/requirements", tags=["需求文档"])
logger = logging.getLogger("requirement")


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


# ── 列表 ──────────────────────────────────────────────

@router.get("", response_model=R[list[RequirementDocumentOut]])
def list_requirements(
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    docs = requirement_service.list_requirements(db, project_id=current.project_id or 0)
    return R.ok([RequirementDocumentOut(**d) for d in docs])


# ── 上传 ──────────────────────────────────────────────

@router.post("/upload", response_model=R[RequirementDocumentOut])
async def upload_requirement(
    req: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    lanhu_url: str = Form(""),
    lanhu_description: str = Form(""),
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
        # P1-S6a: Content-Length 前置检查，避免读取超大文件 (max 20 MB)
        content_length = req.headers.get("content-length")
        if content_length:
            cl = int(content_length)
            max_bytes = 20 * 1024 * 1024
            if cl > max_bytes:
                from app.core.exceptions import APIException
                raise APIException(
                    f"上传文件超过限制 (max: 20 MB, got: {cl / (1024*1024):.1f} MB)",
                    code=413,
                )
        file_bytes = await file.read()
        filename = file.filename
        source_ref = filename
        title = Path(filename).stem
        ext = Path(filename).suffix.lower()

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
            return R(code=400, msg=f"不支持的文件格式: {ext}，支持 .md / .docx / .xlsx")

    elif lanhu_url.strip():
        from app.core.exceptions import APIException

        raise APIException(
            code=409,
            msg="蓝湖链接必须先通过证据包质量门禁，再导入需求/RAG/Wiki",
            http_status=409,
        )
    else:
        return R(code=400, msg="请上传文件或输入蓝湖链接")

    doc = requirement_service.create_requirement(
        db,
        project_id=current.project_id or 0,
        creator_id=current.user.id,
        title=title,
        file_type=file_type,
        source_ref=source_ref,
        content=content,
        parsed_type=parsed_type,
        excel_cases=excel_cases,
    )
    _audit(req, current, db, "requirement:upload", f"#{doc['id']} {title}")
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
        except Exception:
            doc_content = doc.get("content") or ""
    else:
        doc_content = doc.get("content") or ""

    try:
        from app.services.ai_service import extract_features as ai_extract

        extraction_result = await ai_extract(
            content=doc_content,
            file_type=doc["file_type"],
            source_ref=doc["source_ref"],
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

    # Store extraction result
    requirement_service.update_extraction(db, document_id, extraction_result)

    module_count = len(extraction_result.get("modules", []))
    fp_count = sum(
        len(m.get("function_points", []))
        for m in extraction_result.get("modules", [])
    )

    _audit(req, current, db, "requirement:extract", f"doc#{document_id}",
           f"提取 {module_count} 模块 + {fp_count} 功能点")

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
    result = requirement_service.get_extraction(db, document_id, current.project_id or 0)
    if not result:
        # Return code=0 with null data so the frontend doesn't show an error toast.
        # The frontend treats null as "no extraction yet" and falls through to extractFeatures().
        return R.ok(None)
    return R.ok(FeatureExtractionResult(**result))


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

    # Build the data to save
    confirmed_data = {
        "modules": body.modules,
        "overall_assessment": doc.get("extraction_raw", ""),
        "rejected_modules": body.rejected_modules,
        "rejected_notes": body.rejected_notes,
    }

    result = requirement_service.confirm_extraction(db, document_id, confirmed_data, body.action)
    if not result:
        return R(code=500, msg="操作失败")

    audit_detail = "确认功能拆分" if body.action == "confirm" else f"拒绝功能拆分: {body.rejected_notes[:100]}"
    _audit(req, current, db, "requirement:extract:confirm", f"doc#{document_id}", audit_detail)
    return R.ok(result)


# ── AI 生成 ───────────────────────────────────────────

@router.post("/{document_id}/generate", response_model=R[AIGenerateResult])
async def generate_test_cases(
    document_id: int,
    req: Request,
    body: GenerateRequest | None = Body(None),
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    """Call AI to generate test cases from the uploaded requirement document.

    If use_extraction is True and the document has a confirmed extraction,
    the confirmed modules and function points are passed as context to guide
    test case generation (Stage 2 of the two-stage pipeline).
    """
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc:
        return R(code=404, msg="需求文档不存在")

    # Determine extraction context
    extraction = None
    inherited_cases: list[dict] = []
    use_extraction = body.use_extraction if body else False
    if use_extraction and doc.get("extraction_status") == "confirmed":
        try:
            extraction = json.loads(doc.get("extraction_raw", "{}"))
        except json.JSONDecodeError:
            pass

        # ── Inherited function points (batch-26): separate from new FPs to avoid re-generating ──
        if extraction:
            inherited_fps = []
            new_modules = []
            for m in extraction.get("modules", []):
                inherited_in_module = []
                new_fps = []
                for fp in m.get("function_points", []):
                    if fp.get("_inherited"):
                        inherited_in_module.append(fp)
                    else:
                        new_fps.append(fp)
                if inherited_in_module:
                    inherited_fps.extend(inherited_in_module)
                # Only keep modules with new FPs for AI generation
                if new_fps:
                    new_modules.append({**m, "function_points": new_fps})
                elif not inherited_in_module:
                    new_modules.append(m)  # keep module if no FPs at all

            if inherited_fps:
                # Load parent's test cases for inherited FPs
                parent_id = doc.get("parent_id")
                if parent_id:
                    parent_doc = requirement_service.get_requirement(db, parent_id, project_id=current.project_id or 0)
                    if parent_doc and parent_doc.get("ai_raw"):
                        try:
                            parent_ai = json.loads(parent_doc["ai_raw"])
                            # Match inherited FPs to parent's functional cases by FP title/name
                            parent_cases = parent_ai.get("functional_cases", [])
                            inherited_fp_names = {
                                fp.get("name", "").strip()
                                for fp in inherited_fps
                            }
                            for pc in parent_cases:
                                pc_title = pc.get("title", "").strip()
                                # Simple heuristic: check if case title contains FP name
                                for fp_name in inherited_fp_names:
                                    if fp_name and (fp_name in pc_title or pc_title in fp_name):
                                        pc_copy = dict(pc)
                                        pc_copy["_inherited"] = True
                                        pc_copy["_from_version"] = doc.get("version", "")
                                        inherited_cases.append(pc_copy)
                                        break
                        except json.JSONDecodeError:
                            pass

                        # ── Log case inherit match rate for monitoring (batch-28) ──
                        if inherited_fps:
                            logger.info(
                                "case_inherit_match_rate: %d/%d (%.1f%%) [doc_id=%d, version=%s]",
                                len(inherited_cases), len(inherited_fps),
                                len(inherited_cases) / len(inherited_fps) * 100 if inherited_fps else 0,
                                document_id, doc.get("version", ""),
                            )

                # Replace extraction with only new FPs for AI
                extraction = {**extraction, "modules": new_modules} if new_modules else None

    try:
        from app.services.ai_service import generate_test_cases as ai_generate

        ai_result = await ai_generate(
            content=doc["content"],
            file_type=doc["file_type"],
            source_ref=doc["source_ref"],
            extraction=extraction,
        )
    except ValueError as e:
        return R(code=400, msg=str(e))
    except Exception as e:
        return R(code=500, msg=f"AI 生成失败: {str(e)}")

    # Store raw response
    requirement_service.update_ai_result(db, document_id, ai_result)

    # Build structured result with indices (functional cases only)
    func_cases: list[AIGeneratedCase] = []
    idx = 0
    for c in ai_result.get("functional_cases", []):
        c["index"] = idx
        c["case_type"] = "manual"
        if isinstance(c.get("steps"), (list, dict)):
            c["steps"] = json.dumps(c["steps"], ensure_ascii=False)
        func_cases.append(AIGeneratedCase(**c))
        idx += 1

    # ── Append inherited cases (batch-26): carry forward from previous version ──
    for ic in inherited_cases:
        ic["index"] = idx
        ic["case_type"] = "manual"
        if isinstance(ic.get("steps"), (list, dict)):
            ic["steps"] = json.dumps(ic["steps"], ensure_ascii=False) if isinstance(ic["steps"], (list, dict)) else ic.get("steps", "")
        # Mark as inherited in the title for visibility
        if ic.get("_inherited") and not ic.get("title", "").startswith("[沿用"):
            ic["title"] = f"[沿用自{ic.get('_from_version', '上版本')}] {ic.get('title', '')}"
        func_cases.append(AIGeneratedCase(**ic))
        idx += 1

    # Parse API cases from AI result (for integration-type requirements)
    api_cases: list[AIGeneratedCase] = []
    for c in ai_result.get("api_cases", []):
        c["index"] = len(func_cases) + len(api_cases)
        c["case_type"] = "api"
        if isinstance(c.get("steps"), (list, dict)):
            c["steps"] = json.dumps(c["steps"], ensure_ascii=False)
        api_cases.append(AIGeneratedCase(**c))

    # Build requirement_analysis from AI result
    analysis_data = ai_result.get("requirement_analysis", {})
    if not isinstance(analysis_data, dict):
        analysis_data = {}
    extracted_reqs = []
    for er in analysis_data.get("extracted_requirements", []):
        if isinstance(er, dict):
            issues = [Issue(**iss) for iss in (er.get("issues") or []) if isinstance(iss, dict)]
            extracted_reqs.append(ExtractedRequirement(
                id=er.get("id", ""),
                title=er.get("title", ""),
                description=er.get("description", ""),
                type=er.get("type", "functional"),
                issues=issues,
            ))
    req_analysis = RequirementAnalysis(
        extracted_requirements=extracted_reqs,
        overall_assessment=analysis_data.get("overall_assessment", ""),
    )

    mode_label = "基于拆分" if extraction else "直接"
    _audit(req, current, db, "requirement:generate", f"doc#{document_id}",
           f"{mode_label}: 分析 {len(extracted_reqs)} 需求点 + 生成 {len(func_cases)} 功能用例 + {len(api_cases)} 接口用例")
    return R.ok(AIGenerateResult(
        document_id=document_id,
        requirement_analysis=req_analysis,
        functional_cases=func_cases,
        api_cases=api_cases,
        raw_response=json.dumps(ai_result, ensure_ascii=False),
        extraction_summary=ai_result.get("extraction_summary", ""),
    ))


# ── B1: 需求-API 匹配 ──────────────────────────────────

class MatchApiRequest(BaseModel):
    integration_reqs: list[dict] = []
    service_id: int | None = None
    use_embedding: bool = False  # feature flag: 启用 LLM embedding 语义匹配

class ApiMatchItem(BaseModel):
    req_id: str = ""
    title: str = ""
    endpoint_id: int = 0
    method: str = ""
    path: str = ""
    summary: str = ""
    confidence: float = 0.0
    match_method: str = ""  # "keyword" | "embedding"

@router.post("/{document_id}/match-api", response_model=R[list[ApiMatchItem]])
def match_api_endpoints_for_requirement(
    document_id: int,
    body: MatchApiRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为需求文档中 integration 类型的功能点匹配已导入的 API 接口。

    支持两种匹配策略：
    - 关键词匹配（默认）: use_embedding=False
    - LLM embedding 语义相似度: use_embedding=True（需本地 fastembed 模型就绪）
    """
    if not body.integration_reqs:
        return R.ok([])
    matches = requirement_service.match_api_endpoints(
        db,
        integration_reqs=body.integration_reqs,
        project_id=current.project_id or 0,
        service_id=body.service_id,
        use_embedding=body.use_embedding,
    )
    return R.ok([ApiMatchItem(**m) for m in matches])


# ── 导入用例 ──────────────────────────────────────────

@router.post("/{document_id}/import", response_model=R[CaseImportResult])
def import_generated_cases(
    document_id: int,
    body: CaseImportRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("requirement:import")),
    db: Session = Depends(get_db),
):
    """Import selected AI-generated cases into the test_case table."""
    doc = requirement_service.get_requirement(db, document_id, project_id=current.project_id or 0)
    if not doc or not doc.get("ai_raw"):
        return R(code=400, msg="请先生成测试用例再导入")

    try:
        all_data = json.loads(doc["ai_raw"])
    except json.JSONDecodeError:
        return R(code=500, msg="AI 响应格式异常，无法解析")

    # Collect selected cases by position-based index (functional + API cases)
    selected: list[dict] = []
    idx = 0
    for c in all_data.get("functional_cases", []):
        if idx in body.indices:
            c["case_type"] = "manual"
            selected.append(c)
        idx += 1
    for c in all_data.get("api_cases", []):
        if idx in body.indices:
            c["case_type"] = "api"
            selected.append(c)
        idx += 1

    if not selected:
        return R(code=400, msg="未找到匹配的用例")

    result = requirement_service.import_cases(
        db, document_id, selected, project_id=current.project_id or 0,
    )
    _audit(req, current, db, "requirement:import", f"doc#{document_id}",
           f"导入 {result['imported']} 条用例")

    return R.ok(CaseImportResult(**result))


# ── 查看已生成用例 ──────────────────────────────────────

@router.get("/{document_id}/cases", response_model=R[AIGenerateResult])
def get_generated_cases(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """View previously generated test cases for a document."""
    result = requirement_service.get_requirement_cases(
        db, document_id, project_id=current.project_id or 0,
    )
    if not result:
        return R(code=404, msg="该文档尚未生成用例，请先点击 AI 生成")
    return R.ok(AIGenerateResult(**result))


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
    ok = requirement_service.delete_requirement(db, document_id, project_id=current.project_id or 0)
    if not ok:
        return R(code=404, msg="删除失败")
    _audit(req, current, db, "requirement:delete", f"#{document_id} {doc.get('title', '')}")
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
