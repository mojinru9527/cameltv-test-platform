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
from datetime import UTC, datetime
from typing import Any

from app.aiqe.models.run import NodeRun
from app.aiqe.schemas.contracts import EvidenceFile
from app.aiqe.services.query_registry import (
    DbReadonlyExecutor,
    QueryDenied,
    QueryNotRegistered,
    default_connection_resolver,
)
from app.aiqe.security import (
    POLICY_OVERRIDE_KEYS,
    ExecutionCapabilities,
    PolicyDecision,
    SafeHttpExecutor,
    SafeRequest,
    TargetPolicy,
    resolve_execution_policy,
)

#: Driver 能力分类：没有对应能力/策略授权时一律 BLOCKED，禁止降级到 legacy 执行器。
NETWORK_DRIVERS = frozenset({"http", "httpx", "api"})
BROWSER_DRIVERS = frozenset({"playwright", "web", "ui"})
DB_DRIVERS = frozenset({"db", "db_readonly", "database"})
DEVICE_DRIVERS = frozenset({"appium", "android", "mobile"})
EXTERNAL_DRIVERS = frozenset({"external_e2e", "e2e"})

_POLICY_ERROR_CODES: dict[PolicyDecision, str] = {
    PolicyDecision.DENY: "TARGET_POLICY_DENIED",
    PolicyDecision.UNAVAILABLE: "TARGET_POLICY_UNAVAILABLE",
    PolicyDecision.MISSING_BINDING: "TARGET_POLICY_MISSING_BINDING",
}


@dataclass
class NodeExecution:
    status: str
    error_class: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidenceFile] = field(default_factory=list)
    #: AUD-007：结构化 Observation（断言引擎的输入，不参与 Driver 判定）。
    observation: dict[str, Any] | None = None


def _driver_key(node: NodeRun) -> str:
    return str(node.driver_key or "http").strip().lower()


def _run_of(node: NodeRun, db: Any = None) -> Any:
    try:
        run = getattr(node, "run", None)
    except Exception:  # pragma: no cover - 非 ORM 对象
        run = None
    if run is not None:
        return run
    if db is not None:
        try:
            from app.aiqe.models.run import TestRun

            run_id = getattr(node, "run_id", None)
            return db.get(TestRun, run_id) if run_id else None
        except Exception:  # pragma: no cover - DB 不可用时按未绑定处理
            return None
    return None


def _coerce_policy_context(
    policy_context: Any,
    *,
    node: NodeRun,
    db: Any = None,
    policy: TargetPolicy | None = None,
) -> TargetPolicy | ExecutionCapabilities:
    """把显式 ``policy_context`` 规整为唯一授权对象；任何缺失都不构成放行。"""
    if isinstance(policy_context, ExecutionCapabilities):
        return policy_context
    if isinstance(policy_context, TargetPolicy):
        return policy_context
    if isinstance(policy, TargetPolicy):
        return policy
    # 防御式兜底：调用方只给了 db 时按服务端策略重新解析，仍 fail closed。
    return resolve_execution_policy(db, _run_of(node, db), node)


def policy_context_for(db: Any, node: NodeRun, run: Any = None) -> TargetPolicy:
    """服务端策略解析入口（Worker 预检/脚本/测试共用，禁止自行拼授权对象）。"""
    return resolve_execution_policy(db, run if run is not None else _run_of(node, db), node)


def _policy_denial(
    context: TargetPolicy | ExecutionCapabilities,
    *,
    required: str,
    extra: dict[str, Any] | None = None,
) -> NodeExecution | None:
    """返回 BLOCKED 结果或 ``None``（表示已授权）。"""
    if isinstance(context, ExecutionCapabilities):
        allowed = bool(
            (required == "network" and context.network)
            or (required == "db_read" and context.db_read)
            or (required == "browser" and context.browser)
            or (required == "device" and context.device)
        )
        if allowed:
            return None
        return NodeExecution(
            status="BLOCKED",
            error_class="CAPABILITY_REQUIRED",
            detail={
                "reason": f"节点未声明 {required} 能力（禁止用 None 代表绕过）",
                "required_capability": required,
                "capabilities": {
                    "network": context.network,
                    "db_read": context.db_read,
                    "browser": context.browser,
                    "device": context.device,
                },
                **(extra or {}),
            },
            data={"blocked": True},
        )
    if context.decision is PolicyDecision.ALLOW:
        expires_at = context.expires_at
        if expires_at is not None and expires_at <= datetime.now(UTC):
            # V16-001 §8：过期授权不得沿用（Worker 重试必须重新解析）。
            return NodeExecution(
                status="BLOCKED",
                error_class="TARGET_POLICY_EXPIRED",
                detail={
                    "reason": "执行授权已过期，需要重新解析策略",
                    "denial": {
                        "code": "TARGET_POLICY_EXPIRED",
                        "decision": context.decision.value,
                        "policy_version": context.version,
                        "policy_hash": context.policy_hash,
                        "expires_at": expires_at.isoformat(),
                    },
                    "policy": context.snapshot(),
                    "required_capability": required,
                    **(extra or {}),
                },
                data={"blocked": True, "policy_decision": context.decision.value},
            )
        return None
    code = _POLICY_ERROR_CODES.get(context.decision, "TARGET_POLICY_DENIED")
    return NodeExecution(
        status="BLOCKED",
        error_class=code,
        detail={
            "reason": context.deny_reason or context.reason_code or code,
            "denial": {
                "code": code,
                "decision": context.decision.value,
                "reason_code": context.reason_code,
                "policy_id": context.policy_id,
                "policy_version": context.version,
                "policy_hash": context.policy_hash,
            },
            "policy": context.snapshot(),
            "required_capability": required,
            **(extra or {}),
        },
        data={"blocked": True, "policy_decision": context.decision.value},
    )


