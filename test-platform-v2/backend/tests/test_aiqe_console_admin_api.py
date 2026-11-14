"""batch-338（P1）：QualityGate / NoiseRules Console API 测试。

覆盖：质量门禁三态（PASS/FAIL/BLOCKED）、噪音规则 CRUD/续期/到期字段、错误码、权限门禁。
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

BASE = "/api/v1/aiqe/admin"


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="console-tester", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="console-proj", name="Console Project", owner_id=1, status=1)
    db.add_all([user, project])
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


def _make_client(db: Session, permissions: list[str]) -> TestClient:
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db() -> Iterator[Session]:
        yield db

    def _current_user() -> CurrentUser:
        user = db.get(User, 1)
        return CurrentUser(
            user=user,
            permissions=list(permissions),
            project_id=1,
            system_permissions=list(permissions),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(db_session, ["menu:aiqe_runs", "defect:list", "defect:update"])
    yield client
    from app.main import app

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["PASS", "PASS"], "PASS"),
        (["PASS", "FAIL"], "FAIL"),
        (["PASS", "NOT_EVALUATED"], "BLOCKED"),
        (["PASS", "ERROR"], "BLOCKED"),
        (["PASS", "BLOCKED"], "BLOCKED"),
    ],
)
def test_quality_gate_status(
    api: TestClient, db_session: Session, statuses: list[str], expected: str
) -> None:
    run_id = _seed_p0_run(db_session, statuses)
    resp = api.post(f"{BASE}/quality-gate", json={"run_ids": [run_id]})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["gate_status"] == expected
    assert data["immutable"] is True
    assert data["rule_version"].startswith("v1.4")


def test_quality_gate_without_p0_is_blocked(
    api: TestClient, db_session: Session
) -> None:
    run_id = _seed_p0_run(db_session, ["PASS"], severity="P1")
    resp = api.post(f"{BASE}/quality-gate", json={"run_ids": [run_id]})
    assert resp.status_code == 200
    assert resp.json()["data"]["gate_status"] == "BLOCKED"


def test_quality_gate_rejects_foreign_run(
    api: TestClient, db_session: Session
) -> None:
    resp = api.post(f"{BASE}/quality-gate", json={"run_ids": ["missing-run"]})
    assert resp.status_code == 404


def _seed_p0_run(
    db: Session, statuses: list[str], *, severity: str = "P0"
) -> str:
    from app.aiqe.models.run import (
        NodeRun,
        RunAssertionResult,
        StepAttempt,
        TestRun,
    )

    run = TestRun(
        project_id=1,
        run_key=f"RUN-GATE-{uuid.uuid4().hex[:8]}",
        source_type="manual",
        status="COMPLETED",
        outcome="PASS",
    )
    db.add(run)
    db.flush()
    node = NodeRun(run_id=run.id, node_key="n1", driver_key="http", status="PASSED")
    db.add(node)
    db.flush()
    attempt = StepAttempt(
        node_run_id=node.id, step_key="n1", attempt_no=1, status="PASSED"
    )
    db.add(attempt)
    db.flush()
    for index, status in enumerate(statuses):
        db.add(
            RunAssertionResult(
                step_attempt_id=attempt.id,
                assertion_key=f"a{index}",
                assertion_type="http_status",
                oracle_layer="STD",
                oracle_ref=f"STD-{index}",
                status=status,
                severity=severity,
            )
        )
    db.commit()
    return run.id


def test_noise_rule_crud(api: TestClient) -> None:
    created = api.post(
        f"{BASE}/noise-rules",
        json={"pattern": "广告弹窗", "action": "suppress", "scope": "run"},
    )
    assert created.status_code == 200, created.text
    rule = created.json()["data"]
    assert rule["id"] > 0
    assert rule["effective"] is True
    assert rule["status"] == "active"

    listing = api.get(f"{BASE}/noise-rules").json()["data"]
    assert any(item["id"] == rule["id"] for item in listing)

    renewed = api.post(f"{BASE}/noise-rules/{rule['id']}/renew")
    assert renewed.status_code == 200
    assert renewed.json()["data"]["expires_at"] is not None

    patched = api.patch(f"{BASE}/noise-rules/{rule['id']}", json={"action": "hint"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["action"] == "hint"

    deleted = api.delete(f"{BASE}/noise-rules/{rule['id']}")
    assert deleted.status_code == 200
    assert api.get(f"{BASE}/noise-rules").json()["data"] == []


def test_noise_rule_rejects_empty_pattern(api: TestClient) -> None:
    resp = api.post(f"{BASE}/noise-rules", json={"pattern": "   "})
    assert resp.status_code == 400, resp.text


def test_noise_rule_rejects_quarantine_without_expiry(api: TestClient) -> None:
    resp = api.post(f"{BASE}/noise-rules", json={"pattern": "flaky", "action": "quarantine"})
    assert resp.status_code == 400, resp.text


def test_noise_rule_rejects_expiry_over_90_days(api: TestClient) -> None:
    too_far = (datetime.now(UTC) + timedelta(days=120)).isoformat()
    resp = api.post(
        f"{BASE}/noise-rules",
        json={"pattern": "long", "expires_at": too_far},
    )
    assert resp.status_code == 400, resp.text


def test_noise_rule_expired_flag(api: TestClient, db_session: Session) -> None:
    from app.aiqe.models.noise_rule import NoiseRule

    past = datetime.now(UTC) - timedelta(days=1)
    db_session.add(
        NoiseRule(
            project_id=1,
            pattern="expired",
            action="suppress",
            scope="run",
            expires_at=past,
            status="active",
            created_at=past - timedelta(days=90),
            updated_at=past,
        )
    )
    db_session.commit()

    listing = api.get(f"{BASE}/noise-rules").json()["data"]
    expired = next(item for item in listing if item["pattern"] == "expired")
    assert expired["effective"] is False


def test_console_admin_requires_menu_permission(db_session: Session) -> None:
    _seed(db_session)
    client = _make_client(db_session, ["defect:list", "defect:update"])
    try:
        assert client.post(f"{BASE}/quality-gate", json={"p0_total": 1}).status_code == 403
        assert client.get(f"{BASE}/noise-rules").status_code == 403
    finally:
        from app.main import app

        app.dependency_overrides.clear()
