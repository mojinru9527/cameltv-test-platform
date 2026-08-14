"""需求模块 API 路由 —— /api/v1/requirement-modules（提取/用例关联/导入）

Batch 181（FIX-173-P2-10）拆分自 requirement_modules.py，端点逻辑逐字迁移。
（模块查询/树视图在 requirement_modules_core.py）
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import not_found
from app.schemas.common import R
from app.schemas.release_bundle import (
    BuildFromDocumentRequest,
    ModuleExtractRequest,
    ModuleExtractResult,
    ModuleTestSummaryOut,
    ProductionDiffRequest,
)
from app.services import audit_service, requirement_module_service

router = APIRouter(prefix="/requirement-modules", tags=["需求模块-提取"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _commit_with_audit(
    req: Request,
    current: CurrentUser,
    db: Session,
    action: str,
    target: str,
    detail: str = "",
) -> None:
    """Persist one business operation and its audit row atomically."""
    try:
        _audit(req, current, db, action, target, detail)
        db.commit()
    except Exception:
        db.rollback()
        raise


# ═══════════════════════════════════════════════════════
# 模块提取（对接 M2 ModuleExtractor）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/extract", response_model=R[ModuleExtractResult], summary="从证据包提取模块树")
def extract_modules(
    bundle_id: int,
    body: ModuleExtractRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """从 LanhuEvidenceJob 提取模块→页面→功能点层级树。

    自动识别平台（APP/PC/WEB/ADMIN）、更新日志条目和说明附件。
    提取结果写入 RequirementModule 表，关联到指定发布包。
    """
    pid = current.project_id or 0
    bundle = requirement_module_service.get_release_bundle_for_update(db, bundle_id, pid)
    if not bundle:
        raise not_found("发布包")

    from app.services.knowledge.module_extractor import extract_module_tree, persist_module_tree

    # Phase 1: Extract
    extraction = extract_module_tree(
        db,
        evidence_job_id=body.evidence_job_id,
        project_id=pid,
        document_id=body.document_id,
    )

    # Phase 2: Persist
    module_ids = persist_module_tree(
        db,
        extraction=extraction,
        release_bundle_id=bundle_id,
        project_id=pid,
        source_version=body.source_version or bundle.client_version,
    )

    _commit_with_audit(
        req,
        current,
        db,
        "module:extract",
        f"bundle#{bundle_id}",
        f"{len(module_ids)} modules, {extraction.stats}",
    )

    return R.ok(ModuleExtractResult(
        module_ids=module_ids,
        module_count=len(extraction.modules),
        page_count=sum(len(m.pages) for m in extraction.modules),
        attachment_count=len(extraction.attachments),
        changelog_entries=len(extraction.changelog_entries),
        warnings=extraction.warnings,
    ))


@router.post("/build-from-document", response_model=R[ModuleExtractResult], summary="从需求文档直建模块树（C102-3）")
def build_modules_from_document(
    body: BuildFromDocumentRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """C102-3：不依赖蓝湖证据包，从需求文档（extraction_raw/content）直接构建模块树。

    发布包解析顺序：请求体 release_bundle_id → 文档关联 release_bundle_id →
    自动创建（名称=文档标题，client_version=文档版本或 source_version）。
    """
    pid = current.project_id or 0
    document = requirement_module_service.get_requirement_document(db, body.document_id)
    if not document or document.project_id != pid:
        raise not_found("需求文档")

    # Resolve release bundle context
    bundle_id = body.release_bundle_id
    if bundle_id is not None:
        bundle = requirement_module_service.get_release_bundle(db, bundle_id)
        if not bundle or bundle.project_id != pid:
            raise not_found("发布包")
    elif document.release_bundle_id:
        bundle_id = document.release_bundle_id
    else:
        bundle = requirement_module_service.create_release_bundle(
            db,
            project_id=pid,
            name=document.title or "需求文档直建模块树",
            description="Batch 118 C102-3 需求文档直建模块树",
            client_version=document.version or body.source_version or "draft",
        )
        bundle_id = bundle.id

    from app.services.knowledge.module_extractor import (
        build_module_tree_from_document,
        persist_module_tree,
    )

    extraction = build_module_tree_from_document(
        db,
        document_id=body.document_id,
        project_id=pid,
        source_version=body.source_version,
    )
    if not extraction.modules and not extraction.warnings:
        extraction.warnings.append("文档中未解析到模块")

    module_ids = persist_module_tree(
        db,
        extraction=extraction,
        release_bundle_id=bundle_id,
        project_id=pid,
        source_version=body.source_version or document.version or "draft",
    )

    _commit_with_audit(
        req,
        current,
        db,
        "module:build_from_document",
        f"doc#{body.document_id}",
        f"{len(module_ids)} modules, {extraction.stats}",
    )

    return R.ok(ModuleExtractResult(
        module_ids=module_ids,
        module_count=len(extraction.modules),
        page_count=sum(len(m.pages) for m in extraction.modules),
        attachment_count=len(extraction.attachments),
        changelog_entries=len(extraction.changelog_entries),
        warnings=extraction.warnings,
    ))


# ═══════════════════════════════════════════════════════
# 测试用例关联（对接 M2 TestCaseLinker）
# ═══════════════════════════════════════════════════════

@router.post("/bundle/{bundle_id}/link-test-cases", response_model=R[dict], summary="批量关联测试用例到模块")
def link_test_cases(
    bundle_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """对发布包内所有模块执行三级匹配策略（精确名→功能点→API），自动创建 tested_by 关联。"""
    pid = current.project_id or 0
    bundle = requirement_module_service.get_release_bundle(db, bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    from app.services.knowledge.test_case_linker import link_all_modules

    results = link_all_modules(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
        version=bundle.client_version,
    )
    total_linked = sum(r.linked_count for r in results.values())
    total_relations = sum(r.relations_created for r in results.values())

    _commit_with_audit(
        req,
        current,
        db,
        "module:link_tests",
        f"bundle#{bundle_id}",
        f"{len(results)} modules, {total_linked} cases linked",
    )

    return R.ok({
        "modules_processed": len(results),
        "total_linked": total_linked,
        "total_relations": total_relations,
        "results": {
            str(mod_id): {
                "linked_count": r.linked_count,
                "relations_created": r.relations_created,
                "by_strategy": r.by_strategy,
            }
            for mod_id, r in results.items()
        },
    })


@router.get("/{module_id}/test-summary", response_model=R[ModuleTestSummaryOut], summary="模块测试覆盖摘要")
def get_module_test_summary(
    module_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取单个模块的测试覆盖摘要（按用例类型和自动化程度分类）。"""
    pid = current.project_id or 0
    mod = requirement_module_service.get_module(db, module_id)
    if not mod or mod.project_id != pid:
        raise not_found("模块")

    from app.services.knowledge.test_case_linker import get_module_test_summary as get_summary

    summary = get_summary(db, module_id=module_id, project_id=pid)
    return R.ok(ModuleTestSummaryOut(
        module_id=summary.module_id,
        module_name=summary.module_name,
        total_test_cases=summary.total_test_cases,
        functional=summary.functional,
        api=summary.api,
        automation=summary.automation,
        coverage_rate=summary.coverage_rate,
        last_run_status=summary.last_run_status,
        linked_case_ids=summary.linked_case_ids,
    ))


