from __future__ import annotations

from sqlalchemy import inspect

from app.modules.aitde.evidence.service import store_artifact
from app.modules.aitde.execution.models import EvidenceArtifact


def test_evidence_artifact_table_stores_metadata_only(db_session) -> None:
    columns = set(inspect(EvidenceArtifact).columns.keys())
    forbidden = {"data", "bytes", "blob", "raw", "content"}
    assert columns & forbidden == set()
    assert {"storage_uri", "content_hash", "content_type", "size_bytes"}.issubset(columns)


def test_store_artifact_uses_object_storage_metadata(db_session) -> None:
    row = store_artifact(
        db_session,
        project_id=1,
        run_id=1,
        evidence_type="RESPONSE",
        data=b'{"ok": true}',
        content_type="application/json",
    )
    assert row.storage_provider
    assert row.storage_uri
    assert len(row.content_hash) == 64
    assert row.size_bytes > 0
    assert row.run_id == 1
    assert row.project_id == 1
