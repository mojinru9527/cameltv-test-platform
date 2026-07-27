"""发布包路由 —— /api/v1/release-bundles

提供 ReleaseBundle CRUD + 版本链导航 + 版本差异触发。
M3 API 层：对接 M2 VersionDiffer 服务。
"""
from __future__ import annotations

import json

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission

logger = logging.getLogger("release_bundles")
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.schemas.common import Page, R
from app.schemas.release_bundle import (
    ReleaseBundleCreate,
    ReleaseBundleListItem,
    ReleaseBundleOut,
    ReleaseBundleUpdate,
    ReleaseBundleVersionChain,
    VersionDiffConfirmRequest,
    VersionDiffRequest,
)
from app.services import audit_service

router = APIRouter(prefix="/release-bundles", tags=["发布包"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ═══════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════

@router.get("", response_model=R[Page[ReleaseBundleListItem]], summary="发布包列表")
def list_bundles(
    status: str | None = Query(None, description="draft / active / archived"),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """列出项目内所有发布包，按创建时间倒序。含模块数统计。"""
    pid = current.project_id or 0
    stmt = select(ReleaseBundle).where(ReleaseBundle.project_id == pid)
    if status:
        stmt = stmt.where(ReleaseBundle.status == status)
    if keyword:
        stmt = stmt.where(
            ReleaseBundle.name.contains(keyword)
            | ReleaseBundle.client_version.contains(keyword)
            | ReleaseBundle.admin_version.contains(keyword)
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(
        stmt.order_by(ReleaseBundle.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all())

    # Enrich with module counts
    bundle_ids = [r.id for r in rows]
    module_counts: dict[int, dict[str, int]] = {}
    if bundle_ids:
        for bid in bundle_ids:
            mod_count = db.scalar(
                select(func.count(RequirementModule.id)).where(
                    RequirementModule.release_bundle_id == bid,
                    RequirementModule.node_type == "module",
                )
            ) or 0
            page_count = db.scalar(
                select(func.count(RequirementModule.id)).where(
                    RequirementModule.release_bundle_id == bid,
                    RequirementModule.node_type == "page",
                )
            ) or 0
            module_counts[bid] = {"module": mod_count, "page": page_count}

    items = []
    for r in rows:
        item = ReleaseBundleListItem.model_validate(r)
        item.module_count = module_counts.get(r.id, {}).get("module", 0)
        item.page_count = module_counts.get(r.id, {}).get("page", 0)
        items.append(item)

    return R.ok(Page(total=total, page=page, page_size=page_size, items=items))


@router.post("", response_model=R[ReleaseBundleOut], summary="创建发布包")
def create_bundle(
    req: Request,
    body: ReleaseBundleCreate,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """创建新的发布包。发布包是模块树的容器，关联用户端和运营后台版本号。"""
    pid = current.project_id or 0

    # Validate parent_bundle_id if provided
    if body.parent_bundle_id:
        parent = db.get(ReleaseBundle, body.parent_bundle_id)
        if not parent or parent.project_id != pid:
            return R(code=400, msg="父发布包不存在或不属于当前项目")

    bundle = ReleaseBundle(
        project_id=pid,
        name=body.name,
        description=body.description,
        client_version=body.client_version,
        admin_version=body.admin_version,
        release_date=body.release_date,
        parent_bundle_id=body.parent_bundle_id,
        status="draft",
    )
    db.add(bundle)
    db.flush()
    _audit(req, current, db, "bundle:create", f"#{bundle.id} {bundle.name}")
    db.commit()
    db.refresh(bundle)
    return R.ok(ReleaseBundleOut.model_validate(bundle))


@router.get("/{bundle_id}", response_model=R[ReleaseBundleOut], summary="发布包详情")
def get_bundle(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取单个发布包的完整信息。"""
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != (current.project_id or 0):
        from app.core.exceptions import not_found
        raise not_found("发布包")
    return R.ok(ReleaseBundleOut.model_validate(bundle))


@router.put("/{bundle_id}", response_model=R[ReleaseBundleOut], summary="更新发布包")
def update_bundle(
    bundle_id: int,
    body: ReleaseBundleUpdate,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """更新发布包字段。仅更新非 None 字段。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(bundle, key, value)

    db.flush()
    _audit(req, current, db, "bundle:update", f"#{bundle_id}")
    db.commit()
    db.refresh(bundle)
    return R.ok(ReleaseBundleOut.model_validate(bundle))


@router.delete("/{bundle_id}", response_model=R[dict], summary="删除发布包")
def delete_bundle(
    bundle_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """删除发布包及其关联的所有模块节点（CASCADE）。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")
    _audit(req, current, db, "bundle:delete", f"#{bundle_id} {bundle.name}")
    db.delete(bundle)
    db.commit()
    return R.ok({"deleted": True})


# ═══════════════════════════════════════════════════════
# 版本链
# ═══════════════════════════════════════════════════════

@router.get("/{bundle_id}/version-chain", response_model=R[list[ReleaseBundleVersionChain]], summary="版本链追溯")
def get_version_chain(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """追溯发布包的完整版本链：从当前版本一直追溯到最初的父版本。"""
    pid = current.project_id or 0
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    chain: list[ReleaseBundleVersionChain] = []
    visited: set[int] = set()
    current_bundle = bundle

    while current_bundle and current_bundle.id not in visited:
        chain.append(ReleaseBundleVersionChain.model_validate(current_bundle))
        visited.add(current_bundle.id)
        if current_bundle.parent_bundle_id:
            current_bundle = db.get(ReleaseBundle, current_bundle.parent_bundle_id)
        else:
            break

    return R.ok(chain)


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
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    # Validate parent
    parent = db.get(ReleaseBundle, body.parent_bundle_id)
    if not parent or parent.project_id != pid:
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
    bundle = db.get(ReleaseBundle, bundle_id)
    if not bundle or bundle.project_id != pid:
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


# ═══════════════════════════════════════════════════════
# B4+B5: 回归范围 + UI 测试触发 (batch-34)
# ═══════════════════════════════════════════════════════

@router.get("/{bundle_id}/regression-scope", response_model=R[dict], summary="计算 UI 回归范围")
def get_regression_scope(
    bundle_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """基于 ReleaseBundle 版本差异计算推荐的 UI 回归测试范围。

    流程：
    1. 沿 parent_bundle_id 找到上一版本
    2. 从 diff_summary 提取变更模块列表
    3. 通过 KnowledgeRelation tested_by 反查关联的 P0/P1 TestCase
    """
    from app.services.knowledge.test_case_linker import get_module_test_summary

    pid = current.project_id or 0
    bundle = db.query(ReleaseBundle).filter(
        ReleaseBundle.id == bundle_id, ReleaseBundle.project_id == pid
    ).first()
    if not bundle:
        return R(code=404, msg="发布包不存在")

    # 获取变更模块名称列表
    changed_modules: set[str] = set()
    try:
        diff = json.loads(bundle.diff_summary or "{}")
        for mod in diff.get("changed_modules", []):
            if isinstance(mod, dict):
                changed_modules.add(mod.get("name", ""))
            elif isinstance(mod, str):
                changed_modules.add(mod)
    except (json.JSONDecodeError, TypeError):
        pass

    # 从模块树中提取 module 名称（RequirementModule 表）
    if not changed_modules:
        modules_rows = db.query(RequirementModule).filter(
            RequirementModule.release_bundle_id == bundle_id
        ).all()
        changed_modules = {m.name for m in modules_rows if m.name}

    if not changed_modules:
        return R.ok({"changed_modules": [], "regression_cases": [], "coverage": {}})

    # 通过 KnowledgeRelation 查找关联的测试用例
    test_summaries = []
    for mod_name in changed_modules:
        try:
            summary = get_module_test_summary(db, mod_name, pid)
            if summary.get("total", 0) > 0:
                test_summaries.append({"module": mod_name, **summary})
        except Exception:
            pass

    return R.ok({
        "bundle_id": bundle_id,
        "bundle_name": bundle.name,
        "client_version": bundle.client_version,
        "changed_modules": list(changed_modules),
        "regression_summary": test_summaries,
        "total_regression_cases": sum(s.get("total", 0) for s in test_summaries),
    })


@router.post("/{bundle_id}/trigger-regression", response_model=R[dict], summary="触发 UI 回归测试")
def trigger_regression_for_bundle(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
    db: Session = Depends(get_db),
):
    """为指定发布包触发关联模块的 UI 回归测试。

    根据模块名称匹配 UiTestScript，触发对应的 UiTestJob 执行。
    """
    from app.models.ui_test import UiTestScript
    from app.services import ui_test_service

    pid = current.project_id or 0
    bundle = db.query(ReleaseBundle).filter(
        ReleaseBundle.id == bundle_id, ReleaseBundle.project_id == pid
    ).first()
    if not bundle:
        return R(code=404, msg="发布包不存在")

    # 获取模块名称
    modules_rows = db.query(RequirementModule).filter(
        RequirementModule.release_bundle_id == bundle_id
    ).all()
    module_names = {m.name for m in modules_rows if m.name}

    if not module_names:
        return R.ok({"triggered": 0, "message": "没有找到模块数据，请先确认版本差异"})

    # 查找匹配的 UI 脚本
    scripts = db.query(UiTestScript).filter(
        UiTestScript.project_id == pid,
        UiTestScript.module.in_(module_names),
        UiTestScript.status == "active",
    ).all()

    triggered_jobs: list[dict] = []
    for script in scripts:
        try:
            job_data = {
                "name": f"[回归] {bundle.client_version} - {script.module}",
                "description": f"版本 {bundle.client_version} 回归测试 - {script.name}",
                "test_spec": script.spec_path,
                "browser": "chromium",
                "environment_id": None,
            }
            result = ui_test_service.create_job(db, job_data, current.user.id, pid)
            if result:
                ui_test_service.trigger_job(db, result["id"], pid, current.user.id)
                triggered_jobs.append({"job_id": result["id"], "module": script.module, "spec": script.name})
        except Exception as e:
            logger.warning(f"Failed to trigger regression for module {script.module}: {e}")

    return R.ok({
        "bundle_id": bundle_id,
        "bundle_name": bundle.name,
        "client_version": bundle.client_version,
        "matched_modules": list(module_names),
        "matched_scripts": len(scripts),
        "triggered": len(triggered_jobs),
        "jobs": triggered_jobs,
    })
