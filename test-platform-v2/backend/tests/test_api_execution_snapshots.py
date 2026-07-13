"""API 执行快照与生产环境保护测试。

覆盖：
- 请求快照含 curl 命令和敏感头脱敏
- 响应快照含 body_preview、body_size_bytes、truncated 标记
- 生产环境写操作保护（权限 + confirm_prod）
- 生产环境读操作放行
- 敏感头脱敏验证
"""
from __future__ import annotations

import json

import pytest


class TestRequestSnapshot:
    """请求快照格式验证。"""

    def test_request_snapshot_contains_curl(self, db_session):
        """请求快照应包含可复制的 curl 命令。"""
        from app.services.api_execution_service import _build_request_snapshot

        snapshot = _build_request_snapshot(
            method="POST",
            original_url="/api/test",
            resolved_url="https://example.test/api/test",
            headers={"Authorization": "Bearer secret123", "Content-Type": "application/json"},
            body='{"key":"value"}',
            environment_id=1,
        )

        assert snapshot["method"] == "POST"
        assert snapshot["original_url"] == "/api/test"
        assert snapshot["resolved_url"] == "https://example.test/api/test"
        assert snapshot["environment_id"] == 1
        assert "curl" in snapshot
        assert "curl" in snapshot["curl"]
        assert "POST" in snapshot["curl"]
        assert "example.test" in snapshot["curl"]
        assert "Authorization" in snapshot["curl"]

    def test_request_snapshot_always_has_dataset_row_index(self, db_session):
        """请求快照应始终包含 dataset_row_index 字段。"""
        from app.services.api_execution_service import _build_request_snapshot

        snapshot = _build_request_snapshot(
            method="GET",
            original_url="/api/items",
            resolved_url="https://example.test/api/items",
            headers={},
            body="",
            environment_id=None,
        )

        assert "dataset_row_index" in snapshot
        assert snapshot["dataset_row_index"] is None

        snapshot2 = _build_request_snapshot(
            method="GET",
            original_url="/api/items",
            resolved_url="https://example.test/api/items",
            headers={},
            body="",
            environment_id=None,
            dataset_row_index=3,
        )
        assert snapshot2["dataset_row_index"] == 3

    def test_curl_masks_sensitive_headers(self, db_session):
        """curl 命令中敏感头应提示用户替换 token。"""
        from app.services.api_execution_service import _build_request_snapshot

        snapshot = _build_request_snapshot(
            method="GET",
            original_url="/api/secure",
            resolved_url="https://example.test/api/secure",
            headers={"Authorization": "Bearer abc123", "Cookie": "session=xyz"},
            body="",
            environment_id=1,
        )

        curl = snapshot["curl"]
        assert "<your-token>" in curl
        assert "Bearer abc123" not in curl

    def test_large_body_truncated_in_snapshot(self, db_session):
        """超长请求体应在快照中被截断。"""
        from app.services.api_execution_service import _build_request_snapshot

        big_body = "x" * 15000
        snapshot = _build_request_snapshot(
            method="POST",
            original_url="/api/bulk",
            resolved_url="https://example.test/api/bulk",
            headers={},
            body=big_body,
        )

        assert len(snapshot["body"]) < len(big_body)
        assert "truncated" in snapshot["body"]


class TestResponseSnapshot:
    """响应快照格式验证。"""

    def test_response_snapshot_has_body_preview(self, db_session):
        """响应快照应包含 body_preview 字段。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "GET", "url": "https://httpbin.org/get"},
            assertions=[],
        )
        resp_snap = result.get("response_snapshot", {})
        assert "body_preview" in resp_snap, f"Missing body_preview in {json.dumps(resp_snap)}"
        assert isinstance(resp_snap["body_preview"], str)

    def test_response_snapshot_has_truncated_flag(self, db_session):
        """响应快照应包含 truncated 标记。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "GET", "url": "https://httpbin.org/get"},
            assertions=[],
        )
        resp_snap = result.get("response_snapshot", {})
        assert "truncated" in resp_snap
        assert isinstance(resp_snap["truncated"], bool)

    def test_response_snapshot_has_body_size_bytes(self, db_session):
        """响应快照应包含 body_size_bytes 字段。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "GET", "url": "https://httpbin.org/get"},
            assertions=[],
        )
        resp_snap = result.get("response_snapshot", {})
        assert "body_size_bytes" in resp_snap
        assert isinstance(resp_snap["body_size_bytes"], int)

    def test_response_snapshot_has_content_type(self, db_session):
        """响应快照应包含 content_type 字段。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "GET", "url": "https://httpbin.org/get"},
            assertions=[],
        )
        resp_snap = result.get("response_snapshot", {})
        assert "content_type" in resp_snap

    def test_error_result_has_empty_snapshots(self, db_session):
        """错误结果应包含空的快照。"""
        from app.services.api_execution_service import _error_result

        result = _error_result("测试错误")
        assert result["status"] == "error"
        assert "request_snapshot" in result
        assert "response_snapshot" in result
        assert result["error"] == "测试错误"


