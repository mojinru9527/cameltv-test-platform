"""Playground service — compile test cases to Playwright specs, execute them."""
from __future__ import annotations

import base64
import json
import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from app.schemas.playground import (
    CompileRequest, CompileResponse, ExecuteRequest, ExecuteResponse, SourceType,
    PlaygroundBatchCompileResponse, PlaygroundCaseCompileItem,
    PlaygroundBatchRunResponse, PlaygroundCaseRunResult,
)

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
            steps.append(f"  // ⚠️ 未识别步骤（需人工补充）: {stripped}")
            steps.append(f"  // TODO: 请补充对应的 Playwright 操作")

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
            logger.warning("Gherkin 步骤解析失败，跳过")
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
                logger.warning("截图读取失败，按无截图处理")

        duration_ms = (time.perf_counter() - t0) * 1000
        return ExecuteResponse(
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            screenshot_base64=screenshot_base64,
            duration_ms=round(duration_ms, 2),
        )


# ── Batch 166：功能用例批量编译 / 批量执行 ──

def _get_project_cases(db, project_id: int, case_ids: list[int]):
    from sqlalchemy import select
    from app.models.test_case import TestCase

    rows = db.scalars(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestCase.id.in_(case_ids),
        )
    ).all()
    by_id = {r.id: r for r in rows}
    return [by_id[cid] for cid in case_ids if cid in by_id]


def _spec_has_todo(spec_code: str) -> bool:
    return "未识别步骤" in spec_code or "TODO" in spec_code


def compile_case_batch(db, project_id: int, case_ids: list[int]) -> PlaygroundBatchCompileResponse:
    """批量编译用例，不执行，供前端预览生成 spec。"""
    cases = _get_project_cases(db, project_id, case_ids)
    items: list[PlaygroundCaseCompileItem] = []
    for case in cases:
        source = build_gherkin_from_case(case)
        compiled = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        items.append(PlaygroundCaseCompileItem(
            case_id=case.id,
            case_title=case.title or "",
            spec_code=compiled.spec_code,
            has_todo=_spec_has_todo(compiled.spec_code),
        ))
    return PlaygroundBatchCompileResponse(total=len(items), items=items)


def run_case_batch(
    db,
    *,
    project_id: int,
    creator_id: int,
    case_ids: list[int],
    write_back_to_ui: bool,
    timeout_ms: int,
) -> PlaygroundBatchRunResponse:
    """批量编译 + 执行用例，回填用例结果，并可选回写 UI 任务。

    执行复用 execute_spec（临时目录 + headless Chromium），逐条串行执行。
    回写 UI 任务时，把生成 spec 落到 ui_runner 的 generated 目录，并创建
    关联用例的 UiTestJob；后续由 UI 自动化任务运行时生成 trace/report 产物。
    """
    from datetime import datetime, timezone
    from app.models.test_case import TestCase

    cases = _get_project_cases(db, project_id, case_ids)
    results: list[PlaygroundCaseRunResult] = []
    passed = 0
    failed = 0

    for case in cases:
        source = build_gherkin_from_case(case)
        compiled = compile_spec(CompileRequest(source=source, source_type=SourceType.gherkin))
        executed = execute_spec(ExecuteRequest(spec_code=compiled.spec_code, timeout_ms=timeout_ms))
        ok = executed.passed
        if ok:
            passed += 1
        else:
            failed += 1

        ui_job_id = None
        if write_back_to_ui:
            ui_job_id = _write_spec_as_ui_job(db, case, compiled.spec_code, creator_id, project_id)

        # 回填用例执行结果（不存大图，只存可追溯摘要）
        case.last_run_status = "pass" if ok else "fail"
        case.last_response_json = json.dumps({
            "source": "playground_batch",
            "passed": ok,
            "duration_ms": round(executed.duration_ms, 2),
            "stdout": (executed.stdout or "")[-2000:],
            "stderr": (executed.stderr or "")[-2000:],
            "ui_job_id": ui_job_id,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, default=str)

        results.append(PlaygroundCaseRunResult(
            case_id=case.id,
            case_title=case.title or "",
            spec_code=compiled.spec_code,
            passed=ok,
            stdout=executed.stdout or "",
            stderr=executed.stderr or "",
            screenshot_base64=executed.screenshot_base64,
            duration_ms=executed.duration_ms,
            ui_job_id=ui_job_id,
        ))

    db.commit()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "write_back_to_ui": write_back_to_ui,
        "items": [
            {
                "case_id": r.case_id,
                "case_title": r.case_title,
                "passed": r.passed,
                "duration_ms": r.duration_ms,
                "ui_job_id": r.ui_job_id,
            }
            for r in results
        ],
    }
    return PlaygroundBatchRunResponse(
        total=len(results),
        passed=passed,
        failed=failed,
        results=results,
        report=report,
    )


def _write_spec_as_ui_job(db, case, spec_code: str, creator_id: int, project_id: int) -> int | None:
    """把生成 spec 写入 ui_runner 的 generated 目录，并创建关联用例的 UI 任务。

    Batch 177（FIX-173-P1-08）：
    - 幂等：同一用例的 Playground 回写不再重复建任务（按 case_id + spec 查重，
      已存在则复用，修复生产 2 对完全重复任务）；
    - 绑定执行环境：默认取项目首个环境，修复「[Playground] 任务全部未绑定环境
      永远无法执行」的断链。
    """
    try:
        from app.services.playwright_executor import PLAYWRIGHT_DIR
        from app.schemas.ui_test import UiTestJobCreate
        from app.services import ui_test_service
        from app.models.environment import Environment
        from app.models.ui_test import UiTestJob
        from sqlalchemy import select

        generated_dir = PLAYWRIGHT_DIR / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        rel = f"generated/playground-case-{case.id}.spec.ts"
        (generated_dir / f"playground-case-{case.id}.spec.ts").write_text(spec_code, encoding="utf-8")

        # 幂等：同 (case_id, spec) 已存在任务则复用，避免重复堆积
        existing = db.scalar(
            select(UiTestJob).where(
                UiTestJob.project_id == project_id,
                UiTestJob.case_id == case.id,
                UiTestJob.test_spec == rel,
            ).order_by(UiTestJob.id.desc())
        )
        if existing is not None:
            return int(existing.id)

        # 绑定执行环境：默认取项目第一个环境（修复未绑定环境无法执行）
        default_env = db.scalar(
            select(Environment).where(
                Environment.project_id == project_id,
            ).order_by(Environment.id.asc())
        )

        job = ui_test_service.create_job(
            db,
            UiTestJobCreate(
                name=f"[Playground] {case.title}"[:200],
                description="由 Playground 功能用例批量编译生成",
                test_spec=rel,
                browser="chromium",
                environment_id=default_env.id if default_env else None,
                case_id=case.id,
            ),
            creator_id,
            project_id,
        )
        return int(job["id"])
    except Exception:
        logger.exception("Playground 回写 UI 任务失败: case=%s", getattr(case, "id", None))
        return None
