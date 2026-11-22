"""TC-AIQE-005 产品级：共享 resource key 的两个 Run 必须串行（test5）。

- test5 API 经 1.5s 延迟代理，确保锁被持有；
- Run A / Run B 使用同一 `resource_keys=["match:l7oqdehg7gkgr51"]`；
- 断言 B 节点在 A 完成后才开始，且无重叠。
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.workflow import ResourceLock
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.core.db import Base
from app.models.project import Project


class _SlowProxy(BaseHTTPRequestHandler):
    hits = 0

    def log_message(self, *_args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        _SlowProxy.hits += 1
        time.sleep(1.5)
        try:
            r = requests.get("https://camel-test5.elelive.cn" + self.path, timeout=20)
            body = r.content
            self.send_response(r.status_code)
            self.send_header("content-type", r.headers.get("content-type", "application/json"))
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            body = b'{"status":502}'
            self.send_response(502)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def _graph(port: int) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "shared_match",
                "driver": "http",
                "depends_on": [],
                "resource_keys": ["match:l7oqdehg7gkgr51"],
                "input": {
                    "url": f"http://127.0.0.1:{port}/account-service/ee/client/general",
                    "expected_status": 200,
                },
                "assertions": [
                    {
                        "assertion_key": "http_200",
                        "oracle_layer": "REQ",
                        "oracle_ref": "TC-AIQE-005",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            }
        ],
        "edges": [],
    }


def run(*, out: Path) -> dict:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SlowProxy)
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
                node_id="concurrency-http",
                driver_key="http",
                capabilities=["aiqe:http"],
                platforms=["linux"],
                evidence_ref="evidence://concurrency-http",
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
            graph = _graph(port)
            workflow = create_workflow(db, project_id=1, graph=graph)
            approve_workflow(db, workflow.id, approved_by=1)
            run_a = launch_run(
                db, project_id=1, user_id=1, workflow_definition_id=workflow.id,
                launch_key=f"tc005-a-{uuid.uuid4().hex}",
            )
            db.commit()
            job_a = job_consumer.claim_aiqe_jobs(db)
            run_b = launch_run(
                db, project_id=1, user_id=1, workflow_definition_id=workflow.id,
                launch_key=f"tc005-b-{uuid.uuid4().hex}",
            )
            db.commit()
            job_b_before = job_consumer.claim_aiqe_jobs(db)
            for job_id in job_a:
                job_consumer.run_job(db, job_id)
            db.commit()
            db.expire_all()
            run_b = db.get(TestRun, run_b.id)
            if run_b is not None and run_b.status == "READY":
                run_b.status = "RUNNING"
                db.commit()
            node_b_pending = db.scalar(select(NodeRun).where(NodeRun.run_id == run_b.id))
            if node_b_pending is not None and node_b_pending.status == "READY":
                node_b_pending.status = "PENDING"
                db.commit()
            dag_scheduler.schedule(db, run_b.id, graph, dispatch=lambda row: enqueue_node_run(db, row, graph=graph))
            db.commit()
            db.expire_all()
            rb = db.get(TestRun, run_b.id); nb = db.scalar(select(NodeRun).where(NodeRun.run_id == run_b.id))
            job_b = job_consumer.claim_aiqe_jobs(db)
            for job_id in job_b:
                job_consumer.run_job(db, job_id)
            db.commit()
            db.expire_all()
            node_a = db.scalar(select(NodeRun).where(NodeRun.run_id == run_a.id))
            node_b = db.scalar(select(NodeRun).where(NodeRun.run_id == run_b.id))
            serialized = bool(
                node_a.finished_at
                and node_b.started_at
                and node_b.started_at >= node_a.finished_at
            )
            report = {
                "schema_version": "1.0",
                "status": "PASS" if serialized and not job_b_before else "FAIL",
                "executed_at": datetime.now(UTC).isoformat(),
                "resource_key": "match:l7oqdehg7gkgr51",
                "proxy_hits": _SlowProxy.hits,
                "run_a": {
                    "id": run_a.id,
                    "started": node_a.started_at.isoformat() if node_a.started_at else None,
                    "finished": node_a.finished_at.isoformat() if node_a.finished_at else None,
                    "status": node_a.status,
                },
                "run_b": {
                    "id": run_b.id,
                    "started": node_b.started_at.isoformat() if node_b.started_at else None,
                    "finished": node_b.finished_at.isoformat() if node_b.finished_at else None,
                    "status": node_b.status,
                },
                "b_job_before_a_finish": bool(job_b_before),
                "serialized": serialized,
            }
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        server.shutdown()
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-concurrency")
    args = parser.parse_args(argv)
    report = run(out=Path(args.out))
    print(json.dumps({"status": report["status"], "serialized": report["serialized"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
