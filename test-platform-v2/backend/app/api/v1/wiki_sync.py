"""LLM-Wiki 同步 API 路由（同步域） —— /api/v1/wiki/*

Batch 181（FIX-173-P2-10）路由拆分：发布包模块树 → Wiki 基线同步 / 覆盖率 / 差异 / 目录预览。
端点函数体与原 wiki.py 逐字一致；ReleaseBundle ORM 查询收敛到
app.services.wiki.sync_service。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException, not_found
from app.schemas.common import R
from app.schemas.release_bundle import (
    WikiSyncRequest,
    WikiSyncResultOut,
    WikiTreeDiffOut,
)
from app.services import audit_service
from app.services.wiki.sync_service import (
    build_wiki_tree,
    diff_module_tree_vs_wiki,
    get_project_bundle,
    get_sync_coverage as get_coverage,
    sync_to_wiki,
)

router = APIRouter(prefix="/wiki", tags=["Wiki 同步"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


def _require_wiki_enabled() -> None:
    if not settings.wiki_enabled:
        raise APIException(code=503, msg="Wiki 知识库未启用（wiki_enabled=False）", http_status=503)


@router.post("/sync/bundle/{bundle_id}", response_model=R[WikiSyncResultOut], summary="模块树同步到 Wiki Raw Source")
def sync_bundle_to_wiki(
    bundle_id: int,
    body: WikiSyncRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("wiki:manage")),
    db: Session = Depends(get_db),
):
    """将发布包的模块树同步到 Wiki Raw Source。

    对模块树中每个页面：
      1. 构建 Wiki 路径（项目/平台/模块/页面）
      2. 收集 LanhuEvidencePage OCR 内容
      3. 创建/更新 WikiRawSource（不可变版本键：bundle:{id}:module:{id}）
      4. 内容不变则跳过（content_hash 幂等）

    这是 Wiki 基线的核心入口——后续的 Wiki 编译和差异对比都基于此基线。
    """
    _require_wiki_enabled()
    pid = current.project_id or 0

    bundle = get_project_bundle(db, bundle_id, pid)
    if not bundle:
        raise not_found("发布包")
    if bundle.status != "active":
        raise APIException(
            code=409,
            msg="发布包未启用，请先在发布包管理中选择该版本并设为启用",
            http_status=409,
        )

    result = sync_to_wiki(
        db,
        release_bundle_id=bundle_id,
        project_id=pid,
        create_wiki_pages=body.create_wiki_pages,
    )
    db.commit()

    _audit(req, current, db, "wiki:sync_bundle", f"bundle#{bundle_id}",
           f"created={result.raw_sources_created} updated={result.raw_sources_updated} "
           f"skipped={result.raw_sources_skipped}")

    return R.ok(WikiSyncResultOut(
        release_bundle_id=result.release_bundle_id,
        raw_sources_created=result.raw_sources_created,
        raw_sources_updated=result.raw_sources_updated,
        raw_sources_skipped=result.raw_sources_skipped,
        coverage=result.coverage,
        errors=result.errors,
    ))


@router.get("/sync/bundle/{bundle_id}/coverage", response_model=R[dict], summary="Wiki 同步覆盖率")
def get_sync_coverage(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    """获取发布包模块树的 Wiki 同步覆盖率统计。

    返回 synced（活跃同步）/ stale（内容过期需重同步）/ missing（未同步）页面的数量。
    """
    pid = current.project_id or 0

    bundle = get_project_bundle(db, bundle_id, pid)
    if not bundle:
        raise not_found("发布包")

    stats = get_coverage(db, release_bundle_id=bundle_id, project_id=pid)
    return R.ok(stats)


@router.get("/sync/bundle/{bundle_id}/diff", response_model=R[WikiTreeDiffOut], summary="模块树 vs Wiki 差异对比")
def diff_bundle_vs_wiki(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    """对比模块树结构与现有 Wiki 页面的差异。

    返回三类差异：
      - only_in_tree: 模块树中有但 Wiki 中无的页面（需同步）
      - only_in_wiki: Wiki 中有但模块树中无的页面（可能已过时或手动创建）
      - in_both: 两边都存在的页面数
    """
    pid = current.project_id or 0

    bundle = get_project_bundle(db, bundle_id, pid)
    if not bundle:
        raise not_found("发布包")

    diff = diff_module_tree_vs_wiki(db, release_bundle_id=bundle_id, project_id=pid)
    return R.ok(WikiTreeDiffOut(
        only_in_tree=diff["only_in_tree"],
        only_in_wiki=diff["only_in_wiki"],
        in_both=diff["in_both"],
        total_tree_pages=diff["total_tree_pages"],
        total_wiki_pages=diff["total_wiki_pages"],
    ))


@router.get("/sync/bundle/{bundle_id}/tree", response_model=R[list[dict]], summary="模块树 Wiki 目录预览")
def preview_wiki_tree(
    bundle_id: int,
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    """预览模块树将被同步到的 Wiki 目录结构（不实际写入）。

    返回扁平化的 Wiki 路径列表，包含每个页面将要创建的目录路径和标题。
    """
    pid = current.project_id or 0

    bundle = get_project_bundle(db, bundle_id, pid)
    if not bundle:
        raise not_found("发布包")

    tree = build_wiki_tree(db, release_bundle_id=bundle_id)

    # Flatten tree to list of path entries
    def _flatten(node, results: list):
        results.append({
            "path": node.path,
            "title": node.title,
            "page_type": node.page_type,
            "module_id": node.module_id,
            "content_preview": node.content_preview,
            "child_count": len(node.children),
        })
        for child in node.children:
            _flatten(child, results)

    flat: list[dict] = []
    for root in tree:
        _flatten(root, flat)

    return R.ok(flat)
