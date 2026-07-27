"""Playground service — compile test cases to Playwright specs, execute them."""
from __future__ import annotations

import base64
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.schemas.playground import CompileRequest, CompileResponse, ExecuteRequest, ExecuteResponse, SourceType


# ── Gherkin → Playwright mapping ──────────────────────────────────────────

_ACTION_MAP: list[tuple[str, str]] = [
    # Navigation
    (r'Given\s+(?:I\s+)?(?:am\s+)?(?:on|visit|navigate\s+to)\s+["\'](.+?)["\']',
     r"await page.goto('\1');"),
    (r'Given\s+(?:the\s+)?(?:url|page)\s+is\s+["\'](.+?)["\']',
     r"await page.goto('\1');"),
    # Click
    (r'When\s+(?:I\s+)?click\s+["\'](.+?)["\']',
     r"await page.click('\1');"),
    (r'When\s+(?:I\s+)?click\s+(?:on\s+)?(?:the\s+)?["\'](.+?)["\']',
     r"await page.click('\1');"),
    # Type / Fill
    (r'When\s+(?:I\s+)?(?:type|fill|enter)\s+["\'](.+?)["\']\s+(?:in|into)\s+["\'](.+?)["\']',
     r"await page.fill('\2', '\1');"),
    (r'When\s+(?:I\s+)?(?:type|fill|enter)\s+["\'](.+?)["\']',
     r"await page.fill('input', '\1');"),
    # Assert visible text
    (r'Then\s+(?:I\s+)?(?:should\s+)?see\s+["\'](.+?)["\']',
     r"await expect(page.locator('body')).toContainText('\1');"),
    (r'Then\s+(?:the\s+)?(?:page|screen)\s+(?:should\s+)?(?:show|display|contain)\s+["\'](.+?)["\']',
     r"await expect(page.locator('body')).toContainText('\1');"),
    # Assert element visible
    (r'Then\s+(?:the\s+)?["\'](.+?)["\']\s+(?:should\s+)?(?:be\s+)?(?:visible|present)',
     r"await expect(page.locator('\1')).toBeVisible();"),
    # Assert URL
    (r'Then\s+(?:the\s+)?url\s+(?:should\s+)?(?:be|contain)\s+["\'](.+?)["\']',
     r"await expect(page).toHaveURL(/\1/);"),
    # Wait
    (r'When\s+(?:I\s+)?wait\s+(\d+)\s*(?:ms|milliseconds|seconds?s?)',
     r"await page.waitForTimeout(\1);"),
    (r'And\s+(?:I\s+)?wait\s+(\d+)\s*(?:ms|milliseconds|seconds?s?)',
     r"await page.waitForTimeout(\1);"),
    # Screenshot
    (r'Then\s+(?:I\s+)?(?:take|capture)\s+(?:a\s+)?screenshot',
     r"await page.screenshot({ path: 'playground-screenshot.png' });"),
]


def _gherkin_to_playwright(source: str) -> str:
    """Convert Gherkin Given/When/Then lines into Playwright test steps."""
    steps: list[str] = []
    test_name = "Playground Test"

    for line in source.strip().split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("Feature:"):
            if stripped.startswith("Feature:"):
                test_name = stripped.replace("Feature:", "").strip()
            continue

        matched = False
        for pattern, template in _ACTION_MAP:
            m = re.match(pattern, stripped, re.IGNORECASE)
            if m:
                # Replace capture groups in template
                result = template
                for i, group in enumerate(m.groups(), 1):
                    result = result.replace(f"\\{i}", group)
                steps.append(f"  {result}")
                matched = True
                break

        if not matched:
            # Unmatched line → comment + raw
            steps.append(f"  // TODO: {stripped}")
            steps.append(f"  // await page.???")

    joined_steps = "\n".join(steps) if steps else "  // No steps parsed"
    escaped_name = test_name.replace("'", "\\'")

    return f"""import {{ test, expect }} from '@playwright/test';

test('{escaped_name}', async ({{ page }}) => {{
{joined_steps}
}});
"""


def _markdown_to_playwright(source: str) -> str:
    """Extract code blocks or steps from Markdown, fall back to plain."""
    # Try to extract fenced code blocks first
    code_blocks = re.findall(r'```(?:gherkin|feature)?\n(.*?)```', source, re.DOTALL)
    if code_blocks:
        return "\n\n".join(_gherkin_to_playwright(block) for block in code_blocks)
    return _plain_to_playwright(source)


def _plain_to_playwright(source: str) -> str:
    """Simple template: wrap plain description in a Playwright skeleton."""
    escaped_desc = source.strip().replace("'", "\\'").replace("\n", "\\n")
    return f"""import {{ test, expect }} from '@playwright/test';

test('Playground Test', async ({{ page }}) => {{
  // Source: {escaped_desc}
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();
}});
"""


def compile_spec(req: CompileRequest) -> CompileResponse:
    """Compile a test case source into a Playwright .spec.ts."""
    t0 = time.perf_counter()

    if req.source_type == SourceType.gherkin:
        spec_code = _gherkin_to_playwright(req.source)
    elif req.source_type == SourceType.markdown:
        spec_code = _markdown_to_playwright(req.source)
    else:
        spec_code = _plain_to_playwright(req.source)

    compile_ms = (time.perf_counter() - t0) * 1000
    return CompileResponse(spec_code=spec_code, spec_type="playwright", compile_ms=round(compile_ms, 2))


def execute_spec(req: ExecuteRequest) -> ExecuteResponse:
    """Execute a Playwright spec in headless Chromium via subprocess.

    Writes spec to temp file, runs npx playwright test, captures output.
    Returns result with optional screenshot.
    """
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        spec_file = tmppath / "playground.spec.ts"
        spec_file.write_text(req.spec_code, encoding="utf-8")

        # Minimal Playwright config for this single spec
        config = tmppath / "playwright.config.ts"
        config.write_text(f"""import {{ defineConfig }} from '@playwright/test';
export default defineConfig({{
  testDir: '.',
  timeout: {req.timeout_ms},
  use: {{ headless: true, screenshot: 'on' }},
  reporter: [['line']],
}});
""", encoding="utf-8")

        try:
            result = subprocess.run(
                ["npx", "playwright", "test", str(spec_file), "--config", str(config)],
                capture_output=True,
                text=True,
                timeout=req.timeout_ms // 1000 + 15,
                cwd=str(tmppath),
            )
            passed = result.returncode == 0
            stdout = result.stdout or ""
            stderr = result.stderr or ""
        except subprocess.TimeoutExpired:
            passed = False
            stdout = ""
            stderr = "Execution timed out"
        except FileNotFoundError:
            passed = False
            stdout = ""
            stderr = "npx/playwright not found in PATH"

        # Look for screenshot
        screenshot_base64: Optional[str] = None
        screenshots = list(tmppath.glob("**/*.png"))
        if screenshots:
            try:
                screenshot_base64 = base64.b64encode(screenshots[0].read_bytes()).decode()
            except Exception:
                pass

        duration_ms = (time.perf_counter() - t0) * 1000
        return ExecuteResponse(
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            screenshot_base64=screenshot_base64,
            duration_ms=round(duration_ms, 2),
        )
