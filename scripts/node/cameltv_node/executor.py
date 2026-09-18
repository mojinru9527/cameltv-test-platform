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

SUPPORTED_KINDS = ("api", "web")
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
) -> list[dict]:
    """返回逐条断言结果；未识别的断言类型记为失败（不静默放过）。"""
    results: list[dict] = []
    for index, assertion in enumerate(assertions or []):
        kind = str(assertion.get("type") or "").strip()
        expected = assertion.get("expected")
        passed = False
        actual: Any = None
        if kind == "status":
            actual = status_code
            passed = status_code == expected
        elif kind == "json_path":
            actual = _dig(payload, str(assertion.get("path") or ""))
            passed = actual == expected
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

    return httpx.Client(timeout=timeout, follow_redirects=True)


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
        status_code=status_code, text=text, payload=payload, assertions=case.get("assertions") or []
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
    """顺序执行 Web 用例；每步失败即停在该用例，并保留已产出的截图。"""
    directory = Path(evidence_dir)
    directory.mkdir(parents=True, exist_ok=True)
    factory = page_factory or _default_page_factory
    case_results: list[dict] = []
    with factory() as page:
        for case in cases:
            case_results.append(
                _run_one_web_case(page, case, directory=directory, base_url=base_url)
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
            visible = bool(page.is_visible(str(target)))
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
