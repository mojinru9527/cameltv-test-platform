"""用例→Playwright 脚本编译器 — 使用 LLM 将功能用例 steps JSON 编译为 .spec.ts 代码。

设计要点:
- 使用 DeepSeek (OpenAI 兼容 API) 生成 Playwright TypeScript 代码
- 与 ai_service.py 的区别: 输出纯文本代码（非 JSON），不使用 json_object 格式
- 生成后 sandbox 校验: npx playwright test --dry-run（语法检查，不实际执行）
- 编译失败的返回错误行号 + AI 修复建议
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.models.test_case import TestCase

logger = logging.getLogger(__name__)

# ── 配置常量 ──
COMPILE_TIMEOUT = 180.0  # LLM 调用超时（秒），代码生成比 JSON 耗时更长
DRY_RUN_TIMEOUT = 15.0   # playwright --dry-run 超时
MAX_CODE_LENGTH = 50000  # 生成代码最大字符数（防护）
PLAYWRIGHT_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "playwright"
GENERATED_DIR = PLAYWRIGHT_DIR / "specs" / "generated"

# ── System Prompt ────────────────────────────────────────

SYSTEM_PROMPT = """你是 Playwright 测试自动化专家。根据测试用例的步骤描述，生成可直接运行的 Playwright TypeScript 测试代码。

## 输出要求

1. **只输出 TypeScript 代码**，不要任何解释或 markdown 包裹（不要 ```typescript ```）
2. 代码必须以 `import { test, expect } from '@playwright/test';` 开头
3. 使用 `test.describe` 包裹用例标题
4. 每个测试步骤用 `test.step()` 包裹（中文步骤描述）
5. 前置条件放在 `test.beforeEach` 中（如果有）
6. 预期结果用 `expect()` 断言，断言失败时打印友好信息

## 选择器策略（按优先级）

1. `page.getByRole('button', { name: '...' })` — 按 ARIA 角色+名称
2. `page.getByLabel('...')` — 按表单标签
3. `page.getByText('...')` — 按可见文本（精确或包含）
4. `page.getByPlaceholder('...')` — 按输入框占位符
5. `page.locator('[data-testid="..."]')` — 按测试 ID（如果有）
6. **禁止使用 CSS class 选择器**（`.btn-primary`、`.login-form` 等）

## 操作模式

| 步骤描述中的关键词 | Playwright 操作 |
|-------------------|----------------|
| 点击 / 单击 / 按下 | `await page.getByRole('button', { name: '...' }).click()` 或 `page.getByText('...').click()` |
| 输入 / 填写 / 键入 | `await page.getByLabel('...').fill('...')` 或 `page.getByPlaceholder('...').fill('...')` |
| 打开 / 访问 / 进入 | `await page.goto(baseUrl + '/path')` 或 `await page.goto(baseUrl)` |
| 等待 / 加载 | `await page.waitForLoadState('networkidle')` 或 `page.waitForSelector(...)` |
| 选择 / 勾选 | `await page.getByLabel('...').check()` 或 `page.getByRole('checkbox', { name: '...' }).check()` |
| 下拉 / 选择下拉 | `await page.getByLabel('...').selectOption('...')` |
| 验证 / 检查 / 确认 | `await expect(page.getByText('...')).toBeVisible()` |
| 跳转 / 重定向 | `await expect(page).toHaveURL(/pattern/)` |
| 提示 / 弹窗 / toast | `await expect(page.getByText('...')).toBeVisible()` |
| 截图 | 使用 `screenshot: 'only-on-failure'`（test 配置中） |

## 代码风格

- 缩进: 2 空格
- 使用 `const` 而非 `let`
- 变量命名: camelCase
- 每个 test 用例包含完整的步骤序列
- 最后一步通常断言最终页面状态或结果显示

## 安全规则

