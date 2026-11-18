"""v1.4 M2 本地混合 Dogfood：真实 HTTP + Playwright + DB-RO + 断言 + 证据。

不连接生产/测试环境，只在本机临时目录起：
- 一个真实 HTTP 服务（登录 / 建单 / 查单 / 可点击页面）；
- 一个真实 SQLite 目标库；
- 一个真实 Chromium（Playwright）。

验证：
1. `login` 输出 token，`create_order` 的 Authorization 实际收到 token；
2. `create_order` 输出 order_id，DB-RO 与 Public API 实际使用该 id；
3. Playwright 真实点击把状态从 DRAFT 改为 PUBLISHED，probe 不参与；
4. 每步断言落 `run_assertion_results`，HTTP/DB/Playwright 证据落 `run_artifacts`；
5. 同一 TestRun 最终 COMPLETED/PASS。

用法：
  python scripts/qa/aiqe_v14_local_dogfood.py
退出码：0=PASS，1=FAIL。
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_BACKEND = Path(__file__).resolve().parents[2] / "test-platform-v2" / "backend"
if str(REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(REPO_BACKEND))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401,E402 - register all tables
from app.aiqe.models.artifact import RunArtifact  # noqa: E402
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun  # noqa: E402
from app.aiqe.services import execution_service, job_consumer, node_executor  # noqa: E402
from app.aiqe.services.capability_registry import register_manifest  # noqa: E402
from app.aiqe.services.run_context import EnvSecretProvider, RunContext  # noqa: E402
from app.aiqe.services.run_launch import launch_run  # noqa: E402
from app.aiqe.services.workflow_service import approve_workflow, create_workflow  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.db import Base  # noqa: E402
from app.models.execution_job import ExecutionJob  # noqa: E402
from app.models.project import Project  # noqa: E402


class _TargetHandler(BaseHTTPRequestHandler):
    target_db = ""

    def log_message(self, fmt, *args):  # noqa: A003 - silence test server
        return

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            self._json(400, {"error": "bad json"})
            return
        if self.path == "/login":
            self._json(200, {"code": 0, "data": {"token": f"tok-{uuid.uuid4().hex}"}})
            return
        if self.path == "/orders":
            auth = str(self.headers.get("Authorization") or "")
            if not auth.startswith("Bearer tok-"):
                self._json(401, {"error": "unauthorized", "auth": auth})
                return
            order_id = f"order-{uuid.uuid4().hex[:8]}"
            with sqlite3.connect(self.target_db) as connection:
                connection.execute(
                    "INSERT INTO orders (id, status) VALUES (?, ?)", (order_id, "live")
                )
            self._json(200, {"code": 0, "data": {"id": order_id, "item": payload.get("item")}})
            return
        self._json(404, {"error": "not found"})

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/orders/"):
            order_id = self.path.rsplit("/", 1)[-1]
            with sqlite3.connect(self.target_db) as connection:
                row = connection.execute(
                    "SELECT id, status FROM orders WHERE id = ?", (order_id,)
                ).fetchone()
            if row is None:
                self._json(404, {"error": "missing"})
            else:
                self._json(200, {"code": 0, "data": {"id": row[0], "status": row[1]}})
            return
        if self.path.startswith("/ui"):
            self._html(
                200,
                """
<!doctype html><html><head><title>Admin</title></head><body>
<h1>Admin Console</h1>
<button id="publish" onclick="document.getElementById('status').textContent='PUBLISHED'">
  Publish
