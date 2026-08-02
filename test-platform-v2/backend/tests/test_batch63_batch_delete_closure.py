"""Batch 63 — B60-P1-006 批量删除动态闭环（DB/审计/失败回滚）。

要求：确认后 UI/API/DB/审计一致；失败时整批回滚且不写审计。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.audit import AuditLog
from app.models.test_case import TestCase


def _create_case(client, auth_headers, title: str) -> int:
    resp = client.post(
        "/api/v1/test-cases",
        json={"title": title, "domain": "用户端", "module": "测试"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _is_deleted(db_session, case_id: int) -> bool:
    row = db_session.get(TestCase, case_id)
    return bool(row and row.is_deleted)


def test_batch_delete_commits_db_and_audit(client, auth_headers, db_session):
    case_ids = [_create_case(client, auth_headers, f"闭环 {i}") for i in range(2)]

    resp = client.request(
        "DELETE",
        "/api/v1/test-cases/batch",
        json={"ids": case_ids},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["data"] == {"deleted": 2, "total": 2}
    assert all(_is_deleted(db_session, cid) for cid in case_ids)

    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "case:batch_delete",
    ).all()
    assert len(audit) == 1
    assert audit[0].target == "2/2 条用例"
    assert audit[0].project_id == 1


def test_batch_delete_skips_foreign_project_cases(client, auth_headers, db_session):
    own_id = _create_case(client, auth_headers, "本项目用例")
    foreign = TestCase(
        project_id=2,
        title="他项目用例",
        case_type="api",
    )
    db_session.add(foreign)
    db_session.commit()

    resp = client.request(
        "DELETE",
        "/api/v1/test-cases/batch",
        json={"ids": [own_id, foreign.id]},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["data"] == {"deleted": 1, "total": 2}
    assert _is_deleted(db_session, own_id) is True
    assert _is_deleted(db_session, foreign.id) is False
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "case:batch_delete",
    ).one()
    assert audit.target == "1/2 条用例"


def test_batch_delete_failure_rolls_back_all_and_writes_no_audit(
    client, auth_headers, db_session,
):
    case_ids = [_create_case(client, auth_headers, f"回滚 {i}") for i in range(2)]

    real_delete_case = __import__(
        "app.services.test_case_service",
        fromlist=["delete_case"],
    ).delete_case

    calls = {"n": 0}

    def flaky_delete_case(db, case_id, project_id=0):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("injected failure on second case")
        return real_delete_case(db, case_id, project_id=project_id)

    with patch(
        "app.api.v1.test_case.test_case_service.delete_case",
        side_effect=flaky_delete_case,
    ):
        with pytest.raises(RuntimeError, match="injected failure"):
            client.request(
                "DELETE",
                "/api/v1/test-cases/batch",
                json={"ids": case_ids},
                headers=auth_headers,
            )

    assert all(_is_deleted(db_session, cid) is False for cid in case_ids)
    assert db_session.query(AuditLog).filter(
        AuditLog.action == "case:batch_delete",
    ).count() == 0
