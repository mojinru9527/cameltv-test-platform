"""v1.4 FIX-004：Playwright 真实动作 / probe 分离 / 证据测试（fake browser）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.aiqe.drivers.playwright_driver import (
    PlaywrightAction,
    PlaywrightActionError,
    PlaywrightDriver,
)
from app.aiqe.schemas.contracts import DriverResult
from app.aiqe.services import assertion_service


class FakeLocator:
    def __init__(self, page: "FakePage", selector: str) -> None:
        self.page = page
        self.selector = selector

    @property
    def first(self) -> "FakeLocator":
        return self

    def click(self, **kwargs):
        if self.page.intercepted:
            raise RuntimeError("element intercepts pointer events")
        self.page.clicks.append(self.selector)

    def fill(self, value, **kwargs):
        self.page.fills.append((self.selector, value))

    def select_option(self, value, **kwargs):
        self.page.selected.append((self.selector, value))

    def check(self, **kwargs):
        self.page.checked.append(self.selector)

    def uncheck(self, **kwargs):
        self.page.checked.append(("uncheck", self.selector))

    def set_input_files(self, value, **kwargs):
        self.page.files.append((self.selector, value))

    def is_visible(self):
        return self.page.visible

    def count(self):
        return 1

    def bounding_box(self):
        return {"x": 10, "y": 20, "width": 40, "height": 20}

    def wait_for(self, **kwargs):
        if not self.page.visible:
            raise RuntimeError("not visible")

    def inner_text(self, **kwargs):
        return self.page.text


class FakeAccessibility:
    def snapshot(self):
        return {"role": "main"}


class FakeTracing:
    def __init__(self):
        self.started = False

    def start(self, **kwargs):
        self.started = True

    def stop(self, path=None):
        Path(path).write_bytes(b"trace")


class FakeKeyboard:
    def __init__(self, page):
        self.page = page

    def press(self, key):
        self.page.keys.append(key)


class FakeMouse:
    def __init__(self, page):
        self.page = page

    def wheel(self, x, y):
        self.page.scrolls.append((x, y))


class FakePage:
    def __init__(self):
        self.url = ""
        self.text = "hello"
        self.visible = True
        self.intercepted = False
        self.clicks: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.selected: list[tuple[str, str]] = []
        self.checked: list[str] = []
        self.files: list[tuple[str, str]] = []
        self.keys: list[str] = []
        self.scrolls: list[tuple[int, int]] = []
        self.handlers: dict[str, list] = {}
        self.accessibility = FakeAccessibility()
        self.keyboard = FakeKeyboard(self)
        self.mouse = FakeMouse(self)

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def emit(self, event, payload=None):
        for handler in self.handlers.get(event, []):
            handler(payload)

    def goto(self, url, **kwargs):
        self.url = url

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_test_id(self, testid):
        return FakeLocator(self, f"[data-testid={testid}]")

    def get_by_text(self, text, exact=False):
        return FakeLocator(self, f"text={text}")

    def get_by_role(self, role, name=None):
        return FakeLocator(self, f"role={role}")

    def wait_for_load_state(self, *args, **kwargs):
        return None

    def wait_for_timeout(self, *args, **kwargs):
        return None

    def wait_for_url(self, url, **kwargs):
        return None

    def title(self):
        return "Demo"

    def content(self):
        return "<html><body>hello</body></html>"

    def screenshot(self, path=None, full_page=False):
        Path(path).write_bytes(b"png")

    def evaluate(self, script, arg=None):
        return {"tag": "BUTTON", "id": "save"}


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.tracing = FakeTracing()

    def new_page(self):
        return self.page

    def close(self):
        return None


class FakeBrowser:
    def __init__(self, context):
        self.context = context

    def new_context(self, **kwargs):
        return self.context

    def close(self):
        return None


class FakeChromium:
    def __init__(self, browser):
        self.browser = browser

    def launch(self, **kwargs):
        return self.browser


class FakePlaywright:
    def __init__(self, browser):
        self.chromium = FakeChromium(browser)


class FakeCM:
    def __init__(self, playwright):
        self.playwright = playwright

    def __enter__(self):
        return self.playwright

    def __exit__(self, *args):
        return None


@pytest.fixture()
def driver(tmp_path):
    page = FakePage()
    context = FakeContext(page)
    browser = FakeBrowser(context)
    drv = PlaywrightDriver(
        evidence_dir=tmp_path,
        playwright_factory=lambda: FakeCM(FakePlaywright(browser)),
    )
    drv.start()
    yield drv
    drv.close()


def test_real_click_is_default(driver):
    record = driver.perform(PlaywrightAction(type="click", selector="#save"))
    assert record.dispatched is True
    assert driver._page.clicks == ["#save"]
    result = driver.result()
    assert result.data["business_action_dispatched"] is True
    assert result.data["probe_only"] is False


def test_probe_never_dispatches(driver):
    record = driver.perform(
        PlaywrightAction(type="probe_actionability", selector="#save")
    )
    assert record.dispatched is False
    assert driver._page.clicks == []
    result = driver.result()
    assert result.data["probe_only"] is True
    assert result.data["business_action_dispatched"] is False


def test_probe_only_cannot_satisfy_business_assertion(driver, db_session):
    from app.aiqe.models.run import NodeRun, StepAttempt, TestRun

    driver.perform(PlaywrightAction(type="probe_actionability", selector="#save"))
    driver_result = driver.result()
    run = TestRun(project_id=1, run_key="RUN-PROBE", source_type="manual", status="RUNNING")
    db_session.add(run)
    db_session.flush()
    node = NodeRun(run_id=run.id, node_key="n", driver_key="playwright", status="RUNNING")
    db_session.add(node)
    db_session.flush()
    attempt = StepAttempt(
        node_run_id=node.id, step_key="n", attempt_no=1, status="RUNNING"
    )
    db_session.add(attempt)
    db_session.flush()
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=DriverResult(
            driver_key="playwright",
            status="SUCCEEDED",
            data=driver_result.data,
        ),
        declared=[
            {
                "assertion_key": "published",
                "oracle_layer": "REQ",
                "oracle_ref": "AC-1",
                "type": "locator_visible",
                "selector": "#published",
                "expected": True,
            }
        ],
    )
    assert status != "PASS"
    assert outcomes[0].status == "NOT_EVALUATED"


def test_click_interception_classified(driver):
    driver._page.intercepted = True
    with pytest.raises(PlaywrightActionError) as exc:
        driver.perform(PlaywrightAction(type="click", selector="#save"))
    assert exc.value.error_class == "CLICK_INTERCEPTED"


def test_evidence_files(driver):
    driver.perform(PlaywrightAction(type="click", selector="#save"))
    files = driver.capture_evidence()
    names = {item.name for item in files}
    assert {"dom.html", "a11y.json", "console.json", "network.json", "screenshot.png", "trace.zip"} <= names
    assert all(item.sha256 for item in files)
