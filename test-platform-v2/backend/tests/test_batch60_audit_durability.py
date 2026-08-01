from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.audit import AuditLog


def test_system_user_audit_survives_request_session_boundary(
    client,
    auth_headers,
    db_session,
) -> None:
    response = client.post(
        "/api/v1/system/users",
        json={
            "username": "batch60_audit_durable",
            "password": "Batch60!Audit#2026",
            "nickname": "Batch 60 audit durability",
            "email": "batch60-audit@cameltv.local",
            "status": 1,
            "role_codes": [],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    # Simulate the request-scoped session reaching its boundary. A flush-only
    # audit row disappears here; a successful request transaction must persist it.
    db_session.rollback()
    audit = db_session.query(AuditLog).filter_by(
        action="user:create",
        target="用户 batch60_audit_durable",
    ).one_or_none()
    assert audit is not None
    assert audit.project_id == 1
    assert "password" not in audit.detail


def test_failed_request_rolls_back_its_request_transaction(
    client,
    auth_headers,
    db_session,
) -> None:
    first = client.post(
        "/api/v1/system/users",
        json={
            "username": "batch60_duplicate_user",
            "password": "Batch60!Audit#2026",
            "status": 1,
            "role_codes": [],
        },
        headers=auth_headers,
    )
    assert first.status_code == 200

    with pytest.raises(IntegrityError):
        client.post(
            "/api/v1/system/users",
            json={
                "username": "batch60_duplicate_user",
                "password": "Batch60!Audit#2026",
                "status": 1,
                "role_codes": [],
            },
            headers=auth_headers,
        )
    db_session.rollback()
    assert db_session.query(AuditLog).filter_by(
        action="user:create",
        target="用户 batch60_duplicate_user",
    ).count() == 1
