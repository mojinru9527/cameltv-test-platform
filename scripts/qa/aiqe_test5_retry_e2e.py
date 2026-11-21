"""V16-017 TC-003 产品级：API 首次 503 + 重试成功，且不得掩盖失败。

- test-side fault proxy：第一次请求返回 503，第二次转发到真实 test5 API；
- AIQE DAG `retry.max_attempts=2`；第一次 attempt FAILED 证据必须保留；
- 最终 Run PASS，但 report 同时包含 first_failed=true 与两次 attempt/断言证据。
"""
from __future__ import annotations

import argparse
import json
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import job_consumer
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.core.db import Base
from app.models.project import Project

TARGET_PATH = "/account-service/ee/client/general"
UPSTREAM = "https://camel-test5.elelive.cn"


class _FaultProxy(BaseHTTPRequestHandler):
    hits = 0

    def log_message(self, *_args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        _FaultProxy.hits += 1
        if _FaultProxy.hits == 1:
            body = b'{"status":503,"msg":"injected 503"}'
            self.send_response(503)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        try:
            response = requests.get(UPSTREAM + self.path, timeout=20)
            body = response.content
            self.send_response(response.status_code)
            self.send_header("content-type", response.headers.get("content-type", "application/json"))
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:  # noqa: BLE001
            body = json.dumps({"status": 502, "msg": f"proxy error: {type(exc).__name__}"}).encode()
            self.send_response(502)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def _drain(db: Session, graph: dict) -> None:
    for _ in range(30):
        claimed = job_consumer.claim_aiqe_jobs(db)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db, job_id)
        db.commit()
        from app.aiqe.services import dag_scheduler

        runs = list(db.scalars(select(TestRun).where(TestRun.status == "RUNNING")))
        for run in runs:
            dag_scheduler.schedule(db, run.id, graph)
        db.commit()


def run(*, out: Path) -> dict:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FaultProxy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(Project(id=1, code="TEST5", name="Camel test5", owner_id=1, status=1))
            db.flush()
            register_manifest(
                db,
                node_id="retry-http",
                driver_key="http",
                capabilities=["aiqe:http"],
                platforms=["linux"],
                evidence_ref="evidence://retry-http",
            )
            upsert_target_policy(
                db,
                project_id=1,
                environment_id=None,
                policy={
                    "allowed_hosts": ["127.0.0.1"],
                    "allowed_ports": [port],
                    "allowed_schemes": ["http"],
                    "allow_private_cidrs": ["127.0.0.0/8"],
                },
            )
            graph = {
                "schema_version": "1.0",
                "retry": {"max_attempts": 2},
                "nodes": [
                    {
                        "key": "first_503_then_ok",
                        "driver": "http",
                        "depends_on": [],
                        "input": {
                            "url": f"http://127.0.0.1:{port}{TARGET_PATH}",
                            "expected_status": 200,
                        },
                        "assertions": [
                            {
                                "assertion_key": "http_200",
                                "oracle_layer": "REQ",
                                "oracle_ref": "TC-AIQE-003-RETRY",
                                "type": "http_status",
                                "expected": 200,
                                "severity": "P0",
                            }
                        ],
                    }
                ],
                "edges": [],
            }
            workflow = create_workflow(db, project_id=1, graph=graph)
            approve_workflow(db, workflow.id, approved_by=1)
            run = launch_run(
                db,
                project_id=1,
                user_id=1,
                workflow_definition_id=workflow.id,
                launch_key=f"tc003-retry-{uuid.uuid4().hex}",
            )
            db.commit()
            _drain(db, graph)
            db.expire_all()
            run = db.get(TestRun, run.id)
            node = db.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
            attempts = list(
                db.scalars(
                    select(StepAttempt)
                    .where(StepAttempt.node_run_id == node.id)
                    .order_by(StepAttempt.attempt_no)
                )
            )
            assertion_ids = [
                row.id
                for row in db.scalars(
                    select(RunAssertionResult).where(
                        RunAssertionResult.step_attempt_id.in_([a.id for a in attempts])
                    )
                )
            ]
            first_failed = bool(attempts and attempts[0].status == "FAILED")
            report = {
                "schema_version": "1.0",
                "status": "PASS"
                if run.outcome == "PASS" and first_failed and len(attempts) >= 2
                else "FAIL",
                "executed_at": datetime.now(UTC).isoformat(),
                "target": f"http://127.0.0.1:{port}{TARGET_PATH}",
                "upstream": UPSTREAM,
                "proxy_hits": _FaultProxy.hits,
                "run_id": run.id,
                "run_status": run.status,
                "outcome": run.outcome,
                "node_id": node.id,
                "node_status": node.status,
                "first_attempt_failed": first_failed,
                "attempt_count": len(attempts),
                "attempts": [
                    {
                        "attempt": a.attempt_no,
                        "status": a.status,
                        "error": a.error_json,
                    }
                    for a in attempts
                ],
                "assertion_ids": assertion_ids,
                "evidence": {
                    "run": f"run:{run.id}",
                    "node": f"node:{node.id}",
                    "attempts": [f"attempt:{a.id}" for a in attempts],
                },
            }
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return report
    finally:
        server.shutdown()
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-retry")
    args = parser.parse_args(argv)
    report = run(out=Path(args.out))
    print(json.dumps({"status": report["status"], "attempts": report["attempt_count"], "first_failed": report["first_attempt_failed"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
