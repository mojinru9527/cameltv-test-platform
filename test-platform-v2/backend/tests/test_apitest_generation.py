"""接口用例生成测试 — 正向/边界/异常/幂等场景。"""


class TestApiCaseGeneration:
    """Task 3: 用例生成引擎。"""

    def test_generate_cases_basic(self):
        """基础模板应生成正向用例。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "account-service",
            "module": "Auth",
            "method": "POST",
            "path": "/api/v1/users",
            "summary": "创建用户",
            "request_schema": {
                "body": {
                    "type": "object",
                    "required": ["username", "age"],
                    "properties": {
                        "username": {"type": "string", "minLength": 3, "maxLength": 20},
                        "age": {"type": "integer", "minimum": 0, "maximum": 120},
                        "role": {"type": "string", "enum": ["user", "admin"]},
                    },
                }
            },
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["basic"])
        titles = [c["title"] for c in cases]

        assert len(cases) >= 1
        assert any("正常" in t for t in titles)
        # 每条 case 必须有标准字段
        for c in cases:
            assert "title" in c
            assert "priority" in c
            assert "api_method" in c
            assert "api_endpoint" in c
            assert "api_assertions" in c

    def test_generate_cases_includes_boundary(self):
        """边界模板应生成 min/max 边界用例。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "user-svc",
            "module": "User",
            "method": "POST",
            "path": "/api/v1/users",
            "summary": "创建用户",
            "request_schema": {
                "body": {
                    "type": "object",
                    "required": ["username"],
                    "properties": {
                        "username": {"type": "string", "minLength": 3, "maxLength": 20},
                        "age": {"type": "integer", "minimum": 0, "maximum": 120},
                    },
                }
            },
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["boundary"])
        titles = [c["title"] for c in cases]

        assert any("username" in t and ("最小" in t or "边界" in t or "长度" in t) for t in titles), f"titles: {titles}"
        assert any("age" in t and ("最大" in t or "边界" in t) for t in titles), f"titles: {titles}"

    def test_generate_cases_includes_required_validation(self):
        """异常模板应包含必填字段缺失用例。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "order-svc",
            "module": "Order",
            "method": "POST",
            "path": "/api/v1/orders",
            "summary": "创建订单",
            "request_schema": {
                "body": {
                    "type": "object",
                    "required": ["product_id", "quantity"],
                    "properties": {
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer", "minimum": 1},
                    },
                }
            },
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["invalid"])
        titles = [c["title"] for c in cases]
        assert any("必填" in t or "缺失" in t for t in titles), f"titles: {titles}"

    def test_generate_cases_includes_enum_validation(self):
        """异常模板应包含枚举非法值用例。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "user-svc",
            "module": "User",
            "method": "PUT",
            "path": "/api/v1/users/status",
            "summary": "更新状态",
            "request_schema": {
                "body": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {"type": "string", "enum": ["active", "inactive", "suspended"]},
                    },
                }
            },
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["invalid"])
        titles = [c["title"] for c in cases]
        assert any("枚举" in t or "非法" in t or "无效" in t for t in titles), f"titles: {titles}"

    def test_generate_cases_idempotency(self):
        """幂等模板应生成重复提交用例。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "order-svc",
            "module": "Order",
            "method": "POST",
            "path": "/api/v1/orders",
            "summary": "创建订单",
            "request_schema": {
                "body": {
                    "type": "object",
                    "required": ["product_id"],
                    "properties": {"product_id": {"type": "string"}},
                }
            },
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["idempotency"])
        titles = [c["title"] for c in cases]
        assert any("幂等" in t for t in titles), f"titles: {titles}"

    def test_generate_cases_full_set(self):
        """全量模板应生成多条用例，覆盖各场景。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "full-svc",
            "module": "Full",
            "method": "POST",
            "path": "/api/v1/resource",
            "summary": "全量测试",
            "request_schema": {
                "body": {
                    "type": "object",
                    "required": ["name", "type", "count"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 50},
                        "type": {"type": "string", "enum": ["A", "B", "C"]},
                        "count": {"type": "integer", "minimum": 1, "maximum": 999},
                        "email": {"type": "string", "format": "email"},
                    },
                }
            },
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["basic", "boundary", "invalid", "idempotency"])
        titles = [c["title"] for c in cases]

        assert len(cases) >= 5
        assert any("正常" in t for t in titles)
        assert any("必填" in t or "缺失" in t for t in titles)
        assert any("枚举" in t or "非法" in t for t in titles)
        assert any("幂等" in t for t in titles)

    def test_generate_cases_each_has_valid_assertions(self):
        """每条生成的用例必须包含有效断言。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "test-svc",
            "module": "Test",
            "method": "GET",
            "path": "/api/v1/items",
            "summary": "列表",
            "request_schema": {},
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["basic"])
        for c in cases:
            assertions = c.get("api_assertions", [])
            assert isinstance(assertions, list)
            assert len(assertions) >= 1, f"Case '{c['title']}' has no assertions"
            for a in assertions:
                assert "type" in a, f"Assertion missing type in case '{c['title']}'"

    def test_generate_cases_tags_include_service(self):
        """生成的用例 tags 应包含 service:<name>。"""
        from app.services.api_case_generation_service import generate_cases_from_endpoint

        endpoint = {
            "service_name": "my-service",
            "module": "Test",
            "method": "GET",
            "path": "/api/v1/test",
            "summary": "测试",
            "request_schema": {},
        }

        cases = generate_cases_from_endpoint(endpoint, templates=["basic"])
        for c in cases:
            tags = c.get("tags", [])
            assert "service:my-service" in tags


class TestApiExecutionEnhancements:
    """Task 4: 执行引擎增强 — base_url 解析 + 新断言类型。"""

    def test_resolve_url_with_environment_base_url(self, db_session):
        """有 environment base_url 时应正确拼接路径。"""
        from app.models.environment import Environment
        from app.services.api_execution_service import _resolve_url

        env = Environment(
            project_id=1, name="test", env_type="test",
            base_url="https://api.example.com", description="",
        )
        db_session.add(env)
        db_session.flush()

        url = _resolve_url(db_session, env.id, "/api/v1/users")
        assert url == "https://api.example.com/api/v1/users"

    def test_resolve_url_full_url_bypasses_base(self, db_session):
        """完整 URL 不拼接 base_url。"""
        from app.models.environment import Environment
        from app.services.api_execution_service import _resolve_url

        env = Environment(
            project_id=1, name="test", env_type="test",
            base_url="https://api.example.com", description="",
        )
        db_session.add(env)
        db_session.flush()

        url = _resolve_url(db_session, env.id, "https://other.com/api/custom")
        assert url == "https://other.com/api/custom"

    def test_resolve_url_no_environment(self, db_session):
        """无环境时给相对路径加 http:// 前缀。"""
        from app.services.api_execution_service import _resolve_url

        url = _resolve_url(db_session, None, "/api/test")
        assert url == "http:///api/test" or url.startswith("http")

    def test_assert_header_type(self):
        """header 断言类型应能检查响应头。"""
        from app.services.api_execution_service import _run_assertions

        assertions = [{"type": "header", "key": "Content-Type", "expected": "application/json", "operator": "contains"}]
        results = _run_assertions(
            assertions,
            status_code=200,
            response_data={"ok": True},
            raw_body='{"ok":true}',
            duration_ms=100,
            response_headers={"Content-Type": "application/json; charset=utf-8"},
        )
        assert results[0]["passed"] is True

    def test_assert_array_length(self):
        """array_length 断言应检查数组长度。"""
        from app.services.api_execution_service import _run_assertions

        assertions = [{"type": "array_length", "path": "$.items", "expected": 3, "operator": "gte"}]
        results = _run_assertions(
            assertions,
            status_code=200,
            response_data={"items": [1, 2, 3, 4]},
            raw_body="",
            duration_ms=100,
        )
        assert results[0]["passed"] is True

    def test_assert_type_check(self):
        """type 断言应检查字段类型。"""
        from app.services.api_execution_service import _run_assertions

        assertions = [{"type": "type", "path": "$.data.amount", "expected": "number"}]
        results = _run_assertions(
            assertions,
            status_code=200,
            response_data={"data": {"amount": 99.5}},
            raw_body="",
            duration_ms=100,
        )
        assert results[0]["passed"] is True

    def test_assert_json_schema(self):
        """json_schema 断言应验证响应结构。"""
        from app.services.api_execution_service import _run_assertions

        schema = {
            "type": "object",
            "required": ["code", "data"],
            "properties": {
                "code": {"type": "integer"},
                "data": {"type": "object"},
            },
        }
        assertions = [{"type": "json_schema", "expected": schema}]
        results = _run_assertions(
            assertions,
            status_code=200,
            response_data={"code": 0, "data": {"name": "test"}},
            raw_body="",
            duration_ms=100,
        )
        assert results[0]["passed"] is True
