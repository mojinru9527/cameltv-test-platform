"""组织服务 —— 个人组织 / 团队组织 / 成员管理（Batch 105 租户模式）。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.models.user import User


ROLE_OWNER = 1
ROLE_ADMIN = 2
ROLE_MEMBER = 3


def personal_org_code(user_id: int) -> str:
    return f"personal-{user_id}"


def ensure_personal_organization(db: Session, user_id: int) -> Organization:
    """确保用户拥有个人组织（幂等）；注册/创建项目时调用。"""
    org = db.scalar(
        select(Organization).where(Organization.code == personal_org_code(user_id))
    )
    if org:
        return org
    org = Organization(
        code=personal_org_code(user_id),
        name="我的组织",
        description="个人工作空间（自动创建）",
        type="personal",
        owner_id=user_id,
        status=1,
    )
    db.add(org)
    db.flush()
    db.add(OrganizationMember(
        organization_id=org.id,
        user_id=user_id,
        role_id=ROLE_OWNER,
    ))
    return org


def is_member(db: Session, user_id: int, organization_id: int) -> bool:
    row = db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return row is not None


def is_owner_or_admin(db: Session, user_id: int, organization_id: int) -> bool:
    row = db.scalar(
        select(OrganizationMember.role_id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return row in (ROLE_OWNER, ROLE_ADMIN)


def organizations_for_user(db: Session, user_id: int, is_superadmin: bool = False) -> list[dict]:
    """用户可见组织（超管全量）+ 成员数/项目数/我的角色。"""
    if is_superadmin:
        orgs = list(
            db.scalars(
                select(Organization).where(Organization.status == 1).order_by(Organization.id)
            ).all()
        )
        role_of: dict[int, int] = {}
    else:
        orgs = list(
            db.scalars(
                select(Organization)
                .join(
                    OrganizationMember,
                    OrganizationMember.organization_id == Organization.id,
                )
                .where(
                    OrganizationMember.user_id == user_id,
                    Organization.status == 1,
                )
                .order_by(Organization.id)
            ).all()
        )
        role_of = dict(
            db.execute(
                select(OrganizationMember.organization_id, OrganizationMember.role_id).where(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id.in_([o.id for o in orgs]),
                )
            ).all()
        )
    if not orgs:
        return []

    member_counts = dict(
        db.execute(
            select(OrganizationMember.organization_id, func.count())
            .where(OrganizationMember.organization_id.in_([o.id for o in orgs]))
            .group_by(OrganizationMember.organization_id)
        ).all()
    )
    project_counts = dict(
        db.execute(
            select(Project.organization_id, func.count())
            .where(
                Project.organization_id.in_([o.id for o in orgs]),
                Project.status == 1,
            )
            .group_by(Project.organization_id)
        ).all()
    )
    return [
        {
            "id": o.id,
            "code": o.code,
            "name": o.name,
            "description": o.description,
            "type": o.type,
            "owner_id": o.owner_id,
            "my_role": role_of.get(o.id, ROLE_OWNER if is_superadmin else ROLE_MEMBER),
            "status": o.status,
            "member_count": member_counts.get(o.id, 0),
            "project_count": project_counts.get(o.id, 0),
        }
        for o in orgs
    ]


def create_team_organization(
    db: Session,
    owner_id: int,
    code: str,
    name: str,
    description: str = "",
    is_super: bool = False,
) -> Organization:
    if not is_super:
        owned = db.scalar(
            select(func.count()).select_from(Organization).where(
                Organization.owner_id == owner_id,
                Organization.type == "team",
                Organization.status == 1,
            )
        )
        if (owned or 0) >= settings.max_team_organizations_per_user:
            raise APIException(
                code=400,
                msg=f"团队组织数量已达上限（{settings.max_team_organizations_per_user}）",
                http_status=400,
            )
    if db.scalar(select(Organization).where(Organization.code == code)):
        raise APIException(code=400, msg="组织编码已存在", http_status=400)
    org = Organization(
        code=code,
        name=name,
        description=description,
        type="team",
        owner_id=owner_id,
        status=1,
    )
    db.add(org)
    db.flush()
    db.add(OrganizationMember(
        organization_id=org.id,
        user_id=owner_id,
        role_id=ROLE_OWNER,
    ))
    return org


def update_organization(
    db: Session, organization_id: int, data
) -> Organization | None:
    org = db.get(Organization, organization_id)
    if not org:
        return None
    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    if data.status is not None:
        org.status = data.status
    db.flush()
    return org


def disable_organization(db: Session, organization_id: int) -> Organization | None:
    org = db.get(Organization, organization_id)
    if not org:
        return None
    if org.type == "personal":
        raise APIException(code=400, msg="个人组织不可停用", http_status=400)
    org.status = 0
    db.flush()
    return org


def list_members(db: Session, organization_id: int) -> list[dict]:
    rows = db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id, isouter=True)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.role_id, OrganizationMember.id)
    ).all()
    return [
        {
            "organization_id": m.organization_id,
            "user_id": m.user_id,
            "role_id": m.role_id,
            "username": u.username if u else "",
            "nickname": u.nickname if u else "",
        }
        for m, u in rows
    ]


def add_member(
    db: Session, organization_id: int, user_id: int, role_id: int
) -> dict:
    if role_id not in (ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER):
        raise APIException(code=400, msg="无效的组织角色", http_status=400)
    existing = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if existing:
        existing.role_id = role_id
        row = existing
    else:
        row = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role_id=role_id,
        )
        db.add(row)
    db.flush()
    user = db.get(User, user_id)
    return {
        "organization_id": organization_id,
        "user_id": user_id,
        "role_id": role_id,
        "username": user.username if user else "",
        "nickname": user.nickname if user else "",
    }


def remove_member(db: Session, organization_id: int, user_id: int) -> bool:
    row = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if not row:
        return False
    if row.role_id == ROLE_OWNER:
        raise APIException(code=400, msg="不能移除组织负责人", http_status=400)
    db.delete(row)
    db.flush()
    return True


def projects_for_org(db: Session, organization_id: int) -> list[dict]:
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.organization_id == organization_id, Project.status == 1)
            .order_by(Project.id.desc())
        ).all()
    )
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "description": p.description or "",
            "status": p.status,
            "owner_id": p.owner_id,
        }
        for p in projects
    ]
