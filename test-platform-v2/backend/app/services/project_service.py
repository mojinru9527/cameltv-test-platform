"""项目服务 —— 用户可见项目、成员校验 + CRUD。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_user_names
from app.core.config import settings
from app.core.exceptions import APIException, forbidden, not_found
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User
from app.services import organization_service


def projects_for_user(db: Session, user_id: int, is_superadmin: bool = False) -> list[Project]:
    """超管可见全部项目；普通用户仅见其加入的项目。"""
    if is_superadmin:
        projects = list(db.scalars(select(Project).where(Project.status == 1).order_by(Project.id)).all())
    else:
        proj_ids = set(db.scalars(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        ).all())
        # Batch 105：组织成员可见组织下全部项目
        org_ids = set(db.scalars(
            select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id == user_id
            )
        ).all())
        if org_ids:
            proj_ids |= set(db.scalars(
                select(Project.id).where(
                    Project.organization_id.in_(org_ids),
                    Project.status == 1,
                )
            ).all())
        if not proj_ids:
            return []
        projects = list(
            db.scalars(
                select(Project).where(Project.id.in_(proj_ids), Project.status == 1).order_by(Project.id)
            ).all()
        )
    return projects


def attach_organization_names(db: Session, projects: list[Project]) -> list[dict]:
    """为项目列表附加组织名（接口层使用，避免破坏 ORM 消费者）。"""
    org_names = _org_names(db, {p.organization_id for p in projects if p.organization_id})
    return [
        _project_to_dict(p, org_name=org_names.get(p.organization_id, ""))
        for p in projects
    ]


def _org_names(db: Session, org_ids: set[int]) -> dict[int, str]:
    if not org_ids:
        return {}
    rows = db.execute(
        select(Organization.id, Organization.name).where(Organization.id.in_(org_ids))
    ).all()
    return dict((r[0], r[1]) for r in rows)


def is_member(db: Session, user_id: int, project_id: int) -> bool:
    row = db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.user_id == user_id, ProjectMember.project_id == project_id
        )
    )
    return row is not None


def is_active_project(db: Session, project_id: int) -> bool:
    return db.scalar(
        select(Project.id).where(Project.id == project_id, Project.status == 1)
    ) is not None


# ══════════════════════════════════════════════
# Admin CRUD
# ══════════════════════════════════════════════

def list_all_projects(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    base = select(Project).order_by(Project.id.desc())
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    rows = db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    # Batch load owner names in one query (was N+1 per row)
    owner_ids = {r.owner_id for r in rows if r.owner_id}
    owner_names = batch_user_names(db, owner_ids)
    items = [_project_to_dict(r, owner_names.get(r.owner_id, "")) for r in rows]
    return items, total


def get_project(db: Session, project_id: int) -> dict | None:
    r = db.get(Project, project_id)
    if not r or r.status == 0:
        return None
    owner_name = ""
    if r.owner_id:
        u = db.get(User, r.owner_id)
        if u:
            owner_name = u.nickname or u.username
    return _project_to_dict(r, owner_name)


def get_project_orm(db: Session, project_id: int) -> Project | None:
    """按主键查找项目 ORM 对象（路由层 ORM 收敛薄函数）。"""
    return db.get(Project, project_id)


def create_project(
    db: Session,
    data,
    owner_id: int,
    is_super: bool = False,
    organization_id: int | None = None,
) -> dict:
    # Batch 104：普通用户受个人项目数配额约束（超管不限）
    if not is_super:
        owned = db.scalar(
            select(func.count()).select_from(Project).where(
                Project.owner_id == owner_id, Project.status == 1,
            )
        )
        if (owned or 0) >= settings.max_projects_per_user:
            raise APIException(
                code=400,
                msg=f"项目数量已达上限（{settings.max_projects_per_user}），请停用不再使用的项目",
                http_status=400,
            )
    org = None
    if not organization_id:
        org = organization_service.ensure_personal_organization(db, owner_id)
        organization_id = org.id
    else:
        org = db.get(Organization, organization_id)
        if not org or org.status == 0:
            raise not_found("组织不存在")
        if not is_super and not organization_service.is_member(db, owner_id, organization_id):
            raise forbidden("无权在该组织下创建项目")
    r = Project(
        code=data.code, name=data.name,
        description=data.description or "", owner_id=owner_id,
        status=1, organization_id=organization_id,
    )
    db.add(r)
    db.flush()
    # Batch 104：创建者自动成为项目成员（外放轻量模式核心，修复创建后不可见缺口）
    tester_role = db.scalar(select(Role).where(Role.code == "tester"))
    db.add(ProjectMember(
        project_id=r.id,
        user_id=owner_id,
        role_id=tester_role.id if tester_role else 0,
    ))
    return _project_to_dict(r, org_name=org.name if org else "")


def update_project(db: Session, project_id: int, data) -> dict | None:
    r = db.get(Project, project_id)
    if not r:
        return None
    for k in ("name", "description", "status"):
        if hasattr(data, k):
            v = getattr(data, k)
            if v is not None:
                setattr(r, k, v)
    db.flush()
    db.refresh(r)
    return _project_to_dict(r)


def delete_project(db: Session, project_id: int) -> bool:
    r = db.get(Project, project_id)
    if not r:
        return False
    r.status = 0  # soft delete
    db.flush()
    return True


def add_member(db: Session, project_id: int, user_id: int, role_id: int) -> dict:
    existing = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if existing:
        existing.role_id = role_id
        m = existing
    else:
        m = ProjectMember(project_id=project_id, user_id=user_id, role_id=role_id)
        db.add(m)
    db.flush()
    user = db.get(User, user_id)
    role = db.get(Role, role_id)
    return {
        "project_id": project_id, "user_id": user_id, "role_id": role_id,
        "username": user.username if user else "",
        "role_name": role.name if role else "",
    }


def remove_member(db: Session, project_id: int, user_id: int) -> bool:
    m = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if not m:
        return False
    db.delete(m)
    db.flush()
    return True


def list_members(db: Session, project_id: int) -> list[dict]:
    rows = db.execute(
        select(ProjectMember, User, Role)
        .join(User, User.id == ProjectMember.user_id, isouter=True)
        .join(Role, Role.id == ProjectMember.role_id, isouter=True)
        .where(ProjectMember.project_id == project_id)
    ).all()
    return [
        {"project_id": m.project_id, "user_id": m.user_id, "role_id": m.role_id,
         "username": u.username if u else "", "role_name": r.name if r else ""}
        for m, u, r in rows
    ]


def _project_to_dict(r: Project, owner_name: str = "", org_name: str = "") -> dict:
    return {
        "id": r.id, "code": r.code, "name": r.name,
        "description": r.description or "",
        "owner_id": r.owner_id,
        "organization_id": r.organization_id,
        "organization_name": org_name,
        "owner_name": owner_name,
        "config": getattr(r, "config", "{}") or "{}",
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
