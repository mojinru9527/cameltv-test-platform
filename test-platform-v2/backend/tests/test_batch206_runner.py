# -*- coding: utf-8 -*-
"""Batch 206 / C-内网执行器：环境字段 + 执行引擎 needs_runner 分支 + runner 服务。"""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models.environment import Environment
from app.models.runner_execution import RunnerExecutionTask
from app.services import runner_execution_service as rsvc
from app.services.api_execution_service import _do_execute


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_environment_has_access_fields(db):
    env = Environment(project_id=1, name="Test5-接口", env_type="test",
                      base_url="http://camel-api-gateway05.svc.elelive.cn",
                      access_type="internal", execution_mode="runner", runner_key="test5-01")
    db.add(env); db.commit(); db.refresh(env)
    assert env.access_type == "internal"
    assert env.execution_mode == "runner"
    assert env.runner_key == "test5-01"
    assert env.access_type in ("public", "internal")
    assert env.execution_mode in ("on_platform", "runner")


def test_execute_internal_runner_env_returns_needs_runner(db):
    env = Environment(project_id=1, name="Test5-内网", env_type="test",
                      base_url="http://camel-api-gateway05.svc.elelive.cn",
                      access_type="internal", execution_mode="runner", runner_key="test5-01")
    db.add(env); db.commit(); db.refresh(env)
    res = _do_execute(
        db,
        {"method": "GET", "url": "/camel-service/ee/sports_live/hot_match?page=1&size=10", "headers": {}, "body": "", "query_params": {}},
        [{"type": "status_code", "expected": 200, "operator": "gte"},
         {"type": "status_code", "expected": 300, "operator": "lt"}],
        environment_id=env.id, project_id=1,
    )
    assert res["status"] == "error"
    assert res["error_type"] == "NEEDS_RUNNER"
    assert "runner" in res["error"].lower()


def test_execute_public_on_platform_env_not_blocked(db):
    env = Environment(project_id=1, name="public", env_type="test",
                      base_url="https://example.com", access_type="public", execution_mode="on_platform")
    db.add(env); db.commit(); db.refresh(env)
    # 无断言 → 应先被「需要有效断言」拦截，而非 needs_runner（public 不阻塞）
    res = _do_execute(db, {"method": "GET", "url": "/x", "headers": {}, "body": "", "query_params": {}},
                      [], environment_id=env.id, project_id=1)
    assert res["error_type"] != "NEEDS_RUNNER"


def test_runner_service_create_claim_report(db):
    req = {"method": "GET", "url": "/camel-service/ee/sports_live/hot_match", "headers": {}, "body": "", "query_params": {}}
    task = rsvc.create_runner_task(db, 1, 7, "APIEXEC-ABC", req, [{"type": "status_code", "expected": 200, "operator": "gte"}], "test5-01")
    db.commit(); db.refresh(task)
    assert task.status == "pending"
    # 认领
    claimed = rsvc.claim_runner_task(db, "test5-01")
    assert claimed is not None and claimed.id == task.id
    assert claimed.status == "claimed"
    # 回传
    reported = rsvc.report_runner_task(db, task.id, status="done", result={"http_status": 200})
    assert reported.status == "done"
    assert reported.finished_at is not None
