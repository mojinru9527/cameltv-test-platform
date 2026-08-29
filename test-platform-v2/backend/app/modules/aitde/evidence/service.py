"""EvidenceService (V31-003/V31-004).

Persists an evidence artifact: sanitize -> object storage -> metadata row. An
artifact is never stored (or marked COMPLETE) if sanitization or storage fails,
so a broken store can never masquerade as proof.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.integrations.object_storage import StorageError, get_storage
from app.modules.aitde.common.enums import SanitizationStatus
from app.modules.aitde.evidence.sanitizer import sanitize
from app.modules.aitde.execution import repository
from app.modules.aitde.execution.models import EvidenceArtifact


def store_artifact(
    db: Session,
    *,
    project_id: int,
    run_id: int,
    evidence_type: str,
    data: bytes,
    content_type: str,
    step_id: int | None = None,
    headers: dict[str, str] | None = None,
    sensitivity: str = "normal",
    retention_class: str = "standard",
) -> EvidenceArtifact:
    if not isinstance(data, (bytes, bytearray)):
        raise APIException(code=400, msg="证据内容必须是字节", http_status=400)

    safe_bytes, sanitization_status = sanitize(bytes(data), content_type, headers)
    if sanitization_status == SanitizationStatus.REJECTED.value:
        raise APIException(
            code=422, msg="证据包含敏感信息且无法安全清洗，已拒绝", http_status=422
        )

    storage = get_storage()
    filename = f"evidence-{evidence_type.lower()}"
    uri = storage.make_uri(project_id, 0, run_id, filename)

    try:
        info = storage.build(uri, safe_bytes, content_type)
    except StorageError as exc:
        # storage failure must never look like a successful evidence capture
        raise APIException(
            code=503, msg=f"证据存储失败：{exc}", http_status=503
        ) from exc

    row = repository.create_evidence(
        db,
        {
            "project_id": project_id,
            "run_id": run_id,
            "step_id": step_id,
            "evidence_type": evidence_type,
            "storage_provider": storage.provider_name,
            "storage_uri": info["storage_uri"],
            "content_hash": info["content_hash"],
            "content_type": info["content_type"],
            "size_bytes": info["size_bytes"],
            "sanitization_status": sanitization_status,
            "sensitivity": sensitivity,
            "retention_class": retention_class,
        },
    )
    return row


def list_evidence(db: Session, run_id: int, project_id: int) -> list[EvidenceArtifact]:
    return repository.list_evidence(db, run_id, project_id)


def get_artifact(db: Session, artifact_id: int, project_id: int) -> EvidenceArtifact:
    row = repository.get_evidence(db, artifact_id, project_id)
    if not row:
        raise APIException(code=404, msg="证据不存在", http_status=404)
    return row
