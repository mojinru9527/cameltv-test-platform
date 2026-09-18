"""B1-7 端到端演练：真实平台 + 真实节点 CLI + 真实 httpx/Chromium + 真实证据。

为什么需要它：B1-7 的 DoD 是「8 条用例（5 接口 + 3 Web）真实跑通、证据可查、
节点下线任务回 pending」。Test5 内网需要 VPN，本机不可达（192.168.50.170:80 不通），
但**链路本身**可以在本地完整验证——用本地替身当被测系统，其余每一环都是真的：
真 Alembic 迁移建库、真 uvicorn、真节点 CLI 子进程、真 httpx、真 Chromium、
真 sha256 对账、真下载校验。

诚实边界（写进输出，不接受含糊）：
  - 被测目标是**本地替身**，不是 Test5；体育 16.x 真实验收仍需 VPN 机器；
  - 演练把租约压到 3s，好在秒级观察「断线回收」；生产默认 300s，同一套代码路径。
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "test-platform-v2" / "backend"
NODE_CLI = REPO_ROOT / "scripts" / "node" / "cameltv_node" / "cli.py"
LEASE_SECONDS = 3  # 仅演练：把租约压到 3s
# 本机装有系统代理（IE/WinHTTP 注册表 127.0.0.1:7688，未监听）。
# httpx 的 trust_env 会读注册表代理设置，把 127.0.0.1 也代理出去 → 502。
# 演练全部走本机回环，因此显式禁用代理；真实使用中访问云平台应保留代理支持。
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")

PAGE_HTML = (
    '<!doctype html><html><head><title>替身被测系统</title></head><body>'
    '<h1 id="title">赛事首页</h1><div class="banner">banner</div>'
    '<a href="/page2" id="go">下一页</a></body></html>'
)
PAGE2_HTML = (
    '<!doctype html><html><head><title>第二页</title></head><body>'
    '<h1 id="title">赛事详情</h1></body></html>'
)


class _StandInHandler(BaseHTTPRequestHandler):
    """本地替身：2 个接口 + 2 个页面，替代不可达的 Test5。"""

    def log_message(self, *args):
        return

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server 约定
        if self.path.startswith("/api/home"):
            payload = {"status": 200, "data": {"today": "20260918", "list": [1, 2, 3]}}
            self._send(json.dumps(payload).encode(), "application/json")
        elif self.path.startswith("/api/list"):
            payload = {"status": 200, "data": {"list": [{"id": 1}, {"id": 2}]}}
            self._send(json.dumps(payload).encode(), "application/json")
        elif self.path.startswith("/page2"):
            self._send(PAGE2_HTML.encode(), "text/html; charset=utf-8")
        elif self.path.startswith("/page"):
            self._send(PAGE_HTML.encode(), "text/html; charset=utf-8")
        else:
            self._send(b"not found", "text/plain", status=404)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_stand_in() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", free_port()), _StandInHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def run_migrations(db_url: str, evidence_dir: Path) -> None:
    env = {
        **os.environ,
        "DATABASE_URL": db_url,
        "EXECUTION_EVIDENCE_STORAGE_DIR": str(evidence_dir),
        "AUTO_CREATE_TABLES": "false",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"迁移失败: {result.stdout[-800:]} {result.stderr[-800:]}")


def start_platform(db_url: str, evidence_dir: Path, lease_seconds: int):
    """独立子进程里跑真实 uvicorn（真实迁移建的表 + 真实 seed）。"""
    port = free_port()
    env = {
        **os.environ,
        "DATABASE_URL": db_url,
        "ADMIN_USERNAME": "drill-admin",
        "ADMIN_PASSWORD": "Drill-Passw0rd!",
        "AUTO_CREATE_TABLES": "false",
        "EXECUTION_EVIDENCE_STORAGE_DIR": str(evidence_dir),
        "EXECUTION_JOB_LEASE_SECONDS": str(lease_seconds),
        "ENVIRONMENT": "development",
    }
    script = (
        "import sys;"
        f"sys.path.insert(0, r'{BACKEND}');"
        "import uvicorn;"
        "from app.main import app;"
        f"uvicorn.run(app, host='127.0.0.1', port={port}, log_level='warning')"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"平台进程提前退出: {(proc.stdout or '').read()[-800:]}")
        try:
            httpx.get(f"{base}/api/v1/auth/sso-config", timeout=2)
            return proc, base
        except httpx.HTTPError:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("平台未能在 120s 内启动")


class Drill:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append((name, bool(ok), detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return bool(ok)


def build_cases(target: str) -> tuple[list[dict], list[dict]]:
    api_specs = [
        ("/api/home", [{"type": "status", "expected": 200}, {"type": "json_path", "path": "$.status", "expected": 200}]),
        ("/api/home", [{"type": "status", "expected": 200}, {"type": "json_path", "path": "$.data.today", "expected": "20260918"}]),
        ("/api/list", [{"type": "status", "expected": 200}, {"type": "not_empty", "path": "$.data.list"}]),
        ("/api/list", [{"type": "status", "expected": 200}, {"type": "json_path", "path": "$.data.list[0].id", "expected": 1}]),
        ("/api/home", [{"type": "status", "expected": 200}, {"type": "text_contains", "expected": "20260918"}]),
    ]
    api_cases = [
        {
            "id": f"api-{index}",
            "name": f"替身接口用例 {index}",
            "request": {"method": "GET", "url": path},
            "assertions": assertions,
        }
        for index, (path, assertions) in enumerate(api_specs, start=1)
    ]
    web_cases = [
        {
            "id": "web-1",
            "name": "首页标题可见",
            "steps": [
                {"action": "goto", "url": "/page"},
                {"action": "wait_visible", "selector": "#title"},
                {"action": "expect_text", "selector": "#title", "expected": "赛事首页"},
            ],
        },
        {
            "id": "web-2",
            "name": "banner 可见",
            "steps": [
                {"action": "goto", "url": "/page"},
                {"action": "expect_visible", "selector": ".banner"},
            ],
        },
        {
            "id": "web-3",
            "name": "点击跳转第二页",
            "steps": [
                {"action": "goto", "url": "/page"},
                {"action": "click", "selector": "#go"},
                {"action": "wait_visible", "selector": "#title"},
                {"action": "expect_text", "selector": "#title", "expected": "赛事详情"},
            ],
        },
    ]
    return api_cases, web_cases


def main() -> int:
    drill = Drill()
    tmp = Path(tempfile.mkdtemp(prefix="cameltv-b1-drill-"))
    evidence_dir = tmp / "evidence"
    db_url = f"sqlite:///{(tmp / 'drill.db').as_posix()}"

    stand_in, target = start_stand_in()
    print(f"替身被测系统: {target}")
    run_migrations(db_url, evidence_dir)
    drill.check("Alembic 真实迁移建库（upgrade head 退出码 0）", True)

    platform = None
    try:
        platform, base = start_platform(db_url, evidence_dir, LEASE_SECONDS)
        print(f"平台: {base}")
        api = httpx.Client(base_url=base, timeout=180, trust_env=False)

        login = api.post(
            "/api/v1/auth/login",
            json={"username": "drill-admin", "password": "Drill-Passw0rd!"},
        )
        try:
            login_payload = login.json()
        except ValueError:
            login_payload = {}
            print(f"登录响应非 JSON: HTTP {login.status_code} body={login.text[:400]!r}")
        token = (login_payload.get("data") or {}).get("access_token")
        drill.check(
            "平台登录（真实 seed + 真实 JWT）",
            bool(token),
            f"HTTP {login.status_code}",
        )
        if not token:
            print(login.text[:500])
            return 1
        admin_headers = {"Authorization": f"Bearer {token}"}

        raw_projects = api.get("/api/v1/projects", headers=admin_headers).json().get("data") or []
        items = raw_projects.get("items") if isinstance(raw_projects, dict) else raw_projects
        if not items:
            created_project = api.post(
                "/api/v1/projects",
                json={"code": "DRILL", "name": "Drill Project"},
                headers=admin_headers,
            ).json()["data"]
            items = [created_project]
        project_id = int(items[0]["id"])
        admin_headers["X-Project-Id"] = str(project_id)
        drill.check("取到项目上下文", project_id > 0, f"project_id={project_id}")

        node_id = "drill-node"
        reg = api.post(
            "/api/v1/ai/agents/register",
            json={"agent_id": node_id, "capabilities": ["api", "web"]},
            headers=admin_headers,
        )
        node_token = reg.json()["data"]["token"]
        drill.check("注册执行节点并签发节点令牌", bool(node_token), f"node={node_id}")

        api_cases, web_cases = build_cases(target)
        created: dict[str, int] = {}
        for kind, cases in (("api", api_cases), ("web", web_cases)):
            resp = api.post(
                "/api/v1/execution-jobs",
                json={
                    "kind": kind,
                    "case_refs": [case["id"] for case in cases],
                    "env_ref": "local-stand-in",
                    "payload": {"base_url": target, "cases": cases},
                },
                headers=admin_headers,
            )
            created[kind] = int(resp.json()["data"]["id"])
        drill.check(
            "登记执行任务：5 接口 + 3 Web", len(created) == 2, f"job ids = {created}"
        )

        node_env = {
            **os.environ,
            "CAMELTV_BASE_URL": base,
            "CAMELTV_NODE_ID": node_id,
            "CAMELTV_NODE_TOKEN": node_token,
            "CAMELTV_JWT": token,
            "CAMELTV_PROJECT_ID": str(project_id),
            # 隔离节点配置：不读写用户真实的 ~/.cameltv-node.json
            "USERPROFILE": str(tmp),
            "HOME": str(tmp),
        }
        for kind in ("api", "web"):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(NODE_CLI),
                    "up",
                    "--once",
                    "--work-dir",
                    str(tmp / "node-evidence"),
                    "--poll-seconds",
                    "1",
                ],
                env=node_env,
                capture_output=True,
                text=True,
                timeout=1200,
            )
            tail = " | ".join((proc.stdout or "").strip().splitlines()[-2:])
            drill.check(
                f"cameltv-node up --once 跑 {kind} 任务（退出码 {proc.returncode}）",
                proc.returncode == 0,
                tail,
            )
            if proc.returncode != 0:
                print((proc.stdout or "")[-1500:])
                print((proc.stderr or "")[-1500:])

        for kind, job_id in created.items():
            job = api.get(f"/api/v1/execution-jobs/{job_id}", headers=admin_headers).json()["data"]
            expected_total = len(api_cases if kind == "api" else web_cases)
            drill.check(
                f"{kind} 任务 {job_id}: {expected_total}/{expected_total} 通过并上报",
                job["status"] == "completed"
                and job["result"]["passed"] == expected_total
                and job["result"]["failed"] == 0,
                f"status={job['status']} passed={job['result']['passed']}",
            )

            listed = api.get(
                f"/api/v1/execution-jobs/{job_id}/evidence", headers=admin_headers
            ).json()["data"]
            bundles = listed["bundles"]
            if not drill.check(f"{kind} 证据包可查", len(bundles) == 1, f"bundles={len(bundles)}"):
                continue
            manifest = bundles[0]
            drill.check(
                f"{kind} 证据清单含逐文件 sha256",
                manifest["file_count"] > 0 and all(e.get("sha256") for e in manifest["files"]),
                f"attempt={manifest['attempt']} files={manifest['file_count']}",
            )

            mismatches: list[str] = []
            for entry in manifest["files"]:
                got = api.get(
                    f"/api/v1/execution-jobs/{job_id}/evidence/{entry['name']}",
                    params={"attempt": manifest["attempt"]},
                    headers=admin_headers,
                )
                if got.status_code != 200 or hashlib.sha256(got.content).hexdigest() != entry["sha256"]:
                    mismatches.append(entry["name"])
            drill.check(
                f"{kind} 证据可下载且 sha256 与 manifest 一致",
                not mismatches,
                "全部一致" if not mismatches else f"不一致: {mismatches}",
            )
            if kind == "web":
                shots = [e["name"] for e in manifest["files"] if e["name"].endswith(".png")]
                drill.check("Web 用例截图落盘", len(shots) == 3, f"screenshots={shots}")

        # ── 失败用例证据：DoD 明确要求「失败用例有截图/请求回放」。
        #    只跑通过用例证明不了这一条，必须真的跑失败用例并检查留存的证据。 ──
        negative = {
            "api": {
                "cases": [
                    {
                        "id": "neg-api",
                        "name": "故意失败：500 断言 200",
                        "request": {"method": "GET", "url": "/api/boom"},
                        "assertions": [{"type": "status", "expected": 200}],
                    }
                ],
                "expect_files": ["neg-api.request.json", "neg-api.response.json"],
            },
            "web": {
                "cases": [
                    {
                        "id": "neg-web",
                        "name": "故意失败：断言不存在的文案",
                        "steps": [
                            {"action": "goto", "url": "/page"},
                            {
                                "action": "expect_text",
                                "selector": "#title",
                                "expected": "这段文案不存在",
                            },
                        ],
                    }
                ],
                "expect_files": ["neg-web.png", "neg-web.console.json"],
            },
        }
        for kind, spec in negative.items():
            neg_job = api.post(
                "/api/v1/execution-jobs",
                json={
                    "kind": kind,
                    "case_refs": [case["id"] for case in spec["cases"]],
                    "env_ref": "local-stand-in",
                    "payload": {"base_url": target, "cases": spec["cases"]},
                },
                headers=admin_headers,
            ).json()["data"]
            proc = subprocess.run(
                [
                    sys.executable,
                    str(NODE_CLI),
                    "up",
                    "--once",
                    "--work-dir",
                    str(tmp / "node-evidence"),
                    "--poll-seconds",
                    "1",
                ],
                env=node_env,
                capture_output=True,
                text=True,
                timeout=1200,
            )
            after = api.get(
                f"/api/v1/execution-jobs/{neg_job['id']}", headers=admin_headers
            ).json()["data"]
            drill.check(
                f"{kind} 失败用例未被伪造成通过（任务 status={after['status']}）",
                after["status"] == "failed" and after["result"]["failed"] == 1,
                f"passed={after['result']['passed']} failed={after['result']['failed']}",
            )
            neg_bundles = api.get(
                f"/api/v1/execution-jobs/{neg_job['id']}/evidence", headers=admin_headers
            ).json()["data"]["bundles"]
            names = {entry["name"] for entry in neg_bundles[0]["files"]} if neg_bundles else set()
            missing = [name for name in spec["expect_files"] if name not in names]
            drill.check(
                f"{kind} 失败用例留存请求回放/截图证据",
                not missing,
                f"files={sorted(names)}" if not missing else f"缺失: {missing}",
            )
            drill.check(
                f"{kind} 节点对失败任务仍正常退出（退出码 {proc.returncode}）",
                proc.returncode == 0,
                "失败是任务结论，不是节点崩溃",
            )

        orphan = api.post(
            "/api/v1/execution-jobs",
            json={"kind": "api", "case_refs": ["orphan"], "payload": {"cases": api_cases[:1]}},
            headers=admin_headers,
        ).json()["data"]
        node_headers = {"X-AI-Agent-Token": node_token}
        claimed = api.post(
            "/api/v1/execution-jobs/claim", json={"node_id": node_id}, headers=node_headers
        ).json()["data"]
        drill.check(
            "节点认领任务（HTTP + 节点令牌）",
            bool(claimed) and claimed["id"] == orphan["id"] and claimed["attempt"] == 1,
            f"job={claimed['id'] if claimed else '-'}",
        )
        time.sleep(LEASE_SECONDS + 2)
        reclaimed = api.post(
            "/api/v1/execution-jobs/reclaim-stale", json={}, headers=admin_headers
        ).json()["data"]
        after = api.get(
            f"/api/v1/execution-jobs/{orphan['id']}", headers=admin_headers
        ).json()["data"]
        drill.check(
            "失去心跳后任务回到 pending（断线不丢任务）",
            reclaimed["reclaimed"] >= 1 and after["status"] == "pending" and after["node_id"] == "",
            f"reclaimed={reclaimed['reclaimed']} status={after['status']}",
        )
        again = api.post(
            "/api/v1/execution-jobs/claim", json={"node_id": node_id}, headers=node_headers
        ).json()["data"]
        drill.check(
            "节点恢复后可再认领同一任务（attempt 递增）",
            bool(again) and again["id"] == orphan["id"] and again["attempt"] == 2,
            f"attempt={again['attempt'] if again else '-'}",
        )
    finally:
        if platform is not None:
            platform.terminate()
            try:
                platform.wait(timeout=20)
            except subprocess.TimeoutExpired:
                platform.kill()
        stand_in.shutdown()

    passed = sum(1 for _, ok, _ in drill.checks if ok)
    total = len(drill.checks)
    print("\n================ B1-7 演练结果 ================")
    print(f"目标系统：本地替身 {target}（Test5 内网需 VPN，本机不可达——不是 Test5 验收）")
    print(f"租约：{LEASE_SECONDS}s（演练压缩；生产默认 300s，同一代码路径）")
    print(f"通过 {passed}/{total}")
    for name, ok, _detail in drill.checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"证据目录：{evidence_dir}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
