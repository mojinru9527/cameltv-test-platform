"""batch-349（M10-4）：学习候选 API 测试（状态机 + 误报率门禁 + 权限）。"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="learn-tester", password="x", nickname="T", email="t@t.local", status=1)
    approver = User(
        id=2, username="learn-approver", password="x", nickname="A", email="a@t.local", status=1
    )
    project = Project(id=1, code="learn-proj", name="Learn", owner_id=1, status=1)
    db.add_all([user, approver, project])
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.add(ProjectMember(project_id=1, user_id=2, role_id=role.id))
    db.commit()


def _benchmark_run(db: Session, *, false_positive_rate: float = 0.05, samples: int = 60):
    """AUD-018：构造后端真实 BenchmarkRun（golden=A，按比例预测 B 制造误报）。"""
    from app.aiqe.services.benchmark_service import (
        add_sample,
        create_dataset,
        freeze_dataset,
        run_benchmark,
    )

    dataset = create_dataset(
        db, project_id=1, dataset_key=f"api-ds-{uuid.uuid4().hex[:6]}", task_type="learning"
    )
    for index in range(samples):
        add_sample(
            db, dataset.id, sample_id=f"s-{index}", golden_labels=["A"], labeler="qa", reviewer="lead"
        )
    freeze_dataset(db, dataset.id)
    fps = int(round(samples * false_positive_rate))
    return run_benchmark(
        db,
        dataset_id=dataset.id,
        agent_key="A6",
        prompt_hash="sha256:p",
        model_provider="deepseek",
        model_name="deepseek-chat",
        predictor=lambda sample: {
            "labels": ["B"] if int(sample.sample_id.split("-")[1]) < fps else ["A"]
        },
    )


def _make_client(db: Session, permissions: list[str], *, user_id: int = 1) -> TestClient:
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db() -> Iterator[Session]:
        yield db

    def _current_user() -> CurrentUser:
        return CurrentUser(
            user=db.get(User, user_id),
            permissions=list(permissions),
            project_id=1,
            system_permissions=list(permissions),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


@pytest.fixture()
def writer(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(db_session, ["menu:aiqe_runs", "defect:list", "defect:update"])
    yield client
    from app.main import app

    app.dependency_overrides.clear()


@pytest.fixture()
def approver(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(
        db_session,
        ["menu:aiqe_runs", "defect:list", "defect:update", "aiqe:learning:approve"],
    )
    yield client
    from app.main import app

    app.dependency_overrides.clear()


def _create(client: TestClient, pattern: str = "切换账号旧数据残留") -> dict:
    resp = client.post("/api/v1/aiqe/learning/candidates", json={"pattern": pattern})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_create_and_list_candidate(writer: TestClient) -> None:
    created = _create(writer)
    assert created["status"] == "draft"
    listing = writer.get("/api/v1/aiqe/learning/candidates")
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()["data"]] == [created["id"]]


def test_evaluate_and_approve_and_activate(writer: TestClient, db_session: Session) -> None:
    created = _create(writer)
    # FIX-006：双人审批——候选由 user 1 创建，评估/批准/发布必须由不同 user id 执行。
    approver = _make_client(
        db_session,
        ["menu:aiqe_runs", "defect:list", "defect:update", "aiqe:learning:approve"],
        user_id=2,
    )
    run = _benchmark_run(db_session, false_positive_rate=0.05, samples=60)
    evaluated = approver.post(
        f"/api/v1/aiqe/learning/candidates/{created['id']}/evaluate",
        json={"benchmark_run_id": run.id},
    )
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["data"]["status"] == "benchmarked"

    approved = approver.post(f"/api/v1/aiqe/learning/candidates/{created['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "approved"

    activated = approver.post(f"/api/v1/aiqe/learning/candidates/{created['id']}/activate")
    assert activated.status_code == 200, activated.text
    data = activated.json()["data"]
    assert data["candidate"]["status"] == "active"
    assert data["pattern"]["pattern_key"] == "切换账号旧数据残留"

    patterns = approver.get("/api/v1/aiqe/learning/bug-patterns")
    assert patterns.status_code == 200
    assert any(p["pattern_key"] == "切换账号旧数据残留" for p in patterns.json()["data"])


def test_high_false_positive_rate_rejected(approver: TestClient, db_session: Session) -> None:
    created = _create(approver, pattern="高误报规则")
    run = _benchmark_run(db_session, false_positive_rate=0.35, samples=100)
    evaluated = approver.post(
        f"/api/v1/aiqe/learning/candidates/{created['id']}/evaluate",
        json={"benchmark_run_id": run.id},
    )
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["data"]["benchmark"]["false_positive_rate"] > 0.2
    resp = approver.post(f"/api/v1/aiqe/learning/candidates/{created['id']}/approve")
    assert resp.status_code == 400, resp.text
    assert resp.status_code == 400


def test_approve_requires_dedicated_permission(writer: TestClient, db_session: Session) -> None:
    created = _create(writer)
    run = _benchmark_run(db_session, false_positive_rate=0.05, samples=40)
    writer.post(
        f"/api/v1/aiqe/learning/candidates/{created['id']}/evaluate",
        json={"benchmark_run_id": run.id},
    )
    resp = writer.post(f"/api/v1/aiqe/learning/candidates/{created['id']}/approve")
    assert resp.status_code == 403, resp.text


def test_approve_before_benchmark_rejected(approver: TestClient) -> None:
    created = _create(approver, pattern="未评估规则")
    resp = approver.post(f"/api/v1/aiqe/learning/candidates/{created['id']}/approve")
    assert resp.status_code == 400, resp.text


def test_empty_pattern_rejected(writer: TestClient) -> None:
    resp = writer.post("/api/v1/aiqe/learning/candidates", json={"pattern": "   "})
    assert resp.status_code in (400, 422), resp.text


def test_requires_console_menu(db_session: Session) -> None:
    _seed(db_session)
    client = _make_client(db_session, ["defect:update"])
    try:
        assert client.get("/api/v1/aiqe/learning/candidates").status_code == 403
    finally:
        from app.main import app

        app.dependency_overrides.clear()
