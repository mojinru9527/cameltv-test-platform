"""RBAC 计算 —— 汇总用户的角色与权限点。

约定：权限点编码为 '*' 的角色视为拥有全部权限（超管）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import ProjectMember
from app.models.rbac import Permission, RolePermission, UserRole


def role_ids_for_user(db: Session, user_id: int, project_id: int | None = None) -> set[int]:
    """用户的角色集合 = 全局角色(project_id=0) + 指定项目内角色 + 项目成员角色。"""
    stmt = select(UserRole.role_id).where(
        UserRole.user_id == user_id,
        UserRole.project_id == 0,
    )
    role_ids: set[int] = set(db.scalars(stmt).all())

    if project_id:
        stmt2 = select(UserRole.role_id).where(
            UserRole.user_id == user_id, UserRole.project_id == project_id
        )
        role_ids |= set(db.scalars(stmt2).all())
        member_roles = select(ProjectMember.role_id).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.role_id != 0,
        )
        role_ids |= set(db.scalars(member_roles).all())
    return role_ids


def permission_codes(db: Session, user_id: int, project_id: int | None = None) -> list[str]:
    """汇总用户拥有的权限点编码列表。"""
    role_ids = role_ids_for_user(db, user_id, project_id)
    if not role_ids:
        return []
    perm_ids = db.scalars(
        select(RolePermission.permission_id).where(RolePermission.role_id.in_(role_ids))
    ).all()
    if not perm_ids:
        return []
    codes = db.scalars(
        select(Permission.code).where(Permission.id.in_(set(perm_ids)))
    ).all()
    return sorted(set(codes))


def has_permission(codes: list[str], required: str) -> bool:
    return "*" in codes or required in codes
