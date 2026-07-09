"""需求文档 API 路由 — /api/v1/requirements/*"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
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
        file_type = "lanhu"
        source_ref = lanhu_url.strip()
        desc = lanhu_description.strip()
        url_short = lanhu_url.strip()[:60]
        title = f"蓝湖设计稿 {url_short}"
        # Build content: description (if provided) + URL; prefer description for AI
        if desc:
            content = f"设计描述: {desc}\n\n蓝湖链接: {lanhu_url.strip()}"
        else:
            content = lanhu_url.strip()
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

    try:
        from app.services.ai_service import extract_features as ai_extract

        extraction_result = await ai_extract(
            content=doc["content"],
            file_type=doc["file_type"],
            source_ref=doc["source_ref"],
        )
    except ValueError as e:
        return R(code=400, msg=str(e))
    except Exception as e:
        return R(code=500, msg=f"功能拆分失败: {str(e)}")

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
    use_extraction = body.use_extraction if body else False
    if use_extraction and doc.get("extraction_status") == "confirmed":
        try:
            extraction = json.loads(doc.get("extraction_raw", "{}"))
        except json.JSONDecodeError:
            pass

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

    # api_cases always empty — API testing is handled separately
    api_cases: list[AIGeneratedCase] = []

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
           f"{mode_label}: 分析 {len(extracted_reqs)} 需求点 + 生成 {len(func_cases)} 功能用例")
    return R.ok(AIGenerateResult(
        document_id=document_id,
        requirement_analysis=req_analysis,
        functional_cases=func_cases,
        api_cases=api_cases,
        raw_response=json.dumps(ai_result, ensure_ascii=False),
        extraction_summary=ai_result.get("extraction_summary", ""),
    ))


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

    # Collect selected cases by position-based index (functional cases only)
    selected: list[dict] = []
    idx = 0
    for c in all_data.get("functional_cases", []):
        if idx in body.indices:
            c["case_type"] = "manual"
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
