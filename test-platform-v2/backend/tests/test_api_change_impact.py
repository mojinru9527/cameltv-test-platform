"""接口变更影响分析服务测试（C-API-AUTO-002）。

覆盖：
- 新增/删除/修改/未变化接口分类
- 高/中影响级别判定
- 变更接口匹配用例库受影响用例
- Markdown 报告渲染
- 路由端点（新旧 spec 对比）
"""

from __future__ import annotations

from app.models.test_case import TestCase
from app.services import api_change_impact_service as acis


def _spec(endpoints: list[dict]) -> dict:
    paths: dict = {}
    for ep in endpoints:
        method = ep["method"].lower()
        detail: dict = {"summary": ep.get("summary", "")}
        if ep.get("request_schema"):
            detail["requestBody"] = {
                "content": {"application/json": {"schema": ep["request_schema"]}}
            }
        if ep.get("response_schema"):
            detail["responses"] = {"200": {"description": "ok"}}
        paths.setdefault(ep["path"], {})[method] = detail
    return {"openapi": "3.0.0", "info": {"title": "t", "version": "1"}, "paths": paths}


def test_classify_added_removed_modified():
    """新增/删除/修改/未变化分类正确。"""
    old = _spec(
        [
            {"method": "GET", "path": "/api/v1/matches", "summary": "比赛列表"},
            {
                "method": "POST",
                "path": "/api/v1/predict",
                "summary": "预测",
                "request_schema": {"type": "object"},
            },
        ]
    )
    new = _spec(
        [
            {"method": "GET", "path": "/api/v1/matches", "summary": "比赛列表"},
            {
                "method": "POST",
                "path": "/api/v1/predict",
                "summary": "预测",
                "request_schema": {
                    "type": "object",
                    "properties": {"amount": {"type": "integer"}},
                },
            },
            {
                "method": "GET",
                "path": "/api/v1/basketball/matches",
                "summary": "篮球比赛",
            },
        ]
    )
    changes = acis._spec_diff(
        acis._extract_endpoints(old), acis._extract_endpoints(new)
    )
    by_path = {c["path"]: c for c in changes}
    # matches 未变化 → 不出现在变更清单
    assert "/api/v1/matches" not in by_path
    # predict 修改（request_schema 变更）→ HIGH
    assert by_path["/api/v1/predict"]["change_type"] == acis.CHANGE_MODIFIED
    assert by_path["/api/v1/predict"]["impact"] == acis.IMPACT_HIGH
    # basketball 新增
    assert by_path["/api/v1/basketball/matches"]["change_type"] == acis.CHANGE_ADDED


def test_removed_is_high_impact():
    """接口删除 → HIGH。"""
    old = _spec([{"method": "DELETE", "path": "/api/v1/legacy", "summary": "旧接口"}])
    new = _spec([])
    changes = acis._spec_diff(
        acis._extract_endpoints(old), acis._extract_endpoints(new)
    )
    assert len(changes) == 1
    assert changes[0]["change_type"] == acis.CHANGE_REMOVED
    assert changes[0]["impact"] == acis.IMPACT_HIGH


def test_match_cases_finds_affected(db_session):
    """变更接口能匹配到用例库中对应 API 用例。"""
    db_session.add(
        TestCase(
            project_id=1,
            title="比赛列表用例",
            case_type="api",
            module="match",
            api_method="GET",
            api_endpoint="/api/v1/matches",
            priority="P0",
        )
    )
    db_session.add(
        TestCase(
            project_id=1,
            title="预测用例",
            case_type="api",
            module="predict",
            api_method="POST",
            api_endpoint="/api/v1/predict",
            priority="P1",
        )
    )
    db_session.add(
        TestCase(
            project_id=1,
            title="无关用例",
            case_type="api",
            module="other",
            api_method="GET",
            api_endpoint="/api/v1/other",
            priority="P2",
        )
    )
    db_session.commit()

    old = _spec([{"method": "GET", "path": "/api/v1/matches", "summary": "比赛列表"}])
    new = _spec(
        [
            {
                "method": "GET",
                "path": "/api/v1/matches",
                "summary": "比赛列表",
                "request_schema": {"type": "object"},
            },
        ]
    )
    result = acis.analyze_openapi_change(db_session, 1, old, new)
    assert result["stats"]["modified"] == 1
    assert result["stats"]["affected_case_count"] >= 1
    # 受影响用例 key 应为 "GET /api/v1/matches"
    affected = result["affected_cases"].get("GET /api/v1/matches", [])
    assert any(c["title"] == "比赛列表用例" for c in affected)


def test_markdown_render(db_session):
    """Markdown 报告渲染包含关键章节。"""
    old = _spec([{"method": "GET", "path": "/api/v1/a", "summary": "A"}])
    new = _spec(
        [
            {
                "method": "GET",
                "path": "/api/v1/a",
                "summary": "A",
                "request_schema": {"type": "object"},
            }
        ]
    )
    result = acis.analyze_openapi_change(db_session, 1, old, new)
    md = acis.changes_to_markdown(result)
    assert "# 接口变更影响分析报告" in md
    assert "## 变更清单" in md
    assert "modified" in md


def test_route_analyze_change_impact(client, db_session, auth_headers):
    """路由端点：POST /api/v1/apitest/cases/change-impact。"""

    old = _spec([{"method": "GET", "path": "/api/v1/matches", "summary": "比赛列表"}])
    new = _spec(
        [
            {
                "method": "GET",
                "path": "/api/v1/matches",
                "summary": "比赛列表",
                "request_schema": {"type": "object"},
            },
            {"method": "GET", "path": "/api/v1/new", "summary": "新接口"},
        ]
    )

    resp = client.post(
        "/api/v1/apitest/cases/change-impact",
        json={"old_spec": old, "new_spec": new},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    assert data["stats"]["added"] == 1
    assert data["stats"]["modified"] == 1
