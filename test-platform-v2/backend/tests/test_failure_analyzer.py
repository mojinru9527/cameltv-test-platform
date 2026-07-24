"""Unit tests for failure_analyzer service — pure logic, no database needed."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.failure_analyzer import analyze_api_failure, analyze_ui_failure


# ── Helpers ──

def _api_item(error_message="", request_snapshot="{}", response_snapshot="{}",
              assertion_results="[]", duration_ms=0):
    """Create a mock ApiExecutionTaskItem."""
    item = MagicMock()
    item.error_message = error_message
    item.request_snapshot = request_snapshot
    item.response_snapshot = response_snapshot
    item.assertion_results = assertion_results
    item.duration_ms = duration_ms
    return item


def _ui_run(error_message="", base_url="https://example.com", result="{}"):
    """Create a mock UiTestRun."""
    run = MagicMock()
    run.error_message = error_message
    run.base_url = base_url
    run.result = result
    return run


# ═══════════════════════════════════════════════════════════
# analyze_api_failure — category detection
# ═══════════════════════════════════════════════════════════

class TestAnalyzeApiFailureTimeout:
    def test_timeout_chinese(self):
        result = analyze_api_failure(_api_item(error_message="请求超时，已重试3次"))
        assert result["category"] == "timeout"
        assert result["confidence"] == 0.95

    def test_timeout_english(self):
        result = analyze_api_failure(_api_item(error_message="Request timeout after 30s"))
        assert result["category"] == "timeout"
        assert result["confidence"] == 0.95


class TestAnalyzeApiFailureConnection:
    def test_connection_refused(self):
        result = analyze_api_failure(_api_item(error_message="Connection refused"))
        assert result["category"] == "connection"
        assert result["confidence"] == 0.9

    def test_dns_error(self):
        result = analyze_api_failure(_api_item(error_message="DNS resolution failed"))
        assert result["category"] == "connection"
        assert result["confidence"] == 0.9


class TestAnalyzeApiFailureProdProtection:
    def test_prod_protection(self):
        result = analyze_api_failure(
            _api_item(error_message="生产环境保护，请设置 confirm_prod=true")
        )
        assert result["category"] == "prod_protection"
        assert result["confidence"] == 0.99


class TestAnalyzeApiFailureStatusMismatch:
    def test_status_code_assertion_failed(self):
        assertions = '[{"type":"status_code","expected":200,"actual":500,"passed":false,"message":"Expected 200 got 500"}]'
        result = analyze_api_failure(
            _api_item(error_message="", assertion_results=assertions)
        )
        assert result["category"] == "status_mismatch"
        assert result["confidence"] == 0.85

    def test_jsonpath_mismatch(self):
        assertions = '[{"type":"jsonpath","expected":"success","actual":"error","passed":false}]'
        result = analyze_api_failure(
            _api_item(error_message="", assertion_results=assertions)
        )
        assert result["category"] == "jsonpath_mismatch"
        assert result["confidence"] == 0.8

    def test_response_time_slow(self):
        assertions = '[{"type":"response_time","expected":1000,"actual":5000,"passed":false}]'
        result = analyze_api_failure(
            _api_item(error_message="", assertion_results=assertions)
        )
        assert result["category"] == "slow_response"
        assert result["confidence"] == 0.8

    def test_generic_assertion_failed(self):
        assertions = '[{"type":"body","expected":"hello","actual":"world","passed":false}]'
        result = analyze_api_failure(
            _api_item(error_message="", assertion_results=assertions)
        )
        assert result["category"] == "assertion_failed"
        assert result["confidence"] == 0.75


class TestAnalyzeApiFailureServerError:
    def test_500_status(self):
        resp = '{"status_code":500,"headers":{}}'
        result = analyze_api_failure(
            _api_item(error_message="Internal error", response_snapshot=resp)
        )
        assert result["category"] == "server_error"
        assert result["confidence"] == 0.7

    def test_502_status(self):
        resp = '{"status_code":502,"headers":{}}'
        result = analyze_api_failure(
            _api_item(error_message="Bad gateway", response_snapshot=resp)
        )
        assert result["category"] == "server_error"


class TestAnalyzeApiFailureClientError:
    def test_404_status(self):
        resp = '{"status_code":404,"headers":{}}'
        result = analyze_api_failure(
            _api_item(error_message="Not found", response_snapshot=resp)
        )
        assert result["category"] == "client_error"
        assert result["confidence"] == 0.7

    def test_401_status(self):
        resp = '{"status_code":401,"headers":{}}'
        result = analyze_api_failure(
            _api_item(error_message="Unauthorized", response_snapshot=resp)
        )
        assert result["category"] == "client_error"


class TestAnalyzeApiFailureUnknown:
    def test_unknown_empty(self):
        result = analyze_api_failure(_api_item())
        assert result["category"] == "unknown"
        assert result["confidence"] == 0.3

    def test_unknown_unrecognized(self):
        result = analyze_api_failure(
            _api_item(error_message="Something weird happened but no match")
        )
        assert result["category"] == "unknown"
        assert result["confidence"] == 0.3


# ═══════════════════════════════════════════════════════════
# analyze_api_failure — edge cases
# ═══════════════════════════════════════════════════════════

class TestAnalyzeApiFailureEdgeCases:
    def test_empty_error_msg(self):
        result = analyze_api_failure(_api_item(error_message=""))
        assert isinstance(result, dict)
        assert "category" in result
        assert "confidence" in result
        assert "suggestions" in result

    def test_none_attrs_default_gracefully(self):
        """Attributes that return None should not crash the analyzer."""
        item = MagicMock()
        item.error_message = None
        item.request_snapshot = None
        item.response_snapshot = None
        item.assertion_results = None
        item.duration_ms = None
        result = analyze_api_failure(item)
        assert isinstance(result, dict)
        assert "category" in result
        assert "confidence" in result
        assert result["key_info"]["method"] == ""
        assert result["key_info"]["url"] == ""
        assert result["key_info"]["status_code"] == 0

    def test_invalid_json_snapshots(self):
        result = analyze_api_failure(_api_item(
            request_snapshot="not valid json {{{",
            response_snapshot="also bad {{{",
            assertion_results="nope {{{",
        ))
        assert isinstance(result, dict)
        assert result["key_info"]["status_code"] == 0

    def test_corrupt_assertion_string(self):
        result = analyze_api_failure(_api_item(assertion_results="bad json"))
        assert isinstance(result, dict)
        assert "category" in result

    def test_error_summary_truncated_to_500(self):
        long_msg = "x" * 1000
        result = analyze_api_failure(_api_item(error_message=long_msg))
        assert len(result["error_summary"]) <= 500

    def test_failed_assertions_only_returns_failed(self):
        assertions = """[
            {"type":"status_code","expected":200,"actual":200,"passed":true},
            {"type":"body","expected":"ok","actual":"err","passed":false,"message":"mismatch"}
        ]"""
        result = analyze_api_failure(_api_item(assertion_results=assertions))
        failed = result["failed_assertions"]
        assert len(failed) == 1
        assert failed[0]["type"] == "body"


# ═══════════════════════════════════════════════════════════
# analyze_api_failure — structure & suggestions
# ═══════════════════════════════════════════════════════════

class TestAnalyzeApiFailureStructure:
    def test_has_expected_keys(self):
        result = analyze_api_failure(_api_item())
        for key in ("category", "confidence", "error_summary", "key_info",
                     "failed_assertions", "suggestions"):
            assert key in result, f"Missing key: {key}"

    def test_confidence_in_range(self):
        """Confidence must be in [0, 1] for every category."""
        categories = {}
        for msg, resp, assertions, expected_cat in [
            ("超时", '{}', '[]', "timeout"),
            ("connection refused", '{}', '[]', "connection"),
            ("生产环境 confirm_prod", '{}', '[]', "prod_protection"),
            ("", '{"status_code":200}', '[{"type":"status_code","expected":200,"actual":500,"passed":false}]', "status_mismatch"),
            ("", '{"status_code":200}', '[{"type":"body","expected":"ok","actual":"err","passed":false}]', "assertion_failed"),
            ("", '{"status_code":500}', '[]', "server_error"),
            ("", '{"status_code":404}', '[]', "client_error"),
            ("", '{}', '[]', "unknown"),
        ]:
            r = analyze_api_failure(_api_item(error_message=msg, response_snapshot=resp, assertion_results=assertions))
            assert 0 <= r["confidence"] <= 1, f"confidence out of range for {expected_cat}"
            categories[expected_cat] = r

    def test_timeout_has_non_empty_suggestions(self):
        result = analyze_api_failure(_api_item(error_message="超时"))
        assert len(result["suggestions"]) > 0
        assert any("超时" in s or "timeout" in s.lower() for s in result["suggestions"])

    def test_unknown_has_generic_suggestions(self):
        result = analyze_api_failure(_api_item())
        assert len(result["suggestions"]) > 0

    def test_all_categories_have_suggestions(self):
        """Every API error category should produce non-empty suggestions."""
        for msg, resp, assertions in [
            ("超时", '{}', '[]'),
            ("connection refused", '{}', '[]'),
            ("生产环境 confirm_prod=true", '{}', '[]'),
            ("", '{"status_code":200}',
             '[{"type":"status_code","expected":200,"actual":500,"passed":false}]'),
            ("", '{"status_code":200}',
             '[{"type":"body","expected":"ok","actual":"err","passed":false}]'),
            ("", '{"status_code":500}', '[]'),
            ("", '{"status_code":404}', '[]'),
            ("", '{}', '[]'),
        ]:
            r = analyze_api_failure(
                _api_item(error_message=msg, response_snapshot=resp,
                          assertion_results=assertions)
            )
            assert isinstance(r["suggestions"], list), f"No suggestions for {r['category']}"
            assert len(r["suggestions"]) > 0, f"Empty suggestions for {r['category']}"


# ═══════════════════════════════════════════════════════════
# analyze_ui_failure — category detection
# ═══════════════════════════════════════════════════════════

class TestAnalyzeUiFailureTimeout:
    def test_timeout_chinese(self):
        result = analyze_ui_failure(_ui_run(error_message="UI测试超时"))
        assert result["category"] == "timeout"
        assert result["confidence"] == 0.95

    def test_timeout_english(self):
        result = analyze_ui_failure(_ui_run(error_message="Test timed out after 60s"))
        assert result["category"] == "timeout"
        assert result["confidence"] == 0.95


class TestAnalyzeUiFailureSpecMissing:
    def test_spec_not_found(self):
        result = analyze_ui_failure(_ui_run(error_message="文件不存在或 not found"))
        assert result["category"] == "spec_missing"
        assert result["confidence"] == 0.9


class TestAnalyzeUiFailurePlaywrightUnavailable:
    def test_playwright_not_available(self):
        result = analyze_ui_failure(
            _ui_run(error_message="Playwright 不可用: command not found")
        )
        assert result["category"] == "playwright_unavailable"
        assert result["confidence"] == 0.95


class TestAnalyzeUiFailureNpxMissing:
    def test_npx_missing(self):
        result = analyze_ui_failure(_ui_run(error_message="npx: 未找到命令"))
        assert result["category"] == "npx_missing"
        assert result["confidence"] == 0.9


class TestAnalyzeUiFailureCancelled:
    def test_cancelled(self):
        result = analyze_ui_failure(_ui_run(error_message="任务已取消"))
        assert result["category"] == "cancelled"
        assert result["confidence"] == 0.99

    def test_cancelled_english(self):
        result = analyze_ui_failure(_ui_run(error_message="Run cancelled by user"))
        assert result["category"] == "cancelled"
        assert result["confidence"] == 0.99


class TestAnalyzeUiFailureExecutionError:
    def test_exit_code_non_zero(self):
        result = analyze_ui_failure(_ui_run(error_message="Process exit code 1"))
        assert result["category"] == "execution_error"
        assert result["confidence"] == 0.7

    def test_returncode(self):
        result = analyze_ui_failure(_ui_run(error_message="returncode=1 execution failed"))
        assert result["category"] == "execution_error"
        assert result["confidence"] == 0.7


class TestAnalyzeUiFailureOther:
    def test_other(self):
        result = analyze_ui_failure(_ui_run(error_message="unrecognized random error"))
        assert result["category"] == "other"
        assert result["confidence"] == 0.3

    def test_other_empty(self):
        result = analyze_ui_failure(_ui_run())
        assert result["category"] == "other"
        assert result["confidence"] == 0.3


# ═══════════════════════════════════════════════════════════
# analyze_ui_failure — edge cases
# ═══════════════════════════════════════════════════════════

class TestAnalyzeUiFailureEdgeCases:
    def test_empty_error_msg(self):
        result = analyze_ui_failure(_ui_run(error_message=""))
        assert isinstance(result, dict)
        assert "category" in result
        assert "confidence" in result
        assert "suggestions" in result

    def test_none_attrs_gracefully(self):
        run = MagicMock()
        run.error_message = None
        run.base_url = None
        run.result = None
        result = analyze_ui_failure(run)
        assert isinstance(result, dict)
        assert result["key_info"]["base_url"] == ""

    def test_error_summary_truncated(self):
        long_msg = "y" * 800
        result = analyze_ui_failure(_ui_run(error_message=long_msg))
        assert len(result["error_summary"]) <= 500

    def test_invalid_result_json(self):
        result = analyze_ui_failure(_ui_run(result="not json {{{"))
        assert isinstance(result, dict)
        assert result["key_info"]["total_tests"] == 0

    def test_partial_result_json(self):
        result = analyze_ui_failure(
            _ui_run(result='{"total":5,"pass_":3,"fail":2,"skip":0,"duration":120}')
        )
        assert result["key_info"]["total_tests"] == 5
        assert result["key_info"]["passed"] == 3
        assert result["key_info"]["failed"] == 2


# ═══════════════════════════════════════════════════════════
# analyze_ui_failure — structure & suggestions
# ═══════════════════════════════════════════════════════════

class TestAnalyzeUiFailureStructure:
    def test_has_expected_keys(self):
        result = analyze_ui_failure(_ui_run())
        for key in ("category", "confidence", "error_summary", "key_info", "suggestions"):
            assert key in result, f"Missing key: {key}"

    def test_confidence_in_range(self):
        for msg in ["超时", "文件不存在", "playwright 不可用", "npx: not found",
                     "取消", "exit code 1", "other"]:
            r = analyze_ui_failure(_ui_run(error_message=msg))
            assert 0 <= r["confidence"] <= 1, f"confidence out of range for msg={msg}"

    def test_timeout_suggestions_non_empty(self):
        result = analyze_ui_failure(_ui_run(error_message="超时"))
        assert len(result["suggestions"]) > 0

    def test_all_categories_have_suggestions(self):
        for msg in [
            "超时",
            "文件不存在 or not found",
            "playwright 不可用",
            "npx missing",
            "任务取消",
            "exit code 1 execution failed",
            "unrecognized error",
        ]:
            r = analyze_ui_failure(_ui_run(error_message=msg))
            assert isinstance(r["suggestions"], list), f"No suggestions for category {r['category']}"
            assert len(r["suggestions"]) > 0, f"Empty suggestions for category {r['category']}"

    def test_spec_missing_has_relevant_suggestion(self):
        result = analyze_ui_failure(_ui_run(error_message="spec 文件不存在"))
        assert any(".spec.ts" in s or ".spec.js" in s for s in result["suggestions"])

    def test_npx_missing_has_install_advice(self):
        result = analyze_ui_failure(_ui_run(error_message="npx not available"))
        assert any("Node.js" in s or "npm" in s.lower() or "npx" in s for s in result["suggestions"])
