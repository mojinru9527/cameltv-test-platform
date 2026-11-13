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
import sys
import time
from pathlib import Path

import httpx

REPO_BACKEND = Path(__file__).resolve().parents[2] / "test-platform-v2" / "backend"
if str(REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(REPO_BACKEND))

CAPABILITIES = ["aiqe:http", "aiqe:playwright", "aiqe:appium"]


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


def run_once(client: httpx.Client, headers: dict[str, str], node_id: str) -> dict:
    from types import SimpleNamespace

    from app.aiqe.services import node_executor

    job = _claim(client, headers, node_id)
    if not job:
        return {"claimed": False}
    job_id = int(job["id"])
    payload = _payload(client, headers, node_id, job_id)
    node = SimpleNamespace(
        driver_key=str(payload.get("driver") or "http"),
        input_ref=dict(payload.get("input") or {}),
        node_key=payload.get("node_key"),
    )
    execution = node_executor.execute_node(node)
    ok = execution.status == "PASSED"
    result = {
        "status": execution.status,
        "error_class": execution.error_class,
        **execution.detail,
    }
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
                report = run_once(client, headers, args.node_id)
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
