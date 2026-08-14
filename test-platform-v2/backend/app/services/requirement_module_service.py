"""需求模块薄服务 —— RequirementModule / ReleaseBundle / ModuleAdminLink 查询与最小写入。

Batch 181（FIX-173-P2-10）：路由层拆分后禁 ORM 直连，
本文件集中承载模块树/计数/存在性等查询与最小写入薄函数。
全部函数签名 (db, ...)，沿用调用方会话；db.commit() 仍由路由层负责。
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.requirement import RequirementDocument
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.release_bundle import ReleaseBundle


def get_module(db: Session, module_id: int) -> RequirementModule | None:
    """按主键取需求模块节点。"""
    return db.get(RequirementModule, module_id)


def get_release_bundle(db: Session, bundle_id: int) -> ReleaseBundle | None:
    """按主键取发布包。"""
    return db.get(ReleaseBundle, bundle_id)


def get_release_bundle_for_update(
    db: Session,
    bundle_id: int,
    project_id: int,
) -> ReleaseBundle | None:
    """按主键+项目取发布包并加行锁（with_for_update 语义保留在服务内）。"""
    return db.scalar(
        select(ReleaseBundle)
        .where(
            ReleaseBundle.id == bundle_id,
            ReleaseBundle.project_id == project_id,
        )
        .with_for_update()
    )


def get_requirement_document(db: Session, document_id: int) -> RequirementDocument | None:
    """按主键取需求文档（供 C102-3 直建模块树校验/取版本字段）。"""
    return db.get(RequirementDocument, document_id)


def create_release_bundle(
    db: Session,
    *,
    project_id: int,
    name: str,
    description: str = "",
    client_version: str = "",
    status: str = "draft",
) -> ReleaseBundle:
    """新建发布包并 flush，返回带 id 的 ORM 对象（提交由路由层负责）。"""
    bundle = ReleaseBundle(
        project_id=project_id,
        name=name,
        description=description,
        client_version=client_version,
        status=status,
    )
    db.add(bundle)
    db.flush()
    return bundle


def list_modules(
    db: Session,
    project_id: int,
    *,
    release_bundle_id: int | None = None,
    node_type: str | None = None,
    platform: str | None = None,
    change_type: str | None = None,
    parent_module_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[int, list[RequirementModule]]:
    """模块列表（分页 + 多维过滤），返回 (total, rows)。

    与原路由一致：count 与 rows 使用完全相同的过滤条件。
    """
    stmt = select(RequirementModule).where(RequirementModule.project_id == project_id)
    count_stmt = select(func.count()).select_from(RequirementModule).where(
        RequirementModule.project_id == project_id
    )

    if release_bundle_id:
        stmt = stmt.where(RequirementModule.release_bundle_id == release_bundle_id)
        count_stmt = count_stmt.where(RequirementModule.release_bundle_id == release_bundle_id)
    if node_type:
        stmt = stmt.where(RequirementModule.node_type == node_type)
        count_stmt = count_stmt.where(RequirementModule.node_type == node_type)
    if platform:
        stmt = stmt.where(RequirementModule.platform == platform)
        count_stmt = count_stmt.where(RequirementModule.platform == platform)
    if change_type:
        stmt = stmt.where(RequirementModule.change_type == change_type)
        count_stmt = count_stmt.where(RequirementModule.change_type == change_type)
    if parent_module_id is not None:
        if parent_module_id == 0:
            stmt = stmt.where(RequirementModule.parent_module_id.is_(None))
            count_stmt = count_stmt.where(RequirementModule.parent_module_id.is_(None))
        else:
            stmt = stmt.where(RequirementModule.parent_module_id == parent_module_id)
            count_stmt = count_stmt.where(RequirementModule.parent_module_id == parent_module_id)
    if keyword:
        stmt = stmt.where(
            RequirementModule.name.contains(keyword)
            | RequirementModule.description.contains(keyword)
        )
        count_stmt = count_stmt.where(
            RequirementModule.name.contains(keyword)
            | RequirementModule.description.contains(keyword)
        )

    total = db.scalar(count_stmt) or 0
    rows = list(db.scalars(
        stmt.order_by(RequirementModule.sort_order, RequirementModule.id)
        .offset((page - 1) * page_size).limit(page_size)
    ).all())
    return total, rows


def list_bundle_modules(
    db: Session,
    project_id: int,
    bundle_id: int,
) -> list[RequirementModule]:
    """发布包内全部模块（按 sort_order, id 排序）。"""
    return list(db.scalars(
        select(RequirementModule).where(
            RequirementModule.project_id == project_id,
            RequirementModule.release_bundle_id == bundle_id,
        ).order_by(RequirementModule.sort_order, RequirementModule.id)
    ).all())


def get_bundle_module(
    db: Session,
    project_id: int,
    bundle_id: int,
    module_id: int,
) -> RequirementModule | None:
    """发布包内的指定模块（存在性校验）。"""
    return db.scalar(
        select(RequirementModule).where(
            RequirementModule.id == module_id,
            RequirementModule.project_id == project_id,
            RequirementModule.release_bundle_id == bundle_id,
        )
    )


def list_child_modules(
    db: Session,
    project_id: int,
    bundle_id: int,
    parent_id: int,
) -> list[RequirementModule]:
    """某模块的直接子节点（懒加载，P3 只取一层）。"""
    return list(db.scalars(
        select(RequirementModule).where(
            RequirementModule.project_id == project_id,
            RequirementModule.release_bundle_id == bundle_id,
            RequirementModule.parent_module_id == parent_id,
        ).order_by(RequirementModule.sort_order, RequirementModule.id)
    ).all())


def list_modules_by_parent_ids(
    db: Session,
    project_id: int,
    bundle_id: int,
    parent_ids: list[int],
) -> list[RequirementModule]:
    """parent_module_id ∈ parent_ids 的孙节点（子节点懒加载的第二层）。"""
    if not parent_ids:
        return []
    return list(db.scalars(
        select(RequirementModule).where(
            RequirementModule.project_id == project_id,
            RequirementModule.release_bundle_id == bundle_id,
            RequirementModule.parent_module_id.in_(parent_ids),
        ).order_by(RequirementModule.sort_order, RequirementModule.id)
    ).all())


def get_module_in_project(
    db: Session,
    module_id: int,
    project_id: int,
) -> RequirementModule | None:
    """项目内指定模块（跨系统关联校验用）。"""
    return db.scalar(
        select(RequirementModule).where(
            RequirementModule.id == module_id,
            RequirementModule.project_id == project_id,
        )
    )


def list_bundle_module_ids(
    db: Session,
    project_id: int,
    bundle_id: int,
) -> list[int]:
    """发布包内全部模块 id（跨系统关联列表用）。"""
    return list(db.scalars(
        select(RequirementModule.id).where(
            RequirementModule.project_id == project_id,
            RequirementModule.release_bundle_id == bundle_id,
        )
    ).all())


def find_module_id(
    db: Session,
    *,
    project_id: int,
    name: str,
    lanhu_page_id: str,
    parent_id: int | None = None,
) -> int | None:
    """按 (project, name, lanhu_page_id[, parent]) 查模块 id（import-tree 幂等）。"""
    q = select(RequirementModule.id).where(
        RequirementModule.project_id == project_id,
        RequirementModule.name == name,
        RequirementModule.lanhu_page_id == lanhu_page_id,
    )
    q = q.where(
        RequirementModule.parent_module_id.is_(None) if parent_id is None
        else RequirementModule.parent_module_id == parent_id
    )
    return db.scalar(q)


def create_module(
    db: Session,
    *,
    project_id: int,
    release_bundle_id: int,
    name: str,
    node_type: str,
    platform: str,
    lanhu_page_id: str,
    change_type: str,
    parent_module_id: int | None,
    source_version: str,
    screenshot_urls: str,
    sort_order: int,
) -> int:
    """新建需求模块节点并 flush，返回新节点 id。"""
    row = RequirementModule(
        project_id=project_id,
        release_bundle_id=release_bundle_id,
        name=name,
        node_type=node_type,
        platform=platform,
        lanhu_page_id=lanhu_page_id,
        change_type=change_type,
        parent_module_id=parent_module_id,
        source_version=source_version,
        screenshot_urls=screenshot_urls,
        sort_order=sort_order,
    )
    db.add(row)
    db.flush()
    return row.id


# ── ModuleAdminLink ──

def list_admin_links(
    db: Session,
    project_id: int,
    client_module_ids: list[int],
    relation_type: str | None = None,
) -> list[ModuleAdminLink]:
    """发布包内的跨系统关联（按 id 倒序）。"""
    stmt = select(ModuleAdminLink).where(
        ModuleAdminLink.project_id == project_id,
        ModuleAdminLink.client_module_id.in_(client_module_ids),
    )
    if relation_type:
        stmt = stmt.where(ModuleAdminLink.relation_type == relation_type)
    return list(db.scalars(stmt.order_by(ModuleAdminLink.id.desc())).all())


def find_admin_link_id(
    db: Session,
    *,
    project_id: int,
    client_module_id: int,
    admin_module_id: int,
    relation_type: str,
) -> int | None:
    """同 identity 关联查重（返回已存在 id 或 None）。"""
    return db.scalar(
        select(ModuleAdminLink.id).where(
            ModuleAdminLink.project_id == project_id,
            ModuleAdminLink.client_module_id == client_module_id,
            ModuleAdminLink.admin_module_id == admin_module_id,
            ModuleAdminLink.relation_type == relation_type,
        )
    )


def create_admin_link(
    db: Session,
    *,
    project_id: int,
    client_module_id: int,
    admin_module_id: int,
    relation_type: str,
    confidence: float = 1.0,
    evidence: str = "",
) -> ModuleAdminLink:
    """新建跨系统关联（仅 add；flush 由路由层在事务块内执行以捕获 IntegrityError）。"""
    link = ModuleAdminLink(
        project_id=project_id,
        client_module_id=client_module_id,
        admin_module_id=admin_module_id,
        relation_type=relation_type,
        confidence=confidence,
        evidence=evidence,
    )
    db.add(link)
    return link


def get_admin_link(db: Session, link_id: int) -> ModuleAdminLink | None:
    """按主键取跨系统关联。"""
    return db.get(ModuleAdminLink, link_id)
