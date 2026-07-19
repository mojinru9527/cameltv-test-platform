"""case_compiler_service 单元测试 — 编译 functional case steps → Playwright spec 代码。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.case_compiler_service import (
    _build_user_message,
    _clean_generated_code,
    _make_spec_filename,
    _safe_json,
    compile_to_playwright,
)


# ═══════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════

def _make_mock_case(
    title: str = "测试登录功能",
    case_id: str = "TC-LOGIN-001",
    steps: str = '[{"step":1,"desc":"打开登录页面","expected":"登录页面正常显示"},{"step":2,"desc":"输入用户名和密码","expected":"输入框接受输入"},{"step":3,"desc":"点击登录按钮","expected":"跳转到首页"}]',
    preconditions: str = "用户已注册且未登录",
    expected_result: str = "用户成功登录并看到首页",
) -> MagicMock:
    """创建模拟的 TestCase ORM 对象。"""
    case = MagicMock()
    case.id = 1
    case.title = title
    case.case_id = case_id
    case.steps = steps
    case.preconditions = preconditions
    case.expected_result = expected_result
    case.case_type = "manual"
    return case


# ── _safe_json ──────────────────────────────────────

class TestSafeJson:
    def test_valid_json_array(self):
        assert _safe_json('[{"step":1,"desc":"a"}]') == [{"step": 1, "desc": "a"}]

    def test_empty_string(self):
        assert _safe_json("", []) == []

    def test_invalid_json(self):
        assert _safe_json("not json", []) == []

    def test_none(self):
        assert _safe_json(None, []) == []

    def test_custom_default(self):
        assert _safe_json("", "fallback") == "fallback"


# ── _make_spec_filename ──────────────────────────────

class TestMakeSpecFilename:
    def test_normal_case_id(self):
        case = _make_mock_case(case_id="TC-LOGIN-001")
        assert _make_spec_filename(case) == "generated-TC-LOGIN-001.spec.ts"

    def test_special_chars(self):
        case = _make_mock_case(case_id="TC-LOGIN/Test: 登录")
        result = _make_spec_filename(case)
        assert result.endswith(".spec.ts")
        assert "/" not in result
        assert ":" not in result

    def test_empty_case_id(self):
        case = _make_mock_case(case_id="")
        case.id = 42
        result = _make_spec_filename(case)
        assert "TC-UNKNOWN-42" in result


# ── _build_user_message ─────────────────────────────

class TestBuildUserMessage:
    def test_includes_title_and_steps(self):
        case = _make_mock_case()
        steps = json.loads(case.steps)
        msg = _build_user_message(case, steps, "http://localhost:5173")

        assert "测试登录功能" in msg
        assert "用户已注册且未登录" in msg
        assert "打开登录页面" in msg
        assert "预期结果: 登录页面正常显示" in msg
        assert "输入用户名和密码" in msg
        assert "点击登录按钮" in msg
        assert "http://localhost:5173" in msg

    def test_no_preconditions(self):
        case = _make_mock_case(preconditions="")
        steps = json.loads(case.steps)
        msg = _build_user_message(case, steps, "http://test.com")
        assert "无" in msg  # "前置条件\n无"

    def test_varied_step_formats(self):
        """兼容不同的 step key 名称（action/description 等）。"""
        case = _make_mock_case(steps='[{"index":1,"action":"do A","expected_result":"ok"}]')
        steps = json.loads(case.steps)
        msg = _build_user_message(case, steps, "http://x.com")
        assert "do A" in msg
        assert "预期结果: ok" in msg


# ── _clean_generated_code ────────────────────────────

class TestCleanGeneratedCode:
    def test_removes_typescript_fence(self):
        raw = "```typescript\nimport { test } from '@playwright/test';\ntest('a', () => {});\n```"
        cleaned = _clean_generated_code(raw)
        assert cleaned.startswith("import")
        assert "```" not in cleaned

    def test_removes_plain_fence(self):
        raw = "```\ncode here\n```"
        assert _clean_generated_code(raw) == "code here"

    def test_no_fence(self):
        raw = "import { test } from '@playwright/test';"
        assert _clean_generated_code(raw) == raw

    def test_partial_fence_opening(self):
        raw = "```typescript\nimport { test } from '@playwright/test';"
        cleaned = _clean_generated_code(raw)
        assert cleaned.startswith("import")
        assert "```" not in cleaned


# ── compile_to_playwright ────────────────────────────

class TestCompileToPlaywright:
    def test_no_steps_returns_error(self):
        case = _make_mock_case(steps="[]")
        result = compile_to_playwright(case, validate=False)
        assert result["error"] is not None
        assert "没有测试步骤" in result["error"]
        assert result["spec_code"] == ""

    def test_empty_steps_string_returns_error(self):
        case = _make_mock_case(steps="")
        result = compile_to_playwright(case, validate=False)
        assert result["error"] is not None

    @patch("app.services.case_compiler_service._call_llm_for_code")
    def test_successful_compilation(self, mock_llm):
        mock_llm.return_value = (
            "import { test, expect } from '@playwright/test';\n\n"
            "test.describe('TC-LOGIN-001 测试登录功能', () => {\n"
            "  test('should login successfully', async ({ page }) => {\n"
            "    await page.goto('http://localhost:5173');\n"
            "    await test.step('1. 打开登录页面', async () => {\n"
            "      await expect(page.getByText('登录')).toBeVisible();\n"
            "    });\n"
            "  });\n"
            "});\n",
            {"prompt_tokens": 500, "completion_tokens": 200},
        )
        case = _make_mock_case()
        result = compile_to_playwright(case, validate=False)

        assert result["error"] is None
        assert result["case_id"] == 1
        assert "import { test, expect }" in result["spec_code"]
        assert result["spec_file"] == "generated-TC-LOGIN-001.spec.ts"
        assert result["compilation_time_ms"] >= 0  # mock 返回即完成，可能为 0
        assert result["model_used"] != ""
        assert result["prompt_tokens"] == 500
        assert result["completion_tokens"] == 200

    @patch("app.services.case_compiler_service._call_llm_for_code")
    def test_llm_error_handling(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API key missing")
        case = _make_mock_case()
        result = compile_to_playwright(case, validate=False)
        assert result["error"] is not None
        assert "LLM 调用失败" in result["error"]

    @patch("app.services.case_compiler_service._call_llm_for_code")
    def test_empty_response(self, mock_llm):
        mock_llm.return_value = ("", None)
        case = _make_mock_case()
        result = compile_to_playwright(case, validate=False)
        assert result["error"] == "LLM 返回空代码"

    @patch("app.services.case_compiler_service._call_llm_for_code")
    def test_cleans_markdown_fence(self, mock_llm):
        mock_llm.return_value = (
            "```typescript\nimport { test } from '@playwright/test';\ntest('a', () => {});\n```",
            {},
        )
        case = _make_mock_case()
        result = compile_to_playwright(case, validate=False)
        assert "```" not in result["spec_code"]
        assert result["spec_code"].startswith("import")