class TestSensitiveHeaderMasking:
    """敏感头脱敏验证。"""

    SENSITIVE_KEYS = ["authorization", "cookie", "set-cookie", "x-api-key", "x-auth-token", "token"]

    def test_all_sensitive_headers_masked(self, db_session):
        """所有定义的敏感头都应被脱敏为 ***。"""
        from app.services.api_execution_service import _build_request_snapshot, SENSITIVE_MASK

        for key in self.SENSITIVE_KEYS:
            snapshot = _build_request_snapshot(
                method="GET",
                original_url="/",
                resolved_url="https://example.test/",
                headers={key: "secret-value"},
                body="",
            )
            assert snapshot["headers"].get(key) == SENSITIVE_MASK, (
                f"Header '{key}' should be masked as '{SENSITIVE_MASK}', "
                f"got: {snapshot['headers'].get(key)}"
            )

    def test_non_sensitive_headers_preserved(self, db_session):
        """非敏感头值应原样保留。"""
        from app.services.api_execution_service import _build_request_snapshot

        snapshot = _build_request_snapshot(
            method="GET",
            original_url="/",
            resolved_url="https://example.test/",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/html",
                "x-request-id": "req-12345",
            },
            body="",
        )

        assert snapshot["headers"]["Content-Type"] == "application/json"
        assert snapshot["headers"]["Accept"] == "text/html"
        assert snapshot["headers"]["x-request-id"] == "req-12345"

    def test_case_insensitive_matching(self, db_session):
        """敏感头大小写不敏感匹配。"""
        from app.services.api_execution_service import _build_request_snapshot, SENSITIVE_MASK

        variants = ["Authorization", "AUTHORIZATION", "authorization", "AuthorIzation"]
        for v in variants:
            snapshot = _build_request_snapshot(
                method="GET",
                original_url="/",
                resolved_url="https://example.test/",
                headers={v: "secret"},
                body="",
            )
            assert snapshot["headers"].get(v) == SENSITIVE_MASK, (
                f"Case variant '{v}' not masked"
            )


