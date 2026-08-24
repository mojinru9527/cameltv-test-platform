"""A组·参数真实化回归测试（Batch A：example/default/enum 保留与优先级）。

对应 QA 根因（blackbox-platform-modules-qa-report.md §4.2.1 / §8.2）：
- 导入丢失参数 example/enum/default（openapi_import_service.py:320-325）
- 生成/调试样本值产出占位假数据（_sample_value_for_prop / buildSampleBody）
- 生成用例断言缺业务码/核心字段
- preconditions 为硬编码空话
"""
from __future__ import annotations

import json

import pytest


# ═══════════════════════════════════════════════════════
# 1. OpenAPI 导入：参数保留 example/default/enum
# ═══════════════════════════════════════════════════════

class TestImportParamsPreserved:
    def test_oas3_query_param_keeps_example_default_enum(self):
        """OAS3 内联 schema 参数：example/default/enum 必须进入 request_schema.query。"""
        from app.services.openapi_import_service import _extract_endpoints

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T5", "version": "1.0.0"},
            "paths": {
                "/ee/sports_live/home_match": {
                    "get": {
                        "tags": ["sports-live-controller"],
                        "summary": "首页赛事",
                        "parameters": [
                            {
                                "name": "day",
                                "in": "query",
                                "required": True,
                                "schema": {
                                    "type": "string",
                                    "format": "date",
                                    "example": "20260615",
                                    "default": "20260101",
                                    "enum": ["20260615", "20260101"],
                                },
                            },
                            {
                                "name": "sort",
                                "in": "query",
                                "schema": {
                                    "type": "string",
                                    "enum": ["desc", "asc"],
                                    "default": "desc",
                                },
                            },
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        endpoints = _extract_endpoints(spec)
        assert len(endpoints) == 1
        query = endpoints[0]["request_schema"].get("query", [])
        by_name = {p["name"]: p for p in query}
        assert by_name["day"]["example"] == "20260615"
        assert by_name["day"]["default"] == "20260101"
        assert by_name["day"]["enum"] == ["20260615", "20260101"]
        # 真实契约值（example）不再被丢弃
        assert by_name["sort"]["default"] == "desc"
        assert by_name["sort"]["enum"] == ["desc", "asc"]

    def test_ref_parameter_resolved_and_preserved(self):
        """components/parameters 的 $ref 参数也必须解析并保留 example。"""
        from app.services.openapi_import_service import _extract_endpoints

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T5", "version": "1.0.0"},
            "components": {
                "parameters": {
                    "AppCodeParam": {
                        "name": "appCode",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "example": "D04B29D6B957CD44DC5F9894189380B8"},
                    }
                }
            },
            "paths": {
                "/account-service/login/anonymous": {
                    "post": {
                        "tags": ["auth"],
                        "summary": "匿名登录",
                        "parameters": [{"$ref": "#/components/parameters/AppCodeParam"}],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        endpoints = _extract_endpoints(spec)
        assert len(endpoints) == 1
        query = endpoints[0]["request_schema"].get("query", [])
        assert query, "$ref 参数不应丢失"
        app_code = query[0]
        assert app_code["name"] == "appCode"
        assert app_code["example"] == "D04B29D6B957CD44DC5F9894189380B8"

    def test_request_body_ref_resolved(self):
        """OAS3 requestBody $ref 解析后 properties/example 齐备。"""
        from app.services.openapi_import_service import _extract_endpoints

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T5", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "FollowConf": {
                        "type": "object",
                        "properties": {
                            "formKey": {"type": "string", "example": "sport_live_follow_conf"},
                        },
                        "required": ["formKey"],
                    }
                },
                "requestBodies": {
                    "FollowConfBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/FollowConf"}}
                        }
                    }
                },
            },
            "paths": {
                "/web/getDataById": {
                    "post": {
                        "tags": ["config"],
                        "summary": "按 id 取配置",
                        "requestBody": {"$ref": "#/components/requestBodies/FollowConfBody"},
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        endpoints = _extract_endpoints(spec)
        assert len(endpoints) == 1
        body = endpoints[0]["request_schema"].get("body", {})
        props = body.get("properties", {})
        assert "formKey" in props
        assert props["formKey"].get("example") == "sport_live_follow_conf"


# ═══════════════════════════════════════════════════════
# 2. 样本值优先级：example → default → enum[0]
# ═══════════════════════════════════════════════════════

class TestSampleValuePriority:
    def test_example_wins(self):
        from app.services.api_case_generation_service import _sample_value_for_prop
        assert _sample_value_for_prop({"type": "string", "example": "real-20260615"}) == "real-20260615"

    def test_default_when_no_example(self):
        from app.services.api_case_generation_service import _sample_value_for_prop
        assert _sample_value_for_prop({"type": "string", "default": "def-1", "enum": ["a", "b"]}) == "def-1"

    def test_enum_when_no_example_default(self):
        from app.services.api_case_generation_service import _sample_value_for_prop
        assert _sample_value_for_prop({"type": "string", "enum": ["desc", "asc"]}) == "desc"

    def test_falsy_example_zero_still_respected(self):
        from app.services.api_case_generation_service import _sample_value_for_prop
        assert _sample_value_for_prop({"type": "integer", "example": 0}) == 0
        assert _sample_value_for_prop({"type": "boolean", "example": False}) is False

    def test_no_contract_still_type_fallback(self):
        from app.services.api_case_generation_service import _sample_value_for_prop
        assert _sample_value_for_prop({"type": "string", "minLength": 1}) == "ttt"


# ═══════════════════════════════════════════════════════
# 3. preconditions 真实契约描述
# ═══════════════════════════════════════════════════════

class TestPreconditionsReal:
    def test_preconditions_contains_auth_headers_required_params_and_summary(self):
        from app.services.api_case_generation_service import _describe_preconditions

        endpoint = {
            "auth_required": True,
            "summary": "首页赛事",
            "request_schema": {
                "header": [{"name": "clientip", "required": True}],
                "query": [{"name": "day", "required": True}, {"name": "optional", "required": False}],
                "path": [{"name": "id", "required": True}],
            },
        }
        text = _describe_preconditions("GET", "/ee/sports_live/home_match", endpoint)
        assert "GET /ee/sports_live/home_match 可访问" in text
        assert "接口需要认证" in text
        assert "clientip" in text
        assert "day" in text
        assert "optional" not in text
        assert "首页赛事" in text

    def test_generated_case_preconditions_not_hardcoded(self):
        """生成用例的 preconditions 需含契约真实描述（含接口说明），非「可访问」空话。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "camel-service",
            "module": "sports-live-controller",
            "method": "GET",
            "path": "/ee/sports_live/home_match",
            "summary": "首页赛事接口",
            "auth_required": True,
            "request_schema": {
                "header": [{"name": "clientip", "required": True}],
                "query": [{"name": "day", "required": True, "example": "20260615"}],
            },
            "response_schema": {
                "properties": {
                    "status": {"type": "integer", "example": 200},
                    "data": {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}},
                }
            },
        }
        cases = generate_cases_from_endpoint(endpoint, templates=["basic"])
        positive = cases[0]
        pre = positive["preconditions"]
        assert "首页赛事接口" in pre
        assert "GET /ee/sports_live/home_match 可访问" in pre
        assert "day" in pre


# ═══════════════════════════════════════════════════════
# 4. 生成用例断言强制「2xx + 业务码 + 核心字段」
# ═══════════════════════════════════════════════════════

class TestGeneratedAssertionsTriple:
    def _endpoint(self, response_schema: dict | None = None):
        return {
            "service_name": "camel-service",
            "module": "sports-live-controller",
            "method": "GET",
            "path": "/ee/sports_live/home_match",
            "summary": "首页赛事接口",
            "request_schema": {
                "query": [{"name": "day", "required": True, "example": "20260615"}],
            },
            "response_schema": response_schema or {
                "properties": {
                    "status": {"type": "integer", "example": 200},
                    "data": {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}},
                }
            },
        }

    def test_positive_case_has_status_business_code_core_field_assertions(self):
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        cases = generate_cases_from_endpoint(self._endpoint(), templates=["basic"])
        assert cases
        assertions = cases[0]["api_assertions"]
        types = {a.get("type") for a in assertions}
        assert "status_code" in types, "必须保留 2xx 状态码断言"
        jsonpath_rules = {a.get("path"): a for a in assertions if a.get("type") == "jsonpath"}
        assert "$.status" in jsonpath_rules, "必须含业务码断言"
        assert jsonpath_rules["$.status"].get("operator") == "eq"
        assert jsonpath_rules["$.status"].get("expected") == 200
        assert "$.data.id" in jsonpath_rules, "必须含核心字段断言"

    def test_business_code_assertion_uses_contract_example(self):
        from app.services.api_case_generation_service import _contract_business_assertions

        endpoint = self._endpoint()
        asserts = _contract_business_assertions(endpoint)
        status_rule = next(a for a in asserts if a.get("path") == "$.status")
        assert status_rule["expected"] == 200

    def test_empty_response_schema_returns_empty_contract_asserts(self):
        """无响应契约结构时不虚构断言（调用方保留 2xx），避免用例注定失败。"""
        from app.services.api_case_generation_service import _contract_business_assertions

        assert _contract_business_assertions({"response_schema": {}}) == []
        assert _contract_business_assertions({"response_schema": "{}"}) == []

    def test_contract_asserts_survive_str_response_schema(self):
        """DB 返回字符串 response_schema 也能解析（兼容 str/dict 两种形态）。"""
        from app.services.api_case_generation_service import _contract_business_assertions

        endpoint = {
            "response_schema": json.dumps(
                {
                    "properties": {
                        "code": {"type": "integer", "example": 0},
                        "result": {"type": "object", "properties": {"id": {"type": "integer"}}},
                    }
                }
            )
        }
        asserts = _contract_business_assertions(endpoint)
        assert any(a.get("path") == "$.code" for a in asserts)
        assert any(a.get("path") == "$.result.id" for a in asserts)


# ═══════════════════════════════════════════════════════
# 5. release 口径衔接：生成断言（$.status 业务码）可通过门禁
# ═══════════════════════════════════════════════════════

class TestReleaseGateAlignment:
    def test_gate_accepts_status_business_code_path(self):
        """生成器按契约产出的 $.status 业务码断言应被 release 门禁识别（对齐网关契约）。"""
        from app.services.api_execution_service import _assertion_contract_error

        err = _assertion_contract_error(
            [
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "jsonpath", "path": "$.status", "operator": "eq", "expected": 200},
                {"type": "jsonpath", "path": "$.data.id", "operator": "exists"},
            ],
            require_release_assertions=True,
        )
        assert err == ""

    def test_gate_still_rejects_missing_business_code(self):
        """不写业务码断言的 approved 用例仍被门禁拦截（不放松既有口径）。"""
        from app.services.api_execution_service import _assertion_contract_error

        err = _assertion_contract_error(
            [
                {"type": "status_code", "expected": 200, "operator": "gte"},
                {"type": "jsonpath", "path": "$.data.id", "operator": "exists"},
            ],
            require_release_assertions=True,
        )
        assert "business-code" in err
