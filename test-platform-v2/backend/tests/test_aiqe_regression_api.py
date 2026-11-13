"""batch-341（M9-2）：缺陷修复回归 API 测试（创建 + verification Run + 项目隔离）。"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import TestRun
from app.models.defect import Defect, DefectRegression
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="reg-tester", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="reg-proj", name="Reg Project", owner_id=1, status=1)
    other = Project(id=2, code="reg-other", name="Other", owner_id=2, status=1)
    db.add_all([user, project, other])
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
        return CurrentUser(
            user=db.get(User, 1),
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


def _defect(db: Session, *, project_id: int = 1, title: str = "直播入口无响应") -> Defect:
    row = Defect(project_id=project_id, title=title, severity="P1", status="open")
    db.add(row)
    db.commit()
    return row


def _old_run(db: Session, *, project_id: int = 1) -> TestRun:
    run = TestRun(
        project_id=project_id, run_key="RUN-OLD-0001", source_type="manual", status="COMPLETED", outcome="FAIL"
    )
    db.add(run)
    db.commit()
    return run


def test_create_regression_creates_verification_run(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    old = _old_run(db_session)

    resp = api.post(
        "/api/v1/aiqe/regressions",
        json={
            "defect_id": defect.id,
            "fixed_sha": "abc1234def",
            "previous_run_id": old.id,
            "environment_snapshot": {"env": "test"},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["fixed_sha"] == "abc1234def"
    assert data["previous_run_id"] == old.id
    assert data["status"] == "pending"
    assert data["run"]["status"] == "QUEUED"
    assert data["run"]["commit_sha"] == "abc1234def"
    assert data["run"]["retest_of"] == old.id

    db_session.expire_all()
    regression = db_session.get(DefectRegression, data["id"])
    run = db_session.get(TestRun, data["verification_run_id"])
    assert regression is not None and regression.verification_run_id == run.id
    assert run.source_type == "regression"
    assert run.environment_snapshot_json["defect_id"] == defect.id
    # 旧 Run 不被修改
    assert db_session.get(TestRun, old.id).status == "COMPLETED"


def test_regression_detail_and_list(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    created = api.post(
        "/api/v1/aiqe/regressions",
        json={"defect_id": defect.id, "fixed_sha": "abc1234"},
    ).json()["data"]

    detail = api.get(f"/api/v1/aiqe/regressions/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["defect_id"] == defect.id

    listing = api.get("/api/v1/aiqe/regressions", params={"defect_id": defect.id})
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()["data"]] == [created["id"]]

    other = api.get("/api/v1/aiqe/regressions", params={"defect_id": 999})
    assert other.json()["data"] == []


def test_invalid_defect_rejected(api: TestClient) -> None:
    resp = api.post(
        "/api/v1/aiqe/regressions", json={"defect_id": 999, "fixed_sha": "abc1234"}
    )
    assert resp.status_code == 400, resp.text


def test_short_sha_rejected(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    resp = api.post(
        "/api/v1/aiqe/regressions", json={"defect_id": defect.id, "fixed_sha": "abc"}
    )
    assert resp.status_code == 422 or resp.status_code == 400


def test_cross_project_previous_run_rejected(api: TestClient, db_session: Session) -> None:
    defect = _defect(db_session)
    foreign = _old_run(db_session, project_id=2)
    resp = api.post(
        "/api/v1/aiqe/regressions",
        json={"defect_id": defect.id, "fixed_sha": "abc1234", "previous_run_id": foreign.id},
    )
    assert resp.status_code == 400, resp.text


def test_regression_requires_console_permission(db_session: Session) -> None:
    _seed(db_session)
    client = _make_client(db_session, ["defect:list", "defect:update"])
    try:
        assert client.post(
            "/api/v1/aiqe/regressions", json={"defect_id": 1, "fixed_sha": "abc1234"}
        ).status_code == 403
    finally:
        from app.main import app

        app.dependency_overrides.clear()


def test_unknown_regression_404(api: TestClient) -> None:
    assert api.get("/api/v1/aiqe/regressions/424242").status_code == 404
