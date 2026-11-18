"""AUD-008：Artifact Upload / Download API（两阶段上传 + 重新鉴权下载）。

安全约束（v1.5 §02 AUD-008）：

- 上传前必须先创建会话，服务端记录 `expected_sha256`；
- 上传完成后服务端重算 sha256，不匹配标记 `CORRUPTED` 且不落存储；
- 下载/查看前重新检查当前用户 Project scope；禁止仅凭 artifact UUID 下载；
- 未完成上传（PENDING_UPLOAD）不提供下载；已清理（PURGED）只保留审计墓碑。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services.artifact_service import (
    ArtifactAccessDenied,
    InvalidArtifact,
    complete_upload,
    create_pending_artifact,
    get_artifact,
    open_download,
)
from app.aiqe.services.artifact_storage import ArtifactStorageError
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/artifacts", tags=["aiqe-artifacts"])


class ArtifactCreateIn(BaseModel):
    run_id: str = Field(min_length=1, max_length=36)
    artifact_type: str = Field(min_length=1, max_length=32)
    content_type: str = Field(default="application/octet-stream", max_length=100)
    node_run_id: str | None = Field(default=None, max_length=36)
    step_attempt_id: str | None = Field(default=None, max_length=36)
    expected_sha256: str | None = Field(default=None, max_length=64)
    expected_size_bytes: int | None = Field(default=None, ge=0)
    retention_days: int | None = Field(default=None, ge=1, le=365)
    metadata: dict[str, Any] | None = None


def _not_found(artifact_id: str) -> APIException:
    return APIException(code=404, msg=f"artifact 不存在: {artifact_id}", http_status=404)


def _forbidden() -> APIException:
    return APIException(code=403, msg="artifact 不属于当前项目", http_status=403)


def _bad_request(message: str) -> APIException:
    return APIException(code=400, msg=message, http_status=400)


def _serialize(row) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "node_run_id": row.node_run_id,
        "step_attempt_id": row.step_attempt_id,
        "artifact_type": row.artifact_type,
        "content_type": row.mime_type,
        "sha256": row.sha256,
        "size_bytes": row.size_bytes,
        "upload_status": row.upload_status,
        "redaction_status": row.redaction_status,
        "retention_until": row.retention_until.isoformat() if row.retention_until else None,
        "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
        "access_scope": row.access_scope,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "metadata": row.metadata_json or {},
    }


@router.post("", response_model=R[dict], summary="创建 Artifact 上传会话")
def create_artifact_api(
    payload: ArtifactCreateIn,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        row, target = create_pending_artifact(
            db,
            project_id=current.project_id or 0,
            run_id=payload.run_id,
            artifact_type=payload.artifact_type,
            content_type=payload.content_type,
            node_run_id=payload.node_run_id,
            step_attempt_id=payload.step_attempt_id,
            expected_sha256=payload.expected_sha256,
            expected_size_bytes=payload.expected_size_bytes,
            metadata=payload.metadata,
            retention_days=payload.retention_days,
        )
    except ArtifactAccessDenied:
        raise _forbidden() from None
    except InvalidArtifact as exc:
        raise _bad_request(str(exc)) from None
    db.commit()
    return R.ok({"artifact": _serialize(row), "upload": target})


@router.put("/{artifact_id}/content", response_model=R[dict], summary="完成 Artifact 上传")
async def upload_artifact_api(
    artifact_id: str,
    request: Request,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    content = await request.body()
    try:
        row = complete_upload(
            db, artifact_id=artifact_id, project_id=current.project_id or 0, content=content
        )
    except ArtifactAccessDenied:
        db.rollback()
        raise _forbidden() from None
    except InvalidArtifact as exc:
        db.commit()
        message = str(exc)
        if "不存在" in message:
            raise _not_found(artifact_id) from None
        raise _bad_request(message) from None
    db.commit()
    return R.ok({"artifact": _serialize(row)})


@router.get("/{artifact_id}", response_model=R[dict], summary="Artifact 元信息")
def get_artifact_api(
    artifact_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        row = get_artifact(db, artifact_id, current.project_id or 0)
    except ArtifactAccessDenied:
        raise _forbidden() from None
    except InvalidArtifact:
        raise _not_found(artifact_id) from None
    return R.ok(_serialize(row))


@router.get("/{artifact_id}/content", summary="下载 Artifact 内容（重新鉴权）")
def download_artifact_api(
    artifact_id: str,
    current: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    db: Session = Depends(get_db),
):
    try:
        row, content = open_download(
            db, artifact_id=artifact_id, project_id=current.project_id or 0
        )
    except ArtifactAccessDenied:
        raise _forbidden() from None
    except InvalidArtifact as exc:
        if "不存在" in str(exc):
            raise _not_found(artifact_id) from None
        raise _bad_request(str(exc)) from None
    except ArtifactStorageError as exc:
        raise APIException(code=500, msg=str(exc), http_status=500) from None
    return Response(
        content=content,
        media_type=row.mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300"},
    )
