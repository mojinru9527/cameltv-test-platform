"""A组补强回归：response schema $ref 解析 + 用例执行 URL 服务前缀（C203-2 扩展验证发现的两个缺口）。

背景：camel-service 恢复后对「接口用例链路」做端到端验证发现：
1. 导入的 response_schema 存未解析 $ref（#/components/schemas/...）→ 生成用例缺业务码/核心字段断言；
2. 生成用例 api_endpoint 无服务前缀，execute_api_case 直接 base+path → 网关 404。
"""
from __future__ import annotations

import json


class TestResponseSchemaRefResolution:
    SPEC = {
        "openapi": "3.0.0",
        "info": {"title": "T5", "version": "1.0.0"},
        "components": {
            "schemas": {
                "EeResultGroupedMatchResp": {
                    "type": "object",
                    "properties": {
                        "traceId": {"type": "string"},
                        "timestamp": {"type": "integer"},
                        "status": {"type": "integer", "example": 200},
                        "data": {"$ref": "#/components/schemas/GroupedMatchResp"},
                        "msg": {"type": "string"},
                    },
                },
                "GroupedMatchResp": {
                    "type": "object",
                    "properties": {
                        "today": {"type": "string"},
                        "hot_group": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/GroupItem"},
                        },
                    },
                },
                "GroupItem": {
                    "type": "object",
                    "properties": {"competition": {"type": "object"}},
                },
            }
        },
        "paths": {
            "/ee/live/home_match": {
                "get": {
                    "tags": ["live-controller"],
                    "parameters": [
                        {"name": "day", "in": "query", "required": True,
                         "schema": {"type": "string", "example": "20260615"}},
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "*/*": {"schema": {"$ref": "#/components/schemas/EeResultGroupedMatchResp"}},
                            }
                        }
                    },
                }
            }
        },
    }

    def test_import_resolves_response_ref_and_nested_refs(self):
        from app.services.openapi_import_service import _extract_endpoints

        ep = _extract_endpoints(self.SPEC)[0]
        rs = ep["response_schema"]
        props = rs["schema"]["properties"]
        assert props["status"]["example"] == 200
        data_props = props["data"]["properties"]
        assert data_props["today"]["type"] == "string"
        assert data_props["hot_group"]["items"]["properties"]["competition"]["type"] == "object"

    def test_generated_case_gets_business_code_and_core_field_assertions(self):
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        ep = _extract_endpoints_of(self.SPEC)
        cases = generate_cases_from_endpoint(ep, templates=["basic"])
        jsonpath = {a.get("path") for a in cases[0]["api_assertions"] if a.get("type") == "jsonpath"}
        assert "$.status" in jsonpath, "必须含业务码断言"
        assert "$.data.today" in jsonpath, "必须含核心字段断言"
        status_rule = next(
            a for a in cases[0]["api_assertions"]
            if a.get("type") == "jsonpath" and a.get("path") == "$.status"
        )
        assert status_rule["operator"] == "eq" and status_rule["expected"] == 200


def _extract_endpoints_of(spec):
    from app.services.openapi_import_service import _extract_endpoints

    ep = _extract_endpoints(spec)[0]
    return {
        "service_name": "camel-service",
        "module": ep["module"],
        "method": ep["method"],
        "path": ep["path"],
        "summary": ep["summary"],
        "request_schema": ep["request_schema"],
        "response_schema": ep["response_schema"],
    }


class TestCaseExecutionUrl:
    def test_relative_endpoint_bound_to_service_gets_prefix(self, db_session):
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase
        from app.services.api_execution_service import _case_execution_url

        svc = ApiService(project_id=1, name="camel-service", display_name="camel-service")
        db_session.add(svc)
        db_session.flush()
        ep = ApiEndpoint(
            project_id=1, service_id=svc.id, method="GET", path="/ee/live/home_match",
        )
        db_session.add(ep)
        db_session.flush()
        case = TestCase(
            project_id=1, title="t", case_type="api", api_method="GET",
            api_endpoint="/ee/live/home_match", api_endpoint_id=ep.id,
        )
        db_session.add(case)
        db_session.commit()

        assert _case_execution_url(db_session, case) == "/camel-service/ee/live/home_match"

    def test_absolute_and_unbound_endpoints_unchanged(self, db_session):
        from app.models.test_case import TestCase
        from app.services.api_execution_service import _case_execution_url

        abs_case = TestCase(
            project_id=1, title="abs", case_type="api", api_method="GET",
            api_endpoint="https://example.test/health", api_endpoint_id=None,
        )
        rel_case = TestCase(
            project_id=1, title="rel", case_type="api", api_method="GET",
            api_endpoint="/api/v1/x", api_endpoint_id=None,
        )
        db_session.add_all([abs_case, rel_case])
        db_session.commit()

        assert _case_execution_url(db_session, abs_case) == "https://example.test/health"
        assert _case_execution_url(db_session, rel_case) == "/api/v1/x"

    def test_endpoint_already_prefixed_not_duplicated(self, db_session):
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase
        from app.services.api_execution_service import _case_execution_url

        svc = ApiService(project_id=1, name="camel-service", display_name="camel-service")
        db_session.add(svc)
        db_session.flush()
        ep = ApiEndpoint(project_id=1, service_id=svc.id, method="GET", path="/ee/x")
        db_session.add(ep)
        db_session.flush()
        case = TestCase(
            project_id=1, title="t2", case_type="api", api_method="GET",
            api_endpoint="/camel-service/ee/x", api_endpoint_id=ep.id,
        )
        db_session.add(case)
        db_session.commit()

        assert _case_execution_url(db_session, case) == "/camel-service/ee/x"
