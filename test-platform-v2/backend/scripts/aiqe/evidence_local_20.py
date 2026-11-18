"""AIQE 环境证据：在现有本地环境连续执行 20 次混合 Workflow。

真实链路：
- HTTP 节点直连运行中的后端（127.0.0.1:7778）：健康检查 + 管理员登录；
- DB 节点通过 AUD-002 登记查询读取 `sys_project`（只读连接）；
- 断言由后端 Assertion Engine 判定，Run/节点/断言全部落库。

用法（后端需已启动，且管理员密码可用）：
    python scripts/aiqe/evidence_local_20.py --base-url http://127.0.0.1:7778 \
        --runs 20 --password admin123
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

DB_PATH = BACKEND / "data" / "aiqe_evidence.db"
READONLY_PATH = BACKEND / "data" / "aiqe_readonly.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
os.environ.setdefault(
    "AIQE_DB_READONLY_URLS",
    json.dumps({"evidence": f"sqlite:///{READONLY_PATH.as_posix()}"}),
)

import app.models  # noqa: E402,F401
from sqlalchemy import select  # noqa: E402

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun  # noqa: E402
from app.aiqe.security import upsert_target_policy  # noqa: E402
from app.aiqe.services import dag_scheduler, node_executor, result_writer  # noqa: E402
from app.aiqe.services.query_registry import register_query  # noqa: E402
from app.aiqe.services.run_context import RunContext  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402

PROJECT_ID = 1


def _assertion(key: str, **spec: object) -> dict:
    return {"assertion_key": key, "operator": "equals", **spec}


def build_graph(base_url: str) -> dict:
    return {
        "schema_version": "1.0",
        "edges": [],
        "nodes": [
            {
                "key": "health",
                "driver": "http",
                "depends_on": [],
                "input": {
                    "url": f"{base_url}/api/v1/open/health",
                    "method": "GET",
                    "timeout_ms": 10000,
                    "assertions": [
                        _assertion("health.http", source="http_status", expected=200),
                        _assertion(
                            "health.status",
                            source="http_body",
                            path="$.data.status",
                            expected="ok",
                        ),
                    ],
                },
            },
            {
                "key": "login",
                "driver": "http",
                "depends_on": ["health"],
                "input": {
                    "url": f"{base_url}/api/v1/auth/login",
                    "method": "POST",
                    "json": {
                        "username": "admin",
                        "password": "${secrets.ADMIN_PASSWORD}",
                    },
                    "timeout_ms": 10000,
                    "assertions": [
                        _assertion("login.http", source="http_status", expected=200),
                        _assertion(
                            "login.token",
                            source="http_body",
                            path="$.data.access_token",
                            operator="exists",
                            expected=True,
                        ),
                    ],
                },
            },
            {
                "key": "verify_db_readonly",
                "driver": "db",
                "depends_on": ["health"],
                "input": {
                    "query_key": "evidence_project_count",
                    "params": {},
                    "assertions": [
                        _assertion(
                            "db.row",
                            source="db_query",
                            path="$[0]",
                            operator="exists",
                            expected=True,
                        )
                    ],
                },
            },
        ],
    }


def seed(db) -> None:
    upsert_target_policy(
        db,
        project_id=PROJECT_ID,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [7778],
            "allow_private_cidrs": ["127.0.0.0/8"],
            "allowed_methods": ["GET", "POST"],
        },
        name="evidence-local",
    )
    register_query(
        db,
        project_id=PROJECT_ID,
        query_key="evidence_project_count",
        statement="SELECT id, code FROM sys_project WHERE id = :project_id",
        allowed_params=["project_id"],
        connection_ref="evidence",
        created_by=1,
        approved_by=1,
    )
    db.commit()
    # SQLite WAL：先 checkpoint，确保只读副本包含已提交数据。
    from sqlalchemy import text

    db.execute(text("PRAGMA wal_checkpoint(FULL)"))
    db.commit()
    shutil.copyfile(DB_PATH, READONLY_PATH)


def execute_run(db, *, graph: dict, run: TestRun, password: str) -> None:
    secrets = {"ADMIN_PASSWORD": password}
    ctx = RunContext(db, run.id, graph=graph, secrets=secrets)
    dag_scheduler.schedule(db, run.id, graph)
    for _ in range(10):
        ready = list(
            db.scalars(
                select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.status == "READY")
            )
        )
        if not ready:
            break
        for node in ready:
            dag_scheduler.mark_running(db, run.id, node.node_key)
            db.commit()
            resolved = ctx.resolve_inputs(node.node_key, node.input_ref or {}, secrets=secrets)
            result = node_executor.execute_node(node, db=db, input_override=dict(resolved))
            observation = result_writer.observation_from_payload(result.observation)
            status, error_class, outcomes = result_writer.evaluate_node_assertions(
                db,
                run_id=run.id,
                node=node,
                observation=observation,
                driver_status=result.status,
                driver_error=result.error_class or None,
            )
            dag_scheduler.complete_node(
                db,
                run.id,
                node.node_key,
                status or result.status,
                graph,
                error_class=error_class,
                outputs={"assertions": [item.payload() for item in outcomes]},
            )
            db.commit()
        dag_scheduler.schedule(db, run.id, graph)
    dag_scheduler.finalize_run(db, run.id, graph)
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:7778")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--password", default=os.environ.get("AIQE_EVIDENCE_PASSWORD", "admin123"))
    parser.add_argument(
        "--output",
        default=str(BACKEND.parent.parent / "docs/aiqe/evidence/local-dogfood-20.json"),
    )
    args = parser.parse_args()

    db = SessionLocal()
    records: list[dict] = []
    try:
        seed(db)
        graph = build_graph(args.base_url.rstrip("/"))
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        for index in range(1, args.runs + 1):
            run = TestRun(
                project_id=PROJECT_ID,
                run_key=f"EVID-LOCAL-{stamp}-{index:02d}",
                source_type="dogfood",
                status="QUEUED",
                created_at=datetime.now(UTC),
            )
            db.add(run)
            db.flush()
            dag_scheduler.create_node_runs(db, run.id, graph)
            execute_run(db, graph=graph, run=run, password=args.password)
            db.refresh(run)
            node_statuses = {
                node.node_key: node.status
                for node in db.scalars(select(NodeRun).where(NodeRun.run_id == run.id))
            }
            assertion_rows = db.execute(
                select(RunAssertionResult)
                .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
                .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
                .where(NodeRun.run_id == run.id)
            ).scalars()
            assertions = list(assertion_rows)
            records.append(
                {
                    "index": index,
                    "run_id": run.id,
                    "run_key": run.run_key,
                    "status": run.status,
                    "outcome": run.outcome,
                    "node_statuses": node_statuses,
                    "assertions": len(assertions),
                    "assertion_failures": [row.assertion_key for row in assertions if row.status == "FAIL"],
                }
            )
            print(
                f"[{index:02d}] {run.run_key} {run.status}/{run.outcome} nodes={node_statuses} "
                f"assertions={len(assertions)}"
            )
        plaintext = list(
            db.scalars(
                select(TestRun).where(
                    TestRun.environment_snapshot_json.isnot(None)
                )
            )
        )
        payload_text = json.dumps(
            [run.environment_snapshot_json for run in plaintext], ensure_ascii=False
        )
        assert args.password not in payload_text, "secret leaked into run snapshot"
    finally:
        db.close()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "base_url": args.base_url,
                "runs": records,
                "passed": sum(1 for item in records if item["outcome"] == "PASS"),
                "failed": sum(1 for item in records if item["outcome"] != "PASS"),
                "digest": hashlib.sha256(
                    json.dumps(records, sort_keys=True).encode()
                ).hexdigest(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"evidence -> {output}")
    if any(item["outcome"] != "PASS" for item in records):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