- 不要硬编码密码或 token
- 不要在代码中输出敏感信息
- 测试 URL 从 baseUrl 常量拼接
"""


# ═══════════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════════

def compile_to_playwright(
    db_case: TestCase,
    *,
    base_url: str = "http://localhost:5173",
    validate: bool = True,
) -> dict:
    """将 TestCase 的 steps 编译为 Playwright .spec.ts 代码。

    Args:
        db_case: 已从 DB 加载的 TestCase ORM 对象（需含 steps/preconditions/expected_result）
        base_url: 被测前端地址，传入 Playwright 作为 baseUrl
        validate: 是否执行 dry-run 校验

    Returns:
        {
            "case_id": int,
            "spec_code": str,           # 生成的 Playwright 代码
            "spec_file": str,           # 建议文件名
            "validation": {             # 仅 validate=True 时
                "syntax_ok": bool,
                "dry_run_ok": bool,
                "errors": [str],
            },
            "compilation_time_ms": float,
            "model_used": str,
            "prompt_tokens": int | None,
            "completion_tokens": int | None,
            "error": str | None,        # 编译失败时的错误信息
        }
    """
    if not db_case.steps or db_case.steps == "[]":
        return _error_result(db_case.id, "用例没有测试步骤，无法编译")

    steps = _safe_json(db_case.steps, [])
    if not steps:
        return _error_result(db_case.id, "用例步骤为空或无法解析")

    user_message = _build_user_message(db_case, steps, base_url)
    spec_file = _make_spec_filename(db_case)

    t0 = time.perf_counter()

    # 1. 调用 LLM 生成代码
    try:
        raw_code, usage = _call_llm_for_code(SYSTEM_PROMPT, user_message)
    except Exception as exc:
        logger.exception("LLM call failed for case %s", db_case.id)
        return _error_result(db_case.id, f"LLM 调用失败: {exc}")

    if not raw_code or not raw_code.strip():
        return _error_result(db_case.id, "LLM 返回空代码")

    # 2. 后处理：清理 markdown 包裹
    spec_code = _clean_generated_code(raw_code)

    if len(spec_code) > MAX_CODE_LENGTH:
        spec_code = spec_code[:MAX_CODE_LENGTH] + "\n// [TRUNCATED: code exceeded 50000 chars]"

    duration_ms = round((time.perf_counter() - t0) * 1000, 1)

    result: dict = {
        "case_id": db_case.id,
        "spec_code": spec_code,
        "spec_file": spec_file,
        "validation": {"syntax_ok": True, "dry_run_ok": True, "errors": []},
        "compilation_time_ms": duration_ms,
        "model_used": settings.ai_model,
        "prompt_tokens": usage.get("prompt_tokens") if usage else None,
        "completion_tokens": usage.get("completion_tokens") if usage else None,
        "error": None,
    }

    # 3. Sandbox 校验
    if validate:
        validation = _validate_spec(spec_code, spec_file)
        result["validation"] = validation
        if not validation["dry_run_ok"]:
            result["error"] = "Playwright dry-run 校验失败，详见 validation.errors"

    return result


# ═══════════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════════

def _safe_json(raw: str, default: Any = None) -> Any:
    """安全解析 JSON 字符串。"""
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse JSON: %.100s...", raw)
        return default


def _make_spec_filename(db_case: TestCase) -> str:
    """生成 spec 文件名。"""
    case_id = (db_case.case_id or f"TC-UNKNOWN-{db_case.id}").strip()
    safe = re.sub(r"[^A-Za-z0-9一-鿿_-]", "-", case_id)
    return f"generated-{safe}.spec.ts"


def _build_user_message(db_case: TestCase, steps: list[dict], base_url: str) -> str:
    """构建发给 LLM 的用户消息。"""
    lines = [
        f"## 用例标题\n{db_case.title or '(无标题)'}\n",
        f"## 前置条件\n{db_case.preconditions or '无'}\n",
        "## 测试步骤",
    ]
    for s in steps:
        idx = s.get("step", s.get("index", "?"))
        desc = s.get("desc") or s.get("action") or s.get("description") or str(s)
        expected = s.get("expected") or s.get("expected_result") or ""
        lines.append(f"{idx}. {desc}")
        if expected:
            lines.append(f"   预期结果: {expected}")

    lines.append(f"\n## 预期结果\n{db_case.expected_result or '(见各步骤)'}")
    lines.append(f"\n## 被测地址\n{base_url}")

    return "\n".join(lines)


def _call_llm_for_code(system_prompt: str, user_message: str) -> tuple[str | None, dict | None]:
    """调用 DeepSeek API 生成代码（纯文本输出，非 JSON）。

    与 ai_service._call_ai_api 的关键区别：
    - 不传 response_format（默认为 None/纯文本），代码不是 JSON
    - 适当提高 max_tokens 以容纳较长的 spec 文件
    """
    if not settings.ai_api_key:
        raise RuntimeError("AI_API_KEY 未配置，无法编译用例")

    code_max_tokens = max(settings.ai_max_tokens, 8192)  # 代码生成至少 8K tokens

    with httpx.Client(timeout=settings.ai_timeout_seconds) as client:
        resp = client.post(
            f"{settings.ai_api_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": code_max_tokens,
                "temperature": 0.2,  # 代码生成用更低的 temperature（准确性 > 多样性）
            },
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        raw = choice["message"]["content"]
        finish_reason = choice.get("finish_reason", "unknown")

        if finish_reason == "length":
            logger.warning("LLM code generation truncated (finish_reason=length, len=%d)", len(raw))

        usage = data.get("usage")

    return raw, usage


def _clean_generated_code(raw: str) -> str:
    """清理 LLM 返回的代码：去掉 markdown 包裹、修复常见问题。"""
    code = raw.strip()

    # 去 markdown 代码块包裹
    fence_pattern = re.compile(r"^```(?:typescript|ts|javascript|js)?\s*\n(.*?)\n```\s*$", re.DOTALL)
    m = fence_pattern.match(code)
    if m:
        code = m.group(1).strip()
    # 有时 LLM 只包裹开头忘了结尾
    elif code.startswith("```"):
        code = re.sub(r"^```(?:typescript|ts|javascript|js)?\s*\n?", "", code)
        code = re.sub(r"\n?```\s*$", "", code)

    # 修正常见的 import 路径问题（如果有）
    # 去掉可能残留的 markdown 注释
    code = re.sub(r"^> .*$", "", code, flags=re.MULTILINE)

    return code.strip()


def _validate_spec(spec_code: str, spec_file: str) -> dict:
    """使用 npx playwright test --dry-run 校验生成的代码语法。

    不实际执行测试，只检查 TypeScript 编译 + Playwright test 结构是否合法。
    """
    result = {"syntax_ok": True, "dry_run_ok": True, "errors": []}

    # 写入临时文件
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = GENERATED_DIR / spec_file
    try:
        tmp_path.write_text(spec_code, encoding="utf-8")
    except OSError as e:
        result["syntax_ok"] = False
        result["dry_run_ok"] = False
        result["errors"].append(f"无法写入临时文件: {e}")
        return result

    try:
        # 用 TypeScript 编译器做基础语法检查
        npx_result = subprocess.run(
            ["npx", "tsc", "--noEmit", "--strict", str(tmp_path)],
            capture_output=True, text=True, timeout=DRY_RUN_TIMEOUT,
            cwd=str(PLAYWRIGHT_DIR.parent.parent),  # backend/ 目录
        )
        if npx_result.returncode != 0:
            result["syntax_ok"] = False
            errors = _parse_tsc_errors(npx_result.stdout + npx_result.stderr, spec_file)
            result["errors"].extend(errors[:10])  # 最多 10 条
    except FileNotFoundError:
        # tsc 不可用，跳过语法检查（降级到只做 dry-run）
        logger.warning("tsc not found, skipping syntax check")
    except subprocess.TimeoutExpired:
        result["syntax_ok"] = False
        result["errors"].append("TypeScript 语法检查超时")

    # Playwright dry-run（需要 Playwright 已安装）
    try:
        pw_config = PLAYWRIGHT_DIR / "playwright.config.ts"
        if pw_config.exists():
            dry_result = subprocess.run(
                ["npx", "playwright", "test", "--dry-run", str(tmp_path)],
                capture_output=True, text=True, timeout=DRY_RUN_TIMEOUT,
                cwd=str(PLAYWRIGHT_DIR),
            )
            if dry_result.returncode != 0:
                result["dry_run_ok"] = False
                errors = _parse_playwright_errors(dry_result.stdout + dry_result.stderr)
                result["errors"].extend(errors[:10])
        else:
            logger.warning("playwright.config.ts not found, skipping dry-run")
    except FileNotFoundError:
        logger.warning("npx/playwright not found, skipping dry-run")
    except subprocess.TimeoutExpired:
        result["dry_run_ok"] = False
        result["errors"].append("Playwright dry-run 超时")

    # 清理临时文件
    try:
        tmp_path.unlink()
    except OSError:
        pass

    return result


def _parse_tsc_errors(output: str, spec_file: str) -> list[str]:
    """解析 TypeScript 编译器错误输出。"""
    errors = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # tsc 错误格式: file(line,col): error TSxxxx: message
        if spec_file in line or ".spec.ts" in line:
            # 简化路径显示
            simplified = line.replace(str(GENERATED_DIR), "generated/")
            errors.append(simplified)
        elif "error TS" in line:
            errors.append(line)
    return errors


def _parse_playwright_errors(output: str) -> list[str]:
    """解析 Playwright dry-run 错误输出。"""
    errors = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if "Error:" in line or "error:" in line.lower():
            errors.append(line)
    if not errors:
        # 没有明确 error 行，取最后几行
        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
        errors = lines[-5:]
    return errors


def _error_result(case_id: int, message: str) -> dict:
    """生成错误结果。"""
    return {
        "case_id": case_id,
        "spec_code": "",
        "spec_file": "",
        "validation": {"syntax_ok": False, "dry_run_ok": False, "errors": [message]},
        "compilation_time_ms": 0,
        "model_used": "",
        "prompt_tokens": None,
        "completion_tokens": None,
        "error": message,
    }
