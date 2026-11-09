"""本地执行器（Batch 258 / B1-5）：接口用例与 Web 用例的真实执行。

两种 `kind`：
  - `api`：httpx 直发请求 + 断言求值（请求/响应逐条落盘，失败可回放）；
  - `web`：Playwright 驱动 + 步骤解释器（截图/控制台落盘）。

**诚实原则**：依赖不可用时返回 `failed` 并写明原因，绝不伪造通过。
步骤解释器与浏览器解耦（`page_factory` 可注入），因此无需浏览器即可单测。
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

SUPPORTED_KINDS = ("api", "web", "ui")
RESULT_FILE = "results.json"
_INDEX = re.compile(r"\[(\d+)\]")


class ExecutorUnavailable(RuntimeError):
    """本地缺少执行依赖（例如未安装 Playwright）。"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── 断言求值 ───────────────────────────────────────────────────

def _dig(data: Any, path: str) -> Any:
    """支持 `$.a.b[0].c` 形式的取值；取不到返回 None。"""
    if not path:
        return None
    cursor = path.strip()
    if cursor.startswith("$"):
        cursor = cursor[1:]
    for match in _INDEX.finditer(cursor):
        cursor = cursor.replace(match.group(0), "." + match.group(1), 1)
    current = data
    for token in [part for part in cursor.split(".") if part]:
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return None
            continue
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue
        return None
    return current


def evaluate_assertions(
    *,
    status_code: int | None,
    text: str,
    payload: Any,
    assertions: list[dict],
    elapsed_ms: float | None = None,
) -> list[dict]:
    """返回逐条断言结果；未识别的断言类型记为失败（不静默放过）。"""
    results: list[dict] = []
    for index, assertion in enumerate(assertions or []):
        kind = str(assertion.get("type") or "").strip()
        expected = assertion.get("expected")
        passed = False
        actual: Any = None
        if kind in {"status", "status_code"}:
            # Batch 266：库内生成的用例用 `status_code` + `operator`（gte/lt…）表达区间，
            # 节点此前只认等值 `status`，导致这类断言一律判失败。这里补齐算子，
            # 仍保持"未识别即失败"的原则（未知算子不放过）。
            actual = status_code
            operator = str(assertion.get("operator") or "eq").strip().lower()
            if status_code is None:
                passed = False
            elif operator in {"gte", "ge", ">="}:
                passed = status_code >= expected
            elif operator in {"gt", ">"}:
                passed = status_code > expected
            elif operator in {"lte", "le", "<="}:
                passed = status_code <= expected
            elif operator in {"lt", "<"}:
                passed = status_code < expected
            elif operator in {"eq", "equals", "=="}:
                passed = status_code == expected
            else:
                actual = f"未识别的断言算子: {operator or '(空)'}"
                passed = False
        elif kind in {"json_path", "jsonpath"}:
            # Batch 266：库内生成的用例用小写 `jsonpath`；且 `expected=null` 表示
            # "该路径存在且非空"，而不是"等于 null"。
            actual = _dig(payload, str(assertion.get("path") or ""))
            if expected is None:
                passed = actual not in (None, "", [], {})
            else:
                passed = actual == expected
        elif kind == "response_time":
            # Batch 266：`expected` 是毫秒上限（响应时间断言）。
            actual = elapsed_ms
            passed = elapsed_ms is not None and expected is not None and elapsed_ms <= float(expected)
        elif kind == "text_contains":
            actual = expected in (text or "") if expected is not None else False
            passed = bool(actual)
        elif kind == "not_empty":
            actual = _dig(payload, str(assertion.get("path") or ""))
            passed = actual not in (None, "", [], {})
        else:
            actual = f"未识别的断言类型: {kind or '(空)'}"
            passed = False
        results.append(
            {
                "index": index,
                "type": kind,
                "path": assertion.get("path"),
                "expected": expected,
                "actual": actual if not isinstance(actual, (bytes, bytearray)) else "<binary>",
                "passed": bool(passed),
            }
        )
    return results


# ── API 执行 ───────────────────────────────────────────────────

