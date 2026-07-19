"""Knife4j/Swagger doc URL import integration tests — preview, confirm, case generation.

Covers the full chain: discover → preview → confirm → generate cases.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════
# Swagger 2.0 body parameter extraction
# ═══════════════════════════════════════════════════════

class TestSwagger2BodyParam:
    """Verify Swagger 2.0 body parameters are extracted as requestBody."""

    def test_body_param_in_extracted_as_request_schema(self):
        """Swagger 2.0 parameter[in=body] → request_schema.body with properties."""
        from app.services.openapi_import_service import _extract_endpoints

        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy API", "version": "1.0.0"},
            "paths": {
                "/api/v1/users": {
                    "post": {
                        "tags": ["users"],
                        "summary": "创建用户",
                        "parameters": [
                            {
                                "name": "body",
                                "in": "body",
                                "required": True,
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "age": {"type": "integer"},
                                    },
                                    "required": ["username"],
                                },
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        endpoints = _extract_endpoints(spec)
        assert len(endpoints) == 1
        ep = endpoints[0]
        assert ep["method"] == "POST"
        assert ep["path"] == "/api/v1/users"

        body = ep["request_schema"].get("body", {})
        assert body.get("type") == "object"
        assert "username" in body.get("properties", {})
        assert "username" in body.get("required", [])
        assert "age" in body.get("properties", {})

    def test_body_param_resolves_ref(self):
        """Swagger 2.0 body $ref → resolved via spec #/definitions."""
        from app.services.openapi_import_service import _extract_endpoints

        spec = {
            "swagger": "2.0",
            "info": {"title": "Ref API"},
            "definitions": {
                "CreateUser": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                    },
                    "required": ["email"],
                }
            },
            "paths": {
                "/api/v1/users": {
                    "post": {
                        "tags": ["users"],
                        "summary": "创建用户",
                        "parameters": [
                            {
                                "name": "body",
                                "in": "body",
                                "required": True,
                                "schema": {"$ref": "#/definitions/CreateUser"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }

        endpoints = _extract_endpoints(spec)
        assert len(endpoints) == 1
        body = endpoints[0]["request_schema"].get("body", {})
        assert "email" in body.get("properties", {})


# ═══════════════════════════════════════════════════════
# Knife4j swagger_doc_url discovery → preview flow
# ═══════════════════════════════════════════════════════

MINIMAL_OAS3 = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "2.0.0"},
    "paths": {
        "/api/v1/login": {
            "post": {
                "tags": ["auth"],
                "summary": "用户登录",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "password": {"type": "string"},
                                },
                                "required": ["username", "password"],
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"token": {"type": "string"}},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/v1/health": {
            "get": {
                "tags": ["system"],
                "summary": "健康检查",
                "responses": {"200": {"description": "OK"}},
            }
        },
    },
}


class TestKnife4jImportServiceLayer:
    """Test import service with manual spec (no network calls)."""

    def test_preview_from_spec_returns_modules(self):
        """preview_openapi_import_with_db returns module summary."""
        from app.services.openapi_import_service import preview_openapi_import

        result = preview_openapi_import(MINIMAL_OAS3, project_id=1, service_name="test-svc")

        assert result["total_count"] == 2
        assert result["version"] == "2.0.0"
        assert len(result["endpoints"]) == 2

        # All endpoints have source="openapi"
        for ep in result["endpoints"]:
            assert ep["source"] == "openapi"

    def test_confirm_creates_batch_with_source_label(self, db_session):
        """confirm_openapi_import with source_type=swagger_doc_url → source=knife4j_import."""
        from app.services.openapi_import_service import confirm_openapi_import
        from app.models.api_asset import ApiEndpoint, ApiService

        result = confirm_openapi_import(
            db_session,
            MINIMAL_OAS3,
            project_id=1,
            service_name="knife4j-svc",
            source_ref="http://example.com/doc.html#/home",
            source_type="swagger_doc_url",
        )

        assert result["created_count"] == 2
        assert result["batch_id"] > 0

        # Verify all created endpoints have source=knife4j_import
        service = db_session.query(ApiService).filter_by(project_id=1, name="knife4j-svc").first()
        assert service is not None

        endpoints = db_session.query(ApiEndpoint).filter_by(project_id=1, service_id=service.id).all()
        assert len(endpoints) == 2
        for ep in endpoints:
            assert ep.source == "knife4j_import", f"Expected knife4j_import, got {ep.source}"

    def test_confirm_with_swagger_doc_url_stores_batch_source(self, db_session):
        """Batch record reflects source_type and source_ref."""
        from app.services.openapi_import_service import confirm_openapi_import
        from app.models.api_asset import ApiImportBatch

        doc_url = "http://example.com/swagger-ui/index.html"
        result = confirm_openapi_import(
            db_session,
            MINIMAL_OAS3,
            project_id=1,
            service_name="swagger-svc",
            source_ref=doc_url,
            source_type="swagger_doc_url",
        )

        batch = db_session.query(ApiImportBatch).filter_by(id=result["batch_id"]).first()
        assert batch is not None
        assert batch.source_type == "swagger_doc_url"
        assert batch.source_ref == doc_url
        assert batch.status == "completed"


# ═══════════════════════════════════════════════════════
# Case generation — security template
# ═══════════════════════════════════════════════════════

class TestSecurityTemplateInDefaults:
    """Verify 'security' template is included in code-default template list."""

    def test_default_templates_include_security(self):
        """generate_cases_from_endpoint defaults should include 'security'."""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        ep = {
            "service_name": "test",
            "module": "auth",
            "method": "POST",
            "path": "/api/v1/login",
            "summary": "登录",
            "request_schema": {
                "body": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                    },
                    "required": ["username", "password"],
                }
            },
        }

        cases = generate_cases_from_endpoint(ep)

        # Should include security cases (SQL injection, XSS per string field)
        security_cases = [
            c for c in cases
            if any("scenario:security" in t for t in (c.get("tags") or []))
        ]
        assert len(security_cases) > 0, (
            f"Expected security cases in defaults, got tags: "
            f"{sorted(set(t for c in cases for t in (c.get('tags') or [])))}"
        )

    def test_security_cases_have_sql_injection(self):
        """Security template generates SQL injection test cases."""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        ep = {
            "service_name": "test",
            "module": "users",
            "method": "POST",
            "path": "/api/v1/users",
            "summary": "创建用户",
            "request_schema": {
                "body": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["name"],
                }
            },
        }

        # Explicitly request only security template
        cases = generate_cases_from_endpoint(ep, templates=["security"])

        titles = [c["title"] for c in cases]
        sql_case = next((t for t in titles if "SQL" in t.upper()), None)
        assert sql_case is not None, f"No SQL injection case found in: {titles}"

    def test_security_cases_use_4xx_assertions(self):
        """Security injection cases should expect 4xx, not 2xx."""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        ep = {
            "service_name": "test",
            "module": "search",
            "method": "GET",
            "path": "/api/v1/search",
            "summary": "搜索",
            "request_schema": {
                "query": [
                    {"name": "q", "type": "string", "required": True}
                ]
            },
        }

        cases = generate_cases_from_endpoint(ep, templates=["security"])

        for case in cases:
            assertions = case.get("api_assertions", [])
            # Security cases should not have positive assertions
            has_2xx = any(
                a.get("operator") == "gte" and a.get("expected") == 200
                for a in (json.loads(assertions) if isinstance(assertions, str) else assertions)
            )
            assert not has_2xx, (
                f"Security case '{case['title']}' has 2xx assertion — "
                f"injection should expect 4xx"
            )


# ═══════════════════════════════════════════════════════
# Case cap
# ═══════════════════════════════════════════════════════

class TestCaseCap:
    """Verify the 30-case-per-endpoint cap."""

    def test_generation_capped_at_200(self):
        """Even with many fields, cases are capped at _MAX_CASES_PER_ENDPOINT."""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        # Build an endpoint with many properties to trigger many cases
        props = {f"field_{i}": {"type": "string"} for i in range(20)}
        ep = {
            "service_name": "test",
            "module": "big",
            "method": "POST",
            "path": "/api/v1/big",
            "summary": "Large endpoint",
            "request_schema": {
                "body": {
                    "type": "object",
                    "properties": props,
                    "required": [f"field_{i}" for i in range(10)],
                },
                "query": [{"name": f"q{i}", "type": "string", "required": True} for i in range(3)],
                "path": [{"name": "id", "type": "integer", "required": True}],
            },
        }

        cases = generate_cases_from_endpoint(ep)
        assert len(cases) <= 200, f"Expected ≤200 cases, got {len(cases)}"
