"""发布包服务 —— ReleaseBundle / RequirementModule / UiTestScript 的薄查询层。

Batch 181（FIX-173-P2-10）路由拆分：release_bundles_*.py 路由文件不再直连 ORM，
ReleaseBundle / RequirementModule / UiTestScript / RequirementDocument 查询收敛至此。
约定：签名 (db, ...)，沿用调用方会话，不负责 commit（路由中原 db.commit() 保留在路由层）。
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_module import RequirementModule
from app.models.ui_test import UiTestScript


def get_bundle(db: Session, bundle_id: int, project_id: int | None = None) -> ReleaseBundle | None:
    """按 id 取发布包；project_id 非 None 时校验项目归属，不属于则视为不存在。"""
    bundle = db.get(ReleaseBundle, bundle_id)
    if bundle is None:
        return None
    if project_id is not None and bundle.project_id != project_id:
        return None
    return bundle


def list_bundles(
    db: Session,
    *,
    project_id: int,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ReleaseBundle], int]:
    """分页列出项目内发布包（按创建时间倒序），返回 (rows, total)。"""
    stmt = select(ReleaseBundle).where(ReleaseBundle.project_id == project_id)
    if status:
        stmt = stmt.where(ReleaseBundle.status == status)
    if keyword:
        stmt = stmt.where(
            ReleaseBundle.name.contains(keyword)
            | ReleaseBundle.client_version.contains(keyword)
            | ReleaseBundle.admin_version.contains(keyword)
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(
        stmt.order_by(ReleaseBundle.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all())
    return rows, total


def get_module_counts(db: Session, bundle_ids: list[int]) -> dict[int, dict[str, int]]:
    """按发布包统计 module/page 两类节点数，返回 {bundle_id: {"module": n, "page": n}}。"""
    module_counts: dict[int, dict[str, int]] = {}
    if not bundle_ids:
        return module_counts
    counted = db.execute(
        select(
            RequirementModule.release_bundle_id,
            RequirementModule.node_type,
            func.count(RequirementModule.id),
        )
        .where(RequirementModule.release_bundle_id.in_(bundle_ids))
        .group_by(RequirementModule.release_bundle_id, RequirementModule.node_type)
    ).all()
    for bid, node_type, cnt in counted:
        bucket = module_counts.setdefault(bid, {"module": 0, "page": 0})
        if node_type in bucket:
            bucket[node_type] = int(cnt)
    return module_counts


def create_bundle(db: Session, data: dict) -> ReleaseBundle:
    """构造并 flush 新发布包（status 固定 draft）；commit/refresh 由路由层负责。"""
    bundle = ReleaseBundle(
        project_id=data["project_id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        client_version=data.get("client_version", ""),
        admin_version=data.get("admin_version", ""),
        release_date=data.get("release_date"),
        parent_bundle_id=data.get("parent_bundle_id"),
        requirement_url=data.get("requirement_url", ""),
        user_env_url=data.get("user_env_url", ""),
        api_spec_url=data.get("api_spec_url", ""),
        admin_env_url=data.get("admin_env_url", ""),
        environment_id=data.get("environment_id"),
        status="draft",
    )
    db.add(bundle)
    db.flush()
    return bundle


def list_requirement_modules(db: Session, bundle_id: int) -> list[RequirementModule]:
    """发布包下的全部 RequirementModule 节点。"""
    return list(db.scalars(
        select(RequirementModule).where(RequirementModule.release_bundle_id == bundle_id)
    ).all())


def list_active_ui_scripts(
    db: Session, project_id: int, module_names: set[str]
) -> list[UiTestScript]:
    """按项目 + 模块名集合匹配的 active UI 脚本。"""
    if not module_names:
        return []
    return list(db.scalars(
        select(UiTestScript).where(
            UiTestScript.project_id == project_id,
            UiTestScript.module.in_(module_names),
            UiTestScript.status == "active",
        )
    ).all())


def find_requirement_by_source_ref(
    db: Session, project_id: int, url: str
) -> RequirementDocument | None:
    """按 source_ref 查找项目内最新需求文档（同 URL 已存在则复用）。"""
    return db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.project_id == project_id,
            RequirementDocument.source_ref == url,
        ).order_by(RequirementDocument.id.desc())
    )