def _default_api_client_factory(timeout: float):
    import httpx

    # trust_env=False：被测系统是内网服务，绝不能被操作系统的全局代理接管
    # （否则请求会绕到公司/本机代理，既可能失败也把内网目标暴露给代理）。
    # 访问平台的调用另走 cameltv_node.cli.call()，那里保留 proxy 支持。
    return httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False)


def run_api_cases(
    cases: list[dict],
    *,
    evidence_dir: str | Path,
    client_factory: Callable[[float], Any] | None = None,
    base_url: str = "",
    default_timeout: float = 30.0,
) -> dict:
    """顺序执行接口用例，逐条落盘请求/响应证据。"""
    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    factory = client_factory or _default_api_client_factory
    case_results: list[dict] = []
    with factory(default_timeout) as client:
        for case in cases:
            case_results.append(
                _run_one_api_case(
                    client,
                    case,
                    directory=directory,
                    base_url=base_url,
                    default_timeout=default_timeout,
                )
            )
    return _summarize(case_results)


def _run_one_api_case(
    client: Any,
    case: dict,
    *,
    directory: Path,
    base_url: str,
    default_timeout: float,
) -> dict:
    case_id = str(case.get("id") or case.get("name") or f"case-{len(case)}")
    request_spec = case.get("request") or {}
    url = str(request_spec.get("url") or "")
    if base_url and not url.lower().startswith(("http://", "https://")):
        url = base_url.rstrip("/") + "/" + url.lstrip("/")
    method = str(request_spec.get("method") or "GET").upper()
    headers = request_spec.get("headers") or {}
    body = request_spec.get("body")
    timeout = float(request_spec.get("timeout") or default_timeout)

    record: dict = {
        "id": case_id,
        "name": case.get("name") or case_id,
        "method": method,
        "url": url,
        "started_at": _now(),
    }
    status_code = None
    text = ""
    payload: Any = None
    try:
        response = client.request(
            method,
            url,
            headers=headers,
            content=(
                json.dumps(body, ensure_ascii=False).encode("utf-8")
                if body is not None
                else None
            ),
            timeout=timeout,
        )
        status_code = int(response.status_code)
        text = response.text or ""
        try:
            payload = response.json()
        except ValueError:
            payload = None
        record["status_code"] = status_code
        record["elapsed_ms"] = (
            round(response.elapsed.total_seconds() * 1000, 1)
            if getattr(response, "elapsed", None)
            else None
        )
    except Exception as exc:  # 网络/超时都如实记失败，不吞异常
        record["error"] = f"{type(exc).__name__}: {exc}"

    record["assertions"] = evaluate_assertions(
        status_code=status_code,
        text=text,
        payload=payload,
        assertions=case.get("assertions") or [],
        elapsed_ms=record.get("elapsed_ms"),
    )
    record["passed"] = bool(record["assertions"]) and all(
        item["passed"] for item in record["assertions"]
    ) and "error" not in record
    record["finished_at"] = _now()

    _write_json(directory / f"{_slug(case_id)}.request.json", {"method": method, "url": url, "headers": headers, "body": body})
    _write_json(
        directory / f"{_slug(case_id)}.response.json",
        {
            "status_code": status_code,
            "headers": dict(getattr(response, "headers", {}) or {}) if status_code is not None else {},
            "body": payload if payload is not None else text[:200_000],
            "error": record.get("error"),
        },
    )
    return record


# ── Web 执行 ───────────────────────────────────────────────────

def _any_visible(page: Any, selector: str) -> bool:
    """任一匹配元素可见即视为可见（Batch 266 / C264-4）。

    `page.is_visible(selector)` 只看**第一个**匹配元素，而 `text=` 这类选择器常匹配多个，
    与 `wait_visible`（任一匹配可见）结论可能相反。这里统一为"任一匹配可见"。
    """
    try:
        locator = page.locator(selector)
        count = locator.count()
    except AttributeError:
        # 测试替身等不实现 locator 的页面对象：退回单匹配语义（真实 Playwright page 有 locator）。
        try:
            return bool(page.is_visible(selector))
        except Exception:  # noqa: BLE001
            return False
    except Exception:  # noqa: BLE001 - 选择器非法按不可见处理（失败可见）
        return False
    for index in range(min(int(count), 20)):
        try:
            if locator.nth(index).is_visible():
                return True
        except Exception:  # noqa: BLE001 - 单个元素查询失败不影响其余匹配
            continue
    return False

