"""用户 CRUD —— 含角色关联与密码处理。"""
from __future__ import annotations

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.rbac import Role, UserRole
from app.models.user import User


def _role_codes_for(db: Session, user_id: int, project_id: int | None = None) -> list[str]:
    """某用户在某项目下（含全局 project_id=0）的角色 code 列表。"""
    q = select(UserRole.role_id).where(UserRole.user_id == user_id)
    if project_id is not None:
        q = q.where(UserRole.project_id.in_([0, project_id]))
    role_ids = [r for r in db.scalars(q).all() if r]
    if role_ids:
        return list(
            db.scalars(select(Role.code).where(Role.id.in_(set(role_ids)))).all()
        )
    return []


def list_users(db: Session, project_id: int | None = None) -> list[dict]:
    """列出所有用户，附带角色 code 列表。"""
    users = list(db.scalars(select(User).order_by(User.id)).all())
    result = []
    for u in users:
        d = {
            "id": u.id, "username": u.username, "nickname": u.nickname,
            "email": u.email, "status": u.status,
            "role_codes": _role_codes_for(db, u.id, project_id),
            "created_at": u.created_at, "last_login_at": u.last_login_at,
        }
        result.append(d)
    return result


def get_user(db: Session, user_id: int, project_id: int | None = None) -> dict | None:
    u = db.get(User, user_id)
    if not u:
        return None
    return {
        "id": u.id, "username": u.username, "nickname": u.nickname,
        "email": u.email, "status": u.status,
        "role_codes": _role_codes_for(db, u.id, project_id),
        "created_at": u.created_at, "last_login_at": u.last_login_at,
    }


def create_user(db: Session, data: dict) -> dict:
    password = data.get("password")
    if not password:
        raise ValueError("password 为必填字段，不允许为空")
    user = User(
        username=data["username"],
        password=hash_password(password),
        nickname=data.get("nickname", ""),
        email=data.get("email", ""),
        status=data.get("status", 1),
    )
    db.add(user)
    db.flush()

    _sync_roles(db, user.id, data.get("role_codes", []))
    db.commit()
    return get_user(db, user.id)


def update_user(db: Session, user_id: int, data: dict) -> dict | None:
    user = db.get(User, user_id)
    if not user:
        return None
    for key in ("username", "nickname", "email", "status"):
        if key in data and data[key] is not None:
            setattr(user, key, data[key])
    if data.get("password"):
        user.password = hash_password(data["password"])

    if "role_codes" in data and data["role_codes"] is not None:
        _sync_roles(db, user_id, data["role_codes"])

    db.commit()
    return get_user(db, user_id)


def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False
    db.execute(sa_delete(UserRole).where(UserRole.user_id == user_id))
    db.delete(user)
    db.commit()
    return True


def _sync_roles(db: Session, user_id: int, role_codes: list[str]) -> None:
    """全量替换用户的全局角色关联（project_id=0）。"""
    db.execute(sa_delete(UserRole).where(UserRole.user_id == user_id, UserRole.project_id == 0))
    roles = list(db.scalars(select(Role).where(Role.code.in_(role_codes))).all())
    for r in roles:
        db.add(UserRole(user_id=user_id, role_id=r.id, project_id=0))
