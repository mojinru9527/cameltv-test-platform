"""M2 / TA-013：Playwright Driver（Runner 侧，13 号 §19 TA-013）。

- 同一 Run 内：后台登录 → 配置实体 → 前台查询（由调用方串联 login/click/fill）；
- 证据：DOM、A11y snapshot、console/pageerror、screenshot、trace；
- 每个动作失败抛 `PlaywrightStepError`，保留 step 名称；
- playwright 延迟导入，便于无浏览器环境做单测。

用法：
    with PlaywrightDriver(evidence_dir=out) as drv:
        drv.login(url, user, pwd, username_selector=..., password_selector=..., submit_selector=...)
        drv.click(...)
        files = drv.capture_evidence()
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


class PlaywrightStepError(RuntimeError):
    def __init__(self, step: str, message: str) -> None:
        self.step = step
        super().__init__(f"{step}: {message}")


class PlaywrightDriver:
    def __init__(
        self,
        *,
        headless: bool = True,
        evidence_dir: str | Path | None = None,
        storage_state: str | None = None,
        timeout_ms: int = 30000,
        playwright_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.headless = headless
        self.evidence_dir = Path(evidence_dir) if evidence_dir else None
        self.storage_state = storage_state
        self.timeout_ms = timeout_ms
        self._factory = playwright_factory
        self._cm: Any = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._console: list[dict[str, str]] = []
        self._errors: list[str] = []

    # ── lifecycle ──────────────────────────────────────────────────────
    def __enter__(self) -> "PlaywrightDriver":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        if self._factory is None:
            from playwright.sync_api import sync_playwright

            factory = sync_playwright
        else:
            factory = self._factory
        self._cm = factory()
        self._playwright = self._cm.__enter__()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            storage_state=self.storage_state,
            viewport={"width": 1440, "height": 900},
        )
        self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self._page = self._context.new_page()
        self._page.on("console", self._on_console)
        self._page.on("pageerror", self._on_pageerror)

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            if self._browser is not None:
                self._browser.close()
            if self._cm is not None:
                self._cm.__exit__(None, None, None)
            self._cm = self._browser = self._context = self._page = None

    # ── events ─────────────────────────────────────────────────────────
    def _on_console(self, message: Any) -> None:
        self._console.append(
            {"type": str(getattr(message, "type", "")), "text": str(getattr(message, "text", ""))}
        )

    def _on_pageerror(self, error: Any) -> None:
        self._errors.append(str(error))

    # ── actions ────────────────────────────────────────────────────────
    def _step(self, name: str, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except PlaywrightStepError:
            raise
        except Exception as exc:  # noqa: BLE001 - 包装所有 playwright 异常
            raise PlaywrightStepError(name, str(exc)) from exc

    def goto(self, url: str) -> None:
        self._step(
            "goto",
            lambda: self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms),
        )

    def fill(self, selector: str, value: str) -> None:
        self._step("fill", lambda: self._page.fill(selector, value, timeout=self.timeout_ms))

    def click(self, selector: str) -> None:
        self._step("click", lambda: self._page.click(selector, timeout=self.timeout_ms))

    def wait_for(self, selector: str, timeout_ms: int | None = None) -> None:
        self._step(
            "wait_for",
            lambda: self._page.wait_for_selector(
                selector, timeout=timeout_ms or self.timeout_ms
            ),
        )

    def text(self, selector: str) -> str:
        return self._step(
            "text", lambda: self._page.inner_text(selector, timeout=self.timeout_ms)
        )

    def login(
        self,
        url: str,
        username: str,
        password: str,
        *,
        username_selector: str = "#username",
        password_selector: str = "#password",
        submit_selector: str = "button[type=submit]",
        success_selector: str | None = None,
    ) -> None:
        self.goto(url)
        self.fill(username_selector, username)
        self.fill(password_selector, password)
        self.click(submit_selector)
        if success_selector:
            self.wait_for(success_selector)

    # ── evidence ───────────────────────────────────────────────────────
    def _write(self, directory: Path, name: str, kind: str, data: bytes) -> dict[str, Any]:
        path = directory / name
        path.write_bytes(data)
        return {
            "name": name,
            "type": kind,
            "path": str(path),
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def capture_evidence(self, evidence_dir: str | Path | None = None) -> list[dict[str, Any]]:
        directory = Path(evidence_dir or self.evidence_dir or "playwright-evidence")
        directory.mkdir(parents=True, exist_ok=True)
        files: list[dict[str, Any]] = []

        dom = self._step("dom", lambda: self._page.content())
        files.append(self._write(directory, "dom.html", "dom", dom.encode("utf-8")))

        a11y = self._step("a11y", lambda: self._page.accessibility.snapshot())
        files.append(
            self._write(
                directory,
                "a11y.json",
                "a11y",
                json.dumps(a11y, ensure_ascii=False, default=str, indent=2).encode("utf-8"),
            )
        )

        console = {"messages": self._console, "page_errors": self._errors}
        files.append(
            self._write(
                directory,
                "console.json",
                "log",
                json.dumps(console, ensure_ascii=False, indent=2).encode("utf-8"),
            )
        )

        screenshot_path = directory / "screenshot.png"
        self._step("screenshot", lambda: self._page.screenshot(path=str(screenshot_path), full_page=True))
        files.append(
            {
                "name": "screenshot.png",
                "type": "screenshot",
                "path": str(screenshot_path),
                "size_bytes": screenshot_path.stat().st_size,
                "sha256": hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
            }
        )

        trace_path = directory / "trace.zip"
        self._step("trace", lambda: self._context.tracing.stop(path=str(trace_path)))
        files.append(
            {
                "name": "trace.zip",
                "type": "trace",
                "path": str(trace_path),
                "size_bytes": trace_path.stat().st_size,
                "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            }
        )
        return files
