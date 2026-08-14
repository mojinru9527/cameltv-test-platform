"""发布包路由（CRUD/覆盖/需求导入/版本链/回归范围/UI 回归触发） —— /api/v1/release-bundles

Batch 181（FIX-173-P2-10）路由拆分：原 release_bundles.py 拆分为
release_bundles_core.py（本文件）/ release_bundles_diff.py。
端点函数体逐字移动，仅调整 import；ORM 查询收敛至 app.services.release_bundle_service。
"""
from __future__ import annotations

import json

import logging

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.release_bundle import (
    ReleaseBundleCreate,
    ReleaseBundleListItem,
    ReleaseBundleOut,
    ReleaseBundleUpdate,
    ReleaseBundleVersionChain,
    VersionCoverageOut,
)
from app.services import audit_service, release_bundle_service
from app.services.production_operation_guard import ProductionOperation, require_allowed_operation

logger = logging.getLogger("release_bundles")

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
    rows, total = release_bundle_service.list_bundles(
        db, project_id=pid, status=status, keyword=keyword, page=page, page_size=page_size
    )

    # Enrich with module counts
    bundle_ids = [r.id for r in rows]
    module_counts = release_bundle_service.get_module_counts(db, bundle_ids)

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
        parent = release_bundle_service.get_bundle(db, body.parent_bundle_id, pid)
        if not parent:
            return R(code=400, msg="父发布包不存在或不属于当前项目")

    bundle = release_bundle_service.create_bundle(db, {
        "project_id": pid,
        "name": body.name,
        "description": body.description,
        "client_version": body.client_version,
        "admin_version": body.admin_version,
        "release_date": body.release_date,
        "parent_bundle_id": body.parent_bundle_id,
        "requirement_url": body.requirement_url,
        "user_env_url": body.user_env_url,
        "api_spec_url": body.api_spec_url,
        "admin_env_url": body.admin_env_url,
        "environment_id": body.environment_id,
    })
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
    bundle = release_bundle_service.get_bundle(db, bundle_id, current.project_id or 0)
    if not bundle:
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
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
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


