"""接口资产模型 + OpenAPI 导入测试。"""
import pytest


class TestApiAssetModels:
    """Task 1: 验证模型字段和持久化 — SQLAlchemy default 在 INSERT 时生效。"""

    def test_api_service_persist_and_defaults(self, db_session):
        """ApiService 持久化后 default 字段应正确。"""
        from app.models.api_asset import ApiService
        svc = ApiService(project_id=1, name="account-service", display_name="账号服务")
        db_session.add(svc)
        db_session.commit()
        db_session.refresh(svc)

        assert svc.name == "account-service"
        assert svc.project_id == 1
        assert svc.display_name == "账号服务"
        assert svc.status == "active"

    def test_api_endpoint_persist_and_defaults(self, db_session):
        """ApiEndpoint 持久化后 default 字段应正确。"""
        from app.models.api_asset import ApiService, ApiEndpoint
        svc = ApiService(project_id=1, name="ep-svc")
        db_session.add(svc)
        db_session.flush()

        ep = ApiEndpoint(
            project_id=1, service_id=svc.id, module="Auth",
            method="POST", path="/api/v1/login", summary="登录",
        )
        db_session.add(ep)
        db_session.commit()
        db_session.refresh(ep)

        assert ep.method == "POST"
        assert ep.path == "/api/v1/login"
        assert ep.module == "Auth"
        assert ep.source == "manual"
        assert ep.deprecated is False

    def test_api_import_batch_persist(self, db_session):
        """ApiImportBatch 持久化后统计字段应正确。"""
        from app.models.api_asset import ApiImportBatch
        batch = ApiImportBatch(
            project_id=1, service_id=1, source_type="openapi",
            total_count=10, created_count=5, updated_count=3, skipped_count=2,
        )
        db_session.add(batch)
        db_session.commit()
        db_session.refresh(batch)

        assert batch.total_count == 10
        assert batch.created_count == 5
        assert batch.status == "pending"

    def test_api_execution_task_persist(self, db_session):
        """ApiExecutionTask 持久化后 default 字段应正确。"""
        from app.models.api_asset import ApiExecutionTask
        task = ApiExecutionTask(
            project_id=1, task_id="TASK-001", name="回归测试",
            total=10, passed=8, failed=2,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "pending"
        assert task.total == 10
        assert task.trigger_type == "manual"

    def test_api_execution_task_item_snapshot(self, db_session):
        """ApiExecutionTaskItem 应正确存储快照。"""
        from app.models.api_asset import ApiExecutionTaskItem
        item = ApiExecutionTaskItem(
            task_id=1, case_id=42, status="passed", duration_ms=150.5,
            request_snapshot='{"method":"GET"}',
            response_snapshot='{"status":200}',
            assertion_results='[{"passed":true}]',
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.status == "passed"
        assert item.duration_ms == 150.5
        assert item.case_id == 42

    def test_unique_endpoint_constraint(self, db_session):
        """同一 project+service+method+path 重复插入应失败。"""
        from app.models.api_asset import ApiService, ApiEndpoint

        svc = ApiService(project_id=1, name="unique-svc")
        db_session.add(svc)
        db_session.flush()

        ep1 = ApiEndpoint(project_id=1, service_id=svc.id, method="POST", path="/api/dup")
        db_session.add(ep1)
        db_session.commit()

        ep2 = ApiEndpoint(project_id=1, service_id=svc.id, method="POST", path="/api/dup")
        db_session.add(ep2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_unique_service_constraint(self, db_session):
        """同一 project+name 的 service 重复插入应失败。"""
        from app.models.api_asset import ApiService

        s1 = ApiService(project_id=1, name="dup-service")
        db_session.add(s1)
        db_session.commit()

        s2 = ApiService(project_id=1, name="dup-service")
        db_session.add(s2)
        with pytest.raises(Exception):
            db_session.commit()


class TestOpenApiImportPreview:
    """Task 2: OpenAPI 导入预览测试（先写测试再实现 service）。"""

    def test_preview_extracts_endpoints_from_openapi3(self):
        """OpenAPI 3.x spec 应正确提取接口列表。"""
        from app.services.openapi_import_service import preview_openapi_import

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Account API", "version": "1.2.0"},
            "paths": {
                "/api/v1/login": {
                    "post": {
                        "summary": "登录",
                        "tags": ["Auth"],
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                        "responses": {"200": {"description": "ok"}},
                    }
                },
                "/api/v1/users": {
                    "get": {
                        "summary": "用户列表",
                        "tags": ["Users"],
                        "parameters": [{"name": "page", "in": "query", "schema": {"type": "integer"}}],
                        "responses": {"200": {"description": "ok"}},
                    }
                },
            },
        }

        preview = preview_openapi_import(spec, project_id=1, service_name="account-service")

        assert preview["total_count"] == 2
        assert len(preview["endpoints"]) == 2
        # 验证第一条
        login_ep = next(ep for ep in preview["endpoints"] if ep["method"] == "POST")
        assert login_ep["module"] == "Auth"
        assert login_ep["path"] == "/api/v1/login"
        assert login_ep["summary"] == "登录"
        assert login_ep["source"] == "openapi"

    def test_preview_supports_swagger2(self):
        """Swagger 2.0 spec 也应正确解析。"""
        from app.services.openapi_import_service import preview_openapi_import

        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy API", "version": "1.0"},
            "paths": {
                "/api/v1/status": {
                    "get": {
                        "summary": "健康检查",
                        "tags": ["System"],
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        }

        preview = preview_openapi_import(spec, project_id=1, service_name="legacy-svc")
        assert preview["total_count"] == 1
        assert preview["endpoints"][0]["method"] == "GET"
        assert preview["endpoints"][0]["path"] == "/api/v1/status"

    def test_preview_detects_duplicates(self, db_session):
        """已存在的接口应在预览中标记为已存在。"""
        from app.services.openapi_import_service import preview_openapi_import_with_db
        from app.models.api_asset import ApiService, ApiEndpoint

        # 先创建一个已存在的 service + endpoint
        svc = ApiService(project_id=1, name="dup-svc")
        db_session.add(svc)
        db_session.flush()
        ep = ApiEndpoint(project_id=1, service_id=svc.id, method="GET", path="/api/existing", summary="已存在")
        db_session.add(ep)
        db_session.commit()

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api/existing": {"get": {"summary": "已存在", "responses": {"200": {"description": "ok"}}}},
                "/api/new": {"post": {"summary": "新接口", "responses": {"200": {"description": "ok"}}}},
            },
        }

        preview = preview_openapi_import_with_db(db_session, spec, project_id=1, service_name="dup-svc")
        assert preview["total_count"] == 2
        assert preview["new_count"] == 1
        assert preview["existing_count"] == 1

    def test_preview_fallback_module_from_path(self):
        """无 tags 时应从 path 推断 module。"""
        from app.services.openapi_import_service import preview_openapi_import

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/api/v1/orders/list": {
                    "get": {"summary": "订单", "responses": {"200": {"description": "ok"}}},
                }
            },
        }

        preview = preview_openapi_import(spec, project_id=1, service_name="test-svc")
        assert preview["endpoints"][0]["module"] == "orders"  # path segment fallback
