"""AITDE V3.3 BrowserRuntimeDriver (V33-004).

Executes the browser subtree of a Command IR against real Playwright, honoring the
§4 locator priority (data-testid → role+name → label → semantic text → CSS, with
visual-coordinate clicks never a default regression strategy), and captures
trace / screenshot / network / DOM evidence for a replay-proof run.

Design for testability: the driver talks to a *page adapter* exposing the §4
unified methods (``open/goto/click/fill/select/upload/wait_for/content/screenshot/
network_events/trace_path/close``). The default adapter drives Playwright; tests
inject a fake adapter so command dispatch, locator resolution and evidence capture
can be verified without a live Chromium.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from app.modules.aitde.browser.locator import SemanticLocatorResolver

logger = logging.getLogger("aitde.browser")

# Local evidence storage root (mirrors the v1 ui-runner convention); callers may
# override per-session.
DEFAULT_STORAGE_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent / "storage" / "browser-runs"
)

_ROLE_FULL_RE = re.compile(r"^role=([^\[]+)\[name=\"(.*)\"\]$")
_ROLE_BARE_RE = re.compile(r"^role=([^\[]+)$")


class BrowserRuntimeError(Exception):
    """Deterministic browser runtime failure — maps to AUTOMATION_FAIL, never
    BUSINESS_FAIL (a runtime/environment problem can't mask a business bug)."""


# ── page adapter (real Playwright) ───────────────────────────────────────────
class PlaywrightPageAdapter:
    """Drives a real Chromium page, wiring network + trace capture."""

    def __init__(
        self,
        *,
        headless: bool = True,
        base_url: str = "",
        browser_type: str = "chromium",
        timeout_ms: int = 30000,
        storage_root: Path = DEFAULT_STORAGE_ROOT,
    ) -> None:
        self.headless = headless
        self.base_url = base_url.rstrip("/")
        self.browser_type = browser_type
        self.timeout_ms = timeout_ms
        self.storage_root = storage_root
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._network: list[dict[str, Any]] = []

    def open(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        launcher = {
            "chromium": self._pw.chromium,
            "firefox": self._pw.firefox,
            "webkit": self._pw.webkit,
        }.get(self.browser_type, self._pw.chromium)
        self._browser = launcher.launch(headless=self.headless)
        self._context = self._browser.new_context(base_url=self.base_url)
        self._context.set_default_timeout(self.timeout_ms)
        try:
            self._context.tracing.start(screenshots=True, snapshots=True)
        except Exception:  # tracing is best-effort evidence, never fatal
            logger.warning("Playwright tracing unavailable", exc_info=True)
        self._page = self._context.new_page()
        self._page.on("request", self._on_request)
        self._page.on("response", self._on_response)

    def _on_request(self, request: Any) -> None:
        try:
            rtype = request.resource_type
            if callable(rtype):
                rtype = rtype()
        except Exception:
            rtype = ""
        self._network.append(
            {
                "kind": "request",
                "method": request.method,
                "url": request.url,
                "resource_type": rtype,
            }
        )

    def _on_response(self, response: Any) -> None:
        self._network.append(
            {"kind": "response", "url": response.url, "status": response.status}
        )

    def _join(self, route: str) -> str:
        if not self.base_url:
            return route
        return f"{self.base_url}/{route.lstrip('/')}"

    def goto(self, route: str) -> str:
        url = route if route.startswith(("http://", "https://")) else self._join(route)
        self._page.goto(url)
        return url

    def click(self, locator: Any) -> None:
        self._locate(locator).click()

    def fill(self, locator: Any, value: str) -> None:
        self._locate(locator).fill(value)

    def select(self, locator: Any, value: str) -> None:
        self._locate(locator).select_option(value)

    def upload(self, locator: Any, file: str) -> None:
        self._locate(locator).set_input_files(file)

    def wait_for(self, locator: Any) -> None:
        self._locate(locator).wait_for(state="visible")

    def _locate(self, resolved: dict[str, Any]) -> Any:
        """Map a resolved locator ``{kind, selector/...}`` to a Playwright Locator."""
        kind = resolved.get("kind")
        page = self._page
        if kind == "data-testid":
            return page.get_by_test_id(resolved["selector"])
        if kind == "role":
            role = resolved.get("role")
            name = resolved.get("name")
            if role and name:
                return page.get_by_role(role, name=name)
            if role:
                return page.get_by_role(role)
            return page.locator(resolved["selector"])
        if kind == "label":
            return page.get_by_label(resolved["selector"])
        if kind == "text":
            return page.get_by_text(resolved["selector"], exact=False)
        return page.locator(resolved["selector"])

    def content(self) -> str:
        return self._page.content()

    def screenshot(self) -> bytes:
        return self._page.screenshot(full_page=True)

    def network_events(self) -> list[dict[str, Any]]:
        return list(self._network)

    def trace_path(self) -> Path:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        path = self.storage_root / f"trace-{int(time.time() * 1000)}.zip"
        try:
            self._context.tracing.stop(path=str(path))
        except Exception:
            logger.warning("Playwright trace stop failed", exc_info=True)
        return path

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()


# ── rule-based locator resolution (pure, unit-testable) ──────────────────────
def _resolve_role(selector: str) -> dict[str, Any]:
    m = _ROLE_FULL_RE.search(selector)
    if m:
        return {"role": m.group(1), "name": m.group(2)}
    m = _ROLE_BARE_RE.search(selector)
    if m:
        return {"role": m.group(1)}
    return {"selector": selector}


def resolve_locator(locator: dict[str, Any]) -> dict[str, Any]:
    """Resolve a semantic locator to ``{"kind": ..., "selector": ..., ...}``.

    ``kind`` is one of data-testid | role | label | text | css, following the
    plan's priority order (visual-coordinate clicks are never the default).
    """
    resolved = SemanticLocatorResolver().resolve(locator)
    kind = resolved.get("strategy", "css")
    selector = resolved.get("selector", "")
    if kind == "role":
        details = _resolve_role(selector)
        details["kind"] = "role"
        details["selector"] = selector
        return details
    if kind in ("data-testid", "label", "text", "css"):
        return {"kind": kind, "selector": selector}
    return {"kind": "css", "selector": selector}


# ── Command IR executor (browser driver only) ────────────────────────────────
# Actions the runtime driver executes. Other drivers (data/api/assertion) are
# orchestrated by the hybrid coordinator, not here.
_BROWSER_ACTIONS = {
    "open_session",
    "goto",
    "click",
    "fill",
    "select",
    "upload",
    "wait_for",
    "capture_dom",
    "capture_screenshot",
    "capture_network",
    "close_session",
}


class BrowserRuntimeDriver:
    """Executes the browser-subtree of a Command IR, capturing replay evidence.

    ``execute`` yields a structured result: per-command status, a durable DOM/
    screenshot/network/trace evidence ledger, and an overall outcome. A runtime
    error is surfaced as ``status=runtime_error`` (AUTOMATION_FAIL) — never
    BUSINESS_FAIL.
    """

    def __init__(self, *, adapter: Any | None = None) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> Any:
        return self._adapter

    def execute(self, ir: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(ir, dict):
            return {
                "status": "runtime_error",
                "reason": "ir_not_object",
                "evidence": [],
            }
        commands = ir.get("commands", [])
        if not isinstance(commands, list):
            return {
                "status": "runtime_error",
                "reason": "commands_not_list",
                "evidence": [],
            }

        result: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        status = "success"
        opened = False
        try:
            for cmd in commands:
                if cmd.get("driver") != "browser":
                    # Not this driver's responsibility; record as skipped (a hybrid
                    # coordinator drives the other drivers).
                    result.append(
                        {
                            "id": cmd.get("id"),
                            "driver": cmd.get("driver"),
                            "status": "skipped",
                        }
                    )
                    continue
                if cmd.get("action") not in _BROWSER_ACTIONS:
                    raise BrowserRuntimeError(
                        f"unknown browser action: {cmd.get('action')}"
                    )
                r = self._run_command(cmd, evidence)
                result.append(r)
                if r["action"] == "open_session":
                    opened = True
                if r["action"] == "close_session":
                    opened = False
                if r["status"] == "runtime_error":
                    status = "runtime_error"
        except BrowserRuntimeError as exc:
            status = "runtime_error"
            result.append(
                {
                    "id": None,
                    "driver": "browser",
                    "action": None,
                    "status": "runtime_error",
                    "reason": str(exc),
                }
            )
        finally:
            if opened and self._adapter is not None:
                try:
                    self._adapter.close()
                except Exception:
                    logger.warning(
                        "adapter close during error cleanup failed", exc_info=True
                    )
        return {"status": status, "commands": result, "evidence": evidence}

    def _run_command(
        self, cmd: dict[str, Any], evidence: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if self._adapter is None:
            raise BrowserRuntimeError("no page adapter configured")
        action = cmd["action"]
        action_input = cmd.get("input") or {}
        try:
            if action == "open_session":
                self._adapter.open()
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            if action == "goto":
                url = self._adapter.goto(action_input.get("route", ""))
                return {
                    "id": cmd.get("id"),
                    "action": action,
                    "status": "ok",
                    "url": url,
                }
            if action == "click":
                self._adapter.click(resolve_locator(action_input.get("locator", {})))
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            if action == "fill":
                self._adapter.fill(
                    resolve_locator(action_input.get("locator", {})),
                    action_input.get("value", ""),
                )
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            if action == "select":
                self._adapter.select(
                    resolve_locator(action_input.get("locator", {})),
                    action_input.get("value", ""),
                )
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            if action == "upload":
                self._adapter.upload(
                    resolve_locator(action_input.get("locator", {})),
                    action_input.get("file", ""),
                )
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            if action == "wait_for":
                self._adapter.wait_for(resolve_locator(action_input.get("locator", {})))
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            if action == "capture_dom":
                dom = self._adapter.content()
                evidence.append({"type": "dom", "html": dom})
                return {
                    "id": cmd.get("id"),
                    "action": action,
                    "status": "ok",
                    "dom_chars": len(dom),
                }
            if action == "capture_screenshot":
                data = self._adapter.screenshot()
                evidence.append({"type": "screenshot", "bytes": len(data)})
                return {
                    "id": cmd.get("id"),
                    "action": action,
                    "status": "ok",
                    "screenshot_bytes": len(data),
                }
            if action == "capture_network":
                events = self._adapter.network_events()
                evidence.append({"type": "network", "events": events})
                return {
                    "id": cmd.get("id"),
                    "action": action,
                    "status": "ok",
                    "network_count": len(events),
                }
            if action == "close_session":
                self._adapter.close()
                return {"id": cmd.get("id"), "action": action, "status": "ok"}
            raise BrowserRuntimeError(f"unhandled browser action: {action}")
        except BrowserRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001 — map any runtime failure to AUTOMATION_FAIL
            raise BrowserRuntimeError(f"{action} failed: {exc}") from exc
