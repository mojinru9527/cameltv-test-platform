"""Tests for playground service — compile and execute."""
from __future__ import annotations

from app.schemas.playground import CompileRequest, ExecuteRequest, SourceType
from app.services.playground_service import compile_spec, execute_spec


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
