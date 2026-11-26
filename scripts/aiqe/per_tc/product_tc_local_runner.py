"""产品级 TC 本地 rehearsal runner（隔离本地 Test 环境，不是产品验收）。

用法（由 `scripts/aiqe/run_product_tc.py` 调用）：

    python scripts/aiqe/per_tc/product_tc_local_runner.py --tc TC-AIQE-001

环境变量（由 `local_test_env.py start` 生成）：
    AIQE_TEST_BASE_URL / AIQE_TEST_ADMIN_URL / AIQE_TEST_ADMIN_USER /
    AIQE_TEST_ADMIN_PASSWORD / AIQE_TEST_PROJECT_ID / AIQE_TEST_ENVIRONMENT_ID /
    AIQE_TC_RESULT_PATH

诚实边界
--------
本地隔离环境只有平台自身（SQLite + 本地 HTTP SUT），没有 CamelTv 业务 API/后台 UI/
前台 UI/MySQL/真机/Benchmark 数据集。因此**所有产品级 TC 在本环境一律输出
BLOCKED**（附真实执行到的 API/Run/Assertion id 与具体缺口），绝不输出 PASS；
`docs/aiqe/v1.6/e2e/product-results.json`（官方）只能由真实业务 Test 环境产生。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PREREQUISITES: dict[str, str] = {
    "TC-AIQE-001": "需要收藏赛事 PRD 导入 + 后台人工确认（本地仅跑通 Contract API 部分）",
    "TC-AIQE-002": "需要 CamelTv 业务 API + 后台 UI + 前台 UI + MySQL 只读（本地只跑平台自身 HTTP Run）",
    "TC-AIQE-003": "需要可注入一次 503 的业务 API Stub（本地无业务 API）",
    "TC-AIQE-004": "需要直播入口与可注入浮层的 integration profile（本地无业务 UI）",
    "TC-AIQE-005": "需要共享账号/赛事 fixture 与真实业务并发写（本地无业务 DB）",
    "TC-AIQE-006": "需要真实上游赛程接口 504 Stub（本地无业务上游）",
    "TC-AIQE-007": "需要可强制 kill 浏览器的 Runner 环境（本地未接入外部 Runner）",
    "TC-AIQE-008": "依赖 TC-004 缺陷草稿 + 人工确认 + 修复 commit 部署（本地无业务部署）",
    "TC-AIQE-009": "需要 Android Chrome 模拟器/真机（本地无设备池）",
    "TC-AIQE-010": "需要已关闭缺陷标注集 + Benchmark Gate + 人工批准（本地无数据集）",
}


def _load_env_file() -> None:
    candidates = [
        os.environ.get("AIQE_LOCAL_ENV_FILE"),
        str(ROOT / "work-logs/evidence/aiqe-v16/local-test/local-test-env.env"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
        break


def _request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    token: str | None = None,
    project_id: int | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict]:
    base = os.environ["AIQE_TEST_BASE_URL"].rstrip("/")
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(f"{base}{path}", data=data, method=method)
    request.add_header("content-type", "application/json")
    if token:
        request.add_header("authorization", f"Bearer {token}")
    if project_id:
        request.add_header("X-Project-Id", str(project_id))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body or "null")
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return exc.code, parsed


def _login() -> tuple[str, int]:
    status, body = _request(
        "POST",
        "/api/v1/auth/login",
        payload={
            "username": os.environ.get("AIQE_TEST_ADMIN_USER", "admin"),
            "password": os.environ.get("AIQE_TEST_ADMIN_PASSWORD", ""),
        },
    )
    token = str(((body or {}).get("data") or {}).get("access_token") or "")
    if status != 200 or not token:
        raise RuntimeError(f"登录失败 HTTP {status}: {json.dumps(body, ensure_ascii=False)[:300]}")
    return token, int(os.environ.get("AIQE_TEST_PROJECT_ID") or 0)


def _write_result(record: dict) -> int:
    target = os.environ.get("AIQE_TC_RESULT_PATH")
    if not target:
        print("::error::[product-tc-local] 缺少 AIQE_TC_RESULT_PATH")
        return 1
    Path(target).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return 0


def _contract_flow(token: str, project_id: int) -> dict:
    """TC-001 的 Contract API 部分：draft → approve AC → FROZEN → V2，校验 checksum 稳定。"""
    status, body = _request(
        "POST",
        "/api/v1/aiqe/contracts",
        token=token,
        project_id=project_id,
        payload={
            "requirement_id": "local-favorite-match",
            "title": "收藏赛事（本地 rehearsal）",
            "source_refs": ["prd:local/favorites-v1.md#收藏赛事"],
            "acceptance_criteria": [
                {
                    "ac_id": "AC-LOCAL-1",
                    "given": "已登录",
                    "when": "收藏赛事",
                    "then": ["收藏成功"],
                    "priority": "P1",
                    "oracle_type": "REQ",
                    "oracle_ref": "PRD:local/favorites",
                }
            ],
        },
    )
    if status != 200:
        return {"ok": False, "step": "create_v1", "status": status, "body": body}
    contract = (body or {}).get("data") or {}
    contract_id = str(contract["id"])
    for ac in contract.get("acceptance_criteria") or []:
        status, body = _request(
            "POST",
            f"/api/v1/aiqe/contracts/{contract_id}/approve-ac",
            token=token,
            project_id=project_id,
            payload={"ac_id": ac["ac_id"]},
        )
        if status != 200:
            return {"ok": False, "step": "approve_ac", "status": status, "body": body}
    for target in ("REVIEW_REQUIRED", "APPROVED", "FROZEN"):
        status, body = _request(
            "POST",
            f"/api/v1/aiqe/contracts/{contract_id}/transition",
            token=token,
            project_id=project_id,
            payload={"target": target},
        )
        if status != 200:
            return {"ok": False, "step": f"transition:{target}", "status": status, "body": body}
    status, body = _request(
        "GET", f"/api/v1/aiqe/contracts/{contract_id}", token=token, project_id=project_id
    )
    frozen_checksum = str(((body or {}).get("data") or {}).get("revision_checksum") or "")
    status, body = _request(
        "POST",
        "/api/v1/aiqe/contracts",
        token=token,
        project_id=project_id,
        payload={
            "requirement_id": "local-favorite-match",
            "title": "收藏赛事 V2（本地 rehearsal）",
            "source_refs": ["prd:local/favorites-v2.md#收藏赛事"],
            "acceptance_criteria": [
                {
                    "ac_id": "AC-LOCAL-2",
                    "given": "未登录",
                    "when": "点击收藏",
                    "then": ["提示登录"],
                    "priority": "P1",
                    "oracle_type": "REQ",
                    "oracle_ref": "PRD:local/favorites-v2",
                }
            ],
        },
    )
    v2 = ((body or {}).get("data") or {})
    status, body = _request(
        "GET", f"/api/v1/aiqe/contracts/{contract_id}", token=token, project_id=project_id
    )
    v1_again = str(((body or {}).get("data") or {}).get("revision_checksum") or "")
    return {
        "ok": True,
        "contract_id": contract_id,
        "v1_checksum_before": frozen_checksum,
        "v1_checksum_after": v1_again,
        "v1_checksum_stable": bool(frozen_checksum) and frozen_checksum == v1_again,
        "v2_revision": v2.get("revision"),
        "v2_checksum_differs": str(v2.get("revision_checksum") or "") != frozen_checksum,
    }


def _http_run_flow(token: str, project_id: int) -> dict:
    """TC-002 的平台部分：Workflow → 审批 → Run → Worker → 断言（本地 HTTP SUT）。"""
    base = os.environ["AIQE_TEST_BASE_URL"].rstrip("/")
    graph = {
        "schema_version": "1.0",
        "scenario_key": "local-health",
        "nodes": [
            {
                "key": "health",
                "driver": "http",
                "depends_on": [],
                "input": {"url": f"{base}/health", "expected_status": 200},
                "assertions": [
                    {
                        "assertion_key": "health_ok",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-LOCAL-HEALTH",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            }
        ],
        "edges": [],
    }
    status, body = _request(
        "POST",
        "/api/v1/aiqe/workflows",
        token=token,
        project_id=project_id,
        payload={"graph": graph},
    )
    if status != 200:
        return {"ok": False, "step": "create_workflow", "status": status, "body": body}
    workflow = (body or {}).get("data") or {}
    workflow_id = str(workflow["id"])
    status, body = _request(
        "POST",
        f"/api/v1/aiqe/workflows/{workflow_id}/approve",
        token=token,
        project_id=project_id,
        payload={},
    )
    if status != 200:
        return {"ok": False, "step": "approve_workflow", "status": status, "body": body}
    status, body = _request(
        "POST",
        "/api/v1/aiqe/runs",
        token=token,
        project_id=project_id,
        payload={
            "workflow_definition_id": workflow_id,
            "environment_id": int(os.environ.get("AIQE_TEST_ENVIRONMENT_ID") or 0),
            "launch_key": f"local-tc002-{int(time.time())}",
        },
    )
    if status != 200:
        return {"ok": False, "step": "launch_run", "status": status, "body": body}
    run = ((body or {}).get("data") or {}).get("run") or {}
    run_id = str(run.get("id") or "")
    terminal = {"COMPLETED", "FAILED", "ERROR", "CANCELED"}
    final: dict = run
    for _ in range(60):
        status, body = _request(
            "GET", f"/api/v1/aiqe/runs/{run_id}", token=token, project_id=project_id
        )
        final = ((body or {}).get("data") or {}).get("run") or final
        if str(final.get("status")) in terminal:
            break
        time.sleep(1.0)
    status, body = _request(
        "GET", f"/api/v1/aiqe/runs/{run_id}/nodes", token=token, project_id=project_id
    )
    nodes_payload = (body or {}).get("data") or {}
    raw_nodes = nodes_payload.get("nodes") or []
    nodes = [item.get("node") or {} for item in raw_nodes if isinstance(item, dict)]
    status, body = _request(
        "GET", f"/api/v1/aiqe/runs/{run_id}/assertions", token=token, project_id=project_id
    )
    assertions = ((body or {}).get("data") or {}).get("items") or []
    status, body = _request(
        "GET", f"/api/v1/aiqe/runs/{run_id}/artifacts", token=token, project_id=project_id
    )
    artifacts = ((body or {}).get("data") or {}).get("items") or []
    return {
        "ok": True,
        "workflow_id": workflow_id,
        "workflow_checksum": workflow.get("checksum"),
        "run_id": run_id,
        "run_status": final.get("status"),
        "run_outcome": final.get("outcome"),
        "node_run_ids": [str(node["id"]) for node in nodes if node.get("id")],
        "assertion_ids": [str(item["id"]) for item in assertions if item.get("id")],
        "artifact_refs": [str(item["id"]) for item in artifacts if item.get("id")],
        "job_ids": [
            str(node.get("execution_job_id"))
            for node in nodes
            if node.get("execution_job_id")
        ],
        "assertion_count": len(assertions),
        "note": "Run/Assertion 详情 API 未暴露 assertion id，故 assertion_ids 为空（平台 API 面）。",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="产品级 TC 本地 rehearsal runner")
    parser.add_argument("--tc", required=True)
    args = parser.parse_args(argv)
    _load_env_file()
    tc_id = args.tc
    if tc_id not in PREREQUISITES:
        return _write_result(
            {"tc_id": tc_id, "status": "NOT_RUN", "blocked_reason": "未知 TC"}
        )
    try:
        token, project_id = _login()
        probe: dict = {"health": "ok", "project_id": project_id}
        if tc_id == "TC-AIQE-001":
            probe["contract"] = _contract_flow(token, project_id)
        elif tc_id == "TC-AIQE-002":
            probe["run"] = _http_run_flow(token, project_id)
    except Exception as exc:  # noqa: BLE001 - 本地环境探测失败即记录
        return _write_result(
            {
                "tc_id": tc_id,
                "status": "BLOCKED",
                "blocked_reason": f"本地环境探测失败: {type(exc).__name__}: {exc}"[:500],
            }
        )
    run_probe = probe.get("run") or {}
    record = {
        "tc_id": tc_id,
        "status": "BLOCKED",
        "blocked_reason": (
            PREREQUISITES[tc_id]
            + f"；本地环境探测: {json.dumps(probe, ensure_ascii=False, default=str)[:600]}"
        )[:1000],
        "run_id": run_probe.get("run_id"),
        "project_id": project_id,
        "workflow_snapshot_hash": run_probe.get("workflow_checksum") or "",
        "job_ids": run_probe.get("job_ids") or [],
        "node_run_ids": run_probe.get("node_run_ids") or [],
        "assertion_ids": run_probe.get("assertion_ids") or [],
        "artifact_refs": run_probe.get("artifact_refs") or [],
        "duration_ms": 0,
        "probe": probe,
    }
    return _write_result(record)


if __name__ == "__main__":
    raise SystemExit(main())
