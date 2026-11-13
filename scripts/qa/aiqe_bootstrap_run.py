"""AIQE 新项目引导：注册能力节点 + 用 Workflow Graph 创建并派发一条 Run。

在 backend 容器内执行（需要 DATABASE_URL 与 app 代码）：

  docker exec -e PYTHONPATH=/app -w /app <backend容器> python /tmp/aiqe_bootstrap_run.py \
    --project-code camel1-tv --graph /tmp/graph.json

可选：--manifest-node prod-aiqe-inprocess --manifest-capabilities aiqe:http,aiqe:api \
      --manifest-platforms linux --manifest-evidence-ref prod://...
"""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from sqlalchemy import select

from app.aiqe.models.run import TestRun
from app.aiqe.services import dag_scheduler
from app.aiqe.services.capability_registry import known_capabilities, register_manifest
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.aiqe.services.workflow_validator import (
    WorkflowValidationError,
    validate_workflow,
)
from app.core.db import SessionLocal
from app.models.execution_job import ExecutionJob
from app.models.project import Project

DRIVERS = {"http", "playwright", "db", "event", "mobile", "miniapp", "device", "external_e2e"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--graph", required=True, help="workflow graph JSON 文件")
    parser.add_argument("--run-key", default="")
    parser.add_argument("--manifest-node", default="")
    parser.add_argument("--manifest-capabilities", default="")
    parser.add_argument("--manifest-platforms", default="linux")
    parser.add_argument("--manifest-evidence-ref", default="")
    parser.add_argument("--no-dispatch", action="store_true")
    args = parser.parse_args()

    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    try:
        validate_workflow(
            graph,
            registered_drivers=DRIVERS,
            registered_capabilities=set(known_capabilities()),
        )
    except WorkflowValidationError as exc:
        print(json.dumps({"ok": False, "error": f"graph 校验失败: {exc}"}, ensure_ascii=False))
        return 2

    db = SessionLocal()
    try:
        project = db.scalar(select(Project).where(Project.code == args.project_code))
        if project is None:
            print(json.dumps({"ok": False, "error": f"项目不存在: {args.project_code}"}, ensure_ascii=False))
            return 2

        manifest = None
        if args.manifest_node:
            caps = [c.strip() for c in args.manifest_capabilities.split(",") if c.strip()]
            platforms = [p.strip() for p in args.manifest_platforms.split(",") if p.strip()]
            row = register_manifest(
                db,
                node_id=args.manifest_node,
                driver_key="inprocess-http",
                driver_version="release-m15",
                capabilities=caps,
                platforms=platforms,
                max_parallel_sessions=2,
                artifact_types=["http-evidence"],
                evidence_ref=args.manifest_evidence_ref,
            )
            db.commit()
            manifest = {"node_id": row.node_id, "capabilities": caps, "platforms": platforms}

        run = TestRun(
            project_id=project.id,
            run_key=args.run_key or f"BOOT-{uuid.uuid4().hex[:8]}",
            source_type="manual",
            status="QUEUED",
        )
        db.add(run)
        db.flush()
        dag_scheduler.create_node_runs(db, run.id, graph)
        if not args.no_dispatch:
            dag_scheduler.schedule(
                db,
                run.id,
                graph,
                dispatch=lambda node: enqueue_node_run(db, node, graph=graph),
            )
        db.commit()
        job = db.scalar(select(ExecutionJob).where(ExecutionJob.payload_json.like(f"%{run.id}%")))
        print(
            json.dumps(
                {
                    "ok": True,
                    "project": {"id": project.id, "code": project.code},
                    "run_id": run.id,
                    "run_key": run.run_key,
                    "job_id": job.id if job else None,
                    "manifest": manifest,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
