"""Source service (V30-025).

V3.0 Source handling is a snapshot/summary concern, not execution. Attaching a
source creates its artifact and mission link; parsing normalizes it into
addressable fragments via the matching SourceAdapter.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import ParseStatus, SourceType
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.sources import repository
from app.modules.aitde.sources.adapters import get_adapter
from app.modules.aitde.sources.models import SourceArtifact, SourceFragment
from app.modules.aitde.sources.schemas import (
    SourceArtifactCreate,
    SourceParseResult,
)

_SUPPORTED_TYPES = {st.value for st in SourceType}


def _mission_row(db: Session, mission_id: int, project_id: int):
    return mission_service.get_mission(db, mission_id, project_id)


def attach_source(
    db: Session,
    payload: SourceArtifactCreate,
    mission_id: int,
    project_id: int,
    user_id: int,
) -> SourceArtifact:
    _mission_row(db, mission_id, project_id)

    stype = payload.source_type.value
    if stype not in _SUPPORTED_TYPES:
        raise APIException(
            code=400, msg=f"不支持的 Source 类型：{stype}", http_status=400
        )

    metadata: dict[str, Any] = {}
    artifact_data: dict[str, Any] = {
        "source_type": stype,
        "provider": payload.provider,
        "parse_status": ParseStatus.PENDING.value,
    }

    if stype == SourceType.MANUAL_NOTE.value:
        artifact_data["name"] = payload.name or "人工补充说明"
        content = payload.content or ""
        metadata["content"] = content
        artifact_data["normalized_text"] = content[:2000]
    elif stype == SourceType.REQUIREMENT.value:
        artifact_data["name"] = payload.name or (
            f"需求文档 #{payload.requirement_doc_id}"
            if payload.requirement_doc_id
            else "需求文档"
        )
        if payload.requirement_doc_id:
            metadata["requirement_doc_id"] = payload.requirement_doc_id
    elif stype == SourceType.OPENAPI.value:
        artifact_data["name"] = payload.name or (payload.uri or "OpenAPI")
        artifact_data["uri"] = payload.uri or ""
        if payload.uri:
            metadata["uri"] = payload.uri

    artifact_data["metadata_json"] = json.dumps(metadata, ensure_ascii=False)

    row = repository.create_artifact(db, artifact_data, project_id, user_id)
    repository.link_artifact_to_mission(
        db, mission_id, row.id, payload.role.value, user_id
    )

    # Manual notes are self-contained: parse them immediately.
    if stype == SourceType.MANUAL_NOTE.value:
        _run_parse(db, row, content=payload.content or "")
        db.refresh(row)

    db.commit()
    db.refresh(row)
    return row


def list_sources(db: Session, mission_id: int) -> list[SourceArtifact]:
    rows = repository.list_artifacts_for_mission(db, mission_id)
    # Attach counts by artifact.
    counts = {a.id: repository.count_fragments(db, a.id) for a in rows}
    for a in rows:
        a._fragment_count = counts.get(a.id, 0)  # type: ignore[attr-defined]
    return rows


def get_source(db: Session, source_id: int, project_id: int) -> SourceArtifact:
    row = repository.get_artifact(db, source_id, project_id)
    if not row:
        raise APIException(code=404, msg="Source 不存在", http_status=404)
    row._fragment_count = repository.count_fragments(db, row.id)  # type: ignore[attr-defined]
    return row


def _content_for_requirement(
    db: Session, metadata: dict[str, Any], artifact: SourceArtifact
) -> str:
    doc_id = metadata.get("requirement_doc_id")
    if doc_id:
        try:
            from app.models.requirement import RequirementDocument

            doc = db.get(RequirementDocument, int(doc_id))
            if doc and getattr(doc, "content", None):
                return doc.content
        except Exception:  # noqa: BLE001
            pass
    return artifact.normalized_text or ""


def _run_parse(
    db: Session, artifact: SourceArtifact, content: str | None = None
) -> SourceParseResult:
    try:
        metadata = json.loads(artifact.metadata_json or "{}")
        if content is None:
            if artifact.source_type == SourceType.REQUIREMENT.value:
                content = _content_for_requirement(db, metadata, artifact)
            elif artifact.source_type == SourceType.OPENAPI.value and artifact.uri:
                content = f"OpenAPI source: {artifact.uri}"
            else:
                content = metadata.get("content", artifact.normalized_text or "")

        adapter = get_adapter(artifact.source_type)
        drafts = adapter.normalize(content or "")
        fragments = repository.replace_fragments(db, artifact.id, drafts)

        artifact.parse_status = ParseStatus.PARSED.value
        # content_hash is the aggregate of fragment hashes for traceability.
        artifact.content_hash = fragments[-1].content_hash if fragments else ""
        db.flush()
        return SourceParseResult(
            artifact_id=artifact.id,
            parse_status=ParseStatus.PARSED.value,
            fragment_count=len(fragments),
            meta={"fragment_keys": [f.fragment_key for f in fragments][:20]},
        )
    except Exception as exc:  # noqa: BLE001
        artifact.parse_status = ParseStatus.FAILED.value
        artifact.metadata_json = json.dumps(
            {"error": str(exc)}, ensure_ascii=False
        )
        db.flush()
        return SourceParseResult(
            artifact_id=artifact.id,
            parse_status=ParseStatus.FAILED.value,
            fragment_count=0,
            meta={"error": str(exc)},
        )


def parse_source(db: Session, source_id: int, project_id: int) -> SourceParseResult:
    artifact = get_source(db, source_id, project_id)
    result = _run_parse(db, artifact)
    db.commit()
    return result


def fragments(db: Session, source_id: int, project_id: int) -> list[SourceFragment]:
    get_source(db, source_id, project_id)
    return repository.list_fragments(db, source_id)