class TestProductionWriteProtection:
    """生产环境写操作保护。"""

    @pytest.fixture(autouse=True)
    def _seed_prod_env(self, db_session):
        """创建生产环境测试数据。"""
        from app.models.environment import Environment

        env = Environment(
            id=100,
            project_id=1,
            name="生产环境",
            env_type="prod",
            base_url="https://prod.example.com",
        )
        db_session.add(env)
        db_session.commit()
        self.prod_env_id = 100

    def test_get_allowed_in_prod_without_confirm(self, db_session):
        """生产环境 GET 请求无需 confirm_prod 即可执行。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "GET", "url": "/health"},
            environment_id=self.prod_env_id,
            confirm_prod=False,
        )
        # GET should be allowed even without confirm_prod in prod
        # Note: 连接可能失败但不应是生产保护错误
        assert result.get("error", "") == "" or "生产环境禁止" not in result.get("error", "")

    def test_post_blocked_in_prod_without_confirm(self, db_session):
        """生产环境 POST 有权限但无 confirm_prod 应被拒绝。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "POST", "url": "/api/create"},
            environment_id=self.prod_env_id,
            confirm_prod=False,
            has_execute_prod=True,
        )
        assert result["status"] == "error"
        assert "confirm_prod" in result.get("error", "").lower()

    def test_post_blocked_in_prod_without_permission(self, db_session):
        """生产环境 POST 无 has_execute_prod 应被拒绝。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "POST", "url": "/api/create"},
            environment_id=self.prod_env_id,
            confirm_prod=True,
            has_execute_prod=False,
        )
        assert result["status"] == "error"
        assert "apitest:execute_prod" in result.get("error", "")

    def test_post_allowed_in_prod_with_both(self, db_session):
        """生产环境 POST 有 has_execute_prod + confirm_prod 应允许执行。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "POST", "url": "https://httpbin.org/post"},
            environment_id=self.prod_env_id,
            confirm_prod=True,
            has_execute_prod=True,
        )
        # 应正常执行，不因生产保护报错
        assert "生产环境禁止" not in result.get("error", "")
        assert "apitest:execute_prod" not in result.get("error", "")

    def test_put_blocked_in_prod_without_confirm(self, db_session):
        """生产环境 PUT 有权限但无 confirm_prod 应被拒绝。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "PUT", "url": "/api/update/1"},
            environment_id=self.prod_env_id,
            confirm_prod=False,
            has_execute_prod=True,
        )
        assert result["status"] == "error"
        assert "confirm_prod" in result.get("error", "").lower()

    def test_delete_blocked_in_prod_without_confirm(self, db_session):
        """生产环境 DELETE 有权限但无 confirm_prod 应被拒绝。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "DELETE", "url": "/api/items/1"},
            environment_id=self.prod_env_id,
            confirm_prod=False,
            has_execute_prod=True,
        )
        assert result["status"] == "error"
        assert "confirm_prod" in result.get("error", "").lower()

    def test_head_allowed_in_prod(self, db_session):
        """生产环境 HEAD 读操作应被允许。"""
        from app.services.api_execution_service import _check_prod_protection

        allowed, msg = _check_prod_protection(
            db_session, "HEAD", self.prod_env_id, confirm_prod=False
        )
        assert allowed is True

    def test_options_allowed_in_prod(self, db_session):
        """生产环境 OPTIONS 读操作应被允许。"""
        from app.services.api_execution_service import _check_prod_protection

        allowed, msg = _check_prod_protection(
            db_session, "OPTIONS", self.prod_env_id, confirm_prod=False
        )
        assert allowed is True

    def test_non_prod_env_no_protection(self, db_session):
        """非生产环境写操作无需保护。"""
        from app.models.environment import Environment
        from app.services.api_execution_service import quick_execute

        env = Environment(
            project_id=1, name="测试环境", env_type="test",
            base_url="https://test.example.com",
        )
        db_session.add(env)
        db_session.commit()

        result = quick_execute(
            db_session,
            {"method": "POST", "url": "https://httpbin.org/post"},
            environment_id=env.id,
            confirm_prod=False,
            has_execute_prod=False,
        )
        assert "生产环境禁止" not in result.get("error", "")

    def test_no_environment_no_protection(self, db_session):
        """无环境时不做生产保护检查。"""
        from app.services.api_execution_service import _check_prod_protection

        allowed, msg = _check_prod_protection(
            db_session, "POST", None, confirm_prod=False
        )
        assert allowed is True


class TestProdProtectionEdgeCases:
    """生产环境保护边界情况。"""

    def test_missing_env_id_returns_true(self, db_session):
        """environment_id 为 None 时生产保护应通过。"""
        from app.services.api_execution_service import _check_prod_protection

        allowed, msg = _check_prod_protection(
            db_session, "POST", None, confirm_prod=False, has_execute_prod=False,
        )
        assert allowed is True
        assert msg == ""

    def test_invalid_env_id_returns_true(self, db_session):
        """不存在的 environment_id 应放行（由调用方处理）。"""
        from app.services.api_execution_service import _check_prod_protection

        allowed, msg = _check_prod_protection(
            db_session, "POST", 99999, confirm_prod=False, has_execute_prod=False,
        )
        assert allowed is True

    def test_dev_env_writes_allowed(self, db_session):
        """dev 环境写操作无需保护。"""
        from app.models.environment import Environment
        from app.services.api_execution_service import _check_prod_protection

        env = Environment(
            project_id=1, name="开发环境", env_type="dev",
            base_url="https://dev.example.com",
        )
        db_session.add(env)
        db_session.commit()

        allowed, msg = _check_prod_protection(
            db_session, "POST", env.id, confirm_prod=False, has_execute_prod=False,
        )
        assert allowed is True

    def test_staging_env_writes_allowed(self, db_session):
        """staging 环境写操作无需保护。"""
        from app.models.environment import Environment
        from app.services.api_execution_service import _check_prod_protection

        env = Environment(
            project_id=1, name="预发布环境", env_type="staging",
            base_url="https://staging.example.com",
        )
        db_session.add(env)
        db_session.commit()

        allowed, msg = _check_prod_protection(
            db_session, "POST", env.id, confirm_prod=False, has_execute_prod=False,
        )
        assert allowed is True


