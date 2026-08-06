"""Batch 107 — 接口用例生成「测试考虑点」全量固化单测。

覆盖：9 类新模板（smoke/scenario/extra_param/security_ext/performance_low/data_test/
stability/compatibility/monitoring）+ 真实样本响应结构断言 + 默认模板集。
"""

from __future__ import annotations

from app.services.api_case_generation_service import (
    generate_cases_from_endpoint,
    generate_cases_from_real_sample,
)


def _endpoint(method: str = "POST", schema: dict | None = None) -> dict:
    return {
        "service_name": "camel-service",
        "module": "资讯",
        "method": method,
        "path": "/camel-service/ee/news/list_visible",
        "summary": "资讯列表",
        "request_schema": schema or {
            "body": {
                "properties": {
                    "page": {"type": "integer", "minimum": 1},
                    "size": {"type": "integer", "minimum": 1},
                    "locale": {"type": "string", "enum": ["en", "zh"]},
                },
                "required": ["page", "size"],
            }
        },
    }


def _real_sample() -> dict:
    return {
        "body": {
            "sorts": [{"key": "top", "sort": "desc"}, {"key": "updateTime", "sort": "desc"}],
            "page": 2,
            "size": 30,
            "queryList": [{"isOrNotRange": 0, "key": "language", "type": "String", "value1": "0", "value2": ""}],
            "locale": "en",
        },
        "source": "生产 XHR 抓取",
        "response_envelope_keys": ["traceId", "timestamp", "status", "data", "msg"],
        "data_keys": ["records", "total", "size", "current", "pages"],
        "record_count": 30,
        "first_record_fields": ["id", "news_id", "sport_live_news_title", "language", "top"],
        "assertion_design_hints": [
            "业务状态码 status 校验（0=成功）",
            "data.current/page 与请求 page 一致",
            "data.records 数量 <= size(30)",
        ],
    }


def _scenario_tags(cases: list[dict]) -> set[str]:
    tags: set[str] = set()
    for c in cases:
        for t in c.get("tags", []):
            if t.startswith("scenario:"):
                tags.add(t.split(":", 1)[1])
    return tags


def test_default_templates_include_all_15() -> None:
    """默认模板集包含全部 15 项（含 Batch 107 九类新模板）。"""
    cases = generate_cases_from_endpoint(_endpoint())
    scenarios = _scenario_tags(cases)
    for s in ("smoke", "scenario", "extra_param", "security_ext", "performance_low",
              "data_test", "stability", "compatibility", "monitoring"):
        assert s in scenarios, f"缺少新模板场景 {s}"


def test_smoke_case_has_response_structure_when_real_sample() -> None:
    """冒烟用例断言含状态码 + 响应结构（真实样本驱动）。"""
    cases = generate_cases_from_endpoint(_endpoint(), templates=["smoke"], real_samples=[_real_sample()])
    smoke = [c for c in cases if any(t == "scenario:smoke" for t in c.get("tags", []))]
    assert len(smoke) == 1
    types = {a.get("type") for a in smoke[0].get("api_assertions", [])}
    assert "status_code" in types and "response_structure" in types


def test_scenario_case_notes_related_info_or_pending() -> None:
    """场景用例标注接口串联；无关联信息时提示待关联。"""
    cases = generate_cases_from_endpoint(_endpoint(), templates=["scenario"])
    scenario = [c for c in cases if any(t == "scenario:scenario" for t in c.get("tags", []))]
    assert len(scenario) == 1
    assert "场景测试" in scenario[0]["title"]
    assert "接口串联" in scenario[0]["expected_result"] or "关联" in scenario[0]["test_data_note"]


def test_extra_param_case_adds_unknown_field() -> None:
    """增加不存在的参数用例：body 含契约外字段。"""
    cases = generate_cases_from_endpoint(_endpoint(), templates=["extra_param"])
    extra = [c for c in cases if any(t == "scenario:extra_param" for t in c.get("tags", []))]
    assert len(extra) == 1
    body = extra[0].get("api_body", "")
    assert "__unknown_extra_field__" in body


