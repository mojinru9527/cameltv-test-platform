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


def get_user_by_username(db: Session, username: str) -> User | None:
    """精确按用户名查找用户（路由层 ORM 收敛薄函数）。"""
    return db.scalar(select(User).where(User.username == username))


def get_user_orm(db: Session, user_id: int) -> User | None:
    """按主键查找用户 ORM 对象（路由层 ORM 收敛薄函数）。"""
    return db.get(User, user_id)


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
    created = get_user(db, user.id)
    assert created is not None
    return created


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
    # B11：删除前校验业务引用（test_plan.assignee_id 为 FK 无 ondelete → DB 层会 500；
    # 其余为整型引用，也应避免遗留孤儿数据）。有引用时抛 ValueError，由路由层转 4xx。
    from app.models.defect import Defect
    from app.models.test_plan import TestPlan, TestPlanCase

    refs: list[str] = []
    plan_assignee = db.scalars(
        select(TestPlan).where(TestPlan.assignee_id == user_id)
    ).all()
    if plan_assignee:
        names = "、".join((p.name or f"#{p.id}") for p in plan_assignee[:5])
        refs.append(f"测试计划指派人（{names}{' 等' if len(plan_assignee) > 5 else ''}）")
    if db.scalar(select(TestPlan.id).where(TestPlan.creator_id == user_id).limit(1)):
        refs.append("测试计划创建人")
    if db.scalar(select(TestPlanCase.id).where(TestPlanCase.executor_id == user_id).limit(1)):
        refs.append("计划用例执行人")
    if db.scalar(select(Defect.id).where(Defect.assignee_id == user_id).limit(1)):
        refs.append("缺陷指派人")
    if db.scalar(select(Defect.id).where(Defect.creator_id == user_id).limit(1)):
        refs.append("缺陷创建人")
    if refs:
        raise ValueError("该用户被以下业务记录引用，无法删除：" + "、".join(refs))

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
