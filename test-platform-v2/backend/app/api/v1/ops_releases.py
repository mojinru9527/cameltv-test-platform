"""Read-only operations release-control API backed by persisted release facts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import CurrentUser, require_system_permission
from app.schemas.common import R
from app.services.ops_release_reader import (
    OpsDeploymentNotFound,
    OpsReleaseReader,
    OpsReleaseStoreUnavailable,
)

router = APIRouter(prefix="/ops/deployments", tags=["运维发布控制"])


class DeploymentOut(BaseModel):
    id: str
    release_id: str
    manifest_sha256: str
    environment: str
    state: str
    created_at: str


class DeploymentEventOut(BaseModel):
    sequence: int
    from_state: str
    to_state: str
    phase: str
    reason: str
    actor: str
    created_at: str


def _reader() -> OpsReleaseReader:
    return OpsReleaseReader(settings.release_control_database_path)


def _unavailable(exc: OpsReleaseStoreUnavailable) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("", response_model=R[list[DeploymentOut]], summary="运维发布记录列表")
def list_deployments(
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    try:
        return R.ok([DeploymentOut.model_validate(item, from_attributes=True) for item in _reader().list_deployments()])
    except OpsReleaseStoreUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get("/{deployment_id}", response_model=R[DeploymentOut], summary="运维发布记录详情")
def get_deployment(
    deployment_id: str,
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    try:
        return R.ok(DeploymentOut.model_validate(_reader().get_deployment(deployment_id), from_attributes=True))
    except OpsDeploymentNotFound:
        return R(code=404, msg="发布记录不存在")
    except OpsReleaseStoreUnavailable as exc:
        raise _unavailable(exc) from exc


@router.get("/{deployment_id}/events", response_model=R[list[DeploymentEventOut]], summary="运维发布事件")
def list_deployment_events(
    deployment_id: str,
    _: CurrentUser = Depends(require_system_permission("release:view")),
):
    try:
        return R.ok([DeploymentEventOut.model_validate(item, from_attributes=True) for item in _reader().list_events(deployment_id)])
    except OpsDeploymentNotFound:
        return R(code=404, msg="发布记录不存在")
    except OpsReleaseStoreUnavailable as exc:
        raise _unavailable(exc) from exc