def _emit_security_event(db: Any, node: NodeRun, event_type: str, payload: dict[str, Any]) -> None:
    if db is None:
        return
    try:
        from app.aiqe.services import dag_scheduler

        dag_scheduler.emit_event(
            db,
            run_id=node.run_id,
            event_type=event_type,
            payload=payload,
            node_run_id=node.id,
            producer="system",
        )
    except Exception:
        pass


def _safe_url_for_event(url: str) -> str:
    """安全事件只记录规范化目标，不记录 userinfo / query 值（防 Secret 泄漏）。"""
    try:
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(str(url or "").strip())
    except ValueError:
        return ""
    if not parts.scheme or not parts.hostname:
        return ""
    try:
        port = f":{parts.port}" if parts.port else ""
    except ValueError:
        port = ""
    query_keys = ""
    if parts.query:
        keys = sorted(
            {
                item.split("=", 1)[0]
                for item in parts.query.split("&")
                if item.split("=", 1)[0]
            }
        )
        query_keys = "?" + "&".join(f"{key}=***" for key in keys)
    return urlunsplit((parts.scheme, f"{parts.hostname}{port}", parts.path or "/", query_keys, ""))


#: AUD-002 / V16-004：Workflow 不得通过节点输入决定 SQL / 连接 / 表范围 / 查询注册表。
DB_OVERRIDE_KEYS = frozenset(
    {
        "sql",
        "statement",
        "query",
        "connection_url",
        "connection_ref",
        "database_url",
        "allowed_tables",
        "allowed_columns",
        "schema",
        "query_registry",
        "registry",
        "table",
        "tables",
    }
)


def _execute_db_secure(
    spec_input: dict[str, Any], *, node: NodeRun, db: Any
) -> NodeExecution:
    """AUD-002：只允许 ``query_key + typed_params``，SQL/连接由服务端登记。"""
    raw_overrides = {key: spec_input[key] for key in spec_input if key in DB_OVERRIDE_KEYS}
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
        return NodeExecution(
            status="BLOCKED",
            error_class="WORKFLOW_DB_OVERRIDE",
            detail={
                "reason": "Workflow 不能决定 SQL/连接/表范围",
                "rejected_overrides": sorted(raw_overrides),
                "query_key": query_key,
            },
        )
    try:
        run = getattr(node, "run", None)
    except Exception:
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
        result = DbReadonlyExecutor(
            connection_resolver=default_connection_resolver
        ).execute(
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
    except Exception as exc:
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
        observation={
            "source": "db_query",
            "db_rows": list(result.rows),
            "error": None,
        },
    )


