"""组织路由 —— 列表/创建/成员管理/组织项目（Batch 105 租户模式）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import APIException
from app.core.deps import (
    CurrentUser,
    get_current_user,
    require_org_member,
    require_org_owner_or_admin,
)
from app.core.exceptions import not_found
from app.schemas.common import R
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationMemberOut,
    OrganizationOut,
    OrganizationUpdate,
)
from app.services import organization_service, user_service

router = APIRouter(prefix="/organizations", tags=["组织"])


@router.get("", response_model=R[list[OrganizationOut]], summary="我可见的组织")
def list_organizations(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = organization_service.organizations_for_user(
        db, current.user.id, is_superadmin=current.is_super
    )
    return R.ok([OrganizationOut(**item) for item in items])


@router.post("", response_model=R[OrganizationOut], summary="创建团队组织")
def create_organization(
    body: OrganizationCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = organization_service.create_team_organization(
        db,
        owner_id=current.user.id,
        code=body.code,
        name=body.name,
        description=body.description,
        is_super=current.is_super,
    )
    db.commit()
    return R.ok(OrganizationOut(
        id=org.id,
        code=org.code,
        name=org.name,
        description=org.description,
        type=org.type,
        owner_id=org.owner_id,
        my_role=organization_service.ROLE_OWNER,
        status=org.status,
        member_count=1,
        project_count=0,
    ))


@router.put("/{organization_id}", response_model=R[OrganizationOut], summary="更新组织")
def update_organization(
    organization_id: int,
    body: OrganizationUpdate,
    current: CurrentUser = Depends(require_org_owner_or_admin),
    db: Session = Depends(get_db),
):
    org = organization_service.update_organization(db, organization_id, body)
    if not org:
        raise not_found("组织")
    db.commit()
    return R.ok(OrganizationOut(
        id=org.id,
        code=org.code,
        name=org.name,
        description=org.description,
        type=org.type,
        owner_id=org.owner_id,
        my_role=organization_service.ROLE_OWNER,
        status=org.status,
        member_count=0,
        project_count=0,
    ))


@router.delete("/{organization_id}", response_model=R[dict], summary="停用团队组织")
def disable_organization(
    organization_id: int,
    current: CurrentUser = Depends(require_org_owner_or_admin),
    db: Session = Depends(get_db),
):
    org = organization_service.disable_organization(db, organization_id)
    if not org:
        raise not_found("组织")
    db.commit()
    return R.ok({"disabled": True, "id": organization_id})


@router.get("/{organization_id}/members", response_model=R[list[OrganizationMemberOut]], summary="组织成员列表")
def list_members(
    organization_id: int,
    current: CurrentUser = Depends(require_org_owner_or_admin),
    db: Session = Depends(get_db),
):
    return R.ok([
        OrganizationMemberOut(**item)
        for item in organization_service.list_members(db, organization_id)
    ])


@router.post("/{organization_id}/members", response_model=R[OrganizationMemberOut], summary="添加/更新组织成员")
def add_member(
    organization_id: int,
    body: dict,
    current: CurrentUser = Depends(require_org_owner_or_admin),
    db: Session = Depends(get_db),
):
    user_id = body.get("user_id", 0)
    username = body.get("username", "")
    if not user_id and username:
        # 按用户名邀请（不暴露用户目录）：精确匹配
        user = user_service.get_user_by_username(db, username)
        if not user:
            raise APIException(code=400, msg="用户不存在，请先确认对方已注册", http_status=400)
        user_id = user.id
    role_id = body.get("role_id", organization_service.ROLE_MEMBER)
    item = organization_service.add_member(db, organization_id, int(user_id), int(role_id))
    db.commit()
    return R.ok(OrganizationMemberOut(**item))


@router.delete("/{organization_id}/members/{user_id}", response_model=R[dict], summary="移除组织成员")
def remove_member(
    organization_id: int,
    user_id: int,
    current: CurrentUser = Depends(require_org_owner_or_admin),
    db: Session = Depends(get_db),
):
    ok = organization_service.remove_member(db, organization_id, user_id)
    if not ok:
        raise not_found("组织成员")
    db.commit()
    return R.ok({"removed": True, "organization_id": organization_id, "user_id": user_id})


@router.get("/{organization_id}/projects", response_model=R[list[dict]], summary="组织项目列表")
def list_org_projects(
    organization_id: int,
    current: CurrentUser = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return R.ok(organization_service.projects_for_org(db, organization_id))
