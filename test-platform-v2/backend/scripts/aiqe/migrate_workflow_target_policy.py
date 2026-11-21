"""V16-001 §5：旧 Workflow 目标策略迁移命令（隔离迁移工具，不被 Worker 进程 import）。

背景
----
V1.5 及更早的 Workflow 把 `allowed_hosts` / `allow_private` / `allowed_tables` /
`query_registry` / `sql` 写在节点 input 里，这些字段在 V1.6 起**不参与权限决策**。
本命令负责把它们显式迁移到服务端 `aiqe_target_policies`：

- 可映射（存在明确目标 URL / 显式 allowed_hosts，且不含 inline SQL/查询注册表）→ 生成候选策略；
- 不可映射（含 SQL/query_registry/allowed_tables/连接串、私网开关但未显式提供 CIDR、
  无任何目标 URL）→ 标记 `NEEDS_POLICY_REVIEW`，禁止调度，等待管理员人工配置。

安全约束
--------
- 默认 dry-run，只有显式 `--apply` 才写库；
- `allow_private` 绝不自动转成私网授权，必须由管理员用 `--allow-private-cidrs` 显式给出；
- 同一 project 的多条 Workflow 合并为**一条**项目级策略（union），避免逐个 upsert 互相覆盖；
- 本脚本不得被 `app/` 引用（静态扫描 `tests/test_aiqe_v16_001_policy_fail_closed.py` 覆盖）。

用法
----
    python scripts/aiqe/migrate_workflow_target_policy.py --database-url sqlite:///...
    python scripts/aiqe/migrate_workflow_target_policy.py --database-url ... --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from app.aiqe.models.workflow import WorkflowDefinition  # noqa: E402
from app.aiqe.security import upsert_target_policy  # noqa: E402

POLICY_UNREVIEWED = "UNREVIEWED"
POLICY_MIGRATED = "MIGRATED"
POLICY_NEEDS_REVIEW = "NEEDS_POLICY_REVIEW"

#: 旧 Workflow 中一旦出现就无法自动映射为服务端策略的字段。
UNMAPPABLE_DB_KEYS = frozenset(
    {
        "sql",
        "statement",
        "query",
        "query_registry",
        "allowed_tables",
        "allowed_columns",
        "connection_url",
        "connection_ref",
        "database_url",
        "registry",
    }
)
#: 只作为历史数据、迁移后可删除的字段（本命令只读取，不回写 graph）。
LEGACY_POLICY_KEYS = frozenset(
    {"allowed_hosts", "allow_private", "allowed_ports", "max_redirects", "verify_tls"}
)


@dataclass
class WorkflowAnalysis:
    workflow_id: str
    project_id: int
    version: int
    status: str = POLICY_UNREVIEWED
    reasons: list[str] = field(default_factory=list)
    hosts: set[str] = field(default_factory=set)
    ports: set[int] = field(default_factory=set)
    allow_private_requested: bool = False


def _url_host_port(raw: str) -> tuple[str, int] | None:
    try:
        parsed = urlsplit(str(raw or "").strip())
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None
    return parsed.hostname.strip().lower(), int(port)


def analyze_workflow(workflow: WorkflowDefinition) -> WorkflowAnalysis:
    analysis = WorkflowAnalysis(
        workflow_id=str(workflow.id),
        project_id=int(workflow.project_id),
        version=int(workflow.version or 0),
    )
    graph = workflow.graph_json if isinstance(workflow.graph_json, dict) else {}
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        key = str(node.get("key") or "?")
        spec_input = node.get("input") if isinstance(node.get("input"), dict) else {}
        node_input = dict(spec_input or {})
        if str(node.get("driver") or "").lower() in {"db", "db_readonly", "database"}:
            # DB 节点必须迁移为服务端 Query Registry，不能自动生成策略。
            analysis.reasons.append(f"{key}:db_node_requires_query_registry")
        for banned in sorted(UNMAPPABLE_DB_KEYS & set(node_input)):
            analysis.reasons.append(f"{key}:{banned}_requires_manual_migration")
        for legacy_host in node_input.get("allowed_hosts") or []:
            host = str(legacy_host).strip().lower().lstrip("*.")
            if host:
                analysis.hosts.add(host)
        if bool(node_input.get("allow_private")):
            analysis.allow_private_requested = True
        for legacy_port in node_input.get("allowed_ports") or []:
            try:
                analysis.ports.add(int(legacy_port))
            except (TypeError, ValueError):
                analysis.reasons.append(f"{key}:invalid_allowed_port")
        target = _url_host_port(str(node_input.get("url") or ""))
        if target is not None:
            analysis.hosts.add(target[0])
            analysis.ports.add(target[1])
        if not str(node_input.get("url") or "").strip() and str(
            node.get("driver") or ""
        ).lower() in {"http", "httpx", "api", "playwright", "web", "ui"}:
            analysis.reasons.append(f"{key}:missing_target_url")
    if analysis.allow_private_requested:
        analysis.reasons.append("allow_private_requires_admin_cidrs")
    if not analysis.hosts:
        analysis.reasons.append("no_mappable_target")
    analysis.status = POLICY_NEEDS_REVIEW if analysis.reasons else POLICY_MIGRATED
    return analysis


def _dedupe(reasons: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        ordered.append(reason)
    return ordered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="迁移旧 Workflow 目标字段到服务端 TargetPolicy")
    parser.add_argument("--database-url", required=True, help="平台数据库 URL")
    parser.add_argument("--project-id", type=int, default=None, help="只处理指定项目")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认 dry-run）")
    parser.add_argument(
        "--allow-private-cidrs",
        default="",
        help="管理员显式授权的私网网段（逗号分隔）；未提供时 allow_private 一律 NEEDS_POLICY_REVIEW",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="存在 NEEDS_POLICY_REVIEW 时以非 0 退出（CI/发布门禁用）",
    )
    args = parser.parse_args(argv)

    import os

    os.environ["DATABASE_URL"] = args.database_url

    import app.models  # noqa: F401 - 注册全部模型
    from sqlalchemy import select

    from app.core.db import SessionLocal

    private_cidrs = [item.strip() for item in str(args.allow_private_cidrs or "").split(",") if item.strip()]
    db = SessionLocal()
    try:
        query = select(WorkflowDefinition)
        if args.project_id is not None:
            query = query.where(WorkflowDefinition.project_id == int(args.project_id))
        workflows = list(db.scalars(query))
        analyses = [analyze_workflow(row) for row in workflows]

        per_project: dict[int, dict[str, set]] = {}
        for analysis in analyses:
            if analysis.status != POLICY_MIGRATED:
                continue
            bucket = per_project.setdefault(
                analysis.project_id, {"hosts": set(), "ports": set()}
            )
            bucket["hosts"].update(analysis.hosts)
            bucket["ports"].update(analysis.ports)

        applied: list[dict] = []
        if args.apply:
            for project_id, bucket in sorted(per_project.items()):
                policy = {
                    "allowed_hosts": sorted(bucket["hosts"]),
                    "allowed_ports": sorted(bucket["ports"]),
                    "max_redirects": 0,
                }
                if private_cidrs:
                    policy["allow_private_cidrs"] = private_cidrs
                record = upsert_target_policy(
                    db,
                    project_id=project_id,
                    environment_id=None,
                    policy=policy,
                    name="migrated-v16",
                )
                applied.append(
                    {
                        "project_id": project_id,
                        "policy_id": record.id,
                        "version": int(record.version or 0),
                        "allowed_hosts": policy["allowed_hosts"],
                        "allowed_ports": policy["allowed_ports"],
                        "allow_private_cidrs": private_cidrs,
                    }
                )
            by_id = {str(row.id): row for row in workflows}
            for analysis in analyses:
                row = by_id.get(analysis.workflow_id)
                if row is None:
                    continue
                # 无法映射的 Workflow 也写标记，确保后续调度被拦截。
                row.policy_status = analysis.status
            db.commit()

        report = {
            "mode": "apply" if args.apply else "dry-run",
            "workflow_count": len(analyses),
            "migrated": sum(1 for item in analyses if item.status == POLICY_MIGRATED),
            "needs_policy_review": sum(
                1 for item in analyses if item.status == POLICY_NEEDS_REVIEW
            ),
            "policies": applied,
            "workflows": [
                {
                    "workflow_id": item.workflow_id,
                    "project_id": item.project_id,
                    "version": item.version,
                    "status": item.status,
                    "reasons": _dedupe(item.reasons),
                    "candidate_hosts": sorted(item.hosts),
                    "candidate_ports": sorted(item.ports),
                    "allow_private_requested": item.allow_private_requested,
                }
                for item in analyses
            ],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        if args.strict and report["needs_policy_review"]:
            return 2
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
