"""发布包路由（版本差异） —— /api/v1/release-bundles

Batch 181（FIX-173-P2-10）路由拆分：原 release_bundles.py 中的版本差异端点
（POST /{bundle_id}/diff、POST /{bundle_id}/diff/confirm）拆分至此。
端点函数体逐字移动，仅调整 import；ORM 查询收敛至 app.services.release_bundle_service。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.schemas.release_bundle import (
    VersionDiffConfirmRequest,
    VersionDiffRequest,
)
from app.services import release_bundle_service

router = APIRouter(prefix="/release-bundles", tags=["发布包-差异"])


# ═══════════════════════════════════════════════════════
# 版本差异（对接 M2 VersionDiffer）
# ═══════════════════════════════════════════════════════

@router.post("/{bundle_id}/diff", response_model=R[dict], summary="触发版本差异对比")
async def diff_bundle(
    bundle_id: int,
    body: VersionDiffRequest,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """对比当前发布包与父发布包的模块/页面变化（Phase A 规则引擎 + Phase B AI 辅助）。

    返回 VersionDiffResult 供人工审核后通过 confirm 入库。
    """
    pid = current.project_id or 0
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    # Validate parent
    parent = release_bundle_service.get_bundle(db, body.parent_bundle_id, pid)
    if not parent:
        return R(code=400, msg="父发布包不存在或不属于当前项目")

    from app.services.knowledge.version_differ import diff_bundle as do_diff

    diff_result = await do_diff(
        db,
        release_bundle_id=bundle_id,
        parent_bundle_id=body.parent_bundle_id,
        project_id=pid,
        source_version=body.source_version or bundle.client_version,
    )

    # Serialize VersionDiffResult to dict
    result_dict = {
        "new_modules": diff_result.new_modules,
        "modified_modules": [
            {
                "module_name": m.module_name,
                "parent_module_id": m.parent_module_id,
                "change": m.change,
                "new_pages": m.new_pages,
                "modified_pages": m.modified_pages,
                "deleted_pages": m.deleted_pages,
                "unchanged_pages": m.unchanged_pages,
            }
            for m in diff_result.modified_modules
        ],
        "deleted_modules": diff_result.deleted_modules,
        "unchanged_modules": diff_result.unchanged_modules,
        "diff_confidence": diff_result.diff_confidence,
        "total_pages_diff": diff_result.total_pages_diff,
        "warnings": diff_result.warnings,
    }

    # Store diff summary on the bundle
    bundle.diff_summary = json.dumps(result_dict, ensure_ascii=False)
    db.flush()
    db.commit()

    return R.ok(result_dict)


@router.post("/{bundle_id}/diff/confirm", response_model=R[dict], summary="确认差异并构建模块树")
async def confirm_diff(
    bundle_id: int,
    body: VersionDiffConfirmRequest,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """确认版本差异对比结果，将差异应用到模块树（创建 RequirementModule 节点）。

    支持 overrides 人工修正：reclassify（重分类模块类型）和 skip_modules（跳过指定模块）。
    """
    pid = current.project_id or 0
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    if not bundle.parent_bundle_id:
        return R(code=400, msg="当前发布包无父版本，无法确认差异。请先设置 parent_bundle_id 或直接提取模块树。")

    # Parse diff_summary back into VersionDiffResult
    from app.services.knowledge.version_differ import ModuleChange, VersionDiffResult, confirm_diff as do_confirm

    diff_json = json.loads(bundle.diff_summary or "{}")
    if not diff_json:
        return R(code=400, msg="请先执行版本差异对比（POST /diff），再确认差异。")

    diff_result = VersionDiffResult(
        new_modules=diff_json.get("new_modules", []),
        modified_modules=[
            ModuleChange(
                module_name=m["module_name"],
                parent_module_id=m.get("parent_module_id"),
                change=m.get("change", "modified"),
                new_pages=m.get("new_pages", []),
                modified_pages=m.get("modified_pages", []),
                deleted_pages=m.get("deleted_pages", []),
                unchanged_pages=m.get("unchanged_pages", []),
            )
            for m in diff_json.get("modified_modules", [])
        ],
        deleted_modules=diff_json.get("deleted_modules", []),
        unchanged_modules=diff_json.get("unchanged_modules", []),
        diff_confidence=diff_json.get("diff_confidence", 1.0),
        total_pages_diff=diff_json.get("total_pages_diff", 0),
        warnings=diff_json.get("warnings", []),
    )

    created_modules = await do_confirm(
        db,
        release_bundle_id=bundle_id,
        parent_bundle_id=bundle.parent_bundle_id,
        diff_result=diff_result,
        project_id=pid,
        source_version=bundle.client_version,
        overrides=body.overrides,
    )

    db.commit()
    return R.ok({
        "created_modules": len(created_modules),
        "module_ids": [m.id for m in created_modules],
        "module_names": [m.name for m in created_modules],
    })
