"""Tests for playground service — compile and execute."""
from __future__ import annotations

import json

from app.schemas.playground import CompileRequest, ExecuteRequest, SourceType
from app.services.playground_service import (
    build_gherkin_from_case, compile_case_batch, compile_spec, execute_spec,
)


class TestCompileGherkin:
    def test_navigate_and_see_text(self):
        source = """Feature: Login
Given I am on "/login"
When I click "#submit"
Then I should see "Welcome"
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "page.goto('/login')" in result.spec_code
        assert "page.click('#submit')" in result.spec_code
        assert "toContainText('Welcome')" in result.spec_code
        assert result.spec_type == "playwright"
        assert result.compile_ms > 0

    def test_fill_and_expect_visible(self):
        source = """Feature: Search
Given I am on "/"
When I type "hello" in "#search"
Then the "#results" should be visible
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "page.fill('#search', 'hello')" in result.spec_code
        assert "toBeVisible()" in result.spec_code

    def test_url_assertion(self):
        source = """Feature: Redirect
Given I am on "/login"
Then the url should contain "dashboard"
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "toHaveURL(/dashboard/)" in result.spec_code

    def test_unmatched_line_becomes_todo_comment(self):
        source = """Feature: Unknown
When I do something weird
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "TODO" in result.spec_code

    def test_feature_becomes_test_name(self):
        source = """Feature: User Registration
Given I am on "/register"
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "User Registration" in result.spec_code

    def test_empty_source(self):
        source = ""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "No steps parsed" in result.spec_code


class TestCompileMarkdown:
    def test_extracts_gherkin_code_block(self):
        source = """# Login Test
```gherkin
Feature: Login
Given I am on "/login"
Then I should see "Sign In"
```
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.markdown))
        assert "page.goto('/login')" in result.spec_code
        assert "toContainText('Sign In')" in result.spec_code


class TestCompileGherkinChinese:
    """Batch 74: 中文 Gherkin 步骤 → 可执行 Playwright 动作，无 TODO。"""

    def test_chinese_navigate_click_fill_assert(self):
        source = """Feature: 登录
当 打开「/login」
当 在「#username」输入「admin」
当 点击「#submit」
则 看到「欢迎回来」
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "page.goto('/login')" in result.spec_code
        assert "page.fill('#username', 'admin')" in result.spec_code
        assert "page.click('#submit')" in result.spec_code
        assert "toContainText('欢迎回来')" in result.spec_code
        assert "TODO" not in result.spec_code

    def test_chinese_visible_wait_screenshot_and_fill_alt(self):
        source = """Feature: 直播
当 打开「https://www.camellofutbol.com」
当 等待 2 秒
则 「#video」可见
当 输入「搜索词」到「#search」
当 截图
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "page.goto('https://www.camellofutbol.com')" in result.spec_code
        assert "page.waitForTimeout(2 * 1000)" in result.spec_code
        assert "toBeVisible()" in result.spec_code
        assert "page.fill('#search', '搜索词')" in result.spec_code
        assert "page.screenshot" in result.spec_code
        assert "TODO" not in result.spec_code

    def test_expected_line_maps_to_assert(self):
        source = """Feature: 详情
当 打开「/detail」
则 url 应包含「detail」
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "toHaveURL(/detail/)" in result.spec_code
        assert "TODO" not in result.spec_code

    def test_chinese_click_by_text_uses_get_by_text(self):
        source = """Feature: 登录
当 打开「http://localhost:5211/login」
当 点击「登录」
"""
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "page.goto('http://localhost:5211/login')" in result.spec_code
        assert "page.getByText('登录').first().click()" in result.spec_code
        assert "TODO" not in result.spec_code


class TestBuildGherkinFromCase:
    def test_case_steps_become_gherkin_source(self):
        class FakeCase:
            title = "进入直播间默认播放视频流"
            preconditions = '["打开「/」"]'
            steps = json.dumps([
                {"step": 1, "desc": "打开「https://www.camellofutbol.com」", "expected": "页面打开"},
                {"step": 2, "desc": "点击「直播入口」", "expected": ""},
                {"step": 3, "desc": "等待 3 秒", "expected": ""},
                {"step": 4, "desc": "看到「播放中」", "expected": "看到「播放中」"},
            ])

        source = build_gherkin_from_case(FakeCase())
        assert "Feature: 进入直播间默认播放视频流" in source
        assert "当 打开「https://www.camellofutbol.com」" in source
        assert "当 点击「直播入口」" in source
        assert "则 看到「播放中」" in source
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        assert "TODO" not in result.spec_code


class TestCompilePlain:
    def test_basic_skeleton(self):
        source = "Check that the homepage loads."
        result = compile_spec(CompileRequest(source=source, source_type=SourceType.plain))
        assert "page.goto('/')" in result.spec_code
        assert "toBeVisible()" in result.spec_code


class TestExecute:
    def test_execute_returns_response_structure(self):
        """Execute a minimal spec — may fail without Playwright but returns proper structure."""
        source = """Feature: Minimal
Given I am on "about:blank"
"""
        compile_result = compile_spec(CompileRequest(source=source))
        exec_result = execute_spec(ExecuteRequest(spec_code=compile_result.spec_code, timeout_ms=15000))
        assert hasattr(exec_result, "passed")
        assert hasattr(exec_result, "stdout")
        assert hasattr(exec_result, "stderr")
        assert exec_result.duration_ms > 0


class _FakeScalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, stmt):
        return _FakeScalars(self.rows)


class TestBatch166CompileCaseBatch:
    def test_batch_compile_returns_one_item(self):
        class FakeCase:
            id = 101
            title = "登录成功"
            preconditions = '[]'
            steps = json.dumps([
                {"step": 1, "desc": "打开「/login」", "expected": ""},
                {"step": 2, "desc": "点击「#submit」", "expected": ""},
            ])

        result = compile_case_batch(_FakeDb([FakeCase()]), 1, [101])
        assert result.total == 1
        assert result.items[0].case_id == 101
        assert "page.goto('/login')" in result.items[0].spec_code
        assert "page.click('#submit')" in result.items[0].spec_code
        assert result.items[0].has_todo is False
