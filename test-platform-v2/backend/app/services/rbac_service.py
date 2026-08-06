"""RBAC 计算 —— 汇总用户的角色与权限点。

约定：权限点编码为 '*' 的角色视为拥有全部权限（超管）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import OrganizationMember
from app.models.project import Project
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
    codes: list[str] = []
    if role_ids:
        perm_ids = db.scalars(
            select(RolePermission.permission_id).where(RolePermission.role_id.in_(role_ids))
        ).all()
        if perm_ids:
            codes = list(
                db.scalars(
                    select(Permission.code).where(Permission.id.in_(set(perm_ids)))
                ).all()
            )
    # Batch 106（C105-1）：组织负责人/管理员对组织内项目拥有项目管理员能力
    if project_id:
        org_role = _org_role_for_project(db, user_id, project_id)
        if org_role in (1, 2):  # 1=负责人 2=管理员（与 organization_service 常量对齐）
            codes = sorted(set(codes) | {
                "project:manage",
                "project:update",
                "project:delete",
                "project:detail",
            })
    return codes


def _org_role_for_project(db: Session, user_id: int, project_id: int) -> int | None:
    """返回用户在项目所属组织中的角色（非组织成员返回 None）。"""
    org_id = db.scalar(
        select(Project.organization_id).where(Project.id == project_id)
    )
    if not org_id:
        return None
    return db.scalar(
        select(OrganizationMember.role_id).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )


def has_permission(codes: list[str], required: str) -> bool:
    return "*" in codes or required in codes
