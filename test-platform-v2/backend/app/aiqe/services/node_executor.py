"""M10-347：AIQE NodeRun 进程内执行器（http / playwright / appium）。

- http：API 级节点（batch-347 已交付）；
- playwright：UI 节点（batch-347b），支持点击可用性探测与浮层注入（TC-004）；
- appium：Android 设备节点（batch-347b），通过 Appium REST 会话读取 UI 层级；
- 由 `job_consumer` 在 `AIQE_INPROCESS_EXECUTOR_ENABLED=true` 时调用；
- 结果通过 `dag_scheduler.complete_node` 回写（attempt 时间线由 batch-340 持久化）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.aiqe.drivers.httpx_driver import HttpDriver, HttpRequestSpec
from app.aiqe.models.run import NodeRun

OVERLAY_JS = """
(() => {
  const el = document.createElement('div');
  el.id = 'aiqe-injected-overlay';
  el.style.position = 'fixed';
  el.style.inset = '0';
  el.style.zIndex = '2147483647';
  el.style.background = 'rgba(0,0,0,0.01)';
  el.setAttribute('data-aiqe-fixture', 'overlay');
  document.body.appendChild(el);
  return el.id;
})()
"""


@dataclass
class NodeExecution:
    status: str
    error_class: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


def _driver_key(node: NodeRun) -> str:
    return str(node.driver_key or "http").strip().lower()


def execute_node(node: NodeRun) -> NodeExecution:
    driver = _driver_key(node)
    spec_input = dict(node.input_ref or {})
    if driver in {"http", "httpx", "api"}:
        return _execute_http(spec_input)
    if driver in {"playwright", "web", "ui"}:
        return _execute_playwright(spec_input)
    if driver in {"appium", "android", "mobile"}:
        return _execute_appium(spec_input)
    return NodeExecution(
        status="BLOCKED",
        error_class="UNSUPPORTED_DRIVER",
        detail={"driver": driver, "reason": "执行器不支持该 driver"},
    )


def _execute_http(spec_input: dict[str, Any]) -> NodeExecution:
    url = str(spec_input.get("url") or "").strip()
    if not url:
        return NodeExecution(
            status="FAILED", error_class="INPUT_INVALID", detail={"reason": "缺少 url"}
        )
    method = str(spec_input.get("method") or "GET").upper()
    headers = {str(k): str(v) for k, v in (spec_input.get("headers") or {}).items()}
    timeout_ms = int(spec_input.get("timeout_ms") or 15000)
    spec = HttpRequestSpec(
        method=method,
        url=url,
        headers=headers,
        params=spec_input.get("params"),
        json_body=spec_input.get("json"),
        timeout_ms=max(1, timeout_ms),
    )
    try:
        result = HttpDriver().execute(spec)
    except Exception as exc:  # 执行异常必须回写为失败，不得悬挂节点
        return NodeExecution(
            status="FAILED",
            error_class="DRIVER_ERROR",
            detail={"reason": f"{type(exc).__name__}: {exc}"},
        )

    expected = spec_input.get("expected_status")
    if expected is not None:
        try:
            ok = result.status_code == int(expected)
        except (TypeError, ValueError):
            ok = False
    else:
        ok = bool(result.ok)

    detail = {
        "status_code": result.status_code,
        "duration_ms": result.duration_ms,
        "request": result.request,
        "response": result.response,
    }
    if ok:
        return NodeExecution(status="PASSED", detail=detail)
    error_class = "STATUS_MISMATCH" if expected is not None else "HTTP_FAILED"
    return NodeExecution(status="FAILED", error_class=error_class, detail=detail)


def _execute_playwright(spec_input: dict[str, Any]) -> NodeExecution:
    url = str(spec_input.get("url") or "").strip()
    if not url:
        return NodeExecution(
            status="FAILED", error_class="INPUT_INVALID", detail={"reason": "缺少 url"}
        )
    click_text = str(spec_input.get("click_text") or "").strip()
    click_selector = str(spec_input.get("click_selector") or "").strip()
    expect_text = str(spec_input.get("expect_text") or "").strip()
    inject_overlay = bool(spec_input.get("inject_overlay"))
    timeout_ms = int(spec_input.get("timeout_ms") or 30000)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return NodeExecution(
            status="BLOCKED",
            error_class="BROWSER_UNAVAILABLE",
            detail={"reason": f"playwright 不可用: {type(exc).__name__}: {exc}"},
        )

    detail: dict[str, Any] = {"url": url, "inject_overlay": inject_overlay}
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
            except Exception as exc:
                return NodeExecution(
                    status="BLOCKED",
                    error_class="BROWSER_UNAVAILABLE",
                    detail={"reason": f"Chromium 启动失败: {type(exc).__name__}: {exc}"},
                )
            try:
                page = browser.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                detail["status_code"] = response.status if response is not None else None
                detail["title"] = page.title()
                if inject_overlay:
                    detail["overlay_id"] = page.evaluate(OVERLAY_JS)

                clickable: bool | None = None
                if click_text or click_selector:
                    target = (
                        page.get_by_text(click_text, exact=False).first
                        if click_text
                        else page.locator(click_selector).first
                    )
                    try:
                        target.click(trial=True, timeout=4000)
                        clickable = True
                    except Exception as exc:
                        clickable = False
                        detail["click_error"] = str(exc).splitlines()[0][:300]
                detail["clickable"] = clickable

                body_text = page.locator("body").inner_text()[:4000]
                detail["text_len"] = len(body_text)
                if expect_text:
                    detail["expect_text_found"] = expect_text in body_text

                if clickable is False:
                    return NodeExecution(
                        status="FAILED",
                        error_class=(
                            "OVERLAY_INTERCEPTED" if inject_overlay else "CLICK_FAILED"
                        ),
                        detail=detail,
                    )
                if expect_text and not detail.get("expect_text_found"):
                    return NodeExecution(
                        status="FAILED", error_class="TEXT_MISMATCH", detail=detail
                    )
                return NodeExecution(status="PASSED", detail=detail)
            finally:
                browser.close()
    except Exception as exc:
        return NodeExecution(
            status="FAILED",
            error_class="DRIVER_ERROR",
            detail={"reason": f"{type(exc).__name__}: {exc}"},
        )


def _appium_post(client, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def _execute_appium(spec_input: dict[str, Any]) -> NodeExecution:
    import httpx

    appium_url = str(spec_input.get("appium_url") or "http://127.0.0.1:4723").rstrip("/")
    expect_text = str(spec_input.get("expect_text") or "").strip()
    click_text = str(spec_input.get("click_text") or "").strip()
    caps: dict[str, Any] = {
        "platformName": "Android",
        "appium:automationName": spec_input.get("automation_name") or "UiAutomator2",
        "appium:deviceName": spec_input.get("device_name") or "android",
        "appium:noReset": bool(spec_input.get("no_reset", True)),
        "appium:newCommandTimeout": 180,
    }
    if spec_input.get("app_package"):
        caps["appium:appPackage"] = spec_input["app_package"]
    if spec_input.get("app_activity"):
        caps["appium:appActivity"] = spec_input["app_activity"]

    detail: dict[str, Any] = {"appium_url": appium_url, "caps": caps}
    try:
        with httpx.Client(base_url=appium_url, timeout=60) as client:
            try:
                created = _appium_post(
                    client, "/session", {"capabilities": {"alwaysMatch": caps}}
                )
            except Exception as exc:
                return NodeExecution(
                    status="BLOCKED",
                    error_class="APPIUM_UNAVAILABLE",
                    detail={**detail, "reason": f"{type(exc).__name__}: {exc}"},
                )
            session_id = (created.get("value") or {}).get("sessionId") or created.get(
                "sessionId"
            )
            detail["session_id"] = session_id
            if not session_id:
                return NodeExecution(
                    status="FAILED",
                    error_class="APPIUM_SESSION_FAILED",
                    detail=detail,
                )
            try:
                source = client.get(f"/session/{session_id}/source")
                source.raise_for_status()
                xml = str(source.json().get("value") or "")
                detail["source_len"] = len(xml)
                clicked = False
                if click_text:
                    selector = (
                        f'//*[@text="{click_text}" or contains(@text, "{click_text}")]'
                    )
                    try:
                        found = _appium_post(
                            client,
                            f"/session/{session_id}/element",
                            {"using": "xpath", "value": selector},
                        )
                        element_id = (
                            (found.get("value") or {}).get("ELEMENT")
                            or (found.get("value") or {}).get("element-6066-11e4-a52e-4f735466cecf")
                        )
                        if element_id:
                            client.post(
                                f"/session/{session_id}/element/{element_id}/click"
                            ).raise_for_status()
                            clicked = True
                    except Exception as exc:
                        detail["click_error"] = str(exc).splitlines()[0][:300]
                detail["clicked"] = clicked
                if expect_text:
                    detail["expect_text_found"] = expect_text in xml
                if click_text and not clicked:
                    return NodeExecution(
                        status="FAILED", error_class="DEVICE_CLICK_FAILED", detail=detail
                    )
                if expect_text and not detail.get("expect_text_found"):
                    return NodeExecution(
                        status="FAILED", error_class="TEXT_MISMATCH", detail=detail
                    )
                return NodeExecution(status="PASSED", detail=detail)
            finally:
                try:
                    client.delete(f"/session/{session_id}")
                except Exception:
                    pass
    except Exception as exc:
        return NodeExecution(
            status="FAILED",
            error_class="DRIVER_ERROR",
            detail={**detail, "reason": f"{type(exc).__name__}: {exc}"},
        )
