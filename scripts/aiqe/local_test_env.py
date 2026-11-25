"""AIQE 本地隔离 Test 环境（rehearsal，不是产品验收环境）。

作用
----
在本地拉起一个**隔离**的测试平台实例（独立 SQLite + 独立端口 + 独立密钥），并把
产品级 TC 执行器需要的最小上下文准备好：

    AIQE_TEST_BASE_URL        http://127.0.0.1:<port>
    AIQE_TEST_ADMIN_URL       http://127.0.0.1:<port>        （后台 API；UI 需前端 dev server）
    AIQE_TEST_DB_READONLY_DSN sqlite:///...?...（仅本地演练；生产必须是 PG 只读 role）
    AIQE_TEST_ADMIN_USER / AIQE_TEST_ADMIN_PASSWORD
    AIQE_TEST_PROJECT_ID / AIQE_TEST_ENVIRONMENT_ID

同时写入 target policy（允许 127.0.0.1/私网，仅本地 SUT）与基础环境记录。

边界
----
本环境**不能**替代隔离 Test 业务环境的 TC-AIQE-001..010 产品验收：
- 无 CamelTv 业务 API/后台 UI/前台 UI/MySQL/真机；
- SQLite 只读 URI 不是 PostgreSQL 只读 role。

用法
----
    python scripts/aiqe/local_test_env.py start [--port 8101]
    python scripts/aiqe/local_test_env.py status
    python scripts/aiqe/local_test_env.py stop
    python scripts/aiqe/local_test_env.py env          # 打印 export 行
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "test-platform-v2/backend"
DATA_DIR = ROOT / "work-logs/evidence/aiqe-v16/local-test"
STATE = DATA_DIR / "state.json"
ENV_FILE = DATA_DIR / "local-test-env.env"
DB_FILE = DATA_DIR / "platform.db"
ADMIN_USER = "admin"
DEFAULT_PORT = 8101


def _free_port(preferred: int) -> int:
    for port in [preferred, preferred + 1, preferred + 2, preferred + 3, 0]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return sock.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("找不到可用端口")


def _request(
    method: str,
    url: str,
    *,
    payload: dict | None = None,
    token: str | None = None,
    project_id: int | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("content-type", "application/json")
    if token:
        request.add_header("authorization", f"Bearer {token}")
    if project_id:
        request.add_header("X-Project-Id", str(project_id))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body or "null")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body or "null")
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return exc.code, parsed


def _load_state() -> dict:
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def _wait_health(base_url: str, timeout_seconds: float = 180.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            status, _ = _request("GET", f"{base_url}/health", timeout=3)
            if status == 200:
                return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1.0)
    return False


def _login(base_url: str, username: str, password: str) -> tuple[str, dict]:
    status, body = _request(
        "POST", f"{base_url}/api/v1/auth/login", payload={"username": username, "password": password}
    )
    data = (body or {}).get("data") or {}
    if status != 200 or not data.get("access_token"):
        raise RuntimeError(f"登录失败 HTTP {status}: {json.dumps(body, ensure_ascii=False)[:300]}")
    return str(data["access_token"]), data


def _ensure_project(base_url: str, token: str) -> int:
    status, body = _request("GET", f"{base_url}/api/v1/projects", token=token)
    items = ((body or {}).get("data") or []) if status == 200 else []
    for item in items:
        if item.get("code") == "AIQE-LOCAL":
            return int(item["id"])
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/projects",
        token=token,
        payload={"code": "AIQE-LOCAL", "name": "AIQE Local Isolated", "description": "rehearsal"},
    )
    if status != 200:
        raise RuntimeError(f"创建项目失败 HTTP {status}: {json.dumps(body, ensure_ascii=False)[:300]}")
    return int(((body or {}).get("data") or {})["id"])


def _ensure_environment(base_url: str, token: str, project_id: int) -> int:
    status, body = _request(
        "GET", f"{base_url}/api/v1/environments", token=token, project_id=project_id
    )
    items = ((body or {}).get("data") or []) if status == 200 else []
    for item in items:
        if item.get("name") == "local-isolated":
            return int(item["id"])
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/environments",
        token=token,
        project_id=project_id,
        payload={
            "name": "local-isolated",
            "env_type": "test",
            "base_url": base_url,
            "description": "local rehearsal SUT (AIQE self)",
            "access_type": "public",
            "execution_mode": "on_platform",
        },
    )
    if status != 200:
        raise RuntimeError(
            f"创建环境失败 HTTP {status}: {json.dumps(body, ensure_ascii=False)[:300]}"
        )
    return int(((body or {}).get("data") or {})["id"])


def _ensure_target_policy(base_url: str, token: str, project_id: int, port: int) -> None:
    status, body = _request(
        "GET",
        f"{base_url}/api/v1/aiqe/admin/target-policies",
        token=token,
        project_id=project_id,
    )
    if status == 200 and ((body or {}).get("data") or []):
        return
    status, body = _request(
        "POST",
        f"{base_url}/api/v1/aiqe/admin/target-policies",
        token=token,
        project_id=project_id,
        payload={
            "name": "local-isolated",
            "policy": {
                "allowed_hosts": ["127.0.0.1"],
                "allowed_ports": [port],
                "allow_private": True,
            },
        },
    )
    if status != 200:
        raise RuntimeError(
            f"写入 target policy 失败 HTTP {status}: {json.dumps(body, ensure_ascii=False)[:300]}"
        )


def _seed_capabilities() -> None:
    """为本地隔离实例注册 HTTP/DB 能力 manifest（rehearsal 必需，生产由 Runner 心跳注册）。"""
    script = (
        "from app.core.db import SessionLocal\n"
        "from app.aiqe.services.capability_registry import register_manifest\n"
        "db = SessionLocal()\n"
        "try:\n"
        "    register_manifest(db, node_id='local-http', driver_key='http',\n"
        "        capabilities=['aiqe:http', 'http'], platforms=['linux'],\n"
        "        evidence_ref='evidence://local-http')\n"
        "    register_manifest(db, node_id='local-db', driver_key='db',\n"
        "        capabilities=['aiqe:db', 'db.readonly'], platforms=['linux'],\n"
        "        evidence_ref='evidence://local-db')\n"
        "    db.commit()\n"
        "finally:\n"
        "    db.close()\n"
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "development",
        "DATABASE_URL": f"sqlite:///{(DB_FILE).as_posix()}",
    }
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _write_env_file(state: dict) -> None:
    lines = [
        f"AIQE_TEST_BASE_URL={state['base_url']}",
        f"AIQE_TEST_ADMIN_URL={state['base_url']}",
        f"AIQE_TEST_DB_READONLY_DSN={state['readonly_dsn']}",
        f"AIQE_TEST_ADMIN_USER={ADMIN_USER}",
        f"AIQE_TEST_ADMIN_PASSWORD={state['admin_password']}",
        f"AIQE_TEST_PROJECT_ID={state['project_id']}",
        f"AIQE_TEST_ENVIRONMENT_ID={state['environment_id']}",
        f"AIQE_LOCAL_PORT={state['port']}",
        f"AIQE_LOCAL_DATA_DIR={DATA_DIR}",
    ]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def start(port: int) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    if state.get("pid") and _pid_alive(int(state["pid"])) and _wait_health(state["base_url"], 3):
        print(json.dumps({"status": "already-running", **state}, ensure_ascii=False))
        return 0
    chosen = _free_port(port)
    base_url = f"http://127.0.0.1:{chosen}"
    # 已存在的隔离 DB 必须复用原 admin 密码（seed 只在首次启动创建 admin）。
    previous_password = ""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("AIQE_TEST_ADMIN_PASSWORD="):
                previous_password = line.split("=", 1)[1].strip()
                break
    previous_password = previous_password or str(state.get("admin_password") or "")
    if DB_FILE.exists() and previous_password:
        admin_password = previous_password
    else:
        admin_password = "Local-" + secrets.token_urlsafe(18)
    env = {
        **os.environ,
        "ENVIRONMENT": "development",
        "DATABASE_URL": f"sqlite:///{(DB_FILE).as_posix()}",
        "SECRET_KEY": secrets.token_urlsafe(48),
        "ADMIN_PASSWORD": admin_password,
        "SEED_DEMO_USERS": "false",
        "ALLOWED_ORIGINS": base_url,
        "AIQE_INPROCESS_EXECUTOR_ENABLED": "true",
        "AIQE_INPROCESS_POLL_SECONDS": "1",
    }
    log = (DATA_DIR / "backend.log").open("ab")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(chosen),
        ],
        cwd=BACKEND,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
        close_fds=True,
    )
    state = {
        "pid": process.pid,
        "port": chosen,
        "base_url": base_url,
        "admin_password": admin_password,
        "readonly_dsn": f"sqlite:///{(DB_FILE).as_posix()}?mode=ro&uri=true",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    _save_state(state)
    if not _wait_health(base_url):
        raise RuntimeError(f"后端未在 180s 内就绪，见 {(DATA_DIR / 'backend.log').as_posix()}")
    _seed_capabilities()
    token, _ = _login(base_url, ADMIN_USER, admin_password)
    project_id = _ensure_project(base_url, token)
    environment_id = _ensure_environment(base_url, token, project_id)
    _ensure_target_policy(base_url, token, project_id, chosen)
    state.update({"project_id": project_id, "environment_id": environment_id})
    _save_state(state)
    _write_env_file(state)
    print(json.dumps({"status": "started", **state, "env_file": str(ENV_FILE)}, ensure_ascii=False))
    return 0


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop() -> int:
    state = _load_state()
    pid = int(state.get("pid") or 0)
    if pid and _pid_alive(pid):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
    print(json.dumps({"status": "stopped", "pid": pid}, ensure_ascii=False))
    return 0


def status() -> int:
    state = _load_state()
    if not state:
        print(json.dumps({"status": "not-started"}, ensure_ascii=False))
        return 1
    healthy = _wait_health(state.get("base_url", ""), 3)
    print(json.dumps({"status": "running" if healthy else "unhealthy", **state}, ensure_ascii=False))
    return 0 if healthy else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIQE 本地隔离 Test 环境（rehearsal）")
    parser.add_argument("action", choices=("start", "stop", "status", "env"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if args.action == "start":
        return start(args.port)
    if args.action == "stop":
        return stop()
    if args.action == "env":
        state = _load_state()
        if not state:
            print("::error::[local-test-env] 尚未启动")
            return 1
        print(ENV_FILE.read_text(encoding="utf-8"))
        return 0
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