def _execute_http_secure(
    spec_input: dict[str, Any],
    *,
    node: NodeRun,
    db: Any,
    policy: TargetPolicy,
) -> NodeExecution:
    # 调用方（execute_node）已保证 decision == ALLOW；这里只做纵深防御断言。
    if policy.decision is not PolicyDecision.ALLOW:
        return _policy_denial(policy, required="network")  # type: ignore[return-value]
    resolved = policy
    ignored = sorted(set(spec_input) & POLICY_OVERRIDE_KEYS)
    if ignored:
        _emit_security_event(
            db,
            node,
            "security.policy_override_ignored",
            {"keys": ignored, "node_key": node.node_key},
        )
    url = str(spec_input.get("url") or "").strip()
    if not url:
        return NodeExecution(
            status="FAILED",
            error_class="INPUT_INVALID",
            detail={"reason": "缺少 url"},
            data={"error": "missing url"},
        )
    raw_content = spec_input.get("content")
    content = raw_content.encode("utf-8") if isinstance(raw_content, str) else raw_content
    request = SafeRequest(
        method=str(spec_input.get("method") or "GET").upper(),
        url=url,
        headers={str(k): str(v) for k, v in (spec_input.get("headers") or {}).items()},
        params=spec_input.get("params"),
        json_body=spec_input.get("json"),
        content=content,
        timeout_ms=max(1, int(spec_input.get("timeout_ms") or 15000)),
    )
    result = SafeHttpExecutor().request(request, resolved)
    if result.policy_denied:
        code = result.error_code or "TARGET_DENIED"
        _emit_security_event(
            db,
            node,
            "security.target_policy_denied",
            {
                "code": code,
                "node_key": node.node_key,
                "decision": resolved.decision.value,
                "policy_id": resolved.policy_id,
                "policy_version": resolved.version,
                "policy_hash": resolved.policy_hash,
                "project_id": resolved.project_id,
                "environment_id": resolved.environment_id,
                "url": _safe_url_for_event(url),
            },
        )
        return NodeExecution(
            status="BLOCKED",
            error_class=code,
            detail={
                "denial": {
                    "code": code,
                    "message": result.error or "",
                    "decision": resolved.decision.value,
                    "policy_hash": resolved.policy_hash,
                    "policy_version": resolved.version,
                },
                "ignored_overrides": ignored,
                "policy": resolved.snapshot(),
            },
            data={"blocked": True, "status_code": result.status_code},
        )
    response = result.response or {}
    body_text = response.get("body") or ""
    parsed: Any = None
    if body_text:
        try:
            import json

            parsed = json.loads(body_text)
        except (TypeError, ValueError):
            parsed = None
    data = {
        "status_code": result.status_code,
        "headers": response.get("headers") or {},
        "json": parsed,
        "body_json": parsed,
        "body_text": body_text,
    }
    observation = {
        "source": "http_response",
        "status_code": result.status_code,
        "headers": data["headers"],
        "text": body_text,
        "body": parsed if parsed is not None else body_text,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }
    detail = {
        "status_code": result.status_code,
        "duration_ms": result.duration_ms,
        "request": result.request,
        "response": result.response,
        "error": result.error,
        "ignored_overrides": ignored,
        "observation": observation,
    }
    if result.ok:
        error_class = ""
    elif spec_input.get("expected_status") is not None:
        error_class = "STATUS_MISMATCH"
    else:
        error_class = result.error_code or "HTTP_FAILED"
    return NodeExecution(
        status="PASSED" if result.ok else "FAILED",
        error_class=error_class,
        detail=detail,
        data=data,
        observation=observation,
    )


def execute_node(
    node: NodeRun,
    *,
    policy_context: TargetPolicy | ExecutionCapabilities,
    db_engine: Any = None,
    input_override: dict[str, Any] | None = None,
    db: Any = None,
    policy: TargetPolicy | None = None,
) -> NodeExecution:
    """执行单个节点。

    V16-001：``policy_context`` 是**必填**授权对象，必须是
    ``ResolvedExecutionPolicy``（只有 ``decision=ALLOW`` 才放行）或显式的
    ``ExecutionCapabilities``（纯本地节点声明）。不存在“没策略就走 legacy”的分支，
    HTTP/DB/Browser 在没有 ALLOW 策略时不会创建任何 Driver 或网络客户端。
    """
    driver = _driver_key(node)
    spec_input = dict(input_override if input_override is not None else (node.input_ref or {}))
    context = _coerce_policy_context(
        policy_context, node=node, db=db, policy=policy
    )
    if driver in NETWORK_DRIVERS:
        denied = _policy_denial(context, required="network")
        if denied is not None:
            return denied
        return _execute_http_secure(spec_input, node=node, db=db, policy=context)  # type: ignore[arg-type]
    if driver in BROWSER_DRIVERS:
        denied = _policy_denial(context, required="browser")
        if denied is not None:
            return denied
        return _execute_playwright(spec_input, policy_context=context)  # type: ignore[arg-type]
    if driver in DB_DRIVERS:
        denied = _policy_denial(context, required="db_read")
        if denied is not None:
            return denied
        if db is None:
            return NodeExecution(
                status="BLOCKED",
                error_class="POLICY_UNAVAILABLE",
                detail={"reason": "查询注册表需要服务端 DB 会话"},
                data={"blocked": True},
            )
        return _execute_db_secure(spec_input, node=node, db=db)
    if driver in DEVICE_DRIVERS:
        denied = _policy_denial(context, required="device")
        if denied is not None:
            return denied
        return _execute_appium(spec_input, policy_context=context)  # type: ignore[arg-type]
    if driver in EXTERNAL_DRIVERS:
        denied = _policy_denial(context, required="device")
        if denied is not None:
            return denied
        return _execute_external_e2e(spec_input)
    return NodeExecution(
        status="BLOCKED",
        error_class="UNSUPPORTED_DRIVER",
        detail={"driver": driver, "reason": "执行器不支持该 driver"},
        data={"unsupported_driver": driver},
    )