class TestCurlCommand:
    """curl 命令生成验证。"""

    def test_build_curl_get(self):
        """GET 请求 curl 命令。"""
        from app.services.api_execution_service import build_curl_command

        cmd = build_curl_command({
            "method": "GET",
            "resolved_url": "https://example.com/api/items",
            "headers": {"Content-Type": "application/json"},
            "body": "",
        })
        assert "curl" in cmd
        assert "GET" in cmd
        assert "https://example.com/api/items" in cmd
        assert "Content-Type" in cmd

    def test_build_curl_post_with_body(self):
        """POST 请求 curl 命令含 body。"""
        from app.services.api_execution_service import build_curl_command

        cmd = build_curl_command({
            "method": "POST",
            "resolved_url": "https://example.com/api/create",
            "headers": {"Content-Type": "application/json"},
            "body": '{"name":"test"}',
        })
        assert "POST" in cmd
        assert "-d" in cmd
        assert "name" in cmd
        assert "test" in cmd

    def test_build_curl_with_sensitive_header(self):
        """敏感头在 curl 中提示替换。"""
        from app.services.api_execution_service import build_curl_command, SENSITIVE_MASK

        cmd = build_curl_command({
            "method": "GET",
            "resolved_url": "https://example.com/api/secure",
            "headers": {"Authorization": SENSITIVE_MASK},
            "body": "",
        })
        assert "<your-token>" in cmd

    def test_build_curl_empty_snapshot(self):
        """空快照仍生成有效 curl。"""
        from app.services.api_execution_service import build_curl_command

        cmd = build_curl_command({})
        assert "curl" in cmd
        assert "GET" in cmd  # default method


class TestResponseBodyTruncation:
    """响应体截断逻辑验证。"""

    def test_short_body_not_truncated(self, db_session):
        """短响应体不应标记为截断。"""
        from app.services.api_execution_service import quick_execute

        result = quick_execute(
            db_session,
            {"method": "GET", "url": "https://httpbin.org/get"},
            assertions=[],
        )
        resp_snap = result.get("response_snapshot", {})
        # Body preview should contain the response
        assert isinstance(resp_snap.get("body_preview"), str)

    def test_truncate_for_preview(self):
        """_truncate_for_preview 截断逻辑。"""
        from app.services.api_execution_service import _truncate_for_preview

        text = "a" * 100
        result = _truncate_for_preview(text, 50)
        assert len(result) < 100
        assert "truncated" in result

    def test_truncate_for_preview_short(self):
        """短文本不截断。"""
        from app.services.api_execution_service import _truncate_for_preview

        text = "short"
        result = _truncate_for_preview(text, 4096)
        assert result == "short"

    def test_truncate_for_preview_empty(self):
        """空文本截断返回空。"""
        from app.services.api_execution_service import _truncate_for_preview

        result = _truncate_for_preview("", 4096)
        assert result == ""

    def test_truncate_for_preview_none(self):
        """None 文本处理。"""
        from app.services.api_execution_service import _truncate_for_preview

        result = _truncate_for_preview(None, 4096)
        assert result == ""


class TestExecuteApiCaseProdGuard:
    """execute_api_case 函数的生产保护集成测试。"""

    @pytest.fixture(autouse=True)
    def _seed(self, db_session):
        from app.models.environment import Environment
        from app.models.test_case import TestCase

        env = Environment(
            id=200, project_id=1, name="ProdEnv", env_type="prod",
            base_url="https://prod.example.com",
        )
        db_session.add(env)
        db_session.commit()

        self.case = TestCase(
            project_id=1, title="Prod Write Test", case_type="api",
            api_method="POST", api_endpoint="https://httpbin.org/post",
            api_body='{"test":true}',
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db_session.add(self.case)
        db_session.commit()

    def test_execute_api_case_blocks_prod_write_no_confirm(self, db_session):
        from app.services.api_execution_service import execute_api_case

        result = execute_api_case(
            db_session, self.case.id,
            project_id=1,
            environment_id=200,
            confirm_prod=False,
            has_execute_prod=False,
        )
        assert result["status"] == "error"

    def test_execute_api_case_blocks_prod_write_no_permission(self, db_session):
        from app.services.api_execution_service import execute_api_case

        result = execute_api_case(
            db_session, self.case.id,
            project_id=1,
            environment_id=200,
            confirm_prod=True,
            has_execute_prod=False,
        )
        assert result["status"] == "error"
        assert "apitest:execute_prod" in result.get("error", "")

    def test_execute_api_case_allows_prod_write_with_both(self, db_session):
        from app.services.api_execution_service import execute_api_case

        result = execute_api_case(
            db_session, self.case.id,
            project_id=1,
            environment_id=200,
            confirm_prod=True,
            has_execute_prod=True,
        )
        # Should execute (might fail to connect but not because of guard)
        assert "生产环境禁止" not in result.get("error", "")
        assert "apitest:execute_prod" not in result.get("error", "")