def test_security_ext_cases_for_write_and_read() -> None:
    """安全扩展：越权/HTTPS 全方法；CSRF 仅写方法。"""
    post_cases = generate_cases_from_endpoint(_endpoint("POST"), templates=["security_ext"])
    post_titles = [c["title"] for c in post_cases]
    assert any("越权" in t for t in post_titles)
    assert any("加密" in t for t in post_titles)
    assert any("CSRF" in t for t in post_titles)

    get_cases = generate_cases_from_endpoint(_endpoint("GET"), templates=["security_ext"])
    get_titles = [c["title"] for c in get_cases]
    assert any("越权" in t for t in get_titles)
    assert not any("CSRF" in t for t in get_titles)


def test_performance_low_priority() -> None:
    """性能模板 P2/P3 低优先级。"""
    cases = generate_cases_from_endpoint(_endpoint(), templates=["performance_low"])
    perf = [c for c in cases if any(t == "scenario:performance_low" for t in c.get("tags", []))]
    assert len(perf) == 2
    priorities = {c["priority"] for c in perf}
    assert priorities <= {"P2", "P3"}


def test_data_test_has_db_check_assertion() -> None:
    """数据测试断言含 db_check；写方法多一条专业数据用例。"""
    cases = generate_cases_from_endpoint(_endpoint("POST"), templates=["data_test"])
    data = [c for c in cases if any(t == "scenario:data_test" for t in c.get("tags", []))]
    assert all(any(a.get("type") == "db_check" for a in c.get("api_assertions", [])) for c in data)
    assert len(data) == 2


def test_stability_compatibility_monitoring() -> None:
    """稳定性（429 断言）/兼容性（compat_check）/监控（monitoring）模板。"""
    stability = [c for c in generate_cases_from_endpoint(_endpoint(), templates=["stability"])
                 if any(t == "scenario:stability" for t in c.get("tags", []))]
    assert any(a.get("expected") == 429 for c in stability for a in c.get("api_assertions", []))

    compat = [c for c in generate_cases_from_endpoint(_endpoint(), templates=["compatibility"])
              if any(t == "scenario:compatibility" for t in c.get("tags", []))]
    assert any(a.get("type") == "compat_check" for c in compat for a in c.get("api_assertions", []))

    monitoring = [c for c in generate_cases_from_endpoint(_endpoint(), templates=["monitoring"])
                  if any(t == "scenario:monitoring" for t in c.get("tags", []))]
    assert len(monitoring) == 2
    assert all(any(a.get("type") == "monitoring" for a in c.get("api_assertions", [])) for c in monitoring)


def test_real_sample_response_structure_assertions() -> None:
    """真实样本生成：正向用例断言升级 + 返回值结构校验用例 + 冒烟用例。"""
    cases = generate_cases_from_real_sample(_endpoint(), _real_sample())
    scenarios = _scenario_tags(cases)
    assert "response_structure" in scenarios
    assert "smoke" in scenarios

    positive = next(c for c in cases if any(t == "scenario:positive" for t in c.get("tags", [])))
    types = {a.get("type") for a in positive.get("api_assertions", [])}
    assert "response_structure" in types, "正向基线断言应含响应结构"

    resp_case = next(c for c in cases if any(t == "scenario:response_structure" for t in c.get("tags", [])))
    resp_types = {a.get("type") for a in resp_case.get("api_assertions", [])}
    assert "response_structure" in resp_types
    hints = [a for a in resp_case.get("api_assertions", []) if a.get("type") == "response_structure" and a.get("note")]
    assert hints, "断言应包含 assertion_design_hints 提示"


def test_max_case_limit_still_applies() -> None:
    """全量默认模板不超数量上限。"""
    cases = generate_cases_from_endpoint(_endpoint())
    assert len(cases) <= 200
