"""AUD-018：LLM Benchmark 执行与 REST 入口（服务端计算指标、Provider fail-closed）。"""
from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.aiqe.services import benchmark_service
from app.aiqe.services.benchmark_service import (
    BenchmarkError,
    add_sample,
    create_dataset,
    freeze_dataset,
    run_llm_benchmark,
)
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

BASE = "/api/v1/aiqe"


def _frozen_dataset(db_session: Session, *, project_id: int = 1, samples: int = 4) -> str:
    dataset = create_dataset(
        db_session, project_id=project_id, dataset_key="llm-ds", task_type="learning"
    )
    for index in range(samples):
        add_sample(
            db_session,
            dataset.id,
            sample_id=f"s-{index}",
            golden_labels=["A"] if index % 2 == 0 else ["B"],
            frozen_context={"text": f"sample-{index}"},
            labeler="qa",
            reviewer="lead",
        )
    freeze_dataset(db_session, dataset.id)
    return dataset.id


def _stub_provider(monkeypatch, *, configured: bool = True) -> None:
    monkeypatch.setattr(benchmark_service.ai_client, "is_configured", lambda db, pid: configured)
    monkeypatch.setattr(
        benchmark_service.ai_client,
        "resolve_config",
        lambda db, pid: SimpleNamespace(provider_type="deepseek", model="deepseek-chat"),
    )
    monkeypatch.setattr(
        benchmark_service,
        "build_llm_predictor",
        lambda db, *, project_id: (
            lambda sample: {
                "labels": ["A"] if int(sample.sample_id.split("-")[1]) % 2 == 0 else ["B"],
                "token_usage": {"input": 10, "output": 2},
            }
        ),
    )


def test_run_llm_benchmark_computes_metrics(db_session, monkeypatch):
    _stub_provider(monkeypatch)
    dataset_id = _frozen_dataset(db_session)
    run = run_llm_benchmark(
        db_session, dataset_id=dataset_id, project_id=1, agent_key="A6"
    )
    assert run.status == "COMPLETED"
    assert run.result_status == "REFERENCE_ONLY"  # 4 < 30
    assert run.metrics_json["precision"] == 1.0
    assert run.metrics_json["recall"] == 1.0
    assert run.metrics_json["samples"] == 4
    assert run.model_provider == "deepseek"
    assert run.model_name == "deepseek-chat"
    assert run.prompt_hash.startswith("sha256:")
    assert run.token_usage_json == {"input": 40, "output": 8}


def test_run_llm_benchmark_fails_closed_without_provider(db_session, monkeypatch):
    _stub_provider(monkeypatch, configured=False)
    dataset_id = _frozen_dataset(db_session)
    with pytest.raises(BenchmarkError) as exc:
        run_llm_benchmark(db_session, dataset_id=dataset_id, project_id=1)
    assert "AI_PROVIDER_UNCONFIGURED" in str(exc.value)


def test_run_llm_benchmark_rejects_cross_project_dataset(db_session, monkeypatch):
    _stub_provider(monkeypatch)
    dataset_id = _frozen_dataset(db_session, project_id=2)
    with pytest.raises(BenchmarkError):
        run_llm_benchmark(db_session, dataset_id=dataset_id, project_id=1)


def _seed_user(db: Session) -> None:
    role = Role(code="tester", name="测试", data_scope="project")
    db.add(role)
    db.flush()
    db.add_all(
        [
            User(id=1, username="benchllm", password="x", nickname="B", email="b@b.local", status=1),
            Project(id=1, code="bench-llm", name="Bench LLM", owner_id=1, status=1),
        ]
    )
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    _seed_user(db_session)
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    perms = ["menu:aiqe_runs", "defect:list", "defect:update"]

    def _db():
        yield db_session

    def _user():
        return CurrentUser(
            user=db_session.get(User, 1),
            permissions=perms,
            project_id=1,
            system_permissions=perms,
        )

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_benchmark_run_endpoint(api: TestClient, db_session: Session, monkeypatch):
    _stub_provider(monkeypatch)
    dataset_id = _frozen_dataset(db_session)
    resp = api.post(
        f"{BASE}/benchmarks/datasets/{dataset_id}/runs",
        json={"agent_key": "A6"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["metrics"]["samples"] == 4
    assert data["result_status"] == "REFERENCE_ONLY"
    assert data["token_usage"] == {"input": 40, "output": 8}


def test_benchmark_run_endpoint_requires_provider(api: TestClient, db_session: Session, monkeypatch):
    _stub_provider(monkeypatch, configured=False)
    dataset_id = _frozen_dataset(db_session)
    resp = api.post(
        f"{BASE}/benchmarks/datasets/{dataset_id}/runs",
        json={"agent_key": "A6"},
    )
    assert resp.status_code == 400
    assert "AI_PROVIDER_UNCONFIGURED" in resp.json()["msg"]
