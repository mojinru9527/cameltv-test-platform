"""首页「我的待办」dashboard /todo 接口测试（batch-213 / B3）。

沿用 tests/test_ai_config_api.py 的 dependency_overrides 模式：in-memory SQLite
（StaticPool）+ Base.metadata.create_all（顶部 import app.models），override get_db /
get_current_user，不走真实登录。
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.ai_task import AiTask
from app.models.defect import Defect
from app.models.project import Project, ProjectMember
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_review import RequirementReview
from app.models.user import User


@pytest.fixture()
def todo_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine)

    session = maker()
    user = User(id=1, username="tester", password="x", nickname="T", email="t@t.local", status=1)
    session.add(user)
    project = Project(id=1, code="test-proj", name="Test Project", owner_id=1, status=1)
    session.add(project)
    session.add(ProjectMember(project_id=1, user_id=1, role_id=0))

    # 待审：需求文档 + 两条 pending 评审
    doc = RequirementDocument(id=1, project_id=1, title="登录需求", status="parsed")
    session.add(doc)
    session.add(RequirementReview(requirement_id=1, case_index=0, case_type="func", status="pending"))
    session.add(RequirementReview(requirement_id=1, case_index=1, case_type="api", status="pending"))
    session.add(RequirementReview(requirement_id=1, case_index=2, case_type="func", status="approved"))

    # 在跑：AiTask running
    session.add(AiTask(id="task-run-1", task_type="generate", project_id=1, document_id=1, status="running", progress=40))
    # 失败：AiTask failed + 未关闭缺陷
    session.add(AiTask(id="task-fail-1", task_type="extract", project_id=1, document_id=1, status="failed", error="超时"))
    session.add(Defect(id=1, project_id=1, defect_id="D-1", title="登录失败", severity="P1", status="open"))
    session.add(Defect(id=2, project_id=1, defect_id="D-2", title="已修复", severity="P2", status="closed"))
    # 待放行：active 发布包
    session.add(ReleaseBundle(id=1, project_id=1, name="v16.0.0", client_version="16.0.0", admin_version="8.0.0", status="active"))
    session.add(ReleaseBundle(id=2, project_id=1, name="v15.0.0", client_version="15.0.0", status="archived"))

    session.commit()
    return maker


@contextmanager
def _client_for(todo_db, project_id):
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db():
        db = todo_db()
        try:
            yield db
        finally:
            db.close()

    def _current_user():
        db = todo_db()
        try:
            u = db.get(User, 1)
        finally:
            db.close()
        return CurrentUser(user=u, permissions=[], project_id=project_id)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def client(todo_db):
    with _client_for(todo_db, project_id=1) as c:
        yield c


def _data_of(resp):
    assert resp.status_code == 200
    return resp.json()["data"]


def test_todo_buckets(client):
    data = _data_of(client.get("/api/v1/dashboard/todo"))

    assert data["reviews"]["count"] == 2
    assert len(data["reviews"]["items"]) == 2
    assert data["reviews"]["items"][0]["link"].startswith("/requirement/1/review")

    assert data["running"]["count"] == 1
    assert len(data["running"]["items"]) == 1
    assert data["running"]["items"][0]["id"] == "task-run-1"

    assert data["failures"]["count"] == 2  # failed 任务 1 + open 缺陷 1（closed 不计）
    assert len(data["failures"]["items"]) >= 1

    assert data["releases"]["count"] == 1  # 仅 active
    assert len(data["releases"]["items"]) == 1
    assert data["releases"]["items"][0]["link"].startswith("/release-bundles/1")


def test_todo_empty_for_other_project(todo_db):
    # 用 project_id=999（无任何待办数据）验证空桶返回
    with _client_for(todo_db, project_id=999) as emp:
        data = _data_of(emp.get("/api/v1/dashboard/todo"))

    for key in ("reviews", "running", "failures", "releases"):
        assert data[key]["count"] == 0
        assert data[key]["items"] == []
