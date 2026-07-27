"""菜单服务 —— 按用户权限点构建侧边栏菜单树。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import Permission
from app.schemas.system import MenuOut


def menu_tree(db: Session, codes: list[str]) -> list[MenuOut]:
    perms = db.scalars(
        select(Permission).where(Permission.type == "menu").order_by(Permission.sort)
    ).all()
    is_super = "*" in codes
    visible = [p for p in perms if is_super or p.code in codes]

    # Build flat list first
    nodes: dict[int, MenuOut] = {}
    for p in visible:
        nodes[p.id] = MenuOut(
            code=p.code, name=p.name, path=p.path, icon=p.icon, sort=p.sort,
        )

    # Attach children to parents
    roots: list[MenuOut] = []
    for p in visible:
        if p.parent_id and p.parent_id in nodes:
            nodes[p.parent_id].children.append(nodes[p.id])
        else:
            roots.append(nodes[p.id])

    # Sort roots by sort order
    roots.sort(key=lambda m: m.sort)
    return roots
