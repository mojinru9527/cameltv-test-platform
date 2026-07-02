"""角色 CRUD —— 含权限关联。"""
from __future__ import annotations

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, RolePermission


def list_roles(db: Session) -> list[dict]:
    """列出所有角色，附带其拥有的权限 code 列表（批量查询，避免 N+1）。"""
    roles = list(db.scalars(select(Role).order_by(Role.id)).all())
    if not roles:
        return []

    # Batch load all RolePermission rows and all Permission codes in 2 queries
    role_ids = [r.id for r in roles]
    rp_rows = db.execute(
        select(RolePermission.role_id, RolePermission.permission_id)
        .where(RolePermission.role_id.in_(role_ids))
    ).all()

    # Collect unique permission ids
    perm_ids = {rp.permission_id for rp in rp_rows}
    perm_map: dict[int, str] = {}
    if perm_ids:
        perm_rows = db.execute(
            select(Permission.id, Permission.code)
            .where(Permission.id.in_(perm_ids))
        ).all()
        perm_map = {p.id: p.code for p in perm_rows}

    # Group permissions by role_id
    role_perms: dict[int, list[str]] = {rid: [] for rid in role_ids}
    for rp in rp_rows:
        code = perm_map.get(rp.permission_id)
        if code:
            role_perms.setdefault(rp.role_id, []).append(code)  # type: ignore[arg-type]
        else:
            role_perms.setdefault(rp.role_id, [])

    return [
        {
            "id": r.id, "code": r.code, "name": r.name,
            "data_scope": r.data_scope, "remark": r.remark,
            "permission_codes": sorted(role_perms.get(r.id, [])),
            "created_at": r.created_at,
        }
        for r in roles
    ]


def get_role(db: Session, role_id: int) -> dict | None:
    r = db.get(Role, role_id)
    if not r:
        return None
    # Batch load permissions in 2 queries
    rp_rows = db.execute(
        select(RolePermission.permission_id).where(RolePermission.role_id == role_id)
    ).all()
    codes: list[str] = []
    perm_ids = {rp.permission_id for rp in rp_rows}
    if perm_ids:
        codes = list(
            db.scalars(
                select(Permission.code).where(Permission.id.in_(perm_ids))
            ).all()
        )
    return {
        "id": r.id, "code": r.code, "name": r.name,
        "data_scope": r.data_scope, "remark": r.remark,
        "permission_codes": sorted(codes),
        "created_at": r.created_at,
    }


def create_role(db: Session, data: dict) -> dict:
    role = Role(
        code=data["code"], name=data["name"],
        data_scope=data.get("data_scope", "project"),
        remark=data.get("remark", ""),
    )
    db.add(role)
    db.flush()
    _sync_permissions(db, role.id, data.get("permission_codes", []))
    db.commit()
    return get_role(db, role.id)


def update_role(db: Session, role_id: int, data: dict) -> dict | None:
    role = db.get(Role, role_id)
    if not role:
        return None
    for key in ("name", "data_scope", "remark"):
        if key in data and data[key] is not None:
            setattr(role, key, data[key])
    if "code" in data and data["code"] is not None:
        role.code = data["code"]
    if "permission_codes" in data and data["permission_codes"] is not None:
        _sync_permissions(db, role_id, data["permission_codes"])
    db.commit()
    return get_role(db, role_id)


def delete_role(db: Session, role_id: int) -> bool:
    role = db.get(Role, role_id)
    if not role:
        return False
    db.execute(sa_delete(RolePermission).where(RolePermission.role_id == role_id))
    db.delete(role)
    db.commit()
    return True


def list_all_permissions(db: Session) -> list[dict]:
    """返回所有权限点，供前端角色分配用。"""
    perms = list(
        db.scalars(select(Permission).order_by(Permission.parent_id, Permission.sort)).all()
    )
    return [
        {"id": p.id, "code": p.code, "name": p.name, "type": p.type,
         "parent_id": p.parent_id, "path": p.path, "icon": p.icon, "sort": p.sort}
        for p in perms
    ]


def _sync_permissions(db: Session, role_id: int, codes: list[str]) -> None:
    db.execute(sa_delete(RolePermission).where(RolePermission.role_id == role_id))
    perms = list(db.scalars(select(Permission).where(Permission.code.in_(codes))).all())
    for p in perms:
        db.add(RolePermission(role_id=role_id, permission_id=p.id))
