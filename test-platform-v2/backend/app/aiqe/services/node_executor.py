"""M10-347：AIQE NodeRun 进程内执行器（http / playwright / appium）。

- http：API 级节点（batch-347 已交付）；**AUD-001 起统一走
  ``app.aiqe.security.SafeHttpExecutor``**，目标由服务端 Target Policy 决定，
  节点输入里的 allow_private/allowed_hosts 等覆盖项被忽略并记录；
- playwright：UI 节点（batch-347b），支持点击可用性探测与浮层注入（TC-004）；
- appium：Android 设备节点（batch-347b），通过 Appium REST 会话读取 UI 层级；
- 由 `job_consumer` 在 `AIQE_INPROCESS_EXECUTOR_ENABLED=true` 时调用；
- 结果通过 `dag_scheduler.complete_node` 回写（attempt 时间线由 batch-340 持久化）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.aiqe.models.run import NodeRun
from app.aiqe.security import (
    POLICY_OVERRIDE_KEYS,
    SafeHttpExecutor,
    SafeRequest,
    SafeTargetValidator,
    TargetDenied,
    TargetPolicy,
    TargetPolicyResolver,
)
from app.aiqe.services.query_registry import (
    DbReadonlyExecutor,
    QueryDenied,
    QueryNotRegistered,
    default_connection_resolver,
)

logger = logging.getLogger(__name__)

#: AUD-002：Workflow 不得通过节点输入决定 SQL / 连接 / 表范围。
DB_OVERRIDE_KEYS = frozenset(
    {
        "sql",
        "statement",
        "query",
        "connection_url",
        "connection_ref",
        "database_url",
        "allowed_tables",
        "schema",
    }
)

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
    #: AUD-007：结构化 Observation（断言引擎的唯一输入，不参与 Driver 判定）。
    observation: dict[str, Any] | None = None


def _driver_key(node: NodeRun) -> str:
    return str(node.driver_key or "http").strip().lower()


def _resolve_policy(node: NodeRun | Any, db: Any) -> TargetPolicy | None:
    """从 Run 的 project/environment 解析服务端策略；不接受节点输入覆盖。"""
    if db is None or node is None:
        return None
    try:
        run = getattr(node, "run", None)
    except Exception:  # detached instance / 关系未加载
        return None
    if run is None:
        return None
    try:
        return TargetPolicyResolver(db).resolve(
            project_id=int(run.project_id),
            environment_id=getattr(run, "environment_id", None),
        )
    except Exception:
        logger.exception("target policy resolve failed")
        return None


def execute_node(
    node: NodeRun,
    *,
    db: Any = None,
    policy: TargetPolicy | None = None,
) -> NodeExecution:
    driver = _driver_key(node)
    spec_input = dict(node.input_ref or {})
    if driver in {"http", "httpx", "api"}:
        return _execute_http(spec_input, node=node, db=db, policy=policy)
    if driver in {"playwright", "web", "ui"}:
        if db is None and policy is None:
            # 兼容单测：无 DB 上下文时按旧签名调用（生产路径始终带 db）。
            return _execute_playwright(spec_input)
        return _execute_playwright(spec_input, node=node, db=db, policy=policy)
    if driver in {"appium", "android", "mobile"}:
        return _execute_appium(spec_input)
    if driver in {"db", "db_readonly", "database"}:
        return _execute_db(spec_input, node=node, db=db)
    return NodeExecution(
        status="BLOCKED",
        error_class="UNSUPPORTED_DRIVER",
        detail={"driver": driver, "reason": "执行器不支持该 driver"},
    )


def _emit_security_event(
    db: Any,
    node: NodeRun | Any,
    *,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """安全事件必须可追踪（Run/Node/Actor/policy_version），但绝不能因写事件改变执行结果。"""
    if db is None or node is None:
        return
    try:
        from app.aiqe.services.event_service import append_event

        run = getattr(node, "run", None)
        run_id = getattr(run, "id", None)
        if not run_id:
            return
        body = {"schema_version": "1.0", **payload}
        append_event(
            db,
            run_id=str(run_id),
            event_type=event_type,
            payload=body,
            producer="system",
            node_run_id=getattr(node, "id", None),
        )
    except Exception:  # 审计失败不回滚执行事实
        logger.exception("append security event failed")


def _execute_http(
    spec_input: dict[str, Any],
    *,
    node: NodeRun | Any = None,
    db: Any = None,
    policy: TargetPolicy | None = None,
) -> NodeExecution:
    url = str(spec_input.get("url") or "").strip()
    if not url:
        return NodeExecution(
            status="FAILED", error_class="INPUT_INVALID", detail={"reason": "缺少 url"}
        )
    method = str(spec_input.get("method") or "GET").upper()
    headers = {str(k): str(v) for k, v in (spec_input.get("headers") or {}).items()}
    timeout_ms = int(spec_input.get("timeout_ms") or 15000)
    # AUD-001：Workflow 不能通过节点输入扩大访问范围（忽略并留痕）。
    overrides = {
        key: spec_input.pop(key) for key in list(spec_input) if key in POLICY_OVERRIDE_KEYS
    }

    effective_policy = policy if policy is not None else _resolve_policy(node, db)
    if effective_policy is None:
        return NodeExecution(
            status="BLOCKED",
            error_class="POLICY_UNAVAILABLE",
            detail={
                "reason": "缺少服务端 Target Policy，默认拒绝出网",
                "url": url,
                "ignored_overrides": overrides,
            },
        )

    request = SafeRequest(
        method=method,
        url=url,
        headers=headers,
        params=spec_input.get("params"),
        json_body=spec_input.get("json"),
        timeout_ms=max(1, timeout_ms),
    )
    result = SafeHttpExecutor().request(request, effective_policy)

    detail = {
        "status_code": result.status_code,
        "duration_ms": result.duration_ms,
        "request": result.request,
        "response": result.response,
        "policy_version": result.policy_version,
        "resolution": result.resolution,
        "redirect_chain": list(result.redirect_chain),
        "ignored_overrides": overrides,
    }

    if overrides:
        _emit_security_event(
            db,
            node,
            event_type="security.policy_override_ignored",
            payload={"node_key": getattr(node, "node_key", ""), "ignored": sorted(overrides)},
        )

    if result.blocked:
        detail["denial"] = {
            "code": result.error_code,
            "message": result.error,
        }
        _emit_security_event(
            db,
            node,
            event_type="security.target_policy_denied",
            payload={
                "node_key": getattr(node, "node_key", ""),
                "url": url,
                "code": result.error_code,
                "message": result.error,
                "policy_version": result.policy_version,
                "resolution": result.resolution,
            },
        )
        return NodeExecution(
            status="BLOCKED",
            error_class=result.error_code or "POLICY_DENIED",
            detail=detail,
        )

    expected = spec_input.get("expected_status")
    if expected is not None:
        try:
            ok = result.status_code == int(expected)
        except (TypeError, ValueError):
            ok = False
    else:
        ok = bool(result.ok)

    from app.aiqe.assertions.observation import maybe_json

    body_text = str((result.response or {}).get("body") or "")
    observation = {
        "status_code": result.status_code,
        "headers": (result.response or {}).get("headers") or {},
        "text": body_text,
        "body": maybe_json(body_text),
        "duration_ms": result.duration_ms,
        "error": (
            result.error_code
            if result.error_code in {"TIMEOUT", "DRIVER_ERROR", "CLIENT_INIT_FAILED"}
            else None
        ),
    }
    detail["observation"] = observation
    if ok:
        return NodeExecution(status="PASSED", detail=detail, observation=observation)
    error_class = "STATUS_MISMATCH" if expected is not None else "HTTP_FAILED"
    if result.error_code == "TIMEOUT":
        error_class = "TIMEOUT"
    elif result.error_code == "CLIENT_INIT_FAILED":
        error_class = "DRIVER_ERROR"
    return NodeExecution(
        status="FAILED", error_class=error_class, detail=detail, observation=observation
    )


def _execute_db(
    spec_input: dict[str, Any],
    *,
    node: NodeRun | Any = None,
    db: Any = None,
) -> NodeExecution:
    """AUD-002：只允许 ``query_key + typed_params``，SQL/连接由服务端登记。"""
    raw_overrides = {
        key: spec_input[key] for key in list(spec_input) if key in DB_OVERRIDE_KEYS
    }
    query_key = str(spec_input.get("query_key") or "").strip()
    if not query_key:
        return NodeExecution(
            status="BLOCKED",
            error_class="INPUT_INVALID",
            detail={
                "reason": "db 节点必须提供 query_key（禁止内联 SQL）",
                "rejected_overrides": raw_overrides,
            },
        )
    if raw_overrides:
        # v1.5 §01 AUD-002：「Workflow 提交空值、通配符、任意表名和自定义 connection URL：
        # schema 拒绝」→ 这里显式 BLOCKED 而不是静默忽略，便于发现越权尝试。
        return NodeExecution(
            status="BLOCKED",
            error_class="WORKFLOW_DB_OVERRIDE",
            detail={
                "reason": "Workflow 不能决定 SQL/连接/表范围",
                "rejected_overrides": sorted(raw_overrides),
                "query_key": query_key,
            },
        )
    if db is None or node is None:
        return NodeExecution(
            status="BLOCKED",
            error_class="POLICY_UNAVAILABLE",
            detail={"reason": "缺少 DB 会话，无法解析登记查询", "query_key": query_key},
        )
    try:
        run = getattr(node, "run", None)
    except Exception:  # detached instance
        run = None
    if run is None:
        return NodeExecution(
            status="BLOCKED",
            error_class="POLICY_UNAVAILABLE",
            detail={"reason": "节点未关联 Run", "query_key": query_key},
        )

    params = spec_input.get("params") or {}
    if not isinstance(params, dict):
        return NodeExecution(
            status="BLOCKED",
            error_class="INPUT_INVALID",
            detail={"reason": "params 必须是对象", "query_key": query_key},
        )
    version = spec_input.get("query_version")
    try:
        result = DbReadonlyExecutor(connection_resolver=default_connection_resolver).execute(
            db,
            project_id=int(run.project_id),
            query_key=query_key,
            params=params,
            version=int(version) if version is not None else None,
            environment_id=getattr(run, "environment_id", None),
        )
    except QueryNotRegistered:
        return NodeExecution(
            status="BLOCKED",
            error_class="QUERY_NOT_REGISTERED",
            detail={"query_key": query_key},
        )
    except QueryDenied as exc:
        return NodeExecution(
            status="BLOCKED",
            error_class=exc.code,
            detail={"query_key": query_key, "reason": exc.message},
        )
    except Exception as exc:  # 执行异常必须回写为失败，不得悬挂节点
        return NodeExecution(
            status="FAILED",
            error_class="DRIVER_ERROR",
            detail={"query_key": query_key, "reason": f"{type(exc).__name__}: {exc}"},
        )

    return NodeExecution(
        status="PASSED",
        detail={
            "query_key": result.query_key,
            "summary": result.summary(),
            "columns": result.columns,
            "rows": result.rows,
        },
    )


def _mouse_click(page, target, detail: dict[str, Any]) -> bool:
    """真实鼠标点击（move→down→up），并记录点击落点是否被浮层拦截。"""
    box = target.bounding_box()
    if not box:
        detail["click_error"] = "目标无可见位置"
        return False
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    detail["click_point"] = [round(cx, 1), round(cy, 1)]
    detail["top_at_point"] = page.evaluate(
        "({x, y}) => { const el = document.elementFromPoint(x, y);"
        " return el ? {tag: el.tagName, id: el.id || '', cls: String(el.className || '').slice(0, 80)} : null; }",
        {"x": cx, "y": cy},
    )
    url_before = page.url
    page.evaluate(
        "() => { window.__aiqeClicks = [];"
        " document.addEventListener('click', (e) => {"
        " const t = e.target;"
        " window.__aiqeClicks.push({tag: t.tagName, id: t.id || '',"
        " overlay: t.id === 'aiqe-injected-overlay'}); }, true); }"
    )
    page.mouse.move(cx, cy, steps=12)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(400)
    try:
        clicks = page.evaluate("() => window.__aiqeClicks || []")
    except Exception:  # 点击触发导航时上下文销毁，按成功处理
        return True
    detail["clicks"] = clicks[-3:]
    if clicks:
        if clicks[-1].get("overlay"):
            detail["click_error"] = "浮层拦截了点击"
            return False
        return True
    if page.url != url_before:
        return True
    detail["click_error"] = "未捕获到点击事件"
    return False


def _execute_playwright(
    spec_input: dict[str, Any],
    *,
    node: NodeRun | Any = None,
    db: Any = None,
    policy: TargetPolicy | None = None,
) -> NodeExecution:
    url = str(spec_input.get("url") or "").strip()
    if not url:
        return NodeExecution(
            status="FAILED", error_class="INPUT_INVALID", detail={"reason": "缺少 url"}
        )
    effective_policy = policy if policy is not None else _resolve_policy(node, db)
    if effective_policy is not None:
        try:
            SafeTargetValidator().validate(url, effective_policy)
        except TargetDenied as exc:
            _emit_security_event(
                db,
                node,
                event_type="security.target_policy_denied",
                payload={
                    "node_key": getattr(node, "node_key", ""),
                    "url": url,
                    "code": exc.code,
                    "message": exc.message,
                    "policy_version": effective_policy.version,
                    "driver": "playwright",
                },
            )
            return NodeExecution(
                status="BLOCKED",
                error_class=exc.code,
                detail={"url": url, "denial": exc.payload(), "policy_version": effective_policy.version},
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

                click_mode = str(spec_input.get("click_mode") or "trial").lower()
                detail["click_mode"] = click_mode
                clickable: bool | None = None
                if click_text or click_selector:
                    target = (
                        page.get_by_text(click_text, exact=False).first
                        if click_text
                        else page.locator(click_selector).first
                    )
                    if click_mode == "mouse":
                        clickable = _mouse_click(page, target, detail)
                    else:
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
