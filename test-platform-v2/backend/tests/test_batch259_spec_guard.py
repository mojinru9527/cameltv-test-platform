"""Batch 259 / B2-2 — 生成代码危险 API 静态拦截（H1）。

DoD：含 `execSync` 的 spec 在执行前被拒并给出可读原因。
同时必须证明**正常 Playwright 用例不被误伤**（否则守卫会被绕过或关掉）。
"""
from __future__ import annotations

import pytest

from app.core import spec_guard

_SAFE_SPEC = """
import { test, expect } from '@playwright/test';

test('首页可见', async ({ page }) => {
  await page.goto(process.env.CAMELTV_BASE_URL || 'http://localhost:5173');
  await expect(page.locator('h1')).toBeVisible();
  const res = await page.waitForResponse((r) => r.url().includes('/api/home'));
  expect(res.status()).toBe(200);
});
"""


class TestDangerousPatterns:
    @pytest.mark.parametrize(
        "snippet,rule",
        [
            ("const cp = require('child_process');\ncp.execSync('rm -rf /');", "child_process"),
            ("import { execSync } from 'child_process';\nexecSync('whoami');", "child_process"),
            ("execSync('curl http://169.254.169.254/latest/meta-data/');", "process-spawn"),
            ("spawn('bash', ['-c', 'id']);", "process-spawn"),
            ("const fs = require('fs');\nfs.writeFileSync('/etc/passwd', 'x');", "fs-module"),
            ("fs.appendFileSync('a.txt', 'x');", "fs-write"),
            ("const net = require('net');", "raw-network"),
            ("const http = require('http');", "raw-network"),
            ("eval('1+1');", "dynamic-eval"),
            ("const t = process.env.SECRET_KEY;", "process-env"),
            ("const t = process.env['DATABASE_URL'];", "process-env"),
        ],
    )
    def test_dangerous_snippets_are_reported(self, snippet, rule):
        findings = spec_guard.assert_spec_safe(snippet)
        assert findings, f"未拦截: {snippet!r}"
        assert any(rule in item for item in findings), findings

    def test_findings_include_line_number_and_reason(self):
        code = "// 注释\nimport { execSync } from 'child_process';\nexecSync('id');"
        findings = spec_guard.assert_spec_safe(code)
        assert any("第 2 行" in item for item in findings)
        assert all("[" in item and "]" in item for item in findings)

    def test_raise_if_unsafe_produces_readable_error(self):
        with pytest.raises(spec_guard.SpecNotAllowedError) as exc:
            spec_guard.raise_if_unsafe("execSync('whoami');")
        message = str(exc.value)
        assert "拒绝执行" in message
        assert "execSync" in message or "process-spawn" in message


class TestLegitimateSpecsSurvive:
    def test_typical_playwright_spec_passes(self):
        assert spec_guard.assert_spec_safe(_SAFE_SPEC) == []

    def test_contract_env_vars_are_allowed(self):
        assert spec_guard.assert_spec_safe("const u = process.env.CAMELTV_BASE_URL;") == []

    def test_page_level_network_calls_are_allowed(self):
        """用例通过 page/request 出网是正常需求，不能被当成"直连网络模块"。"""
        code = (
            "await page.goto('/');\n"
            "const r = await page.request.get('/api/list');\n"
            "await page.waitForResponse('**/api/**');\n"
        )
        assert spec_guard.assert_spec_safe(code) == []

    def test_eslint_directive_comment_is_not_flagged(self):
        assert spec_guard.assert_spec_safe("// eslint-disable-next-line @typescript-eslint/no-explicit-any") == []

    def test_empty_input_is_safe(self):
        assert spec_guard.assert_spec_safe("") == []
        assert spec_guard.assert_spec_safe(None) == []  # type: ignore[arg-type]


class TestInterceptionHappensBeforeExecution:
    """DoD：含 execSync 的 spec **在执行前**被拒（不是执行后报错）。"""

    def test_playground_rejects_before_writing_or_spawning(self, monkeypatch):
        from fastapi import HTTPException

        from app.services import playground_service
        from app.schemas.playground import ExecuteRequest

        spawned: list[list[str]] = []

        def _record_run(args, **kwargs):
            spawned.append(args)
            raise AssertionError(f"危险代码竟然被执行: {args}")

        monkeypatch.setattr(playground_service.subprocess, "run", _record_run)
        monkeypatch.setattr(playground_service, "run_supervised", _record_run)

        with pytest.raises(HTTPException) as exc:
            playground_service.execute_spec(
                ExecuteRequest(spec_code="import { execSync } from 'child_process';\nexecSync('whoami');")
            )
        detail = str(exc.value.detail)
        assert exc.value.status_code == 400
        assert "拒绝执行" in detail
        assert "child_process" in detail or "execSync" in detail
        assert spawned == [], "拦截必须发生在起进程之前"

    def test_safe_spec_is_not_blocked_by_the_guard(self, monkeypatch):
        """守卫不能把正常代码也拦下来（否则会被绕过或关掉）。"""
        from app.services import playground_service
        from app.schemas.playground import ExecuteRequest

        captured: dict = {}

        class _Result:
            returncode = 1  # 让执行以"失败"结束，避免真的跑浏览器
            stdout = "stub"
            stderr = "stub"

        def _record_run(args, **kwargs):
            captured["args"] = args
            return _Result()

        monkeypatch.setattr(playground_service.subprocess, "run", _record_run)
        monkeypatch.setattr(playground_service, "run_supervised", _record_run)

        response = playground_service.execute_spec(
            ExecuteRequest(spec_code=_SAFE_SPEC)
        )
        assert "args" in captured, "正常代码应当走到执行阶段"
        assert response.passed is False
