"""手工用例 → API 用例泛化服务测试（C-API-AUTO-004）。

覆盖：
- 手工用例选取（含模块过滤）
- 业务动词识别（查询/新增/修改/删除）
- 接口资产匹配（方法 + 路径关键词）
- 规则模式用例生成（骨架/断言/路径参数替换）
- 未匹配场景（无接口资产/无动词 → unmatched）
- 入库
- 路由端点
"""

from __future__ import annotations

import json

from app.models.api_asset import ApiEndpoint
from app.models.test_case import TestCase
from app.services import api_generalization_service as ags


def _mk_manual(db, project_id, title, module="match", steps=None, case_type="manual"):
    tc = TestCase(
        project_id=project_id,
        title=title,
        module=module,
        case_type=case_type,
        priority="P1",
        steps=json.dumps(
            steps or [{"step": 1, "action": "查看比赛列表", "expected": "展示列表"}]
        ),
        expected_result="成功",
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


def _mk_endpoint(db, project_id, method, path, module="match"):
    ep = ApiEndpoint(
        project_id=project_id,
        service_id=1,
        module=module,
        method=method,
        path=path,
        summary=f"{method} {path}",
        request_schema="{}",
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def test_pick_manual_cases_filters_module(db_session):
    """按模块选取手工用例，排除 API/UI 类型。"""
    _mk_manual(db_session, 1, "A", module="match")
    _mk_manual(db_session, 1, "B", module="news")
    _mk_manual(db_session, 1, "C", module="match", case_type="api")

    match_cases = ags.pick_manual_cases(db_session, 1, module="match")
    assert [c["title"] for c in match_cases] == ["A"]
    all_cases = ags.pick_manual_cases(db_session, 1)
    assert len(all_cases) == 2  # C 是 api 类型，排除


def test_detect_verb():
    """从步骤文本识别业务操作动词。"""
    assert ags._detect_verb([{"action": "查询比赛列表"}]) == "查询"
    assert ags._detect_verb([{"action": "新增用户"}]) == "新增"
    assert ags._detect_verb([{"action": "删除订单"}]) == "删除"
    assert ags._detect_verb([{"action": "修改资料"}]) == "修改"
    assert ags._detect_verb([{"action": "随意操作"}]) == ""


def test_match_endpoint_by_method_and_keyword():
    """按动词方法 + 路径关键词匹配接口资产。"""
    endpoints = [
        {"method": "GET", "path": "/api/v1/matches"},
        {"method": "POST", "path": "/api/v1/predict"},
    ]
    # 查询比赛 → GET /matches
    ep = ags._match_endpoint(endpoints, "查询", "比赛列表查询")
    assert ep and ep["path"] == "/api/v1/matches"
    # 无关键词 → 方法匹配兜底
    ep2 = ags._match_endpoint(endpoints, "删除", "清理数据")
    assert ep2 and ep2["method"] == "GET"
    # 无接口 → None
    assert ags._match_endpoint([], "查询", "x") is None


def test_rule_case_generation_basic(db_session):
    """规则模式生成 API 用例骨架。"""
    manual = _mk_manual(
        db_session,
        1,
        "比赛列表查询",
        module="match",
        steps=[{"step": 1, "action": "查询比赛列表", "expected": "展示列表"}],
    )
    _mk_endpoint(db_session, 1, "GET", "/api/v1/matches", module="match")

    result = ags.generalize_cases(db_session, 1, module="match", mode="rule")
    assert result["total_manual"] == 1
    assert result["generated_count"] == 1
    case = result["generated"][0]
    assert case["api_method"] == "GET"
    assert case["api_endpoint"] == "/api/v1/matches"
    assert case["case_type"] == "api"
    assert case["api_assertions"]  # 含状态码断言
    assert "[泛化]" in case["title"]
    assert f"#{manual.id}" in case["preconditions"]


def test_rule_case_path_param_replacement(db_session):
    """需要路径参数的操作（详情/删除）替换 {id} 占位。"""
    _mk_manual(
        db_session,
        1,
        "订单详情查看",
        module="order",
        steps=[{"step": 1, "action": "查看订单详情", "expected": "展示详情"}],
    )
    _mk_endpoint(db_session, 1, "GET", "/api/v1/orders/{id}", module="order")

    result = ags.generalize_cases(db_session, 1, module="order")
    case = result["generated"][0]
    assert case["api_endpoint"] == "/api/v1/orders/1"


def test_unmatched_reported(db_session):
    """无接口资产时进入 unmatched，不报错。"""
    _mk_manual(
        db_session,
        1,
        "比赛列表查询",
        module="match",
        steps=[{"step": 1, "action": "查询比赛列表", "expected": "展示列表"}],
    )
    result = ags.generalize_cases(db_session, 1, module="match")
    assert result["generated_count"] == 0
    assert len(result["unmatched"]) == 1
    assert "未匹配到接口资产" in result["unmatched"][0]["reason"]


def test_create_generated_cases_persists(db_session):
    """泛化用例可入库并返回 ID。"""
    _mk_manual(
        db_session,
        1,
        "比赛列表查询",
        module="match",
        steps=[{"step": 1, "action": "查询比赛列表", "expected": "展示列表"}],
    )
    _mk_endpoint(db_session, 1, "GET", "/api/v1/matches", module="match")

    result = ags.generalize_cases(db_session, 1, module="match")
    ids = ags.create_generated_cases(db_session, 1, result["generated"])
    assert len(ids) == 1
    saved = db_session.get(TestCase, ids[0])
    assert saved is not None
    assert saved.case_type == "api"
    assert saved.api_endpoint == "/api/v1/matches"


def test_ai_mode_without_key_falls_back(db_session, monkeypatch):
    """AI 模式未配置 key 时降级为 rule 模式。"""
    from types import SimpleNamespace

    from app.services.ai_config_service import AIProviderUnconfiguredError

    monkeypatch.setattr(
        ags.ai_config_service,
        "resolve",
        lambda db, project_id: (_ for _ in ()).throw(AIProviderUnconfiguredError()),
    )
    _mk_manual(
        db_session,
        1,
        "比赛列表查询",
        module="match",
        steps=[{"step": 1, "action": "查询比赛列表", "expected": "展示列表"}],
    )
    _mk_endpoint(db_session, 1, "GET", "/api/v1/matches", module="match")

    result = ags.generalize_cases(db_session, 1, module="match", mode="ai")
    assert result["mode"] == "rule"  # 无 key 时静默降级
    assert result["generated_count"] == 1


def test_route_generalize_from_manual(client, db_session, auth_headers):
    """路由端点：POST /api/v1/apitest/cases/generalize-from-manual。"""
    _mk_manual(
        db_session,
        1,
        "比赛列表查询",
        module="match",
        steps=[{"step": 1, "action": "查询比赛列表", "expected": "展示列表"}],
    )
    _mk_endpoint(db_session, 1, "GET", "/api/v1/matches", module="match")

    resp = client.post(
        "/api/v1/apitest/cases/generalize-from-manual",
        json={"module": "match", "mode": "rule"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    assert data["total_manual"] == 1
    assert data["generated_count"] == 1
    assert data["mode"] == "rule"
    assert data["generated"][0]["api_endpoint"] == "/api/v1/matches"


def test_route_rejects_invalid_mode(client, auth_headers):
    """非法 mode 返回 400。"""
    resp = client.post(
        "/api/v1/apitest/cases/generalize-from-manual",
        json={"mode": "magic"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
