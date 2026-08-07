"""Batch 115（C107-2）— 接口依赖链测试（前置执行 + $prev 变量注入 + 环检测）。"""
from __future__ import annotations

import httpx
import pytest

from app.models.test_case import TestCase
from app.services import api_execution_service as svc


def _seed(db, *, depends: str = "[]", endpoint: str = "https://api.test/echo",
          body: str = "{}", method: str = "POST", title: str = "t") -> int:
    c = TestCase(
        project_id=1, title=title, case_type="api", domain="接口测试",
        api_method=method, api_endpoint=endpoint, api_body=body,
        api_headers='{"Content-Type": "application/json"}',
        api_assertions='[{"type":"status_code","expected":200}]',
        depends_on_ids=depends, review_status="draft",
    )
    db.add(c)
    db.flush()
    return c.id


def _fake_request(captured: list):
    def fake(db, *, method, url, headers, body, environment_id, project_id):
        captured.append({"method": method, "url": url, "content": body})
        req = httpx.Request(method, url)
        if "/dep" in url:
            return httpx.Response(200, json={"code": 0, "data": {"token": "TKN-123", "news_id": 42}}, request=req)
        return httpx.Response(200, json={"code": 0, "data": {"ok": True}}, request=req)
    return fake


def test_dependency_chain_injects_variables(db_session, monkeypatch) -> None:
    dep_id = _seed(db_session, endpoint="https://api.test/dep", method="GET", title="dep")
    main_id = _seed(
        db_session,
        depends="[%d]" % dep_id,
        endpoint="https://api.test/news?id=$prev.%d.data.news_id" % dep_id,
        body='{"token":"$prev.%d.data.token"}' % dep_id,
        title="main",
    )
    captured: list = []
    monkeypatch.setattr(svc, "_request_with_target_policy", _fake_request(captured))

    r = svc.execute_api_case(db_session, main_id, project_id=1)
    assert r["all_pass"] is True
    assert len(captured) == 2, f"应执行前置+主用例，实际 {captured}"
    dep_call, main_call = captured[0], captured[1]
    assert "/dep" in dep_call["url"]
    assert "id=42" in main_call["url"], main_call["url"]
    assert "TKN-123" in str(main_call["content"]), main_call["content"]


def test_dependency_missing_raises(db_session, monkeypatch) -> None:
    main_id = _seed(db_session, depends='[999999]', title="main")
    captured: list = []
    monkeypatch.setattr(svc, "_request_with_target_policy", _fake_request(captured))
    with pytest.raises(ValueError):
        svc.execute_api_case(db_session, main_id, project_id=1)


def test_dependency_cycle_raises(db_session, monkeypatch) -> None:
    a_id = _seed(db_session, endpoint="https://api.test/a", title="a")
    b_id = _seed(db_session, endpoint="https://api.test/b", title="b")
    # a -> b, b -> a
    a = db_session.get(TestCase, a_id)
    b = db_session.get(TestCase, b_id)
    a.depends_on_ids = "[%d]" % b_id
    b.depends_on_ids = "[%d]" % a_id
    db_session.flush()
    captured: list = []
    monkeypatch.setattr(svc, "_request_with_target_policy", _fake_request(captured))
    with pytest.raises(ValueError):
        svc.execute_api_case(db_session, a_id, project_id=1)


def test_no_deps_single_request(db_session, monkeypatch) -> None:
    main_id = _seed(db_session, endpoint="https://api.test/plain", title="plain")
    captured: list = []
    monkeypatch.setattr(svc, "_request_with_target_policy", _fake_request(captured))
    r = svc.execute_api_case(db_session, main_id, project_id=1)
    assert r["all_pass"] is True
    assert len(captured) == 1