@router.post("/production-diff", response_model=R[dict], summary="生产页面 vs 需求原型差异标注（C102-4）")
def production_diff_annotate(
    body: ProductionDiffRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """对比发布包模块树与生产页面清单，输出 new / matched / missing 差异标注。"""
    pid = current.project_id or 0
    bundle = requirement_module_service.get_release_bundle(db, body.release_bundle_id)
    if not bundle or bundle.project_id != pid:
        raise not_found("发布包")

    from app.services.knowledge.production_diff_service import compute_production_diff

    result = compute_production_diff(
        db,
        release_bundle_id=body.release_bundle_id,
        project_id=pid,
        production_pages=[p.model_dump() for p in body.production_pages],
    )
    return R.ok(result)


class ModuleTreeImportNode(BaseModel):
    path: str
    type: str = "page"
    lanhu_page_id: str = ""
    screenshots: list[str] = []


class ModuleTreeImportRequest(BaseModel):
    release_bundle_id: int | None = None
    bundle_name: str = "蓝湖需求模块树"
    source_version: str = "e6b5ce1e"
    tree: list[ModuleTreeImportNode]


class ModuleTreeImportResult(BaseModel):
    created: int = 0
    skipped: int = 0
    total: int = 0


@router.post("/import-tree", response_model=R[ModuleTreeImportResult], summary="导入需求模块树（蓝湖 sitemap 层级）")
def import_module_tree(
    body: ModuleTreeImportRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """把蓝湖导出 sitemap 的层级树导入 requirement_module（幂等）。

    按 path 层级建 parent_module_id（path 即 平台/模块/页）；node_type=module|page；
    lanhu_page_id=html 文件；screenshot_urls=设计稿截图清单。
    """
    pid = current.project_id or 0
    bundle_id = body.release_bundle_id
    if bundle_id is None:
        bundle = requirement_module_service.create_release_bundle(
            db,
            project_id=pid,
            name=body.bundle_name,
            description="Batch 124 蓝湖需求模块树导入",
            client_version=body.source_version,
        )
        bundle_id = bundle.id

    nodes = sorted(body.tree, key=lambda n: n.path.count("/"))
    path_to_id: dict[str, int] = {}
    created = skipped = 0
    for n in nodes:
        segs = [s for s in n.path.split("/") if s]
        if not segs:
            continue
        name = segs[-1]
        platform = segs[0]
        parent_key = "/".join(segs[:-1])
        parent_id = path_to_id.get(parent_key)

        exists = requirement_module_service.find_module_id(
            db,
            project_id=pid,
            name=name,
            lanhu_page_id=n.lanhu_page_id,
            parent_id=parent_id,
        )
        if exists:
            path_to_id[n.path] = exists
            skipped += 1
            continue
        new_id = requirement_module_service.create_module(
            db,
            project_id=pid,
            release_bundle_id=bundle_id,
            name=name,
            node_type=n.type,
            platform=platform,
            lanhu_page_id=n.lanhu_page_id,
            change_type="added",
            parent_module_id=parent_id,
            source_version=body.source_version,
            screenshot_urls=json.dumps(n.screenshots, ensure_ascii=False),
            sort_order=0,
        )
        path_to_id[n.path] = new_id
        created += 1

    db.commit()
    _commit_with_audit(req, current, db, "module:import_tree", f"bundle#{bundle_id}", f"created {created} skipped {skipped}")
    return R.ok(ModuleTreeImportResult(created=created, skipped=skipped, total=len(body.tree)))