@router.get("/{bundle_id}/coverage", response_model=R[VersionCoverageOut], summary="版本三类型模块覆盖矩阵（Phase 0）")
def get_bundle_coverage(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """返回发布包模块 × 功能/接口/UI × 执行状态的覆盖矩阵与 60% 门禁。"""
    from app.services.version_coverage_service import compute_bundle_coverage
    return R.ok(VersionCoverageOut(**compute_bundle_coverage(db, bundle_id, current.project_id or 0)))


@router.post("/{bundle_id}/import-requirement", response_model=R[dict], summary="从需求地址创建需求文档并关联发布包（Phase 1）")
def import_bundle_requirement(
    bundle_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """抓取 bundle.requirement_url 并创建关联该发布包的需求文档（同 URL 已存在则复用）。"""
    from app.services.requirement_source_service import RequirementSourceError, fetch_url_content
    from app.services import requirement_service

    pid = current.project_id or 0
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
        from app.core.exceptions import not_found
        raise not_found("发布包")
    url = (bundle.requirement_url or "").strip()
    if not url:
        return R(code=400, msg="发布包尚未配置需求地址")

    existing = release_bundle_service.find_requirement_by_source_ref(db, pid, url)
    if existing:
        existing.release_bundle_id = bundle_id
        db.commit()
        return R.ok({"document_id": existing.id, "reused": True, "title": existing.title})

    try:
        fetched = fetch_url_content(url)
    except RequirementSourceError as exc:
        return R(code=400, msg=str(exc))

    doc = requirement_service.create_requirement(
        db,
        project_id=pid,
        creator_id=current.user.id if current.user else 0,
        title=(fetched.get("title") or "版本需求")[:200],
        file_type=fetched.get("kind", "generic"),
        source_ref=url,
        source_url=url,
        content=fetched.get("content", ""),
        release_bundle_id=bundle_id,
    )
    _audit(req, current, db, "bundle:import_requirement", f"#{bundle_id}", f"doc#{doc['id']}")
    db.commit()
    return R.ok({"document_id": doc["id"], "reused": False, "title": doc["title"]})


@router.delete("/{bundle_id}", response_model=R[dict], summary="删除发布包")
def delete_bundle(
    bundle_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """删除发布包及其关联的所有模块节点（CASCADE）。"""
    pid = current.project_id or 0
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
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
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
        from app.core.exceptions import not_found
        raise not_found("发布包")

    chain: list[ReleaseBundleVersionChain] = []
    visited: set[int] = set()
    current_bundle = bundle

    while current_bundle and current_bundle.id not in visited:
        chain.append(ReleaseBundleVersionChain.model_validate(current_bundle))
        visited.add(current_bundle.id)
        if current_bundle.parent_bundle_id:
            current_bundle = release_bundle_service.get_bundle(db, current_bundle.parent_bundle_id)
        else:
            break

    return R.ok(chain)


# ═══════════════════════════════════════════════════════
# B4+B5: 回归范围 + UI 测试触发 (batch-34)
# ═══════════════════════════════════════════════════════

@router.get("/{bundle_id}/regression-scope", response_model=R[dict], summary="计算 UI 回归范围")
def get_regression_scope(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
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
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
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
        logger.warning("模块树 JSON 解析失败，按空集合处理")

    # 从模块树中提取 module 名称（RequirementModule 表）
    if not changed_modules:
        modules_rows = release_bundle_service.list_requirement_modules(db, bundle_id)
        changed_modules = {m.name for m in modules_rows if m.name}

    if not changed_modules:
        return R.ok({
            "bundle_id": bundle_id,
            "bundle_name": bundle.name,
            "client_version": bundle.client_version,
            "changed_modules": [],
            "regression_summary": [],
            "total_regression_cases": 0,
        })

    # 通过 KnowledgeRelation 查找关联的测试用例
    test_summaries = []
    for mod_name in changed_modules:
        try:
            summary = get_module_test_summary(db, mod_name, pid)
            if summary.get("total", 0) > 0:
                test_summaries.append({"module": mod_name, **summary})
        except Exception:
            logger.warning("获取模块测试摘要失败: %s", mod_name)

    return R.ok({
        "bundle_id": bundle_id,
        "bundle_name": bundle.name,
        "client_version": bundle.client_version,
        "changed_modules": list(changed_modules),
        "regression_summary": test_summaries,
        "total_regression_cases": sum(s.get("total", 0) for s in test_summaries),
    })


class TriggerRegressionRequest(BaseModel):
    environment_id: int
    confirm_prod: bool = False


@router.post("/{bundle_id}/trigger-regression", response_model=R[dict], summary="触发 UI 回归测试")
def trigger_regression_for_bundle(
    bundle_id: int,
    body: TriggerRegressionRequest,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
    db: Session = Depends(get_db),
):
    """为指定发布包触发关联模块的 UI 回归测试。

    根据模块名称匹配 UiTestScript，触发对应的 UiTestJob 执行。
    """
    from app.services import ui_test_service

    pid = current.project_id or 0
    bundle = release_bundle_service.get_bundle(db, bundle_id, pid)
    if not bundle:
        return R(code=404, msg="发布包不存在")

    target_environment = require_allowed_operation(
        db,
        ProductionOperation(
            action=f"Trigger UI regression for release bundle #{bundle_id}",
            project_id=pid,
            environment_id=body.environment_id,
            permission="uitest:trigger_prod",
            confirmed=body.confirm_prod,
        ),
        set(current.permissions),
    )

    # 获取模块名称
    modules_rows = release_bundle_service.list_requirement_modules(db, bundle_id)
    module_names = {m.name for m in modules_rows if m.name}

    if not module_names:
        return R.ok({"triggered": 0, "message": "没有找到模块数据，请先确认版本差异"})

    # 查找匹配的 UI 脚本
    scripts = release_bundle_service.list_active_ui_scripts(db, pid, module_names)

    triggered_jobs: list[dict] = []
    for script in scripts:
        try:
            job_data = {
                "name": f"[回归] {bundle.client_version} - {script.module}",
                "description": f"版本 {bundle.client_version} 回归测试 - {script.name}",
                "test_spec": script.spec_path,
                "browser": "chromium",
                "environment_id": target_environment.id,
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
