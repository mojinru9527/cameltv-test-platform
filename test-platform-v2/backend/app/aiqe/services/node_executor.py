"""M10-347：AIQE NodeRun 进程内执行器（解决 M9-R4：ExecutionJob 无消费者）。

范围：
- 仅支持 `http` driver（API 级节点）；UI/设备节点仍由 cameltv-node/真机 runner 承担；
- 由 `job_consumer` 在 `AIQE_INPROCESS_EXECUTOR_ENABLED=true` 时调用；
- 执行结果通过 `dag_scheduler.complete_node` 回写，attempt 时间线由 batch-340 持久化。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.aiqe.drivers.httpx_driver import HttpDriver, HttpRequestSpec
from app.aiqe.models.run import NodeRun


@dataclass
class NodeExecution:
    status: str
    error_class: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


def _driver_key(node: NodeRun) -> str:
    return str(node.driver_key or "http").strip().lower()


def execute_node(node: NodeRun) -> NodeExecution:
    driver = _driver_key(node)
    if driver not in {"http", "httpx", "api"}:
        return NodeExecution(
            status="BLOCKED",
            error_class="UNSUPPORTED_DRIVER",
            detail={"driver": driver, "reason": "进程内执行器仅支持 http driver"},
        )

    spec_input = dict(node.input_ref or {})
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
