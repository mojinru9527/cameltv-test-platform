"""M2 / TA-013：Playwright Driver 单测（fake playwright，无真实浏览器）。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DRIVER_PATH = ROOT / "scripts" / "node" / "cameltv_node" / "drivers" / "playwright_driver.py"


def load_driver():
    spec = importlib.util.spec_from_file_location("pw_driver_under_test", DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeConsoleMessage:
    def __init__(self, type_: str, text: str) -> None:
        self.type = type_
        self.text = text


class FakeAccessibility:
    def __init__(self, snapshot):
        self.snapshot_value = snapshot

    def snapshot(self):
        return self.snapshot_value


class FakeTracing:
    def __init__(self) -> None:
        self.started = False
        self.stopped_path: str | None = None

    def start(self, **kwargs) -> None:
        self.started = True

    def stop(self, path=None) -> None:
        self.stopped_path = path
        Path(path).write_bytes(b"trace-bytes")


class FakePage:
    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}
        self.calls: list[tuple] = []
        self.accessibility = FakeAccessibility({"role": "main", "name": "root"})
        self.fail_goto = False
        self.content_value = "<html><body>ok</body></html>"

    def on(self, event, handler) -> None:
        self.handlers[event] = handler

    def emit(self, event, payload) -> None:
        self.handlers[event](payload)  # type: ignore[operator]

    def goto(self, url, **kwargs):
        if self.fail_goto:
            raise RuntimeError("nav failed")
        self.calls.append(("goto", url))

    def fill(self, selector, value, **kwargs):
        self.calls.append(("fill", selector, value))

    def click(self, selector, **kwargs):
        self.calls.append(("click", selector))

    def wait_for_selector(self, selector, **kwargs):
        self.calls.append(("wait_for", selector))

    def inner_text(self, selector, **kwargs):
        self.calls.append(("text", selector))
        return "hello"

    def content(self):
        return self.content_value

    def screenshot(self, path=None, full_page=False):
        self.calls.append(("screenshot", full_page))
        Path(path).write_bytes(b"png-bytes")


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.tracing = FakeTracing()
        self.page = page
        self.closed = False
        self.kwargs: dict = {}

    def new_page(self):
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.context = FakeContext(page)
        self.closed = False
        self.launch_kwargs: dict = {}

    def new_context(self, **kwargs):
        self.context.kwargs = kwargs
        return self.context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser

    def launch(self, **kwargs):
        self.browser.launch_kwargs = kwargs
        return self.browser


class FakePlaywright:
    def __init__(self, browser: FakeBrowser) -> None:
        self.chromium = FakeChromium(browser)


class FakeCM:
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright
        self.exited = False

    def __enter__(self):
        return self.playwright

    def __exit__(self, *args):
        self.exited = True


@pytest.fixture()
def driver_module():
    return load_driver()


def make_driver(driver_module, tmp_path):
    page = FakePage()
    browser = FakeBrowser(page)
    playwright = FakePlaywright(browser)
    cm = FakeCM(playwright)
    drv = driver_module.PlaywrightDriver(
        evidence_dir=tmp_path, playwright_factory=lambda: cm
    )
    drv.start()
    return drv, page, browser, cm


def test_login_sequence(driver_module, tmp_path):
    drv, page, _browser, _cm = make_driver(driver_module, tmp_path)
    drv.login(
        "https://admin.test/login",
        "admin",
        "pwd",
        username_selector="#user",
        password_selector="#pass",
        submit_selector="button.login",
        success_selector="#dashboard",
    )
    assert page.calls[:5] == [
        ("goto", "https://admin.test/login"),
        ("fill", "#user", "admin"),
        ("fill", "#pass", "pwd"),
        ("click", "button.login"),
        ("wait_for", "#dashboard"),
    ]
    drv.close()


def test_capture_evidence_files_and_manifest(driver_module, tmp_path):
    drv, page, _browser, _cm = make_driver(driver_module, tmp_path)
    page.emit("console", FakeConsoleMessage("error", "boom"))
    page.emit("pageerror", RuntimeError("js error"))
    files = drv.capture_evidence()
    names = {item["name"] for item in files}
    assert names == {"dom.html", "a11y.json", "console.json", "screenshot.png", "trace.zip"}
    assert all((tmp_path / name).exists() for name in names)
    assert all(item["sha256"] and item["size_bytes"] > 0 for item in files)
    console = (tmp_path / "console.json").read_text(encoding="utf-8")
    assert "boom" in console and "js error" in console
    assert (tmp_path / "a11y.json").read_text(encoding="utf-8").count("root") == 1
    drv.close()


def test_step_error_wrapped(driver_module, tmp_path):
    drv, page, _browser, _cm = make_driver(driver_module, tmp_path)
    page.fail_goto = True
    with pytest.raises(driver_module.PlaywrightStepError) as exc:
        drv.goto("https://x.test")
    assert exc.value.step == "goto"
    assert "nav failed" in str(exc.value)
    drv.close()


def test_close_releases_resources(driver_module, tmp_path):
    drv, _page, browser, cm = make_driver(driver_module, tmp_path)
    drv.close()
    assert browser.closed is True
    assert browser.context.closed is True
    assert cm.exited is True


def test_trace_and_screenshot_calls(driver_module, tmp_path):
    drv, page, browser, _cm = make_driver(driver_module, tmp_path)
    drv.capture_evidence()
    assert browser.context.tracing.started is True
    assert browser.context.tracing.stopped_path == str(tmp_path / "trace.zip")
    assert ("screenshot", True) in page.calls
    drv.close()
