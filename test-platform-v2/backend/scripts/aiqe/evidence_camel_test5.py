"""AIQE 环境证据：Camel Test5 环境连续执行 20 次只读 Workflow。

真实目标：`https://camel-test5.elelive.cn`（CamelTv Test5 API，页面
`https://camelive-g3-test5.elelive.cn` 实际调用同一网关）：
- `GET /camel-service/ee/sports_live/home_match?day=<today>&sportType=football`
- `GET /account-service/ee/client/general`

只执行 GET，不创建/修改测试数据。Run/Node/Assertion 全部落到 AIQE 本地库。

用法：
    python scripts/aiqe/evidence_camel_test5.py --runs 20
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

DB_PATH = BACKEND / "data" / "aiqe_evidence.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

import app.models  # noqa: E402,F401
from sqlalchemy import select  # noqa: E402

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun  # noqa: E402
from app.aiqe.security import upsert_target_policy  # noqa: E402
from app.aiqe.services import dag_scheduler, node_executor, result_writer  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402

PROJECT_ID = 1
HOST = "camel-test5.elelive.cn"
TODAY = datetime.now(UTC).strftime("%Y%m%d")


def _assertion(key: str, **spec: object) -> dict:
    return {"assertion_key": key, "operator": "equals", **spec}


def build_graph() -> dict:
    return {
        "schema_version": "1.0",
        "edges": [],
        "nodes": [
            {
                "key": "home_match",
                "driver": "http",
                "depends_on": [],
                "input": {
                    "url": (
                        f"https://{HOST}/camel-service/ee/sports_live/home_match"
                        f"?day={TODAY}&sportType=football"
                    ),
                    "method": "GET",
                    "timeout_ms": 15000,
                    "assertions": [
                        _assertion("home.http", source="http_status", expected=200),
                        _assertion("home.status", source="http_body", path="$.status", expected=200),
                        _assertion(
                            "home.today",
                            source="http_body",
                            path="$.data.today",
                            operator="exists",
                            expected=True,
                        ),
                        _assertion(
                            "home.groups",
                            source="http_body",
                            path="$.data.living_group",
                            operator="exists",
                            expected=True,
                        ),
                    ],
                },
            },
            {
                "key": "client_general",
                "driver": "http",
                "depends_on": ["home_match"],
                "input": {
                    "url": f"https://{HOST}/account-service/ee/client/general",
                    "method": "GET",
                    "timeout_ms": 15000,
                    "assertions": [
                        _assertion("client.http", source="http_status", expected=200),
                        _assertion(
                            "client.status", source="http_body", path="$.status", expected=200
                        ),
                        _assertion(
                            "client.ip",
                            source="http_body",
                            path="$.data.ip",
                            operator="exists",
                            expected=True,
                        ),
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
            "allowed_hosts": [HOST],
            "allowed_ports": [443],
            "allowed_methods": ["GET"],
            "allow_private_cidrs": ["192.168.0.0/16"],
            "verify_tls": True,
        },
        name="camel-test5-evidence",
    )
    db.commit()


def execute_run(db, *, graph: dict, run: TestRun) -> None:
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
            result = node_executor.execute_node(
                node,
                policy_context=node_executor.policy_context_for(db, node),
                db=db,
            )
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
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument(
        "--output",
        default=str(BACKEND.parent.parent / "docs/aiqe/evidence/camel-test5-20.json"),
    )
    args = parser.parse_args()

    db = SessionLocal()
    records: list[dict] = []
    try:
        seed(db)
        graph = build_graph()
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        for index in range(1, args.runs + 1):
            run = TestRun(
                project_id=PROJECT_ID,
                run_key=f"CAMEL-TEST5-{stamp}-{index:02d}",
                source_type="dogfood",
                status="QUEUED",
                created_at=datetime.now(UTC),
            )
            db.add(run)
            db.flush()
            dag_scheduler.create_node_runs(db, run.id, graph)
            execute_run(db, graph=graph, run=run)
            db.refresh(run)
            node_statuses = {
                node.node_key: node.status
                for node in db.scalars(select(NodeRun).where(NodeRun.run_id == run.id))
            }
            assertions = list(
                db.scalars(
                    select(RunAssertionResult)
                    .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
                    .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
                    .where(NodeRun.run_id == run.id)
                )
            )
            records.append(
                {
                    "index": index,
                    "run_id": run.id,
                    "run_key": run.run_key,
                    "status": run.status,
                    "outcome": run.outcome,
                    "node_statuses": node_statuses,
                    "assertions": len(assertions),
                    "assertion_failures": [
                        row.assertion_key for row in assertions if row.status == "FAIL"
                    ],
                }
            )
            print(
                f"[{index:02d}] {run.run_key} {run.status}/{run.outcome} "
                f"nodes={node_statuses} assertions={len(assertions)}"
            )
    finally:
        db.close()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "target": f"https://{HOST}",
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
    return 0 if all(item["outcome"] == "PASS" for item in records) else 1


if __name__ == "__main__":
    sys.exit(main())
