"""M2 / TA-013 + v1.4 FIX-004：Playwright Driver（Runner/进程内执行器共用）。

关键修复：
- `probe_actionability` 只判断可操作性，绝不替代真实 click，也不产生业务 PASS；
- `click / fill / select / check / upload / navigate / keyboard / scroll` 是真实动作；
- 默认真实 click；probe 必须显式声明；
- 每步记录 locator 摘要、操作前 URL、是否实际 dispatch、操作后页面变化；
- 采集 screenshot（前后）、trace、DOM、A11y、console、pageerror、network；
- 浏览器不可用返回 BLOCKED；浏览器 crash 返回 ERROR（业务断言 NOT_EVALUATED）。

本模块不初始化数据库：证据以 `EvidenceFile` 返回，由执行服务统一脱敏/入库。
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.aiqe.schemas.contracts import DriverResult, EvidenceFile
from app.aiqe.services.evidence_redactor import redact, redact_json_text

SUPPORTED_ACTIONS: frozenset[str] = frozenset(
    {
        "probe_actionability",
        "click",
        "fill",
        "select",
        "check",
        "uncheck",
        "upload",
        "navigate",
        "goto",
        "keyboard",
        "scroll",
        "wait_visible",
        "wait_url",
        "assert_visible",
        "assert_text",
        "assert_url",
        "assert_count",
    }
)
OBSERVE_ONLY = frozenset(
    {"probe_actionability", "wait_visible", "wait_url", "assert_visible", "assert_text", "assert_url", "assert_count"}
)


class PlaywrightUnavailable(RuntimeError):
    pass


class PlaywrightActionError(RuntimeError):
    def __init__(self, action: str, error_class: str, message: str, detail: dict | None = None):
        self.action = action
        self.error_class = error_class
        self.detail = detail or {}
        super().__init__(f"{action}: {message}")


@dataclass
class PlaywrightAction:
    type: str
    selector: str = ""
    role: str = ""
    name: str = ""
    testid: str = ""
    text: str = ""
    value: Any = None
    url: str = ""
    key: str = ""
    expected: Any = None
    timeout_ms: int = 15000
    probe: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PlaywrightAction:
        return cls(
            type=str(raw.get("type") or raw.get("action") or "").strip().lower(),
            selector=str(raw.get("selector") or ""),
            role=str(raw.get("role") or ""),
            name=str(raw.get("name") or ""),
            testid=str(raw.get("testid") or raw.get("test_id") or ""),
            text=str(raw.get("text") or ""),
            value=raw.get("value"),
            url=str(raw.get("url") or ""),
            key=str(raw.get("key") or ""),
            expected=raw.get("expected"),
            timeout_ms=int(raw.get("timeout_ms") or 15000),
            probe=bool(raw.get("probe") or False),
        )


@dataclass
class ActionRecord:
    action: str
    selector: str = ""
    url_before: str = ""
    url_after: str = ""
    dispatched: bool = False
    page_changed: bool = False
    visible: bool | None = None
    count: int = 0
    text: str = ""
    click_point: list[float] | None = None
    top_at_point: dict[str, Any] | None = None
    error: str = ""
    duration_ms: int = 0
    screenshot_before: str = ""
    screenshot_after: str = ""


class PlaywrightDriver:
    def __init__(
        self,
        *,
        headless: bool = True,
        evidence_dir: str | Path | None = None,
        timeout_ms: int = 30000,
        playwright_factory: Callable[[], Any] | None = None,
        allowed_hosts: list[str] | None = None,
    ) -> None:
        self.headless = headless
        self.evidence_dir = Path(evidence_dir) if evidence_dir else None
        self.timeout_ms = max(1, int(timeout_ms))
        self._factory = playwright_factory
        self.allowed_hosts = list(allowed_hosts or [])
        self._cm: Any = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._console: list[dict[str, str]] = []
        self._page_errors: list[str] = []
        self._network: list[dict[str, Any]] = []
        self._started = False
        self._trace_started = False
        self._records: list[ActionRecord] = []

    # ── lifecycle ──────────────────────────────────────────────────────
    def start(self) -> None:
        if self._started:
            return
        try:
            if self._factory is None:
                from playwright.sync_api import sync_playwright

                factory = sync_playwright
            else:
                factory = self._factory
            self._cm = factory()
            self._playwright = self._cm.__enter__()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=False,
            )
            try:
                self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
                self._trace_started = True
            except Exception:
                self._trace_started = False
            self._page = self._context.new_page()
            self._page.on("console", self._on_console)
            self._page.on("pageerror", self._on_pageerror)
            self._page.on("request", self._on_request)
            self._page.on("response", self._on_response)
            self._started = True
        except Exception as exc:
            self.close()
            raise PlaywrightUnavailable(f"{type(exc).__name__}: {exc}") from exc

    def close(self) -> None:
        try:
            if self._context is not None:
                try:
                    self._context.close()
                except Exception:
                    pass
            if self._browser is not None:
                try:
                    self._browser.close()
                except Exception:
                    pass
            if self._cm is not None:
                try:
                    self._cm.__exit__(None, None, None)
                except Exception:
                    pass
        finally:
            self._cm = self._playwright = self._browser = self._context = self._page = None
            self._started = False

    def __enter__(self) -> PlaywrightDriver:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ── events ─────────────────────────────────────────────────────────
    def _on_console(self, message: Any) -> None:
        self._console.append(
            {
                "type": str(getattr(message, "type", "")),
                "text": redact(str(getattr(message, "text", ""))),
            }
        )

    def _on_pageerror(self, error: Any) -> None:
        self._page_errors.append(str(error))

    def _on_request(self, request: Any) -> None:
        if len(self._network) >= 200:
            return
        try:
            self._network.append(
                {
                    "kind": "request",
                    "method": str(getattr(request, "method", "")),
                    "url": redact(str(getattr(request, "url", ""))),
                    "resource_type": str(getattr(request, "resource_type", "")),
                }
            )
        except Exception:
            return

    def _on_response(self, response: Any) -> None:
        if len(self._network) >= 200:
            return
        try:
            self._network.append(
                {
                    "kind": "response",
                    "status": int(getattr(response, "status", 0) or 0),
                    "url": redact(str(getattr(response, "url", ""))),
                }
            )
        except Exception:
            return

    # ── locator ────────────────────────────────────────────────────────
    def _locator(self, action: PlaywrightAction):
        page = self._page
        if page is None:
            raise PlaywrightActionError(action.type, "AUTOMATION_ERROR", "page 未初始化")
        if action.testid and hasattr(page, "get_by_test_id"):
            return page.get_by_test_id(action.testid).first
        if action.text and hasattr(page, "get_by_text"):
            return page.get_by_text(action.text, exact=False).first
        if action.role and hasattr(page, "get_by_role"):
            kwargs = {"name": action.name} if action.name else {}
            return page.get_by_role(action.role, **kwargs).first
        selector = action.selector or (f"[data-testid='{action.testid}']" if action.testid else "")
        if not selector:
            raise PlaywrightActionError(action.type, "LOCATOR_INVALID", "缺少 selector/testid/role")
        return page.locator(selector).first

    def _selector_label(self, action: PlaywrightAction) -> str:
        return (
            action.selector
            or (f"text={action.text}" if action.text else "")
            or (f"role={action.role}[name={action.name}]" if action.role else "")
            or (f"testid={action.testid}" if action.testid else "")
        )

    # ── actions ────────────────────────────────────────────────────────
    def perform(self, action: PlaywrightAction) -> ActionRecord:
        if action.type not in SUPPORTED_ACTIONS:
            raise PlaywrightActionError(
                action.type, "UNSUPPORTED_ACTION", f"未支持的 action: {action.type!r}"
            )
        if action.type == "probe_actionability" or (
            action.probe and action.type not in OBSERVE_ONLY
        ):
            return self._probe(action)
        started = time.monotonic()
        record = ActionRecord(action=action.type, selector=self._selector_label(action))
        url_before = self._url()
        record.url_before = url_before
        try:
            if action.type in {"navigate", "goto"}:
                if not action.url:
                    raise PlaywrightActionError(action.type, "URL_MISSING", "navigate 缺少 url")
                self._page.goto(
                    action.url, wait_until="domcontentloaded", timeout=action.timeout_ms
                )
                record.dispatched = True
            elif action.type == "click":
                locator = self._locator(action)
                record.count = int(getattr(locator, "count", lambda: 1)())
                record.visible = self._is_visible(locator)
                if not record.visible:
                    raise PlaywrightActionError(
                        action.type, "LOCATOR_NOT_VISIBLE", f"目标不可见: {record.selector}"
                    )
                self._record_click_point(locator, record)
                locator.click(timeout=action.timeout_ms)
                record.dispatched = True
            elif action.type == "fill":
                locator = self._locator(action)
                locator.fill(str(action.value or ""), timeout=action.timeout_ms)
                record.dispatched = True
            elif action.type in {"select", "check", "uncheck"}:
                locator = self._locator(action)
                if action.type == "select":
                    locator.select_option(str(action.value or ""), timeout=action.timeout_ms)
                elif action.type == "check":
                    locator.check(timeout=action.timeout_ms)
                else:
                    locator.uncheck(timeout=action.timeout_ms)
                record.dispatched = True
            elif action.type == "upload":
                locator = self._locator(action)
                locator.set_input_files(action.value, timeout=action.timeout_ms)
                record.dispatched = True
            elif action.type == "keyboard":
                self._page.keyboard.press(str(action.key or action.value or "Enter"))
                record.dispatched = True
            elif action.type == "scroll":
                self._page.mouse.wheel(0, int(action.value or 800))
                record.dispatched = True
            elif action.type == "wait_visible":
                locator = self._locator(action)
                locator.wait_for(state="visible", timeout=action.timeout_ms)
                record.visible = True
            elif action.type == "wait_url":
                self._page.wait_for_url(action.url or str(action.value or ""), timeout=action.timeout_ms)
            elif action.type == "assert_visible":
                locator = self._locator(action)
                record.visible = self._is_visible(locator)
                expected = True if action.expected is None else bool(action.expected)
                if record.visible != expected:
                    raise PlaywrightActionError(
                        action.type,
                        "VISIBILITY_MISMATCH",
                        f"visible={record.visible} expected={expected}",
                    )
            elif action.type == "assert_text":
                locator = self._locator(action)
                record.text = str(locator.inner_text(timeout=action.timeout_ms))
                expected_text = str(action.expected if action.expected is not None else action.value or "")
                if expected_text not in record.text:
                    raise PlaywrightActionError(
                        action.type,
                        "TEXT_MISMATCH",
                        f"expect {expected_text!r} in {record.text[:120]!r}",
                    )
            elif action.type == "assert_url":
                actual = self._url()
                expected_url = action.url or str(action.value or "")
                if expected_url not in actual:
                    raise PlaywrightActionError(
                        action.type, "URL_MISMATCH", f"expect {expected_url!r} in {actual!r}"
                    )
            elif action.type == "assert_count":
                locator = self._locator(action)
                actual_count = int(getattr(locator, "count", lambda: 0)())
                if action.expected is not None and actual_count != int(action.expected):
                    raise PlaywrightActionError(
                        action.type,
                        "COUNT_MISMATCH",
                        f"count={actual_count} expected={action.expected}",
                    )
                record.count = actual_count
            # 条件等待：只等 DOM/URL 变化，不用固定 sleep 替代业务等待。
            if record.dispatched:
                self._wait_after_action(action.timeout_ms, url_before)
        except PlaywrightActionError as exc:
            record.error = f"{exc.error_class}: {exc}"
            record.duration_ms = int((time.monotonic() - started) * 1000)
            raise
        except Exception as exc:
            record.error = f"{type(exc).__name__}: {exc}"
            record.duration_ms = int((time.monotonic() - started) * 1000)
            raise PlaywrightActionError(
                action.type, _classify_error(exc), str(exc)[:400], {"record": record.__dict__}
            ) from exc
        record.url_after = self._url()
        record.page_changed = bool(
            record.url_after != record.url_before
            or (record.text and record.text)
            or (record.dispatched and self._network_since(started))
        )
        record.duration_ms = int((time.monotonic() - started) * 1000)
        self._records.append(record)
        return record

    def _probe(self, action: PlaywrightAction) -> ActionRecord:
        started = time.monotonic()
        record = ActionRecord(
            action="probe_actionability", selector=self._selector_label(action)
        )
        locator = self._locator(action)
        record.count = int(getattr(locator, "count", lambda: 1)())
        record.visible = self._is_visible(locator)
        detail: dict[str, Any] = {}
        box = getattr(locator, "bounding_box", lambda: None)()
        if box:
            detail["box"] = box
        try:
            locator.wait_for(state="visible", timeout=action.timeout_ms)
            record.visible = True
        except Exception as exc:
            record.visible = False
            record.error = type(exc).__name__
        record.dispatched = False
        record.duration_ms = int((time.monotonic() - started) * 1000)
        record.text = json.dumps(
            {"ready": bool(record.visible), **detail}, ensure_ascii=False
        )
        self._records.append(record)
        return record

    def _record_click_point(self, locator: Any, record: ActionRecord) -> None:
        try:
            box = locator.bounding_box()
            if not box:
                return
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            record.click_point = [round(cx, 1), round(cy, 1)]
            if self._page is not None and hasattr(self._page, "evaluate"):
                record.top_at_point = self._page.evaluate(
                    "({x, y}) => { const el = document.elementFromPoint(x, y);"
                    " return el ? {tag: el.tagName, id: el.id || '',"
                    " cls: String(el.className || '').slice(0, 80)} : null; }",
                    {"x": cx, "y": cy},
                )
        except Exception:
            return

    def _wait_after_action(self, timeout_ms: int, url_before: str) -> None:
        try:
            if self._page is not None and hasattr(self._page, "wait_for_load_state"):
                self._page.wait_for_load_state("domcontentloaded", timeout=min(3000, timeout_ms))
        except Exception:
            pass
        try:
            if self._page is not None and hasattr(self._page, "wait_for_timeout"):
                # 仅给浏览器一个事件循环 tick，让 DOM/URL mutation 落定；不是业务等待。
                self._page.wait_for_timeout(50)
        except Exception:
            pass

    def _network_since(self, started: float) -> bool:
        return bool(self._network)

    def _url(self) -> str:
        return str(getattr(self._page, "url", "") or "") if self._page is not None else ""

    def _is_visible(self, locator: Any) -> bool:
        try:
            if hasattr(locator, "is_visible"):
                return bool(locator.is_visible())
        except Exception:
            return False
        return True

    # ── evidence ───────────────────────────────────────────────────────
    def capture_evidence(self, evidence_dir: str | Path | None = None) -> list[EvidenceFile]:
        directory = Path(evidence_dir or self.evidence_dir or tempfile.mkdtemp(prefix="aiqe-pw-"))
        directory.mkdir(parents=True, exist_ok=True)
        files: list[EvidenceFile] = []
        if self._page is None:
            return files

        def add(name: str, kind: str, content: bytes, mime: str = "application/octet-stream") -> None:
            files.append(
                EvidenceFile(
                    name=name,
                    artifact_type=kind,
                    mime_type=mime,
                    content=content,
                    sha256=hashlib.sha256(content).hexdigest(),
                )
            )

        try:
            html = self._page.content()
            add("dom.html", "dom", str(html).encode("utf-8"), "text/html")
        except Exception:
            pass
        try:
            a11y = self._page.accessibility.snapshot()
            add(
                "a11y.json",
                "a11y",
                json.dumps(a11y, ensure_ascii=False, default=str).encode("utf-8"),
                "application/json",
            )
        except Exception:
            pass
        console_payload = {"messages": self._console, "page_errors": self._page_errors}
        add(
            "console.json",
            "log",
            redact_json_text(json.dumps(console_payload, ensure_ascii=False)).encode("utf-8"),
            "application/json",
        )
        add(
            "network.json",
            "log",
            redact_json_text(json.dumps(self._network, ensure_ascii=False)).encode("utf-8"),
            "application/json",
        )
        try:
            screenshot = directory / "screenshot.png"
            self._page.screenshot(path=str(screenshot), full_page=True)
            add("screenshot.png", "screenshot", screenshot.read_bytes(), "image/png")
        except Exception:
            pass
        if self._trace_started and self._context is not None:
            try:
                trace_path = directory / "trace.zip"
                self._context.tracing.stop(path=str(trace_path))
                add("trace.zip", "trace", trace_path.read_bytes(), "application/zip")
            except Exception:
                pass
        return files

    def execute(self, spec_input: dict[str, Any]) -> DriverResult:
        """执行一个节点的动作列表，返回标准化 DriverResult（含证据）。"""
        try:
            self.start()
        except PlaywrightUnavailable as exc:
            return DriverResult(
                driver_key="playwright",
                status="BLOCKED",
                error_class="BROWSER_UNAVAILABLE",
                error_message=str(exc),
            )
        actions_raw = spec_input.get("actions")
        actions: list[PlaywrightAction] = []
        if isinstance(actions_raw, list) and actions_raw:
            actions = [
                PlaywrightAction.from_dict(item) for item in actions_raw if isinstance(item, dict)
            ]
        else:
            legacy = self._legacy_actions(spec_input)
            actions = legacy
        url = str(spec_input.get("url") or "").strip()
        error_class = ""
        error_message = ""
        try:
            if url and not any(action.type in {"navigate", "goto"} for action in actions):
                navigate = PlaywrightAction(type="navigate", url=url, timeout_ms=self.timeout_ms)
                self.perform(navigate)
            for action in actions:
                self.perform(action)
        except PlaywrightActionError as exc:
            error_class = exc.error_class
            error_message = str(exc)[:500]
            if exc.detail:
                error_class = str(exc.detail.get("error_class") or error_class)
        except Exception as exc:
            error_class = "AUTOMATION_ERROR"
            error_message = f"{type(exc).__name__}: {exc}"[:500]
        try:
            evidence = self.capture_evidence()
            self.set_evidence_files(evidence)
        except Exception:
            self.set_evidence_files([])
        result = self.result(error_class=error_class, error_message=error_message)
        result.meta["evidence_capture_error"] = not bool(result.evidence)
        return result

    def _legacy_actions(self, spec_input: dict[str, Any]) -> list[PlaywrightAction]:
        actions: list[PlaywrightAction] = []
        click_text = str(spec_input.get("click_text") or "").strip()
        click_selector = str(spec_input.get("click_selector") or "").strip()
        click_mode = str(spec_input.get("click_mode") or "").strip().lower()
        if click_text or click_selector:
            actions.append(
                PlaywrightAction(
                    type="click" if click_mode != "trial" else "probe_actionability",
                    selector=click_selector,
                    text=click_text,
                    probe=click_mode in {"trial", "probe"},
                    timeout_ms=int(spec_input.get("timeout_ms") or 15000),
                )
            )
        expect_text = str(spec_input.get("expect_text") or "").strip()
        if expect_text:
            actions.append(
                PlaywrightAction(
                    type="assert_text",
                    selector="body",
                    expected=expect_text,
                    timeout_ms=int(spec_input.get("timeout_ms") or 15000),
                )
            )
        return actions

    def result(self, *, error_class: str = "", error_message: str = "") -> DriverResult:
        dispatched = [record for record in self._records if record.dispatched]
        probe_actions = [
            record for record in self._records if record.action == "probe_actionability"
        ]
        probe_only = bool(probe_actions) and not dispatched
        data: dict[str, Any] = {
            "url": self._url(),
            "title": str(getattr(self._page, "title", lambda: "")()) if self._page else "",
            "actions": [record.__dict__ for record in self._records],
            "business_action_dispatched": bool(dispatched),
            "probe_actions": len(probe_actions),
            "probe_only": probe_only,
            "console": self._console,
            "page_errors": self._page_errors,
            "network": self._network,
        }
        if dispatched:
            last = dispatched[-1]
            data["locators"] = {
                last.selector: {
                    "visible": last.visible,
                    "count": last.count,
                    "text": last.text,
                }
            }
        try:
            if self._page is not None:
                data["body_text"] = self._page.locator("body").inner_text()[:4000]
        except Exception:
            data["body_text"] = ""
        return DriverResult(
            driver_key="playwright",
            status="FAILED" if error_class else "SUCCEEDED",
            data=data,
            error_class=error_class,
            error_message=error_message,
            evidence=self.evidence_files,
        )

    @property
    def evidence_files(self) -> list[EvidenceFile]:
        return getattr(self, "_evidence_files", [])

    def set_evidence_files(self, files: list[EvidenceFile]) -> None:
        self._evidence_files = files


def _classify_error(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "ACTION_TIMEOUT"
    if "intercept" in message or "overlay" in message:
        return "CLICK_INTERCEPTED"
    if "visible" in message or "not found" in message or "locator" in message:
        return "LOCATOR_NOT_FOUND"
    if "crash" in message or "target closed" in message:
        return "AUTOMATION_ERROR"
    return "DRIVER_ERROR"
