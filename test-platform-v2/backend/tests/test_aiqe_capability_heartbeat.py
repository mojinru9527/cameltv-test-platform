"""AUD-005：节点能力心跳（Preflight 30s TTL）验收测试。"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.aiqe.services import capability_registry
from app.aiqe.services.capability_registry import (
    CapabilityError,
    CapabilityStatus,
    heartbeat,
    register_manifest,
    mark_verified,
)
from app.core.db import get_db
from app.main import app
from app.services import ai_agent_service


def _manifest(
    db: Session,
    node_id: str = "node-hb",
    *,
    evidence_ref: str = "artifact-1",
    verified: bool = False,
    age_seconds: int = 300,
):
    row = register_manifest(
        db,
        node_id=node_id,
        driver_key="playwright",
        driver_version="1.5.0",
        capabilities=["aiqe:playwright"],
        platforms=["web_desktop"],
        evidence_ref=evidence_ref,
        heartbeat_at=datetime.now(UTC) - timedelta(seconds=age_seconds),
    )
    if verified:
        row = mark_verified(
            db, node_id, platforms=["web_desktop"], evidence_ref=evidence_ref
        )
    db.commit()
    return row


def test_stale_manifest_is_unavailable_then_heartbeat_recovers(db_session):
    row = _manifest(db_session)
    assert capability_registry.compute_effective_status(row) == "UNAVAILABLE"

    recovered = heartbeat(db_session, row.node_id)
    db_session.commit()
    assert recovered.capability_status == "AVAILABLE"
    assert recovered.available is True
    assert capability_registry.compute_effective_status(recovered) == "AVAILABLE"


def test_verified_manifest_stays_verified_after_heartbeat(db_session):
    row = _manifest(db_session, verified=True)
    assert capability_registry.compute_effective_status(row) == "UNAVAILABLE"

    recovered = heartbeat(db_session, row.node_id)
    db_session.commit()
    assert recovered.capability_status == "VERIFIED"
    assert capability_registry.compute_effective_status(recovered) == "VERIFIED"


def test_revoked_manifest_cannot_heartbeat(db_session):
    row = _manifest(db_session)
    capability_registry.revoke(db_session, row.node_id, reason="security")
    db_session.commit()
    with pytest.raises(CapabilityError):
        heartbeat(db_session, row.node_id)


def test_missing_manifest_raises_lookup(db_session):
    with pytest.raises(LookupError):
        heartbeat(db_session, "missing-node")


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    def _db():
        yield db_session

    app.dependency_overrides[get_db] = _db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _token(db: Session, node_id: str) -> str:
    _row, plain = ai_agent_service.register_agent(db, node_id, 1, ["aiqe:playwright"])
    assert plain
    return plain


def test_heartbeat_api_success(api: TestClient, db_session: Session):
    _manifest(db_session, node_id="node-api")
    token = _token(db_session, "node-api")
    resp = api.post(
        "/api/v1/aiqe/nodes/node-api/heartbeat",
        headers={"X-AI-Agent-Token": token},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["node_id"] == "node-api"
    assert data["capability_status"] == "AVAILABLE"
    assert data["next_heartbeat_seconds"] == 15


def test_heartbeat_api_requires_token(api: TestClient, db_session: Session):
    _manifest(db_session, node_id="node-noauth")
    assert api.post("/api/v1/aiqe/nodes/node-noauth/heartbeat").status_code == 401
    assert (
        api.post(
            "/api/v1/aiqe/nodes/node-noauth/heartbeat",
            headers={"X-AI-Agent-Token": "bad-token"},
        ).status_code
        == 401
    )


def test_heartbeat_api_rejects_token_node_mismatch(api: TestClient, db_session: Session):
    _manifest(db_session, node_id="node-a")
    token = _token(db_session, "node-b")
    resp = api.post(
        "/api/v1/aiqe/nodes/node-a/heartbeat",
        headers={"X-AI-Agent-Token": token},
    )
    assert resp.status_code == 403


def test_heartbeat_api_unknown_manifest(api: TestClient, db_session: Session):
    token = _token(db_session, "node-ghost")
    resp = api.post(
        "/api/v1/aiqe/nodes/node-ghost/heartbeat",
        headers={"X-AI-Agent-Token": token},
    )
    assert resp.status_code == 404


def test_heartbeat_api_revoked_manifest(api: TestClient, db_session: Session):
    row = _manifest(db_session, node_id="node-revoked")
    capability_registry.revoke(db_session, row.node_id, reason="security")
    db_session.commit()
    token = _token(db_session, "node-revoked")
    resp = api.post(
        "/api/v1/aiqe/nodes/node-revoked/heartbeat",
        headers={"X-AI-Agent-Token": token},
    )
    assert resp.status_code == 409


def test_status_enum_roundtrip():
    assert CapabilityStatus.AVAILABLE.value == "AVAILABLE"
