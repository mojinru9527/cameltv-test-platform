"""Batch 204 回归发现修复：存量用例 api_spec_ref 回退解析服务前缀（执行 URL 404 修复）。"""
from __future__ import annotations


class TestSpecRefFallbackUrl:
    def test_spec_ref_fallback_resolves_service_prefix(self, db_session):
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase
        from app.services.api_execution_service import _case_execution_url

        svc = ApiService(project_id=1, name="live-platform", display_name="live-platform")
        db_session.add(svc)
        db_session.flush()
        ep = ApiEndpoint(project_id=1, service_id=svc.id, method="GET", path="/app/getById")
        db_session.add(ep)
        db_session.flush()
        case = TestCase(
            project_id=1, title="t", case_type="api", api_method="GET",
            api_endpoint="/app/getById?id=1", api_endpoint_id=None,
            api_spec_ref=f"api_endpoint:{ep.id}",
        )
        db_session.add(case)
        db_session.commit()

        assert _case_execution_url(db_session, case) == "/live-platform/app/getById?id=1"

    def test_bad_spec_ref_leaves_url_unchanged(self, db_session):
        from app.models.test_case import TestCase
        from app.services.api_execution_service import _case_execution_url

        case = TestCase(
            project_id=1, title="t2", case_type="api", api_method="GET",
            api_endpoint="/api/v1/x", api_endpoint_id=None,
            api_spec_ref="generated:Client:get-x.spec",
        )
        db_session.add(case)
        db_session.commit()

        assert _case_execution_url(db_session, case) == "/api/v1/x"

    def test_api_endpoint_id_wins_over_spec_ref(self, db_session):
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
            project_id=1, title="t3", case_type="api", api_method="GET",
            api_endpoint="/ee/x", api_endpoint_id=ep.id,
            api_spec_ref=f"api_endpoint:{ep.id}",
        )
        db_session.add(case)
        db_session.commit()

        assert _case_execution_url(db_session, case) == "/camel-service/ee/x"
