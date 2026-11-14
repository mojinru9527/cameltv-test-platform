"""AIQE 外部节点 Runner（浏览器/设备节点执行，M10-347c）。

用途：在具备 Chromium / Appium / 真机的机器上认领 AIQE ExecutionJob，
执行 playwright/appium/http 节点，并把结果回报给平台（平台会回写 NodeRun 状态）。

用法：
  python scripts/qa/aiqe_local_runner.py \
    --base-url http://127.0.0.1:18000 --project-id 1 \
    --node-id local-device-runner --agent-token <token> [--once] [--interval 3]

令牌获取：管理员登录后调用 POST /api/v1/ai/agents/register（需 apitest:execute），
返回一次性 token（也可用 --username/--password 自动注册，密码建议走环境变量）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

REPO_BACKEND = Path(__file__).resolve().parents[2] / "test-platform-v2" / "backend"
if str(REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(REPO_BACKEND))

CAPABILITIES = ["aiqe:http", "aiqe:playwright", "aiqe:appium"]
VAR_RE = re.compile(r"\$\{([^{}]+)\}")


def _secret_value(key: str) -> str | None:
    raw = os.environ.get("AIQE_SECRETS_JSON")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and key in parsed:
                return str(parsed[key])
        except (TypeError, ValueError):
            pass
    return os.environ.get(f"AIQE_SECRET_{key}") or os.environ.get(
        f"AIQE_SECRET_{key.upper()}"
    )


def resolve_input(payload: dict, value=None):
    """在 Runner 本地解析变量；secret 只在 Runner 内存中，不回报给平台。"""
    node_outputs = payload.get("node_outputs") or {}
    fixtures = payload.get("fixtures") or {}
    environ = os.environ
    current = payload.get("input") if value is None else value

    def resolve_ref(ref: str):
        if ref.startswith("nodes."):
            parts = ref.split(".")
            if len(parts) < 4 or parts[2] != "outputs":
                raise ValueError(f"非法节点变量: {ref}")
            outputs = node_outputs.get(parts[1]) or {}
            if parts[3] not in outputs:
                raise ValueError(f"节点输出不存在: {ref}")
            return outputs[parts[3]]
        if ref.startswith("secrets."):
            key = ref.split(".", 1)[1]
            secret = _secret_value(key)
            if secret is None:
                raise ValueError(f"secret 未注入: {key}")
            return secret
        if ref.upper().startswith("SECRET:"):
            key = ref.split(":", 1)[1]
            secret = _secret_value(key)
            if secret is None:
                raise ValueError(f"secret 未注入: {key}")
            return secret
        if ref.upper().startswith("FIXTURE:"):
            key = ref.split(":", 1)[1]
            if key not in fixtures:
                raise ValueError(f"fixture 不存在: {key}")
            return fixtures[key]
        if ref.upper().startswith("ENV:"):
            key = ref.split(":", 1)[1]
            if key not in environ:
                raise ValueError(f"环境变量不存在: {key}")
            return environ[key]
        raise ValueError(f"未知变量: {ref}")

    if isinstance(current, dict):
        return {key: resolve_input(payload, item) for key, item in current.items()}
    if isinstance(current, list):
        return [resolve_input(payload, item) for item in current]
    if not isinstance(current, str):
        return current
    match = VAR_RE.fullmatch(current)
    if match:
        return resolve_ref(match.group(1))

    def replace(part: re.Match[str]):
        resolved = resolve_ref(part.group(1))
        return resolved if isinstance(resolved, str) else str(resolved)

    return VAR_RE.sub(replace, current)


def _login(client: httpx.Client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["data"]["access_token"]


def _register_node(client: httpx.Client, token: str, project_id: int, node_id: str) -> str:
    resp = client.post(
        "/api/v1/ai/agents/register",
        headers={"Authorization": f"Bearer {token}", "X-Project-Id": str(project_id)},
        json={"agent_id": node_id, "capabilities": CAPABILITIES},
    )
    resp.raise_for_status()
    return resp.json()["data"]["token"]


def _claim(client: httpx.Client, headers: dict[str, str], node_id: str) -> dict | None:
    resp = client.post(
        "/api/v1/execution-jobs/claim", headers=headers, json={"node_id": node_id}
    )
    resp.raise_for_status()
    return resp.json().get("data")


def _payload(client: httpx.Client, headers: dict[str, str], node_id: str, job_id: int) -> dict:
    resp = client.get(
        f"/api/v1/execution-jobs/{job_id}/payload",
        headers=headers,
        params={"node_id": node_id},
    )
    resp.raise_for_status()
    return resp.json()["data"]["payload"]


def _report(
    client: httpx.Client,
    headers: dict[str, str],
    node_id: str,
    job_id: int,
    *,
    ok: bool,
    result: dict,
    error: str,
) -> None:
    resp = client.post(
        f"/api/v1/execution-jobs/{job_id}/report",
        headers=headers,
        json={
            "node_id": node_id,
            "status": "completed" if ok else "failed",
            "summary": "aiqe local runner",
            "result": result,
            "error_message": error,
        },
    )
    resp.raise_for_status()


def _upload_evidence(
    client: httpx.Client,
    headers: dict[str, str],
    node_id: str,
    job_id: int,
    execution,
) -> bool:
    files = []
    for item in getattr(execution, "evidence", []) or []:
        if item.content:
            files.append(("files", (item.name, item.content, item.mime_type)))
    if not files:
        return False
    resp = client.post(
        f"/api/v1/execution-jobs/{job_id}/evidence",
        headers=headers,
        params={"node_id": node_id},
        files=files,
    )
    resp.raise_for_status()
    return True


def run_once(
    client: httpx.Client, headers: dict[str, str], node_id: str, *, upload_evidence: bool = True
) -> dict:
    from types import SimpleNamespace

    from app.aiqe.services import node_executor

    job = _claim(client, headers, node_id)
    if not job:
        return {"claimed": False}
    job_id = int(job["id"])
    payload = _payload(client, headers, node_id, job_id)
    try:
        resolved_input = resolve_input(payload)
        resolve_error = ""
    except Exception as exc:  # noqa: BLE001
        resolved_input = {}
        resolve_error = f"{type(exc).__name__}: {exc}"
    node = SimpleNamespace(
        driver_key=str(payload.get("driver") or "http"),
        input_ref=dict(payload.get("input") or {}),
        node_key=payload.get("node_key"),
    )
    if resolve_error:
        execution = node_executor.NodeExecution(
            status="BLOCKED",
            error_class="VARIABLE_NOT_FOUND",
            detail={"reason": resolve_error},
            data={"error": resolve_error},
        )
    else:
        execution = node_executor.execute_node(node, input_override=resolved_input)
    ok = execution.status == "PASSED"
    result = {
        "status": execution.status,
        "driver_status": (
            "SUCCEEDED"
            if execution.status == "PASSED"
            else "BLOCKED"
            if execution.status == "BLOCKED"
            else "ERROR"
            if execution.status == "ERROR"
            else "FAILED"
        ),
        "error_class": execution.error_class,
        "detail": execution.detail,
        "data": execution.data,
    }
    evidence_uploaded = False
    if upload_evidence:
        try:
            evidence_uploaded = _upload_evidence(
                client, headers, node_id, job_id, execution
            )
        except Exception as exc:  # noqa: BLE001 - 证据上传失败不应吞掉执行结论
            result["evidence_upload_error"] = f"{type(exc).__name__}: {exc}"
    _report(
        client,
        headers,
        node_id,
        job_id,
        ok=ok,
        result=result,
        error=execution.error_class,
    )
    return {
        "claimed": True,
        "job_id": job_id,
        "driver": node.driver_key,
        "node_status": execution.status,
        "error_class": execution.error_class,
        "evidence_uploaded": evidence_uploaded,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18000")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--node-id", default="local-device-runner")
    parser.add_argument("--agent-token", default="")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--max-iterations", type=int, default=0)
    parser.add_argument("--no-evidence", action="store_true")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120, trust_env=False) as client:
        token = args.agent_token
        if not token:
            if not args.username or not args.password:
                print(
                    json.dumps(
                        {"error": "需要 --agent-token 或 --username/--password"},
                        ensure_ascii=False,
                    )
                )
                return 2
            login_token = _login(client, args.username, args.password)
            token = _register_node(client, login_token, args.project_id, args.node_id)
        headers = {
            "X-AI-Agent-Token": token,
            "X-Project-Id": str(args.project_id),
        }
        print(json.dumps({"node_id": args.node_id, "base_url": args.base_url}), flush=True)
        iterations = 0
        while True:
            try:
                report = run_once(
                    client, headers, args.node_id, upload_evidence=not args.no_evidence
                )
            except Exception as exc:  # noqa: BLE001
                report = {"error": f"{type(exc).__name__}: {exc}"}
            print(json.dumps(report, ensure_ascii=False, default=str), flush=True)
            iterations += 1
            if args.once or (args.max_iterations and iterations >= args.max_iterations):
                break
            time.sleep(max(0.5, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