def _default_page_factory(headless: bool = True):
    """真实 Playwright 适配器；未安装即明确报错（不降级成"通过"）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - 依赖本机环境
        raise ExecutorUnavailable(
            "未安装 Playwright：请执行 `pip install playwright && playwright install chromium`"
        ) from exc

    class _PageContext:
        def __enter__(self):
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=headless)
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
            return self._page

        def __exit__(self, *args):
            for closer in (self._context, self._browser):
                try:
                    closer.close()
                except Exception:  # noqa: BLE001 - 关闭失败不应掩盖用例结论
                    pass
            self._playwright.stop()
            return False

    return _PageContext()


def run_web_cases(
    cases: list[dict],
    *,
    evidence_dir: str | Path,
    page_factory: Callable[[], Any] | None = None,
    base_url: str = "",
) -> dict:
    """顺序执行 Web 用例；**每条用例独立浏览器上下文**（Batch 266 / C264-4）。

    此前一个 job 只建一次 context/page，用例共享 cookie 与 localStorage，
    站点记住偏好后渲染变化，导致依赖页面状态的断言在连续访问时翻转
    （实测 30 条里 3 条）。现在按用例重建上下文，隔离状态。
    """
    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    factory = page_factory or _default_page_factory
    case_results: list[dict] = []
    for case in cases:
        try:
            with factory() as page:
                case_results.append(
                    _run_one_web_case(page, case, directory=directory, base_url=base_url)
                )
        except ExecutorUnavailable:
            # 环境级不可用（如未安装 Playwright）必须冒泡：不许把"跑不起来"降级成"用例失败"。
            raise
        except Exception as exc:  # noqa: BLE001 - 单条用例失败不得拖垮整个 job
            case_results.append(
                {
                    "id": str(case.get("id") or case.get("name") or "case"),
                    "name": case.get("name") or case.get("id") or "case",
                    "steps": [],
                    "passed": False,
                    "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                    "finished_at": _now(),
                }
            )
    return _summarize(case_results)


def _run_one_web_case(page: Any, case: dict, *, directory: Path, base_url: str) -> dict:
    case_id = str(case.get("id") or case.get("name") or "case")
    slug = _slug(case_id)
    record: dict = {"id": case_id, "name": case.get("name") or case_id, "steps": [], "started_at": _now()}
    console_errors: list[str] = []
    if hasattr(page, "on"):
        try:
            page.on("pageerror", lambda error: console_errors.append(str(error)))
        except Exception:  # noqa: BLE001 - 记录器不可用不影响执行
            pass

    failure: str | None = None
    for index, step in enumerate(case.get("steps") or []):
        action = str(step.get("action") or "").strip()
        target = step.get("selector") or ""
        try:
            if action == "goto":
                url = str(step.get("url") or "")
                if base_url and not url.lower().startswith(("http://", "https://")):
                    url = base_url.rstrip("/") + "/" + url.lstrip("/")
                page.goto(url, wait_until=step.get("wait_until") or "domcontentloaded")
            elif action == "click":
                page.click(str(target))
            elif action == "fill":
                page.fill(str(target), str(step.get("value") or ""))
            elif action == "press":
                page.press(str(target), str(step.get("key") or "Enter"))
            elif action == "wait_visible":
                page.wait_for_selector(str(target), state="visible", timeout=int(step.get("timeout_ms") or 15000))
            elif action == "expect_visible":
                visible = _any_visible(page, str(target))
                if visible != bool(step.get("expected", True)):
                    failure = f"步骤 {index} expect_visible 不满足: {target}"
            elif action == "expect_text":
                actual_text = page.inner_text(str(target))
                if str(step.get("expected") or "") not in actual_text:
                    failure = f"步骤 {index} expect_text 不包含 {step.get('expected')!r}"
            elif action == "wait":
                page.wait_for_timeout(int(step.get("ms") or 500))
            else:
                failure = f"步骤 {index} 未知动作: {action or '(空)'}"
        except Exception as exc:  # noqa: BLE001 - 单步异常记为用例失败，不拖垮 job
            failure = f"步骤 {index} {action or '(空)'} 执行异常: {type(exc).__name__}: {str(exc)[:120]}"

        record["steps"].append({"index": index, "action": action, "selector": target, "ok": failure is None})
        if failure:
            break

    try:
        page.screenshot(path=str(directory / f"{slug}.png"), full_page=bool(case.get("full_page", True)))
        record["screenshot"] = f"{slug}.png"
    except Exception as exc:  # noqa: BLE001 - 截图失败不改变用例结论
        record["screenshot_error"] = f"{type(exc).__name__}: {exc}"

    _write_json(directory / f"{slug}.console.json", {"errors": console_errors})
    record["console_errors"] = console_errors
    if failure:
        record["error"] = failure
    record["passed"] = failure is None and not console_errors
    record["finished_at"] = _now()
    return record


# ── 工具 ───────────────────────────────────────────────────────

def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return cleaned or "case"


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _summarize(case_results: list[dict]) -> dict:
    passed = sum(1 for item in case_results if item.get("passed"))
    return {
        "total": len(case_results),
        "passed": passed,
        "failed": len(case_results) - passed,
        "all_pass": bool(case_results) and passed == len(case_results),
        "cases": case_results,
        "finished_at": _now(),
    }

# ── ui 模式：执行控制面下发的 Playwright spec（batch-277b / P0-4）─────────
_SPEC_ENTRY = re.compile(r"^[A-Za-z0-9._/-]+$")


def _safe_rel_path(name: str) -> str:
    """只接受相对、无 .. 的 spec 文件名（防路径穿越）。"""
    cleaned = (name or "").replace("\\", "/").strip()
    if not cleaned or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise ValueError(f"非法 spec 文件名: {name!r}")
    if not _SPEC_ENTRY.fullmatch(cleaned):
        raise ValueError(f"spec 文件名含非法字符: {name!r}")
    return cleaned


def _playwright_root() -> Path | None:
    """仓库内 backend/tests/playwright（含 playwright 配置与 node_modules）优先。"""
    root = Path(__file__).resolve().parents[3]
    candidate = root / "test-platform-v2" / "backend" / "tests" / "playwright"
    return candidate if candidate.is_dir() else None


def _default_spec_runner(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: float):
    import subprocess

    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _spec_cases(report: dict) -> list[dict]:
    """把 Playwright JSON report 拍平成用例列表。"""
    cases: list[dict] = []

    def walk(suite: dict) -> None:
        for spec in suite.get("specs") or []:
            statuses = []
            for test in spec.get("tests") or []:
                for result in test.get("results") or []:
                    statuses.append(str(result.get("status") or ""))
            passed = bool(statuses) and all(s in ("passed", "skipped") for s in statuses)
            cases.append(
                {
                    "id": spec.get("id") or spec.get("title") or "spec",
                    "name": spec.get("title") or spec.get("file") or "spec",
                    "passed": passed,
                    "statuses": statuses,
                }
            )
        for child in suite.get("suites") or []:
            walk(child)

    for suite in report.get("suites") or []:
        walk(suite)
    return cases


def _node_spec_name(name: str, slug: str) -> str:
    """在保留 Playwright 识别后缀（.spec.ts / .test.ts …）的前提下加唯一后缀。"""
    for suffix in (".spec.ts", ".spec.js", ".spec.mts", ".spec.mjs", ".test.ts", ".test.js", ".test.mts", ".test.mjs"):
        if name.endswith(suffix):
            return f"{name[: -len(suffix)]}.node{slug}{suffix}"
    stem, dot, ext = name.rpartition(".")
    return f"{stem}.node{slug}.{ext}" if dot else f"{name}.node{slug}"


def run_spec_files(
    files: list[dict],
    *,
    entry: str,
    evidence_dir: str | Path,
    base_url: str = "",
    browser: str = "chromium",
    env: dict[str, str] | None = None,
    timeout_seconds: float = 1800,
    runner=None,
) -> dict:
    """把 spec 文件落到节点本地并用 Playwright CLI 执行，产出 JSON 报告 + 证据目录。

    `runner(cmd, cwd=, env=, timeout=) -> (returncode, stdout, stderr)` 可注入，便于单测。
    """
    import json
    import os
    import shutil
    import subprocess

    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / "report.json"
    results_dir = directory / "test-results"

    pw_root = _playwright_root()
    spec_base = (pw_root / "generated" / f"node-{directory.name}") if pw_root else (directory / "spec")
    spec_base.mkdir(parents=True, exist_ok=True)

    try:
        rel_files = [(name, _safe_rel_path(name)) for name in (f.get("name") for f in files)]
    except ValueError as exc:
        return {"total": 0, "passed": 0, "failed": 0, "all_pass": False, "cases": [], "error": str(exc)}
    if not rel_files:
        return {"total": 0, "passed": 0, "failed": 0, "all_pass": False, "cases": [], "error": "任务载荷不含 spec 文件"}

    written: dict[str, Path] = {}
    for original, rel in rel_files:
        content = next((str(f.get("content") or "") for f in files if f.get("name") == original), "")
        if pw_root:
            # 保留原目录深度（相对导入 ../support 仍可解析），文件名加后缀避免覆盖仓库现网 spec
            target_dir = pw_root / Path(rel).parent
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / _node_spec_name(Path(rel).name, _slug(directory.name))
        else:
            target = spec_base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written[original] = target

    entry_rel = _safe_rel_path(entry) if entry else rel_files[0][1]
    if pw_root:
        entry_target = written.get(entry) or next(iter(written.values()))
        cwd = pw_root
        spec_arg = entry_target.relative_to(pw_root).as_posix()
        config_args = ["--config", str((pw_root / "playwright.config.ts").resolve())]
    else:
        cwd = spec_base
        spec_arg = entry_rel
        config_args = []

    child_env = {
        k: v for k, v in os.environ.items() if not k.upper().startswith(("SECRET", "TOKEN", "PASSWORD"))
    }
    child_env.update({str(k): str(v) for k, v in (env or {}).items()})
    child_env.update(
        {
            "BASE_URL": base_url,
            "CAMELTV_BASE_URL": base_url,
            "BROWSER": browser,
            "PLAYWRIGHT_JSON_OUTPUT_NAME": str(report_path),
        }
    )
    npx = shutil.which("npx") or "npx"
    cmd = [
        npx, "playwright", "test", spec_arg, *config_args,
        "--project", browser,
        "--reporter", "json",
        "--output", str(results_dir),
    ]
    run = runner or _default_spec_runner
    try:
        code, stdout, stderr = run(cmd, cwd=cwd, env=child_env, timeout=float(timeout_seconds))
    except subprocess.TimeoutExpired:
        return {"total": 0, "passed": 0, "failed": 0, "all_pass": False, "cases": [], "error": f"执行超时（{timeout_seconds}s）"}
    except FileNotFoundError as exc:
        return {"total": 0, "passed": 0, "failed": 0, "all_pass": False, "cases": [], "error": f"Playwright 不可用: {exc}"}

    if not report_path.exists():
        tail = (stderr or stdout or "")[-500:]
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "all_pass": False,
            "cases": [],
            "error": f"未生成 Playwright JSON 报告（exit={code}）: {tail}".strip(),
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"total": 0, "passed": 0, "failed": 0, "all_pass": False, "cases": [], "error": f"报告解析失败: {exc}"}

    cases = _spec_cases(report)
    passed = sum(1 for c in cases if c["passed"])
    failed = len(cases) - passed
    return {
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "all_pass": len(cases) > 0 and failed == 0,
        "cases": cases,
        "exit_code": code,
        "error": "" if cases else "报告中没有用例",
    }

