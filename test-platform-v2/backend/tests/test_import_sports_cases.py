"""Batch 125 sports-case importer regression tests."""
from __future__ import annotations

import json

from scripts.import_sports_cases import (
    response_contains_exact_case,
    stable_case_id,
    to_create,
)


def _base_case(**overrides):
    case = {
        "id": "TC-001",
        "title": "预测提交成功",
        "domain": "体育-用户端-功能",
        "module": "PC-web/赛事详情/预测Pick",
        "priority": "P0",
        "client_scope": ["pc", "app", "mweb"],
        "steps": [{"step": 1, "desc": "提交预测", "expected": "仅生成一条记录"}],
    }
    case.update(overrides)
    return case


def test_stable_case_id_is_repeatable_and_unique_across_source_modules():
    case = _base_case()

    first = stable_case_id(case, "用户端/赛事详情")
    repeated = stable_case_id(case, "用户端/赛事详情")
    other_module = stable_case_id(case, "用户端/首页")

    assert first == repeated
    assert first.startswith("SP-B125-")
    assert first != other_module


def test_stable_case_id_preserves_existing_globally_scoped_id():
    case = _base_case(case_id="SP-PC-PICK-001")
    assert stable_case_id(case, "用户端/赛事详情") == "SP-PC-PICK-001"


def test_to_create_aggregates_terminal_wrappers_and_preserves_metadata():
    payload = to_create(_base_case(), "用户端/赛事详情")

    assert payload["domain"] == "用户端/赛事详情"
    assert payload["module"] == "预测Pick"
    assert payload["priority"] == "P0"
    assert payload["positive_negative"] == "positive"
    assert set(json.loads(payload["tags"])) >= {
        "端:PC Web",
        "端:安卓/iOS",
        "端:移动 Web",
    }


def test_to_create_uses_inventory_surface_for_ambiguous_shared_domain():
    user_payload = to_create(
        _base_case(domain="商城", module="商品列表"),
        "用户端/商城",
    )
    admin_payload = to_create(
        _base_case(domain="商城", module="商品管理"),
        "运营后台/商城",
    )

    assert user_payload["domain"] == "用户端/商城"
    assert user_payload["module"] == "商品列表"
    assert admin_payload["domain"] == "运营后台/商城"
    assert admin_payload["module"] == "商品管理"


def test_to_create_keeps_different_historical_domain_as_child_module():
    payload = to_create(
        _base_case(domain="数据页", module="赛况统计"),
        "用户端/赛事详情",
    )

    assert payload["domain"] == "用户端/赛事详情"
    assert payload["module"] == "数据页/赛况统计"


def test_response_contains_exact_case_does_not_trust_unfiltered_total():
    response_data = {
        "data": {
            "total": 977,
            "items": [{"case_id": "SOME-OTHER-CASE"}],
        }
    }

    assert not response_contains_exact_case(response_data, "SP-B125-EXPECTED")
    response_data["data"]["items"].append({"case_id": "SP-B125-EXPECTED"})
    assert response_contains_exact_case(response_data, "SP-B125-EXPECTED")


def test_to_create_infers_missing_negative_and_boundary_metadata():
    negative = to_create(
        _base_case(title="未登录用户提交预测被拦截", positive_negative=""),
        "用户端/预测Pick",
    )
    boundary = to_create(
        _base_case(title="预测金额达到单场上限边界", positive_negative=""),
        "用户端/预测Pick",
    )

    assert negative["positive_negative"] == "negative"
    assert negative["case_design_method"] == "错误推测"
    assert boundary["positive_negative"] == "boundary"
    assert boundary["case_design_method"] == "边界值分析"


def test_to_create_preserves_interface_action_as_executable_step_description():
    payload = to_create(
        _base_case(steps=[{"step": 1, "action": "发送 GET /matches", "expected": "返回 200"}]),
        "用户端/赛事详情",
    )

    assert json.loads(payload["steps"])[0] == {
        "step": 1,
        "desc": "发送 GET /matches",
        "expected": "返回 200",
    }
