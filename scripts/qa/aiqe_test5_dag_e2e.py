"""V16-017 TC-003 产品级 DAG 执行与证据（真实 test5 API）。

使用本地 AIQE 运行时（Launch → Worker → HTTP Driver → Assertion → Artifact），
目标为 test5 真实接口：`https://camel-test5.elelive.cn/account-service/ee/client/general`。
证据写入 work-logs/evidence/aiqe-v16/test5-dag/report.json；不修改 test5 数据。

运行：
  python scripts/qa/aiqe_test5_dag_e2e.py
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import job_consumer
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.core.db import Base
from app.models.project import Project

TARGET_URL = "https://camel-test5.elelive.cn/account-service/ee/client/general"
COUNTRY_URL = "https://camel-test5.elelive.cn/account-service/ee/client/getCountryCode"
HOST = "camel-test5.elelive.cn"


def _drain(db: Session) -> None:
    for _ in range(20):
        claimed = job_consumer.claim_aiqe_jobs(db)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db, job_id)
        db.commit()


def run(*, out: Path) -> dict:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Project(id=1, code="TEST5", name="Camel test5", owner_id=1, status=1))
        db.flush()
        register_manifest(
            db,
            node_id="product-http",
            driver_key="http",
            capabilities=["aiqe:http"],
            platforms=["linux"],
            evidence_ref="evidence://product-http",
        )
        upsert_target_policy(
            db,
            project_id=1,
            environment_id=None,
            policy={
                "allowed_hosts": [HOST],
                "allowed_ports": [443],
                "allowed_schemes": ["https"],
                "allow_private_cidrs": ["192.168.0.0/16"],
            },
        )
        graph = {
            "schema_version": "1.0",
            "nodes": [
                {
                    "key": "test5_general",
                    "driver": "http",
                    "depends_on": [],
                    "input": {"url": TARGET_URL, "expected_status": 200},
                    "assertions": [
                        {
                            "assertion_key": "http_200",
                            "oracle_layer": "REQ",
                            "oracle_ref": "TC-AIQE-003-API-200",
                            "type": "http_status",
                            "expected": 200,
                            "severity": "P0",
                        },
                        {
                            "assertion_key": "business_status",
                            "oracle_layer": "REQ",
                            "oracle_ref": "TC-AIQE-003-BIZ-STATUS",
                            "type": "jsonpath",
                            "path": "$.status",
                            "expected": 200,
                            "severity": "P0",
                        },
                    ],
                },
                {
                    "key": "country_code",
                    "driver": "http",
                    "depends_on": ["test5_general"],
                    "input": {"url": COUNTRY_URL, "expected_status": 200},
                    "assertions": [
                        {
                            "assertion_key": "country_http_200",
                            "oracle_layer": "REQ",
                            "oracle_ref": "TC-AIQE-003-COUNTRY-200",
                            "type": "http_status",
                            "expected": 200,
                            "severity": "P0",
                        },
                        {
                            "assertion_key": "country_business_status",
                            "oracle_layer": "REQ",
                            "oracle_ref": "TC-AIQE-003-COUNTRY-STATUS",
                            "type": "jsonpath",
                            "path": "$.status",
                            "expected": 200,
                            "severity": "P0",
                        },
                    ],
                }
            ],
            "edges": [{"from": "test5_general", "to": "country_code"}],
        }
        workflow = create_workflow(db, project_id=1, graph=graph)
        approve_workflow(db, workflow.id, approved_by=1)
        run = launch_run(
            db,
            project_id=1,
            user_id=1,
            workflow_definition_id=workflow.id,
            launch_key=f"tc003-{uuid.uuid4().hex}",
        )
        db.commit()
        _drain(db)
        db.expire_all()
        run = db.get(TestRun, run.id)
        nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
        attempts = list(
            db.scalars(
                select(StepAttempt).where(
                    StepAttempt.node_run_id.in_([node.id for node in nodes])
                ).order_by(StepAttempt.attempt_no)
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
        artifacts = list(
            db.scalars(select(RunArtifact).where(RunArtifact.run_id == run.id))
        )
        report = {
            "schema_version": "1.0",
            "status": "PASS" if run.outcome == "PASS" else "FAIL",
            "executed_at": datetime.now(UTC).isoformat(),
            "target": TARGET_URL,
            "run_id": run.id,
            "run_status": run.status,
            "outcome": run.outcome,
            "node_ids": [node.id for node in nodes],
            "node_statuses": {node.node_key: node.status for node in nodes},
            "assertion_ids": assertion_ids,
            "artifact_ids": [item.id for item in artifacts],
            "artifact_count": len(artifacts),
            "attempts": [
                {"attempt": a.attempt_no, "status": a.status, "error": a.error_json}
                for a in attempts
            ],
            "evidence": {
                "run": f"run:{run.id}",
                "nodes": [f"node:{node.id}" for node in nodes],
                "assertion_count": len(assertion_ids),
            },
        }
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-dag")
    args = parser.parse_args(argv)
    report = run(out=Path(args.out))
    print(json.dumps({"status": report["status"], "run_id": report["run_id"], "outcome": report["outcome"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
