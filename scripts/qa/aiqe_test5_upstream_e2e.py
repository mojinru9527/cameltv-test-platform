"""V16-017 TC-006 产品级：上游第三方 504 → Node BLOCKED/UPSTREAM，不归因产品。

- test-side upstream stub 固定返回 504（模拟赛程第三方依赖故障）；
- 节点输入显式 `upstream_dependency: true`，AIQE 必须 BLOCKED/UPSTREAM_5XX；
- 业务 Assertion 不得 PASS/FAIL 归因产品，Run 不得 PASS。
"""
from __future__ import annotations

import argparse
import json
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

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


class _UpstreamStub(BaseHTTPRequestHandler):
    hits = 0

    def log_message(self, *_args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        _UpstreamStub.hits += 1
        body = b'{"status":504,"msg":"upstream timeout"}'
        self.send_response(504)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _drain(db: Session) -> None:
    for _ in range(10):
        claimed = job_consumer.claim_aiqe_jobs(db)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db, job_id)
        db.commit()


def run(*, out: Path) -> dict:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _UpstreamStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(Project(id=1, code="TEST5", name="Camel test5", owner_id=1, status=1))
            db.flush()
            register_manifest(
                db,
                node_id="upstream-http",
                driver_key="http",
                capabilities=["aiqe:http"],
                platforms=["linux"],
                evidence_ref="evidence://upstream-http",
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
                "nodes": [
                    {
                        "key": "third_party_schedule",
                        "driver": "http",
                        "depends_on": [],
                        "input": {
                            "url": f"http://127.0.0.1:{port}/third-party/schedule",
                            "expected_status": 200,
                            "upstream_dependency": True,
                        },
                        "assertions": [
                            {
                                "assertion_key": "schedule_200",
                                "oracle_layer": "REQ",
                                "oracle_ref": "TC-AIQE-006-UPSTREAM",
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
                launch_key=f"tc006-{uuid.uuid4().hex}",
            )
            db.commit()
            _drain(db)
            db.expire_all()
            run = db.get(TestRun, run.id)
            node = db.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
            attempts = list(db.scalars(select(StepAttempt).where(StepAttempt.node_run_id == node.id)))
            assertions = list(
                db.scalars(
                    select(RunAssertionResult).where(
                        RunAssertionResult.step_attempt_id.in_([a.id for a in attempts])
                    )
                )
            )
            passed = (
                node.status == "BLOCKED"
                and node.error_class == "UPSTREAM_5XX"
                and run.outcome != "PASS"
                and all(item.status != "PASS" for item in assertions)
            )
            report = {
                "schema_version": "1.0",
                "status": "PASS" if passed else "FAIL",
                "executed_at": datetime.now(UTC).isoformat(),
                "upstream_stub": f"http://127.0.0.1:{port}/third-party/schedule",
                "upstream_hits": _UpstreamStub.hits,
                "run_id": run.id,
                "run_status": run.status,
                "outcome": run.outcome,
                "node_id": node.id,
                "node_status": node.status,
                "error_class": node.error_class,
                "assertions": [{"status": item.status} for item in assertions],
                "bug_created": False,
                "evidence": {"run": f"run:{run.id}", "node": f"node:{node.id}"},
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
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-upstream")
    args = parser.parse_args(argv)
    report = run(out=Path(args.out))
    print(json.dumps({"status": report["status"], "node": report["node_status"], "error": report["error_class"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