</button>
<div id="status">DRAFT</div>
</body></html>
""",
            )
            return
        self._json(404, {"error": "not found"})


def _start_server(target_db: str) -> tuple[ThreadingHTTPServer, str]:
    handler = type("DogfoodHandler", (_TargetHandler,), {"target_db": target_db})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _graph(base_url: str) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "login",
                "driver": "http",
                "depends_on": [],
                "input": {
                    "url": f"{base_url}/login",
                    "method": "POST",
                    "allow_private": True,
                    "json_body": {"user": "qa"},
                    "expected_status": 200,
                },
                "outputs": {"token": "$.json.data.token"},
                "assertions": [
                    {
                        "assertion_key": "login_status",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-LOGIN-1",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            },
            {
                "key": "create_order",
                "driver": "http",
                "depends_on": ["login"],
                "input": {
                    "url": f"{base_url}/orders",
                    "method": "POST",
                    "allow_private": True,
                    "headers": {"Authorization": "Bearer ${nodes.login.outputs.token}"},
                    "json_body": {"item": "dogfood"},
                },
                "outputs": {"order_id": "$.json.data.id"},
                "assertions": [
                    {
                        "assertion_key": "order_created",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-ORDER-1",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            },
            {
                "key": "ui_publish",
                "driver": "playwright",
                "depends_on": ["create_order"],
                "input": {
                    "url": f"{base_url}/ui?order=${{nodes.create_order.outputs.order_id}}",
                    "actions": [
                        {"type": "click", "selector": "#publish"},
                        {
                            "type": "assert_text",
                            "selector": "#status",
                            "expected": "PUBLISHED",
                        },
                    ],
                },
                "assertions": [
                    {
                        "assertion_key": "ui_published",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-UI-1",
                        "type": "text_contains",
                        "expected": "PUBLISHED",
                        "severity": "P0",
                    }
                ],
            },
            {
                "key": "db_check",
                "driver": "db",
                "depends_on": ["create_order"],
                "input": {
                    "query_key": "order_status",
                    "params": {"id": "${nodes.create_order.outputs.order_id}"},
                    "allowed_tables": ["orders"],
                    "query_registry": {
                        "order_status": {
                            "sql": "SELECT status FROM orders WHERE id = :id",
                            "allowed_tables": ["orders"],
                        }
                    },
                },
                "assertions": [
                    {
                        "assertion_key": "db_live",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-DB-1",
                        "type": "db_value_eq",
                        "path": "$.rows[0].status",
                        "expected": "live",
                        "severity": "P0",
                    }
                ],
            },
            {
                "key": "verify_public",
                "driver": "http",
                "depends_on": ["ui_publish", "db_check"],
                "input": {
                    "url": f"{base_url}/orders/${{nodes.create_order.outputs.order_id}}",
                    "allow_private": True,
                    "expected_status": 200,
                },
                "assertions": [
                    {
                        "assertion_key": "public_live",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-PUBLIC-1",
                        "type": "jsonpath",
                        "path": "$.data.status",
                        "expected": "live",
                        "severity": "P0",
                    }
                ],
            },
        ],
        "edges": [
            {"from": "login", "to": "create_order"},
            {"from": "create_order", "to": "ui_publish"},
            {"from": "create_order", "to": "db_check"},
            {"from": "ui_publish", "to": "verify_public"},
            {"from": "db_check", "to": "verify_public"},
        ],
        "run_policy": {"max_parallel_nodes": 3, "fail_fast": False},
    }


def _run_playwright_job(db, run: TestRun, node: NodeRun, job: ExecutionJob, graph: dict) -> dict:
    from datetime import UTC, datetime

    job.status = "running"
    job.node_id = "local-dogfood"
    job.claimed_at = datetime.now(UTC)
    job.started_at = datetime.now(UTC)
    job.heartbeat_at = datetime.now(UTC)
    db.commit()
    ctx = RunContext(db, run.id, graph=graph, secrets=EnvSecretProvider())
    resolved = ctx.resolve_node_input(node.node_key, node.input_ref or {})
    execution = node_executor._execute_playwright(dict(resolved.values))
    result = {
        "status": execution.status,
        "driver_status": (
            "SUCCEEDED" if execution.status == "PASSED" else execution.status
        ),
        "error_class": execution.error_class,
        "data": execution.data,
        "detail": execution.detail,
    }
    out = execution_service.complete_from_external_report(
        db,
        job_id=job.id,
        status="completed" if execution.status == "PASSED" else "failed",
        result=result,
        error_message=execution.error_class,
    )
    # 外部 Runner 证据单独落库（截图/Trace/DOM/A11y/console/network）。
    attempt = db.scalar(
        select(StepAttempt)
        .where(StepAttempt.node_run_id == node.id)
        .order_by(StepAttempt.attempt_no.desc())
    )
    if attempt is not None and execution.evidence:
        execution_service.persist_execution_evidence(
            db,
            run=run,
            node=node,
            attempt=attempt,
            execution=execution,
        )
        db.commit()
    return out


def main() -> int:
    tempdir = Path(tempfile.mkdtemp(prefix="aiqe-v14-dogfood-"))
    platform_db = tempdir / "platform.db"
    target_db = tempdir / "target.db"
    with sqlite3.connect(target_db) as connection:
        connection.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, status TEXT)")

    engine = create_engine(f"sqlite:///{platform_db.as_posix()}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    server = None
    try:
        db.add(Project(id=1, code="DOGFOOD", name="Dogfood", owner_id=1, status=1))
        db.flush()
        for node_id, driver, caps, platforms in (
            ("local-http", "http", ["aiqe:http"], ["linux"]),
            ("local-browser", "playwright", ["browser.chromium"], ["linux"]),
            ("local-db", "db", ["db.readonly"], ["linux"]),
        ):
            register_manifest(
                db,
                node_id=node_id,
                driver_key=driver,
                capabilities=caps,
                platforms=platforms,
                max_parallel_sessions=2,
                evidence_ref=f"local://{node_id}/self-check",
            )
        db.commit()

        server, base_url = _start_server(str(target_db))
        graph = _graph(base_url)
        workflow = create_workflow(db, project_id=1, graph=graph)
        approve_workflow(db, workflow.id, approved_by=1)
        db.commit()

        settings.aiqe_db_readonly_url = f"sqlite:///{target_db.as_posix()}"
        execution_service._DB_ENGINE = None
        run = launch_run(
            db,
            project_id=1,
            user_id=None,
            workflow_definition_id=workflow.id,
            launch_key=f"dogfood-{uuid.uuid4().hex[:8]}",
            build_ref="local-dogfood",
            commit_sha="local",
        )
        db.commit()
        if run.status != "RUNNING":
            print(json.dumps({"ok": False, "stage": "launch", "status": run.status,
                              "preflight": run.preflight_json}, ensure_ascii=False, indent=2))
            return 1

        for _ in range(40):
            db.expire_all()
            current = db.get(TestRun, run.id)
            if current.status in {"COMPLETED", "BLOCKED", "ERROR", "CANCELED"}:
                break
            claimed = job_consumer.claim_aiqe_jobs(db)
            if claimed:
                for job_id in claimed:
                    job_consumer.run_job(db, job_id)
                continue
            pending = db.scalar(
                select(ExecutionJob).where(ExecutionJob.status == "pending").order_by(ExecutionJob.id)
            )
            if pending is None:
                break
            payload = json.loads(pending.payload_json or "{}")
            node = db.get(NodeRun, str(payload.get("node_run_id") or ""))
            if node is None or node.driver_key.lower() not in {"playwright", "web", "ui"}:
                break
            _run_playwright_job(db, current, node, pending, graph)
        else:
            pass

        db.expire_all()
        run = db.get(TestRun, run.id)
        nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id).order_by(NodeRun.node_key)))
        assertions = list(
            db.scalars(
                select(RunAssertionResult)
                .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
                .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
                .where(NodeRun.run_id == run.id)
            )
        )
        artifacts = list(
            db.scalars(select(RunArtifact).where(RunArtifact.run_id == run.id))
        )
        payload = {
            "ok": run.status == "COMPLETED" and run.outcome == "PASS",
            "run": {"id": run.id, "status": run.status, "outcome": run.outcome},
            "nodes": [
                {
                    "key": node.node_key,
                    "status": node.status,
                    "error_class": node.error_class,
                    "outputs": node.outputs_json,
                }
                for node in nodes
            ],
            "assertions": [
                {
                    "node": row.assertion_key,
                    "status": row.status,
                    "oracle_ref": row.oracle_ref,
                }
                for row in assertions
            ],
            "artifacts": [
                {
                    "type": row.artifact_type,
                    "sha256": row.sha256,
                    "size_bytes": row.size_bytes,
                    "redaction_status": row.redaction_status,
                }
                for row in artifacts
            ],
            "artifact_types": sorted({row.artifact_type for row in artifacts}),
            "artifact_count": len(artifacts),
            "temp_dir": str(tempdir),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0 if payload["ok"] else 1
    finally:
        if server is not None:
            server.shutdown()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
