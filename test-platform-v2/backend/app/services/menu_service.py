"""菜单服务 —— 按用户权限点构建侧边栏菜单（P0 为扁平菜单）。"""
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
    return [
        MenuOut(code=p.code, name=p.name, path=p.path, icon=p.icon, sort=p.sort)
        for p in visible
    ]
