"""Playground service — compile test cases to Playwright specs, execute them."""
from __future__ import annotations

import base64
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.schemas.playground import CompileRequest, CompileResponse, ExecuteRequest, ExecuteResponse, SourceType

# 中文 Gherkin 引号集合（「」 “” " 和 '）
_OPEN_QUOTES = r'[「“"\']'
_CLOSE_QUOTES = r'[」”"\']'

# 看起来像 CSS 选择器：以 # . [ @ 或标签+[ 开头（用于点击目标判断）
_SELECTOR_LIKE = re.compile(r'^(?:#|\.|\[|@|[a-zA-Z][\w-]*\[)')


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
    # ── 中文 Gherkin 映射（batch-74，支持「当/且/则」前缀）──
    # 导航：打开/访问/进入/前往/来到/浏览 "url"
    (rf'(?:当|且|则)?\s*(?:我\s*)?(?:打开|访问|进入|前往|来到|浏览)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}',
     r"await page.goto('\1');"),
    # 点击：点击/单击/按下 "选择器"
    (rf'(?:当|且|则)?\s*(?:我\s*)?(?:点击|单击|按下)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}',
     r"await page.click('\1');"),
    # 输入：在 "选择器" 输入/填写 "文本"
    (rf'(?:当|且|则)?\s*(?:我\s*)?在\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}\s*(?:输入|填写|填入|键入)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}',
     r"await page.fill('\1', '\2');"),
    # 输入（倒装）：输入 "文本" 到 "选择器"
    (rf'(?:当|且|则)?\s*(?:我\s*)?(?:输入|填写|填入|键入)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}\s*(?:到|至|于)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}',
     r"await page.fill('\2', '\1');"),
    # 断言文本：看到/显示/包含 "文本"
    (rf'(?:当|且|则)?\s*(?:我\s*)?(?:应该\s*)?(?:看到|可见|显示|出现|包含|能看到|应显示)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}',
     r"await expect(page.locator('body')).toContainText('\1');"),
    # 断言元素可见："选择器" 可见/出现/显示
    (rf'(?:当|且|则)?\s*(?:我\s*)?(?:应该\s*)?{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}\s*(?:应\s*)?(?:可见|出现|显示)',
     r"await expect(page.locator('\1')).toBeVisible();"),
    # 断言 URL：url/地址 应包含/变为 "x"
    (rf'(?:当|且|则)?\s*(?:url|URL|地址|网址)\s*(?:应该|应)?\s*(?:包含|变为|跳转到|是)\s*{_OPEN_QUOTES}(.+?){_CLOSE_QUOTES}',
     r"await expect(page).toHaveURL(/\1/);"),
    # 等待：等待 N 秒（转毫秒）
    (r'(?:当|且|则)?\s*(?:我\s*)?(?:等待|等)\s*(\d+)\s*(?:秒|s)',
     r"await page.waitForTimeout(\1 * 1000);"),
    # 等待：等待 N 毫秒
    (r'(?:当|且|则)?\s*(?:我\s*)?(?:等待|等)\s*(\d+)\s*(?:毫秒|ms)',
     r"await page.waitForTimeout(\1);"),
    # 截图（可用 PLAYGROUND_SCREENSHOT 环境变量重定向输出目录）
    (r'(?:当|且|则)?\s*(?:我\s*)?(?:截图|截图保存|拍个截图)',
     r"await page.screenshot({ path: process.env.PLAYGROUND_SCREENSHOT || 'playground-screenshot.png' });"),
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
                    escaped = group.replace("\\", "\\\\").replace("'", "\\'")
                    result = result.replace(f"\\{i}", escaped)
                steps.append(f"  {result}")
                matched = True
                break

        if not matched:
            # Unmatched line → comment + raw
            steps.append(f"  // TODO: {stripped}")
            steps.append(f"  // await page.???")

    steps = [_rewrite_click_target(step) for step in steps]
    joined_steps = "\n".join(steps) if steps else "  // No steps parsed"
    escaped_name = test_name.replace("'", "\\'")

    return f"""import {{ test, expect }} from '@playwright/test';

test('{escaped_name}', async ({{ page }}) => {{
{joined_steps}
}});
"""


def _rewrite_click_target(step: str) -> str:
    """把 `page.click('文本')` 重写为 getByText，让中文自然步骤可执行。"""
    m = re.match(r"^(\s*)await page\.click\('(.+)'\);$", step)
    if not m:
        return step
    indent, target = m.group(1), m.group(2)
    if _SELECTOR_LIKE.match(target):
        return f"{indent}await page.click('{target}');"
    return f"{indent}await page.getByText('{target}').first().click();"


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


def build_gherkin_from_case(case) -> str:
    """把功能用例（TestCase ORM）的 steps JSON 组装为 Gherkin 源文本。

    每条步骤按 `当 {desc}` 输出（desc 通常已经是动作句）；预期结果作为独立
    `则 看到/显示` 行（仅当含可断言关键词），无法映射的步骤编译时保持 TODO 降级。
    """
    title = (case.title or "Playground Test").strip()
    lines = [f"Feature: {title}"]
    if getattr(case, "preconditions", "") and case.preconditions != "[]":
        try:
            pre = json.loads(case.preconditions)
            if isinstance(pre, list):
                for item in pre:
                    if isinstance(item, str) and item.strip():
                        lines.append(f"当 {item.strip()}")
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    try:
        steps = json.loads(case.steps or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        steps = []
    for item in steps if isinstance(steps, list) else []:
        if not isinstance(item, dict):
            continue
        desc = (item.get("desc") or item.get("step") or "").strip()
        expected = (item.get("expected") or "").strip()
        if desc:
            lines.append(f"当 {desc}")
        if expected and any(kw in expected for kw in ("看到", "显示", "包含", "可见", "出现", "url", "URL")):
            lines.append(f"则 {expected}")
    return "\n".join(lines)


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