def _execute_playwright(
    spec_input: dict[str, Any],
    *,
    policy_context: TargetPolicy | ExecutionCapabilities,
) -> NodeExecution:
    """浏览器节点：策略由服务端解析，Workflow 不能自带 allowed_hosts（V16-002）。"""
    from app.aiqe.drivers.playwright_driver import PlaywrightDriver

    if not isinstance(policy_context, TargetPolicy):
        return NodeExecution(
            status="BLOCKED",
            error_class="TARGET_POLICY_MISSING_BINDING",
            detail={"reason": "浏览器节点必须绑定服务端 TargetPolicy"},
            data={"blocked": True},
        )
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
        policy=policy_context,
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


def _appium_post(client, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def _validate_device_service_url(url: str) -> str:
    """设备服务（Appium）必须是本机回环地址；Workflow 不能把它指向内网/公网。"""
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(str(url or "").strip())
    except ValueError:
        return "DEVICE_SERVICE_INVALID"
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "DEVICE_SERVICE_INVALID"
    host = parsed.hostname.strip().lower().rstrip(".")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        return "DEVICE_SERVICE_NOT_LOCAL"
    return ""


def _execute_appium(
    spec_input: dict[str, Any],
    *,
    policy_context: TargetPolicy | ExecutionCapabilities,
) -> NodeExecution:
    import httpx

    appium_url = str(spec_input.get("appium_url") or "http://127.0.0.1:4723").rstrip("/")
    url_error = _validate_device_service_url(appium_url)
    if url_error:
        return NodeExecution(
            status="BLOCKED",
            error_class=url_error,
            detail={"reason": "Appium 服务地址必须是本机回环地址", "appium_url": appium_url[:120]},
            data={"blocked": True},
        )
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

def _execute_external_e2e(spec_input: dict[str, Any]) -> NodeExecution:
    """Run a pinned external E2E command (TesterArmy contract).

    Used for cross-tool chains such as Android Appium + MQTT that need a
    workstation/device runner rather than the API process.
    """
    from pathlib import Path

    from app.aiqe.drivers.external_e2e_driver import TesterArmyAdapter

    command = spec_input.get("command")
    version = str(spec_input.get("version") or "").strip()
    if not isinstance(command, list) or not command or not version:
        return NodeExecution(
            status="FAILED",
            error_class="INPUT_INVALID",
            detail={"reason": "external_e2e 需要非空 command 数组和固定 version"},
            data={"result": "FAIL"},
        )
    artifacts_dir = spec_input.get("artifacts_dir")
    adapter = TesterArmyAdapter(
        [str(part) for part in command],
        version=version,
        cwd=spec_input.get("cwd"),
        env={
            str(key): str(value)
            for key, value in (spec_input.get("env") or {}).items()
        },
        timeout_s=float(spec_input.get("timeout_s") or 300),
        artifacts_dir=artifacts_dir,
    )
    try:
        result = adapter.run(replay=bool(spec_input.get("replay", False)))
    except Exception as exc:
        return NodeExecution(
            status="ERROR",
            error_class="EXTERNAL_E2E_ERROR",
            detail={"reason": f"{type(exc).__name__}: {exc}"},
            data={"result": "FAIL"},
        )
    evidence: list[EvidenceFile] = []
    artifact_rows: list[dict[str, Any]] = []
    for artifact in result.artifacts:
        try:
            content = Path(artifact.path).read_bytes()
        except OSError:
            content = b""
        evidence.append(
            EvidenceFile(
                name=artifact.name,
                artifact_type=artifact.artifact_type,
                content=content,
                sha256=artifact.sha256,
                metadata={"source": "external_e2e"},
            )
        )
        artifact_rows.append(
            {
                "name": artifact.name,
                "artifact_type": artifact.artifact_type,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
            }
        )
    status = "PASSED" if result.exit_code == 0 else "FAILED"
    return NodeExecution(
        status=status,
        error_class="" if status == "PASSED" else "EXTERNAL_E2E_FAILED",
        detail={
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
            "replay_exit_code": result.replay_exit_code,
        },
        data={
            "result": "PASS" if status == "PASSED" else "FAIL",
            "json": {
                "result": "PASS" if status == "PASSED" else "FAIL",
                "exit_code": result.exit_code,
            },
            "exit_code": result.exit_code,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
            "artifacts": artifact_rows,
        },
        evidence=evidence,
    )
