"""需求文档 AI 生成路由 —— /api/v1/requirements/*（AI 生成用例 + 需求-API 匹配）

Batch 181（FIX-173-P2-10）拆分自 requirement.py，端点逻辑逐字迁移。
（Stage-1 功能拆分/异步任务在 requirement_ai.py）
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import not_found
from app.schemas.common import R
from app.schemas.requirement import (
    AIGenerateResult,
    AIGeneratedCase,
    GenerateRequest,
    Issue,
    ExtractedRequirement,
    RequirementAnalysis,
)
from app.services import audit_service, requirement_service
from app.services.openapi_import_service import get_project_service

router = APIRouter(prefix="/requirements", tags=["需求文档-AI-生成"])
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
            logger.warning("extraction_raw JSON 解析失败，按空提取处理: doc=%s", doc.get("id"))

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
                            inherited_fp_versions = {
                                (fp.get("name") or fp.get("title") or "").strip():
                                (
                                    fp.get("_from_version")
                                    or parent_doc.get("version")
                                    or "上版本"
                                )
                                for fp in inherited_fps
                                if (fp.get("name") or fp.get("title") or "").strip()
                            }
                            for pc in parent_cases:
                                pc_title = pc.get("title", "").strip()
                                # Simple heuristic: check if case title contains FP name
                                for fp_name, from_version in inherited_fp_versions.items():
                                    if fp_name and (fp_name in pc_title or pc_title in fp_name):
                                        pc_copy = dict(pc)
                                        pc_copy["_inherited"] = True
                                        pc_copy["_from_version"] = from_version
                                        inherited_cases.append(pc_copy)
                                        break
                        except json.JSONDecodeError:
                            logger.warning("用例 JSON 解析失败，跳过继承项")

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
            db,
            content=doc["content"],
            file_type=doc["file_type"],
            source_ref=doc["source_ref"],
            extraction=extraction,
            project_id=current.project_id or 0,
        )
    except ValueError as e:
        return R(code=400, msg=str(e))
    except Exception as e:
        return R(code=500, msg=f"AI 生成失败: {str(e)}")

    # Inherited cases are part of the canonical generated result. Persist them
    # before exposing the response so refresh/import sees the same case set.
    canonical_functional = [
        dict(case) for case in ai_result.get("functional_cases", [])
    ]
    for inherited_case in inherited_cases:
        inherited_case = dict(inherited_case)
        if (
            inherited_case.get("_inherited")
            and not inherited_case.get("title", "").startswith("[沿用")
        ):
            inherited_case["title"] = (
                f"[沿用自{inherited_case.get('_from_version') or '上版本'}] "
                f"{inherited_case.get('title', '')}"
            )
        canonical_functional.append(inherited_case)
    ai_result = {
        **ai_result,
        "functional_cases": canonical_functional,
        "api_cases": [
            dict(case) for case in ai_result.get("api_cases", [])
        ],
    }

    # Build structured result with canonical indices.
    func_cases: list[AIGeneratedCase] = []
    idx = 0
    for c in ai_result.get("functional_cases", []):
        c["index"] = idx
        c["case_type"] = "manual"
        if isinstance(c.get("steps"), (list, dict)):
            c["steps"] = json.dumps(c["steps"], ensure_ascii=False)
        func_cases.append(AIGeneratedCase(**c))
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

    mode_label = "基于拆分" if use_extraction else "直接"
    try:
        requirement_service.update_ai_result(
            db, document_id, ai_result, commit=False
        )
        requirement_service.replace_review_queue(db, document_id, ai_result)
        _audit(
            req,
            current,
            db,
            "requirement:generate",
            f"doc#{document_id}",
            f"{mode_label}: 分析 {len(extracted_reqs)} 需求点 + "
            f"生成 {len(func_cases)} 功能用例 + {len(api_cases)} 接口用例",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
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
    integration_reqs: list[dict] = Field(default_factory=list)
    service_id: int | None = None


class ApiMatchItem(BaseModel):
    req_id: str = ""
    title: str = ""
    endpoint_id: int = 0
    method: str = ""
    path: str = ""
    summary: str = ""
    confidence: float = 0.0


@router.post("/{document_id}/generate-api-from-endpoints", response_model=R[dict], summary="按已导入接口生成真实接口用例（Phase 2）")
def generate_api_from_endpoints(
    document_id: int,
    service_id: int | None = Query(None),
    current: CurrentUser = Depends(require_permission("requirement:generate")),
    db: Session = Depends(get_db),
):
    """对需求 integration 功能点匹配已导入 ApiEndpoint，确定性生成接口用例并回填模块关联。"""
    try:
        result = requirement_service.generate_api_cases_from_linked_endpoints(
            db,
            doc_id=document_id,
            project_id=current.project_id or 0,
            service_id=service_id,
            reviewer_id=current.user.id if current.user else 0,
        )
    except ValueError as e:
        return R(code=400, msg=str(e))
    return R.ok(result)


@router.post("/{document_id}/match-api", response_model=R[list[ApiMatchItem]], summary="匹配 API 端点")
def match_api_endpoints_for_requirement(
    document_id: int,
    body: MatchApiRequest,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    """Return candidate matches without changing the confirmed selection."""
    doc = requirement_service.get_requirement(
        db, document_id, project_id=current.project_id or 0
    )
    if doc is None:
        raise not_found("需求文档")
    if body.service_id is not None:
        service = get_project_service(db, body.service_id, current.project_id or 0)
        if service is None:
            raise not_found("API 服务")
    if not body.integration_reqs:
        return R.ok([])
    matches = requirement_service.match_api_endpoints(
        db,
        integration_reqs=body.integration_reqs,
        project_id=current.project_id or 0,
        service_id=body.service_id,
    )
    return R.ok([ApiMatchItem(**m) for m in matches])
