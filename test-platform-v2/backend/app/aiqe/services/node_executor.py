"""AIQE 节点 Driver 调度（M10-347 / v1.4 FIX-003/004/007）。

Runner 只负责“执行动作并采集事实”，不决定业务 PASS：
- http：httpx 执行，返回 status/headers/body/json；
- playwright：真实动作 + probe 分离 + 截图/Trace/DOM/A11y/console/network；
- db：只读查询（engine 注入；无 engine 时 BLOCKED，绝不伪造结果）；
- appium：Android 真机动作。
业务断言由后端 Assertion Runtime 统一执行（FIX-002）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.aiqe.drivers.httpx_driver import HttpDriver, HttpRequestSpec
from app.aiqe.models.run import NodeRun
from app.aiqe.schemas.contracts import EvidenceFile


@dataclass
class NodeExecution:
    status: str
    error_class: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidenceFile] = field(default_factory=list)


def _driver_key(node: NodeRun) -> str:
    return str(node.driver_key or "http").strip().lower()


def execute_node(
    node: NodeRun,
    *,
    db_engine: Any = None,
    input_override: dict[str, Any] | None = None,
) -> NodeExecution:
    driver = _driver_key(node)
    spec_input = dict(input_override if input_override is not None else (node.input_ref or {}))
    if driver in {"http", "httpx", "api"}:
        return _execute_http(spec_input)
    if driver in {"playwright", "web", "ui"}:
        return _execute_playwright(spec_input)
    if driver in {"db", "db_readonly", "database"}:
        return _execute_db(spec_input, db_engine=db_engine)
    if driver in {"appium", "android", "mobile"}:
        return _execute_appium(spec_input)
    return NodeExecution(
        status="BLOCKED",
        error_class="UNSUPPORTED_DRIVER",
        detail={"driver": driver, "reason": "执行器不支持该 driver"},
        data={"unsupported_driver": driver},
    )


def _execute_http(spec_input: dict[str, Any]) -> NodeExecution:
    url = str(spec_input.get("url") or "").strip()
    if not url:
        return NodeExecution(
            status="FAILED",
            error_class="INPUT_INVALID",
            detail={"reason": "缺少 url"},
            data={"error": "missing url"},
        )
    allowed = spec_input.get("allowed_hosts")
    allowed_hosts = (
        [str(item) for item in allowed]
        if isinstance(allowed, list)
        else None
    )
    raw_content = spec_input.get("content")
    content = raw_content.encode("utf-8") if isinstance(raw_content, str) else raw_content
    spec = HttpRequestSpec(
        method=str(spec_input.get("method") or "GET").upper(),
        url=url,
        headers={str(k): str(v) for k, v in (spec_input.get("headers") or {}).items()},
        params=spec_input.get("params"),
        json_body=spec_input.get("json"),
        content=content,
        timeout_ms=max(1, int(spec_input.get("timeout_ms") or 15000)),
        correlation_id=str(spec_input.get("correlation_id") or ""),
        idempotency_key=str(spec_input.get("idempotency_key") or ""),
        allowed_hosts=allowed_hosts,
        allow_private=(
            bool(spec_input.get("allow_private"))
            if "allow_private" in spec_input
            else None
        ),
    )
    try:
        result = HttpDriver(allowed_hosts=allowed_hosts).execute(spec)
    except Exception as exc:
        return NodeExecution(
            status="FAILED",
            error_class="DRIVER_ERROR",
            detail={"reason": f"{type(exc).__name__}: {exc}"},
            data={"error": f"{type(exc).__name__}: {exc}"},
        )

    detail = {
        "status_code": result.status_code,
        "duration_ms": result.duration_ms,
        "request": result.request,
        "response": result.response,
        "error": result.error,
    }
    data = dict(getattr(result, "data", None) or {})
    data.setdefault("status_code", result.status_code)
    data.setdefault("headers", (result.response or {}).get("headers") or {})
    if result.status_code is None:
        return NodeExecution(
            status="FAILED" if result.error else "ERROR",
            error_class=result.error_class or ("NETWORK_ERROR" if result.error else "EMPTY_RESPONSE"),
            detail=detail,
            data=data,
        )
    # 请求本身完成即成功；业务 PASS 由 Assertion Runtime 判定（HTTP 500 也可能是预期）。
    return NodeExecution(status="PASSED", detail=detail, data=data)


def _execute_playwright(spec_input: dict[str, Any]) -> NodeExecution:
    from app.aiqe.drivers.playwright_driver import PlaywrightDriver

    has_actions = isinstance(spec_input.get("actions"), list) and bool(spec_input.get("actions"))
    has_legacy = bool(spec_input.get("click_text") or spec_input.get("click_selector"))
    if not str(spec_input.get("url") or "").strip() and not has_actions and not has_legacy:
        return NodeExecution(
            status="FAILED",
            error_class="INPUT_INVALID",
            detail={"reason": "缺少 url/actions"},
            data={"error": "missing url/actions"},
        )
    driver = PlaywrightDriver(
        headless=bool(spec_input.get("headless", True)),
        timeout_ms=max(1, int(spec_input.get("timeout_ms") or 30000)),
        allowed_hosts=list(spec_input.get("allowed_hosts") or []),
    )
    try:
        result = driver.execute(spec_input)
    finally:
        driver.close()
    detail = result.data
    if result.status == "BLOCKED":
        return NodeExecution(
            status="BLOCKED",
            error_class=result.error_class or "BROWSER_UNAVAILABLE",
            detail=detail,
            data=detail,
            evidence=result.evidence,
        )
    if result.status == "ERROR":
        return NodeExecution(
            status="ERROR",
            error_class=result.error_class or "AUTOMATION_ERROR",
            detail=detail,
            data=detail,
            evidence=result.evidence,
        )
    if result.status == "FAILED":
        return NodeExecution(
            status="FAILED",
            error_class=result.error_class or "PLAYWRIGHT_FAILED",
            detail=detail,
            data=detail,
            evidence=result.evidence,
        )
    return NodeExecution(status="PASSED", detail=detail, data=detail, evidence=result.evidence)


def _execute_db(spec_input: dict[str, Any], *, db_engine: Any = None) -> NodeExecution:
    if db_engine is None:
        return NodeExecution(
            status="BLOCKED",
            error_class="DB_UNAVAILABLE",
            detail={"reason": "未配置只读数据库连接（AIQE_DB_READONLY_URL）"},
            data={"error": "db engine unavailable"},
        )
    from app.aiqe.drivers.db_readonly_driver import (
        DbReadonlyDriver,
        QueryRegistry,
        RowLimitExceeded,
        UnsafeSqlError,
    )

    registry_raw = spec_input.get("query_registry")
    registry = (
        QueryRegistry(registry_raw)
        if isinstance(registry_raw, dict)
        else QueryRegistry()
    )
    driver = DbReadonlyDriver(
        db_engine,
        max_rows=int(spec_input.get("max_rows") or 1000),
        max_field_chars=int(spec_input.get("max_field_chars") or 2000),
        allowed_tables=spec_input.get("allowed_tables") or [],
        registry=registry,
        statement_timeout_ms=int(spec_input.get("timeout_ms") or 5000),
    )
    try:
        result = driver.query(
            sql=None if spec_input.get("query_key") else str(spec_input.get("sql") or ""),
            params=spec_input.get("params") or {},
            query_key=str(spec_input.get("query_key") or ""),
            max_rows=spec_input.get("max_rows"),
        )
    except UnsafeSqlError as exc:
        return NodeExecution(
            status="BLOCKED",
            error_class="UNSAFE_SQL",
            detail={"reason": str(exc), "audit": [event.__dict__ for event in driver.last_audit]},
            data={"error": str(exc)},
        )
    except RowLimitExceeded as exc:
        return NodeExecution(
            status="FAILED",
            error_class="ROW_LIMIT_EXCEEDED",
            detail={"reason": str(exc)},
            data={"error": str(exc)},
        )
    except Exception as exc:
        return NodeExecution(
            status="ERROR",
            error_class="DB_ERROR",
            detail={"reason": f"{type(exc).__name__}: {exc}"},
            data={"error": f"{type(exc).__name__}: {exc}"},
        )
    db_data = {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "query_key": result.query_key,
        "elapsed_ms": result.elapsed_ms,
        "truncated_fields": result.truncated_fields,
    }
    return NodeExecution(
        status="PASSED",
        detail={"db": db_data, "audit": [event.__dict__ for event in driver.last_audit]},
        data={"db": db_data},
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
        with httpx.Client(base_url=appium_url, timeout=60, trust_env=False) as client:
            try:
                created = _appium_post(
                    client, "/session", {"capabilities": {"alwaysMatch": caps}}
                )
            except Exception as exc:
                return NodeExecution(
                    status="BLOCKED",
                    error_class="APPIUM_UNAVAILABLE",
                    detail={**detail, "reason": f"{type(exc).__name__}: {exc}"},
                    data={"error": f"{type(exc).__name__}: {exc}"},
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
                    data={"error": "no session"},
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
                            or (found.get("value") or {}).get(
                                "element-6066-11e4-a52e-4f735466cecf"
                            )
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
                data = {
                    "source_len": len(xml),
                    "clicked": clicked,
                    "expect_text_found": bool(expect_text and expect_text in xml),
                    "locators": (
                        {"text": {"visible": True, "count": 1, "text": xml[:4000]}}
                        if expect_text and expect_text in xml
                        else {}
                    ),
                }
                if click_text and not clicked:
                    return NodeExecution(
                        status="FAILED",
                        error_class="DEVICE_CLICK_FAILED",
                        detail=detail,
                        data=data,
                    )
                if expect_text and not detail.get("expect_text_found"):
                    return NodeExecution(
                        status="FAILED",
                        error_class="TEXT_MISMATCH",
                        detail=detail,
                        data=data,
                    )
                return NodeExecution(status="PASSED", detail=detail, data=data)
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
            data={"error": f"{type(exc).__name__}: {exc}"},
        )
